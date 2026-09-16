# 根据{{FastAPI}}初始化项目代码，要求如：

1. 需要创建虚拟环境并激活，安装相关依赖；
2. 按路由层、校验层、业务层、数据库层四层组织代码；
3. 数据库层仅用内存字典模拟，不连接真实数据库；
4. 实现用户信息增删改查接口，用户包含{{id}}、{{username}}、{{password}}字段；
5. 密码使用{{passlib[bcrypt]}}做哈希加密，存储时不保留明文；
6. 复用{{Pydantic(v2)}}的请求/响应参数校验；
7. 代码简洁高效，并合理添加注释；   

## 生成{{FastAPI}}统一错误处理代码

### 核心目标
报错前端中文可读、后端可定位、日志可追溯

### 关键要求

1. 自定义业务/系统两类异常类
2. 标准化响应模型（含code/message/detail）
3. 注册全局异常处理器
4. 在用户信息接口中加上错误处理功能

### 实现步骤

自定义异常→响应模型→日志配置→全局异常处理器→业务示例

# 用FastAPI + SQLAlchemy 2.0 + MySQL 实现用户信息数据建模

1. 定义 User 表（id 自增主键、username 唯一非空、password、 create_time 自动填充当前时间）
2. 配置 MySQL 连接串 {{mysql_url}}；
3. 集成 Alembic 管路表结构变更，支持修改表结构后一键同步数据库。


# 实现环境变量分层管理和日志体系

1. 环境变量分层：支持开发/生产。
2. 敏感信息只走环境变量/配置层，不写死在业务层。
3. 建立日志体系：日志文件用于留痕与排障，避免多余日志，日志记录使用Loguru工具。
4. 最后补齐忽略规则

# 在项目里完善稳定性保障：实现健康检查接口，并补齐基础冒烟测试

要求：
1. 健康检查：实现 ' /health ' 接口，校验服务存活及数据库连通性，异常返回503。
2. 冒烟测试：用 'pytest' + 'httpx' 编写用户接口测试用例。
3. 交付：说明改动文件运行测试命令（‘pytest tests/test_smoke.py -v’ ）。

# 安全实现注册接口，保持代码简洁：
1. 注册接口：新增 /auth/register，复用UserService.create_user
2. 密码加密：bcrypt 哈希加密，禁止明文入库
3. 弱密码校验：黑名单 + 必须字母+数字 +禁止包含用户名
4. 接口限流：固定窗口 + IP 维度，注册 5/min


## 实现登录接口：
- JWT鉴权流程，包括：
    - 登录时使用PyJWT生成访问令牌 （Access Token）和刷新令牌（Refresh Token）。
    - 使用鉴权保护接口，验证请求的合法性。
    - 当访问令牌过期时，自动使用刷新令牌（Refresh Token）获取新的访问令牌，并重试原请求，无需用户手动操作。
- token 密钥必须经过环境变量进行安全存储。

# 创建一个 需要认证 的通用文件上传接口。该接口需 自动判断 文件类型：

- 如果时图片，则保存文件并 更新 用户数据库中的 avatar 字段。
- 如果是文档 ， 则 只保存文件。
- 存储逻辑 ： 文件和保存在按用户 ID 划分的目录中（新建uploads/user_id），并使用文件内容的 MD5 哈希值作为文件名以实现去重。
- 文件上传依赖：python-multipart == 0.0.9

# 请使用 SQLAlchemy 2.0 语法，根据一下信息创建三个 ORM 模型：
 1. 会话表（Session）
    - id 自增主键
    - user_id 外键关联用户表的ID，索引
    - session_model ：整数，非空（注释：0=学习，1=面试，2=笔记）
    - title：字符串(255)，非空，会话标题
    - create_at :Unix 秒时间戳，非空，默认'UNIX_TIMESTAMP()'(会话创建时间)

