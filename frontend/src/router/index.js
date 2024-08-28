import { createRouter, createWebHistory } from 'vue-router';
import Home from '../Home.vue';
import App from '../App.vue'; 
import UpdateLog from '../UpdateLog.vue'; 

const routes = [
  {
    path: '/',
    name: 'App',
    component: App
  },
  {
    path: '/log',
    name: 'UpdateLog',
    component: UpdateLog
  },
];

const router = createRouter({
  history: createWebHistory('/'),
  routes
});

export default router;