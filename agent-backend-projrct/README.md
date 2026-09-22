# 学面通 AI · 后端（agent-backend-projrct）

基于 **FastAPI + SQLAlchemy 2.0 + MySQL + MinIO** 构建的 AI 面试模拟与学习后端服务，采用四层架构组织代码，提供用户认证、会话管理、聊天消息存储、面试记录、MinIO 文件存储与预签名访问能力。

## 一、技术栈

| 组件 | 说明 |
| --- | --- |
| FastAPI | Web 框架，负责路由分发与接口定义 |
| Pydantic v2 | 请求/响应参数结构化校验 |
| SQLAlchemy 2.0 | ORM 框架，统一数据建模与数据库操作 |
| PyMySQL | MySQL 驱动，供 SQLAlchemy 连接 MySQL |
| Alembic | 数据库表结构迁移，支持模型变更一键同步 |
| passlib[bcrypt] | 密码哈希加密，存储不保留明文 |
| pydantic-settings | 环境变量结构化读取与校验 |
| python-dotenv 1.0.1 | 按运行环境分层加载 .env 文件 |
| Loguru 0.7.2 | 日志体系：控制台彩色输出 + 文件滚动留痕 |
| uvicorn | ASGI 服务器 |
| python-multipart | multipart/form-data 表单与文件上传解析（FastAPI UploadFile 依赖） |
| minio | MinIO 对象存储 SDK，封装原文件上传/删除/预签名下载 |
| httpx | HTTP 客户端，供接口冒烟测试使用（经 starlette TestClient 同步调用 ASGI） |

## 二、项目结构（四层架构）

