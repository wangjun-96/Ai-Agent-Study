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
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 大文本字段类型：生产 MySQL 使用 MEDIUMTEXT（最大约 16MB）；
# 测试环境使用 SQLite 内存库，其方言编译器没有 MEDIUMTEXT，
# 通过 with_variant 在 SQLite 下回退为 TEXT，保证同一份模型两端均可建表
LargeText = MEDIUMTEXT().with_variant(Text(), "sqlite")

# 小整数字段类型：生产 MySQL 使用 TINYINT（资源类型/存储场景/上传用途）；
# SQLite 方言没有 TINYINT，回退为 SmallInteger，保证同一份模型两端均可建表
TinyInt = TINYINT().with_variant(SmallInteger(), "sqlite")

# 自增主键类型：生产 MySQL 使用 BIGINT；SQLite 只有 INTEGER PRIMARY KEY
# 才有 rowid 自增语义（BIGINT 主键不会自动生成 ID），故回退为 Integer
BigIntPrimaryKey = BigInteger().with_variant(Integer(), "sqlite")


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
    - file_extracted_text：从文件中提取的完整文本（对话上下文用），无文件时为空
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
    # 从文件中提取的完整文本（对话上下文用）：仅携带文件的消息有值，其余为空
    file_extracted_text: Mapped[str | None] = mapped_column(
        LargeText, nullable=True, comment="从文件中提取的完整文本（对话上下文用）"
    )
    # 用户消息附件段：仅存 file/image/audio 附件，文本正文走 request_text
    request_segments: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True, comment="用户消息附件段（file/image/audio）"
    )
    # AI 回复附件段：仅存 file/image/audio 附件，文本正文走 response_text
    response_segments: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True, comment="AI回复附件段（file/image/audio）"
    )
    # RAG 参考来源：只存 chunk_id 与 score，知识块原文保存在 knowledge_chunks
    reference_sources: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True, comment="RAG参考来源（chunk_id/score）"
    )
    # AI 回复结构化数据：如测评出题的 quiz JSON，提交评分后清空
    response_payload: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="AI回复结构化数据（如测评题目JSON）"
    )
    # 关联面试记录 ID：仅模拟面试入口消息/面试复盘消息有值，用于前端面试卡片逻辑
    # use_alter=True：与 interviews.message_id 形成循环外键，延迟建表后通过 ALTER 添加约束
    interview_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("interviews.id", use_alter=True),
        nullable=True,
        index=True,
        comment="关联面试记录ID",
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
    - user_id            ：外键关联用户表 ID，面试归属用户，按 interview_id+user_id 查询
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
    # 外键关联用户表 ID：面试归属用户，获取面试记录需 interview_id + user_id 联合查询
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="用户ID",
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


class Resource(Base):
    """资源元数据表：统一管理音频、文件、图片，元数据与文件解耦。

    - 原文件存 MinIO，本表只存元数据；
    - file_hash 为文件内容 MD5，与 user_id 组成联合唯一键，实现用户级去重；
    - storage_scene=2（EXTRACT_ONLY）时不落原文件，不产生本表记录，
      提取文本由调用方写入 chat_messages.file_extracted_text。

    字段：
    - id             ：自增主键
    - resource_type  ：资源类型（0=文件，1=图片，2=音频），见 ResourceType 枚举
    - storage_scene  ：存储场景（0=长过期1个月，1=短过期2小时），见 StorageScene 枚举
    - update_purpose ：上传用途（0=普通资源，1=用户头像），见 UploadPurpose 枚举
    - file_name      ：用户上传原始文件名
    - file_hash      ：文件 MD5，去重核心字段
    - storage_path   ：MinIO 路径，格式 minio://{bucket}/{object_key}
    - user_id        ：上传用户 ID
    - expire_time    ：资源过期时间，null 表示不过期
    - create_time    ：创建时间，数据库自动填充
    - 联合唯一键      ：(file_hash, user_id)，用户 + MD5 去重，数据库兜底
    """

    __tablename__ = "resources"

    # 自增主键（MySQL BIGINT，SQLite 回退 Integer 以支持自增）
    id: Mapped[int] = mapped_column(
        BigIntPrimaryKey,
        primary_key=True,
        autoincrement=True,
        comment="资源主键ID",
    )
    # 资源类型：0=文件，1=图片，2=音频（见 ResourceType 枚举）
    resource_type: Mapped[int] = mapped_column(
        TinyInt, nullable=False, comment="资源类型：0=文件，1=图片，2=音频"
    )
    # 存储场景：0=长过期（1个月），1=短过期（2小时）（见 StorageScene 枚举）
    storage_scene: Mapped[int] = mapped_column(
        TinyInt,
        nullable=False,
        server_default="0",
        comment="存储场景：0=长过期时间（1个月），1=短过期时间（2小时）",
    )
    # 上传用途：0=普通资源，1=用户头像（见 UploadPurpose 枚举）
    update_purpose: Mapped[int] = mapped_column(
        TinyInt,
        nullable=False,
        server_default="0",
        comment="上传用途：0=普通资源，1=用户头像",
    )
    # 用户上传原始文件名
    file_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="用户上传原始文件名"
    )
    # 文件 MD5：去重核心字段
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="文件MD5，去重核心字段"
    )
    # MinIO 对象存储路径：minio://{bucket}/{object_key}
    storage_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="MinIO对象存储路径"
    )
    # 上传用户 ID
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="上传用户ID"
    )
    # 资源过期时间：到期后定时任务先删 MinIO 对象再删元数据；null 表示不过期
    expire_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="资源过期时间"
    )
    # 创建时间：由数据库自动填充当前时间
    create_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    # 联合唯一键：file_hash + user_id，用户级 MD5 去重，并发场景数据库兜底
    __table_args__ = (
        UniqueConstraint(
            "file_hash", "user_id", name="uk_file_hash_user_id"
        ),
    )


