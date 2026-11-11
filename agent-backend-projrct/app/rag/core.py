"""RAG 文件向量化入库：解析 → 清洗 → 分类 → 递归切片 → 向量化 → 写 Qdrant。

对外只暴露 ``ingest_file``。原文不写 Qdrant，由调用方（RagService）写入
MySQL knowledge_chunks，两侧通过同一个 vector_id 关联。
"""
import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import PointStruct

from app.core import BusinessException, SystemException, get_logger, settings
from app.enums.response_code import ResponseCode
from app.rag.ocr import ocr_pdf
from app.rag.qdrant_utils import embed_texts, ensure_collection, get_qdrant_client

logger = get_logger("rag_core")

# 扫描版判定阈值：平均每页字符数低于该值视为扫描件，走 OCR 兜底
SCANNED_PDF_MIN_CHARS_PER_PAGE = 20

# 递归切片分隔符：按文档结构优先级从强到弱
CHUNK_SEPARATORS = [
    "\n###",
    "\n##",
    "\n#",
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    "；",
    "，",
    " ",
    "",
]

# 文档分类关键字（按命中次数计分，显式分类优先）
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "resume": (
        "简历", "个人信息", "教育背景", "工作经历", "项目经历",
        "求职意向", "自我评价", "专业技能", "获奖情况", "实习经历",
    ),
    "study_material": (
        "教程", "课程", "知识点", "考点", "章节", "习题",
        "例题", "考试", "学习笔记", "大纲", "复习", "重点",
    ),
}

# 零宽字符
INVISIBLE_PATTERN = re.compile(r"[\u200b-\u200f\ufeff]")
# 行内连续空白
INLINE_SPACE_PATTERN = re.compile(r"[ \t\u00a0]+")
# 连续空行
MULTI_NEWLINE_PATTERN = re.compile(r"\n{2,}")
# 独立页码行（如 "12"、"- 12 -"、"第 12 页"）
PAGE_NUMBER_PATTERN = re.compile(
    r"^\s*(?:[-—–]\s*)?(?:\d{1,4}|第\s*\d{1,4}\s*页)\s*(?:[-—–])?\s*$"
)


@dataclass
class IngestedChunk:
    """入库切片：vector_id 对齐 Qdrant point 与 MySQL knowledge_chunks。"""

    vector_id: str
    text: str
    chunk_index: int
    char_count: int


def _parse_file(path: Path) -> str:
    """按扩展名分派解析器，未知类型抛业务异常。"""
    ext = path.suffix.lower()
    parsers = {
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
        ".txt": _parse_txt,
        ".md": _parse_txt,
    }
    parser = parsers.get(ext)
    if parser is None:
        raise BusinessException(
            ResponseCode.PARAM_INVALID,
            message="不支持的文件类型，仅支持 PDF / DOCX / TXT",
            detail=f"ext={ext}",
        )
    return parser(path)


def _parse_pdf(path: Path) -> str:
    """PDF 解析：先抽文字，平均每页字符数过低判定扫描件并走 OCR 兜底。"""
    document = pdfium.PdfDocument(str(path))
    try:
        pages: list[str] = []
        for page_index in range(len(document)):
            page = document[page_index]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_range() or "")
        page_count = len(pages)
    finally:
        document.close()

    if page_count == 0:
        return ""

    total_chars = sum(len(text.strip()) for text in pages)
    avg_chars = total_chars / page_count
    if avg_chars < SCANNED_PDF_MIN_CHARS_PER_PAGE:
        logger.info(
            "PDF 判定为扫描件 path={} pages={} avg_chars={}，走 OCR 兜底",
            path,
            page_count,
            avg_chars,
        )
        return ocr_pdf(path)
    return "\n".join(pages)


