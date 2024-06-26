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
          <div v-for="item in options">
          <el-tooltip
          v-if="item.value === 'all'"
        class="box-item"
        effect="dark"
        content="搜索所有语言，可能导致运行缓慢，请谨慎使用"
        placement="top"
      >
            <el-option
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-tooltip>
          <el-option v-else
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </div>
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
        <el-pagination
          background
          layout="prev, pager, next"
          :total="pagination.total"
          :page-size="pagination.per_page"
          :current-page.sync="pagination.page"
          @current-change="handlePageChange"
          style="margin-top: 10px;"
        />
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
    <div class="footer-text">
      <el-divider></el-divider>
      FINAL FANTASY is a registered trademark of Square Enix Holdings Co., Ltd.<br>
      All contents here © SQUARE ENIX
    </div>
    <el-dialog v-model="dialogFormVisible" title="设置" width="500">
      <h3>语言/版本设置</h3>
      <div v-for="(item, index) in allVersions" :key="index">
      <h4>{{ languages[item.language] }}</h4>
      <el-checkbox-group v-model="tempSelectedVersions[item.language]">
        <el-checkbox
          v-for="version in item.versions"
          :key="version"
          :label="version"
        >
          {{ version }}
        </el-checkbox>
      </el-checkbox-group>
    </div>
    <h4>默认搜索语言</h4>
    <el-cascader v-model="tempDefaultLanguage" :options="languageOptions" />
    <el-divider></el-divider>
    <h3>显示设置</h3>
    <h4>每页数据条数</h4>
    <el-input-number v-model="tempPaginationNumber" :min="2" :max="50" />
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogFormVisible = false">取消</el-button>
          <el-button type="primary" @click="dialogFormVisible = false, handleConfirm()">确认</el-button>
        </div>
      </template>
      <el-divider></el-divider>
      <h5>*所有设置均用Cookies存储，更改设置视为同意使用Cookies</h5>
    </el-dialog>
  </el-config-provider>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, computed, provide, watch } from 'vue'
