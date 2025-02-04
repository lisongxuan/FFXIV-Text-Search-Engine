<script setup lang="ts">
import { ref, reactive, onMounted, computed, provide, watch } from 'vue'
import { ElMessage } from "element-plus";
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
const { t ,locale} = useI18n();
defineProps<{ msg: string }>();

onMounted(() => {
  const storedPageLanguage = Cookies.get('pageLanguage');
  if (storedPageLanguage) {
    locale.value = JSON.parse(storedPageLanguage);
  }
  document.title = t('updateLog.pageTitle');
});
</script>

<template>
  <el-config-provider namespace="ep">
    <EmptyHeader />
    <div>
      <div w="full" py="4">
        <h1 color="$ep-color-primary">{{$t('updateLog.title')}}</h1>
      </div>
      <div v-for="log in $tm('updateLog.content')" :key="log.version" :timestamp="log.date" placement="top">
            <h3>{{ log.version }}</h3>
            <h4>{{ log.date }}</h4>
              <p v-for="detail in log.detail" :key="detail">{{ detail }}</p>
              <div style="height: 20px;"></div>
      </div>

    </div>
  </el-config-provider>
</template>

<style>
#app {
  text-align: center;
  color: var(--ep-text-color-primary);
}

.main-container {
  height: calc(100vh - var(--ep-menu-item-height) - 3px);
}

.ep-button {
  margin: 4px;
}

.ep-button + .ep-button {
  margin-left: 0;
  margin: 4px;
}
</style>