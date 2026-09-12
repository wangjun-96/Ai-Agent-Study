<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { School } from '@element-plus/icons-vue'
import TabSwitch from '@/components/common/TabSwitch.vue'
import { TAB_LIST } from '@/config/constant'

const route = useRoute()
const router = useRouter()

/** 当前激活 Tab：与当前路由路径匹配 */
const activeTab = computed(() => route.path)

/** 切换 Tab：路由跳转 */
function handleTabChange(path: string): void {
  router.push(path)
}
</script>

<template>
  <header class="app-header">
    <!-- 第一列：Logo + 项目名称（宽度对齐侧边栏） -->
    <div class="brand" @click="handleTabChange('/interview')">
      <span class="brand-logo">
        <el-icon :size="22" color="#ffffff"><School /></el-icon>
      </span>
      <span class="brand-name">学面通AI</span>
    </div>

    <!-- 第二列：模块切换 Tab，对齐主内容区正上方 -->
    <TabSwitch
      class="header-tabs"
      :tabs="TAB_LIST"
      :model-value="activeTab"
      @update:model-value="handleTabChange"
    />
  </header>
</template>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.app-header {
  display: grid;
  grid-template-columns: #{$sidebar-width} 1fr;
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
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: $color-primary;
}

.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-main;
}

.header-tabs {
  padding-left: 24px;
}
</style>
