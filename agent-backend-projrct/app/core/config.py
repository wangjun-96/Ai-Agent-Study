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
    # 实际上传文件按 uploads/{user_id}/ 分用户目录存放
    UPLOAD_DIR: str = "uploads"
    # 上传文件访问 URL 前缀，与 main.py 中 StaticFiles 挂载路径保持一致
    UPLOAD_URL_PREFIX: str = "/uploads"
    # 单个上传文件大小上限（字节），默认 10MB，超限返回业务错误 40004
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024

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
