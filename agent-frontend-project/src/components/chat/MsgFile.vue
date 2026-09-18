<script setup lang="ts">
import { computed, ref } from 'vue'
import { Document, Picture, Microphone } from '@element-plus/icons-vue'
import type { MessageSegment } from '@/types/interview'

/** 单条消息附件组件：支持文件、图片、音频 */
interface Props {
  /** 附件数据 */
  segment: MessageSegment
  /** 是否为用户发送的附件（默认false） */
  isUser?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isUser: false,
})

/** 附件图标 */
const iconComponent = computed(() => {
  switch (props.segment.type) {
    case 'image':
      return Picture
    case 'audio':
      return Microphone
    default:
      return Document
  }
})

/** 图片加载失败状态 */
const imageError = ref(false)

/** 音频加载失败状态 */
const audioError = ref(false)

/** 处理图片加载失败 */
function handleImageError() {
  imageError.value = true
}

/** 处理音频加载失败 */
function handleAudioError() {
  audioError.value = true
}

/** 下载附件 */
function downloadFile() {
  const link = document.createElement('a')
  link.href = props.segment.url
  link.download = props.segment.name
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
</script>

<template>
  <div class="msg-file" :class="{ 'is-user': isUser }">
    <!-- 图片附件 -->
    <template v-if="segment.type === 'image'">
      <div v-if="imageError" class="image-placeholder">
        <el-icon :size="24"><Picture /></el-icon>
        <span>图片加载失败</span>
      </div>
      <el-image
        v-else
        class="image-attachment"
        :src="segment.url"
        :alt="segment.name"
        fit="cover"
        @error="handleImageError"
      />
    </template>

    <!-- 音频附件 -->
    <template v-else-if="segment.type === 'audio'">
      <div v-if="audioError" class="audio-error">
        <el-icon :size="18"><Microphone /></el-icon>
        <span>音频加载失败</span>
      </div>
      <audio v-else controls class="audio-attachment" @error="handleAudioError">
        <source :src="segment.url" />
        您的浏览器不支持音频播放
      </audio>
    </template>

    <!-- 文件附件 -->
    <template v-else>
      <div class="file-attachment" @click="downloadFile">
        <el-icon :size="20" class="file-icon">
          <component :is="iconComponent" />
        </el-icon>
        <div class="file-info">
          <span class="file-name" :title="segment.name">{{ segment.name }}</span>
          <span class="file-action">点击下载</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.msg-file {
  margin-top: 8px;

  &.is-user {
    /* 用户附件靠右对齐 */
    display: flex;
    justify-content: flex-end;
  }
}

/* 图片附件 */
.image-attachment {
  max-width: 280px;
  max-height: 200px;
  border-radius: $radius-md;
  cursor: pointer;
  overflow: hidden;
}

.image-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  background: $color-bg-gray;
  border-radius: $radius-md;
  color: $color-text-secondary;
  font-size: 13px;
}

/* 音频附件 */
.audio-attachment {
  width: 280px;
  height: 40px;
  border-radius: $radius-md;
}

.audio-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef2f2;
  border-radius: $radius-md;
  color: #ef4444;
  font-size: 13px;
}

/* 文件附件 */
.file-attachment {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: $color-bg-gray;
  border-radius: $radius-md;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background: #e8eaed;
  }
}

.file-icon {
  color: $color-primary;
  flex-shrink: 0;
}

.file-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  color: $color-text-main;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.file-action {
  font-size: 12px;
  color: $color-text-secondary;
  margin-top: 2px;
}
</style>
