// App.vue
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
  <el-table-column label="位置" width="180">
    <template #default="{ row }">
      <div>{{ row.position }}</div> 
      <el-button size="small" @click="goToContext(row)">跳转至上下文</el-button> 
    </template>
  </el-table-column>
  <el-table-column
    v-for="column in columns"
    :key="column.id"
    :label="column.text"
  >
    <template #default="{ row }">
      <span v-html="row[`language_${column.language}_version_${column.version}`]"></span>
    </template>
  </el-table-column>
</el-table>

      </div>
    </div>
  </el-config-provider>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, computed, provide, watch } from 'vue'
import axios from 'axios';
import { Search } from '@element-plus/icons-vue'
import config from './config.json';

const headerSelected = ref('include');
provide('headerSelected', headerSelected);

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
const regex = /[\s,.!?;:"'()\[\]<>、。，！？；：“”（）【】《》]+/;

watch(headerSelected, (newValue, oldValue) => {
  handleInputChange(newValue);
});
// 使用计算属性来动态生成options
const options = computed(() => [
  { value: 'all', label: '全部语言' },
  ...columns.value.map(column => ({ value: column.id, label: `${column.text}` }))
]);
interface RowType {
  position: string; 
  [key: string]: any; 
}

const goToContext = (row: RowType) => {
  const substrings = inputValue.value.split(regex);
  console.log("跳转至上下文", row);
  const searchedLanguages = columns.value.map(column => column.language).join(',');
  const searchedVersions = columns.value.map(column => column.version).join(',');
  let dataItems: DataItem[] = [];
  getMultiLanguagesDataAroundName({ name: row.position,languages: searchedLanguages, versions: searchedVersions }).then((data: DataItem[]) => {
    dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
      console.log(tableData.value);
  });
};
const handleInputChange = (value: string) => {
  const substrings = inputValue.value.split(regex);
  console.log(substrings);
  if (selectValue.value === 'all') {
    // 使用 map() 提取 language 和 version，然后使用 join() 连接成字符串
    const searchedLanguages = columns.value.map(column => column.language).join(',');
    const searchedVersions = columns.value.map(column => column.version).join(',');
    let dataItems: DataItem[] = [];
    if(headerSelected.value === 'similar'){
    getMultiLanguagesDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
      console.log(tableData.value);
    });
}
else if(headerSelected.value === 'include'){
    getIncludeMultiLanguagesDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
      console.log(tableData.value);
    });
  } 
  else if(headerSelected.value === 'exact'){
    getExactMultiLanguagesDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
      console.log(tableData.value);
    });
  }
}
  
  else {
    // 使用 map() 提取 language 和 version，然后使用 join() 连接成字符串
    const searchedLanguages = columns.value.map(column => column.language).join(',');
    const searchedVersions = columns.value.map(column => column.version).join(',');
    const selectedOption = options.value.find(option => option.value === selectValue.value);
    const selectedColumn = columns.value.find(column => column.id === selectedOption?.value);
    let dataItems: DataItem[] = [];
    if(headerSelected.value === 'similar'){
    getDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions, language: selectedColumn?.language, version: selectedColumn?.version }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
    });
  }
  else if(headerSelected.value === 'include'){
    getIncludeDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions, language: selectedColumn?.language, version: selectedColumn?.version }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
    });
  }
  else if(headerSelected.value === 'exact'){
    getExactDataByData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions, language: selectedColumn?.language, version: selectedColumn?.version }).then((data: DataItem[]) => {
      dataItems = data;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
    });
  }
}
};
const highlight = (text: string, keywords: string[]) => {
  const regex = new RegExp(`(${keywords.join('|')})`, 'gi');
  return text.replace(regex, '<span style="color: red">$1</span>');
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
const getIncludeMultiLanguagesDataByData = async (data: any) => {
  // 将对象转换为查询字符串
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/include_multi_language_data_by_data?${queryParams}`);
  return result.data;
};
const getIncludeDataByData = async (data: any) => {
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/include_multi_data_by_data?${queryParams}`);
  return result.data;
};
const getExactMultiLanguagesDataByData = async (data: any) => {
  // 将对象转换为查询字符串
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/exact_multi_language_data_by_data?${queryParams}`);
  return result.data;
};
const getExactDataByData = async (data: any) => {
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/exact_multi_data_by_data?${queryParams}`);
  return result.data;
};
const getMultiLanguagesDataAroundName = async (data: any) => {
  const queryParams = new URLSearchParams(data).toString();
  const result = await axios.get(`${config.backendUrl}/multi_language_data_around_name?${queryParams}`);
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
