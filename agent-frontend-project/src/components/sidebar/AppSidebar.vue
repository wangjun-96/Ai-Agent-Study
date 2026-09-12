<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import type { ChatSession } from '@/types/interview'
import ChatHistoryList from './ChatHistoryList.vue'

/**
 * 通用列表侧边栏：新建按钮 + 列表标题 + 列表。
 * 聊天会话与笔记列表共用，通过文案配置区分业务
 */
interface Props {
  /** 列表数据 */
  list: ChatSession[]
  /** 当前激活项 ID */
  activeId: string
  /** 新建按钮文案 */
  createLabel?: string
  /** 列表标题文案 */
  sectionLabel?: string
}

withDefaults(defineProps<Props>(), {
  createLabel: '新建会话',
  sectionLabel: '历史会话',
})

const emit = defineEmits<{
  (e: 'create'): void
  (e: 'select', id: string): void
  (e: 'rename', id: string, title: string): void
  (e: 'delete', id: string): void
}>()
</script>

<template>
  <aside class="app-sidebar">
    <div class="sidebar-body">
      <!-- 新建按钮 -->
      <el-button class="create-btn" :icon="Plus" size="large" @click="emit('create')">
        {{ createLabel }}
      </el-button>

      <p class="section-title">{{ sectionLabel }}</p>

      <!-- 列表 -->
      <ChatHistoryList
        :list="list"
        :active-id="activeId"
        @select="emit('select', $event)"
        @rename="(id, title) => emit('rename', id, title)"
        @delete="emit('delete', $event)"
      />
    </div>
  </aside>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.app-sidebar {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: $sidebar-width;
  background: $color-bg-white;
  border-right: 1px solid $color-border;
}

.sidebar-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 14px 14px 14px;
}

.create-btn {
  width: 100%;
  height: 42px;
  font-size: 14px;
  color: #ffffff;
  background: $color-primary;
  border-color: $color-primary;
  border-radius: $radius-md;

  &:hover,
  &:focus {
    color: #ffffff;
    background: $color-primary-hover;
    border-color: $color-primary-hover;
  }
}

.section-title {
  margin: 18px 4px 8px;
  font-size: 13px;
  color: $color-text-secondary;
}
</style>
