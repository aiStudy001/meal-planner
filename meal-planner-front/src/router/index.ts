import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: 'AI 맞춤 식단 플래너' },
    },
    {
      path: '/input',
      name: 'input',
      component: () => import('@/views/InputView.vue'),
      meta: { title: '정보 입력' },
    },
    {
      path: '/processing',
      name: 'processing',
      component: () => import('@/views/ProcessingView.vue'),
      meta: { title: '식단 생성 중' },
    },
  ],
})

// Update document title based on route meta
router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} | AI 맞춤 식단 플래너`
  }
  next()
})

export default router
