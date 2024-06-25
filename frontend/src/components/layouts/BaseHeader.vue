// BaseHeader.vue
<template>
  <div class="menus-container"> 
    <el-menu
      class="el-menu-demo"
      mode="horizontal"
      :ellipsis="false"
    >
      <el-menu-item index="0" :to="{ path: '/' }">最终幻想14 文本搜索器</el-menu-item>
    </el-menu>

    <el-menu
      :default-active="'include'"
      class="el-menu-demo flex-grow"
      mode="horizontal"
      :ellipsis="false"
      @select="handleSelect"
    >
      <el-menu-item index="include">部分搜索</el-menu-item>
      <el-menu-item index="similar">相似搜索</el-menu-item>
      <el-menu-item index="exact">精确搜索</el-menu-item>
      <el-menu-item disabled index="advanced">高级搜索</el-menu-item>
    </el-menu>

    <el-menu
      class="el-menu-demo"
      mode="horizontal"
      :ellipsis="false"
    >
      <div class="flex-grow" />
      <el-menu-item h="full" @click="toggleDark()">
        <button
          class="border-none w-full bg-transparent cursor-pointer"
          style="height: var(--ep-menu-item-height)"
        >
          <i inline-flex i="dark:ep-moon ep-sunny" />
        </button>
      </el-menu-item>
      
      <el-sub-menu index="2">
        <template #title>关于</template>
        <el-menu-item index="2-1">开发：Selini@神拳痕</el-menu-item>
        <el-menu-item index="2-2">
          <a href="https://github.com/lisongxuan/FFXIV-text-search-engine" target="_blank" class="github-link">
            GitHub Repository
          </a>
        </el-menu-item>
        <el-menu-item index="2-3" @click="copyToClipboard('selini141414@gmail.com')">
          反馈邮箱（建议，点击复制）
        </el-menu-item>
        <el-menu-item index="2-4" @click="copyToClipboard('719279154')">
          反馈QQ（点击复制）
        </el-menu-item>
        <el-menu-item index="2-5">更新日志</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script lang="ts" setup>
import { ref, inject, Ref } from 'vue'
import { ElMessage } from 'element-plus';
import { toggleDark } from '~/composables';

const selected = inject<Ref<string>>('headerSelected', ref('include'))

const handleSelect = (key: string, keyPath: string[]) => {
  selected.value = key
}

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    // 使用 ElMessage 显示复制成功的提示
    ElMessage({
      message: '复制成功',
      type: 'success',
      duration: 3000, // 持续时间，单位毫秒
    });
  }).catch(err => {
    // 使用 ElMessage 显示复制失败的提示
    ElMessage.error({
      message: '复制失败',
      duration: 3000, // 持续时间，单位毫秒
    });
    console.error('复制失败', err);
  });

}
</script>

<style>
.flex-grow {
  flex-grow: 1;
}
.github-link {
  color: inherit; /* 继承父元素的字体颜色 */
  text-decoration: none; /* 去除下划线 */
  display: flex; /* 使链接内容居中 */
  align-items: center; /* 垂直居中 */
  justify-content: center; /* 水平居中 */
}
.menus-container {
  display: flex; 
  justify-content: space-between; 
}

</style>
