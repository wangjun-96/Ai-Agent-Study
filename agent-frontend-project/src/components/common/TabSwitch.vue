<script setup lang="ts">
import type { TabItem } from '@/types/interview'

/** Tab 切换组件：支持 v-model 双向绑定当前选中项 */
interface Props {
  /** Tab 配置列表 */
  tabs: TabItem[]
  /** 当前选中的 Tab key */
  modelValue: string
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', key: string): void
}>()
</script>

<template>
  <div class="tab-switch">
    <button
      v-for="tab in tabs"
      :key="tab.path"
      type="button"
      class="tab-item"
      :class="{ 'is-active': tab.path === modelValue }"
      @click="emit('update:modelValue', tab.path)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.tab-switch {
  display: flex;
  gap: 12px;
}

.tab-item {
  min-width: 72px;
  padding: 8px 20px;
  border: 1px solid transparent;
  border-radius: $radius-md;
  background: $color-bg-gray;
  color: $color-text-main;
  font-size: 14px;
  cursor: pointer;
  transition:
    background-color 0.2s,
    border-color 0.2s;

  /* 选中态：品牌浅黄底 + 黄色描边 */
  &.is-active {
    background: $color-primary-light;
    border-color: $color-primary-border;
    font-weight: 500;
  }

  &:hover:not(.is-active) {
    background: #e8e9ec;
  }
}
</style>
