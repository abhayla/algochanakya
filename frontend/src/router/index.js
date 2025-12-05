import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'

let authInitialized = false

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/watchlist',
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false },
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: AuthCallbackView,
      meta: { requiresAuth: false },
    },
    {
      path: '/watchlist',
      name: 'watchlist',
      component: () => import('../views/WatchlistView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/optionchain',
      name: 'optionchain',
      component: () => import('../views/OptionChainView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/strategy',
      name: 'strategy',
      component: () => import('../views/StrategyBuilderView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/strategy/:id',
      name: 'strategy-detail',
      component: () => import('../views/StrategyBuilderView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/strategy/shared/:shareCode',
      name: 'shared-strategy',
      component: () => import('../views/StrategyBuilderView.vue'),
      meta: { requiresAuth: false },  // Public access for shared strategies
    },
  ],
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Initialize auth on first navigation
  if (!authInitialized) {
    authInitialized = true
    await authStore.checkAuth()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/watchlist')
  } else {
    next()
  }
})

export default router
