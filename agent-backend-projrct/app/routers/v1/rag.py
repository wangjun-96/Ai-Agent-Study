"""路由层：知识库入库接口。

把已上传到 MinIO 的文档资源解析、切片、向量化，写入 Qdrant 与 MySQL。
接口统一挂载 JWT 登录鉴权，用户只能操作自己的资源。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import success
from app.core.responses import ApiResponse
from app.db.database import get_db
from app.db.models import User
from app.routers.v1.deps import get_current_user, get_rag_service
from app.services.rag_service import RagService

router = APIRouter(
    prefix="/rag",
    tags=["知识库"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"model": ApiResponse, "description": "未授权：缺失/过期/伪造访问令牌(40104)"},
    },
)


@router.post(
    "/resources/{resource_id}/ingest",
    summary="文档资源入库知识库",
    description=(
        "解析 PDF/DOCX/TXT 文档并递归切片，向量化写入 Qdrant，"
        "切片原文写入 MySQL；扫描版 PDF 自动走 OCR。"
    ),
    response_model=ApiResponse[dict],
)
def ingest_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: RagService = Depends(get_rag_service),
) -> dict:
    """把当前用户的上传资源入库为知识切片。"""
    result = service.ingest_resource(resource_id, int(current_user.id), db)
    return success(result, "知识库入库成功")
