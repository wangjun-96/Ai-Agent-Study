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


# 请在现有 FastAPI 项目中实现并完善会话与聊天接口，严格遵循一下语义与约束：

## 核心语义

1. `ChatMessage.request_text/response_text` 是聊天正文主字段；
2. `reqquest_segments/response_segments` 只存附件段（`file/image/audio`）;
3. 用户提问可带附件；AI 回复可带文本或者附件（文本进入 `response_text`，附件进入 `response_segments`）。
4. 聊天消息返回需包含`status`与`interview_id`,用于前端面试卡片逻辑；
5. `interview`表包含`user_id`字段，获取面试记录需要根据`interview_id`+`user_id`进行查询。interview表新增user_id字段

## 需要实现/确认的接口

1. `GET/sessions?page=&page_size=`：会话列表分页（按当前用户）
2. `POST/sessions`：创建会话主题（title+session_model）
3. `PUT/sessions/{session_id}`：编辑会话标题
4. `DELETE/sessions/{session_id}`：删除会话(级联删除)
    - 删除 session
    - 删除 session 下 `Chat_Message`
    - 删除关联 `interview`
    - 解析消息 segments 收集 `resource_id`
    - 删除关联 `resources`中文件元信息与对象存储文件
5. `GET/sessions/{session_id}/messages?page=&page_size=`：分页获取聊天信息
    - 返回： `request_text/response_text`+`request_segments/response_segments`+`status/interview_id/created_at`
6. `GET/interviews/{interview_id}`：按`interview_id`获取面试详情文本（含`qa_object`）

# 为消息表添加字段

 ## 用户消息 
    - request_segments:Mapped[List[dict]]= mapped_column(JSON)
 ## AI消息
    - response_segments:Mapped[List[dict]]= mapped_column(JSON)
## 面试记录id 
    - interview_id:Mapped[int] = mapped_column(nullable=True)
### response_segments示例
    “response_segments”:[
        {
            "type":"image",
           "url":"https://example.com/image.jpg",
           "name":"image.jpg" 
        },
    ],"interview_id":123456

# 请按“三层架构”实现AI聊天流式响应：

目标：

- 实现接口：`POST /sessions/{session_id}/stream-chat`（SSE）

架构要求：

## 通过 langchain 实现下面三层功能：

1. 模型层（llm.py）：只负责 provider -> 模型实例
2. 提示词层（prompt_layer.py）：只负责 Prompt + 链路组装
3. 记忆层（memory.py）：负责从数据库查询多轮历史对话记录，构建并拼接成最终的上下文（Context），然后再发送给大模型。


## 核心需求

FastAPI 中实现提示词版本管理：支持多智能体、公共模板、一键回滚、Redis缓存。

### 数据表 (PromptTemplate)

- **PromptTemplate 表**：
  - agent_name: VARCHAR(64) NULL（公共模板此字段为空）
  - scene: VARCHAR(64) NOT NULL
  - template_type: INT（1=私有, 2=公共）
  - template_content: MEDIUMTEXT
  - variables: VARCHAR(512)（JSON格式变量列表）
  - version: INT（整数自增）
  - is_active: INT（0/1，控制生效版本）
  - description: VARCHAR(255)（版本说明）
  - created_at: BIGINT

### 关键规则

- 公共模板：agent_name=NULL, template_type=2
- 私有模板：agent_name有值, template_type=1
- 同一(agent_name,scene)下版本独立
- 同一(agent_name,scene)下仅一条is_active=1

### 服务类 (PromptTemplateManager)

实现计算下一版本、启动加载模板到Redis（私有Key为{agent}:{scene}，公共Key为__common__:{scene}）、从Redis读取模板、拼接公共和私有模板、以及支持一键回滚等核心功能。

### API端点 (4个)

- GET /prompt/templates/{agent_name}/{scene}
- POST /prompt/rollback（body: template_id）
- GET /prompt/config/agents

