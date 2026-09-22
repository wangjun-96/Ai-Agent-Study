import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import type {
  ChatMessage,
  ChatSession,
  MessageRole,
  MessageResponse,
  SessionResponse,
  SessionModel,
} from '@/types/interview'
import {
  getSessions,
  createSession as apiCreateSession,
  updateSession as apiUpdateSession,
  deleteSession as apiDeleteSession,
} from '@/api/session'
import { getMessages } from '@/api/message'
import { GREETING_MESSAGE } from '@/config/constant'

/** 自增消息 ID 种子，配合时间戳生成唯一 ID */
let idSeed = 0

/** 生成消息唯一标识 */
function genMessageId(): string {
  idSeed += 1
  return `msg-${Date.now()}-${idSeed}`
}

/** 构造一条聊天消息 */
function createMessage(
  role: MessageRole,
  content: string,
  extras?: Partial<ChatMessage>,
): ChatMessage {
  return {
    id: genMessageId(),
    role,
    content,
    timeText: '刚刚',
    ...extras,
  }
}

/** 会话模式到图标映射 */
const SESSION_MODEL_ICONS: Record<SessionModel, { icon: string; color: string }> = {
  0: { icon: 'Monitor', color: '#3b82f6' }, // 学习
  1: { icon: 'ChatLineRound', color: '#fbc531' }, // 面试
  2: { icon: 'Notebook', color: '#10b981' }, // 笔记
}

/** 格式化后端消息为前端格式 */
function formatMessageResponse(msg: MessageResponse): ChatMessage {
  return {
    id: String(msg.id),
    role: 'ai', // 后端消息统一为 AI 视角，实际内容根据 request_text/response_text 判断
    content: msg.response_text || msg.request_text || '',
    timeText: formatTime(msg.created_at),
    created_at: msg.created_at,
    request_segments: msg.request_segments || [],
    response_segments: msg.response_segments || [],
    status: msg.status,
    interview_id: msg.interview_id,
  }
}

/** 格式化时间为相对时间 */
function formatTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

/**
 * 聊天全局状态（Pinia）：
 * 历史会话列表、当前会话消息缓存、AI 回复状态。
 * 布局层侧边栏与面试间页面共享此状态
 */
