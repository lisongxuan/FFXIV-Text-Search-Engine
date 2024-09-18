import { createApp } from 'vue';
import UpdateLog from './UpdateLog.vue';
import router from './router';
import { createI18n } from 'vue-i18n';
import en from './languages/en';
import zh from './languages/zh';
// If you want to use ElMessage, import it.
import "element-plus/theme-chalk/src/message.scss";
import "~/styles/index.scss";
import "uno.css";
const messages = {
    en,
    zh
}
const i18n = createI18n({
    locale: navigator.language || 'en',
    messages,
    legacy: false
})
const app = createApp(UpdateLog);
app.use(router);
app.use(i18n);
// app.use(ElementPlus);
app.mount("#app");
