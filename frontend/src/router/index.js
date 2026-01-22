import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/lottery/join',
    name: 'LotteryJoin',
    component: () => import('@/views/lottery/index.vue'),
    meta: { title: '抽奖报名' }
  },
  {
    path: '/',
    component: () => import('@/views/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '首页', icon: 'Odometer' }
      },
      {
        path: 'birthday',
        name: 'Birthday',
        component: () => import('@/views/birthday/index.vue'),
        meta: { title: '生日管理', icon: 'Calendar' }
      },
      {
        path: 'messages',
        name: 'Messages',
        component: () => import('@/views/messages/index.vue'),
        meta: { title: '消息管理', icon: 'ChatDotRound' }
      },
      {
        path: 'config',
        name: 'Config',
        component: () => import('@/views/config/index.vue'),
        meta: { title: '系统配置', icon: 'Setting' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.afterEach((to) => {
  document.title = `${to.meta.title || '管理后台'} - Agent 智能座舱`
})

export default router
