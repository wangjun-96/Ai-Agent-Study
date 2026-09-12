import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, ChatSession, MessageRole } from '@/types/interview'
import {
  GREETING_MESSAGE,
  MOCK_AI_REPLY,
  MOCK_SESSIONS,
} from '@/config/constant'

/** 自增消息 ID 种子，配合时间戳生成唯一 ID */
let idSeed = 0

/** 生成消息唯一标识 */
function genMessageId(): string {
  idSeed += 1
  return `msg-${Date.now()}-${idSeed}`
}

/** 构造一条聊天消息 */
function createMessage(role: MessageRole, content: string): ChatMessage {
  return { id: genMessageId(), role, content, timeText: '刚刚' }
}

/**
 * 聊天全局状态（Pinia）：
 * 历史会话列表、当前会话消息缓存、AI 回复状态。
 * 布局层侧边栏与面试间页面共享此状态
 */
export const useChatStore = defineStore('chat', () => {
  // ==================== 状态 ====================

  /** 历史会话列表 */
  const sessions = ref<ChatSession[]>([...MOCK_SESSIONS])

  /** 当前激活的会话 ID */
  const activeSessionId = ref('')

  /** 各会话的消息列表缓存，key 为会话 ID */
  const conversations = reactive<Record<string, ChatMessage[]>>({})

  /** AI 是否正在回复（回复期间禁止继续发送） */
  const isReplying = ref(false)

  // ==================== 计算属性 ====================

  /** 当前会话的消息列表 */
  const messages = computed<ChatMessage[]>(() => conversations[activeSessionId.value] ?? [])

  // ==================== 动作 ====================

  /** 初始化会话消息（浅拷贝避免污染模块级 mock 数据，已存在则不覆盖） */
  function initSession(sessionId: string, initialMessages: ChatMessage[]): void {
    if (!conversations[sessionId]) {
      conversations[sessionId] = [...initialMessages]
    }
  }

  /** 切换会话：激活会话并懒初始化招呼语 */
  function loadSession(sessionId: string): void {
    activeSessionId.value = sessionId
    initSession(sessionId, [createMessage('ai', GREETING_MESSAGE)])
  }

  /** 新建会话：列表顶部插入并激活 */
  function createSession(): void {
    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      title: `新会话 ${sessions.value.length + 1}`,
      icon: 'ChatLineRound',
      color: '#fbc531',
    }
    sessions.value.unshift(newSession)
    loadSession(newSession.id)
  }

  /** 重命名会话 */
  function renameSession(id: string, title: string): void {
    const target = sessions.value.find((item) => item.id === id)
    if (target) {
      target.title = title
    }
  }

  /** 删除会话（移除列表项并清理消息缓存），若删除当前会话则自动切换到第一个 */
  function deleteSession(id: string): void {
    delete conversations[id]
    sessions.value = sessions.value.filter((item) => item.id !== id)

    if (id === activeSessionId.value) {
      const next = sessions.value[0]
      if (next) {
        loadSession(next.id)
      } else {
        activeSessionId.value = ''
      }
    }
  }

  /** 发送用户消息，并模拟 AI 异步回复（后续替换为真实接口调用） */
  function sendMessage(content: string): void {
    const text = content.trim()
    if (!text || isReplying.value || !activeSessionId.value) return

    conversations[activeSessionId.value].push(createMessage('user', text))
    isReplying.value = true

    window.setTimeout(() => {
      conversations[activeSessionId.value]?.push(createMessage('ai', MOCK_AI_REPLY))
      isReplying.value = false
    }, 600)
  }

  return {
    sessions,
    activeSessionId,
    isReplying,
    messages,
    initSession,
    loadSession,
    createSession,
    renameSession,
    deleteSession,
    sendMessage,
  }
})
