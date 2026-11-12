# 学面通 AI · 后端（agent-backend-projrct）

基于 **FastAPI + SQLAlchemy 2.0 + MySQL + Redis + MinIO + LangChain + LangGraph** 构建的 AI Agent 后端。核心能力：三层流式聊天（模型层 / 提示词层 / 记忆层）、提示词版本管理 + 公共/私有模板拼接 + Redis 缓存、用户画像变量注入、RAG 向量检索（双存储 + 用户隔离）、三层记忆（瞬时 / 工作 / 长期）、LangGraph 学习测评工作流（interrupt + checkpoint + 评分 JSON + A2A 信封）、流程总控路由（关键词 + 语义意图）。

## 一、技术栈

| 组件 | 说明 |
| --- | --- |
| FastAPI | Web 框架，路由分发、接口定义、依赖注入、lifespan 生命周期管理 |
| Pydantic v2 | 请求/响应参数结构化校验，禁止裸参接收 |
| SQLAlchemy 2.0 | ORM 框架，同步 Session + MySQL 方言，统一数据建模与数据库操作 |
| PyMySQL | MySQL 驱动 |
| Alembic | 数据库表结构迁移，revision head 当前为 `f0a1b2c3d4e5` |
| passlib[bcrypt] | 密码哈希加密，存储不保留明文 |
| pydantic-settings | 环境变量结构化读取与校验（环境分层核心） |
| python-dotenv 1.0.1 | 按 `APP_ENV` 加载 `.env.{APP_ENV}` |
| Loguru 0.7.2 | 日志体系：控制台彩色 + 文件滚动留痕 + ERROR 单独文件 |
| uvicorn | ASGI 服务器（`--reload` 开发 / `--host 0.0.0.0` 生产） |
| python-multipart | multipart/form-data 表单与文件上传解析（FastAPI UploadFile 依赖） |
| minio | MinIO 对象存储 SDK，封装上传/删除/预签名 URL/桶管理 |
| redis>=5.0 | 提示词模板 Hash 缓存 + 工作记忆（滑动摘要，TTL 8h） |
| LangChain | Prompt 模板、Message 类型、Runnable 链路组装、递归智能切片 |
| langchain-openai | OpenAI 兼容模型适配器（openai / deepseek / dashscope 统一入口） |
| langchain-text-splitters | RecursiveCharacterTextSplitter，按标题→段落→句子优先级切分 |
| LangGraph | StateGraph / interrupt / Command / MemorySaver checkpoint，编排学习测评工作流 |
| qdrant-client | 向量检索：远端 Server 或本地文件模式（`QDRANT_LOCAL_PATH` 非空时用本地） |
| DashScope (dashscope) | `text-embedding-v4` 文本向量化，1024 维，每批 10 条 |
| pypdfium2 | PDF 解析与扫描件渲染（替代 PyPDF2），150 DPI 渲染页面为 PNG |
| python-docx | Word 文档解析，识别 Heading 1/2/3 注入 `#/##/###` 标题标记 |
| 火山引擎 SDK (volcengine) | OCRNormal 扫描版 PDF 兜底，取 `data.line_texts` 按行拼接 |
| pillow | PDF 页面渲染为 PNG 图片 |
| fastembed | 本地向量模型 `BAAI/bge-small-zh-v1.5`，语义意图判断（~30MB，首次下载，失败降级关键词） |
| httpx | HTTP 客户端，冒烟测试用（经 starlette TestClient 同步调用 ASGI） |

## 二、项目结构（分层架构）

