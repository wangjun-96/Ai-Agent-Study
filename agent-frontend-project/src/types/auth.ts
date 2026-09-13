/**
 * 认证模块全局类型定义。
 * 与后端接口文档（openai.json）保持一致，接口入参 / 出参全部强制约束。
 */

/** 后端统一响应体结构：code 为 0 表示成功，非 0 时 data 为 null */
export interface ApiResponse<T = unknown> {
  /** 业务状态码：0 成功；失败时为 5 位业务码（如 40104） */
  code: number
  /** 中文提示信息，可直接面向用户展示 */
  message: string
  /** 业务数据 */
  data: T
  /** 失败时的调试详情（字段级校验错误等），成功时不返回 */
  detail?: unknown
}

/** 登录请求参数 */
export interface LoginParams {
  /** 用户名（2-50 字符） */
  username: string
  /** 密码（明文传输，依赖 HTTPS 保护） */
  password: string
}

/** 注册请求参数（字段与登录一致，后端额外执行弱密码业务校验） */
export type RegisterParams = LoginParams

/** 登录成功返回的双令牌数据 */
export interface TokenResult {
  /** 访问令牌：访问受保护接口时放入 Authorization: Bearer 头 */
  access_token: string
  /** 刷新令牌：访问令牌过期后用于静默换取新的访问令牌 */
  refresh_token: string
  /** 令牌类型，固定为 bearer */
  token_type: string
  /** 访问令牌有效期（秒） */
  expires_in: number
}

/** 刷新令牌接口返回数据（仅下发新的访问令牌，刷新令牌保持不变） */
export interface AccessTokenResult {
  /** 新签发的访问令牌 */
  access_token: string
  /** 令牌类型，固定为 bearer */
  token_type: string
  /** 访问令牌有效期（秒） */
  expires_in: number
}

/** 用户信息（响应模型已脱敏，不含密码） */
export interface UserInfo {
  /** 用户 ID */
  id: number
  /** 用户名 */
  username: string
  /** 创建时间（ISO 时间字符串） */
  create_time: string
}

/** 后端字段级校验错误明细（422 时位于响应体 detail.errors 中） */
export interface FieldValidationError {
  /** 出错字段名 */
  field: string
  /** 字段级中文错误文案 */
  message: string
  /** 错误类型标识 */
  type: string
}
