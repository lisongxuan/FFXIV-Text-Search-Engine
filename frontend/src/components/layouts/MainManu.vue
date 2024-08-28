// MainManu.vue
<template>

    <el-menu
      class="el-menu-demo"
      mode="horizontal"
      :ellipsis="false"
    >
      <div class="flex-grow" />
      <el-sub-menu index="3">
        <template #title>
        <svg preserveAspectRatio="xMidYMid meet" viewBox="0 0 24 24" width="1.2em" height="1.2em" data-v-63d067da=""><path fill="currentColor" d="m18.5 10l4.4 11h-2.155l-1.201-3h-4.09l-1.199 3h-2.154L16.5 10h2zM10 2v2h6v2h-1.968a18.222 18.222 0 0 1-3.62 6.301a14.864 14.864 0 0 0 2.336 1.707l-.751 1.878A17.015 17.015 0 0 1 9 13.725a16.676 16.676 0 0 1-6.201 3.548l-.536-1.929a14.7 14.7 0 0 0 5.327-3.042A18.078 18.078 0 0 1 4.767 8h2.24A16.032 16.032 0 0 0 9 10.877a16.165 16.165 0 0 0 2.91-4.876L2 6V4h6V2h2zm7.5 10.885L16.253 16h2.492L17.5 12.885z"></path></svg>
      </template>
        <el-menu-item index="3-1" @click="selectLanguage('zh')">中文</el-menu-item>
        <el-menu-item index="3-2" @click="selectLanguage('en')">English</el-menu-item>
    </el-sub-menu>
      <el-menu-item h="full"  @click="dialogFormVisible = true">
        <button
          class="border-none w-full bg-transparent cursor-pointer"
          style="height: var(--ep-menu-item-height)"
        > 
          <i inline-flex i="ep-setting" />
        </button>
      </el-menu-item>
      <el-menu-item h="full" @click="toggleDark()">
        <button
          class="border-none w-full bg-transparent cursor-pointer"
          style="height: var(--ep-menu-item-height)"
        >
          <i inline-flex i="dark:ep-moon ep-sunny" />
        </button>
      </el-menu-item>
      
      <el-sub-menu index="2">
        <template #title>{{$t('header.about')}}</template>
        <el-menu-item index="2-1"><a href="https://arkady14.me" target="_blank" class="github-link">{{$t('header.author')}}</a></el-menu-item>
        <el-menu-item index="2-2">
          <a href="https://github.com/lisongxuan/FFXIV-text-search-engine" target="_blank" class="github-link">
            {{$t('header.github')}}
          </a>
        </el-menu-item>
        <el-menu-item index="2-3" @click="copyToClipboard('selini141414@gmail.com')">
          {{$t('header.contactmail')}}
        </el-menu-item>
        <el-menu-item index="2-4" @click="copyToClipboard('719279154')">
          {{$t('header.contactqq')}}
        </el-menu-item>
        
      <el-menu-item index="2-5">
        <a :href="$router.resolve({ path: '/log' }).href" target="_blank" class="github-link">{{$t('header.updatelog')}}</a>
      </el-menu-item>
      </el-sub-menu>
    </el-menu>

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