def _parse_docx(path: Path) -> str:
    """DOCX 解析：识别 Heading 1/2/3 并注入 #/##/### 标题标记。"""
    document = Document(str(path))
    lines: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = paragraph.style.name if paragraph.style is not None else ""
        match = re.search(r"Heading\s*([1-3])", style_name or "", re.IGNORECASE)
        if match:
            level = int(match.group(1))
            lines.append(f"{'#' * level} {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def _parse_txt(path: Path) -> str:
    """TXT / Markdown 解析：按 UTF-8 读取，忽略非法字节。"""
    return path.read_text(encoding="utf-8", errors="ignore")


def _clean_text(text: str) -> str:
    """清洗：去零宽字符、合并空白、压缩换行、删除独立页码行。"""
    text = INVISIBLE_PATTERN.sub("", text)
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 逐行处理：合并行内空白、剔除页码行
    lines: list[str] = []
    for line in text.split("\n"):
        cleaned = INLINE_SPACE_PATTERN.sub(" ", line).strip()
        if PAGE_NUMBER_PATTERN.match(cleaned):
            continue
        lines.append(cleaned)
    text = "\n".join(lines)
    text = MULTI_NEWLINE_PATTERN.sub("\n\n", text)
    return text.strip()


def _classify_document(text: str, explicit: str | None) -> str:
    """文档分类：显式值优先，否则按关键字命中次数计分（resume/study_material/general）。"""
    if explicit:
        return explicit
    scores = {
        category: sum(text.count(keyword) for keyword in keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "general"
    return best


def _split_text(text: str) -> list[str]:
    """递归智能切片：500 字 / 50 重叠，MD5 去重。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
        keep_separator=True,
    )
    chunks: list[str] = []
    seen: set[str] = set()
    for chunk in splitter.split_text(text):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        digest = hashlib.md5(cleaned.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        chunks.append(cleaned)
    return chunks


def _write_qdrant(
    chunks: list[IngestedChunk],
    *,
    user_id: int,
    doc_category: str,
    file_name: str,
    resource_id: int,
) -> None:
    """向量化并写入 Qdrant：payload 只存过滤字段，不存原文。"""
    vectors = embed_texts([chunk.text for chunk in chunks])
    if len(vectors) != len(chunks):
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="文本向量化结果不完整，请稍后再试",
            detail=f"chunks={len(chunks)}, vectors={len(vectors)}",
        )
    points = [
        PointStruct(
            id=chunk.vector_id,
            vector=vector,
            payload={
                "user_id": user_id,
                "doc_category": doc_category,
                "file_name": file_name,
                "chunk_index": chunk.chunk_index,
                "resource_id": resource_id,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    client = get_qdrant_client()
    ensure_collection(client)
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points,
        wait=True,
    )


def ingest_file(
    path: str | Path,
    *,
    user_id: int,
    file_name: str,
    resource_id: int,
    doc_category: str | None = None,
) -> list[IngestedChunk]:
    """文件向量化入库：解析 → 清洗 → 分类 → 切片 → 向量化 → 写 Qdrant。

    :param path: 本地文件路径（PDF / DOCX / TXT / MD）
    :param user_id: 归属用户，用于检索隔离
    :param file_name: 原始文件名（检索结果展示来源）
    :param resource_id: 关联 resources 表 ID
    :param doc_category: 显式文档分类，为空时自动分类
    :return: 切片列表（含 vector_id / 原文 / 序号 / 字符数），供 MySQL 双存储
    """
    file_path = Path(path)
    raw_text = _parse_file(file_path)
    cleaned = _clean_text(raw_text)
    if not cleaned:
        logger.info("文件解析后无有效文本 file={}", file_name)
        return []

    category = _classify_document(cleaned, doc_category)
    parts = _split_text(cleaned)
    chunks = [
        IngestedChunk(
            vector_id=str(uuid.uuid4()),
            text=part,
            chunk_index=index,
            char_count=len(part),
        )
        for index, part in enumerate(parts)
    ]
    if chunks:
        _write_qdrant(
            chunks,
            user_id=user_id,
            doc_category=category,
            file_name=file_name,
            resource_id=resource_id,
        )
    logger.info(
        "文件向量化入库完成 file={} category={} chunks={} chars={}",
        file_name,
        category,
        len(chunks),
        len(cleaned),
    )
    return chunks
