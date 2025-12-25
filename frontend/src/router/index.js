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
      redirect: '/dashboard',
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
    {
      path: '/positions',
      name: 'positions',
      component: () => import('../views/PositionsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/strategies',
      name: 'strategies',
      component: () => import('../views/StrategyLibraryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      meta: { requiresAuth: true },
    },
    // AutoPilot routes
    {
      path: '/autopilot',
      name: 'AutoPilot',
      component: () => import('../views/autopilot/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/strategies/new',
      name: 'AutoPilotStrategyBuilder',
      component: () => import('../views/autopilot/StrategyBuilderView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/strategies/:id',
      name: 'AutoPilotStrategyDetail',
      component: () => import('../views/autopilot/StrategyDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/strategies/:id/edit',
      name: 'AutoPilotStrategyEdit',
      component: () => import('../views/autopilot/StrategyBuilderView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/settings',
      name: 'AutoPilotSettings',
      component: () => import('../views/autopilot/SettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/ai/settings',
      name: 'AISettings',
      component: () => import('../views/ai/AISettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/ai/paper-trading',
      name: 'AIPaperTrading',
      component: () => import('../views/ai/PaperTradingView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/ai/analytics',
      name: 'AIAnalytics',
      component: () => import('../views/ai/AnalyticsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/orders',
      name: 'AutoPilotOrders',
      component: () => import('../views/autopilot/OrderHistoryView.vue'),
      meta: { requiresAuth: true },
    },
    // Phase 5 routes - Redirect to main option chain
    {
      path: '/autopilot/option-chain',
      redirect: '/optionchain'
    },
    // Phase 4 routes
    {
      path: '/autopilot/templates',
      name: 'AutoPilotTemplates',
      component: () => import('../views/autopilot/TemplateLibraryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/journal',
      name: 'AutoPilotJournal',
      component: () => import('../views/autopilot/TradeJournalView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/analytics',
      name: 'AutoPilotAnalytics',
      component: () => import('../views/autopilot/AnalyticsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/reports',
      name: 'AutoPilotReports',
      component: () => import('../views/autopilot/ReportsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/backtests',
      name: 'AutoPilotBacktests',
      component: () => import('../views/autopilot/BacktestsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/autopilot/shared/:token',
      name: 'AutoPilotSharedStrategy',
      component: () => import('../views/autopilot/SharedStrategyView.vue'),
      meta: { requiresAuth: false },  // Public access for shared strategies
    },
    {
      path: '/autopilot/shared',
      name: 'AutoPilotSharedList',
      component: () => import('../views/autopilot/SharedStrategiesView.vue'),
      meta: { requiresAuth: true },
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
    next('/dashboard')
  } else {
    next()
  }
})

export default router
