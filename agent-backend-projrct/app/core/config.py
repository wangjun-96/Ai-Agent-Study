"""统一配置层：环境变量分层管理（开发 / 生产）。

设计要点：
1. 通过系统环境变量 APP_ENV（development / production）决定加载哪一份环境文件，
   默认 development，业务代码不随环境变化。
2. 使用 python-dotenv 把对应 .env 文件加载进环境变量，再由 pydantic-settings
   做结构化校验，数据库地址、密钥、日志级别等敏感/环境相关配置全部从配置层读取，
   业务层只允许使用 ``settings``，禁止硬编码。
3. 优先级：系统环境变量 > .env.{APP_ENV} 文件 > 代码默认值，
   生产环境可直接由部署平台注入环境变量覆盖文件内容。
"""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（app/core/config.py 向上三级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 支持的运行环境
ENV_DEVELOPMENT = "development"
ENV_PRODUCTION = "production"
_SUPPORTED_ENVS = (ENV_DEVELOPMENT, ENV_PRODUCTION)

# 当前运行环境：由系统环境变量 APP_ENV 指定，默认开发环境
APP_ENV = os.getenv("APP_ENV", ENV_DEVELOPMENT).strip().lower()
if APP_ENV not in _SUPPORTED_ENVS:
    raise ValueError(
        f"不支持的 APP_ENV={APP_ENV}，仅支持：{', '.join(_SUPPORTED_ENVS)}"
    )

# 当前环境对应的环境变量文件：项目根目录下 .env.development / .env.production
ENV_FILE = PROJECT_ROOT / f".env.{APP_ENV}"

# 加载环境文件；override=False 保证已存在的系统环境变量优先（容器/CI 注入不被覆盖）
load_dotenv(ENV_FILE, override=False, encoding="utf-8")


