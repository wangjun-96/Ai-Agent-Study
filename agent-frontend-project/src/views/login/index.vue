<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormItemRule, FormRules, UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Camera, Lock, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { BRAND_LOGO_URL, DEFAULT_AVATAR_URL, DEFAULT_TAB_PATH } from '@/config/constant'
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  USERNAME_MAX_LENGTH,
  USERNAME_MIN_LENGTH,
  validatePasswordStrength,
} from '@/utils/validate'

/** 头像文件大小上限：2MB */
const AVATAR_MAX_SIZE = 2 * 1024 * 1024

/** 允许的头像图片类型 */
const AVATAR_ACCEPT = 'image/png,image/jpeg,image/webp'

/** 页面模式：登录 / 注册 */
type AuthMode = 'login' | 'register'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

/** 当前模式（默认登录） */
const mode = ref<AuthMode>('login')

/** 表单引用 */
const formRef = ref<FormInstance>()

/** 表单数据（登录 / 注册共用） */
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

/** 提交中状态（防止重复提交） */
const loading = ref(false)

/** 头像预览地址：默认展示网络占位图，选择本地文件后替换为本地预览 */
const avatarUrl = ref<string>(DEFAULT_AVATAR_URL)

/** 用户选中的头像文件：选图时仅本地预览，提交注册时随 multipart 表单一并上传 */
const avatarFile = ref<File | null>(null)

/** 当前头像的本地 ObjectURL（用于离开页面 / 重置时释放内存） */
let avatarObjectUrl: string | null = null

/** 释放本地头像预览占用的 ObjectURL */
function revokeAvatarObjectUrl(): void {
  if (avatarObjectUrl) {
    URL.revokeObjectURL(avatarObjectUrl)
    avatarObjectUrl = null
  }
}

/**
 * 选择头像文件：仅做类型 / 大小校验与本地预览，不发起任何请求。
 * 点击注册时头像随 multipart 注册表单一起提交，建号与头像保存一个请求完成。
 */
function handleAvatarChange(file: UploadFile): void {
  const raw = file.raw
  if (!raw) return
  if (!raw.type.startsWith('image/')) {
    ElMessage.warning('仅支持上传图片格式的头像')
    return
  }
  if (raw.size > AVATAR_MAX_SIZE) {
    ElMessage.warning('头像大小不能超过 2MB')
    return
  }
  revokeAvatarObjectUrl()
  avatarObjectUrl = URL.createObjectURL(raw)
  avatarUrl.value = avatarObjectUrl
  avatarFile.value = raw
}

/** 头像重置回默认占位图并清空已选文件 */
function resetAvatar(): void {
  revokeAvatarObjectUrl()
  avatarUrl.value = DEFAULT_AVATAR_URL
  avatarFile.value = null
}

onBeforeUnmount(() => {
  revokeAvatarObjectUrl()
})

/** 用户名校验规则：必填 + 长度区间，与后端约束一致 */
const usernameRules: FormItemRule[] = [
  { required: true, message: '请输入用户名', trigger: 'blur' },
  {
    min: USERNAME_MIN_LENGTH,
    max: USERNAME_MAX_LENGTH,
    message: `用户名长度需为 ${USERNAME_MIN_LENGTH}-${USERNAME_MAX_LENGTH} 个字符`,
    trigger: 'blur',
  },
]

/** 登录密码规则：必填 + 长度区间（登录不做强度校验，凭证错误由后端判定） */
const loginPasswordRules: FormItemRule[] = [
  { required: true, message: '请输入密码', trigger: 'blur' },
  {
    min: PASSWORD_MIN_LENGTH,
    max: PASSWORD_MAX_LENGTH,
    message: `密码长度需为 ${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} 个字符`,
    trigger: 'blur',
  },
]

