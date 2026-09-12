"""日志体系：统一使用 Loguru，区分 debug / info / warning / error 级别。

- 控制台输出：彩色等级，便于开发调试。
- 文件输出（logs/app.log）：按天零点滚动、保留期由环境变量 LOG_RETENTION 控制，
  滚动文件自动压缩，用于操作留痕与后端排障。
- 错误文件（logs/error.log）：单独收集 ERROR 及以上级别（含完整堆栈），告警/排障优先查看。
- 标准库 logging 桥接：uvicorn / sqlalchemy / alembic 等三方库日志统一汇入 Loguru，
  全项目禁止 print，关键操作、报错、入参出参统一通过 get_logger 记录。

日志级别与保留期全部来自配置层（.env.development / .env.production），不在业务层硬编码。
"""
import logging
import sys

from loguru import logger

from app.core.config import PROJECT_ROOT, settings

# 日志目录：项目根目录/logs（已在 .gitignore 忽略，不提交版本库）
_LOG_DIR = PROJECT_ROOT / "logs"

# 日志格式：时间 | 级别 | 模块标签 | 定位(文件:函数:行号) | 消息
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[tag]}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[tag]} | "
    "{name}:{function}:{line} | {message}"
)

# 未显式 bind 标签的日志（如三方库桥接日志）使用的默认标签
_DEFAULT_TAG = "app"


class _InterceptHandler(logging.Handler):
    """标准库 logging 桥接处理器：把三方库日志转发给 Loguru 统一输出。"""

    def emit(self, record: logging.LogRecord) -> None:
        # 标准库等级名映射为 Loguru 等级，无法映射时使用数字等级
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 回溯真实调用栈帧，使日志中的 name/function/line 指向最初发起方
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> type(logger):
    """初始化 Loguru 日志配置，返回全局 logger。

    重复调用安全：先清空已有 sink 再重新注册，避免 uvicorn --reload 重复输出。
    返回类型使用 type(logger) 以兼容 loguru 未公开导出 Logger 类型的情况。

    环境策略：
    - 开发环境：控制台 + 文件双写，便于调试；
    - 生产环境：仅文件输出，避免容器控制台日志被 stdout 收集器二次落盘，
      也避免控制台彩色转义符污染收集到的日志文本。
    """
    # 清空 Loguru 默认 handler；设置默认标签，保证桥接日志也有 tag 字段
    logger.remove()
    logger.configure(extra={"tag": _DEFAULT_TAG})

    log_level = settings.LOG_LEVEL.upper()

    # 1. 控制台 sink：仅开发环境启用，彩色输出，DEBUG 级别可看到调试细节
    #    生产环境关闭，避免容器 stdout 收集器与文件双写，减少敏感信息外露面
    if not settings.is_production:
        logger.add(
            sys.stderr,
            level=log_level,
            format=_CONSOLE_FORMAT,
            colorize=True,
            backtrace=True,
            diagnose=False,
        )

    # 2. 全量文件 sink：按天零点滚动，过期自动清理，滚动文件压缩为 zip
    logger.add(
        _LOG_DIR / "app.log",
        level=log_level,
        format=_FILE_FORMAT,
        rotation="00:00",
        retention=settings.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,  # 异步写入，避免磁盘 IO 阻塞业务请求
        backtrace=True,
        # 生产安全：强制 False，不打印异常局部变量值，避免敏感信息泄漏
        diagnose=False,
    )

    # 3. 错误文件 sink：仅记录 ERROR 及以上级别，便于排障与告警接入
    logger.add(
        _LOG_DIR / "error.log",
        level="ERROR",
        format=_FILE_FORMAT,
        rotation="00:00",
        retention=settings.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # 桥接标准库 logging：三方库日志统一走 Loguru 的控制台与文件 sink
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy",
        "alembic",
    ):
        std_logger = logging.getLogger(logger_name)
        std_logger.handlers = [_InterceptHandler()]
        std_logger.propagate = False  # 防止命名 logger 与 root 重复输出

    return logger


def get_logger(name: str | None = None):
    """获取带模块标签的 logger，name 通常传业务模块名（如 user_service）。

    用法：logger = get_logger("user_service")；logger.info("用户创建成功 id={}", uid)
    Loguru 使用 {} 占位符，禁止使用 %s 风格与 print。
    """
    if name:
        return logger.bind(tag=name)
    return logger
