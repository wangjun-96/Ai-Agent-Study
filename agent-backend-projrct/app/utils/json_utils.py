"""JSON 解析工具：容错解析大模型返回的 JSON 对象。

兼容三类常见输出：
1. 纯 JSON 对象；
2. Markdown ```json 围栏包裹；
3. 正文中混排 JSON（提取首个 { 到最后一个 } 之间的内容）。
"""
import json
import re

# Markdown 代码围栏
FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def parse_json_object(text: str) -> dict | None:
    """把模型输出解析为字典，失败返回 None（不抛出异常）。

    :param text: 模型原始输出
    :return: JSON 对象字典；无法解析时返回 None
    """
    raw = (text or "").strip()
    if not raw:
        return None

    candidates: list[str] = []
    fence_match = FENCE_PATTERN.search(raw)
    if fence_match:
        candidates.append(fence_match.group(1).strip())
    candidates.append(raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict):
            return payload
    return None
