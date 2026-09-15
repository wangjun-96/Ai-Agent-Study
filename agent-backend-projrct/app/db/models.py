"""数据模型层：SQLAlchemy ORM 模型定义。

- 字段注释、索引、关联关系完整书写，禁止裸写原生 SQL 字符串拼接。
- 表结构变更统一通过 Alembic 迁移脚本管理，禁止手动改表。
- 所有模型继承自 Base，统一注册到 Base.metadata，供 Alembic 自动检测。
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 大文本字段类型：生产 MySQL 使用 MEDIUMTEXT（最大约 16MB）；
# 测试环境使用 SQLite 内存库，其方言编译器没有 MEDIUMTEXT，
# 通过 with_variant 在 SQLite 下回退为 TEXT，保证同一份模型两端均可建表
LargeText = MEDIUMTEXT().with_variant(Text(), "sqlite")


class User(Base):
    """用户表。

    字段：
    - id          ：自增主键
    - username    ：用户名，唯一非空，建立索引加速唯一性校验
    - password    ：密码哈希（bcrypt），不保留明文
    - avatar      ：头像访问 URL，注册/上传图片后回写，未设置为空
    - create_time ：创建时间，由数据库 server_default=now() 自动填充
    """

    __tablename__ = "users"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID")
    # 用户名：唯一非空，加索引便于登录与唯一性校验
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="用户名"
    )
    # 密码哈希存储
    password: Mapped[str] = mapped_column(String(128), nullable=False, comment="密码哈希")
    # 头像访问 URL：图片上传接口保存文件成功后回写，未上传头像时为空
    avatar: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="头像访问URL"
    )
    # 创建时间：由数据库自动填充当前时间
    create_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )


class Session(Base):
    """会话表。

    字段：
    - id            ：自增主键
    - user_id       ：外键关联用户表 ID，加索引加速按用户查询会话
    - session_model ：会话模式（0=学习，1=面试，2=笔记），见 SessionModel 枚举
    - title         ：会话标题，非空
    - create_at     ：会话创建时间，Unix 秒时间戳，默认 UNIX_TIMESTAMP()
    """

    __tablename__ = "sessions"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="会话ID")
    # 外键关联用户表 ID，加索引加速按用户查询会话
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    # 会话模式：0=学习，1=面试，2=笔记（见 SessionModel 枚举）
    session_model: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="会话模式：0=学习，1=面试，2=笔记"
    )
    # 会话标题
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="会话标题")
    # 创建时间：Unix 秒时间戳，默认 UNIX_TIMESTAMP()
    create_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="会话创建时间（Unix秒）",
    )


class ChatMessage(Base):
    """消息表。

    字段：
    - id            ：自增主键
    - user_id       ：外键关联用户表 ID
    - session_id    ：外键关联会话表 ID
    - select_model  ：选择模式（0=默认，1=知识精讲，2=刷题，3=简历优化，4=模拟面试，5=面试复盘）
    - request_id    ：请求唯一标识，加索引加速按请求追踪
    - request_text  ：请求文本（MEDIUMTEXT，支持大文本存储）
    - response_text ：响应文本（MEDIUMTEXT，支持大文本存储）
    - create_at     ：消息创建时间，Unix 秒时间戳
    - 复合索引       ：(session_id, create_at)，按会话拉取消息并按时间排序
    """

    __tablename__ = "chat_messages"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="消息ID")
    # 外键关联用户表 ID
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="用户ID",
    )
    # 外键关联会话表 ID
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sessions.id"),
        nullable=False,
        comment="会话ID",
    )
    # 选择模式：0=默认，1=知识精讲，2=刷题，3=简历优化，4=模拟面试，5=面试复盘（见 SelectModel 枚举）
    select_model: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="选择模式：0=默认，1=知识精讲，2=刷题，3=简历优化，4=模拟面试，5=面试复盘",
    )
    # 请求唯一标识，加索引加速按请求追踪
    request_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="请求ID"
    )
    # 请求文本（MySQL 为 MEDIUMTEXT，SQLite 测试库回退为 TEXT）
    request_text: Mapped[str] = mapped_column(
        LargeText, nullable=False, comment="请求文本"
    )
    # 响应文本（MySQL 为 MEDIUMTEXT，SQLite 测试库回退为 TEXT）
    response_text: Mapped[str] = mapped_column(
        LargeText, nullable=False, comment="响应文本"
    )
    # 创建时间：Unix 秒时间戳，默认 UNIX_TIMESTAMP()
    create_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="消息创建时间（Unix秒）",
    )

    # 复合索引：session_id + create_at，按会话拉取消息并按时间排序
    __table_args__ = (
        Index("ix_chat_messages_session_id_create_at", "session_id", "create_at"),
    )


class Interview(Base):
    """面试记录表。

    字段：
    - id                 ：自增主键
    - session_id         ：外键关联会话表 ID，同一会话/面试场景
    - message_id         ：外键关联消息表 ID，唯一，指向开启本次模拟面试的入口消息
    - qa_object          ：一问一答 JSON 对象，字段约定：{id, question, answer, created_at}
    - interview_duration ：累计面试时长（秒），默认 0
    - status             ：面试状态（0=进行中，1=已完成，2=异常终止），默认 0，加索引
    - create_at          ：面试开始时间，Unix 秒时间戳
    - update_at          ：更新面试时间，Unix 秒时间戳
    - 复合索引            ：(session_id, message_id)
    """

    __tablename__ = "interviews"

    # 自增主键
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="面试记录ID"
    )
    # 外键关联会话表 ID，同一会话/面试场景
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sessions.id"),
        nullable=False,
        comment="会话ID",
    )
    # 外键关联消息表 ID，唯一，指向开启本次模拟面试的入口消息
    message_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_messages.id"),
        unique=True,
        nullable=False,
        comment="入口消息ID",
    )
    # 一问一答 JSON 对象，字段约定：{id, question, answer, created_at}
    qa_object: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="问答对象"
    )
    # 累计面试时长（秒），默认 0
    interview_duration: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="累计面试时长（秒）"
    )
    # 面试状态：0=进行中，1=已完成，2=异常终止（见 InterviewStatus 枚举），加索引
    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        index=True,
        comment="面试状态：0=进行中，1=已完成，2=异常终止",
    )
    # 面试开始时间：Unix 秒时间戳，默认 UNIX_TIMESTAMP()
    create_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="面试开始时间（Unix秒）",
    )
    # 更新面试时间：Unix 秒时间戳，默认 UNIX_TIMESTAMP()
    update_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="更新面试时间（Unix秒）",
    )

    # 复合索引：session_id + message_id
    __table_args__ = (
        Index("ix_interviews_session_id_message_id", "session_id", "message_id"),
    )
