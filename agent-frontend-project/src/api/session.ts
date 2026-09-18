/**
 * 会话模块接口：会话列表、新建会话、编辑会话、删除会话。
 * 与后端接口文档（openai.json）保持一致。
 */
import request from '@/utils/request'
import type { SessionResponse, SessionCreateParams, SessionUpdateParams } from '@/types/interview'

/** 会话列表分页 */
export interface SessionListResult {
  items: SessionResponse[]
  total: number
  page: number
  page_size: number
}

export function getSessions(params?: {
  session_model?: number
  page?: number
  page_size?: number
}) {
  return request.get<SessionListResult>('/api/v1/sessions/', { params })
}

/** 创建会话 */
export function createSession(data: SessionCreateParams) {
  return request.post<SessionResponse>('/api/v1/sessions/', data)
}

/** 编辑会话 */
export function updateSession(sessionId: number, data: SessionUpdateParams) {
  return request.put<SessionResponse>(`/api/v1/sessions/${sessionId}`, data)
}

/** 删除会话（需传入 session_model 校验） */
export function deleteSession(sessionId: number, sessionModel: number) {
  return request.delete<void>(`/api/v1/sessions/${sessionId}`, {
    params: { session_model: sessionModel },
  })
}
