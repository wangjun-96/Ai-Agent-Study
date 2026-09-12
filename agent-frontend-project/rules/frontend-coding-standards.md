# 前端编码规范

> 本规范适用于本项目（Vue3 + TypeScript + Vite）所有前端代码，所有提交代码必须严格遵守。
> 违反关键条款（标【强制】）的代码不予合并；其他条款（标【建议】）作为最佳实践引导。

---

## 一、技术栈与基础约定

1. 【强制】统一使用 **Vue3 + Composition API + `<script setup>`** 语法，禁止混用 Options API 编写业务页面组件。
2. 【强制】全部代码使用 **TypeScript**，禁止使用纯 JavaScript 提交业务代码。
3. 【强制】包管理统一使用 **npm**，禁止混用 yarn / pnpm lock 文件。
4. 【强制】Node 版本统一（建议 ≥ 18），通过 `.nvmrc` 或 README 约束。

---

## 二、目录结构规范

1. 【强制】目录分层清晰，按职责归类：

```
src/
├── api/          # 接口请求层（按业务模块拆分）
├── assets/       # 静态资源（图片、字体、样式等）
├── components/   # 全局通用基础组件
├── composables/  # 组合式函数（Hook）
├── config/       # 全局常量、枚举、配置
├── directives/   # 自定义指令（v-permission 等）
├── layouts/      # 布局组件
├── router/       # 路由配置
├── stores/       # Pinia 状态管理
├── styles/       # 全局公共样式、主题变量
├── types/        # 全局 TS 类型定义
├── utils/        # 工具函数（axios 实例、log、storage 等）
├── views/        # 页面容器组件（按业务模块分子目录）
├── App.vue
└── main.ts
```

2. 【强制】通用工具函数、常量、枚举、公共配置统一抽离封装，全局复用，禁止重复复制代码。
3. 【强制】业务逻辑与页面视图/接口入口强制分离：入口仅做参数接收、路由分发、异常捕获，不堆砌核心业务代码。
4. 【强制】禁止千行级超大单体文件、超大接口、超大页面组件，单文件代码行数控制在 **500 行**内，超限必须拆分子组件。

---

## 三、命名规范

1. 【强制】**组件文件名**使用大驼峰：`UserList.vue`、`BaseTable.vue`。
2. 【强制】**脚本文件名**使用小驼峰：`request.ts`、`userApi.ts`。
3. 【强制】**目录名**统一小写或小驼峰，保持全项目一致。
4. 【强制】**组件 name** 必须使用大驼峰，且与文件名一致。
5. 【建议】**常量**使用全大写下划线：`MAX_PAGE_SIZE`。
6. 【建议】**类型/接口**使用大驼峰：`interface UserInfo`。
7. 【建议】**枚举**使用大驼峰，枚举值使用全大写下划线：

```ts
enum OrderStatus {
  PENDING = 'PENDING',
  PAID = 'PAID',
  CANCELED = 'CANCELED',
}
```

---

## 四、组件规范

1. 【强制】组件分层拆分：
   - **页面容器组件**（views/）：负责数据装配、子组件编排。
   - **业务子组件**（views/xxx/components/）：负责具体业务展示。
   - **通用基础组件**（components/）：纯 UI、无业务逻辑，全局复用。
2. 【强制】模板、脚本、样式代码分离，单个 `.vue` 文件代码行数 ≤ 500 行，超限必须拆分。
3. 【强制】Props 必须定义类型与默认值，复杂对象使用 `PropType` 约束，禁止 `any`、`unknown` 滥用：

```ts
interface Props {
  userId: number
  userInfo?: UserInfo
  list: UserItem[]
}
const props = withDefaults(defineProps<Props>(), {
  userId: 0,
  list: () => [],
})
```

4. 【强制】事件统一通过 `defineEmits` 声明，禁止直接操作 DOM 绑定原生事件：

```ts
const emit = defineEmits<{
  (e: 'update', value: UserItem): void
  (e: 'delete', id: number): void
}>()
```

