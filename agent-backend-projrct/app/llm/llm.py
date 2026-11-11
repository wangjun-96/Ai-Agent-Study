"""模型层：只负责 provider -> 模型实例。

职责边界（见 prompt.md「三层架构」）：
- 本模块只做「根据配置创建 LangChain 模型实例」，不负责提示词拼接、
  不负责查询历史消息、不执行业务逻辑；
- provider、密钥、接入地址、模型名、温度等全部来自配置层，
  业务代码禁止硬编码；
- 实例按配置参数缓存，避免每次请求重复创建 HTTP 连接池。

所有 provider 均通过 OpenAI 兼容协议接入（deepseek / dashscope 提供兼容端点），
因此统一使用 langchain_openai.ChatOpenAI，仅切换 base_url 与 model。
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core import SystemException, get_logger, settings
from app.enums.response_code import ResponseCode

logger = get_logger("llm")

# provider -> 默认接入地址与默认模型
# custom 表示完全由环境变量指定 base_url / model，无内置默认值
PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "custom": {"base_url": "", "model": ""},
}


def _resolve_provider_config(provider: str) -> dict[str, str]:
    """解析 provider 对应的接入地址与模型名：环境变量优先，其次 provider 默认值。

    :param provider: 模型提供方标识（openai / deepseek / dashscope / custom）
    :return: 含 base_url 与 model 的配置字典
    """
    defaults = PROVIDER_DEFAULTS.get(provider)
    if defaults is None:
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message=f"不支持的大模型提供方：{provider}",
            detail=f"可选值：{', '.join(PROVIDER_DEFAULTS)}",
        )

    base_url = settings.LLM_BASE_URL.strip() or defaults["base_url"]
    model = settings.LLM_MODEL.strip() or defaults["model"]
    if not base_url or not model:
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="大模型服务未配置完整",
            detail="custom provider 必须配置 LLM_BASE_URL 与 LLM_MODEL",
        )
    return {"base_url": base_url, "model": model}


@lru_cache(maxsize=8)
def _build_llm(
    provider: str,
    base_url: str,
    model: str,
    api_key: str,
    temperature: float,
    streaming: bool,
) -> ChatOpenAI:
    """按参数构造并缓存 ChatOpenAI 实例（参数全部可哈希，便于 lru_cache）。"""
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT,
        streaming=streaming,
    )


def get_llm(
    provider: str | None = None,
    *,
    streaming: bool = True,
    temperature: float | None = None,
    model: str | None = None,
) -> ChatOpenAI:
    """获取模型实例：provider -> 模型实例的唯一入口。

    :param provider: 模型提供方，缺省读取配置 LLM_PROVIDER
    :param streaming: 是否启用流式输出（SSE 场景为 True，一次性生成为 False）
    :param temperature: 采样温度，缺省读取配置 LLM_TEMPERATURE
    :param model: 模型名称，缺省读取配置 LLM_MODEL 或 provider 默认模型
    :return: LangChain ChatOpenAI 模型实例
    """
    provider_name = (provider or settings.LLM_PROVIDER).strip().lower()
    api_key = settings.LLM_API_KEY.strip()
    if not api_key:
        # 配置缺失属于系统级问题，提示管理员补齐环境变量，不向前端暴露内部细节
        raise SystemException(
            code=ResponseCode.SYSTEM_ERROR,
            message="大模型服务未配置，请联系管理员",
            detail="环境变量 LLM_API_KEY 为空",
        )

    provider_config = _resolve_provider_config(provider_name)
    resolved_temperature = (
        settings.LLM_TEMPERATURE if temperature is None else temperature
    )
    resolved_model = model.strip() if model else provider_config["model"]

    logger.info(
        "获取模型实例 provider={} model={} streaming={}",
        provider_name,
        resolved_model,
        streaming,
    )
    return _build_llm(
        provider_name,
        provider_config["base_url"],
        resolved_model,
        api_key,
        resolved_temperature,
        streaming,
    )
