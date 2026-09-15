# 学面通AI（agent-frontend-project）

基于 **Vue 3 + TypeScript + Vite** 构建的 AI 面试模拟与学习辅助前端应用。应用围绕「面试练习 + 学习问答 + 笔记沉淀」三个场景组织，当前包含三大业务模块：**面试间**、**学习室**、**笔记本**，并已接入后端完成**用户注册、登录鉴权**闭环。

> 说明：用户认证（注册 / 登录 / 双令牌刷新 / 退出）已对接真实后端接口；会话、笔记等业务数据仍使用本地 Mock，AI 回复为前端定时模拟（详见「数据与接口现状」）。

---

## 一、功能特性

- **登录 / 注册**：登录、注册同页 Tab 切换；表单按后端约束做长度与密码强度前置校验（必填提示仅在失焦或提交时出现）；注册成功自动登录并回跳原目标页。
- **登录鉴权闭环**：双令牌（access / refresh）持久化到 localStorage，刷新页面保持登录态；访问令牌过期时用刷新令牌「单飞」静默换新并重放请求，刷新令牌失效则自动清理并跳转登录页；未登录访问业务页面统一被路由守卫拦截。
- **用户菜单**：头部展示「头像 + 用户名」整体入口，点击弹出二级菜单（个人信息为预留入口、退出登录二次确认后清理登录态）。
- **面试间（默认首页）**：聊天式模拟面试，支持多轮对话、消息自动滚动、AI 回复期间禁止重复发送；输入区预置「上传文件 / 简历优化 / 模拟面试 / 面试复盘 / 知识精讲 / 语音输入」功能入口。
- **学习室**：与面试间共用聊天室组件，预置「上传文件 / 知识精讲 / 刷题模式」功能入口，占位文案与按钮按场景配置。
- **笔记本**：基于 wangEditor 的富文本笔记编辑，支持标题实时编辑、常用格式工具栏（加粗、列表、对齐、链接、图片等）。
- **历史会话 / 笔记侧边栏**：新建、切换、行内重命名、删除（删除二次确认），聊天列表与笔记列表复用同一套组件。
- **顶部模块导航**：Tab 切换与路由双向联动，刷新后保持当前模块。
- **多环境配置**：内置开发 / 测试 / 生产三套环境变量，本地开发通过代理转发后端接口。

---

## 二、技术栈

| 分类 | 技术 | 版本（package.json） |
| --- | --- | --- |
| 框架 | Vue（Composition API + `<script setup>`） | ^3.5.41 |
| 语言 | TypeScript | ~6.0.2 |
| 构建工具 | Vite | ^8.2.2 |
| 状态管理 | Pinia | ^4.0.3 |
| 路由 | Vue Router（History 模式） | ^5.3.0 |
| UI 组件库 | Element Plus + @element-plus/icons-vue | ^2.14.5 / ^2.3.2 |
| HTTP 请求 | axios（统一实例封装，见 `src/utils/request.ts`） | ^1.20.0 |
| 富文本编辑器 | wangEditor（@wangeditor/editor + editor-for-vue） | ^5.1.23 / ^5.1.12 |
| 样式 | Sass（SCSS） | ^1.103.1 |
| 类型检查 | vue-tsc | ^3.3.11 |
| 包管理器 | npm（禁止混用 yarn / pnpm lock 文件） | - |

---

## 三、环境要求

- **Node.js**：建议使用 LTS 版本。Vite 8 官方要求 Node.js `20.19+` 或 `22.12+`。
- **npm**：随 Node.js 安装即可。
- 后端服务：登录注册与鉴权依赖后端，本地开发默认对接 `http://localhost:8000`，可通过 `VITE_PROXY_TARGET` 修改。后端未启动时仍可打开页面，但登录、注册及受保护接口不可用。

---

## 四、快速开始

```bash
# 1. 安装依赖
npm install

# 2. 启动本地开发服务（默认 http://localhost:5173 ，启动后自动打开浏览器）
npm run dev

# 3. 类型检查 + 生产环境构建（产物输出至 dist/）
npm run build

# 4. 本地预览生产构建产物
npm run preview
```

如需以测试环境配置启动，可指定 Vite mode：

```bash
npm run dev -- --mode test
```

---

## 五、环境变量

项目根目录提供三套环境配置，业务代码统一通过 `import.meta.env.VITE_XXX` 读取：