5. 【强制】优先使用 Vue 内置指令（v-if / v-show / v-for / v-model），禁止在模板中写复杂表达式。
6. 【建议】v-for 必须绑定 `:key`，且 key 唯一稳定，禁止使用 index 作为 key。

---

## 五、TypeScript 类型规范

1. 【强制】新增功能必须配套类型定义，接口入参、出参、业务实体强制约束类型，杜绝任意隐式类型。
2. 【强制】接口请求参数、返回数据、组件 props、emit 事件必须书写完整 `interface` 类型。
3. 【强制】禁止滥用 `any`，确需放宽类型时使用 `unknown` 并做类型守卫收窄。
4. 【强制】公共类型统一抽到 `types/` 目录，按业务模块拆分文件，禁止散落在各组件内重复定义。
5. 【建议】优先使用 `interface` 描述对象结构，使用 `type` 描述联合类型/工具类型。

---

## 六、接口请求规范

1. 【强制】接口请求统一封装 **axios 实例**（`utils/request.ts`），统一拦截请求头、响应错误、加载状态，页面禁止直接裸写 axios 请求。
2. 【强制】按业务模块拆分接口文件（`api/user.ts`、`api/order.ts`），同模块接口集中维护。
3. 【强制】接口入参、出参必须有 TS 类型定义：

```ts
interface LoginParams {
  username: string
  password: string
}
interface LoginResult {
  token: string
  expires: number
}
export function login(data: LoginParams) {
  return request.post<LoginResult>('/auth/login', data)
}
```

4. 【强制】接口地址、超时配置、第三方接口地址统一从环境变量读取，禁止硬编码。
5. 【建议】统一响应格式 `{ code, message, data }`，在响应拦截器统一处理 code != 0 的业务异常。

---

## 七、状态管理规范

1. 【强制】状态管理区分：
   - **全局状态**存放 Pinia（用户信息、权限、主题等）。
   - **页面临时状态**用 `ref` / `reactive`，禁止滥用全局存储临时变量。
2. 【强制】Pinia store 按业务模块拆分，命名 `useXxxStore`。
3. 【强制】store 中只放状态与状态相关逻辑，不耦合接口请求细节，接口调用由组件或 composables 触发。
4. 【建议】复杂状态变更使用 actions 封装，禁止在组件内直接修改 store 内部结构。

---

## 八、路由规范

1. 【强制】路由统一集中管理（`router/`），路由元信息、权限控制、页面标题统一在路由配置中定义，不在页面内单独处理：

```ts
const routes: RouteRecordRaw[] = [
  {
    path: '/user',
    name: 'User',
    component: () => import('@/views/user/index.vue'),
    meta: { title: '用户管理', requiresAuth: true, permission: 'user:view' },
  },
]
```

2. 【强制】路由懒加载统一使用 `() => import()`，禁止同步 import 大型页面。
3. 【建议】路由按业务模块分组，使用嵌套路由组织父子关系。

---

## 九、样式规范

1. 【强制】样式统一使用 **Scoped** 隔离，禁止组件间样式相互污染：

```vue
<style scoped lang="scss">
.user-card { /* ... */ }
</style>
```

2. 【强制】全局公共样式、主题变量抽离至 `styles/` 目录，使用 CSS 变量统一管理：

```scss
:root {
  --color-primary: #409eff;
  --spacing-base: 16px;
}
```

3. 【强制】禁止大量行内 style 硬写样式，行内样式仅用于动态计算值的场景。
4. 【强制】禁止硬编码颜色值，统一使用主题变量或 SCSS 变量。
5. 【建议】类名使用小写连字符：`.user-card-title`。

---

## 十、权限控制规范

1. 【强制】权限控制统一封装指令 **v-permission**，页面按钮、菜单权限统一读取全局权限列表判断：

```vue
<el-button v-permission="'user:create'">新增用户</el-button>
```

2. 【强制】路由级权限通过路由 meta 的 `requiresAuth` 与 `permission` 字段，在全局前置守卫统一拦截。
3. 【强制】接口返回的权限列表在登录后写入 Pinia，刷新后从本地存储恢复。

---

## 十一、静态资源规范

