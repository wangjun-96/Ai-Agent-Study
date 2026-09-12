<script setup lang="ts">
import type { ChatMessage } from '@/types/interview'
import MessageAvatar from './MessageAvatar.vue'

/** 单条消息气泡：头像 + 内容 + 时间 */
defineProps<{
  /** 消息数据 */
  message: ChatMessage
}>()
</script>

<template>
  <div class="message-bubble">
    <MessageAvatar :role="message.role" />
    <div class="bubble-body">
      <!-- 消息内容（保留换行） -->
      <div class="bubble-content">{{ message.content }}</div>
      <span class="bubble-time">{{ message.timeText }}</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.message-bubble {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.bubble-body {
  min-width: 0;
  max-width: 620px;
}

.bubble-content {
  padding: 14px 20px;
  border-radius: $radius-lg;
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;

  /* AI 消息：白底描边气泡 */
  .ai & {
    background: $color-bg-white;
    border: 1px solid $color-border;
  }

  /* 用户消息：浅灰气泡 */
  .user & {
    background: $color-bubble-user;
  }
}

.bubble-time {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  color: $color-text-secondary;
}
</style>
