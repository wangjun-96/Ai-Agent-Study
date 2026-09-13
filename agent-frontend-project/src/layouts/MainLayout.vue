<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/sidebar/AppSidebar.vue'
import { MOCK_MESSAGES, MOCK_NOTES, MOCK_SESSIONS } from '@/config/constant'
import { useChatStore } from '@/stores/chat'
import { useNoteStore } from '@/stores/note'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const chatStore = useChatStore()
const noteStore = useNoteStore()
const userStore = useUserStore()

// 布局挂载时初始化默认会话的完整对话并激活（仅首次生效）
chatStore.initSession(MOCK_SESSIONS[0].id, MOCK_MESSAGES)
chatStore.loadSession(MOCK_SESSIONS[0].id)

// 默认激活第一篇笔记（内容懒初始化）
noteStore.selectNote(MOCK_NOTES[0].id)

// 已登录（含刷新页面从 localStorage 恢复登录态）时拉取当前用户信息；
// 令牌失效由请求拦截器统一静默刷新 / 跳转登录页，此处无需额外处理
if (userStore.isLoggedIn) {
  userStore.fetchCurrentUser().catch(() => undefined)
}

/** 当前路由的侧边栏类型：chat 聊天会话 / note 笔记 */
const sidebarType = computed(() => route.meta.sidebar ?? 'chat')
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
        :active-id="chatStore.activeSessionId"
        create-label="新建会话"
        section-label="历史会话"
        @create="chatStore.createSession"
        @select="chatStore.loadSession"
        @rename="chatStore.renameSession"
        @delete="chatStore.deleteSession"
      />

      <!-- 笔记侧边栏 -->
      <AppSidebar
        v-else
        :list="noteStore.notes"
        :active-id="noteStore.activeNoteId"
        create-label="新建笔记"
        section-label="我的笔记"
        @create="noteStore.createNote"
        @select="noteStore.selectNote"
        @rename="noteStore.renameNote"
        @delete="noteStore.deleteNote"
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
