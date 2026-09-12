<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage } from '@/types/interview'
import MessageBubble from './MessageBubble.vue'

/** 消息列表容器：滚动区域，新消息到达后自动滚到底部 */
interface Props {
  /** 消息列表 */
  list: ChatMessage[]
}

const props = defineProps<Props>()

/** 滚动容器引用 */
const scrollRef = ref<HTMLElement>()

// 监听消息数量变化，自动平滑滚动到底部
watch(
  () => props.list.length,
  async () => {
    await nextTick()
    scrollRef.value?.scrollTo({ top: scrollRef.value.scrollHeight, behavior: 'smooth' })
  },
)
</script>

<template>
  <div ref="scrollRef" class="chat-message-list">
    <div class="message-flow">
      <MessageBubble v-for="msg in list" :key="msg.id" :message="msg" />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.chat-message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: $color-bg-page;
}

/* 消息流：居中限宽排布 */
.message-flow {
  display: flex;
  flex-direction: column;
  gap: 28px;
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 24px 24px;
}
</style>
