<template>
  <el-config-provider namespace="ep">
    <BaseHeader />
    <div class="flex main-container">
      <div class="custom-width py-4">
        <div class="flex-row"> 
          <el-select
            v-model="selectValue"
            placeholder="Select"
            size="large"
            style="width: 240px"
            @change="handleInputChange"
            
          >
            <el-option
              v-for="item in options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
          <el-input
            v-model="inputValue"
            size="large"
            placeholder="请输入搜索内容"
            clearable
            :suffix-icon="Search"
            @input="handleInputChange"
          />
        </div>
        <el-table :data="tableData" style="width: 100%">
    <el-table-column prop="position" label="位置" width="180"></el-table-column>
    <el-table-column
      v-for="column in columns"
      :key="column.id"
      :prop="`language_${column.language}`"
      :label="column.text"
    >
    </el-table-column>
  </el-table>
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

.custom-width {
  width: 90%;
  margin-left: 20px; /* 添加左侧缩进 */
}
.flex-row {
  display: flex;
  align-items: center; /* 确保选项和输入框垂直居中 */
  gap: 20px; /* 在选项和输入框之间添加一些间隙 */
}
</style>

<script lang="ts" setup>
import { ref, reactive, onMounted, computed } from 'vue'
import axios from 'axios';
import { Search } from '@element-plus/icons-vue'
import config from './config.json';

interface Column {
  id: number;
  text: string;
  language: keyof typeof languages;
  version: string;
}
interface DataItem {
  id: number;
  name: string;
  data: Array<{
    language: string;
    version: string;
    data: string;
  }>;
  path: string;
}
const inputValue = ref('')
const versions = ref([]);
const latestVersions = ref([]);
const languages = reactive({
  'en': '英语',
  'jp': '日语',
  'cn': '中文',
});
var selectedVersions = ref([]);
const tableData = ref<string[][]>([]);
let columns = ref<Column[]>([]); // Use ref to ensure reactivity
const selectValue = ref('all');

// 使用计算属性来动态生成options
const options = computed(() => [
  { value: 'all', label: '全部语言' },
  ...columns.value.map(column => ({ value: column.id, label: `${column.text}` }))
]);

const handleInputChange = (value: string) => {
  if (selectValue.value === 'all') {
    // 使用 map() 提取 language 和 version，然后使用 join() 连接成字符串
    const searchedLanguages = columns.value.map(column => column.language).join(',');
    const searchedVersions = columns.value.map(column => column.version).join(',');
    let dataItems: DataItem[] = [];
    getMultiLanguagesDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
    const row: any = { position: item.name };
    item.data.forEach(data => {
      row[`language_${data.language}`] = data.data;
    });
    return row;
  });
  console.log(tableData.value);
});

  } else {
    // 使用 map() 提取 language 和 version，然后使用 join() 连接成字符串
    const searchedLanguages = columns.value.map(column => column.language).join(',');
    const searchedVersions = columns.value.map(column => column.version).join(',');
    const selectedOption = options.value.find(option => option.value === selectValue.value);
    const selectedColumn = columns.value.find(column => column.id === selectedOption?.value);
// Log the found option, if any
console.log(selectedColumn);
    let dataItems: DataItem[] = [];
    getDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions, language:selectedColumn?.language, version:selectedColumn?.version}).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
    const row: any = { position: item.name };
    item.data.forEach(data => {
      row[`language_${data.language}`] = data.data;
    });
    return row;
  });
  console.log(tableData.value);
});
  }
};

const getMultiLanguagesDataByData = async (data: any) => {
  // 将对象转换为查询字符串
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/multi_language_data_by_data?${queryParams}`);
  return result.data;
};
const getDataByData = async (data: any) => {
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/multi_data_by_data?${queryParams}`);
  return result.data;
};

onMounted(async () => {
  try {
    const versionsResponse = await axios.get(`${config.backendUrl}/versions`);
    versions.value = versionsResponse.data;
    const latestVersionsResponse = await axios.get(`${config.backendUrl}/latest_versions`);
    latestVersions.value = latestVersionsResponse.data;
    selectedVersions.value = latestVersions.value;
    columns.value = selectedVersions.value.map((item, index) => {
  const languageCode = Object.keys(item)[0] as keyof typeof languages;
  const version = item[languageCode];
  const languageText = languages[languageCode];
  return {
    id: index, 
    text: `${languageText}-${version}`,
    language: languageCode,
    version: version
  };
});
    console.log(columns.value);
  } catch (error) {
    console.error("Failed to fetch data:", error);
  }
});
</script>