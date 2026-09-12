<script setup lang="ts">
import type { MessageRole } from '@/types/interview'
import { Service, User } from '@element-plus/icons-vue'

/** 消息头像：AI 为蓝色圆角方块，用户为深灰圆形 */
interface Props {
  /** 消息角色 */
  role: MessageRole
}

withDefaults(defineProps<Props>(), {
  role: 'ai',
})
</script>

<template>
  <div class="message-avatar" :class="role">
    <el-icon :size="20" color="#ffffff">
      <Service v-if="role === 'ai'" />
      <User v-else />
    </el-icon>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.message-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 40px;
  height: 40px;

  /* AI 头像：品牌蓝圆角方块 */
  &.ai {
    border-radius: $radius-md;
    background: $color-avatar-ai;
  }

  /* 用户头像：深灰圆形 */
  &.user {
    border-radius: 50%;
    background: $color-avatar-user;
  }
}
</style>