1. 【强制】图片、静态资源统一放入 `assets/` 目录，按类型分子目录（`assets/images/`、`assets/icons/`）。
2. 【强制】大体积图片必须做压缩，线上禁止引入本地超大静态资源。
3. 【建议】SVG 图标统一封装为组件或使用图标库（如 `@iconify/vue`）批量引用。
4. 【建议】小图标使用 base64 或 iconfont 雪碧图减少请求数。

---

## 十二、环境变量与配置规范

1. 【强制】环境区分 **开发、测试、生产** 三套独立配置（`.env.development` / `.env.test` / `.env.production`）。
2. 【强制】禁止硬编码常量、接口地址、密钥、环境变量，全部抽离至 `.env.*` 文件统一管理。
3. 【强制】业务代码统一通过 `import.meta.env.VITE_XXX` 读取，禁止在 vite.config 之外读取 process.env。
4. 【强制】禁止本地调试代码、测试打印语句（`console.log`、debugger）提交至线上分支。
5. 【建议】`.env.*` 文件中变量必须以 `VITE_` 前缀开头，敏感信息（如密钥）不写入前端环境变量。

---

## 十三、日志与调试规范

1. 【强制】提交代码前消除控制台无用 `console` 打印。
2. 【强制】调试日志统一封装全局 `log` 工具（`utils/log.ts`），支持 info / warn / error 级别，环境开关控制：

```ts
import { log } from '@/utils/log'
log.info('用户登录成功', userInfo)
log.error('接口异常', error)
```

3. 【强制】关键操作（登录、支付、删除）必须记录日志，禁止用 `alert` 提示用户。

---

## 十四、通用工具与公共组件规范

1. 【强制】表单、弹窗、表格、分页封装通用基础组件，页面仅传入配置项，不重复编写重复 DOM 结构。
2. 【强制】通用工具函数（防抖、节流、深拷贝、格式化等）统一抽到 `utils/`，禁止散落业务文件内。
3. 【强制】第三方接口、文件上传、缓存（localStorage / sessionStorage）操作统一封装工具类，业务层只调用工具方法，不裸写 SDK 代码。
4. 【建议】通用组件提供完整的 props 类型与 emit 事件，配套使用示例。

---

## 十五、代码质量规范

1. 【强制】禁止循环导入、全局变量存储临时业务数据，单次请求数据通过函数参数、返回值传递。
2. 【强制】所有删除逻辑默认使用**逻辑删除**（`is_delete` 标记），禁止前端直接发起物理删除请求（除非有明确业务确认与后端校验）。
3. 【强制】所有代码添加必要注释：复杂算法、业务规则、特殊兼容逻辑、入参出参说明；简单基础逻辑无需冗余注释。
4. 【强制】注释统一使用中文，与代码意图一致，禁止注释与代码不符或过期注释。
5. 【建议】函数单一职责，超长函数（> 80 行）拆分子函数。
6. 【建议】统一异常处理、统一返回格式、统一日志打印标准，前后端交互数据结构保持约定一致。

---

## 十六、Git 提交规范

1. 【强制】提交信息格式：`<type>(<scope>): <subject>`
   - type：`feat` / `fix` / `docs` / `style` / `refactor` / `test` / `chore` / `perf`
   - scope：影响模块（user / order / common 等）
   - subject：简短描述，中文或英文均可
2. 【强制】禁止提交 `node_modules/`、`dist/`、本地环境配置文件中的密钥。
3. 【建议】单次提交只解决一个问题，避免大杂烩提交。

---

## 附：检查清单（PR 前自检）

- [ ] 是否使用 `<script setup>` + Composition API？
- [ ] 是否有 `any` 滥用？类型是否完整？
- [ ] 单文件是否超 500 行？
- [ ] 是否有裸写 axios 请求、裸写 console？
- [ ] 是否硬编码接口地址 / 颜色 / 常量？
- [ ] Props / Emits 类型是否完整？
- [ ] 样式是否 scoped？是否使用主题变量？
- [ ] 是否有未删除的调试代码（debugger / 测试 console）？
- [ ] 路由权限、按钮权限是否配置？
- [ ] 注释是否覆盖复杂业务逻辑？
```
