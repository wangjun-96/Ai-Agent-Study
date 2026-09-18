<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import type { ChatMessage } from '@/types/interview'
import MessageBubble from './MessageBubble.vue'

/** 消息列表容器：滚动区域，新消息到达后自动滚到底部，支持上拉分页 */
interface Props {
  /** 消息列表 */
  list: ChatMessage[]
  /** 是否正在加载更多（用于上拉分页） */
  loadingMore?: boolean
  /** 是否还有更多数据 */
  hasMore?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loadingMore: false,
  hasMore: true,
})

const emit = defineEmits<{
  (e: 'loadMore'): void
}>()

/** 滚动容器引用 */
const scrollRef = ref<HTMLElement>()

/** 上拉加载的阈值（px） */
const LOAD_THRESHOLD = 100

/** 防重入锁：防止在加载中时再次触发 */
let loadLock = false

/** 判断是否已滚动到顶部区域 */
function isNearTop(): boolean {
  if (!scrollRef.value) return false
  return scrollRef.value.scrollTop <= LOAD_THRESHOLD
}

/** 处理滚动事件 */
function handleScroll() {
  // 上拉分页：滚动到顶部附近且有更多数据且未在加载中
  if (isNearTop() && props.hasMore && !props.loadingMore && !loadLock) {
    loadLock = true
    emit('loadMore')
    // 解锁延迟，等新消息插入完成
    setTimeout(() => {
      loadLock = false
    }, 500)
  }
}

// 监听消息数量变化，自动滚动到底部
watch(
  () => props.list.length,
  async () => {
    await nextTick()
    if (scrollRef.value) {
      // 如果用户已经在底部附近，自动滚动到底部
      const { scrollHeight, scrollTop, clientHeight } = scrollRef.value
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
      if (isAtBottom) {
        scrollRef.value.scrollTo({ top: scrollRef.value.scrollHeight, behavior: 'smooth' })
      }
    }
  },
)

// 组件挂载时滚动到底部
onMounted(() => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTo({ top: scrollRef.value.scrollHeight, behavior: 'instant' })
    }
  })
})
</script>

<template>
  <div ref="scrollRef" class="chat-message-list" @scroll="handleScroll">
    <!-- 加载更多指示器 -->
    <div v-if="loadingMore" class="load-more-indicator">
      <el-icon class="is-loading" :size="20"><Loading /></el-icon>
      <span>加载更多...</span>
    </div>

    <div class="message-flow">
      <MessageBubble v-for="msg in list" :key="msg.id" :message="msg" />
    </div>

    <!-- 空状态提示 -->
    <div v-if="list.length === 0 && !loadingMore" class="empty-state">
      <p>暂无消息记录</p>
      <p class="hint">发送消息开始对话</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.chat-message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: $color-bg-page;
  position: relative;
}

/* 消息流：居中限宽排布 */
.message-flow {
  display: flex;
  flex-direction: column;
  gap: 28px;
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 24px 24px;
}

/* 加载更多指示器 */
.load-more-indicator {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: $color-bg-page;
  color: $color-text-secondary;
  font-size: 13px;
}

/* 空状态 */
.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: $color-text-secondary;
  font-size: 15px;

  .hint {
    margin-top: 8px;
    font-size: 13px;
  }
}
</style>