```
agent-backend-projrct/
├── .venv/                          # Python 虚拟环境（不提交）
├── .env.development                # 开发环境配置（含敏感信息，不提交）
├── .env.production                 # 生产环境配置模板（部署时替换真实账号/密钥，不提交）
├── .gitignore                      # Git 忽略规则
├── requirements.txt                # 依赖清单
├── alembic.ini                     # Alembic 迁移配置（连接串不写死）
├── pytest.ini                      # pytest 配置
├── prompt.md / spec.md / tasks.md  # 原始需求与 Spec 产物（开发参考）
├── README.md
├── alembic/                        # 数据库迁移脚本目录
│   ├── env.py                      # 迁移环境（连接串从配置层注入）
│   └── versions/                   # 各版本迁移脚本（按时间顺序）
│       ├── 2026_09_11_1656_init_users_table                     # users 表初始化
│       ├── 2026_09_13_1030_add_user_avatar                      # users.avatar 字段
│       ├── 2026_09_15_1000_add_session_tables                   # session / chat_messages / interviews 表
│       ├── 2026_09_15_1100_add_resources_table                  # resources 表 + chat_messages.file_extracted_text
│       ├── 2026_09_16_1000_add_chat_segments_interview_user     # chat_messages.request/response_segments + interviews.user_id
│       ├── 2026_10_29_1000_add_prompt_templates_user_profiles   # prompt_templates 模板版本表 + user_profiles 画像表
│       ├── 2026_10_30_1000_add_knowledge_chunks_and_chat_reference # knowledge_chunks 切片原文 + chat_messages.reference_sources/response_payload
│       ├── 2026_10_30_1100_add_long_term_memory                 # user_profiles 新增 4 字段（learning_goal/learning_style/interview_focus/long_term_summary）
│       └── 2026_10_30_1200_add_workflow_runs                    # workflow_runs 工作流运行记录表
├── logs/                           # Loguru 日志产物（不提交）
├── uploads/                        # 旧本地存储目录（file_service.py 教学保留，运行已切 MinIO）
├── tests/                          # 冒烟测试（33 项，全部通过）
│   ├── conftest.py                 # SQLite 内存 DB + FakeMinio + 依赖覆写 + TestClient
│   ├── test_smoke.py               # 核心冒烟：健康检查、CRUD、注册限流、鉴权链路
│   ├── test_auth_login.py          # 登录 / JWT 鉴权 / 刷新链路
│   ├── test_rate_limit.py          # 固定窗口限流器单元测试
│   ├── test_upload_minio.py        # MinIO 上传链路
│   └── test_avatar_proxy.py        # 头像公开代理接口
└── app/
    ├── main.py                     # FastAPI 入口：日志初始化、lifespan 定时清理 + 模板缓存 + 语义预热、异常处理器、自定义 Swagger/ReDoc（npmmirror CDN）、根路径 302 → /docs
    ├── security.py                 # 安全工具：密码 bcrypt 哈希 + 弱密码强度策略
    │
    ├── core/                       # 横切基础设施
    │   ├── config.py               # 统一配置层（pydantic-settings，含 RAG/记忆/工作流全部环境变量）
    │   ├── exceptions.py           # BusinessException / SystemException 两层异常
    │   ├── responses.py            # ApiResponse 响应模型 + success() 构造器
    │   ├── pagination.py           # 分页参数（Pagination）与分页结果（PageResult）
    │   ├── jwt.py                  # JWT 签发/校验（Access/Refresh 双令牌，PyJWT HS256）
    │   ├── rate_limit.py           # 固定窗口限流（注册接口 IP 维度）
    │   ├── logger.py               # Loguru 配置（开发双写 / 生产仅文件 + 异常桥接）
    │   ├── scheduler.py            # 每日 03:00 过期资源清理（asyncio 轻量定时器，可手动执行）
    │   └── handlers.py             # 全局异常处理器（业务/系统/参数/框架异常统一拦截）
    │
    ├── enums/                      # 业务枚举，禁止硬编码数字状态
    │   ├── response_code.py        # 5 位业务状态码（前三位对齐 HTTP 状态码）
    │   ├── select_model.py         # 消息选择模式：DEFAULT=0 / KNOWLEDGE=1 / PRACTICE=2 / RESUME_OPTIMIZE=3 / MOCK_INTERVIEW=4 / INTERVIEW_REVIEW=5
    │   ├── session_model.py        # 会话模式：LEARNING=0 / INTERVIEW=1 / NOTE=2
    │   ├── resource_type.py        # 资源类型：FILE=0 / IMAGE=1 / AUDIO=2
    │   ├── storage_scene.py        # 存储场景：LONG_EXPIRE=0 / SHORT_EXPIRE=1 / EXTRACT_ONLY=2
    │   ├── upload_purpose.py       # 上传用途：GENERAL=0 / AVATAR=1
    │   ├── token_type.py           # 令牌类型：ACCESS / REFRESH
    │   ├── template_type.py        # 模板类型：PRIVATE=1 / PUBLIC=2
    │   ├── interview_status.py     # 面试状态：RUNNING=0 / COMPLETED=1 / ABNORMAL=2
    │   └── file_type.py            # 文件类型：IMAGE / DOCUMENT（旧本地上传用）
    │
    ├── agent/                       # Agent 层：智能体配置 + LangGraph 工作流 + A2A 信封
    │   ├── config.py               # 7 个智能体映射（study_coach / interview_coach / note_assistant / resume_coach / quiz_generate_workflow / learning_evaluator / difficulty_learner）
    │   ├── workflows/
    │   │   ├── __init__.py
    │   │   ├── checkpoint.py       # 全局 MemorySaver（lru_cache 单例）+ build_thread_config(thread_id)
    │   │   ├── state.py            # LearningWorkflowState(TypedDict, total=False)：run_id/user_id/session_id/.../a2a_envelope
    │   │   └── learning.py         # LangGraph 学习测评工作流：prepare → generate_quiz → wait_user_answer(interrupt) → evaluate_answer → finalize → END
    │   └── a2a/
    │       ├── __init__.py         # 对外暴露 A2AEnvelope
    │       └── envelope.py         # Pydantic v2 最小契约信封：from_agent / payload_type / payload / next_agent / confidence(0~1)
    │
    ├── llm/                         # LLM 三层架构
    │   ├── __init__.py
    │   ├── llm.py                   # 模型层：get_llm(provider, streaming, temperature, model) → LangChain 实例
    │   ├── prompt_layer.py          # 提示词层：merge_system_messages 合并历史与 system_prompt，缺省回退 DEFAULT_SYSTEM_PROMPT
    │   └── memory.py                # 记忆层：从 DB 拉最近 N 轮对话拼接上下文（教学保留，实际由 memory_service 替代）
    │
    ├── rag/                         # RAG 双存储链路（解析 → 清洗 → 分类 → 切片 → 向量化 → Qdrant + MySQL）
    │   ├── __init__.py
    │   ├── qdrant_utils.py          # get_qdrant_client()（lru_cache，本地/远端自动切换）+ ensure_collection + embed_texts + search_vectors
    │   ├── ocr.py                   # ocr_pdf(path)：pypdfium2 150 DPI 渲染 → base64 → 火山 OCRNormal → line_texts
    │   ├── core.py                  # 对外只暴露 ingest_file(path, *, user_id, file_name, resource_id, doc_category) → list[IngestedChunk]
    │   ├── chunk_store.py           # save_chunks / fetch_chunks_by_vector_ids / fetch_sources_by_reference（原文回查）
    │   ├── retriever.py             # search_similar_chunks：embed → threshold 过滤 → 回查 MySQL → 截断 → 返回
    │   └── chat_rag.py              # should_retrieve 意图判断 + format_retrieved_chunks + build_rag_system_prompt
    │
    ├── utils/                       # 通用工具（业务可复用）
    │   ├── __init__.py
    │   └── json_utils.py            # parse_json_object：支持 ```json 围栏、首尾大括号提取，失败返回 None
    │
    ├── db/                          # 数据库层
    │   ├── base.py                  # Declarative Base
    │   ├── database.py              # Engine + SessionLocal(sessionmaker) + get_db Depends（pool_pre_ping / pool_recycle=3600）
    │   └── models.py                # ORM：User / Session / ChatMessage / Interview / Resource / PromptTemplate / UserProfile / KnowledgeChunk / WorkflowRun
    │
    ├── dao/                         # 数据访问层（数据库操作全部封装在此）
    │   ├── user_dao.py              # 用户 CRUD + find_by_username
    │   ├── session_dao.py           # 会话 CRUD + get_session_by_user + **级联删除**（workflow_runs → interviews → chat_messages → knowledge_chunks → resources → sessions）
    │   ├── message_dao.py           # 消息 insert / get_by_session + list_paginate + **get_by_request_id / update_response**
    │   ├── interview_dao.py         # 面试 insert / get_by_id / get_by_message_id
    │   ├── resource_dao.py          # 资源元数据 insert / get_by_hash / list_expired / delete
    │   ├── prompt_template_dao.py   # 模板 CRUD + get_active / list_by_group / max_version / activate
    │   ├── user_profile_dao.py      # 用户画像 get_by_user / upsert
    │   └── workflow_run_dao.py      # 工作流运行记录 insert / get_by_run_id / update_status
    │
    ├── integrations/                # 第三方集成层（封装 SDK，业务层只调工具方法）
    │   ├── minio_client.py          # MinioStorage：upload / delete / presigned_get_url / ensure_bucket / get_object_bytes（RAG 入库用）
    │   └── redis_client.py          # RedisCache（lru_cache 单例）：get / set / hget_json / hset_json / delete / expire
    │
    ├── services/                    # 业务层：业务逻辑，只调 DAO / 第三方工具，不直接操作 Session
    │   ├── auth_service.py          # 注册（含头像两阶段 + 弱密码校验） / 登录 / 令牌刷新
    │   ├── user_service.py          # 用户 CRUD（含头像回写）
    │   ├── session_service.py       # 会话业务：创建/列表/编辑/级联删除
    │   ├── message_service.py       # 消息分页查询：4 元组 (messages, total, status_map, sources_map)
    │   ├── interview_service.py     # 面试详情查询
    │   ├── upload_service_minio.py  # MinIO 上传：去重 / 场景分流 / 头像回写
    │   ├── resource_cleanup_service.py # 过期资源清理：先删 MinIO 对象再删元数据
    │   ├── prompt_template_service.py # 提示词版本管理：get_full_prompt(agent_name) → 公共模板 + 私有模板拼接；启动加载 Redis Hash；一键回滚
    │   ├── prompt_variable_service.py # 三层变量注入：安全检查 → 格式化 → 占位符替换（防注入、防超长）
    │   ├── user_profile_service.py  # UserProfile CRUD，扩展 4 个画像字段（learning_goal/learning_style/interview_focus/long_term_summary）
    │   ├── semantic_intent_service.py # fastembed 语义意图判断，warmup() 首次加载本地向量模型，不可用时降级关键词
    │   ├── long_term_memory.py      # 长期画像写入：关键词+语义判断是否触发 → 后台 daemon 线程 LLM JSON 抽取 → create_or_update
    │   ├── memory_service.py        # 三层记忆 orchestrator：InstantMemory(DB) + WorkingMemory(Redis+滑动摘要) + LongTermMemory(画像) → load_context / append_turn
    │   ├── stream_chat_service.py   # **三层流式聊天**：LLM 模型层 → MemoryService.load_context → should_retrieve + search_similar_chunks → PromptVariableService.build_system_prompt → memory.merge_system_messages → chain.astream SSE → 落库 + working_memory.append_turn + 画像后台提交
    │   ├── rag_service.py           # RagService.ingest_resource：校验归属 → MinIO 下载 → 临时文件 → ingest_file → commit → finally unlink
    │   ├── learning_workflow_service.py # LangGraph 学习测评业务：start（出题到 interrupt）/ submit_answer（恢复评分）/ get_run（查状态）
    │   └── orchestrator_service.py  # 流程总控路由：关键词快筛 + fastembed 语义兜底，命中工作流返回 workflow_type，否则 chat
    │
    ├── schemas/                      # Pydantic v2 校验层
    │   ├── auth.py                  # RegisterRequest / LoginRequest / RefreshRequest / UserResponse / TokenResponse
    │   ├── user.py                  # UserCreate / UserUpdate / UserResponse
    │   ├── session.py               # SessionCreate / SessionUpdate / SessionResponse
    │   ├── message.py               # StreamChatRequest / MessageResponse（含 sources / response_payload）/ Segment
    │   ├── interview.py             # InterviewResponse
    │   ├── file.py                  # FileUploadResult / ResourceUploadResult
    │   ├── prompt.py                # PromptTemplateCreate / PromptTemplateResponse / PromptRollbackRequest
    │   ├── user_profile.py          # UserProfileUpsert / UserProfileResponse（扩展 4 个画像字段）
    │   ├── learning_workflow.py     # LearningWorkflowStartRequest / SubmitRequest / StartResponse / SubmitResponse / DetailResponse
    │   └── orchestrator_schemas.py  # AgentTaskStartRequest / RouteDecision / StartResponse
    │
    └── routers/                      # 路由层：只做参数接收 / 路由分发 / 异常捕获，不堆砌业务逻辑
        ├── health.py                # GET /health（无鉴权，验证服务存活 + SELECT 1 数据库连通性，异常 503）
        └── v1/
            ├── api.py               # v1 路由统一聚合出口（main.py 只挂载 health + v1）
            ├── deps.py              # 公共依赖项：get_current_user(JWT) / DAO 工厂 / Service 工厂
            ├── auth.py              # 注册 / 登录 / 刷新 / 当前用户（注册/登录/刷新公开，/me 挂 JWT）
            ├── users.py             # 用户 CRUD（统一挂 JWT）
            ├── sessions.py          # 会话列表/创建/编辑/删除/消息列表 + stream-chat（SSE）
            ├── interviews.py        # 面试详情（JWT）
            ├── files.py             # 通用文件上传（multipart → MinIO + MySQL）
            ├── avatar.py            # 头像公开代理（无鉴权，307 重定向到 MinIO 预签名 URL）
            ├── prompts.py           # 提示词模板查看 / 回滚 / 智能体配置（全部 JWT）
            ├── rag.py               # RAG 入库 POST /api/v1/rag/resources/{resource_id}/ingest（JWT）
            ├── learning_workflows.py # 学习测评工作流 start / submit / 查状态（JWT）
            └── orchestrator.py      # 流程总控 POST /api/v1/agent/tasks/start（JWT，工作流 JSON / 聊天 SSE 双分支）