```
### 配置
- AGENT_CONFIG：7个智能体映射
- Redis：支持host, port, db, password
- 缓存Key：prompt:templates:active

# 提示词变量注入设计思想

## 1. 数据存储层
创建 user_profiles 表存储用户背景：
 - id: 主键
 - user_id: 用户ID（外键）
 - target_job: 目标岗位
 - years_experience: 工作经验
 - target_level: 目标等级
 - target_skills: 已掌握技能（JSON数组）
 - weak_topics: 薄弱点（JSON数组）
 - created_at: 创建时间戳

## 2. 提示词拼接设计
**分层思想**：公共模板（通用规则）+ 私有模板（Agent指令）+ 动态注入用户信息变量 = 完整提示词
- 版本控制：每个Agent可独立更新

## 3. 提示词注入设计  
**三层处理流程**：
1. 验证层 - 安全检查（防注入、长度限制）
2. 转换层 - 数据格式化（数组转文本、默认值处理）
3. 填充层 - 占位符替换（{target_job} → 实际值）

# 实现 RAG 文件向量化入库

新建 app/rag/core.py，对外只暴露 `ingest_file`。

流水线：解析 → 清洗 → 分类 → 分块 → 向量化 → 写 Qdrant。

## 要求
1. **解析**：PDF(PyPDF2) / DOCX(python-docx) / TXT，字典分派；不支持类型抛异常。
2. **清洗**：去零宽字符、合并空白、压缩多换行、删独立页码行。
3. **分类**：resume / study_material / general，按关键字计分，显式值优先。
4. **分块**：滑动窗口 size=500、overlap=50，回退到句子终止符（。！？\n）切分，MD5 去重。
5. **向量化**：DashScope `text-embedding-v4`，维度 1024，每批 10 条，按 text_index 对齐顺序。
6. **写库**：Qdrant collection=`knowledge_chunks`，余弦距离，不存在自动建；point.id=uuid4，payload 含 text/user_id/doc_category/file_name/chunk_index。

## 约束
- 配置走 settings（dashscope_api_key、qdrant_host、qdrant_port）
- 单文件聚合，不过度抽象



背景：app/rag/core.py 用 PyPDF2 解析 PDF，扫描版抽不出文字。

请升级 PDF 解析链路：

1. 解析器替换：PyPDF2 → pypdfium2
。requirements.txt 同步
增删，并加 volcengine SDK。，pillow

2. 扫描版判定：在 _parse_pdf 里先用 pypdfium2 抽文字，平均每页字符数
   低于 20 视为扫描件，走 OCR 兜底；否则直接返回。

3. OCR 单独成文件 app/rag/ocr.py，对外只暴露 ocr_pdf(path)。内部三步：
   pypdfium2 按 150 DPI 渲染每页为 PNG → base64 上送 VisualService 的
   OCRNormal → 取 data.line_texts 按行拼接为全文。

4. 凭证：settings.py 新增 volc_access_key / secret_key / region。



目标：把现有文本切片升级为递归智能切片，并增强 Word 文档结构识别，
代码做最小改造，只修改 core.py

具体要求：
1. 引入 RecursiveCharacterTextSplitter。
2. DOCX 提取时识别 Heading 1 / Heading 2 / Heading 3，并分别注入 # / ## / ### 标题标记。
3. 新的切片分隔符按以下优先级：
   \n### 、\n## 、\n# 、\n\n、\n、。、！、？、；、，、空格、字符兜底。
4. 其余的业务逻辑都保留。


优化切片数据的存储方式：

**核心功能：切片数据分两份存储**
- Qdrant：只存向量 + 检索过滤字段（user_id、doc_category 等），不存原文
- MySQL knowledge_chunks：存切片原文（text、chunk_index、char_count），关联已有的 resources 表

两边通过同一个 vector_id 关联：入库时生成 UUID 同时写入 Qdrant Point id 和 MySQL vector_id 字段。

**实现要点**
-创建一个 chunk_store.py 需实现：save_chunks 
- RagService 增加 db 和 resource_id 入参，写完 Qdrant 后调 save_chunks 再 commit

请结合我的项目现有代码实现。

# 实现 RAG 检索模块：用户提问 → 找到最相关的知识库片段

核心思路：
检索时把问题也变成向量，
在 Qdrant 里找距离最近的 N 个片段（向量空间找近邻）。

原文回查：fetch_chunks_by_vector_ids 已在 chunk_store.py 实现，用它回查 MySQL

新建 app/rag/retriever.py，对外只暴露一个函数 search_similar_chunks，
检索必须带 user_id 过滤。
- 分数阈值过滤（低于 0.4 丢弃）
- 单条 text 截断（超过 800 字截断）

# 请实现 RAG 对话链路：意图判断、资料注入、来源展示。

目标：
用户提问时按需检索知识库，把命中的知识片段注入本轮上下文；前端能看到回答来源，刷新历史后仍能回显，但数据库不重复保存知识块全文。

实现要点：
1. 用 should_retrieve(request_text) 做轻量意图判断，跳过空输入、极短输入、确认语、礼貌语和推进语。
2. 需要检索时调用 search_similar_chunks(query, user_id, db, top_k=3)，按 user_id 隔离资料，得到 retrieved_chunks。
3. 用 format_retrieved_chunks(retrieved_chunks) 生成 retrieved_text，并作为 rag_context 拼到本轮用户问题前。
4. build_rag_system_prompt 只补充 RAG 回答规则。
5. SSE done 返回完整 sources：chunk_id、resource_id、chunk_index、file_name、score、text。
6. 在 ChatMessage 表中新增 reference_sources 字段，用来存储 ：chunk_id、score
7. 历史消息接口根据 reference_sources 回查 knowledge_chunks 和 resources，重新拼出 sources；知识块已删除时返回“该参考片段已被删除”。

验收标准：
该检索的问题能基于资料回答；无意义输入会跳过检索；前端和历史消息都能展示 sources；数据库不重复保存知识块全文。

#封装短期记忆的读取逻辑
功能目标 ：
实现一个专门读取短期记忆的服务，把“怎么查历史”的逻辑和主业务流程分开。

设计思路 ：
创建一个 InstantMemory 类，它负责从数据库查询最近的聊天记录，并按字符预算做裁剪，最后转换成 LangChain 能识别的消息格式。再用一个 MemoryService 作为统一入口，为后续扩展工作记忆和长期记忆预留位置。

重点函数/修改 ：
在 app/services/memory_service.py 中实现 InstantMemory.load() 方法，核心逻辑是： 先按 create_at 倒序查最近 8轮 → 再用 _fit_char_budget 做字符裁剪 → 最后调用 build_chat_history_from_rows 格式化输出 。

# 任务：构建工作记忆模块

**目标文件：** `app/services/memory_service.py`


## 一、整体思路

- **读的时候**：优先从 Redis 读取工作记忆（原文 + 摘要）。如果 Redis 无数据，则从 MySQL 加载历史作为冷启动。
- **写的时候**：追加新对话。当总长度超过阈值时，同步触发总结，并裁剪原文。


## 二、读取：Redis 优先，MySQL 兜底
需要将 redis 客户端封装成一个文件，方便调用
在 `MemoryService.load_context()` 中：

1.  先调用 `WorkingMemory.get()` 从 Redis 读数据 (`raw` 和 `summary`)。
2.  如果 `raw` 有内容，直接使用。
3.  如果 `raw` 为空（新会话、过期或 Redis 故障），则回退到 `InstantMemory` 从 MySQL 加载历史记录。

## 三、写入与总结：

在 `WorkingMemory.append_turn()` 中：

1.  AI 回答完后，将本轮的用户和 AI 消息追加到 `raw` 数组中。
2.  计算 `raw` 中所有消息的总字符数。
3.  如果总字符数超过 (8000字)，则执行总结：
    a.  保留最近的  (6条) 消息在 `raw` 中。
    b.  将更早的消息和旧摘要一起传入 `quick_summarize` 生成新摘要。
    c.  将新的 `raw` (6条消息) 和新摘要写回 Redis。
4.  如果未超过字数限制，则只更新 `raw`，摘要不变。

## 四、关键设计要点

1.  **读降级**：Redis 无数据时，自动从 MySQL 加载，保证对话连续性。
2.  **摘要限长**：通过提示词引导模型将摘要控制在 500 字以内，保证摘要信息的完整性。
3.  **按需总结**：只有在历史消息累积到一定长度时才触发总结，避免频繁调用 LLM。
4.  **Redis 异常不抛错**：所有 Redis 操作捕获异常后返回空值，保证主流程的稳定性。


## 五、需要实现的方法

- `WorkingMemory.get()`：读取 `raw` + `summary`，自动续期，异常时返回空结构。
- `WorkingMemory.append_turn()`：追加消息，并在需要时同步触发总结和裁剪。
- `MemoryService.load_context()`：实现 Redis 优先、MySQL 兜底的加载策略。


## 六、约束

- 摘要函数：`app.services.memory_service.quick_summarize`
- 阈值：保留最近 3 轮对话（6条消息），原始消息总长超过 8000 字符时触发总结。
- 摘要上限：500 字
- TTL：8 小时，每次读写后自动续期。
- Key 格式：`memory:working:{user_id}:{session_id}`

# 实现长期记忆功能，

## 任务一：扩展用户画像数据模型
在 UserProfile ORM 模型中新增四个字段：
- learning_goal: 字符串，可为空
- learning_style: 字符串，可为空
- interview_focus: JSON 数组，可为空
- long_term_summary: 长文本，可为空
同步更新 user_profile_service.py 中的 create_or_update 和 get_profile_dict 方法支持这四个字段。

## 任务二：实现 LongTermMemory 服务类
新建 long_term_memory.py，实现以下能力：
1. load_memory_context(user_id, ...) → 从数据库读取用户画像，返回格式化的 memory_text 字符串
2. should_write(text, user_id) → 使用 fastembed + BAAI/bge-small-zh-v1.5 做语义相似度判断，
   判断用户消息是否属于"画像写入意图"（即用户在表达关于自己目标、偏好、方向的信息）
3. submit_profile_update_async(user_id, request_text, context) → 在后台线程中调用大模型，
   从对话上下文抽取结构化用户信息，更新 UserProfile 对应字段

## 任务三：MemoryService 接入长期记忆
在 memory_service.py 的 load_context 方法中：
- 初始化时挂载 LongTermMemory
- 调用 load_memory_context 获取画像文本
- 如果有画像文本，将其包装为 LangChain SystemMessage 插入 history_messages 列表最前面
- 新增 enable_long_term 开关参数，默认 True

## 任务四：prompt_layer 合并 SystemMessage
在构建最终 system_prompt 之前：
- 从 history_messages 中提取所有 SystemMessage 的内容
- 将提取后的内容从 history_messages 中移除
- 将提取内容追加合并到 system_prompt 末尾，用两个换行分隔

## 任务五：stream_chat_service 加入意图判断和异步更新
在流式对话服务中：
- 收到消息后，先调用 LongTermMemory.should_write 判断意图
- 命中画像写入意图时跳过 RAG 检索
- 流式输出完成后，构建包含最近 4 条历史消息和本轮 AI 回复的上下文，
  调用 LongTermMemory.submit_profile_update_async 异步触发画像更新

请按顺序逐一实现，每完成一个任务后告诉我，并说明关键实现细节。


# 长期记忆 & 短期记忆 测试清单

- [ ] 在同一会话中连续发送多条消息，验证短期记忆从 MySQL 加载并触发上下文裁剪日志。
- [ ] 发送用户信息写入长期记忆，验证数据库对应字段写入成功。
- [ ] 发送需要查询的用户信息，验证回答是否包含用户信息。
- [ ] 发送无关闲聊，验证不触发用户信息读取/写入。
- [ ] 发送文档/简历类问题，验证触发 RAG 检索而非用户信息写入。


实现一个最小学习测评工作流，并使用 LangGraph 做流程编排。

业务目标：
1. 前端调用接口提交学习测评需求。
2. 后端根据用户要求生成结构化题目 JSON，返回给前端渲染答题表单。
3. 用户提交整套答案后，后端统一完成评分、逐题点评、薄弱点提取和学习建议。
4. 整个流程跨两次 HTTP 请求，通过 run_id 和 workflow_runs 状态表保存、恢复流程状态。

数据库要求：
1. 在ORM 模型 中 新增 workflow_runs 表。
2. 核心字段包括 run_id、user_id、session_id、workflow_type、status、state_json、error_message、created_at、updated_at、completed_at。
3. state_json 用于保存完整工作流状态，支持第二次请求恢复题目和继续评分。

状态定义：
新建 LearningWorkflowState，只保留当前闭环必需字段：
- run_id、user_id、session_id、request_text、provider、question_count
- quiz、answers、evaluation、score、weaknesses、review、status

LangGraph 流程图设计：
1. 启动图：prepare_learning_context -> generate_quiz -> END。
2. 提交图：evaluate_and_review -> END。
3. prepare_learning_context 只做轻量状态标记。
4. generate_quiz 调用 LLM 生成结构化题目 JSON。
5. evaluate_and_review 调用 LLM 一次性完成评分、点评、薄弱点提取、学习建议生成。


接口要求：
1. POST /learning-workflows/start：入参 session_id/request_text/question_count/provider，返回 run_id/status/quiz
2. POST /learning-workflows/{run_id}/submit：入参 answers，返回 run_id/status/score/evaluation/weaknesses/review
3. GET /learning-workflows/{run_id}：返回 run_id/status/state

前后端边界：
1. 后端仅返回标准化 quiz JSON。
2. 前端根据题目类型渲染对应表单组件。
3. 用户仅提交 question_id 和对应答案 value。

封装工具函数：
JSON 解析工具函数，解析模型返回的JSON 数据

# 实现流程总控路由：

1. **目标**：新增 `POST /agent/tasks/start` 作为流程总控入口，根据前端传入的 `agent_name` 决定启动工作流或走通用聊天。
2. **路由策略**：先校验 `agent_name`，再执行“关键词快筛 + 语义兜底”。命中 `required_keywords` 直接进工作流；未命中时调用 `classify_intent()` 对当前工作流的 `intent_examples` 做确认；仍未命中则走通用聊天。
3. **当前规则**：`quiz_generate_workflow -> learning_quiz`，关键词覆盖“题、出题、刷题、练习、测验、测评、小测、面试题”等出题意图。
4. **关键文件**：`app/schemas/orchestrator_schemas.py` 定义入参；`app/services/orchestrator_service.py` 定义 `WORKFLOW_ROUTE_RULES` 和 `OrchestratorService`；`app/routes/orchestrator_routes.py` 暴露总控接口。
5. **关键函数**：`OrchestratorService.route(agent_name, request_text)` 只做路由判断；`OrchestratorService.start_task(...)` 负责调用 `LearningWorkflowService.start()` 或返回聊天标记；聊天分支由路由层复用 `StreamChatService.stream_chat()`。
6. **性能优化**：在 `app/main.py` 的 `lifespan` 中启动后台线程调用 `SemanticIntentClassifier.get().warmup()` 预热语义模型，避免模型下载或缓存异常阻塞应用启动；明确出题请求优先走关键词快筛，减少不必要的向量模型调用。
7. **扩展方式**：新增工作流时，只需新增一条 `WorkflowRouteRule`，配置 `workflow_type`、`required_keywords`、`intent_examples` 和阈值，并新增加对应服务调用分支。


# 请把现有学习测评工作流改造成 LangGraph interrupt + checkpoint 案例，要求保留现有接口和业务表。

核心设计：
1. 新增 app/agent/workflows/checkpoint.py：
   - get_workflow_checkpointer() 返回全局 MemorySaver。
   - build_thread_config(thread_id) 返回 {"configurable": {"thread_id": thread_id}}。
3. run_id 同时作为 workflow_runs.run_id 和 LangGraph thread_id。
4. WorkflowRun 只保存业务快照，checkpoint 只保存 LangGraph 执行现场。

学习图结构：
generate_quiz → wait_user_answer → evaluate_answer → finalize_result → END

核心节点：
1. generate_quiz：调用 LLM 生成 quiz，status 设置为 waiting_answer。
2. wait_user_answer：调用 interrupt({"quiz": quiz}) 暂停；恢复后接收 answers，status 设置为 grading。
3. evaluate_answer：调用 LLM 根据 quiz 和 answers 评分，输出 evaluation、score、weaknesses、review。
4. finalize_result：设置 status 为 completed。

服务层：
1. start()：
   - 生成 run_id。
   - 创建 WorkflowRun，状态 created。
   - 用 build_thread_config(run_id) 启动完整图。
   - 图执行到 interrupt 后，通过 graph.get_state(config).values 获取 quiz 快照。
   - 更新 WorkflowRun 为 waiting_answer。
   - 返回 run_id、status、quiz。

2. submit_answer()：
   - 校验 run_id、workflow_type、status=waiting_answer。
   - 先更新 WorkflowRun 为 grading。
   - 用 Command(resume=answers) 恢复同一个 graph thread。
   - 图继续执行评分和完成。
   - 更新 WorkflowRun 为 completed。
   - 返回 score、evaluation、weaknesses、review。


# 请在现有学习测评工作流中实现动态提示词和消息持久化功能：

1. 出题提示词通过 `prompt_template_manager.get_full_prompt("quiz_generate_workflow", db)` 获取。
2. 评分提示词通过 `prompt_template_manager.get_full_prompt("learning_evaluator",  db)` 获取。
3. 出题 AI 返回 JSON，题目 `type` 使用前端控件类型：`radio`、`checkbox`、`textarea`。
4. 评分 AI 返回 JSON，必须包含 `display_text`（中文点评文本）、`score`、`items`、`weaknesses`、`review`。
5. 出题完成后写入一条 `chat_messages`：
   - `request_text` = 用户出题请求
   - `response_text` = `"已完成出题，请完成后提交答案。"`（固定值）
   - `response_payload` = 完整 quiz JSON
   - `request_id` = `"{run_id}:quiz"`
6. 评分完成后不新增消息，而是更新第5步那条消息：
   - `response_text` = 最终评分展示文本（优先用 `display_text`，过短则兜底拼接）
   - `response_payload` = `None`
7. 新增 `chat_messages.response_payload` JSON 字段，历史消息接口返回该字段。
8. 验证标准：启动出题生成表单 JSON，提交答案后原消息变为点评文本，`response_payload` 为空，历史接口正常返回。


# 任务：给项目补上 A2A 消息信封（最小改动）

## 改动清单

### 1. 新建 `app/agent/a2a/envelope.py`
`A2AEnvelope`（Pydantic v2）字段：
- `from_agent: str`（必填）
- `payload_type: str`（必填）
- `payload: dict[str, Any]`（default_factory=dict）
- `next_agent: str | None`（默认 None）
- `confidence: float`（默认 1.0，Field(ge=0.0, le=1.0)）

### 2. 新建 `app/agent/a2a/__init__.py`
导出 `A2AEnvelope`，`__all__ = ["A2AEnvelope"]`

### 3. 修改 `app/agent/workflows/state.py`
`LearningWorkflowState.status` 下方新增：
`a2a_envelope: dict[str, Any] = Field(default_factory=dict, description="A2A 契约信封")`
（用 dict 因 LangGraph State 需 JSON 可序列化）

### 4. 修改 `app/agent/workflows/learning.py` 的 `create_evaluate_and_review_node`
- 函数内 `from app.agent.a2a import A2AEnvelope`
- `weaknesses = [...][:5]`（截断从 return 移至列表推导式尾部）
- `review = str(...)` 下方插入：
```python
has_weakness = bool(weaknesses)
envelope = A2AEnvelope(
    from_agent="learning_evaluator",
    payload_type="weak_points",
    payload={"score": score, "weaknesses": weaknesses, "review": review},
    next_agent="difficulty_learner" if has_weakness else None,
    confidence=0.9 if has_weakness else 0.4,
)
```

- return 中 `"review"` 下方加 `"a2a_envelope": envelope.model_dump(),`

## 业务规则

有薄弱点 → `next_agent="difficulty_learner"`，`confidence=0.9`；无 → `None`，`0.4`。`payload` 只放 `score` / `weaknesses` / `review`。