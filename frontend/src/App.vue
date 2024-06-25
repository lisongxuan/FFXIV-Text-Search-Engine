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
        <el-button v-if="contextFlag" @click="handleReturn()" type="primary" style="margin: 10px;">返回搜索</el-button>
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
        <el-pagination
          background
          layout="prev, pager, next"
          :total="pagination.total"
          :page-size="pagination.per_page"
          :current-page.sync="pagination.page"
          @current-change="handlePageChange"
        />
        
      </div>
    </div>
  </el-config-provider>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, computed, provide, watch } from 'vue'
import axios from 'axios';
import { Search } from '@element-plus/icons-vue'
import config from './config.json';
import { ca } from 'element-plus/es/locale';

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
interface Pagination {
  total: number;
  page: number;
  per_page: number;
}

const inputValue = ref('')
const versions = ref([]);
const latestVersions = ref([]);
const languages: { [key: string]: string } = reactive({
  'en': '英语',
  'jp': '日语',
  'cn': '中文',
});
var selectedVersions = ref([]);
const tableData = ref<string[][]>([]);
let columns = ref<Column[]>([]); // Use ref to ensure reactivity
const selectValue = ref('all');
const regex = /[\s,.!?;:"'()\[\]<>、。，！？；：“”（）【】《》]+/;
const pagination = reactive<Pagination>({
  total: 0,
  page: 1,
  per_page: 10
});
var cacheData= ref<string[][]>([]);
var cachePagination= reactive<Pagination>({
  total: 0,
  page: 1,
  per_page: 10
});
var contextFlag=ref(false);
watch(headerSelected, (newValue, oldValue) => {
  handleInputChange(newValue);
});
// 使用计算属性来动态生成options
const options = computed(() => [
  { value: 'all', label: '全部语言' },
  ...columns.value.map(column => ({ value: column.text, label: `${column.text}` }))
]);
interface RowType {
  position: string; 
  [key: string]: any; 
}

const goToContext = (row: RowType) => {
  const substrings = inputValue.value.split(regex);
  const searchedLanguages = columns.value.map(column => column.language).join(',');
  const searchedVersions = columns.value.map(column => column.version).join(',');
  let dataItems: DataItem[] = [];
  if(!contextFlag.value){
cacheData.value=tableData.value;
cachePagination.total=pagination.total;
cachePagination.page=pagination.page;
cachePagination.per_page=pagination.per_page;
contextFlag.value=true;}
  getMultiLanguagesDataAroundName({ name: row.position, languages: searchedLanguages, versions: searchedVersions, page: pagination.page, per_page: pagination.per_page }).then((data: any) => {
    dataItems = data.data;
    pagination.total = data.pagination.total;
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
  if(inputValue.value === '' || inputValue.value === null || inputValue.value === undefined ||contextFlag.value===true) {
    return;
  }
  const substrings = inputValue.value.split(regex);
  if (selectValue.value === 'all') {
    const searchedLanguages = columns.value.map(column => column.language).join(',');
    const searchedVersions = columns.value.map(column => column.version).join(',');
    let dataItems: DataItem[] = [];
    const fetchData = headerSelected.value === 'similar' ? getMultiLanguagesDataByData :
                      headerSelected.value === 'include' ? getIncludeMultiLanguagesDataByData :
                      getExactMultiLanguagesDataByData;
    fetchData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions, page: pagination.page, per_page: pagination.per_page }).then((data: any) => {
      dataItems = data.data;
      console.log(dataItems);
      pagination.total = data.pagination.total;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        console.log(item.data);
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
      console.log(tableData.value);
    });
  } else {
    const searchedLanguages = columns.value.map(column => column.language).join(',');
    const searchedVersions = columns.value.map(column => column.version).join(',');
    const selectedOption = options.value.find(option => option.value === selectValue.value);
    const selectedColumn = columns.value.find(column => column.text === selectedOption?.value);
    let dataItems: DataItem[] = [];
    const fetchData = headerSelected.value === 'similar' ? getDataByData :
                      headerSelected.value === 'include' ? getIncludeDataByData :
                      getExactDataByData;
    fetchData({ data: inputValue.value, languages: searchedLanguages, versions: searchedVersions, language: selectedColumn?.language, version: selectedColumn?.version, page: pagination.page, per_page: pagination.per_page }).then((data: any) => {
      dataItems = data.data;
      pagination.total = data.pagination.total;
      tableData.value = dataItems.map(item => {
  const row: any = { position: item.name };
  
  // Check if item.data is an array before iterating
  if (Array.isArray(item.data)) {
    item.data.forEach(data => {
      row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
    });
  } else {
    // Handle the case where item.data is not an array
    // For example, you might want to log a warning or assign a default value
    console.warn(`Expected item.data to be an array, but got:`, item.data);
    // Assign a default value or perform other error handling as needed
  }
  return row;
});
    });
  }
};
const handlePageChange = (page: number) => {
  pagination.page = page;
  handleInputChange(inputValue.value);
};
const handleReturn = () => {
  tableData.value=cacheData.value;
  contextFlag.value=false;
  pagination.total=cachePagination.total;
  pagination.page=cachePagination.page;
  pagination.per_page=cachePagination.per_page;
};
const highlight = (text: string, keywords: string[]) => {
  const regex = new RegExp(`(${keywords.join('|')})`, 'gi');
  return text.replace(regex, '<span style="color: red">$1</span>');
};
const getMultiLanguagesDataByData = async (data: any) => {
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
    const defaultLanguage = config.defaultLanguage;
    const versionsResponse = await axios.get(`${config.backendUrl}/versions`);
    versions.value = versionsResponse.data;
    const latestVersionsResponse = await axios.get(`${config.backendUrl}/latest_versions`);
    const latestDefaultLanguageVersion = latestVersionsResponse.data.filter((item: any) => Object.keys(item)[0] === defaultLanguage)[0][defaultLanguage];
    
    console.log(latestDefaultLanguageVersion);
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
    var tempSelect=columns.value[0];
    for (var i=0;i<columns.value.length;i++){
      if (columns.value[i].language==defaultLanguage){
        if (tempSelect.language==defaultLanguage && tempSelect.version>columns.value[i].version) 
        continue;
      else
        tempSelect=columns.value[i];
      }
    }
    console.log(tempSelect);
    selectValue.value = tempSelect.text;
    console.log(columns.value);
  } catch (error) {
    console.error("Failed to fetch data:", error);
  }
});
</script>

<style>
.main-container {
  margin-left: 250px;
}
.custom-width {
  width: 95%;
}
.el-table .highlight {
  background-color: yellow;
}
.flex-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}
</style>