```

### 分层职责（严格单向依赖）

- **路由层（routers）**：参数接收、路由分发、依赖注入、统一异常捕获，不堆砌业务逻辑。v1 路由在 `routers/v1/api.py` 统一聚合，`main.py` 只挂载 `health_router` + `v1_router`，新增业务模块只需在 `api.py` 追加 `include_router`。
- **校验层（schemas）**：Pydantic v2 定义请求/响应模型，路径/查询/请求体全部结构化，禁止裸参接收。
- **业务层（services）**：处理业务逻辑，只调 DAO / 第三方工具 / 其他 Service，不直接操作 Session、不写裸 SQL。
- **数据访问层（dao）**：数据库操作全部封装在此，禁止裸写原生 SQL 拼接；写操作统一加事务，失败自动回滚；DAO 之间互不依赖。
- **第三方集成层（integrations）**：封装 MinIO / Redis SDK，业务层只调工具方法，不裸写第三方代码。
- **Agent 层（agent）**：智能体配置（7 个）、LangGraph 工作流编排（checkpoint + state + graph）、A2A 信封契约。
- **LLM 层（llm）**：LangChain 封装，模型层 / 提示词层 / 记忆层 三层解耦。
- **RAG 层（rag）**：文件向量化入库 + 语义检索链路，独立模块。
- **横切基础设施（core / enums / db / utils）**：统一配置、统一响应、分页、全局异常处理、日志、ORM 建模、定时调度、业务状态码、通用工具。

## 三、安装与运行

> 以下命令均在项目根目录 `d:\ProgramData\VueProjects\agent-backend-projrct` 下执行。虚拟环境统一使用 `.venv`。

### 1. 创建虚拟环境

```powershell
python -m venv .venv
```

### 2. 激活虚拟环境

PowerShell：
```powershell
.\.venv\Scripts\Activate.ps1
```

cmd：
```bat
.\.venv\Scripts\activate.bat
```

PowerShell 提示"禁止运行脚本"时先执行一次（仅影响当前用户）：
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. 安装依赖

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. 启动外部依赖服务

后端依赖以下外部服务（截图已验证 MinIO + Redis 均启动）：

| 服务 | 默认端口 | 必须？ | 启动方式 | 说明 |
| --- | --- | --- | --- | --- |
| MySQL | 3306 | **必须** | `net start MySQL80` | 提前创建数据库 `agent_project_database`，`alembic upgrade head` 会自动建表 |
| MinIO | 9000（API）/ 9001（Console） | **必须** | 启动 `minio.exe server` | 预先创建桶 `ai-resource`（Console 可直接创建） |
| Redis | 6379 | **必须** | 启动 `redis-server.exe` | 无密码，`REDIS_ENABLED=true` |
| Qdrant | 无（本地模式） | **可选** | 无需部署 | `.env.development` 已配 `QDRANT_LOCAL_PATH=".qdrant_data"`，走嵌入式本地文件存储；如需多实例共享可部署 Qdrant Server 改 `QDRANT_HOST/PORT` |
| DashScope API | 外部 | **可选** | 无需本地 | `DASHSCOPE_API_KEY` 为空时 RAG 入库/检索会返回明确错误提示，不影响其它接口 |
| 火山引擎 API | 外部 | **可选** | 无需本地 | 扫描版 PDF 兜底 OCR，未配置时扫描件报错 |

### 5. 数据库迁移

```powershell
alembic upgrade head
```

当前 revision head：`f0a1b2c3d4e5`（workflow_runs 表）。

### 6. 启动服务

通过系统环境变量 `APP_ENV` 决定加载哪份配置（缺省 `development`）：

```powershell
# 开发环境（默认，热重载）
$env:APP_ENV = "development"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 生产环境（加载 .env.production，启动前必须替换真实账号/密钥）
$env:APP_ENV = "production"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

