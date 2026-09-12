<script setup lang="ts">
import NoteEditorCard from '@/components/note/NoteEditorCard.vue'

/** 笔记本页面：富文本编辑器主内容区，无聊天输入框 */
</script>

<template>
  <div class="note-view">
    <NoteEditorCard />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.note-view {
  display: flex;
  justify-content: center;
  flex: 1;
  min-height: 0;
  padding: 24px;
  overflow-y: auto;
  background: $color-bg-page;
}
</style>