| 变量名 | 说明 | 开发环境默认值 |
| --- | --- | --- |
| `VITE_APP_TITLE` | 应用标题 | `Agent Frontend (Dev)` |
| `VITE_PORT` | 本地开发服务器端口 | `5173` |
| `VITE_API_PREFIX` | 业务接口代理匹配规则（后端业务接口前缀 `/api/v1`） | `/api` |
| `VITE_PROXY_TARGET` | 开发 / 测试环境代理转发的后端地址 | `http://localhost:8000` |
| `VITE_API_BASE_URL` | axios 实例 baseURL；开发 / 测试环境置空走 Vite 同源代理，生产环境配真实域名 | （空） |
| `VITE_LOG_ENABLED` | 是否开启调试日志（生产环境关闭） | `true` |

配置文件：`.env.development`、`.env.test`、`.env.production`。`NODE_ENV` 由 Vite 按 mode 自动注入，请勿在文件中手动设置。

---

## 六、目录结构

```
agent-frontend-project/
├── public/
│   └── favicon.svg                # 站点图标
├── rules/
│   └── frontend-coding-standards.md  # 前端编码规范（提交前必读）
├── src/
│   ├── api/                        # 接口请求层（按业务模块拆分）
│   │   └── auth.ts                 # 认证接口：注册 / 登录 / 刷新令牌 / 当前用户
│   ├── components/                # 通用 / 业务组件
│   │   ├── chat/                  # 聊天相关：聊天室、输入区、消息列表、气泡、头像
│   │   ├── common/                # 通用基础组件（TabSwitch）
│   │   ├── layout/                # 布局组件（AppHeader 顶部导航 + 用户菜单）
│   │   ├── note/                  # 笔记组件（NoteEditorCard 富文本卡片）
│   │   └── sidebar/               # 侧边栏（AppSidebar 容器 + ChatHistoryList 列表）
│   ├── config/
│   │   └── constant.ts            # 全局常量：Tab/功能按钮配置、登录路径、招呼语、Mock 数据
│   ├── layouts/
│   │   └── MainLayout.vue         # 主布局：顶部导航 + 侧边栏 + 路由出口
│   ├── router/
│   │   └── index.ts               # 集中路由配置 + 登录守卫 + 全局标题
│   ├── stores/
│   │   ├── chat.ts                # 聊天状态（会话列表、消息缓存、模拟回复）
│   │   ├── note.ts                # 笔记状态（笔记列表、富文本内容缓存）
│   │   └── user.ts                # 用户状态（双令牌、当前用户、登录/注册/登出）
│   ├── styles/
│   │   ├── index.scss             # 全局基础样式与滚动条美化
│   │   └── variables.scss         # 主题色、布局尺寸、圆角等 SCSS 变量
│   ├── types/
│   │   ├── auth.ts                # 统一响应体、登录/注册、令牌、用户信息类型
│   │   ├── interview.ts           # 消息、会话、Tab、功能按钮等全局类型
│   │   └── router.d.ts            # 路由 meta 类型扩展（title / sidebar / requiresAuth）
│   ├── utils/                     # 工具层
│   │   ├── request.ts             # axios 实例：令牌注入、静默刷新、统一错误提示
│   │   ├── storage.ts             # localStorage 封装（access / refresh 双令牌读写）
│   │   └── validate.ts            # 用户名/密码长度与密码强度校验（与后端约束一致）
│   ├── views/                     # 页面容器组件
│   │   ├── interview/index.vue    # 面试间
│   │   ├── study/index.vue        # 学习室
│   │   ├── note/index.vue         # 笔记本
│   │   └── login/index.vue        # 登录 / 注册页
│   ├── App.vue                    # 根组件（仅承载 router-view）
│   └── main.ts                    # 应用入口（注册 Element Plus / Pinia / Router、登录态失效回调）
├── .env.development               # 开发环境变量
├── .env.test                      # 测试环境变量
├── .env.production                # 生产环境变量
├── index.html                     # HTML 入口（标题：学面通AI）
├── vite.config.ts                 # Vite 配置（别名、代理、构建分桶）
├── tsconfig.json                  # TS 配置入口（引用 app / node 两份配置）
├── tsconfig.app.json              # 应用代码 TS 配置（@ 路径别名等）
└── package.json
```

---

## 七、功能模块说明

### 1. 面试间 `/interview`（默认页）

- 根路径 `/` 通过 `DEFAULT_TAB_PATH` 重定向至此。
- 页面容器 `views/interview/index.vue` 仅负责装配：复用 `ChatRoom` 组件，传入面试场景占位文案「输入你的回答...」与 `INTERVIEW_INPUT_ACTIONS` 按钮配置。
- 进入会话时 AI 自动发送招呼语；发送消息后模拟 600ms 异步回复，回复期间输入区禁用。

### 2. 学习室 `/study`

- 与面试间共用 `ChatRoom`，占位文案为「输入你的问题...」，按钮配置为 `STUDY_INPUT_ACTIONS`。
- 两个聊天页面共享同一个 `useChatStore`，会话与消息缓存互通。

