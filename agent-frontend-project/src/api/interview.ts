/**
 * 面试模块接口：获取面试详情。
 * 与后端接口文档（openai.json）保持一致。
 */
import request from '@/utils/request'
import type { InterviewResponse } from '@/types/interview'

/**
 * 获取面试详情
 * @param interviewId 面试记录 ID
 */
export function getInterview(interviewId: number) {
  return request.get<InterviewResponse>(`/api/v1/interviews/${interviewId}`)
}

/** 统一导出别名（兼容组件中使用 useInterviewApi） */
export const useInterviewApi = getInterview
