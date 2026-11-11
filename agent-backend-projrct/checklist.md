# 验收清单（对照 spec.md）

> 以下检查项均已逐条核对代码与运行结果，通过即勾选。

## 一、配置与依赖
- [x] RAG / OCR / 记忆配置项全部进入 `app/core/config.py`，`.env.development` 同步提供占位配置
- [x] `requirements.txt` 包含 qdrant-client、dashscope、pypdfium2、python-docx、volcengine、pillow、fastembed、langchain-text-splitters、langgraph

## 二、RAG 入库（任务 4-7）
- [x] `app/rag/core.py` 对外只暴露 `ingest_file`，内部完成解析 → 清洗 → 分类 → 切片 → 向量化 → 写 Qdrant
- [x] PDF 由 pypdfium2 抽文字，平均每页字符数 < 20 自动走 `ocr_pdf`（火山 OCRNormal，150 DPI）
- [x] DOCX 识别 Heading 1/2/3 并注入 `#/##/###`；递归切片分隔符按 `\n###` 到字符兜底排序；MD5 去重
- [x] Qdrant payload 只含 `user_id/doc_category/file_name/chunk_index/resource_id`，不存原文
- [x] 切片原文写入 `knowledge_chunks`，与 Qdrant 以 `vector_id` 对齐；`resource_id` 类型与 `resources.id`（BIGINT）一致
- [x] `POST /api/v1/rag/resources/{resource_id}/ingest` 完成归属校验、MinIO 下载、入库与事务提交

## 三、RAG 检索与对话（任务 8-9）
- [x] `search_similar_chunks` 按 `user_id` 过滤，低于 `RAG_SCORE_THRESHOLD=0.4` 丢弃，超 800 字截断
- [x] `should_retrieve` 对空输入、确认语、推进语返回 False；资料型问题返回 True
- [x] 流式对话命中资料时注入 RAG 规则与参考资料，`done` 事件返回完整 `sources`
- [x] 落库写 `reference_sources`（仅 chunk_id/score）；历史消息接口回查切片与文件名并返回 `sources`

## 四、记忆层（任务 10-12）
- [x] 工作记忆 Key `memory:working:{user_id}:{session_id}`，TTL 8 小时，超 8000 字保留最近 6 条并摘要（≤500 字）
- [x] Redis 不可用时回退 MySQL 即时记忆，并触发上下文裁剪
- [x] 长期画像以 SystemMessage 前置注入，`prompt_layer.merge_system_messages` 合并进 system_prompt
- [x] 长期记忆写入意图判断（语义 + 关键词降级），命中时跳过 RAG；流结束后后台线程异步抽取画像
- [x] 画像抽取未注册智能体时回退默认提示词，不再抛「未知智能体」异常

## 五、学习测评工作流（任务 13-16）
- [x] `workflow_runs` 表字段完整（run_id/user_id/session_id/workflow_type/status/state_json/error_message/时间戳）
- [x] `run_id` 同时作为 LangGraph `thread_id`，checkpoint 用全局 MemorySaver 保存执行现场
- [x] 图结构 `prepare_learning_context → generate_quiz → wait_user_answer → evaluate_answer → finalize_result → END`
- [x] `wait_user_answer` 通过 `interrupt({"quiz": quiz})` 暂停，`Command(resume=answers)` 恢复并继续评分
- [x] 出题/评分分别使用 `quiz_generate_workflow` / `learning_evaluator` 动态提示词
- [x] 出题写一条 `request_id="{run_id}:quiz"` 的刷题消息（`response_payload=quiz`），提交后回写点评文本并清空 `response_payload`
- [x] `POST /learning-workflows/start`、`POST /{run_id}/submit`、`GET /{run_id}` 三个接口可用且 JWT 鉴权

## 六、流程总控与 A2A（任务 17-18）
- [x] `POST /agent/tasks/start` 先校验 `agent_name`，再关键词快筛，未命中走语义兜底，仍未命中走通用聊天
- [x] `WORKFLOW_ROUTE_RULES` 覆盖 `quiz_generate_workflow → learning_quiz` 与出题关键词
- [x] 工作流分支返回 JSON，聊天分支复用 `StreamChatService.stream_chat()` 返回 SSE
- [x] `main.py` lifespan 后台线程预热语义模型，失败只告警不阻塞启动
- [x] `A2AEnvelope` 字段与业务规则：有薄弱点 → `difficulty_learner`/0.9，无 → None/0.4，payload 仅含 score/weaknesses/review

## 七、兼容性
- [x] 会话级联删除同步清理 `workflow_runs` 与 `knowledge_chunks`，避免外键约束失败
- [x] 原有接口语义与统一响应格式不变

## 八、运行验证
- [x] `python -m compileall app` 通过
- [x] `import app.main` 通过
- [x] `alembic upgrade head` 成功，版本号 `f0a1b2c3d4e5`，新增表/字段齐全
- [x] `pytest tests/test_smoke.py -v`：33 passed
- [x] 定向冒烟：清洗/切片/分类、`should_retrieve`、工作流 interrupt+resume、A2A 信封全部 PASS
