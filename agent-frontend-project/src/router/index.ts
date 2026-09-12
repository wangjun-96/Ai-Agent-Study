import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { DEFAULT_TAB_PATH } from '@/config/constant'
import MainLayout from '@/layouts/MainLayout.vue'

/** 全局集中路由配置：按业务模块分组，元信息统一在此维护 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: DEFAULT_TAB_PATH,
    children: [
      {
        path: 'study',
        name: 'Study',
        component: () => import('@/views/study/index.vue'),
        meta: { title: '学习室', sidebar: 'chat' },
      },
      {
        path: 'interview',
        name: 'Interview',
        component: () => import('@/views/interview/index.vue'),
        meta: { title: '面试间', sidebar: 'chat' },
      },
      {
        path: 'note',
        name: 'Note',
        component: () => import('@/views/note/index.vue'),
        meta: { title: '笔记本', sidebar: 'note' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/** 全局前置守卫：统一设置页面标题 */
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - 学面通AI` : '学面通AI'
  next()
})

export default router
