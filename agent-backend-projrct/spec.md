# 后端改造规格说明书（prompt.md 剩余任务）

## 1. 背景与范围

`prompt.md` 中第 194 行至文末要求依次完成：RAG 入库/OCR/切片/双存储/检索/对话链路、短期/工作/长期记忆、LangGraph 学习测评工作流（interrupt + checkpoint + 动态提示词 + 消息持久化）、流程总控路由、A2A 消息信封。

已完成：三层流式聊天、提示词版本管理、用户画像与变量注入（任务 1-3）。
本规格覆盖剩余全部任务，保持现有分层（routers/v1 → services → dao → db/models），不破坏既有接口。

## 2. 关键技术决策

1. **Qdrant 运行模式**：新增 `QDRANT_HOST/QDRANT_PORT/QDRANT_LOCAL_PATH`。`QDRANT_LOCAL_PATH` 非空时使用 qdrant-client 本地文件模式（无需部署 Qdrant 服务），否则连接远端 host/port。开发环境默认启用本地模式 `.qdrant_data`。
2. **向量化**：DashScope SDK `text-embedding-v4`，维度 1024，批大小 10，按 `text_index` 排序对齐。`DASHSCOPE_API_KEY` 为空时入库接口抛出明确业务错误；对话检索失败只记日志并跳过检索，不影响聊天主流程。
3. **扫描版 PDF OCR**：pypdfium2 抽取文字，平均每页字符数 < 20 判定扫描件；`ocr_pdf` 按 150 DPI 渲染 PNG → base64 → volcengine `VisualService.ocr_normal` → `data.line_texts` 按行拼接。火山凭证缺失时抛出明确系统错误。
4. **切片双存储**：Qdrant point payload 只存 `user_id/doc_category/file_name/chunk_index/resource_id`；原文写 MySQL `knowledge_chunks`，两侧以 `vector_id`（UUID）关联。
5. **语义意图判断**：fastembed `BAAI/bge-small-zh-v1.5` 单例，懒加载 + 余弦相似度；模型下载/推理失败时降级为关键词匹配并记录告警。供长期记忆 `should_write` 与总控 `classify_intent` 复用。
6. **工作流状态**：`run_id` 同时作为 `workflow_runs.run_id` 与 LangGraph `thread_id`；`WorkflowRun` 只存业务快照，LangGraph 现场由 `MemorySaver` checkpoint 保存。
7. **路由文件位置**：项目无 `app/routes/`，总控接口按现有结构落在 `app/routers/v1/orchestrator.py`，服务与 Schema 文件名仍按 prompt.md 命名。

## 3. 文件级改动清单

### 3.1 配置与依赖

- `requirements.txt`：追加 `qdrant-client`、`dashscope`、`pypdfium2`、`python-docx`、`volcengine`、`pillow`、`fastembed`。
- `app/core/config.py` 新增：
  - RAG：`DASHSCOPE_API_KEY`、`QDRANT_HOST`、`QDRANT_PORT`、`QDRANT_LOCAL_PATH`、`QDRANT_COLLECTION="knowledge_chunks"`、`RAG_EMBEDDING_MODEL="text-embedding-v4"`、`RAG_EMBEDDING_DIM=1024`、`RAG_TOP_K=3`、`RAG_SCORE_THRESHOLD=0.4`、`RAG_CHUNK_SIZE=500`、`RAG_CHUNK_OVERLAP=50`、`RAG_CHUNK_TEXT_MAX=800`
  - OCR：`VOLC_ACCESS_KEY`、`VOLC_SECRET_KEY`、`VOLC_REGION="cn-north-1"`
  - 记忆：`WORKING_MEMORY_TTL_SECONDS=28800`、`WORKING_MEMORY_MAX_CHARS=8000`、`WORKING_MEMORY_KEEP_MESSAGES=6`、`SUMMARY_MAX_CHARS=500`、`LONG_TERM_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"`、`LONG_TERM_SIMILARITY_THRESHOLD=0.62`
- `.env.development` 追加上述配置（密钥留空占位），`QDRANT_LOCAL_PATH=".qdrant_data"`。

### 3.2 RAG 模块（任务 4-9）

- 新建 `app/rag/__init__.py`。
- 新建 `app/rag/qdrant_utils.py`：
  - `get_qdrant_client()`：lru_cache；本地/远端模式；初始化失败不缓存异常。
  - `ensure_collection(client)`：不存在则按 Cosine + 1024 维创建。
  - `embed_texts(texts) -> list[list[float]]`：DashScope 每批 10 条，按 `text_index` 对齐；key 缺失抛 `SystemException`。
  - `search_vectors(query_vector, user_id, top_k)`：`query_points` + `user_id` 过滤。
