/**
 * axios 统一封装（业务层禁止裸写 axios，全部通过本实例发起请求）：
 *
 * 1. 请求拦截器：自动注入 Authorization: Bearer <access_token>；
 * 2. 响应拦截器：成功直接返回统一响应体；错误按后端业务码分流——
 *    - 40104 访问令牌过期：使用刷新令牌「单飞」静默换新，并重放原请求；
 *      多个并发请求同时 401 时共享同一次刷新，避免刷新风暴；
 *    - 40105 刷新令牌失效 / 静默刷新失败：清理登录态并跳转登录页；
 *    - 其余错误：统一弹出后端中文 message，页面层不再重复提示；
 * 3. 登录态失效后的清理与跳转通过 setTokenExpiredHandler 注入，
 *    避免本模块与 router / store 产生循环依赖。
 */
import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '@/types/auth'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
} from '@/utils/storage'

/** 扩展 axios 请求配置：标记重试请求与刷新令牌请求，防止刷新死循环 */
declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 401 刷新后是否已重放过（同一请求最多重放一次） */
    _isRetry?: boolean
    /** 是否为刷新令牌接口请求本身 */
    _isRefreshRequest?: boolean
  }
}

/** 请求超时时间（毫秒） */
const REQUEST_TIMEOUT = 15000

/** 后端业务码：访问令牌无效或已过期 */
const BIZ_ACCESS_TOKEN_INVALID = 40104
/** 后端业务码：刷新令牌无效或已过期 */
const BIZ_REFRESH_TOKEN_INVALID = 40105

/** 登录态失效处理器（由 main.ts 注入：清理 store + 跳转登录页） */
let tokenExpiredHandler: (() => void) | null = null

/**
 * 注册登录态失效回调。
 * 在 Pinia / Router 就绪后由应用入口调用，避免模块间循环依赖。
 */
export function setTokenExpiredHandler(handler: () => void): void {
  tokenExpiredHandler = handler
}

/** 创建 axios 实例：baseURL 由环境变量统一管理，开发环境置空走 Vite 代理 */
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ==================== 请求拦截器 ====================

service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 刷新令牌接口使用 refresh_token 鉴权语义，无需携带访问令牌
    if (!config._isRefreshRequest) {
      const accessToken = getAccessToken()
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`
      }
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ==================== 静默刷新（单飞） ====================

/** 进行中的刷新 Promise：并发 401 共享同一次刷新，null 表示当前无刷新 */
let refreshingPromise: Promise<string | null> | null = null

/** 防止失效处理（提示 + 跳转）在并发请求下重复触发 */
let isExpiredHandling = false

/** 统一处理登录态失效：提示一次，清理令牌并跳转登录页 */
function handleTokenExpired(): void {
  if (isExpiredHandling) return
  isExpiredHandling = true
  ElMessage.warning('登录状态已过期，请重新登录')
  clearTokens()
  tokenExpiredHandler?.()
  // 跳转完成后释放标记，后续重新登录仍可正常处理
  window.setTimeout(() => {
    isExpiredHandling = false
  }, 1000)
}

/**
 * 使用刷新令牌换取新的访问令牌（单飞）。
 * @returns 新访问令牌；刷新失败或无刷新令牌时返回 null
 */
function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return Promise.resolve(null)
  }
  // 已有刷新进行中时直接复用，保证并发请求只触发一次刷新
  if (!refreshingPromise) {
    refreshingPromise = service
      .post('/auth/refresh', { refresh_token: refreshToken }, { _isRefreshRequest: true })
      .then((res) => {
        // 成功拦截器已返回统一响应体，res.data 即 AccessTokenResult
        const newToken = (res.data as { access_token?: string } | undefined)
          ?.access_token
        if (newToken) {
          setAccessToken(newToken)
          return newToken
        }
        return null
      })
      .catch(() => null)
      .finally(() => {
        refreshingPromise = null
      })
  }
  return refreshingPromise
}

// ==================== 响应拦截器 ====================

service.interceptors.response.use(
  // HTTP 2xx：后端统一响应体 code 恒为 0，直接返回响应体供业务层取 data
  (response) => response.data,
  async (error: AxiosError<ApiResponse>) => {
    const config = error.config as InternalAxiosRequestConfig | undefined

    // 刷新令牌请求自身失败：不在此提示 / 跳转，交由触发刷新的调用方统一处理
    if (config?._isRefreshRequest) {
      return Promise.reject(error)
    }

    // 无 response：网络断开 / 跨域 / 超时等，axios 无法拿到响应体
    if (!error.response) {
      ElMessage.error('网络连接异常，请检查网络后重试')
      return Promise.reject(error)
    }

    const body = error.response.data
    const code = body?.code
    const message = body?.message || '请求失败，请稍后重试'

    // 40104：访问令牌过期/无效，尝试静默刷新后重放原请求（仅一次）
    if (code === BIZ_ACCESS_TOKEN_INVALID && config && !config._isRetry) {
      const newToken = await refreshAccessToken()
      if (newToken) {
        config._isRetry = true
        config.headers.Authorization = `Bearer ${newToken}`
        return service(config)
      }
      // 无刷新令牌或刷新失败：登录态已失效
      handleTokenExpired()
      return Promise.reject(error)
    }

    // 40105：刷新令牌无效或已过期，无法静默续期，清理登录态并跳登录页
    if (code === BIZ_REFRESH_TOKEN_INVALID) {
      handleTokenExpired()
      return Promise.reject(error)
    }

    // 其余业务 / 参数 / 限流 / 系统错误：统一展示后端中文提示
    ElMessage({
      type: 'error',
      message,
      showClose: true,
      duration: 3000,
    })
    return Promise.reject(error)
  },
)

/** 统一请求方法类型：拦截器成功时返回后端响应体本身 */
export interface Request {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
  post<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>>
  put<T = unknown>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>>
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>>
}

export default service as unknown as Request