### 3. 笔记本 `/note`

- 富文本编辑卡片 `NoteEditorCard`：wangEditor 工具栏 + 标题输入框 + 编辑区。
- 标题与内容通过可写计算属性实时同步到 `useNoteStore`，切换笔记即时加载对应内容；组件卸载时销毁编辑器实例避免内存泄漏。

### 4. 全局布局与侧边栏

- `MainLayout` 由 `AppHeader`（Logo + Tab 导航 + 用户菜单）、`AppSidebar`（新建按钮 + 列表）、`router-view` 三部分组成。
- 侧边栏根据当前路由 `meta.sidebar` 切换数据源：`chat` 渲染聊天会话，`note` 渲染笔记列表；两套列表复用 `AppSidebar` + `ChatHistoryList`，仅通过 props 文案与事件区分业务。
- 布局挂载后若已登录会拉取 `/api/v1/auth/me` 恢复当前用户信息，供头部展示用户名。

### 5. 登录 / 注册与用户菜单

- 登录页 `views/login/index.vue`（路由 `/login`）：登录与注册同页 Tab 切换，共用一套 `el-form`；用户名、密码规则与后端约束保持一致（长度区间、密码须字母 + 数字组合且不能包含用户名）。
- 表单设置 `validate-on-rule-change=false`，模式切换不触发校验，必填错误仅在字段失焦或点击提交时出现。
- 注册成功后使用同一凭证自动登录，并回跳登录前被拦截的目标地址（`?redirect=`）。
- 头部右侧为「头像 + 用户名 + 下拉箭头」整体入口，点击弹出 `el-dropdown`：`个人信息`（功能预留，点击给出开发中提示）、`退出登录`（`ElMessageBox` 二次确认后清理令牌并跳转登录页）。

---

## 八、架构与约定

### 路由

- 路由集中在 `src/router/index.ts` 维护，页面组件全部使用动态 `import()` 懒加载。
- 路由 meta 约定（类型见 `src/types/router.d.ts`）：
  - `title`：页面标题，全局前置守卫统一拼接为 `${title} - 学面通AI` 并设置 `document.title`；
  - `sidebar`：侧边栏类型，`'chat'`（默认）或 `'note'`，决定布局层渲染哪个侧边栏；
  - `requiresAuth`：是否需要登录，业务页面为 `true`，登录页显式置为 `false`。
- 全局前置守卫（返回值写法，不使用已废弃的 `next()`）：
  - 未登录访问受保护页面 → 重定向 `/login?redirect=<原路径>`；
  - 已登录访问 `/login` → 直接进入默认首页 `DEFAULT_TAB_PATH`。
- 使用 `createWebHistory()`（History 模式），部署到静态服务器时需配置 history fallback。

### 状态管理（Pinia）

- 全部使用 Setup Store 写法（`defineStore` + 组合式函数）。
- `useChatStore`：`sessions` 历史会话、`activeSessionId`、`conversations`（按会话 ID 缓存的消息表）、`isReplying`；提供初始化、切换、新建、重命名、删除、发送消息等动作。
- `useNoteStore`：`notes` 笔记列表、`activeNoteId`、`contents`（按笔记 ID 缓存的 HTML 内容）；提供选择、新建、重命名、内容更新、删除等动作。
- `useUserStore`：`accessToken` / `refreshToken` / `userInfo` 状态（初始化时从 localStorage 恢复），计算属性 `isLoggedIn`、`username`；提供 `login`（签发令牌并拉取用户信息）、`register`、`fetchCurrentUser`、`logout` / `clearAuth` 动作。
- 删除当前激活项后自动切换到列表首项；列表为空时激活 ID 置空。

### 接口请求与登录鉴权

- 所有请求统一走 `src/utils/request.ts` 的 axios 实例（`baseURL` 取 `VITE_API_BASE_URL`，开发环境置空），页面禁止裸写 axios；接口按业务模块放在 `src/api/`，入参出参在 `src/types/auth.ts` 等文件中定义完整 interface。
- 后端统一响应体为 `{ code, message, data }`，`code = 0` 为成功；成功拦截器直接返回响应体，业务层取 `res.data`。
- 请求拦截器自动注入 `Authorization: Bearer <access_token>`；响应错误按业务码分流：
  - `40104` 访问令牌过期：调用 `/api/v1/auth/refresh`「单飞」静默换新，并发 401 共享同一次刷新，成功后重放原请求（每请求最多一次）；
  - `40105` 刷新令牌失效或刷新失败：提示一次「登录状态已过期」，清理令牌并跳转登录页；
  - 其他错误（如 `40103` 凭证错误、`42200` 参数错误、`42901` 限流）：统一弹出后端中文 `message`，页面层不再重复提示；无响应时提示网络异常。