- 新建 `app/rag/core.py`（对外只暴露 `ingest_file`）：
  - `ingest_file(path, *, user_id, file_name, resource_id, doc_category=None) -> list[IngestedChunk]`
  - 内部：`_parse_file`（PDF/DOCX/TXT 字典分派，未知类型抛业务异常）、`_parse_pdf`（pypdfium2 + 扫描判定 + ocr 兜底）、`_parse_docx`（Heading 1/2/3 注入 `#/##/###`）、`_clean_text`、`_classify_document`、`_split_text`（RecursiveCharacterTextSplitter，分隔符 `\n###,\n##,\n#, \n\n,\n,。！？；，,空格,字符兜底`，MD5 去重）、`_write_qdrant`（uuid4 point id，payload 不含原文）。
  - `IngestedChunk` 数据类：`vector_id/text/chunk_index/char_count`。
- 新建 `app/rag/ocr.py`：仅暴露 `ocr_pdf(path) -> str`。
- 新建 `app/rag/chunk_store.py`：
  - `save_chunks(db, *, resource_id, user_id, chunks) -> int`：`add_all + flush`，不 commit（由 Service 统一提交）。
  - `fetch_chunks_by_vector_ids(db, vector_ids) -> dict[str, KnowledgeChunk]`。
  - `fetch_sources_by_reference(db, references) -> list[dict]`：关联 resources 回查，缺失 chunk 返回 `text="该参考片段已被删除"`。
- 新建 `app/rag/retriever.py`：仅暴露 `search_similar_chunks(query, user_id, db, top_k=3)`；分数 < 0.4 丢弃，text 超 800 字截断；返回 `chunk_id/resource_id/chunk_index/file_name/score/text`。
- 新建 `app/rag/chat_rag.py`：`should_retrieve`、`format_retrieved_chunks`、`build_rag_system_prompt`。
- 新建 `app/services/rag_service.py`：`ingest_resource(resource_id, user_id, db)` 下载 MinIO 对象到临时文件 → `ingest_file` → `save_chunks` → `db.commit()`。
- 新建 `app/routers/v1/rag.py`：`POST /rag/resources/{resource_id}/ingest`（JWT），返回切片数；注册到 `api.py`。
- 修改 `app/integrations/minio_client.py`：新增 `get_object_bytes(object_key, bucket)`。
- 数据模型：`app/db/models.py` 新增 `KnowledgeChunk`（id、resource_id FK+索引、user_id 索引、vector_id 唯一、text、chunk_index、char_count、create_at）。
- 迁移：`alembic/versions/2026_10_30_1000-c9d0e1f2a3b4_add_knowledge_chunks.py`（down_revision=`b8c9d0e1f2a3`）。
- 对话链路：
  - `ChatMessage` 新增 `reference_sources JSON`（存 `[{chunk_id, score}]`）。
  - `stream_chat_service`：意图判断 → 检索 → 拼接 `rag_context` 到本轮问题前 → RAG 规则追加系统提示词；`done` 事件返回完整 `sources`；落库写 `reference_sources`。
  - `MessageResponse` 新增 `sources` 与 `response_payload`；`message_service` 按 `reference_sources` 回查 `knowledge_chunks + resources`。
  - `MessageDao` 新增 `get_by_request_id`、`update_response`（供工作流复用）。

### 3.3 记忆模块（任务 10-12）

- 新建 `app/services/memory_service.py`：
  - `build_chat_history_from_rows(rows) -> list[BaseMessage]`
  - `InstantMemory(message_dao).load(session_id)`：最近 8 轮 → `_fit_char_budget` → 格式化。
  - `WorkingMemory(cache)`：`get(user_id, session_id)`、`append_turn(user_id, session_id, request_text, response_text)`；Key `memory:working:{user_id}:{session_id}`，TTL 8 小时，读写续期；超 8000 字保留最近 6 条并调用 `quick_summarize`。
  - `quick_summarize(llm, messages, old_summary) -> str`，摘要 ≤ 500 字。
  - `MemoryService(message_dao, cache, profile_dao)`：`load_context(session_id, user_id, enable_long_term=True)`（Redis 优先、MySQL 兜底、画像 SystemMessage 前置）、`append_turn(...)`。
- 修改 `app/integrations/redis_client.py`：新增 `expire(key, seconds)`。
- 新建 `app/services/semantic_intent_service.py`：`SemanticIntentClassifier.get()`、`similarity(text, examples)`、`warmup()`；fastembed 懒加载，异常降级关键词。
- 新建 `app/services/long_term_memory.py`：`load_memory_context(user_id, db)`、`should_write(text)`、`submit_profile_update_async(user_id, request_text, context)`（后台线程 + `SessionLocal` + LLM JSON 抽取）。
- `UserProfile` 新增 `learning_goal`、`learning_style`、`interview_focus JSON`、`long_term_summary LargeText`；`user_profile_service` 的字段白名单与 `get_profile_dict` 同步扩展。
- 迁移：`2026_10_30_1100-d0e1f2a3b4c5_add_long_term_memory.py`。
- `app/llm/prompt_layer.py`：新增 `merge_system_messages(history, system_prompt) -> (history, prompt)`。
- `stream_chat_service`：`MemoryService.load_context` 替代 `ChatMemory`；命中画像写入意图时跳过 RAG；流结束后 `append_turn` 并提交 `submit_profile_update_async`（上下文=最近 4 条历史+本轮回复）。