```
agent-backend-projrct/
├── .venv/                          # Python 虚拟环境（不提交）
├── .env.development                # 开发环境配置（含敏感信息，不提交）
├── .env.production                 # 生产环境配置（含敏感信息，不提交）
├── .gitignore                      # Git 忽略规则
├── requirements.txt                # 依赖清单
├── alembic.ini                     # Alembic 迁移配置（连接串不在这里写死）
├── pytest.ini                      # pytest 配置：测试路径、发现规则、warning 过滤
├── prompt.md                       # 原始需求说明
├── README.md
├── alembic/                        # 数据库迁移脚本目录
│   ├── env.py                      # 迁移环境（连接串从配置层注入）
│   └── versions/                   # 各版本迁移脚本
│       ├── 2026_09_11_1656-37fbff02c763_init_users_table.py        # users 表初始化
│       ├── 2026_09_13_1030-a1b2c3d4e5f6_add_user_avatar.py         # users.avatar 字段
│       ├── 2026_09_15_1000-c5d6e7f8a9b0_add_session_tables.py      # session/chat_messages/interviews 表
│       └── 2026_09_15_1100-d7e8f9a0b1c2_add_resources_table.py     # resources 表 + chat_messages.file_extracted_text
├── logs/                           # Loguru 日志产物（不提交）
│   ├── app.log                     # 全量日志（按天滚动、自动压缩）
│   └── error.log                   # ERROR 及以上级别日志
├── uploads/                        # 旧本地存储目录（仅 file_service.py 教学保留，运行逻辑已切换 MinIO）
├── tests/                          # 冒烟测试目录
│   ├── conftest.py                 # 测试夹具：SQLite 内存 DB + 依赖覆写 + TestClient + FakeMinio
│   ├── test_smoke.py               # 冒烟测试：健康检查、CRUD、异常分支、注册/限流
│   ├── test_auth_login.py          # 登录/JWT 鉴权链路测试
│   ├── test_rate_limit.py          # 固定窗口限流器单元测试
│   ├── test_upload_minio.py        # MinIO 上传链路冒烟测试
│   └── test_avatar_proxy.py        # 头像公开代理接口测试
└── app/
    ├── main.py                     # FastAPI 入口：日志初始化、异常处理器、路由聚合、lifespan 定时清理
    ├── security.py                 # 安全工具：密码 bcrypt 哈希 + 弱密码强度策略
    ├── core/                       # 横切基础设施
    │   ├── config.py               # 统一配置层（环境分层 + pydantic-settings + MinIO 配置）
    │   ├── exceptions.py           # 自定义业务/系统异常
    │   ├── responses.py            # 统一响应模型（code/message/data/detail）
    │   ├── pagination.py          # 分页参数与结果模型
    │   ├── jwt.py                  # JWT 签发/校验（Access/Refresh 双令牌）
    │   ├── rate_limit.py           # 固定窗口限流（注册接口 IP 维度）
    │   ├── logger.py               # Loguru 日志配置（开发双写 / 生产仅文件）
    │   ├── scheduler.py            # 每日 03:00 过期资源清理调度（asyncio 轻量实现，可手动执行）
    │   └── handlers.py             # 全局异常处理器
    ├── enums/
    │   ├── response_code.py        # 业务状态码枚举
    │   ├── token_type.py           # JWT 令牌类型枚举（access/refresh）
    │   ├── resource_type.py        # 资源类型枚举：0=文件，1=图片，2=音频
    │   ├── storage_scene.py        # 存储场景枚举：0=长过期(1月)，1=短过期(2小时)，2=只提取内容
    │   ├── upload_purpose.py       # 上传用途枚举：0=普通资源，1=用户头像
    │   ├── file_type.py            # 文件类型枚举：image/document（旧本地逻辑用）
    │   ├── interview_status.py     # 面试状态枚举：进行中/已完成/异常终止
    │   ├── select_model.py         # 消息选择模式枚举：默认/知识精讲/刷题/简历优化/模拟面试/面试复盘
    │   └── session_model.py        # 会话模式枚举：学习/面试/笔记
    ├── schemas/                    # 校验层：Pydantic v2 请求/响应模型
    │   ├── user.py                 # 用户模型
    │   ├── auth.py                 # 注册/登录/刷新/令牌模型
    │   ├── file.py                 # 文件上传响应模型：FileUploadResult / ResourceUploadResult
    │   ├── session.py              # 会话创建/更新/响应模型
    │   ├── message.py              # 消息响应模型（含 Segment 子模型）
    │   └── interview.py            # 面试记录响应模型
    ├── db/                         # 数据库层
    │   ├── base.py                 # SQLAlchemy Declarative Base
    │   ├── database.py             # Engine / Session 工厂 / get_db 依赖
    │   └── models.py               # ORM 模型：User / Session / ChatMessage / Interview / Resource
    ├── dao/                        # 数据访问层
    │   ├── user_dao.py             # 用户表：insert/get/update/delete/find_by_username
    │   ├── resource_dao.py          # 资源元数据：insert/get_by_hash/list_expired/delete
    │   ├── session_dao.py           # 会话表：insert/get/list/update/delete
    │   ├── message_dao.py           # 消息表：insert/get_by_session/list_paginate
    │   └── interview_dao.py        # 面试记录：insert/get_by_id/get_by_message_id
    ├── integrations/               # 第三方集成层：封装 SDK，业务层只调用工具方法
    │   └── minio_client.py         # MinioStorage 工具类：上传/删除/预签名URL/桶管理/path编解码
    ├── services/                   # 业务层：业务逻辑 + 密码哈希
    │   ├── user_service.py          # 用户业务（含头像回写）
    │   ├── auth_service.py          # 注册/登录认证/令牌刷新（注册头像走 MinIO 两阶段）
    │   ├── session_service.py       # 会话业务：创建/列表/编辑/级联删除
    │   ├── message_service.py       # 消息业务：分页查询/关联面试状态注入
    │   ├── interview_service.py     # 面试记录业务：按 ID+用户查询详情
    │   ├── upload_service_minio.py  # MinIO 上传业务：去重/场景分流/头像回写
    │   ├── resource_cleanup_service.py # 过期资源清理：先删 MinIO 对象再删元数据
    │   └── file_service.py          # 旧本地上传逻辑（教学保留，不参与运行）
    └── routers/                    # 路由层
        ├── health.py               # 健康检查路由（/health，不挂鉴权）
        └── v1/
            ├── api.py              # v1 路由统一聚合出口（main.py 只挂载 health_router + v1_router）
            ├── deps.py             # 公共依赖项：JWT 鉴权 get_current_user / Service 工厂等
            ├── auth.py             # 认证路由（注册/登录/刷新/当前用户）
            ├── users.py            # 用户增删改查路由（统一 JWT 登录鉴权）
            ├── sessions.py          # 会话路由：列表/创建/编辑/删除/消息列表（统一 JWT 鉴权）
            ├── interviews.py       # 面试详情路由：按 ID 获取 qa_object（统一 JWT 鉴权）
            ├── files.py            # 文件上传路由（统一 JWT 鉴权）
            └── avatar.py           # 头像公开代理路由（无鉴权）
```