class PromptTemplate(Base):
    """提示词模板表：公共模板与私有模板统一存储，版本按 (agent_name, scene) 独立递增。

    规则：
    - 公共模板：agent_name 为空，template_type=2，所有智能体共享；
    - 私有模板：agent_name 有值，template_type=1，仅该智能体使用；
    - 同一 (agent_name, scene) 下只有一条 is_active=1 的生效版本。

    字段：
    - agent_name       ：智能体名称，公共模板为空
    - scene            ：业务场景标识
    - template_type    ：模板类型（1=私有，2=公共），见 TemplateType 枚举
    - template_content ：模板正文（含 {变量} 占位符）
    - variables        ：变量名列表（JSON 字符串）
    - version          ：版本号，同组内自增
    - is_active        ：是否生效版本（0=否，1=是）
    - description      ：版本说明
    - created_at       ：创建时间，Unix 秒时间戳
    """

    __tablename__ = "prompt_templates"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="模板ID")
    # 智能体名称：公共模板留空
    agent_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="智能体名称（公共模板为空）"
    )
    # 业务场景标识，加索引加速按场景组装
    scene: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="业务场景"
    )
    # 模板类型：1=私有，2=公共（见 TemplateType 枚举）
    template_type: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="模板类型：1=私有，2=公共"
    )
    # 模板正文（MEDIUMTEXT，支持长提示词）
    template_content: Mapped[str] = mapped_column(
        LargeText, nullable=False, comment="模板正文"
    )
    # 变量名列表（JSON 字符串，如 ["target_job","weak_topics"]）
    variables: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="变量名列表（JSON字符串）"
    )
    # 版本号：同一 (agent_name, scene) 内自增
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1", comment="版本号"
    )
    # 是否生效版本：0=否，1=是；同组内仅一条为 1
    is_active: Mapped[int] = mapped_column(
        TinyInt,
        nullable=False,
        server_default="0",
        comment="是否生效版本：0=否，1=是",
    )
    # 版本说明
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="版本说明"
    )
    # 创建时间：Unix 秒时间戳
    created_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="创建时间（Unix秒）",
    )

    # 复合索引：按智能体 + 场景 + 版本检索
    __table_args__ = (
        Index("ix_prompt_templates_agent_scene_version", "agent_name", "scene", "version"),
    )


