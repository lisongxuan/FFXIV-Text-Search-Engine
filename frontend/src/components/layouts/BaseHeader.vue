// BaseHeader.vue
<template>
  <div class="menus-container"> 
    <el-menu
      class="el-menu-demo"
      mode="horizontal"
      :ellipsis="false"
    >
    <router-link :to="{ path: '/' }" class="github-link">
  <el-menu-item index="0">
    <img src="/favicon.png" v-if="!isDark" style="width: 100%; height: 100%; margin-right: 8px;">
    <img src="/favicon-dark.png" v-else style="width: 100%; height: 100%; margin-right: 8px;" >
    {{  $t('header.title') }}
  </el-menu-item>
</router-link>
    </el-menu>

    <el-menu
      :default-active="'include'"
      class="el-menu-demo flex-grow"
      mode="horizontal"
      :ellipsis="false"
      @select="handleSelect"
    >
    <el-tooltip
        class="box-item"
        effect="dark"
        :content="$t('header.partialDesc')"
        placement="bottom-start"
      >
      <el-menu-item index="include">{{$t('header.partial')}}</el-menu-item></el-tooltip>
      <el-tooltip
        class="box-item"
        effect="dark"
        :content="$t('header.similarDesc')"
        placement="bottom-start"
      >
      <el-menu-item index="similar">{{$t('header.similar')}}</el-menu-item></el-tooltip>
      <el-tooltip
        class="box-item"
        effect="dark"
        :content="$t('header.exactDesc')"
        placement="bottom-start"
      >
      <el-menu-item index="exact">{{$t('header.exact')}}</el-menu-item></el-tooltip>
    </el-menu>
<MainManu/>
  </div>
</template>

<script lang="ts" setup>
import { ref, inject, Ref } from 'vue'
import { ElMessage } from 'element-plus';
import { toggleDark ,isDark} from '~/composables';
import Setting from 'path/to/Setting.vue'; // Import the Setting component
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
const { t ,locale} = useI18n();
const selected = inject<Ref<string>>('headerSelected', ref('include'))
const dialogFormVisible = inject<Ref<Boolean>>('dialogFormVisible', ref(false))
const handleSelect = (key: string, keyPath: string[]) => {
  selected.value = key
}
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    // 使用 ElMessage 显示复制成功的提示
    ElMessage({
      message: t('header.copysuccess'),
      type: 'success',
      duration: 3000, // 持续时间，单位毫秒
    });
  }).catch(err => {
    // 使用 ElMessage 显示复制失败的提示
    ElMessage.error({
      message: t('header.copyfail'),
      duration: 3000, // 持续时间，单位毫秒
    });
    console.error(t('header.copyfail'), err);
  });

}
const selectLanguage = (lang: string) => {
  locale.value = lang;
  Cookies.set('pageLanguage', JSON.stringify(lang), { expires: 7 }); // cookies有效期为7天
  ElMessage({
      message: t('header.selectlanguagesuccess'),
      type: 'success',
      duration: 6000, // 持续时间，单位毫秒
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
