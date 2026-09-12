<script setup lang="ts">
import ChatRoom from '@/components/chat/ChatRoom.vue'
import { INTERVIEW_INPUT_ACTIONS } from '@/config/constant'

/** 面试间页面：复用聊天室组件，配置面试场景功能按钮 */
</script>

<template>
  <ChatRoom placeholder="输入你的回答..." :actions="INTERVIEW_INPUT_ACTIONS" />
</template>
