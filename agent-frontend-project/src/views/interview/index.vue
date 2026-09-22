<script setup lang="ts">
import { onMounted } from 'vue'
import ChatRoom from '@/components/chat/ChatRoom.vue'
import { INTERVIEW_INPUT_ACTIONS } from '@/config/constant'
import { useChatStore } from '@/stores/chat'
import type { SessionModel } from '@/types/interview'

/** 面试间页面：复用聊天室组件，配置面试场景功能按钮 */
const chatStore = useChatStore()

/** 当前会话模式：面试=1 */
const SESSION_MODEL_INTERVIEW: SessionModel = 1

/** 加载会话列表（面试模式） */
async function loadSessions() {
  // 切换模块时重置当前激活的会话，避免默认展示其他模块的会话内容
  chatStore.activeSessionId = ''
  await chatStore.fetchSessions({ session_model: SESSION_MODEL_INTERVIEW, page: 1, page_size: 50 })
}

// 组件挂载时加载会话列表
onMounted(() => {
  loadSessions()
})

/** 处理发送消息（实际应用中这里需要对接发送消息的 API） */
async function handleSend(content: string) {
  // 实际应用中需要调用发送消息的 WebSocket 或 HTTP API
  // 这里只是简单地添加用户消息，AI回复需要后端推送或轮询
  console.log('发送消息:', content)
  
  // 模拟 AI 回复（后续替换为真实接口）
  setTimeout(() => {
    chatStore.addAIMessage('收到！这是模拟的AI回复。')
  }, 1000)
}

/** 处理加载更多消息 */
function handleLoadMore() {
  chatStore.loadMoreMessages()
}

/** 处理功能按钮点击 */
function handleAction(key: string) {
  console.log('功能按钮点击:', key)
}

// 注册发送消息处理器
chatStore.registerSendHandler(handleSend)
</script>

<template>
  <ChatRoom
    placeholder="输入你的回答..."
    :actions="INTERVIEW_INPUT_ACTIONS"
    :messages="chatStore.messages"
    :loading-more="chatStore.loadingMore"
    :has-more="chatStore.hasMoreMessages"
    :disabled="chatStore.isReplying"
    :has-active-session="!!chatStore.activeSessionId"
    @send="chatStore.sendMessage"
    @load-more="handleLoadMore"
    @action="handleAction"
  />
</template>
