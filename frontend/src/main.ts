import { createApp } from "vue";
import App from "./App.vue";
import Home from "./Home.vue"
import { createI18n } from 'vue-i18n';
import en from './languages/en';
import zh from './languages/zh';
import router from './router';
// import "~/styles/element/index.scss";

// import ElementPlus from "element-plus";
// import all element css, uncommented next line
// import "element-plus/dist/index.css";

// or use cdn, uncomment cdn link in `index.html`

import "~/styles/index.scss";
import "uno.css";

// If you want to use ElMessage, import it.
import "element-plus/theme-chalk/src/message.scss";
const messages = {
    en,
    zh
}
const i18n = createI18n({
    locale: navigator.language || 'en',
    messages,
    legacy: false
})

const app = createApp(Home);
app.use(router);
app.use(i18n);
// app.use(ElementPlus);
app.mount("#app");
