import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatSession } from '@/types/interview'
import { DEFAULT_NOTE_CONTENT, MOCK_NOTES } from '@/config/constant'

/**
 * 笔记全局状态（Pinia）：
 * 笔记列表 + 各笔记富文本内容缓存。
 * 布局层笔记侧边栏与笔记本页面共享此状态
 */
export const useNoteStore = defineStore('note', () => {
  // ==================== 状态 ====================

  /** 笔记列表 */
  const notes = ref<ChatSession[]>([...MOCK_NOTES])

  /** 当前激活的笔记 ID */
  const activeNoteId = ref('')

  /** 各笔记的富文本内容缓存，key 为笔记 ID */
  const contents = reactive<Record<string, string>>({})

  // ==================== 计算属性 ====================

  /** 当前激活的笔记 */
  const activeNote = computed<ChatSession | undefined>(() =>
    notes.value.find((item) => item.id === activeNoteId.value),
  )

  /** 当前笔记的富文本内容 */
  const activeContent = computed<string>(() => contents[activeNoteId.value] ?? '')

  // ==================== 动作 ====================

  /** 切换笔记：激活并懒初始化默认内容 */
  function selectNote(noteId: string): void {
    activeNoteId.value = noteId
    if (!contents[noteId]) {
      contents[noteId] = DEFAULT_NOTE_CONTENT
    }
  }

  /** 新建笔记：列表顶部插入并激活 */
  function createNote(): void {
    const newNote: ChatSession = {
      id: `note-${Date.now()}`,
      title: `新笔记 ${notes.value.length + 1}`,
      icon: 'Notebook',
      color: '#fbc531',
    }
    notes.value.unshift(newNote)
    selectNote(newNote.id)
  }

  /** 重命名笔记 */
  function renameNote(id: string, title: string): void {
    const target = notes.value.find((item) => item.id === id)
    if (target) {
      target.title = title
    }
  }

  /** 重命名当前激活笔记（编辑器标题栏实时输入时调用） */
  function renameActiveNote(title: string): void {
    if (activeNoteId.value) {
      renameNote(activeNoteId.value, title)
    }
  }

  /** 更新当前笔记内容（编辑器输入时实时调用） */
  function updateContent(html: string): void {
    if (activeNoteId.value) {
      contents[activeNoteId.value] = html
    }
  }

  /** 删除笔记（移除列表项并清理内容缓存），若删除当前笔记则自动切换到第一个 */
  function deleteNote(id: string): void {
    delete contents[id]
    notes.value = notes.value.filter((item) => item.id !== id)

    if (id === activeNoteId.value) {
      const next = notes.value[0]
      if (next) {
        selectNote(next.id)
      } else {
        activeNoteId.value = ''
      }
    }
  }

  return {
    notes,
    activeNoteId,
    activeNote,
    activeContent,
    selectNote,
    createNote,
    renameNote,
    renameActiveNote,
    updateContent,
    deleteNote,
  }
})
