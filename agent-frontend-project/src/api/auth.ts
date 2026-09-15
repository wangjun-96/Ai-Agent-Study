/**
 * 认证模块接口：注册、登录、刷新令牌、获取当前登录用户、文件上传。
 * 入参 / 出参均有完整 TS 类型，路径与后端接口文档保持一致：
 * - 认证接口统一前缀 /api/v1/auth（注册/登录/刷新匿名公开，由 Vite 代理转发）；
 * - 文件上传为 /api/v1 下的已认证业务接口，由 Vite 代理转发；
 * - 受保护接口通过请求拦截器自动携带 Bearer 令牌。
 */
import request from '@/utils/request'
import type {
  AccessTokenResult,
  FileUploadResult,
  LoginParams,
  RegisterParams,
  TokenResult,
  UserInfo,
} from '@/types/auth'

/**
 * 用户注册（成功 HTTP 201，返回脱敏后的用户信息）。
 *
 * 后端注册接口为 multipart/form-data：username/password 文本字段 + 可选 avatar 头像，
 * 建号与头像保存在同一个请求完成，无需注册后再登录二次上传。
 *
 * 必须显式声明 multipart/form-data：axios 实例默认头是 application/json，
 * 不覆盖时 FormData 会被 JSON 序列化导致字段丢失；此处不带 boundary，
 * 由浏览器在发送时自动追加 multipart 边界。
 */
export function register(params: RegisterParams, avatar?: File | null) {
  const formData = new FormData()
  formData.append('username', params.username)
  formData.append('password', params.password)
  if (avatar) {
    formData.append('avatar', avatar)
  }
  return request.post<UserInfo>('/api/v1/auth/register', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 用户登录（成功返回 Access/Refresh 双令牌） */
export function login(data: LoginParams) {
  return request.post<TokenResult>('/api/v1/auth/login', data)
}

/** 使用刷新令牌静默换取新的访问令牌 */
export function refreshToken(refreshToken: string) {
  return request.post<AccessTokenResult>('/api/v1/auth/refresh', { refresh_token: refreshToken })
}

/** 获取当前登录用户信息（需携带访问令牌） */
export function getCurrentUser() {
  return request.get<UserInfo>('/api/v1/auth/me')
}

/**
 * 通用文件上传（需先登录，Authorization 头由请求拦截器自动注入）。
 * multipart/form-data 表单字段名 file，与后端 POST /api/v1/files/upload 约定一致；
 * 后端按内容自动分类：图片保存后回写用户 avatar，文档仅保存。
 *
 * 必须显式声明 multipart/form-data：axios 实例默认头是 application/json，
 * 不覆盖时 FormData 会被 JSON 序列化导致文件字段丢失；此处不带 boundary，
 * 由浏览器在发送时自动追加 multipart 边界。
 */
export function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<FileUploadResult>('/api/v1/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
