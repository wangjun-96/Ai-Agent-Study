# 用户管理 API

基于 **FastAPI + SQLAlchemy 2.0 + MySQL** 的用户增删改查示例项目，采用四层架构组织代码，密码使用 passlib[bcrypt] 哈希存储，环境变量按开发/生产分层管理，日志统一使用 Loguru 记录。

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
├── logs/                           # Loguru 日志产物（不提交）
│   ├── app.log                     # 全量日志（按天滚动、自动压缩）
│   └── error.log                   # ERROR 及以上级别日志
├── tests/                          # 冒烟测试目录
│   ├── conftest.py                 # 测试夹具：SQLite 内存 DB + 依赖覆写 + TestClient
│   └── test_smoke.py               # 冒烟测试用例（健康检查、CRUD、异常分支）
└── app/
    ├── main.py                     # FastAPI 入口：日志初始化、异常处理器、路由
    ├── security.py                 # 安全工具：密码 bcrypt 哈希 + 弱密码强度策略
    ├── core/                       # 横切基础设施
    │   ├── config.py               # 统一配置层（环境分层 + pydantic-settings）
    │   ├── exceptions.py           # 自定义业务/系统异常
    │   ├── responses.py            # 统一响应模型（code/message/data/detail）
    │   ├── jwt.py                  # JWT 签发/校验（Access/Refresh 双令牌）
    │   ├── rate_limit.py           # 固定窗口限流（注册接口 IP 维度）
    │   ├── logger.py               # Loguru 日志配置（开发双写 / 生产仅文件）
    │   └── handlers.py             # 全局异常处理器
    ├── enums/
    │   ├── response_code.py        # 业务状态码枚举
    │   └── token_type.py           # JWT 令牌类型枚举（access/refresh）
    ├── schemas/                    # 校验层：Pydantic v2 请求/响应模型
    │   ├── user.py                 # 用户模型
    │   └── auth.py                 # 注册/登录/刷新/令牌模型
    ├── db/                         # 数据库层
    │   ├── base.py                 # SQLAlchemy Declarative Base
    │   ├── database.py             # Engine / Session 工厂 / get_db 依赖
    │   └── models.py               # ORM 模型：User 表定义
    ├── dao/
    │   └── user_dao.py             # 数据访问层：所有数据库操作封装在此
    ├── services/                   # 业务层：业务逻辑 + 密码哈希
    │   ├── user_service.py
    │   └── auth_service.py         # 注册/登录认证/令牌刷新
    └── routers/                    # 路由层
        ├── health.py               # 健康检查路由（/health，不挂鉴权）
        ├── auth.py                 # 认证路由（注册/登录/刷新/当前用户）
        └── v1/
            ├── deps.py             # 公共依赖项：JWT 鉴权 get_current_user 等
            └── users.py            # 用户增删改查路由（统一 JWT 登录鉴权）
