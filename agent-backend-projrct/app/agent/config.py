"""智能体配置：7 个智能体映射（名称 / 中文标签 / 默认场景 / 职责说明）。

- 每个智能体对应一组私有提示词模板（agent_name + scene）；
- 同一 scene 下可存在一份公共模板（agent_name 为空），与私有模板拼成完整提示词；
- 提示词版本管理、路由配置均以此为唯一数据源，禁止在业务代码中散落硬编码。
"""
from typing import TypedDict


class AgentConfigItem(TypedDict):
    """单个智能体的配置结构。"""

    label: str        # 中文标签，前端下拉、Swagger 描述使用
    scene: str        # 默认业务场景，用于定位提示词模板
    description: str  # 职责说明


# 智能体名称 -> 配置：新增智能体只需在此追加一条映射
AGENT_CONFIG: dict[str, AgentConfigItem] = {
    "study_coach": {
        "label": "学习辅导",
        "scene": "study",
        "description": "学习室通用问答智能体，负责知识讲解与学习答疑",
    },
    "interview_coach": {
        "label": "面试辅导",
        "scene": "interview",
        "description": "面试间智能体，负责模拟面试提问与追问",
    },
    "note_assistant": {
        "label": "笔记助手",
        "scene": "note",
        "description": "笔记本智能体，负责整理、总结与结构化笔记内容",
    },
    "resume_coach": {
        "label": "简历优化",
        "scene": "resume",
        "description": "简历优化智能体，负责简历诊断与改写建议",
    },
    "quiz_generate_workflow": {
        "label": "学习测题生成",
        "scene": "quiz_generate",
        "description": "学习测评工作流出题智能体，输出结构化题目 JSON",
    },
    "learning_evaluator": {
        "label": "学习评测",
        "scene": "learning_evaluate",
        "description": "学习测评工作流评分智能体，负责评分、点评与薄弱点提取",
    },
    "difficulty_learner": {
        "label": "薄弱点专项提升",
        "scene": "difficulty_learning",
        "description": "针对薄弱点生成专项练习的智能体",
    },
}


def get_agent_config(agent_name: str) -> AgentConfigItem | None:
    """按智能体名称获取配置，不存在返回 None。"""
    return AGENT_CONFIG.get(agent_name)


def get_agent_scene(agent_name: str) -> str | None:
    """获取智能体默认场景，不存在返回 None。"""
    config = AGENT_CONFIG.get(agent_name)
    return config["scene"] if config else None
