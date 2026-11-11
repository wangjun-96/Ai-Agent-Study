"""LangGraph 工作流 checkpoint 配置。

checkpoint 只保存 LangGraph 执行现场（节点中间态与线程级记忆），
业务快照统一存 workflow_runs 表，便于查询、审计与断点恢复。
"""
from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import MemorySaver


@lru_cache(maxsize=1)
def get_workflow_checkpointer() -> MemorySaver:
    """获取全局唯一的进程内 MemorySaver 实例。

    通过 lru_cache 保证整个进程共享同一份 checkpoint 存储，
    避免重复创建导致同一 thread_id 的执行现场丢失。
    """
    return MemorySaver()


def build_thread_config(thread_id: str) -> dict[str, Any]:
    """按 thread_id 构造 LangGraph 运行配置（thread_id 即 workflow run_id）。"""
    return {"configurable": {"thread_id": thread_id}}
