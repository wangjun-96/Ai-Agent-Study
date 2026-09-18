# 项目初始化提示

初始化一个名为'{{agent-frontend-project}}'的新项目。


** 项目配置：**


- **框架：** ‘{{Vue3}}’
- **语言：** ‘{{TypeScript}}’
- **包管理器：** ‘{{npm}}’
- **UI 框架：** ‘{{Element Plus}}’
- **状态管理：** ‘{{Pinia}}’
- **构建工具：** ‘{{Vite}}’

** 操作指令：**
1. 创建项目目录。
2. 使用指定框架和语言初始化项目。
3. 安装并配置所有必要的依赖项，包括 UI 框架。
4. 配置代码检查和格式化工具。
5. 确保项目可以成功构建和运行。

# 实现前端登录功能：
1. 引入 axios 并二次封装 axios （请求头带 token，401自动刷新并重试，失败清理 token 并跳转登录）。
2. 统一错误提示：全局捕获 axios 错误信息；
3. 调用接口文档中的登录注册接口，处理登录和注册逻辑。
4. 路由前置守卫拦截未登录：在路由守卫中检查token，未登录则跳转到登录页。
5. 登录成功后，保存 token 到 localStorage。
6. 头部按钮支持退出登录：添加退出登录按钮，点击后清理 token 并跳转到登录页。

# 用户注册时，实现头像上传功能

1. 用户选择头像时，只在本地预览，不上传。
2. 点击注册时，先用文本信息创建账号，成功后 自动登录 以获取token。
3. 登录成功后，再发起 已认证的头像上传请求。
4. “使用 Pinia 全局管理用户信息

# 实现聊天页面会话管理，对话管理数据回显：

- 会话管理：支持会话列表分页（`GET/sessions`）、新建（`POST/sessions`）、编辑标题（`PUT/sessions/{session_id}`）、删除（`DELETE/sessions/{id}`，操作后刷新并切换会话）。
- 聊天信息：按会话ID分页获取消息（`GET/sessions/{session_id}/messages`），正文渲染`request_text/response_text`,附件渲染`request_segments/response_segments`（只含`file/image/audio`字段容错，结构为`type/name/url/resource_id`）。
- 消息区：正文与附件分区显示，附件用独立组件（如`MsgFile.vue`）,图片失败显示占位图，音频失败有提示。
- 消息加载：上拉分页（距离顶部100px触发），loading锁防重入，增量追加，按`created_at`排序。
- 面试卡片：`status=1` 时显示卡片，点击调用`GET/interviews/{interview_id}`,弹窗展示`qa_object`。

全部需对接的接口如下：

- `GET/sessions`
- `GET/sessions/{session_id}/messages`
- `GET/interviews/{interview_id}`
- `POST/sessions`
- `PUT/sessions/{session_id}`
- `DELETE/sessions/{id}`