### 分层职责

- **路由层（routers）**：仅做参数接收、路由分发，不堆砌核心业务逻辑。v1 路由在 `routers/v1/api.py` 统一聚合，`main.py` 只挂载 `health_router` + `v1_router`，新增业务模块只需在 `api.py` 追加 `include_router`。
- **校验层（schemas）**：Pydantic v2 定义请求/响应模型，路径/查询/请求体全部结构化。
- **业务层（services）**：处理业务逻辑，密码哈希在此层完成，只调用 DAO，不直接操作 Session；MinIO 上传/去重/场景分流/头像回写/过期清理均在此层。
- **数据访问层（dao）**：数据库操作全部封装在此，禁止裸写原生 SQL 拼接；写操作统一加事务，失败自动回滚。
- **第三方集成层（integrations）**：封装 MinIO 等 SDK，业务层只调用工具方法，不裸写第三方代码。
- **横切基础设施（core / enums / db）**：统一配置、统一响应、分页模型、全局异常处理、日志、ORM 建模、定时调度、业务状态码与资源/会话/面试等枚举，供各层复用。

## 三、安装与运行

> 以下命令均在项目根目录 `d:\ProgramData\VueProjects\agent-backend-projrct` 下执行。
> 虚拟环境统一使用隐藏目录 `.venv`（Python 社区惯例，IDE 默认识别）。

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

激活成功后，命令行提示符前会出现 `(.venv)` 前缀。若 PowerShell 提示"禁止运行脚本"，先执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. 安装依赖

```powershell
# 推荐：用 python -m pip，确保使用当前虚拟环境的解释器
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. 选择运行环境并启动服务

通过系统环境变量 `APP_ENV` 决定加载哪一份配置（缺省为 `development`）：

```powershell
# 开发环境（默认，加载 .env.development）
$env:APP_ENV = "development"
python -m uvicorn app.main:app --reload

# 生产环境（加载 .env.production，启动前必须替换其中的真实账号与密钥）
$env:APP_ENV = "production"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 也可以不激活环境，直接用解释器绝对路径执行：
> `.venv\Scripts\python.exe -m pip install -r requirements.txt`
> `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`

### 依赖服务说明

后端依赖以下外部服务，启动前需确保均已就绪：

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| MySQL | 3306 | 数据库，需提前创建 `agent_project_database` 数据库 |
| MinIO | 9000（API）/ 9001（Console） | 对象存储，需预先创建 `ai-resource` 桶 |

启动后访问：

- 接口地址：<http://127.0.0.1:8000/api/v1/users>
- Swagger 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/>

## 四、环境变量分层管理（开发 / 生产）

环境变量文件统一放在**项目根目录**，按环境拆分，由 [`app/core/config.py`](app/core/config.py) 统一加载：

| 文件 | 用途 | 是否提交 |
| --- | --- | --- |
| `.env.development` | 开发环境配置，日志级别 DEBUG、本地 MySQL | 否（.gitignore 已忽略） |
| `.env.production` | 生产环境配置模板，部署时替换为真实账号/密钥 | 否（.gitignore 已忽略） |

**配置优先级**：系统环境变量 > `.env.{APP_ENV}` 文件 > 代码默认值。容器/CI 可直接注入系统环境变量覆盖文件内容。

### 配置项一览

