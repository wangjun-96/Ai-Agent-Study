"""通用分页工具：封装分页参数解析与分页结果结构，所有列表查询统一复用。

- PageParams：FastAPI 依赖，从 query 解析 page / page_size，限制最大值防止拖垮数据库；
- PageResult：通用分页响应结构（items / total / page / page_size），业务层直接返回。
"""
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

# 分页参数上下限：防止前端传入超大 page_size 导致全表扫描
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PageParams:
    """分页参数依赖：通过 Query 解析 page 与 page_size。

    用法::

        def list_items(page: PageParams = Depends()):
            ...
    """

    def __init__(
        self,
        page: int = Query(DEFAULT_PAGE, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(
            DEFAULT_PAGE_SIZE,
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"每页条数，最大 {MAX_PAGE_SIZE}",
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """SQL offset：(page - 1) * page_size。"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL limit：等于 page_size。"""
        return self.page_size


class PageResult(BaseModel, Generic[T]):
    """通用分页响应体。"""

    items: list[T] = Field(..., description="当前页数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