### 3.4 学习测评工作流（任务 13-16）

- `app/db/models.py` 新增 `WorkflowRun`：`id/run_id(unique)/user_id/session_id/workflow_type/status/state_json JSON/error_message/created_at/updated_at/completed_at`。
- 迁移：`2026_10_30_1200-e1f2a3b4c5d6_add_workflow_runs.py`。
- 新建 `app/dao/workflow_run_dao.py`：insert/get_by_run_id/update_status/update_state。
- 新建 `app/agent/workflows/checkpoint.py`：`get_workflow_checkpointer()` 全局 `MemorySaver`、`build_thread_config(thread_id)`。
- 新建 `app/agent/workflows/state.py`：`LearningWorkflowState`（run_id/user_id/session_id/request_text/provider/question_count/quiz/answers/evaluation/score/weaknesses/review/status/a2a_envelope）。
- 新建 `app/agent/workflows/learning.py`：图 `generate_quiz → wait_user_answer → evaluate_answer → finalize_result → END`；`wait_user_answer` 使用 `interrupt({"quiz": quiz})`；`create_evaluate_and_review_node` 生成 A2A 信封（薄弱点 → `difficulty_learner`，confidence 0.9；否则 None，0.4）。
- 新建 `app/utils/__init__.py`、`app/utils/json_utils.py`：`parse_json_object(text)` 容错解析模型 JSON（剥离 ```json 围栏、提取首尾大括号）。
- 新建 `app/services/learning_workflow_service.py`：`start()`、`submit_answer()`、`get_run()`；`generate_quiz` 动态提示词 `quiz_generate_workflow`，`evaluate_answer` 动态提示词 `learning_evaluator`；出题后写一条 `chat_messages`（`request_id="{run_id}:quiz"`、`response_text="已完成出题，请完成后提交答案。"`、`response_payload=quiz`）；提交后更新同一条消息为点评文本、`response_payload=None`。
- 新建 `app/schemas/learning_workflow.py`、`app/routers/v1/learning_workflows.py`：`POST /learning-workflows/start`、`POST /learning-workflows/{run_id}/submit`、`GET /learning-workflows/{run_id}`，注册到 `api.py`。

### 3.5 总控路由与 A2A（任务 17-18）

- 新建 `app/schemas/orchestrator_schemas.py`：`AgentTaskStartRequest/Response`。
- 新建 `app/services/orchestrator_service.py`：`WorkflowRouteRule`、`WORKFLOW_ROUTE_RULES`（`quiz_generate_workflow → learning_quiz`，关键词“题、出题、刷题、练习、测验、测评、小测、面试题”）、`route()`、`start_task()`。
- 新建 `app/routers/v1/orchestrator.py`：`POST /agent/tasks/start`；命中工作流返回 JSON，聊天分支返回 `StreamingResponse`（复用 `StreamChatService.stream_chat()`）。
- `main.py` lifespan 后台线程调用 `SemanticIntentClassifier.get().warmup()`。
- 新建 `app/agent/a2a/envelope.py`、`app/agent/a2a/__init__.py`；按 prompt.md 字段与业务规则实现 `A2AEnvelope`。

## 4. 验证方案

1. `python -m compileall app` 与 `.venv\Scripts\python.exe -c "import app.main"` 导入通过。
2. `alembic upgrade head` 成功，检查 `knowledge_chunks/user_profiles/workflow_runs/chat_messages.reference_sources/response_payload` 列。
3. 运行 `pytest tests/test_smoke.py -v` 现有冒烟用例不回归。
4. 定向冒烟脚本：
   - 分类/清洗/切片函数单测（TXT 文本，不依赖外部 API）。
   - `should_retrieve` 对空输入/确认语返回 False、对资料型问题返回 True。
   - LangGraph 图构建与 `interrupt` 暂停（Mock LLM 返回固定 JSON），校验 run 状态流转。
   - `A2AEnvelope` 字段校验、信封业务规则。
5. Qdrant/OCR/DashScope/火山真实调用需在用户配置密钥后验证（本规格保证未配置时错误可读、聊天不中断）。

## 5. 验收与风险

- 验收：prompt.md 第 194 行后每条要求均有对应实现；原有接口语义不变；删除仍为逻辑/级联规则不变。
- 风险与降级：Qdrant 不可用 → 入库报错、检索跳过；DashScope/火山/Embedding 密钥缺失 → 对应能力报明确错误；fastembed 下载失败 → 关键词降级；Redis 故障 → 记忆回退 MySQL。
