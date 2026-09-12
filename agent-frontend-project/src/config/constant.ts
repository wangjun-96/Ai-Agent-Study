import type { ChatMessage, ChatSession, InputAction, TabItem } from '@/types/interview'

/** 顶部导航 Tab 配置（path 与路由路径一一对应） */
export const TAB_LIST: TabItem[] = [
  { path: '/study', label: '学习室' },
  { path: '/interview', label: '面试间' },
  { path: '/note', label: '笔记本' },
]

/** 默认重定向的 Tab 路径 */
export const DEFAULT_TAB_PATH = '/interview'

/** 学习室输入区功能按钮配置 */
export const STUDY_INPUT_ACTIONS: InputAction[] = [
  { key: 'upload', label: '上传文件', icon: 'Upload' },
  { key: 'lecture', label: '知识精讲', icon: 'Reading' },
  { key: 'quiz', label: '刷题模式', icon: 'Edit' },
]

/** 面试间输入区功能按钮配置 */
export const INTERVIEW_INPUT_ACTIONS: InputAction[] = [
  { key: 'upload', label: '上传文件', icon: 'Upload' },
  { key: 'resume', label: '简历优化', icon: 'Document' },
  { key: 'mock', label: '模拟面试', icon: 'ChatDotRound' },
  { key: 'review', label: '面试复盘', icon: 'DataAnalysis' },
  { key: 'lecture', label: '知识精讲', icon: 'Reading' },
  { key: 'voice', label: '语音输入', icon: 'Microphone' },
]

/** 新会话进入时的 AI 招呼语 */
export const GREETING_MESSAGE =
  '你好！我是学面通AI面试官，很高兴为你提供面试模拟服务。请告诉我你想练习哪个职位的面试？比如前端工程师、后端工程师或者产品经理等。'

/** 发送消息后模拟的 AI 回复文案（后续替换为真实接口） */
export const MOCK_AI_REPLY =
  '收到！我们继续下一题：请介绍一下浏览器的事件循环（Event Loop）机制，以及宏任务与微任务的区别？'

/** 历史会话 mock 数据 */
export const MOCK_SESSIONS: ChatSession[] = [
  { id: 'session-1', title: '前端技术面试准备', icon: 'Monitor', color: '#3b82f6' },
  { id: 'session-2', title: '数据库优化策略', icon: 'Coin', color: '#10b981' },
  { id: 'session-3', title: '系统架构设计', icon: 'Connection', color: '#8b5cf6' },
  { id: 'session-4', title: '云计算基础', icon: 'Cloudy', color: '#f59e0b' },
  { id: 'session-5', title: '移动端开发要点', icon: 'Iphone', color: '#ef4444' },
  { id: 'session-6', title: '网络安全防护', icon: 'Lock', color: '#6366f1' },
  { id: 'session-7', title: '数据分析方法', icon: 'TrendCharts', color: '#14b8a6' },
  { id: 'session-8', title: '机器学习入门', icon: 'Cpu', color: '#64748b' },
]

/** 笔记列表 mock 数据 */
export const MOCK_NOTES: ChatSession[] = [
  { id: 'note-1', title: '前端技术面试准备', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-2', title: '数据库优化策略', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-3', title: '系统架构设计', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-4', title: '云计算基础', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-5', title: '移动端开发要点', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-6', title: '网络安全防护', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-7', title: '数据分析方法', icon: 'Notebook', color: '#fbc531' },
  { id: 'note-8', title: '机器学习入门', icon: 'Notebook', color: '#fbc531' },
]

/** 新笔记的默认内容（空段落） */
export const DEFAULT_NOTE_CONTENT = '<p><br></p>'

/** 笔记内容 mock 数据，key 为笔记 ID */
export const MOCK_NOTE_CONTENTS: Record<string, string> = {
  'note-1': `<h2>JavaScript 闭包</h2><h3>定义</h3><p>闭包是指一个函数能够访问并"记住"其外部作用域中的变量，即使在其外部函数已经返回之后。</p><h3>应用场景</h3><ul><li>数据封装</li><li>模块模式</li><li>创建私有变量</li></ul><h2>React 虚拟DOM</h2><h3>工作原理</h3><p>虚拟DOM是React用来提升性能的关键技术。它是一个轻量级的JavaScript对象树，是对真实DOM的抽象表示。</p><h3>性能提升机制</h3><ol><li>当组件状态发生变化时，React会创建一个新的虚拟DOM树</li><li>与之前的虚拟DOM树进行比较(diff算法)</li><li>找出最小的变化集</li><li>只更新真实DOM中需要改变的部分，从而减少昂贵的DOM操作</li></ol><h2>React Hooks</h2><h3>工作原理</h3><p>useState和useEffect是React Hooks中最常用的两个API，后续继续补充。</p>`,
}

/** 默认会话的初始对话 mock 数据 */
export const MOCK_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'ai',
    content: GREETING_MESSAGE,
    timeText: '刚刚',
  },
  {
    id: 'msg-2',
    role: 'user',
    content: '我想练习前端工程师的面试，主要关注JavaScript和React相关的知识点。',
    timeText: '刚刚',
  },
  {
    id: 'msg-3',
    role: 'ai',
    content: '很好！我们来开始第一个问题：\n请解释一下JavaScript中的闭包是什么？它有什么应用场景？',
    timeText: '刚刚',
  },
  {
    id: 'msg-4',
    role: 'user',
    content:
      '闭包是指一个函数能够访问并"记住"其外部作用域中的变量，即使在其外部函数已经返回之后。主要应用场景包括数据封装、模块模式、以及创建私有变量等。',
    timeText: '刚刚',
  },
  {
    id: 'msg-5',
    role: 'ai',
    content: '回答得很好！接下来请解释一下React中的虚拟DOM是如何工作的，以及它如何提高性能？',
    timeText: '刚刚',
  },
  {
    id: 'msg-6',
    role: 'user',
    content:
      '虚拟DOM是React用来提升性能的关键技术。它是一个轻量级的JavaScript对象树，是对真实DOM的抽象表示。当组件状态发生变化时，React会创建一个新的虚拟DOM树，然后与之前的虚拟DOM树进行比较(diff算法)，找出最小的变化集，最后只更新真实DOM中需要改变的部分，从而减少昂贵的DOM操作。',
    timeText: '刚刚',
  },
  {
    id: 'msg-7',
    role: 'ai',
    content:
      '非常棒的解释！现在让我们深入一点：你能谈谈React Hooks的工作原理吗？特别是useState和useEffect?',
    timeText: '刚刚',
  },
]
