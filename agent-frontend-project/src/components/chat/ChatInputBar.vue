<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Component } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  DataAnalysis,
  Document,
  Edit,
  Microphone,
  Paperclip,
  Promotion,
  Reading,
  Upload,
} from '@element-plus/icons-vue'
import type { InputAction } from '@/types/interview'

/**
 * 底部输入区：多行输入 + 功能按钮组（由外部配置）+ 发送按钮。
 * 功能按钮均为轻量化预留入口，点击统一提示
 */
interface Props {
  /** AI 回复期间禁用输入 */
  disabled?: boolean
  /** 输入框占位文案 */
  placeholder?: string
  /** 左侧功能按钮配置 */
  actions?: InputAction[]
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  placeholder: '输入你的回答...',
  actions: () => [],
})

const emit = defineEmits<{
  (e: 'send', content: string): void
  (e: 'action', key: string): void
}>()

/** 功能按钮图标名 -> 图标组件映射（漏配时回退到附件图标） */
const ACTION_ICONS: Record<string, Component> = {
  ChatDotRound,
  DataAnalysis,
  Document,
  Edit,
  Microphone,
  Reading,
  Upload,
}

/** 输入框内容 */
const inputText = ref('')

/** 是否可发送：内容非空且未处于回复中 */
const canSend = computed(() => inputText.value.trim().length > 0 && !props.disabled)

/** 发送消息：清空输入框并通知父级 */
function handleSend(): void {
  if (!canSend.value) return
  emit('send', inputText.value)
  inputText.value = ''
}

/** 预留功能按钮统一提示 */
function handleReserved(key: string, label: string): void {
  emit('action', key)
  ElMessage.info(`${label}功能开发中`)
}
</script>

<template>
  <footer class="chat-input-bar">
    <div class="input-card">
      <el-input
        v-model="inputText"
        class="chat-textarea"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="placeholder"
        :disabled="disabled"
        @keydown.enter.exact.prevent="handleSend"
      />

      <div class="input-actions">
        <!-- 左侧：功能按钮组（按页面配置渲染） -->
        <div class="action-left">
          <el-button
            v-for="action in actions"
            :key="action.key"
            text
            size="small"
            class="feature-btn"
            @click="handleReserved(action.key, action.label)"
          >
            <el-icon :size="15"><component :is="ACTION_ICONS[action.icon] ?? Paperclip" /></el-icon>
            {{ action.label }}
          </el-button>
        </div>

        <!-- 右侧：发送按钮 -->
        <button type="button" class="send-btn" :disabled="!canSend" @click="handleSend">
          <el-icon :size="18" color="#ffffff"><Promotion /></el-icon>
        </button>
      </div>
    </div>
  </footer>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.chat-input-bar {
  flex-shrink: 0;
  padding: 8px 24px 24px;
  background: $color-bg-page;
}

.input-card {
  max-width: 760px;
  margin: 0 auto;
  padding: 12px 16px;
  background: $color-bg-white;
  border-radius: $radius-lg;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.chat-textarea {
  font-size: 15px;

  /* 隐藏 textarea 内边框，由外层卡片承接视觉 */
  :deep(.el-textarea__inner) {
    padding: 4px 2px;
    box-shadow: none;
    background: transparent;
  }
}

.input-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
}

.action-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
  min-width: 0;
}

.feature-btn {
  padding: 6px 8px;
  font-size: 13px;
  color: $color-text-secondary;
  border-radius: $radius-md;

  /* 图标与文字间距 */
  .el-icon {
    margin-right: 4px;
  }

  &:hover {
    color: $color-text-main;
    background: #f5f6f7;
  }
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: $color-primary;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover:not(:disabled) {
    background: $color-primary-hover;
  }

  /* 禁用态：浅黄不可点 */
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
</style>
