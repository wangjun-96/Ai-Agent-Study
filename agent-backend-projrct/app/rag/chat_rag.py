"""RAG 对话辅助：检索意图判断、资料格式化、RAG 系统提示词拼接。"""
from collections.abc import Sequence

# 确认/寒暄类短句：无需检索知识库
CONFIRM_WORDS = {
    "好", "好的", "可以", "行", "嗯", "是的", "对", "谢谢", "多谢",
    "收到", "明白", "知道了", "ok", "okay", "辛苦了",
}

# 推进对话类短句：承接上文，无需重新检索
PUSH_FORWARD_WORDS = {
    "继续", "下一步", "再来一个", "换一题", "下一题", "接着",
    "接着说", "然后呢", "继续吧", "换成下一题",
}

# RAG 资料使用规则：约束模型只依据召回片段作答并标注来源
RAG_RULES = """【检索资料使用规则】
1. 优先依据下方“参考资料”回答，不要编造资料中不存在的细节。
2. 资料不足以回答时，明确说明“现有资料未覆盖该内容”，再给出通用建议。
3. 引用资料时在句末标注 [资料N]，N 为资料编号。
4. 参考资料与用户问题无关时忽略资料，按常识回答。"""


def should_retrieve(request_text: str) -> bool:
    """判断是否需要检索知识库。

    - 空输入或极短输入：不检索；
    - 确认/寒暄短句、推进对话短句：不检索；
    - 其余问题：检索。
    """
    text = (request_text or "").strip()
    if len(text) < 2:
        return False
    normalized = text.lower().strip("。！？!? ")
    if len(normalized) <= 8 and normalized in CONFIRM_WORDS:
        return False
    if len(normalized) <= 10 and normalized in PUSH_FORWARD_WORDS:
        return False
    return True


def format_retrieved_chunks(chunks: Sequence[dict]) -> str:
    """把召回切片格式化为提示词中的“参考资料”段落。"""
    if not chunks:
        return ""
    lines = ["参考资料："]
    for index, chunk in enumerate(chunks, start=1):
        file_name = chunk.get("file_name") or "未知来源"
        chunk_index = chunk.get("chunk_index")
        location = f"，片段 {chunk_index}" if chunk_index is not None else ""
        text = (chunk.get("text") or "").strip()
        lines.append(f"【资料{index}】来源：{file_name}{location}\n{text}")
    return "\n\n".join(lines)


def build_rag_system_prompt(base_prompt: str) -> str:
    """在基础系统提示词后追加 RAG 资料使用规则。"""
    return f"{base_prompt.strip()}\n\n{RAG_RULES}"
