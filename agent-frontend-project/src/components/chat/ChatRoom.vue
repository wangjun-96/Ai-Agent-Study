<script setup lang="ts">
import { computed } from 'vue'
import type { InputAction, ChatMessage } from '@/types/interview'
import ChatMessageList from './ChatMessageList.vue'
import ChatInputBar from './ChatInputBar.vue'

/**
 * 聊天室组合组件：消息列表 + 输入区。
 * 面试间 / 学习室等聊天式页面共用，占位文案与功能按钮均可配置。
 *
 * 只有当 hasActiveSession 为 true（即用户已在侧边栏点击了某个会话）
 * 时才会渲染消息列表与输入框；进入模块的默认状态不显示任何聊天内容。
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
  /** 是否已选中会话：只有为 true 时才显示消息列表与输入框 */
  hasActiveSession?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '输入你的回答...',
  actions: () => [],
  messages: () => [],
  loadingMore: false,
  hasMore: true,
  disabled: false,
  hasActiveSession: false,
})

const emit = defineEmits<{
  (e: 'send', content: string): void
  (e: 'loadMore'): void
  (e: 'action', key: string): void
}>()

/** 是否禁用输入（AI回复中） */
const isInputDisabled = computed(() => props.disabled)

/** 是否应该展示聊天主体（消息列表 + 输入框） */
const showChat = computed(() => props.hasActiveSession)

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
    <!-- 默认空状态：未选中任何会话时不显示消息列表与输入框 -->
    <div v-if="!showChat" class="chat-empty">
      <slot name="empty">
        <div class="chat-empty__inner">
          <p class="chat-empty__title">未选择会话</p>
          <p class="chat-empty__desc">请点击左侧侧边栏中的某个会话以查看消息列表</p>
        </div>
      </slot>
    </div>

    <template v-else>
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
    </template>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.chat-room {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  // 与项目主色调（品牌黄 + 米色背景）保持一致：自上而下的暖色渐变
  background: linear-gradient(
    180deg,
    $color-bg-page 0%,
    $color-primary-light 100%
  );
}

.chat-empty__inner {
  text-align: center;
  color: $color-text-main;
  padding: 24px 32px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid $color-primary-border;
  border-radius: $radius-lg;
  box-shadow: 0 2px 12px rgba(251, 197, 49, 0.12);
}

.chat-empty__title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
  color: $color-primary-hover;
}

.chat-empty__desc {
  font-size: 13px;
  margin: 0;
  color: $color-text-secondary;
}
</style>