> 也可以不激活环境，直接用解释器绝对路径：`.venv\Scripts\python.exe -m uvicorn app.main:app --reload`

### 7. 启动后访问

| 地址 | 说明 |
| --- | --- |
| <http://127.0.0.1:8000/> | 根路径 → 302 重定向到 Swagger UI |
| <http://127.0.0.1:8000/health> | 健康检查（验证服务存活 + MySQL 连通性，异常 503） |
| <http://127.0.0.1:8000/docs> | **Swagger UI**（推荐，国内 CDN，自动分组展示全部接口） |
| <http://127.0.0.1:8000/redoc> | ReDoc API 文档页（备选） |
| <http://127.0.0.1:8000/openapi.json> | OpenAPI 3.1 JSON 元数据 |

### Swagger UI 打开空白页排障

Swagger UI 静态资源默认从 `cdn.jsdelivr.net` 加载，国内网络经常被强制关闭连接（"远程主机强迫关闭了一个现有的连接"），导致页面空白。本项目已改为**国内镜像 npmmirror**（`registry.npmmirror.com`），正常情况下无需手动干预。

如果仍空白：

1. 打开浏览器 **F12 → Network**，查看是不是 `swagger-ui-bundle.js` 或 `swagger-ui.css` 加载失败（红色）；
2. 直接访问 `http://127.0.0.1:8000/openapi.json` 确认 JSON 可访问 → 后端没问题，问题出在浏览器 CDN 加载；
3. 换浏览器（Edge / Chrome / Firefox）或换网络（手机热点）测试；
4. 完全离线方案：下载 [swagger-ui-dist@5](https://www.npmjs.com/package/swagger-ui-dist) 的 `swagger-ui-bundle.js` 和 `swagger-ui.css` 到项目根目录 `static/swagger-ui/` 下，改 `app/main.py` 中的 `SWAGGER_JS_URL` / `SWAGGER_CSS_URL` 为 `/static/swagger-ui/swagger-ui-bundle.js`（并在 main.py 里 mount StaticFiles）。

## 四、环境变量分层管理（开发 / 生产）

环境变量文件统一放在**项目根目录**，按环境拆分，由 [`app/core/config.py`](app/core/config.py) 统一加载。

| 文件 | 用途 | 是否提交 |
| --- | --- | --- |
| `.env.development` | 开发环境配置，日志级别 DEBUG、本地 MySQL | **否**（.gitignore 已忽略） |
| `.env.production` | 生产环境配置模板，部署时替换为真实账号/密钥 | **否** |

**配置优先级**：系统环境变量 > `.env.{APP_ENV}` 文件 > 代码默认值。容器/CI 可直接注入系统环境变量覆盖文件内容。

### 配置项一览

#### 基础

| 变量 | 说明 | 开发环境值 |
| --- | --- | --- |
| `APP_ENV` | 运行环境（`development` / `production`） | `development` |
| `APP_NAME` | 应用名称（Swagger 标题） | `用户管理 API` |
| `MYSQL_URL` | MySQL 连接串 | `mysql+pymysql://root:123456@localhost:3306/agent_project_database` |
| `JWT_SECRET_KEY` | JWT 签名密钥（≥32 字符，`python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成） | 本地随机串 |
| `JWT_ALGORITHM` | 签名算法 | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期（分钟） | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期（天） | `7` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` |
| `LOG_RETENTION` | 日志文件保留时长 | `15 days` |
| `SQL_ECHO` | 是否回显 SQL | `false` |
| `REGISTER_RATE_LIMIT` | 注册接口 IP 限流次数 | `5` |
| `REGISTER_RATE_WINDOW_SECONDS` | 限流窗口（秒） | `60` |

#### MinIO 对象存储

| 变量 | 说明 | 开发环境值 |
| --- | --- | --- |
| `MINIO_ENDPOINT` | `host:port`（不含 scheme） | `localhost:9000` |
| `MINIO_ACCESS_KEY` | 访问密钥 | `minioadmin` |
| `MINIO_SECRET_KEY` | 秘密密钥 | `minioadmin` |
| `MINIO_BUCKET` | 资源默认桶名 | `ai-resource` |
| `MINIO_SECURE` | 是否 HTTPS | `false` |
| `MINIO_PRESIGN_EXPIRY_SECONDS` | 预签名下载 URL 有效期 | `7200` |

#### Redis

| 变量 | 说明 | 开发环境值 |
| --- | --- | --- |
| `REDIS_ENABLED` | 是否启用（关闭后自动降级 DB 直读） | `true` |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | 地址 / 端口 / 逻辑库 | `127.0.0.1 / 6379 / 0` |
| `REDIS_PASSWORD` | 密码（空表示无密码） | 空 |
| `REDIS_TIMEOUT` | 连接/读写超时（秒） | `3` |
| `PROMPT_CACHE_KEY` | 提示词模板 Redis Hash Key | `prompt:templates:active` |

#### LLM

| 变量 | 说明 | 开发环境值 |
| --- | --- | --- |
| `LLM_PROVIDER` | 模型提供方：`openai / deepseek / dashscope / custom` | 按接入方填 |
| `LLM_API_KEY` | API Key（必填） | 自行填写 |
| `LLM_BASE_URL` | 接入地址（为空用 provider 默认；custom 场景必填） | 按需 |
| `LLM_MODEL` | 模型名称（为空用 provider 默认） | 按需 |
| `LLM_TEMPERATURE` | 采样温度 | `0.7` |
| `LLM_MAX_TOKENS` | 单次最大 token | `2048` |
| `LLM_TIMEOUT` | 请求超时（秒） | `60` |

#### 用户画像 + 提示词变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `PROMPT_VAR_MAX_LENGTH` | 单个变量值最大长度 | `500` |
| `PROMPT_VARS_TOTAL_MAX_LENGTH` | 变量值总长度上限 | `4000` |

#### RAG（知识库）

| 变量 | 说明 | 开发环境值 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | DashScope API Key（向量化） | 自行填写 |
| `QDRANT_LOCAL_PATH` | Qdrant 本地文件路径（非空时走本地模式，无需部署 Server） | `.qdrant_data` |
| `QDRANT_HOST` / `QDRANT_PORT` | Server 模式地址（本地模式忽略） | `127.0.0.1 / 6333` |
| `QDRANT_COLLECTION` | 向量集合名 | `knowledge_chunks` |
| `RAG_EMBEDDING_MODEL` | 向量化模型 | `text-embedding-v4` |
| `RAG_EMBEDDING_DIM` | 向量维度 | `1024` |
| `RAG_TOP_K` | 检索默认条数 | `3` |
| `RAG_SCORE_THRESHOLD` | 相似度阈值（低于丢弃） | `0.4` |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | 切片大小与重叠 | `500 / 50` |
| `RAG_CHUNK_TEXT_MAX` | 注入 LLM 前单条原文最大长度 | `800` |

#### 火山引擎 OCR

| 变量 | 说明 | 开发环境值 |
| --- | --- | --- |
| `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY` | AK/SK | 自行填写（扫描件场景必填） |
| `VOLC_REGION` | 区域 | `cn-north-1` |

#### 记忆层

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `MEMORY_MAX_TURNS` | 瞬时记忆上下文回带轮数（1 轮 = 用户消息 + AI 回复） | `8` |
| `MEMORY_MAX_CHARS` | 瞬时记忆总字符预算 | `8000` |
| `WORKING_MEMORY_TTL_SECONDS` | 工作记忆 Key 过期时间（每次读写自动续期） | `28800`（8h） |
| `WORKING_MEMORY_MAX_CHARS` | 工作记忆原始消息触发总结阈值 | `8000` |
| `WORKING_MEMORY_KEEP_MESSAGES` | 总结后保留的最近消息条数 | `6` |
| `SUMMARY_MAX_CHARS` | LLM 生成摘要长度上限 | `500` |
| `LONG_TERM_SIMILARITY_THRESHOLD` | 长期画像语义写入判定阈值（fastembed 余弦相似度） | `0.62` |

#### 文件上传

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `UPLOAD_MAX_SIZE` | 单文件大小上限（字节） | `104857600`（100MB） |

### 使用约定

```python
from app.core.config import settings

print(settings.MYSQL_URL)      # 仅基础设施层使用
print(settings.LLM_API_KEY)   # 业务层仅读，不硬编码
```

敏感信息（密钥）只出现在 `.env.*` 或部署平台环境变量注入，**禁止硬编码到业务层代码**。

## 五、日志体系（Loguru）

日志统一由 [`app/core/logger.py`](app/core/logger.py) 配置，全项目禁止 `print`，关键操作、报错、入参出参必须记录日志。

| 输出通道 | 位置 | 级别 | 开发环境 | 生产环境 |
| --- | --- | --- | --- | --- |
| 控制台 | 标准错误输出 | `LOG_LEVEL` | 彩色输出，便于调试 | **关闭** |
| 全量日志文件 | `logs/app.log` | `LOG_LEVEL` | 每天 00:00 滚动、保留 `LOG_RETENTION`、滚动文件压缩 zip、异步写入 | 同左 |
| 错误日志文件 | `logs/error.log` | ERROR 及以上 | 含完整堆栈 | 同左 |

- uvicorn / SQLAlchemy / Alembic 等三方库的标准库日志已桥接进 Loguru，格式统一。
- 异常日志强制关闭变量值诊断（`diagnose=False`），避免敏感信息（密码、连接串）随堆栈写入日志。
- `logs/` 已在 `.gitignore` 中忽略。

业务代码中使用：
```python
from app.core.logger import get_logger

logger = get_logger("rag_service")
logger.info("RAG 入库完成 resource_id={} chunks={}", resource_id, len(chunks))
logger.error("数据库不可用: {}", exc)
```

## 六、统一响应约定（双层状态码）

项目采用 **HTTP 状态码 + 5 位业务码** 双层设计，前三位与 HTTP 状态码对齐，后两位做业务细分。

### 统一响应体结构

```json
{
  "code": 0,
  "message": "操作成功",
  "data": {},
  "detail": null
}
```

### 状态码映射表（节选）

| 场景 | HTTP | body code | message |
| --- | --- | --- | --- |
| 成功 | 200 / 201 | 0 | 操作成功 |
| 用户名重复 | 400 | 40001 | 用户名已存在 |
| 弱密码 | 400 | 40002 | 密码强度不足 |
| 上传类型不支持 | 400 | 40003 | 文件类型不支持 |
| 上传超大小限制 | 400 | 40004 | 文件大小超出限制 |
| 上传空文件 | 400 | 40005 | 文件为空 |
| 刷新令牌不可用 | 401 | 40103 / 40104 / 40105 | 按具体细分 |
| 鉴权路由非法智能体 | 422 | 42200 | 未知智能体 agent_name=... |
| 用户不存在 | 404 | 40401 | 用户不存在 |
| 会话不存在 | 404 | 40403 | 会话不存在 |
| 面试/资源不存在 | 404 | 40404 / 40405 | — |
| 参数校验失败 | 422 | 42200 | 字段级明细 |
| 数据库不可用 | 503 | 50300 | 服务异常：数据库不可用 |
| 出题/评分结果解析失败 | 500 | 50000 | 系统繁忙，请稍后再试 |

### 错误响应示例

```json
{
  "code": 40403,
  "message": "会话不存在",
  "data": null,
  "detail": { "path": "/api/v1/sessions/9999", "method": "GET", "query_params": {} }
}
```

## 七、接口列表

| 方法 | 路径 | 说明 | 鉴权 | HTTP 状态码 |
| --- | --- | --- | --- | --- |
| GET | `/` | 根路径 302 → Swagger UI | 否 | 302 |
| GET | `/health` | 健康检查（服务存活 + SELECT 1） | 否 | 200 / 503 |
| GET | `/docs` | Swagger UI | 否 | 200 |
| GET | `/redoc` | ReDoc | 否 | 200 |
| GET | `/openapi.json` | OpenAPI 3.1 JSON | 否 | 200 |
| **认证鉴权** | | | | |
| POST | `/api/v1/auth/register` | 用户注册（弱密码校验 + bcrypt + IP 限流 5/min） | 否 | 201 |
| POST | `/api/v1/auth/login` | 登录，返回 Access/Refresh 双令牌 | 否 | 200 |
| POST | `/api/v1/auth/refresh` | Refresh Token 换新 Access Token | 否（凭刷新令牌） | 200 |
| GET | `/api/v1/auth/me` | 当前登录用户 | JWT | 200 |
| **用户管理** | | | | |
| POST / GET / GET / PUT / DELETE | `/api/v1/users/{user_id}` | 用户 CRUD | JWT | 201/200 |
| **文件 / 头像** | | | | |
| POST | `/api/v1/files/upload` | 通用文件上传 → MinIO + MySQL 元数据 | JWT | 200 |
| GET | `/api/v1/avatar/{user_id}` | 头像公开代理 → 307 到 MinIO 预签名 URL | 否 | 307 |
| **会话与聊天** | | | | |
| POST | `/api/v1/sessions/` | 创建会话（title + session_model） | JWT | 201 |
| GET | `/api/v1/sessions/` | 会话列表分页（可按 session_model 过滤） | JWT | 200 |
| PUT | `/api/v1/sessions/{session_id}` | 编辑会话 | JWT | 200 |
| DELETE | `/api/v1/sessions/{session_id}` | 级联删除（workflow_runs → interviews → chat_messages → knowledge_chunks → resources → sessions） | JWT | 200 |
| GET | `/api/v1/sessions/{session_id}/messages` | 分页获取聊天消息（含 request/response segments + sources + response_payload） | JWT | 200 |
| POST | `/api/v1/sessions/{session_id}/stream-chat` | **三层流式聊天**（SSE）：sources 来源片段、记忆注入、RAG 检索 | JWT | 200（SSE） |
| **面试** | | | | |
| GET | `/api/v1/interviews/{interview_id}` | 面试详情（含 qa_object） | JWT | 200 |
| **提示词版本管理** | | | | |
| GET | `/api/v1/prompts/config/agents` | 7 个智能体配置列表 | JWT | 200 |
| GET | `/api/v1/prompts/templates/{agent_name}/{scene}` | 查看指定智能体场景的模板历史版本 | JWT | 200 |
| POST | `/api/v1/prompts/rollback` | 模板一键回滚（`{"template_id": 123}`） | JWT | 200 |
| **RAG 知识库入库** | | | | |
| POST | `/api/v1/rag/resources/{resource_id}/ingest` | MinIO 下载 → 解析 → 切片 → 向量化 → Qdrant + MySQL 双写 | JWT | 200 |
| **学习测评工作流（LangGraph）** | | | | |
| POST | `/api/v1/learning-workflows/start` | 启动测评生成题目（图停 interrupt，返回 run_id + quiz JSON；同时写刷题消息） | JWT | 200 |
| POST | `/api/v1/learning-workflows/{run_id}/submit` | 提交答案 → 恢复图执行 → 评分 JSON + A2A 信封 → 回写原出题消息 | JWT | 200 |
| GET | `/api/v1/learning-workflows/{run_id}` | 查工作流状态 + 业务快照 | JWT | 200 |
| **流程总控** | | | | |
| POST | `/api/v1/agent/tasks/start` | 自动路由：命中工作流返回 JSON，否则流式聊天返回 SSE | JWT | 200（JSON 或 SSE） |

### 鉴权白名单

以下接口**不挂** JWT 登录鉴权：
- `/health`
- `/docs`、`/redoc`、`/openapi.json`、`/`
- `/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/auth/refresh`
- `/api/v1/avatar/{user_id}`

其余业务接口（含 `/api/v1/sessions/*`、`/api/v1/interviews/*`、`/api/v1/files/upload`、所有 prompts/rag/learning/agent 路由）统一要求登录。

### 鉴权流程（JWT 双令牌 + 无感刷新）

1. `POST /api/v1/auth/login` 成功后拿到 `access_token`（30 分钟） + `refresh_token`（7 天）；
2. 业务请求头携带 `Authorization: Bearer <access_token>`；
3. Access Token 过期 → 401(40104) → 前端 `POST /api/v1/auth/refresh` 换新 Access Token → 自动重试原请求（单飞，避免并发刷新）；
4. Refresh Token 也失效（40105）→ 跳转登录页。

### 会话与消息数据流

```
前端发送消息
  → POST /sessions/{session_id}/stream-chat（SSE）
  → MemoryService.load_context：LongTermMemory（画像 SystemMessage）
                               + WorkingMemory（Redis 滑动摘要 SystemMessage）
                               + InstantMemory（DB 近 N 轮）
  → should_retrieve + search_similar_chunks（关键词+语义双重触发 RAG）
  → PromptVariableService.build_system_prompt（公共模板 + 私有模板 + 画像变量）
  → chat_rag.build_rag_system_prompt（检索命中时注入 RAG_RULES）
  → chain.astream → SSE 帧
  → message_dao.insert_message（reference_sources 存 [{chunk_id, score}]）
  → working_memory.append_turn（追加消息 + 触发滑动摘要）
  → LongTermMemory.submit_profile_update_async（后台 daemon 线程判定是否抽取画像）
  → done 事件：携带 sources 完整 [{chunk_id, resource_id, file_name, chunk_index, score, text}]

前端轮询 / WebSocket 获取消息更新（也可用 GET /sessions/{session_id}/messages）
  → message_service.list_messages（按 reference_sources 调 fetch_sources_by_reference 回查原文）
  → 返回 4 元组 (messages, total, status_map, sources_map)
  → 消息 Response 含 sources 字段
```

### 请求示例（PowerShell）

```powershell
# 1. 登录
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/auth/login" `
  -Method Post -ContentType "application/json" `
  -Body '{"username":"alice","password":"Goodpass1"}'

# 2. 创建会话
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/sessions/" `
  -Method Post -ContentType "application/json" `
  -Headers @{ "Authorization" = "Bearer $($login.data.access_token)" } `
  -Body '{"title":"我的第一次面试","session_model":1}'

# 3. 流式聊天（SSE，curl 更方便）
# curl -N -X POST http://127.0.0.1:8000/api/v1/sessions/1/stream-chat `
#   -H "Authorization: Bearer $TOKEN" `
#   -H "Content-Type: application/json" `
#   -d '{"request_text":"介绍一下你自己","agent_name":"interview_coach"}'

# 4. RAG 入库（上传文件后拿到 resource_id）
# curl -X POST http://127.0.0.1:8000/api/v1/rag/resources/42/ingest -H "Authorization: Bearer $TOKEN"

# 5. 学习测评工作流
# curl -X POST http://127.0.0.1:8000/api/v1/learning-workflows/start `
#   -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" `
#   -d '{"session_id":1,"request_text":"出三道关于函数作用域的题","question_count":3}'

# 6. 流程总控（自动分流工作流或聊天）
# curl -N -X POST http://127.0.0.1:8000/api/v1/agent/tasks/start `
#   -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" `
#   -d '{"session_id":1,"agent_name":"quiz_generate_workflow","request_text":"出几道面试题"}'
```

## 八、数据库迁移（Alembic）

连接串由 `alembic/env.py` 从配置层注入，`alembic.ini` 不写死任何账号密码。

```powershell
# 自动生成迁移脚本
alembic revision --autogenerate -m "add_some_table"

# 一键同步
alembic upgrade head

# 查当前 revision
alembic current
```

当前迁移版本（按时间顺序）：

| 迁移脚本 | 说明 |
| --- | --- |
| `2026_09_11_1656_init_users_table` | users 表 |
| `2026_09_13_1030_add_user_avatar` | users.avatar 字段 |
| `2026_09_15_1000_add_session_tables` | session / chat_messages / interviews |
| `2026_09_15_1100_add_resources_table` | resources 表 |
| `2026_09_16_1000_add_chat_segments_interview_user` | chat_messages.request/response_segments + interviews.user_id |
| `2026_10_29_1000_add_prompt_templates_user_profiles` | prompt_templates（模板版本表）+ user_profiles（画像表） |
| `2026_10_30_1000_add_knowledge_chunks_and_chat_reference` | knowledge_chunks（切片原文表，resource_id BIGINT）+ chat_messages.reference_sources/response_payload |
| `2026_10_30_1100_add_long_term_memory` | user_profiles 新增 learning_goal / learning_style / interview_focus / long_term_summary |
| `2026_10_30_1200_add_workflow_runs` | workflow_runs（工作流运行记录） |

**级联删除顺序**（`session_dao.delete_cascade`）：workflow_runs → interviews → chat_messages → knowledge_chunks → resources → sessions（先删子级、先删 FK 依赖方，避免外键约束失败）。

## 九、MinIO 对象存储

采用 **元数据（MySQL resources 表）+ 原文件（MinIO 私有桶）** 解耦架构。

### 存储路径结构

```
user_{user_id}/{images|audio|files}/{file_hash}{ext}
```

完整存储路径：`minio://{bucket}/user_{user_id}/{images|audio|files}/{file_hash}{ext}`

### 去重规则

- 用户级去重：同一用户上传相同 MD5 文件直接复用元数据，`duplicated=true`；
- 双层兜底：Service 层预查 + 数据库唯一键 `uk_file_hash_user_id` 捕获 IntegrityError 后回查复用。

### 场景分流

| `storage_scene` | 行为 | expire_time |
| --- | --- | --- |
| 0 长过期 | 上传 MinIO + 写元数据 | 30 天后 |
| 1 短过期 | 上传 MinIO + 写元数据 | 2 小时后 |
| 2 只提取内容 | 不上传原文件、不写元数据，仅返回提取文本 | NULL |

### 头像特殊处理

注册接口的头像上传采用两阶段调用避免孤儿账号：先校验图片合法，建号成功后再上传 MinIO + 回写 `users.avatar`。头像资源永不过期（不参与定时清理），访问通过 `GET /api/v1/avatar/{user_id}` 307 重定向到 MinIO 预签名 URL。

### 过期清理

`app/core/scheduler.py` asyncio 轻量定时器，**每日 03:00** 扫描已到期记录，先删 MinIO 对象再删元数据，单条失败不阻断整体。由 FastAPI lifespan 启动与取消。

手动立即清理：
```powershell
python -m app.core.scheduler
```

## 十、核心架构（四层能力）

### 10.1 三层流式聊天（LangChain）

```
POST /sessions/{session_id}/stream-chat （SSE）
│
├─ llm.get_llm(provider, streaming=True)          # 模型层：provider → LangChain 实例
├─ MemoryService.load_context(user_id, session_id, db)
│   ├─ LongTermMemory.load_memory_context → SystemMessage【用户长期画像】
│   ├─ WorkingMemory.get → Redis Hash 滑动摘要 → SystemMessage【工作记忆摘要】
│   └─ InstantMemory.load → DB 近 MEMORY_MAX_TURNS 轮原始消息（FIFO + 字符预算裁剪）
├─ should_retrieve(request_text) → 触发 RAG？
│   ├─ 空文本 / 极短（<10 字）/ 确认语（"好的"/"知道了"）/ 推进语（"继续"）→ 跳过
│   └─ search_similar_chunks（关键词命中 or fastembed 语义判定）
│       ├─ embed(DashScope) → Qdrant query_points(user_id filter)
│       ├─ score < RAG_SCORE_THRESHOLD 丢弃
│       └─ knowledge_chunks 回查原文（>800 字截断 + "……"）
├─ PromptVariableService.build_system_prompt → 公共模板 + 私有模板 + {target_job} 等画像变量
├─ chat_rag.build_rag_system_prompt（检索命中时追加 RAG_RULES + 【资料1】/【资料2】）
├─ memory.merge_system_messages → 合并 SystemMessage（多层画像 + RAG_RULES + 公共/私有模板）
├─ chain.astream → SSE 帧（event: token / event: done / event: error）
├─ message_dao.insert_message → commit（reference_sources=[{chunk_id,score}]）
├─ working_memory.append_turn(request, response) → Redis 续期
│   └─ 原始消息 ≥ 8000 字 → LLM 总结 ≤500 字 + 保留最近 6 条原始消息
└─ LongTermMemory.submit_profile_update_async(request_text, conversation_context)
    └─ daemon 线程：关键词（"记住"/"记一下"）或 fastembed 相似度 ≥ 0.62 → LLM JSON 抽取 → create_or_update
```

### 10.2 RAG 双存储链路

```
ingest_file(path, *, user_id, file_name, resource_id, doc_category)
│
├─ 解析（字典分派）
│   ├─ PDF: pypdfium2 抽文字 → 平均每页 <20 字 → 火山引擎 OCRNormal 兜底
│   │       （150 DPI 渲染 → PNG → base64 → OCR → data.line_texts 拼接）
│   ├─ DOCX: python-docx + Heading 识别（Heading 1 → # / 2 → ## / 3 → ###）
│   ├─ TXT / MD: 直接读取
│   └─ 不支持类型抛异常
│
├─ _clean_text         # 零宽字符 / 空白合并 / 独立页码行删除
├─ _classify_document   # resume / study_material / general，显式 doc_category 优先
├─ _split_text          # RecursiveCharacterTextSplitter + 优先级 separators：
│                       # \n### → \n## → \n# → \n\n → \n → 。 → ！ → ？ → ； → ， → " " → ""
│                       # + MD5 去重（相同文本只留一份）
│
├─ DashScope embed      # text-embedding-v4 1024 维，每批 10 条，按 text_index 对齐
│
├─ Qdrant（只存向量 + 过滤字段，不存原文）
│   └─ payload = {user_id, doc_category, file_name, chunk_index, resource_id}
│       point.id = uuid4()
│       collection knowledge_chunks 自动建（COSINE + 1024）
│
└─ MySQL knowledge_chunks（存原文）
    └─ resource_id BIGINT FK + vector_id UNIQUE + text + chunk_index + char_count

检索（retriever.search_similar_chunks）：
  embed(query) → Qdrant query_points(top_k, user_id Filter)
    → score < RAG_SCORE_THRESHOLD 丢弃
    → knowledge_chunks 回查原文（缺失时 text="该参考片段已被删除"）
    → 超 RAG_CHUNK_TEXT_MAX(800 字) 截断 + "……"
    → 返回 [{chunk_id, resource_id, file_name, chunk_index, score, text}]
```

### 10.3 三层记忆体系

| 层 | 实现 | Key / 表 | 触发总结条件 | 总结策略 |
| --- | --- | --- | --- | --- |
| **瞬时记忆** | DB 拉近 N 轮 | `chat_messages` 按 session_id 取最近 `MEMORY_MAX_TURNS*2` 条 | 不触发 | 直接拼接（总字符预算 `MEMORY_MAX_CHARS` 裁剪） |
| **工作记忆** | Redis Hash | `memory:working:{user_id}:{session_id}`，TTL 8h，每次读写自动续期 | 原始消息总字符 ≥ `WORKING_MEMORY_MAX_CHARS`（8000 字） | LLM 生成 ≤500 字摘要，保留最近 6 条原始消息，旧消息丢弃 |
| **长期记忆** | UserProfile + 后台线程 | `user_profiles` 各字段 + `long_term_summary` | 用户消息含 "记住"/"记一下" 关键词，或 fastembed 本地语义模型相似度 ≥ `LONG_TERM_SIMILARITY_THRESHOLD`（0.62） | daemon 线程（非阻塞聊天）LLM 抽取 JSON → 字段校验 → create_or_update |

**降级策略**：Redis 不可用时工作记忆自动跳过（只走瞬时 + 长期）；fastembed 模型首次加载需要下载（~30MB），失败降级关键词判断；LLM 抽取失败静默重试不影响主流程。

### 10.4 LangGraph 学习测评工作流

```
LearningWorkflowState = TypedDict({
    run_id: str                  # UUID hex，同时作 LangGraph thread_id + workflow_runs.run_id
    user_id: int
    session_id: int
    request_text: str
    provider: str | None
    question_count: int
    quiz: dict                   # 出题 JSON（questions 列表）
    answers: list[dict]          # 用户作答
    evaluation: dict             # 评分 JSON（score/display_text/items/weaknesses/review）
    score: int                   # 0-100
    weaknesses: list[str]
    review: str
    status: str                  # creating / waiting_answer / grading / completed / failed
    a2a_envelope: dict            # A2A 信封
})

图结构（learning_workflow_graph.compile(checkpointer=get_workflow_checkpointer())）：
  prepare_learning_context → generate_quiz → wait_user_answer(interrupt)
                                                    ↓ Command(resume=answers)
                              evaluate_answer → finalize_result → END

关键设计：
  - 全局 MemorySaver checkpoint 保存图执行现场，崩溃后可 resume；
  - WorkflowRun.state_json 存业务快照（供前端展示 / 后端恢复）；
  - run_id 同时作 thread_id（LangGraph checkpoint 要求 thread_id 唯一）；
  - generate_quiz / evaluate_answer 各自独立 SessionLocal，在图节点内部构建提示词，
    节点之间不共享 DB 连接；
  - 动态提示词：agent_name="quiz_generate_workflow"/"learning_evaluator"，
    PromptTemplateManager.get_full_prompt + PromptVariableService.build_system_prompt；
  - 出题结果校验：parse_json_object → dict 且 questions list 非空，否则抛 SystemException；
  - 评分结果校验：同上，score clamp 到 0..100，weaknesses 最多 5 个；
  - **消息持久化**：启动时写 request_id="{run_id}:quiz" 的刷题消息
    （response_payload=quiz JSON）；提交后回写同一条消息的 response_text
    （优先 evaluation.display_text，不足 20 字时用得分+复盘兜底）。

A2A 信封（evaluate_answer 节点产出）：
  {
    "from_agent": "learning_evaluator",
    "payload_type": "weak_points",
    "payload": { "score": 85, "weaknesses": ["函数作用域"], "review": "建议复习闭包与作用域链" },
    "next_agent": "difficulty_learner",   // 有薄弱点时指向薄弱点专项 Agent
    "confidence": 0.9                     // 0-1 之间，无薄弱点时 0.4 / null
  }
```

### 10.5 流程总控路由

```python
WORKFLOW_ROUTE_RULES = (
    WorkflowRouteRule(
        agent_name="quiz_generate_workflow",
        workflow_type="learning_quiz",
        required_keywords=("题", "出题", "刷题", "练习", "测验", "测评", "小测", "面试题"),
        intent_examples=("帮我出几道练习题", "我想刷题", "来一套测验题",
                         "针对薄弱点出题", "做一个小测试", "出几道面试题"),
    ),
)

OrchestratorService.route(agent_name, request_text):
  1) agent_name 不在 AGENT_CONFIG → BusinessException 42200
  2) 无对应规则 → 返回 {"mode": "chat", "confidence": 1.0}
  3) 关键词快筛命中 → {"mode": "workflow", "confidence": 1.0}
  4) fastembed 语义兜底：similarity >= 0.62 → workflow（confidence=round(score,4)）
  5) fastembed 不可用（模型未下载）→ 降级 chat

POST /api/v1/agent/tasks/start（统一入口）：
  ├─ mode=workflow → LearningWorkflowService.start → JSON 响应
  └─ mode=chat    → assert_session → StreamChatService.stream_chat → SSE 流
```

### 10.6 智能体配置（7 个）

| agent_name | 中文标签 | 默认 scene | 职责 |
| --- | --- | --- | --- |
| `study_coach` | 学习辅导 | `study` | 知识讲解与答疑 |
| `interview_coach` | 面试辅导 | `interview` | 模拟面试提问与追问 |
| `note_assistant` | 笔记助手 | `note` | 整理、总结与结构化笔记 |
| `resume_coach` | 简历优化 | `resume` | 简历诊断与改写建议 |
| `quiz_generate_workflow` | 学习测题生成 | `quiz_generate` | 结构化题目 JSON |
| `learning_evaluator` | 学习评测 | `learning_evaluate` | 评分 + 点评 + 薄弱点 JSON |
| `difficulty_learner` | 薄弱点专项提升 | `difficulty_learning` | 针对薄弱点生成专项练习 |

`get_full_prompt(agent_name)` 通过 `AGENT_CONFIG` 解析 scene，**不存在的 agent_name 会抛 BusinessException**（长期画像抽取场景做了特殊处理）。

## 十一、安全说明

- **密码哈希**：bcrypt，存储不保留明文；弱密码校验（黑名单 + 字母+数字 + 禁止含用户名）。
- **JWT 双令牌**：Access（30min）/ Refresh（7d）严格隔离；签名密钥从环境变量读取（HS256 ≥32 字符）。
- **MinIO 私有桶 + 预签名 URL**：原文件存私有桶，外部无法直接访问；前端临时访问通过预签名下载 URL（默认 2 小时过期）。
- **会话越权防护**：所有会话/消息/面试/资源接口按 `session_id/resource_id` + `user_id` 联合查询，越权统一 404，避免 ID 枚举。
- **工作流/学习测评越权防护**：按 `run_id` + `user_id` 归属校验，无法操作他人发起的测评。
- **RAG 用户隔离**：Qdrant query_points 强制 `user_id` 过滤，切片只对上传用户本人可见。
- **登录限流**：注册接口固定窗口 IP 维度 5/min，超出 429。
- **敏感配置**：`.env.*` 含数据库账号、MinIO 密钥、JWT 密钥、DashScope/火山引擎 AK/SK，已由 `.gitignore` 忽略，禁止提交。
- **响应脱敏**：健康检查异常只返回 boolean，堆栈写日志；系统错误 message 统一 "系统繁忙，请稍后再试"。
- **日志脱敏**：`diagnose=False` 关闭变量值打印；生产环境关闭控制台 sink，仅文件输出。
- **Alembic 连接串**：不写死在 `alembic.ini`，从 `settings.MYSQL_URL` 注入。

## 十二、冒烟测试

`tests/` 目录当前共 **33 项**全部通过（`pytest tests/test_smoke.py -v`），覆盖核心基础链路：
- 健康检查 + 数据库隔离（SQLite 内存 DB，不污染真实 MySQL）；
- 用户 CRUD（5 个接口）；
- 注册 → 登录 → 刷新令牌 → /me 完整 JWT 链路；
- 固定窗口限流器单元测试（命中 / 未命中 / 窗口过期）；
- MinIO 上传链路（FakeMinio 内存桶，验证去重 / 头图像回写）；
- 头像公开代理 307 重定向。

**未覆盖**（需手动验证）：
- RAG 入库与检索（需要真实 Qdrant + DashScope）；
- LangGraph 学习测评工作流（需要 LLM 接入）；
- Redis 工作记忆（需要 Redis）；
- fastembed 语义模型（首次下载 ~30MB）。

### 运行测试

```powershell
python -m pytest tests/ -v
```

## 十三、完整验证清单

部署前在项目根目录依次执行，全部通过后方可认为后端健康：

```powershell
# 1. 语法检查
python -m compileall app

# 2. 应用导入（验证所有路由模块可加载）
python -c "import app.main; print('import ok')"

# 3. 数据库迁移（确保表结构与 ORM 模型对齐）
alembic upgrade head
alembic current   # 应输出 f0a1b2c3d4e5

# 4. 冒烟测试（33 项）
python -m pytest tests/test_smoke.py -v

# 5. 启动后浏览器访问
# - http://127.0.0.1:8000/            → 302 到 Swagger
# - http://127.0.0.1:8000/health      → {"status":"healthy"}
# - http://127.0.0.1:8000/docs        → Swagger UI 显示全部接口（无空白）
# - http://127.0.0.1:8000/openapi.json → 200，约 50KB JSON
```
