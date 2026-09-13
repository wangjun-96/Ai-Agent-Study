import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  getCurrentUser,
  login as loginApi,
  register as registerApi,
} from '@/api/auth'
import type { LoginParams, RegisterParams, UserInfo } from '@/types/auth'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/utils/storage'

/**
 * 用户全局状态（Pinia）：
 * 双令牌（内存状态 + localStorage 持久化）、当前登录用户信息、登录登出动作。
 * 页面与组件只调用本 store，不直接操作 token 或 localStorage。
 */
export const useUserStore = defineStore('user', () => {
  // ==================== 状态 ====================

  /** 访问令牌（初始化时从 localStorage 恢复，刷新页面保持登录态） */
  const accessToken = ref<string>(getAccessToken())

  /** 刷新令牌 */
  const refreshToken = ref<string>(getRefreshToken())

  /** 当前登录用户信息（登录后通过 /auth/me 拉取） */
  const userInfo = ref<UserInfo | null>(null)

  /** 当前头像访问地址（后端 /uploads 路径，由 /auth/me 或上传接口返回） */
  const avatarUrl = ref<string>('')

  // ==================== 计算属性 ====================

  /** 是否已登录（以访问令牌是否存在为准，刷新流程由请求拦截器负责） */
  const isLoggedIn = computed<boolean>(() => !!accessToken.value)

  /** 展示用用户名（用户信息未加载时兜底） */
  const username = computed<string>(() => userInfo.value?.username ?? '')

  // ==================== 动作 ====================

  /** 保存双令牌：同步内存状态与 localStorage */
  function saveTokens(access: string, refresh: string): void {
    accessToken.value = access
    refreshToken.value = refresh
    setTokens(access, refresh)
  }

  /** 拉取并缓存当前登录用户信息 */
  async function fetchCurrentUser(): Promise<UserInfo> {
    const res = await getCurrentUser()
    userInfo.value = res.data
    // 头像以服务端记录为准（图片上传成功后后端回写 avatar 字段）
    avatarUrl.value = res.data.avatar ?? ''
    return res.data
  }

  /** 登录：调用接口、持久化令牌、加载用户信息 */
  async function login(params: LoginParams): Promise<void> {
    const res = await loginApi(params)
    saveTokens(res.data.access_token, res.data.refresh_token)
    await fetchCurrentUser()
  }

  /**
   * 注册：multipart 单请求完成建号与可选头像保存（头像随注册表单提交，无需先登录）。
   * 注册成功后由页面直接调用 login 自动登录，再经 /auth/me 拉取含头像的用户信息。
   */
  async function register(params: RegisterParams, avatar?: File | null): Promise<UserInfo> {
    const res = await registerApi(params, avatar)
    return res.data
  }

  /** 清理全部登录态（退出登录 / 令牌失效时调用） */
  function clearAuth(): void {
    accessToken.value = ''
    refreshToken.value = ''
    userInfo.value = null
    avatarUrl.value = ''
    clearTokens()
  }

  /** 主动退出登录：清理登录态（路由跳转由调用方处理） */
  function logout(): void {
    clearAuth()
  }

  return {
    accessToken,
    refreshToken,
    userInfo,
    avatarUrl,
    isLoggedIn,
    username,
    saveTokens,
    fetchCurrentUser,
    login,
    register,
    clearAuth,
    logout,
  }
})
