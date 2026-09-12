<script setup lang="ts">
import { ref } from 'vue'
import type { Component } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatLineRound,
  Cloudy,
  Coin,
  Connection,
  Cpu,
  Delete,
  EditPen,
  Iphone,
  Lock,
  Monitor,
  Notebook,
  TrendCharts,
} from '@element-plus/icons-vue'
import type { ChatSession } from '@/types/interview'

/** 会话图标名 -> 图标组件映射 */
const SESSION_ICONS: Record<string, Component> = {
  ChatLineRound,
  Cloudy,
  Coin,
  Connection,
  Cpu,
  Iphone,
  Lock,
  Monitor,
  Notebook,
  TrendCharts,
}

/** 历史会话列表：选中 / 重命名 / 删除 */
interface Props {
  /** 会话列表 */
  list: ChatSession[]
  /** 当前激活的会话 ID */
  activeId: string
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'rename', id: string, title: string): void
  (e: 'delete', id: string): void
}>()

/** 当前编辑中的会话 ID（空串表示未处于编辑态） */
const editingId = ref('')
/** 编辑中的会话标题草稿 */
const editingTitle = ref('')

/** 进入行内重命名编辑态 */
function startEdit(session: ChatSession): void {
  editingId.value = session.id
  editingTitle.value = session.title
}

/** 提交重命名：标题非空才生效，Esc 已在取消分支处理 */
function confirmEdit(): void {
  const title = editingTitle.value.trim()
  if (editingId.value && title) {
    emit('rename', editingId.value, title)
  }
  editingId.value = ''
}

/** 取消重命名编辑 */
function cancelEdit(): void {
  editingId.value = ''
}

/** 点击会话项：若正处于重命名编辑态，则先退出编辑再忽略本次选择 */
function handleItemClick(session: ChatSession): void {
  if (editingId.value) {
    cancelEdit()
    return
  }
  emit('select', session.id)
}

/** 删除会话：二次确认后通知父级 */
function handleDelete(session: ChatSession): void {
  ElMessageBox.confirm(`确定删除会话「${session.title}」吗？`, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      emit('delete', session.id)
      ElMessage.success('会话已删除')
    })
    .catch(() => {
      // 用户取消删除，无需处理
    })
}
</script>

<template>
  <ul class="chat-history-list">
    <li
      v-for="session in list"
      :key="session.id"
      class="history-item"
      :class="{ 'is-active': session.id === activeId }"
      @click="handleItemClick(session)"
    >
      <!-- 会话图标 -->
      <el-icon :size="18" :color="session.color">
        <component :is="SESSION_ICONS[session.icon] ?? Monitor" />
      </el-icon>

      <!-- 标题 / 重命名输入框 -->
      <template v-if="session.id === editingId">
        <el-input
          v-model="editingTitle"
          class="rename-input"
          size="small"
          maxlength="30"
          @click.stop
          @keydown.enter.prevent="confirmEdit"
          @keydown.esc.prevent="cancelEdit"
          @blur="confirmEdit"
        />
      </template>
      <span v-else class="item-title" :title="session.title">{{ session.title }}</span>

      <!-- 悬停操作：重命名 / 删除 -->
      <span v-if="session.id !== editingId" class="item-actions">
        <el-icon
          class="action-icon"
          :size="15"
          title="重命名"
          @click.stop="startEdit(session)"
        >
          <EditPen />
        </el-icon>
        <el-icon
          class="action-icon"
          :size="15"
          title="删除"
          @click.stop="handleDelete(session)"
        >
          <Delete />
        </el-icon>
      </span>
    </li>
  </ul>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.chat-history-list {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px;
  border-radius: $radius-md;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background: #f6f7f8;

    .item-actions {
      opacity: 1;
    }
  }

  &.is-active .item-title {
    font-weight: 600;
  }
}

.item-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: $color-text-main;
}

.rename-input {
  flex: 1;
  min-width: 0;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;

  .action-icon {
    color: $color-text-secondary;

    &:hover {
      color: $color-text-main;
    }
  }
}
</style>
