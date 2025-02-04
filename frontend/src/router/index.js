import { createRouter, createWebHashHistory } from 'vue-router';
import Home from '../Home.vue';
import UpdateLog from '../UpdateLog.vue'; 

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/log',
    name: 'UpdateLog',
    component: UpdateLog
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes
});

export default router;