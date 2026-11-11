"""校验层：提示词模板管理与智能体配置的请求/响应模型。"""
from pydantic import BaseModel, Field

from app.enums.template_type import TemplateType


class PromptTemplateItem(BaseModel):
    """单个提示词模板版本信息。"""

    id: int = Field(..., description="模板ID")
    agent_name: str | None = Field(None, description="智能体名称（公共模板为空）")
    scene: str = Field(..., description="业务场景")
    template_type: TemplateType = Field(..., description="模板类型：1=私有，2=公共")
    template_content: str = Field(..., description="模板正文")
    variables: list[str] = Field(default_factory=list, description="变量名列表")
    version: int = Field(..., description="版本号")
    is_active: int = Field(..., description="是否生效版本：0=否，1=是")
    description: str | None = Field(None, description="版本说明")
    created_at: int = Field(..., description="创建时间（Unix秒）")


class PromptTemplateDetail(BaseModel):
    """指定智能体/场景下的模板详情：公共模板 + 私有模板 + 拼接结果。"""

    agent_name: str = Field(..., description="智能体名称")
    scene: str = Field(..., description="业务场景")
    public_template: PromptTemplateItem | None = Field(
        None, description="生效的公共模板"
    )
    private_template: PromptTemplateItem | None = Field(
        None, description="生效的私有模板"
    )
    full_prompt: str = Field("", description="公共模板 + 私有模板拼接后的完整提示词")


class PromptRollbackRequest(BaseModel):
    """一键回滚请求：指定要重新生效的历史版本。"""

    template_id: int = Field(..., gt=0, description="模板ID（历史版本）")


class AgentConfigItemResponse(BaseModel):
    """智能体配置项。"""

    agent_name: str = Field(..., description="智能体名称")
    label: str = Field(..., description="中文标签")
    scene: str = Field(..., description="默认业务场景")
    description: str = Field(..., description="职责说明")
