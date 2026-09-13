import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import router from '@/router'
import { LOGIN_PATH } from '@/config/constant'
import { setTokenExpiredHandler } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import '@/styles/index.scss'
import App from './App.vue'

const app = createApp(App)

// 全量注册 Element Plus，后续可按需引入优化体积
app.use(ElementPlus)

const pinia = createPinia()
app.use(pinia)
app.use(router)

// 注册登录态失效回调：40105 或静默刷新失败时，由 axios 拦截器触发——
// 清理用户登录态并跳转登录页（携带当前地址用于登录后回跳）
setTokenExpiredHandler(() => {
  const userStore = useUserStore()
  userStore.clearAuth()
  const currentPath = router.currentRoute.value.fullPath
  if (router.currentRoute.value.path !== LOGIN_PATH) {
    router.push({ path: LOGIN_PATH, query: { redirect: currentPath } })
  }
})

app.mount('#app')
