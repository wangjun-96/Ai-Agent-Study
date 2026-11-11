"""业务层：提示词变量注入（三层处理流程）。

设计思想（见 prompt.md「提示词变量注入设计思想」）：
- 公共模板（通用规则）+ 私有模板（Agent 指令）+ 动态注入用户信息变量 = 完整提示词；
- 注入按三层依次处理：
  1. 验证层：安全检查（防提示词注入、去除零宽字符、长度限制）；
  2. 转换层：数据格式化（数组转文本、空值补默认值）；
  3. 填充层：占位符替换（{target_job} -> 实际值）。

本模块不直接查询数据库：画像数据由 UserProfileService 提供，模板由 PromptTemplateManager 提供。
"""
import re

from app.core import get_logger, settings
from app.dao.user_profile_dao import UserProfileDao
from app.services.prompt_template_service import PromptTemplateManager
from app.services.user_profile_service import UserProfileService

logger = get_logger("prompt_variable_service")

# 变量默认值：用户未填写时使用，避免提示词出现空占位符
DEFAULT_VALUES: dict[str, str] = {
    "target_job": "未指定",
    "years_experience": "未提供",
    "target_level": "未指定",
    "target_skills": "暂无记录",
    "weak_topics": "暂无记录",
    "learning_goal": "未指定",
    "learning_style": "未指定",
    "interview_focus": "暂无记录",
}

# 常见提示词注入特征：命中后直接移除，避免用户输入篡改系统指令
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"忽略(以上|之前|上面|前面)(的)?(所有)?(指令|提示|规则)"),
    re.compile(r"<\s*\|?\s*(im_start|im_end|system)\s*\|?\s*>", re.IGNORECASE),
    re.compile(r"(system|assistant)\s*[:：]", re.IGNORECASE),
    re.compile(r"developer\s+mode", re.IGNORECASE),
)

# 占位符：只匹配 {字母或下划线开头} 的变量名，不干扰正文中的普通大括号
PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# 零宽字符与控制字符
INVISIBLE_PATTERN = re.compile(r"[\u200b-\u200f\ufeff\x00-\x1f\x7f]")


class PromptVariableService:
    """提示词变量注入服务：验证 -> 转换 -> 填充。"""

    def __init__(self, profile_dao: UserProfileDao) -> None:
        self.profile_service = UserProfileService(profile_dao)

    # ------------------------------ 验证层 ------------------------------

    def validate(self, value) -> str:
        """验证层：清洗变量值并做长度限制。

        处理内容：去除零宽/控制字符、移除提示词注入特征、按配置截断超长内容。

        :param value: 原始变量值（字符串/列表/数字等）
        :return: 清洗后的字符串
        """
        text = "" if value is None else str(value)
        text = INVISIBLE_PATTERN.sub("", text)
        for pattern in INJECTION_PATTERNS:
            text = pattern.sub("", text)
        text = text.strip()
        if len(text) > settings.PROMPT_VAR_MAX_LENGTH:
            text = text[: settings.PROMPT_VAR_MAX_LENGTH]
        return text

    # ------------------------------ 转换层 ------------------------------

    def transform(self, raw: dict) -> dict[str, str]:
        """转换层：格式化画像数据为可直接填充的字符串变量。

        - 数组 -> 中文顿号拼接；
        - 空值 / 空列表 -> 默认值；
        - 单值统一转字符串并做验证层清洗；
        - 变量总长度受 PROMPT_VARS_TOTAL_MAX_LENGTH 约束。

        :param raw: 画像原始字典（UserProfileService.get_profile_dict 的输出）
        :return: 变量名 -> 字符串值
        """
        variables: dict[str, str] = {}
        for key in DEFAULT_VALUES:
            value = raw.get(key)
            if isinstance(value, (list, tuple, set)):
                parts = [self.validate(item) for item in value]
                parts = [part for part in parts if part]
                variables[key] = "、".join(parts) if parts else DEFAULT_VALUES[key]
            else:
                cleaned = self.validate(value)
                variables[key] = cleaned or DEFAULT_VALUES[key]

        # 总量控制：超出预算时按顺序截断，保证提示词长度可控
        total = sum(len(value) for value in variables.values())
        if total > settings.PROMPT_VARS_TOTAL_MAX_LENGTH:
            logger.warning(
                "提示词变量总长度超限 total={} budget={}",
                total,
                settings.PROMPT_VARS_TOTAL_MAX_LENGTH,
            )
            budget = settings.PROMPT_VARS_TOTAL_MAX_LENGTH
            for key in list(variables):
                if budget <= 0:
                    variables[key] = ""
                    continue
                variables[key] = variables[key][:budget]
                budget -= len(variables[key])
        return variables

    # ------------------------------ 填充层 ------------------------------

    def fill(self, template: str, variables: dict[str, str]) -> str:
        """填充层：按占位符替换变量值。

        - 已知变量：替换为注入值；
        - 已知默认变量但未提供：替换为默认值；
        - 未定义的占位符保持原样，避免误删模板中的业务内容。

        :param template: 模板正文
        :param variables: 变量字典
        :return: 替换后的提示词
        """

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name in variables:
                return variables[name]
            if name in DEFAULT_VALUES:
                return DEFAULT_VALUES[name]
            return match.group(0)

        return PLACEHOLDER_PATTERN.sub(_replace, template)

    # ------------------------------ 对外入口 ------------------------------

    def build_variables(self, user_id: int) -> dict[str, str]:
        """构建用户变量：读取画像并完成验证 + 转换两层处理。"""
        raw = self.profile_service.get_profile_dict(user_id)
        return self.transform(raw)

    def build_system_prompt(
        self,
        manager: PromptTemplateManager,
        agent_name: str,
        user_id: int,
    ) -> str:
        """构建最终系统提示词：公共 + 私有模板 + 用户变量注入。

        :param manager: 提示词模板管理器
        :param agent_name: 智能体名称
        :param user_id: 用户ID
        :return: 注入后的系统提示词；模板缺失时返回空串（调用方使用默认提示词）
        """
        template = manager.get_full_prompt(agent_name)
        if not template:
            logger.info("智能体未配置提示词模板，使用默认提示词 agent={}", agent_name)
            return ""
        variables = self.build_variables(user_id)
        system_prompt = self.fill(template, variables)
        logger.info(
            "提示词变量注入完成 agent={} user_id={} vars={} chars={}",
            agent_name,
            user_id,
            list(variables),
            len(system_prompt),
        )
        return system_prompt
