import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'

import App from './App.vue'
import './styles.css'

import Employees from './views/Employees.vue'
import Attendance from './views/Attendance.vue'
import Payroll from './views/Payroll.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/attendance' },
    { path: '/employees', name: 'employees', component: Employees },
    { path: '/attendance', name: 'attendance', component: Attendance },
    { path: '/payroll', name: 'payroll', component: Payroll },
  ],
})

createApp(App).use(router).mount('#app')