- 令牌由 `src/utils/storage.ts` 统一读写 localStorage（键名 `agent_access_token` / `agent_refresh_token`），业务代码不直接操作。
- 登录态失效后的清理与跳转通过 `setTokenExpiredHandler` 由 `main.ts` 注入，避免 `request` 与 router / store 循环依赖。
- 后端认证接口统一为 `/api/v1/auth/*`（注册、登录、刷新、`/api/v1/auth/me`），与业务接口共用 `/api/v1` 版本前缀。

### 组件复用与配置驱动

- `ChatRoom`（消息列表 + 输入区）被面试间、学习室复用，差异通过 `placeholder` 与 `actions` 配置消化。
- 功能按钮由 `src/config/constant.ts` 的 `InputAction[]` 驱动，图标通过 `ChatInputBar` 内的图标名映射渲染，未匹配时回退到附件图标。
- 输入区的功能按钮当前为预留入口，点击统一弹出「xx功能开发中」提示。

### 数据与接口现状

- **用户认证已对接真实后端**：注册、登录、令牌刷新、`/api/v1/auth/me` 均通过 `src/api/auth.ts` + `src/utils/request.ts` 调用，双令牌持久化在 localStorage。
- **业务数据仍为 Mock**：会话、笔记、消息等数据仍是 `src/config/constant.ts` 中的 Mock 数据，仅保存在 Pinia 内存中，刷新页面后重置；AI 回复由 `stores/chat.ts` 中的 `window.setTimeout` 模拟（代码内已标注「后续替换为真实接口调用」）。
- 业务接口接入步骤（基础设施已就绪，无需再安装 axios）：
  1. 按业务模块在 `src/api/` 新增接口文件，入参 / 出参补充完整 interface，统一经 `src/utils/request.ts` 发起；
  2. 将 `sendMessage` 中的模拟逻辑替换为真实接口调用，并移除 `constant.ts` 中对应的 Mock 数据。

### Vite 工程配置

- 路径别名：`@` 指向 `src`（`vite.config.ts` 与 `tsconfig.app.json` 两处保持一致）。
- 开发服务器：监听 `0.0.0.0:5173`，自动打开浏览器；代理目标取 `VITE_PROXY_TARGET`（默认 `http://localhost:8000`）。代理包含两条规则且均**原样透传、不做 rewrite**：`VITE_API_PREFIX`（默认 `/api`，对应后端 `/api/v1` 业务与认证接口，含 `/api/v1/auth/*`）与 `/uploads`（上传静态资源）。因浏览器始终同源访问 dev server，后端无需开启 CORS。
- 构建：产物输出 `dist/`；非生产环境生成 sourcemap；`node_modules` 中的 `element-plus`、`@wangeditor`、`vue` 拆分为独立 chunk，便于缓存复用；单包告警阈值 1500KB。

### 样式规范

- 组件样式统一 `<style scoped lang="scss">` 隔离，类名使用小写连字符。
- 颜色、尺寸、圆角等禁止硬编码，统一引用 `src/styles/variables.scss`（品牌主色为品牌黄 `#fbc531`，聊天区背景为米色 `#fbf4e9`）。
- 全局基础重置、字体栈、滚动条美化位于 `src/styles/index.scss`。

---

## 九、新增页面 / 模块指引

1. 在 `src/views/<模块>/index.vue` 新建页面容器组件，保持「容器装配、子组件承载 UI」的分层；
2. 在 `src/router/index.ts` 的 `MainLayout` children 中注册路由，按需配置 `meta.title`、`meta.sidebar`；受保护页面保持默认 `requiresAuth` 行为（缺省即需登录），仅公开页面（如登录页）显式置为 `false`；
3. 如需出现在顶部导航，在 `src/config/constant.ts` 的 `TAB_LIST` 中追加 `{ path, label }`；
4. 涉及全局状态时在 `src/stores/` 新增独立 store，页面临时状态使用 `ref` / `reactive`；
5. 公共类型补充到 `src/types/`，禁止在组件内重复定义。

---

## 十、编码规范

项目强制遵循 [前端编码规范](./rules/frontend-coding-standards.md)，提交代码前请按文档末尾的检查清单自检，核心要求包括：

- 统一使用 Vue 3 Composition API + `<script setup>` + TypeScript，禁止滥用 `any`；
- 单文件控制在 500 行以内，Props / Emits 必须定义完整类型；
- 接口请求统一走 axios 封装，禁止裸写 axios 与硬编码地址；
- 样式 scoped 隔离并使用主题变量，提交前移除无用 `console` / `debugger`。