import axios from 'axios';
import { Search } from '@element-plus/icons-vue'
import config from './config.json';
import { ca } from 'element-plus/es/locale';
import Cookies from 'js-cookie';
const headerSelected = ref('include');
provide('headerSelected', headerSelected);
const dialogFormVisible = ref(false);
provide('dialogFormVisible', dialogFormVisible);
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
interface Version{
  language: string;
  id: number;
  run_date: string;
  version: string;
}
interface OrganizedVersion {
  language: string;
  versions: string[];
}
const tempPaginationNumber = ref(10);
const paginationNumber =ref(10);
const inputValue = ref('')
const versions = ref([]);
const latestVersions = ref<{ [key: string]: string }[]>([]);
const languages: { [key: string]: string } = reactive({
  'en': '英语',
  'jp': '日语',
  'cn': '中文',
  'de': '德语',
  'fr': '法语',
  'kr': '韩语'
});
var selectedVersions = ref<{ [key: string]: string; }[]>([]);
const tableData = ref<string[][]>([]);
const cacheRow = ref<RowType>();
const languageOptions: { value: string; label: string }[] = [];
let columns = ref<Column[]>([]); // Use ref to ensure reactivity
const selectValue = ref('all');
const tempSelectedVersions = ref<Record<string, string[]>>({});;
const defaultLanguage = ref(config.defaultLanguage);
const tempDefaultLanguage = ref(config.defaultLanguage);
const regex = /[\s,.!?;:"'()\[\]<>、。，！？；：“”（）【】《》]+/;
const pagination = reactive<Pagination>({
  total: 0,
  page: 1,
  per_page: 10
});
var allVersions = ref<OrganizedVersion[]>([]);
var cacheData= ref<string[][]>([]);
var cachePagination= reactive<Pagination>({
  total: 0,
  page: 1,
  per_page: 10
});
var contextFlag=ref(false);
var hintForAllVisible=ref(false);
watch(headerSelected, (newValue, oldValue) => {
  handleInputChange(newValue);
});
watch(paginationNumber, (newValue) => {
      Cookies.set('paginationNumber', newValue.toString(), { expires: 7 }); // cookies有效期为7天
    });

    watch(selectedVersions, (newValue) => {
      Cookies.set('selectedVersions', JSON.stringify(newValue), { expires: 7 }); // cookies有效期为7天
    });
    watch(defaultLanguage, (newValue) => {
      Cookies.set('defaultLanguage', JSON.stringify(newValue), { expires: 7 }); // cookies有效期为7天
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

   const handleConfirm=() => {
    defaultLanguage.value = tempDefaultLanguage.value;
    const transformedArray: { [key: string]: string }[] = [];
    Object.keys(tempSelectedVersions.value).forEach(key => {
      tempSelectedVersions.value[key as keyof typeof tempSelectedVersions.value].forEach(value => {
    let obj: any = {};
    obj[key] = value;
    transformedArray.push(obj);
  });
});
    selectedVersions.value = transformedArray;
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
      if (columns.value[i].language==defaultLanguage.value){
        if (tempSelect.language==defaultLanguage.value && tempSelect.version>columns.value[i].version) 
        continue;
      else
        tempSelect=columns.value[i];
      }
    }
    paginationNumber.value=tempPaginationNumber.value;
    pagination.per_page=paginationNumber.value;
    if (contextFlag.value==false){
      handleInputChange(inputValue.value, false);
    }
    else{
      if (cacheRow.value) {
        goToContext(cacheRow.value);
        
      }
    }
    var tempSelect=columns.value[0];
    for (var i=0;i<columns.value.length;i++){
      if (columns.value[i].language==defaultLanguage.value){
        if (tempSelect.language==defaultLanguage.value && tempSelect.version>columns.value[i].version) 
        continue;
      else
        tempSelect=columns.value[i];
      }
    }
    selectValue.value = tempSelect.text;
  };
const goToContext = (row: RowType) => {
  cacheRow.value = row;
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
  getMultiLanguagesDataAroundName({ name: row.position, languages: searchedLanguages, versions: searchedVersions,near_range: Math.floor(pagination.per_page / 2) }).then((data: any) => {
    dataItems = data.data;
    pagination.total = data.pagination.total;
    tableData.value = dataItems.map(item => {
      const row: any = { position: item.name };
      item.data.forEach(data => {
        row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
      });
      return row;
    });
  });
};
const handleInputChange = (value: string, newSearchFlag: boolean = true) => {
  if(inputValue.value === '' || inputValue.value === null || inputValue.value === undefined ||contextFlag.value===true) {
    return;
  }
  if (newSearchFlag) {
  pagination.total= 0;
  pagination.page= 1;
  pagination.per_page= 10;}
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
      pagination.total = data.pagination.total;
      tableData.value = dataItems.map(item => {
        const row: any = { position: item.name };
        item.data.forEach(data => {
          row[`language_${data.language}_version_${data.version}`] = highlight(data.data, substrings);
        });
        return row;
      });
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
    console.warn(`Expected item.data to be an array, but got:`, item.data);
  }
  return row;
});
    });
  }
};
const handlePageChange = (page: number) => {
  pagination.page = page;
  handleInputChange(inputValue.value, false);
};
const handleReturn = () => {
  tableData.value=cacheData.value;
  contextFlag.value=false;
  if (pagination.per_page==cachePagination.per_page){
    pagination.total=cachePagination.total;
    pagination.page=cachePagination.page;
    pagination.per_page=cachePagination.per_page;
  }
  else{
    handleInputChange(inputValue.value, false);
  }

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

const organizeVersion = (data: Version[]): OrganizedVersion[] => {
  const result = data.reduce<OrganizedVersion[]>((acc, current) => {
    const existingLanguage = acc.find(item => item.language === current.language);

    if (existingLanguage) {
      existingLanguage.versions.push(current.version);
    } else {
      acc.push({
        language: current.language,
        versions: [current.version]
      });
    }

    return acc;
  }, []);

  result.forEach(language => {
    language.versions.sort((a, b) => {
      const aParts = a.split('.').map(Number);
      const bParts = b.split('.').map(Number);
      for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
        if ((bParts[i] || 0) > (aParts[i] || 0)) return 1;
        if ((bParts[i] || 0) < (aParts[i] || 0)) return -1;
      }
      return 0;
    });
  });
  result.sort((a, b) => {
    if (a.language === defaultLanguage.value) return -1;
    if (b.language === defaultLanguage.value) return 1;
    if (a.versions[0]>b.versions[0]) return 1;
    if (a.versions[0]<b.versions[0]) return -1;
    if (a.language<b.language) return 1;
    if (a.language>b.language) return -1;
    return 0;
  });
  return result;
}
onMounted(async () => {
  try {

    const versionsResponse = await axios.get(`${config.backendUrl}/versions`);
    versions.value = versionsResponse.data;
    allVersions.value = organizeVersion(versions.value);
    latestVersions.value = allVersions.value.map(item => {
  return { [item.language]: item.versions[0] };
});
    for (let i = 0; i < allVersions.value.length; i++) {
      languageOptions.push({
        value: allVersions.value[i].language,
        label: languages[allVersions.value[i].language]
      })
    }
const storedPaginationNumber = Cookies.get('paginationNumber');
      if (storedPaginationNumber) {
        paginationNumber.value = parseInt(storedPaginationNumber, 10);
        pagination.per_page = paginationNumber.value;
        tempPaginationNumber.value = paginationNumber.value;
      }
const storedDefaultLanguage = Cookies.get('defaultLanguage');
      if (storedDefaultLanguage) {
        defaultLanguage.value = JSON.parse(storedDefaultLanguage);
        tempDefaultLanguage.value = JSON.parse(storedDefaultLanguage);
      }
      const storedSelectedVersions = Cookies.get('selectedVersions');
      if (storedSelectedVersions) {
        selectedVersions.value = JSON.parse(storedSelectedVersions);
      }
      else{
    selectedVersions.value = latestVersions.value;
  }
  selectedVersions.value.forEach(item => {
  const language = Object.keys(item)[0];
  if (tempSelectedVersions.value[language]) {
    if (!tempSelectedVersions.value[language].includes(item[language])) {
      tempSelectedVersions.value[language].push(item[language]);
    }
  } else {
    tempSelectedVersions.value[language] = [item[language]];
  }
});
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
      if (columns.value[i].language==defaultLanguage.value){
        if (tempSelect.language==defaultLanguage.value && tempSelect.version>columns.value[i].version) 
        continue;
      else
        tempSelect=columns.value[i];
      }
    }
    selectValue.value = tempSelect.text;
  } catch (error) {
    console.error("Failed to fetch data:", error);
  }
});
</script>

<style>
.main-container {
  margin-left: 2%;
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
.footer-text {
  margin-left: 2%;
  width: 95%;
  margin-top: 20px;  
  color: #666;
  font-size: 14px; 
}
</style>
