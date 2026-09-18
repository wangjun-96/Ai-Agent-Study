/**
 * 消息模块接口：按会话分页获取聊天消息。
 * 与后端接口文档（openai.json）保持一致。
 */
import request from '@/utils/request'
import type { MessageResponse } from '@/types/interview'

/** 消息列表分页结果 */
export interface MessageListResult {
  items: MessageResponse[]
  total: number
  page: number
  page_size: number
}

/**
 * 分页获取聊天消息
 * @param sessionId 会话 ID
 * @param params 分页参数
 */
export function getMessages(
  sessionId: number,
  params?: { page?: number; page_size?: number },
) {
  return request.get<MessageListResult>(`/api/v1/sessions/${sessionId}/messages`, { params })
}
