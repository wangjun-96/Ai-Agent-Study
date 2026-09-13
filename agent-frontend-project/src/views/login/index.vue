<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormItemRule, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Lock, School, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { DEFAULT_TAB_PATH } from '@/config/constant'
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  USERNAME_MAX_LENGTH,
  USERNAME_MIN_LENGTH,
  validatePasswordStrength,
} from '@/utils/validate'

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

/** 提交表单：登录直接签发令牌；注册成功后自动登录并跳转 */
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (mode.value === 'register') {
      // 注册成功后使用同一凭证自动登录，减少用户操作
      await userStore.register({ username: form.username, password: form.password })
      ElMessage.success('注册成功，正在自动登录...')
      await userStore.login({ username: form.username, password: form.password })
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
      <!-- 品牌区 -->
      <div class="login-brand">
        <span class="brand-logo">
          <el-icon :size="26" color="#ffffff"><School /></el-icon>
        </span>
        <h1 class="brand-title">学面通AI</h1>
        <p class="brand-subtitle">AI 模拟面试与学习辅助平台</p>
      </div>

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

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: $color-primary;
}

.brand-title {
  margin: 14px 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: $color-text-main;
}

.brand-subtitle {
  margin: 0 0 24px;
  font-size: 13px;
  color: $color-text-secondary;
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
