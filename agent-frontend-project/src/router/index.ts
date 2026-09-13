import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { DEFAULT_TAB_PATH, LOGIN_PATH } from '@/config/constant'
import MainLayout from '@/layouts/MainLayout.vue'
import { useUserStore } from '@/stores/user'

/** 全局集中路由配置：按业务模块分组，元信息统一在此维护 */
const routes: RouteRecordRaw[] = [
  {
    path: LOGIN_PATH,
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/',
    component: MainLayout,
    redirect: DEFAULT_TAB_PATH,
    children: [
      {
        path: 'study',
        name: 'Study',
        component: () => import('@/views/study/index.vue'),
        meta: { title: '学习室', sidebar: 'chat', requiresAuth: true },
      },
      {
        path: 'interview',
        name: 'Interview',
        component: () => import('@/views/interview/index.vue'),
        meta: { title: '面试间', sidebar: 'chat', requiresAuth: true },
      },
      {
        path: 'note',
        name: 'Note',
        component: () => import('@/views/note/index.vue'),
        meta: { title: '笔记本', sidebar: 'note', requiresAuth: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 全局前置守卫：
 * 1. 未登录访问受保护页面 → 跳转登录页并携带 redirect 回跳地址；
 * 2. 已登录访问登录页 → 直接进入默认首页；
 * 3. 统一设置页面标题。
 */
router.beforeEach((to) => {
  const userStore = useUserStore()
  const requiresAuth = to.meta.requiresAuth !== false

  // 未登录访问受保护页面：跳转登录页并携带 redirect 回跳地址
  if (requiresAuth && !userStore.isLoggedIn) {
    return { path: LOGIN_PATH, query: { redirect: to.fullPath } }
  }

  // 已登录访问登录页：直接进入默认首页
  if (to.path === LOGIN_PATH && userStore.isLoggedIn) {
    return DEFAULT_TAB_PATH
  }

  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - 学面通AI` : '学面通AI'
  return true
})

export default router