class UserProfile(Base):
    """用户画像表：存储用户背景信息，供提示词变量注入使用。

    字段：
    - user_id        ：用户ID（外键，一人一条画像）
    - target_job     ：目标岗位
    - years_experience：工作经验
    - target_level   ：目标等级
    - target_skills  ：已掌握技能（JSON 数组）
    - weak_topics    ：薄弱点（JSON 数组）
    - created_at     ：创建时间，Unix 秒时间戳
    """

    __tablename__ = "user_profiles"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="画像ID")
    # 用户ID：一人一条画像，联合唯一键保证
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    # 目标岗位
    target_job: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="目标岗位"
    )
    # 工作经验（如「应届」「3年」）
    years_experience: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="工作经验"
    )
    # 目标等级（如「初级」「高级」「专家」）
    target_level: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="目标等级"
    )
    # 已掌握技能（JSON 数组）
    target_skills: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="已掌握技能（JSON数组）"
    )
    # 薄弱点（JSON 数组）
    weak_topics: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="薄弱点（JSON数组）"
    )
    # 学习目标
    learning_goal: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="学习目标"
    )
    # 学习偏好/风格
    learning_style: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="学习风格/偏好"
    )
    # 面试关注方向（JSON 数组）
    interview_focus: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="面试关注方向（JSON数组）"
    )
    # 长期记忆摘要（大文本）
    long_term_summary: Mapped[str | None] = mapped_column(
        LargeText, nullable=True, comment="长期记忆摘要"
    )
    # 创建时间：Unix 秒时间戳
    created_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="创建时间（Unix秒）",
    )

    # 联合唯一键：一个用户仅一条画像
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_user_profiles_user_id"),
    )


class KnowledgeChunk(Base):
    """知识切片表：RAG 切片原文存储，与 Qdrant 向量通过 vector_id 关联。

    字段：
    - resource_id ：关联 resources 表主键（来源文件）
    - user_id     ：归属用户，检索隔离
    - vector_id   ：Qdrant point id（UUID），全表唯一
    - text        ：切片原文（检索命中后回查注入上下文）
    - chunk_index ：切片在文件内的序号
    - char_count  ：切片字符数
    - create_at   ：创建时间，Unix 秒时间戳
    """

    __tablename__ = "knowledge_chunks"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="切片ID")
    # 关联资源表：切片来源文件（resources.id 为 BIGINT，外键类型必须对齐）
    resource_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("resources.id"),
        nullable=False,
        index=True,
        comment="资源ID",
    )
    # 归属用户：检索时按用户隔离
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="用户ID"
    )
    # Qdrant point id（UUID），两侧关联键
    vector_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="向量ID（Qdrant point id）"
    )
    # 切片原文
    text: Mapped[str] = mapped_column(LargeText, nullable=False, comment="切片原文")
    # 切片序号
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="切片序号"
    )
    # 切片字符数
    char_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="切片字符数"
    )
    # 创建时间：Unix 秒时间戳
    create_at: Mapped[int] = mapped_column(
        BigInteger,
        server_default=func.unix_timestamp(),
        nullable=False,
        comment="创建时间（Unix秒）",
    )

    # 复合索引：按资源 + 用户快速回查
    __table_args__ = (
        Index("ix_knowledge_chunks_resource_user", "resource_id", "user_id"),
    )


class WorkflowRun(Base):
    """工作流运行记录表：保存业务快照，LangGraph 执行现场由 checkpoint 保存。

    字段：
    - run_id        ：工作流唯一标识（同时作为 LangGraph thread_id），唯一索引
    - user_id       ：发起用户
    - session_id    ：关联会话
    - workflow_type ：工作流类型（如 learning_quiz）
    - status        ：状态（created/waiting_answer/grading/completed/failed）
    - state_json    ：完整业务状态快照（题目、答案、评分结果）
    - error_message ：失败原因
    - created_at / updated_at / completed_at：Unix 秒时间戳
    """

    __tablename__ = "workflow_runs"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="运行记录ID")
    # 工作流唯一标识（LangGraph thread_id）
    run_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, comment="工作流运行ID"
    )
    # 发起用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID"
    )
    # 关联会话
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False, index=True, comment="会话ID"
    )
    # 工作流类型
    workflow_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="工作流类型"
    )
    # 状态
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="created", comment="运行状态"
    )
    # 业务状态快照
    state_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="业务状态快照"
    )
    # 失败原因
    error_message: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="失败原因"
    )
    # 创建 / 更新 / 完成时间（Unix 秒）
    created_at: Mapped[int] = mapped_column(
        BigInteger, server_default=func.unix_timestamp(), nullable=False, comment="创建时间（Unix秒）"
    )
    updated_at: Mapped[int] = mapped_column(
        BigInteger, server_default=func.unix_timestamp(), nullable=False, comment="更新时间（Unix秒）"
    )
    completed_at: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="完成时间（Unix秒）"
    )

    # 复合索引：按用户 + 状态查询
    __table_args__ = (
        Index("ix_workflow_runs_user_status", "user_id", "status"),
    )