class Settings(BaseSettings):
    """应用配置：从环境变量与 .env 文件统一读取，禁止在业务层硬编码。"""

    # 运行环境
    APP_ENV: str = APP_ENV
    # 应用名称（Swagger 标题等使用）
    APP_NAME: str = "用户管理 API"

    # MySQL 连接串，形如：mysql+pymysql://user:password@host:port/database
    MYSQL_URL: str

    # JWT 签名密钥：只允许从环境变量/配置层注入，禁止在业务代码中硬编码；
    # HS256 要求密钥具备足够长度与随机性（至少 32 字符），生产环境必须替换为高强度随机串
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="JWT 签名密钥")
    # JWT 签名算法，默认 HS256（HMAC + SHA-256，对称加密，签发与校验共用同一密钥）
    JWT_ALGORITHM: str = "HS256"
    # 访问令牌（Access Token）有效期（分钟）：短期有效，过期后用刷新令牌静默换新
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # 刷新令牌（Refresh Token）有效期（天）：长期有效，仅用于换取新的访问令牌
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 日志级别：开发环境建议 DEBUG，生产环境建议 INFO
    LOG_LEVEL: str = "INFO"
    # 日志文件保留时长，loguru retention 语义，如 "30 days"
    LOG_RETENTION: str = "30 days"
    # 是否回显 SQL 语句，开发排障可置 true，生产必须 false
    SQL_ECHO: bool = False

    # 注册接口限流：固定窗口内单个 IP 的最大请求次数（默认 5 次/分钟）
    REGISTER_RATE_LIMIT: int = 5
    # 注册接口限流窗口大小（秒）
    REGISTER_RATE_WINDOW_SECONDS: int = 60
    # 可信反向代理跳数：0=直连不信任 X-Forwarded-For（防伪造绕过限流）；
    # 单层 Nginx/网关部署填 1，两层代理填 2
    TRUSTED_PROXY_HOPS: int = 0

    # 文件上传：本地存储根目录（相对路径相对于项目根目录解析），
    # 实际上传文件按 uploads/{user_id}/ 分用户目录存放。
    # 仅旧本地逻辑 file_service.py 使用（教学保留，运行逻辑已切换至 MinIO）
    UPLOAD_DIR: str = "uploads"
    # 上传文件访问 URL 前缀，与 main.py 中 StaticFiles 挂载路径保持一致
    UPLOAD_URL_PREFIX: str = "/uploads"
    # 单个上传文件大小上限（字节），默认 100MB，支持音频/视频等大文件上传
    UPLOAD_MAX_SIZE: int = 100 * 1024 * 1024

    # MinIO 对象存储连接配置（敏感信息从环境变量注入，禁止硬编码到业务层）
    # 服务地址，形如 host:port（不含 scheme）
    MINIO_ENDPOINT: str = "localhost:9000"
    # 访问密钥
    MINIO_ACCESS_KEY: str = "minioadmin"
    # 秘密密钥
    MINIO_SECRET_KEY: str = "minioadmin"
    # 资源桶名
    MINIO_BUCKET: str = "ai-resource"
    # 是否启用 HTTPS
    MINIO_SECURE: bool = False
    # 预签名下载 URL 有效期（秒），供前端临时访问私有桶对象
    MINIO_PRESIGN_EXPIRY_SECONDS: int = 2 * 60 * 60

    # 资源过期策略：长过期场景（storage_scene=0）保留天数，默认 1 个月
    RESOURCE_LONG_EXPIRE_DAYS: int = 30
    # 资源过期策略：短过期场景（storage_scene=1）保留小时数，默认 2 小时
    RESOURCE_SHORT_EXPIRE_HOURS: int = 2

    # ------------------------- 大模型（LLM）接入配置 -------------------------
    # 模型提供方：openai / deepseek / dashscope / custom（均按 OpenAI 兼容协议接入）
    LLM_PROVIDER: str = "openai"
    # 模型 API Key：敏感信息只走环境变量，未配置时对话接口返回明确错误提示
    LLM_API_KEY: str = ""
    # 接入地址（Base URL）：为空时使用 provider 默认地址，custom 场景必须显式配置
    LLM_BASE_URL: str = ""
    # 模型名称：为空时使用 provider 默认模型
    LLM_MODEL: str = ""
    # 采样温度：0 更确定，1 更发散
    LLM_TEMPERATURE: float = 0.7
    # 单次回复最大 token 数
    LLM_MAX_TOKENS: int = 2048
    # 请求超时（秒）
    LLM_TIMEOUT: int = 60

    # ------------------------- 记忆层（短期记忆）配置 -------------------------
    # 上下文回带的最近对话轮数（一轮 = 一条用户消息 + 一条 AI 回复）
    MEMORY_MAX_TURNS: int = 8
    # 上下文总字符预算：超出后从最旧的一轮开始裁剪，避免超长提示词
    MEMORY_MAX_CHARS: int = 8000

    # ------------------------- Redis 配置 -------------------------
    # 是否启用 Redis（关闭后提示词模板/工作记忆自动降级为数据库直读）
    REDIS_ENABLED: bool = True
    # Redis 服务地址
    REDIS_HOST: str = "127.0.0.1"
    # Redis 端口
    REDIS_PORT: int = 6379
    # Redis 逻辑库编号
    REDIS_DB: int = 0
    # Redis 密码，无密码时为空
    REDIS_PASSWORD: str = ""
    # 连接/读写超时（秒）
    REDIS_TIMEOUT: int = 3

    # 提示词模板生效版本缓存 Key（Redis Hash：field={agent}:{scene}，value=模板 JSON）
    PROMPT_CACHE_KEY: str = "prompt:templates:active"

    # ------------------------- 用户画像（提示词变量） -------------------------
    # 提示词变量注入：单个变量值的最大长度，超长截断，防止提示词被撑爆
    PROMPT_VAR_MAX_LENGTH: int = 500
    # 提示词变量注入：变量值总长度上限，超出后拒绝填充
    PROMPT_VARS_TOTAL_MAX_LENGTH: int = 4000

    # ------------------------- RAG（知识库向量检索） -------------------------
    # DashScope 文本向量化 API Key（text-embedding-v4），为空时入库/检索给出明确错误
    DASHSCOPE_API_KEY: str = ""
    # Qdrant 服务地址与端口（远端 Server 模式使用）
    QDRANT_HOST: str = "127.0.0.1"
    QDRANT_PORT: int = 6333
    # Qdrant 本地文件模式路径：非空时使用嵌入式存储（无需部署 Qdrant 服务）
    QDRANT_LOCAL_PATH: str = ""
    # 知识库向量集合名
    QDRANT_COLLECTION: str = "knowledge_chunks"
    # 向量化模型与维度（DashScope text-embedding-v4）
    RAG_EMBEDDING_MODEL: str = "text-embedding-v4"
    RAG_EMBEDDING_DIM: int = 1024
    # 检索默认条数与相似度阈值（低于阈值丢弃）
    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.4
    # 切片大小、重叠长度与单条原文最大长度（检索注入用）
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_CHUNK_TEXT_MAX: int = 800

    # ------------------------- 扫描版 PDF OCR（火山引擎） -------------------------
    # 火山引擎访问密钥（Access Key / Secret Key），为空时扫描件解析给出明确错误
    VOLC_ACCESS_KEY: str = ""
    VOLC_SECRET_KEY: str = ""
    # 火山引擎区域
    VOLC_REGION: str = "cn-north-1"

    # ------------------------- 工作记忆（Redis） -------------------------
    # 工作记忆 Key 过期时间（秒），每次读写自动续期，默认 8 小时
    WORKING_MEMORY_TTL_SECONDS: int = 8 * 60 * 60
    # 工作记忆原始消息总字符阈值，超过触发总结与裁剪
    WORKING_MEMORY_MAX_CHARS: int = 8000
    # 总结后保留的最近消息条数（3 轮 = 6 条）
    WORKING_MEMORY_KEEP_MESSAGES: int = 6
    # 摘要长度上限（字）
    SUMMARY_MAX_CHARS: int = 500

    # ------------------------- 长期记忆（用户画像语义判断） -------------------------
    # 本地向量模型名称（fastembed）
    LONG_TERM_EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    # 语义相似度阈值：达到阈值判定为画像写入意图
    LONG_TERM_SIMILARITY_THRESHOLD: float = 0.62

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略 .env 中未声明的其他变量
        case_sensitive=True,
    )

    @property
    def is_production(self) -> bool:
        """是否为生产环境，便于按环境切换行为。"""
        return self.APP_ENV == ENV_PRODUCTION

    @property
    def upload_root(self) -> Path:
        """上传文件存储根目录绝对路径：相对路径基于项目根目录解析。"""
        path = Path(self.UPLOAD_DIR)
        return path if path.is_absolute() else (PROJECT_ROOT / path)


@lru_cache
def get_settings() -> Settings:
    """获取全局唯一配置实例（缓存，避免重复解析环境变量）。"""
    return Settings()


# 全局配置：业务层统一 ``from app.core.config import settings`` 读取
settings = get_settings()
