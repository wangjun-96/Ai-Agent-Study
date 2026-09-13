/**
 * localStorage 统一封装：仅用于访问令牌 / 刷新令牌的持久化。
 * 业务层不允许直接操作 window.localStorage，统一走本工具。
 */

/** 访问令牌存储键 */
const ACCESS_TOKEN_KEY = 'agent_access_token'

/** 刷新令牌存储键 */
const REFRESH_TOKEN_KEY = 'agent_refresh_token'

/** 读取访问令牌 */
export function getAccessToken(): string {
  return localStorage.getItem(ACCESS_TOKEN_KEY) ?? ''
}

/** 读取刷新令牌 */
export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? ''
}

/** 持久化双令牌（登录成功 / 刷新成功后调用） */
export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

/** 仅更新访问令牌（静默刷新成功后调用，刷新令牌保持不变） */
export function setAccessToken(accessToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
}

/** 清除全部令牌（退出登录 / 登录态失效时调用） */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}
