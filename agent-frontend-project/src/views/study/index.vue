<script setup lang="ts">
import ChatRoom from '@/components/chat/ChatRoom.vue'
import { STUDY_INPUT_ACTIONS } from '@/config/constant'

/** 学习室页面：复用聊天室组件，配置学习场景功能按钮 */
</script>

<template>
  <ChatRoom placeholder="输入你的问题..." :actions="STUDY_INPUT_ACTIONS" />
</template>