| 变量 | 说明 | 开发环境值 | 生产环境值 |
| --- | --- | --- | --- |
| `APP_ENV` | 运行环境（development/production） | `development` | `production` |
| `MYSQL_URL` | MySQL 连接串 | `mysql+pymysql://root:123456@localhost:3306/agent_project_database` | 替换为生产最小权限账号 |
| `JWT_SECRET_KEY` | JWT 签名密钥（至少 32 位随机串，`python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成） | 本地开发随机串 | 必须替换为高强度随机字符串 |
| `JWT_ALGORITHM` | JWT 签名算法 | `HS256` | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 访问令牌有效期（分钟） | `30` | 按安全策略设定 |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 刷新令牌有效期（天） | `7` | 按安全策略设定 |
| `LOG_LEVEL` | 日志级别 | `DEBUG` | `INFO` |
| `LOG_RETENTION` | 日志文件保留时长（Loguru retention 语义） | `15 days` | `30 days` |
| `SQL_ECHO` | 是否回显 SQL 语句 | `false` | `false` |
| `MINIO_ENDPOINT` | MinIO 服务地址（host:port，不含 scheme） | `localhost:9000` | 替换为生产 MinIO 地址 |
| `MINIO_ACCESS_KEY` | MinIO 访问密钥 | `minioadmin` | 替换为生产最小权限账号 |
| `MINIO_SECRET_KEY` | MinIO 秘密密钥 | `minioadmin` | 必须替换为高强度密钥 |
| `MINIO_BUCKET` | 资源默认桶名 | `ai-resource` | 按业务命名 |
| `MINIO_SECURE` | MinIO 是否启用 HTTPS | `false` | `true` |
| `MINIO_PRESIGN_EXPIRY_SECONDS` | 预签名下载 URL 有效期（秒），供前端临时访问私有桶对象 | `7200`（2 小时） | 按安全策略设定 |
| `RESOURCE_LONG_EXPIRE_DAYS` | 长过期场景（storage_scene=0）保留天数 | `30`（1 个月） | 按业务设定 |
| `RESOURCE_SHORT_EXPIRE_HOURS` | 短过期场景（storage_scene=1）保留小时数 | `2` | 按业务设定 |
| `UPLOAD_MAX_SIZE` | 单个上传文件大小上限（字节） | `104857600`（100MB） | 按业务设定 |
| `UPLOAD_DIR` | 旧本地存储根目录（仅 file_service.py 教学保留用） | `uploads` | `uploads` |
| `UPLOAD_URL_PREFIX` | 旧本地上传访问 URL 前缀（与 StaticFiles 挂载一致） | `/uploads` | `/uploads` |

### 使用约定

- 数据库地址、密钥等敏感/环境相关信息只允许出现在环境变量或配置层，**业务层统一通过 `settings` 读取，禁止硬编码**：

```python
from app.core.config import settings

print(settings.MYSQL_URL)   # 仅配置层/基础设施层使用，业务代码不直接读密钥
```

- 生产环境的 `.env.production` 仅在部署服务器单独维护，不随代码库分发；变量也可由部署平台直接注入。

## 五、日志体系（Loguru）

日志统一由 [`app/core/logger.py`](app/core/logger.py) 配置，全项目禁止 `print`，关键操作、报错、入参出参必须记录日志。

| 输出通道 | 位置 | 级别 | 开发环境 | 生产环境 |
| --- | --- | --- | --- | --- |
| 控制台 | 标准错误输出 | `LOG_LEVEL` | 彩色输出，便于调试 | **关闭**，避免容器 stdout 收集器二次落盘 |
| 全量日志文件 | `logs/app.log` | `LOG_LEVEL` | 每天 00:00 滚动、保留 `LOG_RETENTION`、滚动文件压缩 zip、异步写入 | 同左 |
| 错误日志文件 | `logs/error.log` | ERROR 及以上 | 含完整堆栈，排障与告警优先查看 | 同左 |

- 开发环境默认 `DEBUG` 级别且控制台+文件双写，便于调试；生产环境使用 `INFO` 且**仅文件输出**，避免控制台日志被容器 stdout 收集器二次落盘后与文件双写，减少敏感信息外露面。
- uvicorn / SQLAlchemy / Alembic 等三方库的标准库日志已桥接进 Loguru，格式统一。
- 异常日志强制关闭变量值诊断（`diagnose=False`），避免敏感信息（如密码、连接串）随堆栈写入日志。
- `logs/` 目录已在 `.gitignore` 中忽略，日志只用于本地/服务器留痕，不提交版本库。

业务代码中获取与使用日志（Loguru 使用 `{}` 占位符）：

```python
from app.core.logger import get_logger

