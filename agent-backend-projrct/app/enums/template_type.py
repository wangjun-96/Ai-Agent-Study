"""提示词模板类型枚举：区分公共模板与私有模板，禁止硬编码数字。"""
from enum import IntEnum


class TemplateType(IntEnum):
    """模板类型，写入 prompt_templates.template_type 字段。"""

    PRIVATE = 1  # 私有模板：绑定具体智能体（agent_name 非空）
    PUBLIC = 2   # 公共模板：所有智能体共享（agent_name 为空）
