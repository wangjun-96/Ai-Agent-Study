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
  /** 头像访问地址（/uploads/{user_id}/{md5}.ext，未设置时为 null） */
  avatar?: string | null
  /** 创建时间（ISO 时间字符串） */
  create_time: string
}

/** 通用文件上传的业务分类 */
export type UploadFileType = 'image' | 'document'

/** 通用文件上传成功返回数据（图片类型时后端已同步更新用户 avatar） */
export interface FileUploadResult {
  /** 文件访问 URL（/uploads 前缀的相对路径，由 Vite 代理透传） */
  url: string
  /** 文件业务分类：image=图片（已更新头像），document=文档（仅保存） */
  file_type: UploadFileType
  /** 本次上传是否更新了当前用户头像 */
  is_avatar: boolean
  /** 客户端原始文件名 */
  original_name: string
  /** 实际存储文件名（内容 MD5 + 扩展名） */
  stored_name: string
  /** 文件 MIME 类型 */
  content_type?: string | null
  /** 文件大小（字节） */
  size: number
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