logger = get_logger("user_service")
logger.info("用户创建成功 id={} username={}", user.id, user.username)
logger.error("系统异常：{}", exc)
```

## 六、接口列表

| 方法 | 路径 | 说明 | 鉴权 | 成功 HTTP 状态码 |
| --- | --- | --- | --- | --- |
| GET | `/` | 根路径健康检查（仅返回存活标识） | 否 | 200 |
| GET | `/health` | 健康检查：服务存活 + 数据库连通性，异常返回 503 | 否 | 200 / 503 |
| GET | `/docs` | Swagger UI 接口文档 | 否 | 200 |
| GET | `/redoc` | ReDoc 接口文档 | 否 | 200 |
| GET | `/openapi.json` | OpenAPI 元数据 | 否 | 200 |
| POST | `/api/v1/auth/register` | 用户注册（弱密码校验 + bcrypt 哈希 + IP 限流 5/min，可选头像走 MinIO 两阶段上传） | 否 | 201 |
| POST | `/api/v1/auth/login` | 登录，返回 Access/Refresh 双令牌 | 否 | 200 |
| POST | `/api/v1/auth/refresh` | 用 Refresh Token 换新 Access Token | 否（凭刷新令牌） | 200 |
| GET | `/api/v1/auth/me` | 获取当前登录用户信息 | 是（JWT） | 200 |
| POST | `/api/v1/users/` | 创建用户 | 是（JWT） | 201 |
| GET | `/api/v1/users/` | 查询用户列表 | 是（JWT） | 200 |
| GET | `/api/v1/users/{user_id}` | 查询单个用户 | 是（JWT） | 200 |
| PUT | `/api/v1/users/{user_id}` | 更新用户 | 是（JWT） | 200 |
| DELETE | `/api/v1/users/{user_id}` | 删除用户 | 是（JWT） | 200 |
| POST | `/api/v1/sessions/` | 创建会话（title + session_model） | 是（JWT） | 201 |
| GET | `/api/v1/sessions/` | 会话列表分页，可按 session_model 过滤 | 是（JWT） | 200 |
| PUT | `/api/v1/sessions/{session_id}` | 编辑会话标题/模式 | 是（JWT） | 200 |
| DELETE | `/api/v1/sessions/{session_id}` | 级联删除会话（含消息/面试/资源清理） | 是（JWT） | 200 |
| GET | `/api/v1/sessions/{session_id}/messages` | 分页获取聊天消息（含 request/response segments） | 是（JWT） | 200 |
| GET | `/api/v1/interviews/{interview_id}` | 获取面试详情（含 qa_object） | 是（JWT） | 200 |
| POST | `/api/v1/files/upload` | 通用文件上传（multipart，MinIO 存原文件 + MySQL 存元数据） | 是（JWT） | 200 |
| GET | `/api/v1/avatar/{user_id}` | 头像公开代理（307 重定向到 MinIO 预签名 URL） | 否 | 307 |

> **鉴权白名单**：`/health`、文档接口、`/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/auth/refresh`、`/api/v1/avatar/{user_id}` 不挂登录鉴权；
> 其余业务接口（含 `/api/v1/sessions/*`、`/api/v1/interviews/*`、`/api/v1/files/upload`）统一要求登录。

### 鉴权流程（JWT 双令牌 + 无感刷新）

1. `POST /api/v1/auth/login` 登录成功，拿到 `access_token`（默认 30 分钟）与 `refresh_token`（默认 7 天）；
2. 后续业务请求在请求头携带 `Authorization: Bearer <access_token>`；
3. 访问令牌过期时接口返回 401(40104)，前端调用 `POST /api/v1/auth/refresh`（请求体携带 `refresh_token`）换取新的访问令牌；
4. 用新令牌自动重试原请求，全程无需用户重新登录；刷新令牌也失效（40105）时再跳转登录页。

### 会话与消息数据流

```
前端发送消息
  → 后端按 select_model（默认/知识精讲/刷题/简历优化/模拟面试/面试复盘）路由到 AI 服务
  → AI 返回结果写入 chat_messages 表（含 request_text / response_text / segments）
  → 模拟面试场景：同时写入 interviews 表，message.interview_id 关联
  → 前端轮询 / WebSocket 获取消息更新
```

### 请求示例

```powershell
# 1. 登录获取令牌
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/auth/login" `
  -Method Post -ContentType "application/json" `
  -Body '{"username":"alice","password":"Goodpass1"}'

# 2. 创建会话
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/sessions/" `
  -Method Post -ContentType "application/json" `
  -Headers @{ "Authorization" = "Bearer $($login.data.access_token)" } `
  -Body '{"title":"我的第一次面试","session_model":1}'

# 3. 获取会话列表
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/sessions/?page=1&page_size=20" `
  -Headers @{ "Authorization" = "Bearer $($login.data.access_token)" }

# 4. 访问令牌过期后，用刷新令牌换新
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/auth/refresh" `
  -Method Post -ContentType "application/json" `
  -Body (@{ refresh_token = $login.data.refresh_token } | ConvertTo-Json)
```

## 七、统一响应约定（双层状态码）

项目采用 **HTTP 状态码 + 业务码** 双层设计：

- **HTTP 状态码**：按真实语义返回，前端可直接用于请求成败判断、监控告警。
- **响应体 `code`**：5 位业务码，前三位与 HTTP 状态码对齐，后两位做业务细分（同为 404 可区分"用户不存在/会话不存在"）。

### 统一响应体结构

```json
{
  "code": 0,
  "message": "操作成功",
  "data": {},
  "detail": null
}
```

- `code`：业务状态码，`0` 成功，非 `0` 失败；
- `message`：中文提示，前端可直接展示；
- `data`：业务数据，失败时为 `null`；
- `detail`：可选，失败时返回请求定位信息（path/method/query_params）及字段级校验明细。

### 状态码映射表

| 场景 | HTTP 状态码 | body code | message 示例 |
| --- | --- | --- | --- |
| 成功 | 200 / 201 | 0 | 操作成功 |
| 用户名重复 | 400 | 40001 | 用户名已存在 |
| 用户名或密码错误 | 401 | 40103 | 用户名或密码错误 |
| 缺失/过期/伪造访问令牌 | 401 | 40104 | 访问令牌无效或已过期 |
| 刷新令牌无效或已过期 | 401 | 40105 | 刷新令牌无效或已过期 |
| 上传文件类型不支持 | 400 | 40003 | 文件类型不支持 |
| 上传文件超出大小限制 | 400 | 40004 | 文件大小超出限制 |
| 上传文件为空 | 400 | 40005 | 文件为空 |
| 资源重复（并发兜底） | 400 | 40006 | 资源已存在 |
| 用户不存在 | 404 | 40401 | 用户不存在 |
| 会话不存在 | 404 | 40403 | 会话不存在 |
| 面试记录不存在 | 404 | 40404 | 面试记录不存在 |
| 路由不存在 | 404 | 404 | 请求的资源不存在 |
| 请求参数校验失败 | 422 | 42200 | 字段【username】字段长度不能小于限制值 |
| 健康检查数据库不可用 | 503 | 50300 | 服务异常：数据库不可用 |
| 系统内部错误 | 500 | 50000 | 系统繁忙，请稍后再试 |

### 错误响应示例

```json
{
  "code": 40403,
  "message": "会话不存在",
  "data": null,
  "detail": { "path": "/api/v1/sessions/9999", "method": "GET", "query_params": {} }
}
```

> 前端处理建议：axios 响应拦截器按 body `code` 分流——`40104` 时自动用刷新令牌换新并重试原请求（单飞，避免并发刷新），`40105` 刷新失败再跳转登录页，`422` 展示字段错误，其他统一 toast `message`。

## 八、数据库迁移（Alembic）

连接串由 `alembic/env.py` 从配置层注入，`alembic.ini` 中不写死任何账号密码。修改 `app/db/models.py` 中的模型后：

```powershell
# 1. 自动生成迁移脚本（检测模型与数据库的差异）
alembic revision --autogenerate -m "add_user_table"

# 2. 一键同步到数据库
alembic upgrade head
```

当前已有迁移版本（按时间顺序）：

| 迁移脚本 | 说明 |
| --- | --- |
| `2026_09_11_1656_init_users_table` | users 表初始化 |
| `2026_09_13_1030_add_user_avatar` | users.avatar 头像字段 |
| `2026_09_15_1000_add_session_tables` | session / chat_messages / interviews 会话相关表 |
| `2026_09_15_1100_add_resources_table` | resources 资源元数据表 + chat_messages.file_extracted_text 字段 |
| `2026_09_16_1000_add_chat_segments_interview_user` | chat_messages.request/response_segments 字段 + interviews 表 user_id 字段 |

## 九、MinIO 对象存储

文件资源采用 **元数据与原文件解耦** 架构：原文件存入 MinIO 私有桶，资源元数据（文件名、MD5、存储路径、过期时间、用途等）写入 MySQL `resources` 表，两者通过 `storage_path`（`minio://{bucket}/{object_key}`）关联。

### resources 表关键字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT | 自增主键 |
| `resource_type` | TINYINT | 资源类型：0=文件，1=图片，2=音频（见 `ResourceType` 枚举） |
| `storage_scene` | TINYINT | 存储场景：0=长过期(1月)，1=短过期(2小时)，2=只提取内容（见 `StorageScene` 枚举） |
| `update_purpose` | TINYINT | 上传用途：0=普通资源，1=用户头像（见 `UploadPurpose` 枚举） |
| `file_name` | VARCHAR | 客户端上传原始文件名（仅展示用，不参与存储路径） |
| `file_hash` | VARCHAR | 文件内容 MD5，去重核心字段 |
| `storage_path` | VARCHAR | MinIO 存储路径 `minio://{bucket}/{object_key}`；只提取场景为空串 |
| `user_id` | BIGINT | 上传用户 ID（与 `file_hash` 组合唯一键 `uk_file_hash_user_id`） |
| `expire_time` | DATETIME | 资源过期时间；头像资源为 `NULL`（永不过期，不参与定时清理） |
| `create_time` | DATETIME | 创建时间，数据库 `now()` 自动填充 |

> `chat_messages` 表另新增 `file_extracted_text`（MEDIUMTEXT）字段，用于存储从文件中提取的完整文本（对话上下文使用）。

### 存储路径结构

object_key 按 **用户 + 资源类型分目录**，内容 MD5 命名，天然支持去重：

```
user_{user_id}/{images|audio|files}/{file_hash}{ext}
```

完整存储路径：`minio://{bucket}/user_{user_id}/{images|audio|files}/{file_hash}{ext}`

例：用户 7 上传一张 PNG，MD5 为 `abc123...`，存储路径为 `minio://ai-resource/user_7/images/abc123....png`。

### 去重规则

- **用户级去重**：同一用户上传相同内容（MD5）的文件，直接复用已存在的元数据，不重复上传 MinIO 对象，响应中 `duplicated=true`。
- **双层兜底**：Service 层先按 `file_hash + user_id` 预查；并发场景下若仍命中数据库唯一键 `uk_file_hash_user_id`，捕获 `IntegrityError` 后回查复用，不产生重复对象。

### 场景分流（storage_scene）

| 场景 | 行为 | expire_time |
| --- | --- | --- |
| `0` 长过期 | 上传 MinIO + 写元数据 | 默认 30 天后 |
| `1` 短过期 | 上传 MinIO + 写元数据 | 默认 2 小时后 |
| `2` 只提取内容 | 不上传原文件、不写元数据，仅返回提取的文本 | `NULL` |

### 头像特殊处理

- 注册接口 `POST /api/v1/auth/register` 的头像上传采用 **两阶段** 调用，避免头像非法时产生孤儿账号：
  1. `prepare_avatar`：先校验图片（类型/大小/空文件），不上传、不写库；
  2. 建号成功后 `commit_avatar`：上传 MinIO、落元数据、回写 `users.avatar`。
- 头像资源 `expire_time=None`（永不过期），被 `users.avatar` 永久引用，不参与定时清理。
- 头像访问通过 `GET /api/v1/avatar/{user_id}` 公开代理（307 重定向到预签名 URL），`<img>` 标签可直接使用。**注意**：MinIO 服务不可达时，该接口会超时并返回 HTTP 500，需确保 MinIO 正常运行。

### 过期清理

- `app/core/scheduler.py` 使用 asyncio 轻量定时器，**每日 03:00** 扫描 `expire_time` 已到期记录，先删 MinIO 对象再删元数据，单条失败不阻断整体清理。
- 定时任务由 FastAPI `lifespan` 启动与取消，适用于单 worker 部署；多 worker 各触发一次，删除操作幂等。
- **手动清理入口**：`python -m app.core.scheduler` 可立即执行一次过期资源清理（不入循环）。

## 十、安全说明

- **密码哈希**：`app/security.py` 使用 bcrypt 算法，存储时不保留明文。
- **登录鉴权（JWT）**：`app/core/jwt.py` 基于 PyJWT 签发/校验 Access/Refresh 双令牌（HS256 验签，载荷含 sub/username/type/exp/jti，两类令牌严格隔离不可混用）；`app/routers/v1/deps.py` 的 `get_current_user` 依赖在业务路由组统一挂载，未登录请求一律 401(40104)；签名密钥只从配置层（`JWT_SECRET_KEY` 环境变量）读取，业务层不写死。
- **MinIO 私有桶 + 预签名 URL**：原文件存入 MinIO 私有桶，外部无法直接通过对象路径访问；前端临时访问通过 `MinioStorage.presigned_get_url` 生成带签名的预签名下载 URL，有效期由 `MINIO_PRESIGN_EXPIRY_SECONDS` 控制（默认 2 小时），过期后需重新获取。
- **头像公开代理安全**：`GET /api/v1/avatar/{user_id}` 为**无鉴权公开接口**，因为 `<img>` 标签无法携带 `Authorization` 头。该接口仅返回 307 重定向到 MinIO 预签名 URL，不直接返回文件内容；预签名 URL 有时效限制，过期后浏览器再次请求即可获取新 URL。
- **会话越权防护**：所有会话/面试接口按 `session_id` + `user_id` 联合查询，越权访问统一返回 404，避免 ID 被枚举。
- **敏感配置**：`.env.*` 包含数据库账号、MinIO 密钥与 JWT 密钥，已由 `.gitignore` 忽略，禁止提交；生产部署必须替换默认值。
- **响应脱敏**：响应模型仅暴露必要字段，不返回密码字段等敏感信息。
- **健康检查脱敏**：`/health` 接口在数据库不可用时只返回 `database=fail` 布尔状态，异常原始信息仅写入 `logs/error.log`，不回传给调用方。
- **日志脱敏**：所有 sink 强制 `diagnose=False`，异常堆栈不打印局部变量值；生产环境关闭控制台 sink，仅落盘到文件。
- **统一异常处理**：`app/core/handlers.py` 全局捕获业务/系统/参数/框架异常，系统错误堆栈仅写入日志文件，对外只返回通用提示与请求定位信息。

## 十一、冒烟测试

测试代码位于 [`tests/`](tests/)，使用 `pytest` + `httpx`（通过 `starlette.testclient.TestClient`）验证接口核心链路，不依赖外部 MySQL 与 MinIO 服务，当前共 **76 个用例全部通过**。

### 测试策略

- **数据库隔离**：`tests/conftest.py` 用 SQLite 内存数据库 + `StaticPool` 替代 MySQL，所有 Session 共享同一连接，测试不污染真实数据库。
- **MinIO 隔离**：`conftest.py` 提供 `FakeMinio` 内存版 MinIO 夹具，覆写 `get_minio_storage` 依赖，记录上传对象供断言与去重验证，不依赖真实 MinIO 服务。
- **依赖覆写**：仅覆写 `get_db` 与 `get_minio_storage`，无需真实 MySQL/MinIO；JWT 鉴权不绕过，用例通过真实"注册→登录"获取访问令牌后携带 Bearer 头访问业务接口。
- **用例隔离**：每个用例执行后自动清空所有表数据并重置限流器，保证用例间互不影响。

### 运行测试

```powershell
# 激活虚拟环境后执行
pytest tests/ -v
```

> 真实 MySQL / MinIO 连通性验证不在冒烟测试范围内：MySQL 由 `/health` 接口在真实运行时承担（启动应用后访问 `http://localhost:8000/health`，数据库异常时返回 503）；MinIO 连通性由首次上传时 `ensure_bucket` 懒触发，启动期不强依赖。
