# 实施任务清单（依据 spec.md）

> 执行顺序自上而下；每项完成后勾选，并在最终汇报中说明关键实现与验证结果。

## A. 配置与依赖
- [x] A1 `requirements.txt` 追加 qdrant-client / dashscope / pypdfium2 / python-docx / volcengine / pillow / fastembed
- [x] A2 `app/core/config.py` 新增 RAG、OCR、记忆相关配置项
- [x] A3 `.env.development` 补充配置（密钥留空、Qdrant 本地路径）

## B. RAG 入库（任务 4-7）
- [x] B1 新建 `app/rag/qdrant_utils.py`（客户端、建集合、DashScope 批量向量化、检索封装）
- [x] B2 新建 `app/rag/ocr.py`（pypdfium2 150DPI + 火山 OCRNormal）
- [x] B3 新建 `app/rag/core.py`（解析/清洗/分类/递归切片/DOCX 标题/Qdrant 写入，只暴露 ingest_file）
- [x] B4 `KnowledgeChunk` 模型 + `chunk_store.py`（save_chunks / fetch_chunks_by_vector_ids / fetch_sources_by_reference）
- [x] B5 迁移 `add_knowledge_chunks`（down_revision=b8c9d0e1f2a3）
- [x] B6 `app/services/rag_service.py` + `app/routers/v1/rag.py`（资源入库接口）
- [x] B7 `minio_client.py` 新增 `get_object_bytes`

## C. RAG 检索与对话（任务 8-9）
- [x] C1 新建 `app/rag/retriever.py`（user_id 过滤、0.4 阈值、800 字截断）
- [x] C2 新建 `app/rag/chat_rag.py`（should_retrieve / format_retrieved_chunks / build_rag_system_prompt）
- [x] C3 `ChatMessage` 新增 `reference_sources` JSON + 迁移
- [x] C4 `StreamChatService` 接入检索、RAG 上下文、sources、reference_sources 落库
- [x] C5 `MessageResponse` + `MessageService` 历史消息回查回显 sources

## D. 记忆层（任务 10-12）
- [x] D1 `redis_client.py` 新增 `expire(key, seconds)`
- [x] D2 新建 `app/services/memory_service.py`（InstantMemory / WorkingMemory / MemoryService / quick_summarize）
- [x] D3 新建 `app/services/semantic_intent_service.py`（fastembed 单例 + warmup + 降级）
- [x] D4 `UserProfile` 扩展 4 字段 + `user_profile_service` 同步 + 迁移
- [x] D5 新建 `app/services/long_term_memory.py`（load_memory_context / should_write / submit_profile_update_async）
- [x] D6 `prompt_layer.py` 新增 `merge_system_messages`
- [x] D7 `StreamChatService` 改用 `MemoryService`，接入长期记忆意图判断、异步画像更新

## E. 学习测评工作流（任务 13-16）
- [x] E1 `WorkflowRun` 模型 + 迁移 + `workflow_run_dao.py`
- [x] E2 `app/agent/workflows/checkpoint.py`（MemorySaver / build_thread_config）
- [x] E3 `app/agent/workflows/state.py`（LearningWorkflowState）
- [x] E4 `app/agent/workflows/learning.py`（interrupt 图 + 动态提示词 + 评分 JSON）
- [x] E5 `app/utils/json_utils.py`（parse_json_object）
- [x] E6 `app/services/learning_workflow_service.py`（start/submit_answer/get_run + 消息持久化）
- [x] E7 `app/schemas/learning_workflow.py` + `app/routers/v1/learning_workflows.py` + 注册路由
- [x] E8 `MessageDao` 新增 `get_by_request_id` / `update_response`

## F. 总控路由与 A2A（任务 17-18）
- [x] F1 `app/schemas/orchestrator_schemas.py`
- [x] F2 `app/services/orchestrator_service.py`（WORKFLOW_ROUTE_RULES / route / start_task）
- [x] F3 `app/routers/v1/orchestrator.py` + 注册路由
- [x] F4 `main.py` lifespan 后台预热语义模型
- [x] F5 `app/agent/a2a/envelope.py` + `__init__.py`
- [x] F6 `StreamChatService.stream_chat()` 供总控聊天分支复用

## G. 验证
- [x] G1 `python -m compileall app` + `import app.main` 通过
- [x] G2 `alembic upgrade head` 成功，核对新增表/字段
- [x] G3 `pytest tests/test_smoke.py -v` 无回归
- [x] G4 定向冒烟：切片/清洗、should_retrieve、工作流 interrupt、A2A 信封
