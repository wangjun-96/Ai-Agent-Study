/**
 * 认证模块接口：注册、登录、刷新令牌、获取当前登录用户。
 * 入参 / 出参均有完整 TS 类型，路径与后端接口文档保持一致：
 * - 认证接口统一前缀 /auth（匿名公开，由 Vite 代理转发）；
 * - 受保护接口通过请求拦截器自动携带 Bearer 令牌。
 */
import request from '@/utils/request'
import type {
  AccessTokenResult,
  LoginParams,
  RegisterParams,
  TokenResult,
  UserInfo,
} from '@/types/auth'

/** 用户注册（成功 HTTP 201，返回脱敏后的用户信息） */
export function register(data: RegisterParams) {
  return request.post<UserInfo>('/auth/register', data)
}

/** 用户登录（成功返回 Access/Refresh 双令牌） */
export function login(data: LoginParams) {
  return request.post<TokenResult>('/auth/login', data)
}

/** 使用刷新令牌静默换取新的访问令牌 */
export function refreshToken(refreshToken: string) {
  return request.post<AccessTokenResult>('/auth/refresh', { refresh_token: refreshToken })
}

/** 获取当前登录用户信息（需携带访问令牌） */
export function getCurrentUser() {
  return request.get<UserInfo>('/auth/me')
}