```

### 分层职责

- **路由层（routers）**：仅做参数接收、路由分发、异常捕获，不堆砌核心业务逻辑。
- **校验层（schemas）**：Pydantic v2 定义请求/响应模型，路径/查询/请求体全部结构化。
- **业务层（services）**：处理业务逻辑，密码哈希在此层完成，只调用 DAO，不直接操作 Session。
- **数据访问层（dao）**：数据库操作全部封装在此，禁止裸写原生 SQL 拼接。
- **横切基础设施（core / enums / db）**：统一配置、统一响应、全局异常处理、日志、ORM 建模、业务状态码枚举，供各层复用。

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

激活成功后，命令行提示符前会出现 `(.venv)` 前缀。若 PowerShell 提示“禁止运行脚本”，先执行一次：

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

### 虚拟环境注意事项

- **不要直接重命名或移动 `.venv` 目录**：其内部的 `pip.exe` 启动器和激活脚本写死了创建时的绝对路径，改名/移动后会报
  `Fatal error in launcher: Unable to create process ...`。如需迁移，请删除后在新位置重新创建：
  `Remove-Item -Recurse -Force .venv; python -m venv .venv`。
- 安装包优先使用 `python -m pip install ...` 而非裸 `pip`，避免多个 Python 环境时路径串用。
- `.venv` 为本地环境目录，已在 `.gitignore` 中忽略，不会提交到版本库。

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
| POST | `/auth/register` | 用户注册（弱密码校验 + bcrypt 哈希 + IP 限流 5/min） | 否 | 201 |
| POST | `/auth/login` | 登录，返回 Access/Refresh 双令牌 | 否 | 200 |
| POST | `/auth/refresh` | 刷新令牌过期后，用 Refresh Token 换新 Access Token | 否（凭刷新令牌） | 200 |
| GET | `/auth/me` | 获取当前登录用户信息 | 是（JWT） | 200 |
| POST | `/api/v1/users/` | 创建用户 | 是（JWT） | 201 |
| GET | `/api/v1/users/` | 查询用户列表 | 是（JWT） | 200 |
| GET | `/api/v1/users/{user_id}` | 查询单个用户 | 是（JWT） | 200 |
| PUT | `/api/v1/users/{user_id}` | 更新用户 | 是（JWT） | 200 |
| DELETE | `/api/v1/users/{user_id}` | 删除用户 | 是（JWT） | 200 |

> **鉴权白名单**：`/health`、文档接口与 `/auth/register`、`/auth/login`、`/auth/refresh` 不挂登录鉴权，供监控探活与匿名认证使用；
> 其余业务接口（含全部 `/api/v1/*`）统一要求登录，在请求头携带 `Authorization: Bearer <access_token>`，
> 缺失/过期/伪造令牌统一返回 401(40104)。

### 鉴权流程（JWT 双令牌 + 无感刷新）

1. `POST /auth/login` 登录成功，拿到 `access_token`（默认 30 分钟）与 `refresh_token`（默认 7 天）；
2. 后续业务请求在请求头携带 `Authorization: Bearer <access_token>`；
3. 访问令牌过期时接口返回 401(40104)，前端调用 `POST /auth/refresh`（请求体携带 `refresh_token`）换取新的访问令牌；
4. 用新令牌自动重试原请求，全程无需用户重新登录；刷新令牌也失效（40105）时再跳转登录页。

### 请求示例

```powershell
# 1. 登录获取令牌
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/login" `
  -Method Post -ContentType "application/json" `
  -Body '{"username":"alice","password":"Goodpass1"}'

# 2. 携带访问令牌调用受保护接口
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/users/" `
  -Method Post -ContentType "application/json" `
  -Headers @{ "Authorization" = "Bearer $($login.data.access_token)" } `
  -Body '{"username":"bob","password":"secret123"}'

# 3. 访问令牌过期后，用刷新令牌换新
Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/refresh" `
  -Method Post -ContentType "application/json" `
  -Body (@{ refresh_token = $login.data.refresh_token } | ConvertTo-Json)
```

## 七、统一响应约定（双层状态码）

项目采用 **HTTP 状态码 + 业务码** 双层设计：

- **HTTP 状态码**：按真实语义返回，前端可直接用于请求成败判断、监控告警。
- **响应体 `code`**：5 位业务码，前三位与 HTTP 状态码对齐，后两位做业务细分（同为 404 可区分"用户不存在/订单不存在"）。

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
| 成功 | 200 / 201 | 0 | 用户创建成功 |
| 用户名重复 | 400 | 40001 | 用户名已存在 |
| 用户名或密码错误 | 401 | 40103 | 用户名或密码错误 |
| 缺失/过期/伪造访问令牌 | 401 | 40104 | 访问令牌无效或已过期 |
| 刷新令牌无效或已过期 | 401 | 40105 | 刷新令牌无效或已过期 |
| 用户不存在 | 404 | 40401 | 用户不存在 |
| 路由不存在 | 404 | 404 | 请求的资源不存在 |
| 请求参数校验失败 | 422 | 42200 | 字段【username】字段长度不能小于限制值 |
| 健康检查数据库不可用 | 503 | 50300 | 服务异常：数据库不可用 |
| 系统内部错误 | 500 | 50000 | 系统繁忙，请稍后再试 |

### 错误响应示例

```json
{
  "code": 40401,
  "message": "用户不存在",
  "data": null,
  "detail": { "path": "/api/v1/users/999", "method": "GET", "query_params": {} }
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

## 九、安全说明

- **密码哈希**：`app/security.py` 使用 bcrypt 算法，存储时不保留明文。
- **登录鉴权（JWT）**：`app/core/jwt.py` 基于 PyJWT 签发/校验 Access/Refresh 双令牌（HS256 验签，载荷含 sub/username/type/exp/jti，两类令牌严格隔离不可混用）；`app/routers/v1/deps.py` 的 `get_current_user` 依赖在业务路由组（`/api/v1/*`）统一挂载，未登录请求一律 401(40104)；签名密钥只从配置层（`JWT_SECRET_KEY` 环境变量）读取，业务层不写死。
- **敏感配置**：`.env.*` 包含数据库账号与密钥，已由 `.gitignore` 忽略，禁止提交；生产部署必须替换默认值。
- **响应脱敏**：响应模型 `UserResponse` 仅暴露 `id` 与 `username`，不返回密码字段。
- **健康检查脱敏**：`/health` 接口在数据库不可用时只返回 `database=fail` 布尔状态，异常原始信息（连接串、驱动报错）仅写入 `logs/error.log`，不回传给调用方，避免敏感信息外泄。
- **日志脱敏**：所有 sink 强制 `diagnose=False`，异常堆栈不打印局部变量值；生产环境关闭控制台 sink，仅落盘到文件，减少敏感信息外露面。
- **统一异常处理**：`app/core/handlers.py` 全局捕获业务/系统/参数/框架异常，系统错误堆栈仅写入日志文件（`logs/error.log`），对外只返回通用提示与请求定位信息。

## 十、冒烟测试

测试代码位于 [`tests/`](tests/)，使用 `pytest` + `httpx`（通过 `starlette.testclient.TestClient`）验证接口核心链路，不依赖外部 MySQL 服务。

### 测试策略

- **数据库隔离**：`tests/conftest.py` 用 SQLite 内存数据库 + `StaticPool` 替代 MySQL，所有 Session 共享同一连接，测试不污染真实数据库。
- **依赖覆写**：仅覆写 `get_db`，无需真实 MySQL；JWT 鉴权不绕过，用例通过真实"注册→登录"获取访问令牌后携带 Bearer 头访问业务接口，鉴权链路被真实覆盖。
- **用例隔离**：每个用例执行后自动清空所有表数据并重置限流器，保证用例间互不影响。

### 覆盖范围

| 分组 | 用例数 | 覆盖内容 |
| --- | --- | --- |
| 健康检查 | 2 | `/health` 服务存活 + 数据库连通性；`/docs`、`/redoc`、`/openapi.json` 文档可访问性 |
| 用户 CRUD | 5 | 登录获取 JWT → 创建 → 查询列表 → 查询详情 → 更新 → 删除全链路 |
| 登录鉴权 | 5 | 用户接口五种 HTTP 方法未登录统一 401(40104) |
| 登录/JWT | 18 | `test_auth_login.py`：登录、令牌载荷、`/auth/me` 保护、刷新换新、过期自动刷新重试闭环 |
| 异常分支 | 7 | 用户不存在 404、用户名重复 400、密码/用户名过短 422、缺字段 422、更新/删除不存在 404 |
| 注册/限流 | 11 | bcrypt 哈希入库、弱密码校验 400、重复用户名 400、注册限流 429 |

### 运行测试

```powershell
# 激活虚拟环境后执行
pytest tests/ -v
```

> 真实 MySQL 连通性验证不在冒烟测试范围内，由 `/health` 接口在真实运行时承担：启动应用后访问 `http://localhost:8000/health`，数据库异常时返回 503。
