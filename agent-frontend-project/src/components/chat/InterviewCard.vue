<script setup lang="ts">
import { ref } from 'vue'
import { ElDialog } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useInterviewApi } from '@/api/interview'
import type { InterviewResponse } from '@/types/interview'

/** 面试卡片组件：当消息 status=1 时显示，点击可查看面试详情 */
interface Props {
  /** 面试 ID */
  interviewId: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'view'): void
}>()

/** 弹窗是否可见 */
const dialogVisible = ref(false)

/** 面试详情数据 */
const interviewDetail = ref<InterviewResponse | null>(null)

/** 加载状态 */
const loading = ref(false)

/** 从 QA 对象中提取问题文本（兼容多种字段名） */
function getQuestionText(item: Record<string, string>): string {
  return item.question || item.q || item.q1 || item.Q || item.Q1 || '未提供问题'
}

/** 从 QA 对象中提取答案文本（兼容多种字段名） */
function getAnswerText(item: Record<string, string>): string {
  return item.answer || item.a || item.a1 || item.A || item.A1 || '未提供答案'
}

/** 打开弹窗并获取面试详情 */
async function openInterviewDialog() {
  dialogVisible.value = true
  emit('view')

  if (!interviewDetail.value) {
    loading.value = true
    try {
      const res = await useInterviewApi(props.interviewId)
      if (res.code === 0 && res.data) {
        interviewDetail.value = res.data
      }
    } catch (error) {
      console.error('获取面试详情失败:', error)
    } finally {
      loading.value = false
    }
  }
}
</script>

<template>
  <div class="interview-card">
    <el-button type="primary" plain @click="openInterviewDialog">
      查看面试详情
    </el-button>

    <el-dialog
      v-model="dialogVisible"
      title="面试详情"
      width="600px"
      :close-on-click-modal="true"
    >
      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-else-if="interviewDetail" class="interview-content">
        <div
          v-for="(item, index) in interviewDetail.qa_object"
          :key="index"
          class="qa-item"
        >
          <div class="question">
            <span class="label">Q{{ index + 1 }}:</span>
            <span class="text">{{ getQuestionText(item) }}</span>
          </div>
          <div class="answer">
            <span class="label">A{{ index + 1 }}:</span>
            <span class="text">{{ getAnswerText(item) }}</span>
          </div>
        </div>

        <div v-if="!interviewDetail.qa_object || interviewDetail.qa_object.length === 0" class="empty-data">
          暂无面试数据
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.interview-card {
  margin-top: 12px;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: $color-text-secondary;
}

.interview-content {
  max-height: 60vh;
  overflow-y: auto;
}

.qa-item {
  padding: 16px;
  margin-bottom: 12px;
  background: $color-bg-gray;
  border-radius: $radius-md;

  &:last-child {
    margin-bottom: 0;
  }
}

.question,
.answer {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.label {
  font-weight: 600;
  color: $color-primary;
  flex-shrink: 0;
}

.text {
  flex: 1;
  font-size: 14px;
  line-height: 1.6;
  color: $color-text-main;
  white-space: pre-wrap;
}

.empty-data {
  text-align: center;
  padding: 40px;
  color: $color-text-secondary;
  font-size: 14px;
}
</style>
