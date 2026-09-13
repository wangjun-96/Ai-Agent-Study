import 'vue-router'

/** 扩展路由 meta 类型定义 */
declare module 'vue-router' {
  interface RouteMeta {
    /** 页面标题（守卫中用于设置 document.title） */
    title?: string
    /** 侧边栏类型：chat 聊天会话列表（默认）/ note 笔记列表 */
    sidebar?: 'chat' | 'note'
    /** 是否需要登录鉴权：true 未登录跳转登录页；false 为登录页等公开路由 */
    requiresAuth?: boolean
  }
}

export {}
