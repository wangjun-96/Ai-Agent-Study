"""提示词层：只负责 Prompt 模板与链路组装。

职责边界（见 prompt.md「三层架构」）：
- 定义系统提示词与 Prompt 模板结构；
- 负责「Prompt + 模型」的链路（Runnable）组装；
- 不查询数据库、不创建模型实例、不执行业务逻辑。

模板占位符约定：
- {system_prompt}  ：系统提示词（后续可切换为提示词版本管理中的生效模板）
- history          ：历史消息列表（由记忆层提供，经 MessagesPlaceholder 插入）
- {request_text}   ：本轮用户提问
"""
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 默认系统提示词：通用中文学习/面试辅导助手
DEFAULT_SYSTEM_PROMPT = (
    "你是一名专业的中文 AI 学习与面试辅导助手。"
    "请用简洁、准确、结构化的中文回答问题，必要时给出示例；"
    "不确定的内容要明确说明，不要编造事实。"
)


def merge_system_messages(
    history: list[BaseMessage], system_prompt: str | None
) -> tuple[list[BaseMessage], str]:
    """把历史消息中的 SystemMessage 内容合并进最终系统提示词。

    长期记忆画像、工作记忆摘要等以 SystemMessage 存放在上下文最前，
    这里统一提取并合并，避免历史消息中出现多条 system 指令。

    :param history: 记忆层返回的消息列表
    :param system_prompt: 模板生成的系统提示词（可能为空）
    :return: (不含 SystemMessage 的历史消息, 合并后的系统提示词)
    """
    parts: list[str] = []
    if system_prompt and system_prompt.strip():
        parts.append(system_prompt.strip())
    filtered: list[BaseMessage] = []
    for message in history:
        if isinstance(message, SystemMessage):
            content = message.content
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
            continue
        filtered.append(message)
    merged = "\n\n".join(parts) or DEFAULT_SYSTEM_PROMPT
    return filtered, merged


def build_prompt(system_prompt: str | None = None) -> ChatPromptTemplate:
    """构建对话 Prompt 模板。

    :param system_prompt: 系统提示词，为空时使用默认提示词
    :return: 含 system / history / human 三段结构的 Prompt 模板
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt or DEFAULT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{request_text}"),
        ]
    )


def build_chain(llm, system_prompt: str | None = None):
    """组装「Prompt + 模型」链路。

    :param llm: 模型实例（由模型层 get_llm() 提供）
    :param system_prompt: 系统提示词，为空时使用默认提示词
    :return: 可调用 / 可流式输出的 Runnable 链路
    """
    return build_prompt(system_prompt) | llm