export const useChatStore = defineStore('chat', () => {
  // ==================== 状态 ====================

  /** 历史会话列表 */
  const sessions = ref<ChatSession[]>([])

  /** 当前激活的会话 ID */
  const activeSessionId = ref<number | string>('')

  /** 各会话的消息列表缓存，key 为会话 ID（转为字符串） */
  const conversations = reactive<Record<string, ChatMessage[]>>({})

  /** 各会话的消息分页状态，key 为会话 ID */
  const paginationInfo = reactive<Record<string, { page: number; total: number; hasMore: boolean }>>({})

  /** AI 是否正在回复（回复期间禁止继续发送） */
  const isReplying = ref(false)

  /** 会话列表加载状态 */
  const sessionsLoading = ref(false)

  /** 消息加载更多状态 */
  const loadingMore = ref(false)

  // ==================== 计算属性 ====================

  /** 当前会话的消息列表 */
  const messages = computed<ChatMessage[]>(() => {
    const key = String(activeSessionId.value)
    return conversations[key] ?? []
  })

  /** 当前会话是否还有更多消息 */
  const hasMoreMessages = computed(() => {
    const key = String(activeSessionId.value)
    return paginationInfo[key]?.hasMore ?? true
  })

  // ==================== 动作 ====================

  /** 从后端会话响应转换为本应用格式 */
  function formatSessionResponse(session: SessionResponse): ChatSession {
    const iconConfig = SESSION_MODEL_ICONS[session.session_model as SessionModel] || SESSION_MODEL_ICONS[0]
    return {
      id: session.id,
      title: session.title,
      session_model: session.session_model,
      icon: iconConfig.icon,
      color: iconConfig.color,
      create_time: session.create_time,
      update_time: session.update_time,
    }
  }

  /** 加载会话列表 */
  async function fetchSessions(params?: { session_model?: number; page?: number; page_size?: number }) {
    sessionsLoading.value = true
    try {
      const res = await getSessions(params)
      if (res.code === 0 && res.data) {
        sessions.value = (res.data.items || []).map(formatSessionResponse)
        // 不再自动选中第一个会话：默认不显示任何聊天内容，
        // 用户点击侧边栏的某个会话后才会在 ChatRoom 中显示对应消息与输入框
      }
    } catch (error) {
      console.error('获取会话列表失败:', error)
    } finally {
      sessionsLoading.value = false
    }
  }

  /** 创建新会话 */
  async function createSession(title: string, sessionModel: SessionModel = 0) {
    try {
      const res = await apiCreateSession({ title, session_model: sessionModel })
      if (res.code === 0 && res.data) {
        const newSession = formatSessionResponse(res.data)
        sessions.value.unshift(newSession)
        await loadSession(newSession.id)
        return newSession
      }
    } catch (error) {
      console.error('创建会话失败:', error)
    }
    return null
  }

  /** 编辑会话标题 */
  async function renameSession(id: number | string, title: string) {
    try {
      const res = await apiUpdateSession(Number(id), { title })
      if (res.code === 0 && res.data) {
        const target = sessions.value.find((item) => item.id === id)
        if (target) {
          target.title = res.data.title
        }
      }
    } catch (error) {
      console.error('编辑会话失败:', error)
    }
  }

  /** 删除会话 */
  async function deleteSession(id: number | string) {
    const session = sessions.value.find((item) => item.id === id)
    if (!session) return

    try {
      const sessionModel = (session.session_model as SessionModel) ?? 0
      await apiDeleteSession(Number(id), sessionModel)
      delete conversations[String(id)]
      delete paginationInfo[String(id)]
      sessions.value = sessions.value.filter((item) => item.id !== id)

      // 如果删除的是当前会话，切换到第一个
      if (id === activeSessionId.value) {
        if (sessions.value.length > 0) {
          await loadSession(sessions.value[0].id)
        } else {
          activeSessionId.value = ''
        }
      }
    } catch (error) {
      console.error('删除会话失败:', error)
    }
  }

  /** 加载会话消息（分页） */
  async function fetchMessages(sessionId: number | string, page = 1, pageSize = 20, append = false) {
    const key = String(sessionId)

    if (!append) {
      // 首次加载，显示招呼语
      if (!conversations[key]) {
        conversations[key] = []
      }
      // 如果消息为空，添加招呼语
      if (conversations[key].length === 0) {
        conversations[key].push(createMessage('ai', GREETING_MESSAGE))
      }
    }

    loadingMore.value = true
    try {
      const res = await getMessages(Number(sessionId), { page, page_size: pageSize })
      if (res.code === 0 && res.data) {
        const newMessages = (res.data.items || [])
          .map(formatMessageResponse)
          .sort((a, b) => {
            const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
            const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
            return timeA - timeB // 按创建时间升序排列
          })

        // 更新分页信息
        paginationInfo[key] = {
          page: res.data.page,
          total: res.data.total,
          hasMore: res.data.items.length >= pageSize,
        }

        if (append) {
          // 增量追加（去重）
          const existingIds = new Set(conversations[key].map((m) => m.id))
          const uniqueNewMessages = newMessages.filter((m) => !existingIds.has(m.id))
          conversations[key].unshift(...uniqueNewMessages.reverse())
        } else {
          // 替换消息列表（去掉招呼语，因为后端会返回真实消息）
          conversations[key] = newMessages
          // 如果后端没有返回消息，添加招呼语
          if (conversations[key].length === 0) {
            conversations[key].push(createMessage('ai', GREETING_MESSAGE))
          }
        }
      }
    } catch (error) {
      console.error('获取消息列表失败:', error)
    } finally {
      loadingMore.value = false
    }
  }

  /** 切换会话：激活会话并懒加载消息 */
  async function loadSession(sessionId: number | string) {
    activeSessionId.value = sessionId
    const key = String(sessionId)

    // 如果没有消息，加载消息
    if (!conversations[key] || conversations[key].length === 0) {
      await fetchMessages(sessionId, 1, 20, false)
    }
  }

  /** 加载更多消息（上拉分页） */
  async function loadMoreMessages() {
    if (loadingMore.value || !hasMoreMessages.value) return

    const key = String(activeSessionId.value)
    const currentPage = paginationInfo[key]?.page ?? 1
    await fetchMessages(activeSessionId.value, currentPage + 1, 20, true)
  }

  /** 添加用户消息（发送后由外部处理 AI 回复） */
  function addUserMessage(content: string, segments?: ChatMessage['request_segments']) {
    const key = String(activeSessionId.value)
    if (!conversations[key]) {
      conversations[key] = []
    }
    const msg = createMessage('user', content, { request_segments: segments })
    conversations[key].push(msg)
    return msg
  }

  /** 添加 AI 回复消息 */
  function addAIMessage(content: string, segments?: ChatMessage['response_segments']) {
    const key = String(activeSessionId.value)
    if (!conversations[key]) {
      conversations[key] = []
    }
    const msg = createMessage('ai', content, { response_segments: segments })
    conversations[key].push(msg)
    return msg
  }

  /** 发送消息占位（实际由调用方实现） */
  let sendMessageHandler: ((content: string) => Promise<void>) | null = null

  /** 注册发送消息处理器 */
  function registerSendHandler(handler: (content: string) => Promise<void>) {
    sendMessageHandler = handler
  }

  /** 发送消息（使用注册的处理器） */
  async function sendMessage(content: string) {
    const text = content.trim()
    if (!text || isReplying.value || !activeSessionId.value) return

    // 添加用户消息
    addUserMessage(text)

    // 如果有注册的处理器，调用它
    if (sendMessageHandler) {
      isReplying.value = true
      try {
        await sendMessageHandler(text)
      } finally {
        isReplying.value = false
      }
    }
  }

  return {
    // 状态
    sessions,
    activeSessionId,
    isReplying,
    sessionsLoading,
    loadingMore,
    // 计算属性
    messages,
    hasMoreMessages,
    // 方法
    fetchSessions,
    createSession,
    renameSession,
    deleteSession,
    fetchMessages,
    loadSession,
    loadMoreMessages,
    addUserMessage,
    addAIMessage,
    registerSendHandler,
    sendMessage,
  }
})