2. 消息表（chat_messages）
    - id 自增主键
    - user_id 外键关联用户表的ID
    - session_id 外键关联会话表的ID
    - select_model:整数，非空； 选择模式：0=默认，1=知识精讲，2=刷题，3=简历优化，4=模拟面试，5=面试复盘
    - request_id:字符串(64)，非空，索引
    - request_text:MEDIUMTEXT，非空,请求文本
    - response_text:MEDIUMTEXT，非空，响应文本
    - filr_extracted_text, 从文件中提取的完整文本（对话上下文用）
    - create_at :Unix 秒时间戳，非空
    - 要求：在 session_id 与 created_at 上创建复合索引（按会话拉取并按时间排序）

3. 面试记录表（interviews）
    - id 自增主键
    - session_id 外键关联会话表的ID，同一会话/面试场景
    - message_id 外键关联消息表的ID，唯一；指向开启本次模拟面试的入口消息
    - qa_object:JSON，非空；一问一答对象，字段约定见下方示例
    - interview_duration:整数，非空,默认 0；累计面试时长（秒）
    - status:整数，非空,默认 0;索引（0=进行中，1=已完成，2=异常终止）
    - create_at :Unix 秒时间戳，非空，（面试开始时间）
    - update_at :Unix 秒时间戳，非空，（更新面试时间）
    - 要求：在 session_id 与 message_id 上创建复合索引

    'qa_object' 示例（JSON内’created_at’为Unix秒，可与表字段对齐）：
    ‘’'json
    {
        "id":"uuid",
        "question":"...",
        "answer":"...",
        "created_at":1694502400,
    }
    ’‘’



# 创建 资源元数据表：统一管理音频、文件、图片，MD5实现用户级去重

CREATE TABLE `resources` (
    `id` bigint not null AUTO_INCREMENT PRIMARY KEY comment '资源主键ID',
    `resource_type` TINYINT not null comment '资源类型：0=文件，1=图片，2=音频',
    `storage_scene` TINYINT not null default 0 comment '存储场景：0= 长过期时间（1个月），1= 短过期时间（2小时）,2= 只提取内容不存原文件/音频',
    `update_purpose` TINYINT not null default 0 comment '上传用途：0= 普通资源，1= 用户头像',
    `file_name` VARCHAR(255) not null comment '用户上传原始文件名',
    `file_hash` VARCHAR(64) not null comment '文件MD5,去重核心字段',
    `storage_path` VARCHAR(512) not null comment 'MinIO对象存储路径',
    `user_id` bigint not null comment '上传用户ID',
    `expire_time` datetime default null comment '资源过期时间',
    `create_time` datetime DEFAULT CURRENT_TIMESTAMP comment '创建时间',
    unique key `uk_file_hash_user_id` (`file_hash`, `user_id`) comment '用户+MD5联合去重'
) engine=InnoDB default charset=utf8mb4 comment '资源元数据表';

# 请按”元数据与文件解耦“架构，完成 MinIO 对象存储改造。

目标：

- MySQL resources 存元数据；
- MinIO 存原文件；
- /upload/file 接口路径不变。

要求：

1. 保留去重规则： UNIQUE(file_hash, user_id)(代码层可预查，数据库兜底)。
2. 上传改为 MinIO put_object; storage_path 格式：minio://{bucket}/{}/{object_key}
3. storage_scene = 2 : 只提取文件内容，不上传原文件。
4. 新增 upload_purpose 入参（0=general, 1=avatar）,仅 update_purpose = 1 且图片类型时更新 users.avatar 字段。
5. 创建 MinIO 客户端，并在环境变量中配置连接变量。
6. 教学/运行分离：
    - file_service.py 保留旧本地逻辑(不运行)；
    - 新建 upload_service_minio.py 作为运行逻辑；
    - /upload/file 路由切换到 upload_service_minio.py；
7. 新增过期清理：每天03：00扫描expire_time,先删MioIO对象，再删元数据；
8. 更新requirements.txt：添加 minio
9. 代码简洁，指责单一、注释清晰、无冗余代码。