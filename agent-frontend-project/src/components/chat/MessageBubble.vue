<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, MessageSegment } from '@/types/interview'
import MessageAvatar from './MessageAvatar.vue'
import MsgFile from './MsgFile.vue'
import InterviewCard from './InterviewCard.vue'

/** 单条消息气泡：头像 + 内容 + 时间 */
const props = defineProps<{
  /** 消息数据 */
  message: ChatMessage
}>()

/** 是否为用户消息 */
const isUser = computed(() => props.message.role === 'user')

/** 根据角色类型获取附件列表 */
const segments = computed<MessageSegment[]>(() => {
  return isUser.value
    ? (props.message.request_segments || [])
    : (props.message.response_segments || [])
})

/** 是否显示面试卡片（AI消息且status=1且有interview_id） */
const showInterviewCard = computed(() => {
  return !isUser.value && props.message.status === 1 && props.message.interview_id
})

/** 格式化时间文本 */
const timeText = computed(() => {
  if (props.message.timeText) {
    return props.message.timeText
  }
  if (props.message.created_at) {
    return formatTime(props.message.created_at)
  }
  return ''
})

/** 格式化时间戳为相对时间 */
function formatTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="message-bubble" :class="[message.role]">
    <MessageAvatar :role="message.role" />
    <div class="bubble-body">
      <!-- 消息正文内容（保留换行） -->
      <div v-if="message.content" class="bubble-content">{{ message.content }}</div>

      <!-- 附件区域（如果有） -->
      <template v-if="segments.length > 0">
        <MsgFile
          v-for="(segment, index) in segments"
          :key="`${segment.type}-${segment.name}-${index}`"
          :segment="segment"
          :is-user="isUser"
        />
      </template>

      <!-- 面试卡片（如果 status=1 且有 interview_id） -->
      <InterviewCard
        v-if="showInterviewCard"
        :interview-id="message.interview_id!"
      />

      <!-- 时间戳 -->
      <span v-if="timeText" class="bubble-time">{{ timeText }}</span>
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
  display: flex;
  flex-direction: column;
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
