<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/sidebar/AppSidebar.vue'
import { useChatStore } from '@/stores/chat'
import { useNoteStore } from '@/stores/note'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const chatStore = useChatStore()
const noteStore = useNoteStore()
const userStore = useUserStore()

// 已登录（含刷新页面从 localStorage 恢复登录态）时拉取当前用户信息；
// 令牌失效由请求拦截器统一静默刷新 / 跳转登录页，此处无需额外处理
if (userStore.isLoggedIn) {
  userStore.fetchCurrentUser().catch(() => undefined)
}

/** 当前路由的侧边栏类型：chat 聊天会话 / note 笔记 */
const sidebarType = computed(() => route.meta.sidebar ?? 'chat')

/** 根据会话模式获取侧边栏配置 */
const sidebarConfig = computed(() => {
  if (sidebarType.value === 'chat') {
    return {
      createLabel: '新建会话',
      sectionLabel: '历史会话',
    }
  }
  return {
    createLabel: '新建笔记',
    sectionLabel: '我的笔记',
  }
})

/** 创建新会话/笔记 */
async function handleCreate() {
  if (sidebarType.value === 'chat') {
    await chatStore.createSession('新会话', 0)
  } else {
    noteStore.createNote()
  }
}

/** 选择会话/笔记 */
async function handleSelect(id: string | number) {
  if (sidebarType.value === 'chat') {
    await chatStore.loadSession(typeof id === 'string' ? Number(id) : id)
  } else {
    noteStore.selectNote(String(id))
  }
}

/** 重命名会话/笔记 */
async function handleRename(id: string | number, title: string) {
  if (sidebarType.value === 'chat') {
    await chatStore.renameSession(typeof id === 'string' ? Number(id) : id, title)
  } else {
    noteStore.renameNote(String(id), title)
  }
}

/** 删除会话/笔记 */
async function handleDelete(id: string | number) {
  if (sidebarType.value === 'chat') {
    await chatStore.deleteSession(typeof id === 'string' ? Number(id) : id)
  } else {
    noteStore.deleteNote(String(id))
  }
}
</script>

<template>
  <div class="main-layout">
    <!-- 顶部：全屏导航栏（Logo + 项目名 + 模块切换） -->
    <AppHeader />

    <!-- 主体：侧边栏（按路由切换数据源） + 路由页面 -->
    <div class="layout-body">
      <!-- 聊天会话侧边栏 -->
      <AppSidebar
        v-if="sidebarType === 'chat'"
        :list="chatStore.sessions"
        :active-id="String(chatStore.activeSessionId)"
        :create-label="sidebarConfig.createLabel"
        :section-label="sidebarConfig.sectionLabel"
        @create="handleCreate"
        @select="handleSelect"
        @rename="handleRename"
        @delete="handleDelete"
      />

      <!-- 笔记侧边栏 -->
      <AppSidebar
        v-else
        :list="noteStore.notes"
        :active-id="noteStore.activeNoteId"
        :create-label="sidebarConfig.createLabel"
        :section-label="sidebarConfig.sectionLabel"
        @create="handleCreate"
        @select="handleSelect"
        @rename="handleRename"
        @delete="handleDelete"
      />

      <main class="layout-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.main-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.layout-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.layout-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
</style>
