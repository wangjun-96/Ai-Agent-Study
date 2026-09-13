<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CaretBottom, SwitchButton, UserFilled } from '@element-plus/icons-vue'
import TabSwitch from '@/components/common/TabSwitch.vue'
import { BRAND_LOGO_URL, LOGIN_PATH, TAB_LIST } from '@/config/constant'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

/** 当前激活 Tab：与当前路由路径匹配 */
const activeTab = computed(() => route.path)

/** 头部展示的用户名：用户信息加载完成前兜底显示 */
const displayName = computed(() => userStore.username || '用户')

/** 切换 Tab：路由跳转 */
function handleTabChange(path: string): void {
  router.push(path)
}

/** 用户下拉菜单命令分发 */
async function handleUserCommand(command: string): Promise<void> {
  if (command === 'profile') {
    // 个人信息页尚未实现，先预留入口
    ElMessage.info('个人信息功能开发中，敬请期待')
    return
  }
  if (command === 'logout') {
    await handleLogout()
  }
}

/** 退出登录：二次确认后清理令牌并跳转登录页 */
async function handleLogout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定退出当前账号吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    // 用户取消退出，无需处理
    return
  }
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push(LOGIN_PATH)
}
</script>

<template>
  <header class="app-header">
    <!-- 第一列：小 Logo + 项目名称（宽度对齐侧边栏），点击回到面试间 -->
    <div class="brand" @click="handleTabChange('/interview')">
      <img class="brand-logo" :src="BRAND_LOGO_URL" alt="学面通AI Logo" />
      <span class="brand-name">学面通AI</span>
    </div>

    <!-- 第二列：模块切换 Tab，对齐主内容区正上方 -->
    <TabSwitch
      class="header-tabs"
      :tabs="TAB_LIST"
      :model-value="activeTab"
      @update:model-value="handleTabChange"
    />

    <!-- 第三列：头像 + 用户名整体，点击弹出用户菜单 -->
    <el-dropdown
      trigger="click"
      placement="bottom-end"
      @command="handleUserCommand"
    >
      <div class="user-entry">
        <span class="user-avatar">
          <img v-if="userStore.avatarUrl" :src="userStore.avatarUrl" alt="用户头像" />
          <el-icon v-else :size="18"><UserFilled /></el-icon>
        </span>
        <span class="user-name" :title="displayName">{{ displayName }}</span>
        <el-icon class="user-arrow" :size="12"><CaretBottom /></el-icon>
      </div>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="profile" :icon="UserFilled">
            个人信息
          </el-dropdown-item>
          <el-dropdown-item command="logout" divided :icon="SwitchButton">
            退出登录
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </header>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.app-header {
  display: grid;
  grid-template-columns: #{$sidebar-width} 1fr auto;
  align-items: center;
  flex-shrink: 0;
  height: $header-height;
  /* 左侧不留 padding，第一列宽度即对齐侧边栏 */
  padding: 0 24px 0 0;
  background: $color-bg-white;
  border-bottom: 1px solid $color-border;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 24px;
  cursor: pointer;
}

.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 1px 6px rgba(251, 197, 49, 0.35);
}

.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-main;
}

.header-tabs {
  padding-left: 24px;
}

/* 用户入口整体：头像 + 用户名 + 下拉箭头，点击弹出用户菜单 */
.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 10px;
  margin-right: 4px;
  border-radius: $radius-md;
  cursor: pointer;
  outline: none;
  transition: background-color 0.2s;

  &:hover,
  &:focus {
    background: $color-bg-gray;
  }
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  overflow: hidden;
  border-radius: 50%;
  color: $color-primary-hover;
  background: $color-primary-light;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.user-name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: $color-text-main;
}

.user-arrow {
  color: $color-text-secondary;
}
</style>
