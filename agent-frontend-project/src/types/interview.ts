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

/** 消息角色：用户 / AI */
export type MessageRole = 'user' | 'ai'

/** 附件类型 */
export type SegmentType = 'file' | 'image' | 'audio'

/** 单条消息附件 */
export interface MessageSegment {
  /** 附件类型：file=文件，image=图片，audio=音频 */
  type: SegmentType
  /** 附件名称 */
  name: string
  /** 附件 URL */
  url: string
  /** 资源 ID（可选） */
  resource_id?: number
}

/** 单条聊天消息 */
export interface ChatMessage {
  /** 消息唯一标识 */
  id: string | number
  /** 消息角色 */
  role: MessageRole
  /** 消息文本内容 */
  content: string
  /** 展示用时间文案（如"刚刚"） */
  timeText?: string
  /** 创建时间（ISO 时间字符串） */
  created_at?: string
  /** 用户发送的附件列表 */
  request_segments?: MessageSegment[]
  /** AI 回复的附件列表 */
  response_segments?: MessageSegment[]
  /** 面试状态：null 或 0=待开始，1=进行中/可查看详情 */
  status?: number | null
  /** 关联的面试 ID */
  interview_id?: number | null
}

/** 历史会话项 */
export interface ChatSession {
  /** 会话唯一标识 */
  id: number | string
  /** 会话标题 */
  title: string
  /** 列表图标名（对应 element-plus 图标组件名） */
  icon?: string
  /** 图标主题色 */
  color?: string
  /** 会话模式：0=学习，1=面试，2=笔记 */
  session_model?: SessionModel
  /** 创建时间 */
  create_time?: string
  /** 更新时间 */
  update_time?: string
}

/** 会话模式枚举 */
export type SessionModel = 0 | 1 | 2

/** 顶部导航 Tab 配置项 */
export interface TabItem {
  /** Tab 对应路由路径（同时作为选中标识） */
  path: string
  /** Tab 展示文案 */
  label: string
}

/** 聊天输入区功能按钮配置项 */
export interface InputAction {
  /** 按钮唯一标识 */
  key: string
  /** 按钮展示文案 */
  label: string
  /** 图标名（对应 ChatInputBar 内图标映射的 key） */
  icon: string
}

/** ==================== 后端接口返回类型 ==================== */

/** 会话响应（后端返回） */
export interface SessionResponse {
  id: number
  title: string
  session_model: SessionModel
  create_time: string
  update_time: string
}

/** 创建会话参数 */
export interface SessionCreateParams {
  title: string
  session_model: SessionModel
}

/** 更新会话参数 */
export interface SessionUpdateParams {
  title?: string
  session_model?: SessionModel
}

/** 消息响应（后端返回） */
export interface MessageResponse {
  id: number
  request_text: string
  response_text: string
  request_segments: MessageSegment[]
  response_segments: MessageSegment[]
  status: number | null
  interview_id: number | null
  created_at: string
}

/** 面试响应（后端返回） */
export interface InterviewResponse {
  id: number
  qa_object: Record<string, string>[]
  status: number
  create_time: string
}
