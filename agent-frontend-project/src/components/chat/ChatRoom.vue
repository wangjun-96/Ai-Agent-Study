<script setup lang="ts">
import ChatMessageList from './ChatMessageList.vue'
import ChatInputBar from './ChatInputBar.vue'
import { useChatStore } from '@/stores/chat'
import type { InputAction } from '@/types/interview'

/**
 * 聊天室组合组件：消息列表 + 输入区。
 * 面试间 / 学习室等聊天式页面共用，占位文案与功能按钮均可配置
 */
interface Props {
  /** 输入框占位文案 */
  placeholder?: string
  /** 输入区功能按钮配置 */
  actions?: InputAction[]
}

withDefaults(defineProps<Props>(), {
  placeholder: '输入你的回答...',
  actions: () => [],
})

const chatStore = useChatStore()
</script>

<template>
  <div class="chat-room">
    <!-- 聊天消息区 -->
    <ChatMessageList :list="chatStore.messages" />

    <!-- 底部输入区 -->
    <ChatInputBar
      :disabled="chatStore.isReplying"
      :placeholder="placeholder"
      :actions="actions"
      @send="chatStore.sendMessage"
    />
  </div>
</template>

<style scoped lang="scss">
.chat-room {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
</style>
