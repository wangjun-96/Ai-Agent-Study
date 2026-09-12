/** 消息角色：用户 / AI */
export type MessageRole = 'user' | 'ai'

/** 单条聊天消息 */
export interface ChatMessage {
  /** 消息唯一标识 */
  id: string
  /** 消息角色 */
  role: MessageRole
  /** 消息文本内容 */
  content: string
  /** 展示用时间文案（如"刚刚"） */
  timeText: string
}

/** 历史会话项 */
export interface ChatSession {
  /** 会话唯一标识 */
  id: string
  /** 会话标题 */
  title: string
  /** 列表图标名（对应 element-plus 图标组件名） */
  icon: string
  /** 图标主题色 */
  color: string
}

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
