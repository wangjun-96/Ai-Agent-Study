<script setup lang="ts">
import { computed } from 'vue'
import type { InputAction, ChatMessage } from '@/types/interview'
import ChatMessageList from './ChatMessageList.vue'
import ChatInputBar from './ChatInputBar.vue'

/**
 * 聊天室组合组件：消息列表 + 输入区。
 * 面试间 / 学习室等聊天式页面共用，占位文案与功能按钮均可配置
 */
interface Props {
  /** 输入框占位文案 */
  placeholder?: string
  /** 输入区功能按钮配置 */
  actions?: InputAction[]
  /** 消息列表 */
  messages?: ChatMessage[]
  /** 是否正在加载更多消息 */
  loadingMore?: boolean
  /** 是否还有更多消息 */
  hasMore?: boolean
  /** AI 是否正在回复 */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '输入你的回答...',
  actions: () => [],
  messages: () => [],
  loadingMore: false,
  hasMore: true,
  disabled: false,
})

const emit = defineEmits<{
  (e: 'send', content: string): void
  (e: 'loadMore'): void
  (e: 'action', key: string): void
}>()

/** 是否禁用输入（AI回复中） */
const isInputDisabled = computed(() => props.disabled)

/** 发送消息 */
function handleSend(content: string) {
  emit('send', content)
}

/** 加载更多消息 */
function handleLoadMore() {
  emit('loadMore')
}

/** 功能按钮点击 */
function handleAction(key: string) {
  emit('action', key)
}
</script>

<template>
  <div class="chat-room">
    <!-- 聊天消息区 -->
    <ChatMessageList
      :list="messages"
      :loading-more="loadingMore"
      :has-more="hasMore"
      @load-more="handleLoadMore"
    />

    <!-- 底部输入区 -->
    <ChatInputBar
      :disabled="isInputDisabled"
      :placeholder="placeholder"
      :actions="actions"
      @send="handleSend"
      @action="handleAction"
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
