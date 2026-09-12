<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import type { IDomEditor, IEditorConfig, IToolbarConfig } from '@wangeditor/editor'
import '@wangeditor/editor/dist/css/style.css'
import { useNoteStore } from '@/stores/note'

/**
 * 笔记编辑卡片：wangEditor 工具栏 + 标题 + 富文本编辑区。
 * 数据读写均走笔记 store，切换笔记自动切换内容
 */
const noteStore = useNoteStore()

/** 编辑器实例（非响应式，避免深度代理开销） */
const editorRef = shallowRef<IDomEditor>()

/** 工具栏是否初始化完成，用于隐藏加载占位 */
const isEditorReady = ref(false)

/** 工具栏配置：与设计稿一致的常用格式项 */
const toolbarConfig: Partial<IToolbarConfig> = {
  toolbarKeys: [
    'bold',
    'italic',
    'underline',
    'bulletedList',
    'numberedList',
    'justifyLeft',
    'justifyCenter',
    'justifyRight',
    'justifyJustify',
    '|',
    'insertLink',
    'insertImage',
  ],
}

/** 编辑器配置 */
const editorConfig: Partial<IEditorConfig> = {
  placeholder: '开始记录你的笔记...',
}

/** 当前笔记标题（可写计算属性，实时同步到 store） */
const activeTitle = computed<string>({
  get: () => noteStore.activeNote?.title ?? '',
  set: (value) => noteStore.renameActiveNote(value),
})

/** 当前笔记富文本内容（可写计算属性，实时同步到 store） */
const activeContent = computed<string>({
  get: () => noteStore.activeContent,
  set: (value) => noteStore.updateContent(value),
})

/** 编辑器创建完成回调 */
function handleCreated(editor: IDomEditor): void {
  editorRef.value = editor
  isEditorReady.value = true
}

// 组件销毁时销毁编辑器实例，防止内存泄漏
onBeforeUnmount(() => {
  editorRef.value?.destroy()
})
</script>

<template>
  <div class="note-editor-card">
    <!-- 格式工具栏 -->
    <Toolbar
      class="note-toolbar"
      :editor="editorRef"
      :default-config="toolbarConfig"
      mode="default"
    />

    <!-- 笔记标题 -->
    <el-input
      v-model="activeTitle"
      class="note-title-input"
      placeholder="请输入笔记标题"
      maxlength="50"
    />

    <!-- 富文本编辑区 -->
    <div class="note-editor-wrap">
      <Editor
        v-model="activeContent"
        class="note-editor"
        :default-config="editorConfig"
        mode="default"
        @on-created="handleCreated"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.note-editor-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 900px;
  height: 620px;
  background: $color-bg-white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  overflow: hidden;

  /* 融合 wangEditor 默认边框，由卡片统一承接视觉 */
  :deep(.w-e-toolbar) {
    background: $color-bg-white;
    border: none !important;
    border-bottom: 1px solid $color-border !important;
    padding: 10px 16px;
    flex-wrap: nowrap;
  }

  :deep(.w-e-text-container) {
    background: $color-bg-white;

    .w-e-scroll {
      &::-webkit-scrollbar {
        width: 6px;
      }

      &::-webkit-scrollbar-thumb {
        border-radius: 3px;
        background: rgba(0, 0, 0, 0.15);
      }
    }
  }
}

.note-toolbar {
  flex-shrink: 0;
  cursor: default;
}

.note-title-input {
  flex-shrink: 0;

  /* 标题栏：大字号无边框输入 */
  :deep(.el-input__wrapper) {
    padding: 16px 20px;
    box-shadow: none;
    border-bottom: 1px solid $color-border;
    border-radius: 0;
  }

  :deep(.el-input__inner) {
    font-size: 22px;
    font-weight: 600;
    color: $color-text-main;
  }
}

.note-editor-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.note-editor {
  height: 100%;
  overflow-y: hidden;
}
</style>
