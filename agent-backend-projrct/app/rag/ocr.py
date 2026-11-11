"""扫描版 PDF OCR：pypdfium2 渲染页面为 PNG，调用火山引擎 OCRNormal 提取文字。

对外只暴露 ocr_pdf(path)。凭证与区域全部来自配置层，业务层不直接调用 SDK。
"""
import base64
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from volcengine.visual.VisualService import VisualService

from app.core import SystemException, get_logger, settings
from app.enums.response_code import ResponseCode

logger = get_logger("rag_ocr")

# 渲染分辨率（DPI）：150 DPI 在 OCR 精度与请求体积之间较均衡
RENDER_DPI = 150


def _build_visual_service() -> VisualService:
    """构造火山 VisualService 并注入 AK/SK/区域。"""
    if not settings.VOLC_ACCESS_KEY.strip() or not settings.VOLC_SECRET_KEY.strip():
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="OCR 服务未配置，请联系管理员",
            detail="环境变量 VOLC_ACCESS_KEY / VOLC_SECRET_KEY 为空",
        )
    service = VisualService()
    service.set_ak(settings.VOLC_ACCESS_KEY.strip())
    service.set_sk(settings.VOLC_SECRET_KEY.strip())
    # 区域写入 service_info.credentials（默认 cn-north-1）
    service.service_info.credentials.region = settings.VOLC_REGION
    return service


def _ocr_image(service: VisualService, image_bytes: bytes) -> list[str]:
    """单页图片 OCR：base64 上送 OCRNormal，返回按行文本。"""
    form = {
        "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
        "language": "zh",
    }
    response = service.ocr_normal(form)
    if response.get("code") != 10000:
        logger.warning(
            "火山 OCR 失败 code={} message={}",
            response.get("code"),
            response.get("message"),
        )
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="扫描版 PDF 识别失败，请稍后再试",
            detail=f"code={response.get('code')}, message={response.get('message')}",
        )
    data = response.get("data") or {}
    return [str(line) for line in data.get("line_texts") or []]


def ocr_pdf(path: str | Path) -> str:
    """扫描版 PDF 转文字：逐页 150 DPI 渲染 PNG → OCR → 按行拼接全文。

    :param path: PDF 本地文件路径
    :return: 识别出的完整文本，无文字时返回空串
    """
    service = _build_visual_service()
    lines: list[str] = []
    document = pdfium.PdfDocument(str(path))
    try:
        for page_index in range(len(document)):
            page = document[page_index]
            bitmap = page.render(scale=RENDER_DPI / 72)
            image = bitmap.to_pil()
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            lines.extend(_ocr_image(service, buffer.getvalue()))
    finally:
        document.close()

    text = "\n".join(line for line in lines if line.strip())
    logger.info("PDF OCR 完成 path={} lines={} chars={}", path, len(lines), len(text))
    return text