/** 注册密码规则：必填 + 长度 + 强度（字母数字组合、禁止包含用户名） */
const registerPasswordRules: FormItemRule[] = [
  { required: true, message: '请输入密码', trigger: 'blur' },
  {
    min: PASSWORD_MIN_LENGTH,
    max: PASSWORD_MAX_LENGTH,
    message: `密码长度需为 ${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} 个字符`,
    trigger: 'blur',
  },
  {
    validator: (_rule, value: string, callback: (error?: Error) => void) => {
      const reason = validatePasswordStrength(value, form.username)
      if (reason) {
        callback(new Error(reason))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  },
]

/** 确认密码规则：必填且与密码一致 */
const confirmPasswordRules: FormItemRule[] = [
  { required: true, message: '请再次输入密码', trigger: 'blur' },
  {
    validator: (_rule, value: string, callback: (error?: Error) => void) => {
      if (value !== form.password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  },
]

/** 动态表单规则：随模式切换校验项 */
const formRules = computed<FormRules>(() => ({
  username: usernameRules,
  password: mode.value === 'register' ? registerPasswordRules : loginPasswordRules,
  confirmPassword: mode.value === 'register' ? confirmPasswordRules : [],
}))

/** 切换登录 / 注册模式：重置表单与校验状态，切换本身不触发任何校验提示 */
function switchMode(target: AuthMode): void {
  if (mode.value === target) return
  mode.value = target
  formRef.value?.resetFields()
  form.confirmPassword = ''
  resetAvatar()
  // 规则切换、新表单项挂载后统一清除校验态，必填提示只允许由失焦或提交触发
  nextTick(() => formRef.value?.clearValidate())
}

/** 登录成功后的跳转地址：优先 redirect 参数，兜底默认首页 */
function resolveRedirectPath(): string {
  const redirect = route.query.redirect
  if (typeof redirect === 'string' && redirect.startsWith('/')) {
    return redirect
  }
  return DEFAULT_TAB_PATH
}

/** 提交表单：注册为「multipart 建号（含可选头像）→ 自动登录」两步；登录直接签发令牌 */
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (mode.value === 'register') {
      // 第一步：用户名、密码与可选头像一个 multipart 请求完成注册（头像在后端随建号保存）
      await userStore.register(
        { username: form.username, password: form.password },
        avatarFile.value,
      )
      // 第二步：注册成功后使用同一凭证自动登录，获取访问令牌并拉取含头像的用户信息
      await userStore.login({ username: form.username, password: form.password })
      ElMessage.success('注册成功')
    } else {
      await userStore.login({ username: form.username, password: form.password })
      ElMessage.success('登录成功')
    }
    router.push(resolveRedirectPath())
  } catch {
    // 接口错误文案已由 axios 响应拦截器统一提示，此处仅恢复提交状态
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <!-- 品牌区：小 Logo 与标题并排 -->
      <div class="login-brand">
        <div class="brand-row">
          <img class="brand-logo" :src="BRAND_LOGO_URL" alt="学面通AI Logo" />
          <h1 class="brand-title">学面通AI</h1>
        </div>
        <p class="brand-subtitle">AI 模拟面试与学习辅助平台</p>
      </div>

      <!-- 注册头像选择：选图仅本地预览，提交注册时随 multipart 表单上传，可不上传 -->
      <el-upload
        v-if="mode === 'register'"
        class="avatar-uploader"
        :accept="AVATAR_ACCEPT"
        :show-file-list="false"
        :auto-upload="false"
        :on-change="handleAvatarChange"
      >
        <img class="avatar-img" :src="avatarUrl" alt="头像预览" />
        <span class="avatar-mask">
          <el-icon :size="18"><Camera /></el-icon>
          <span class="avatar-mask-text">更换</span>
        </span>
      </el-upload>

      <!-- 模式切换 -->
      <div class="mode-switch">
        <button
          type="button"
          class="mode-item"
          :class="{ 'is-active': mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="mode-item"
          :class="{ 'is-active': mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <!-- 登录 / 注册表单 -->
      <!-- validate-on-rule-change=false：登录/注册模式切换导致 rules 变化时
           不自动校验，必填提示仅在字段失焦或点击提交时出现 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        :validate-on-rule-change="false"
        class="login-form"
        label-position="top"
        size="large"
        @keyup.enter="handleSubmit"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :maxlength="USERNAME_MAX_LENGTH"
            clearable
          >
            <template #prefix>
              <el-icon class="input-prefix-icon"><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :maxlength="PASSWORD_MAX_LENGTH"
            show-password
          >
            <template #prefix>
              <el-icon class="input-prefix-icon"><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="mode === 'register'" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            :maxlength="PASSWORD_MAX_LENGTH"
            show-password
          >
            <template #prefix>
              <el-icon class="input-prefix-icon"><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-button
          type="primary"
          class="submit-btn"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <!-- 底部模式切换文案 -->
      <p class="mode-tip">
        {{ mode === 'login' ? '还没有账号？' : '已有账号？' }}
        <span class="mode-link" @click="switchMode(mode === 'login' ? 'register' : 'login')">
          {{ mode === 'login' ? '立即注册' : '去登录' }}
        </span>
      </p>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
  background: $color-bg-page;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 36px 36px 28px;
  background: $color-bg-white;
  border-radius: $radius-lg;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}

.login-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Logo 与标题并排的一行 */
.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 2px 8px rgba(251, 197, 49, 0.35);
}

.brand-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: $color-text-main;
}

.brand-subtitle {
  margin: 8px 0 20px;
  font-size: 13px;
  color: $color-text-secondary;
}

/* 注册头像选择：圆形预览 + hover 遮罩 */
.avatar-uploader {
  display: flex;
  justify-content: center;
  margin-bottom: 18px;

  :deep(.el-upload) {
    position: relative;
    width: 84px;
    height: 84px;
    overflow: hidden;
    border: 1px solid $color-border;
    border-radius: 50%;
    cursor: pointer;
    transition: border-color 0.2s;

    &:hover {
      border-color: $color-primary-border;

      .avatar-mask {
        opacity: 1;
      }
    }
  }
}

.avatar-img {
  display: block;
  width: 84px;
  height: 84px;
  object-fit: cover;
}

.avatar-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #ffffff;
  background: rgba(0, 0, 0, 0.45);
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-mask-text {
  font-size: 12px;
  line-height: 1;
}

.mode-switch {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
  padding: 4px;
  background: $color-bg-gray;
  border-radius: $radius-md;
}

.mode-item {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: $radius-md;
  background: transparent;
  font-size: 14px;
  color: $color-text-main;
  cursor: pointer;
  transition:
    background-color 0.2s,
    color 0.2s;

  &.is-active {
    background: $color-bg-white;
    color: $color-text-main;
    font-weight: 600;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  }
}

.login-form {
  :deep(.el-form-item) {
    margin-bottom: 20px;
  }
}

/* 输入框前缀图标：弱化颜色，避免视觉过硬 */
.input-prefix-icon {
  color: $color-text-secondary;
}

.submit-btn {
  width: 100%;
  height: 42px;
  margin-top: 4px;
  font-size: 15px;
  color: $color-text-main;
  background: $color-primary;
  border-color: $color-primary;

  &:hover,
  &:focus {
    color: $color-text-main;
    background: $color-primary-hover;
    border-color: $color-primary-hover;
  }
}

.mode-tip {
  margin: 18px 0 0;
  text-align: center;
  font-size: 13px;
  color: $color-text-secondary;
}

.mode-link {
  color: $color-primary-hover;
  cursor: pointer;

  &:hover {
    text-decoration: underline;
  }
}
</style>
