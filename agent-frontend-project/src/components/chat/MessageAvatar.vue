<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MessageRole } from '@/types/interview'
import { Service, User } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

/** 消息头像：AI 为品牌蓝圆角方块图标，用户为真实头像（后端代理加载） */
interface Props {
  /** 消息角色 */
  role: MessageRole
}

withDefaults(defineProps<Props>(), {
  role: 'ai',
})

const userStore = useUserStore()

/** 用户头像 URL：走后端代理接口，无头像时后端返回默认 SVG */
const userAvatarUrl = computed(
  () => `/api/v1/avatar/${userStore.userInfo?.id ?? 0}`,
)

/** 头像 img 加载失败标记：true 时回退到默认图标 */
const avatarLoadFailed = ref(false)

/** 是否显示真实头像 img（有用户 ID 且未加载失败） */
const showAvatarImg = computed(
  () => !!userStore.userInfo?.id && !avatarLoadFailed.value,
)

/** img 加载失败时切换到图标 */
function handleAvatarError(): void {
  avatarLoadFailed.value = true
}
</script>

<template>
  <div class="message-avatar" :class="role">
    <!-- AI 头像：固定图标 -->
    <el-icon v-if="role === 'ai'" :size="20" color="#ffffff">
      <Service />
    </el-icon>
    <!-- 用户头像：真实头像，加载失败回退到图标 -->
    <img
      v-else-if="showAvatarImg"
      :src="userAvatarUrl"
      alt="用户头像"
      @error="handleAvatarError"
    />
    <el-icon v-else :size="20" color="#ffffff">
      <User />
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
  overflow: hidden;

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

  /* 用户真实头像 img：撑满容器 */
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}
</style>
