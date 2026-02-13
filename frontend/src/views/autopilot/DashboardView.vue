<script setup>
/**
 * AutoPilot Dashboard View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 1
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import { useWebSocket } from '@/composables/autopilot/useWebSocket'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import ShareModal from '@/components/autopilot/common/ShareModal.vue'
import MarketStatusIndicator from '@/components/autopilot/dashboard/MarketStatusIndicator.vue'
import Sparkline from '@/components/autopilot/common/Sparkline.vue'
import EnhancedStrategyCard from '@/components/autopilot/dashboard/EnhancedStrategyCard.vue'
import RiskOverviewPanel from '@/components/autopilot/dashboard/RiskOverviewPanel.vue'
import ActivityTimeline from '@/components/autopilot/dashboard/ActivityTimeline.vue'
import AIStatusCard from '@/components/autopilot/dashboard/AIStatusCard.vue'
import '@/assets/styles/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

// WebSocket connection for real-time updates
const { isConnected, connectionStatus, notifications, clearNotifications } = useWebSocket()

// Fallback polling interval (only when WS disconnected)
const refreshInterval = ref(null)

// Time tracking interval for sync status
const timeInterval = ref(null)

// Show notification panel
const showNotifications = ref(false)

// Kill switch modal
const showKillSwitchModal = ref(false)

// Share modal state
const showShareModal = ref(false)
const selectedStrategyForShare = ref(null)

// Confirmation modals
const showPauseModal = ref(false)
const showExitModal = ref(false)
const selectedStrategy = ref(null)

// Premium monitoring data
const premiumMonitoring = ref({
  totalPremium: 0,
  totalCaptured: 0,
  capturedPct: 0,
  topCapturers: [],
  atRiskStrategies: []
})

// Index prices for market status
const indexPrices = ref({
  NIFTY: { ltp: null, change: null, change_percent: null },
  BANKNIFTY: { ltp: null, change: null, change_percent: null },
  VIX: { ltp: null, change: null, change_percent: null }
})

// P&L sparkline data (last 30 data points for intraday trend)
const pnlSparklineData = computed(() => {
  // TODO: In production, fetch actual intraday P&L history from API
  // For now, generate sample data based on current P&L
  const currentPnl = store.dashboardSummary?.today_total_pnl || 0
  const points = []
  const numPoints = 30

  for (let i = 0; i < numPoints; i++) {
    // Simulate a trend leading to current P&L
    const progress = i / (numPoints - 1)
    const randomVariation = (Math.random() - 0.5) * (Math.abs(currentPnl) * 0.3)
    const value = currentPnl * progress + randomVariation
    points.push(value)
  }

  // Ensure last point matches current P&L
  points[points.length - 1] = currentPnl

  return points
})

// Broker sync tracking
const now = ref(Date.now())

// Broker sync status
const brokerSyncStatus = computed(() => {
  if (!store.dashboardSummary?.kite_connected) {
    return { text: 'Disconnected', isStale: false, showWarning: true }
  }

  const lastSyncTime = store.dashboardSummary?.last_sync_time
  if (!lastSyncTime) {
    return { text: 'Connected', isStale: false, showWarning: false }
  }

  const lastSync = new Date(lastSyncTime).getTime()
  const diffMs = now.value - lastSync
  const diffSec = Math.floor(diffMs / 1000)

  let syncText = ''
  if (diffSec < 10) syncText = 'just now'
  else if (diffSec < 60) syncText = `${diffSec}s ago`
  else {
    const diffMin = Math.floor(diffSec / 60)
    syncText = `${diffMin}m ago`
  }

  const isStale = diffSec > 30

  return {
    text: `Connected · Synced ${syncText}`,
    isStale,
    showWarning: isStale
  }
})

// Unread notifications count
const unreadCount = computed(() =>
  notifications.value.filter(n => !n.read).length
)

// Check if there are active or waiting strategies
const hasActiveOrWaitingStrategies = computed(() => {
  if (!store.dashboardSummary) return false
  return store.dashboardSummary.active_strategies > 0 || store.dashboardSummary.waiting_strategies > 0
})

// Format recent logs for ActivityTimeline component
const formattedActivities = computed(() => {
  if (!store.recentLogs || store.recentLogs.length === 0) return []

  // Map severity to event_type for ActivityTimeline
  const severityToEventType = {
    'info': 'condition_met',
    'warning': 'alert_triggered',
    'error': 'order_rejected'
  }

  return store.recentLogs.map(log => ({
    id: log.id,
    event_type: log.event_type || severityToEventType[log.severity] || 'condition_met',
    message: log.message,
    description: log.message,
    timestamp: log.created_at,
    created_at: log.created_at,
    strategy_name: log.strategy_name || null,
    underlying: log.underlying || null
  }))
})

// Fetch premium monitoring data for all active strategies
const fetchPremiumMonitoring = async () => {
  try {
    // Get active and waiting strategies
    const activeStrategies = store.strategies.filter(s =>
      ['active', 'waiting'].includes(s.status)
    )

    if (activeStrategies.length === 0) {
      premiumMonitoring.value = {
        totalPremium: 0,
        totalCaptured: 0,
        capturedPct: 0,
        topCapturers: [],
        atRiskStrategies: []
      }
      return
    }

    // Fetch decay curve for each active strategy
    const premiumPromises = activeStrategies.map(async (strategy) => {
      try {
        const response = await fetch(`/api/v1/autopilot/strategies/${strategy.id}/premium/decay-curve`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        const data = await response.json()

        if (data.success && data.data) {
          return {
            strategyId: strategy.id,
            strategyName: strategy.name,
            underlying: strategy.underlying,
            entryPremium: parseFloat(data.data.entry_premium),
            currentPremium: parseFloat(data.data.current_premium),
            capturedPct: parseFloat(data.data.premium_captured_pct),
            daysToExpiry: data.data.days_to_expiry,
            decayRate: data.data.decay_rate
          }
        }
      } catch (err) {
        console.error(`Error fetching premium for strategy ${strategy.id}:`, err)
      }
      return null
    })

    const results = (await Promise.all(premiumPromises)).filter(r => r !== null)

    // Calculate totals
    const totalCurrent = results.reduce((sum, r) => sum + r.currentPremium, 0)
    const totalEntry = results.reduce((sum, r) => sum + r.entryPremium, 0)
    const totalCaptured = totalEntry - totalCurrent
    const capturedPct = totalEntry > 0 ? (totalCaptured / totalEntry) * 100 : 0

    // Top capturers (sorted by captured %)
    const topCapturers = results
      .sort((a, b) => b.capturedPct - a.capturedPct)
      .slice(0, 5)

    // At risk strategies (decay rate > 1.5x or near SL)
    const atRiskStrategies = results
      .filter(r => r.decayRate > 1.5 || r.capturedPct < 10)
      .slice(0, 5)

    premiumMonitoring.value = {
      totalPremium: totalCurrent,
      totalCaptured,
      capturedPct,
      topCapturers,
      atRiskStrategies
    }
  } catch (error) {
    console.error('Error fetching premium monitoring data:', error)
  }
}

onMounted(async () => {
  await store.fetchDashboardSummary()
  await store.fetchStrategies()
  await store.fetchRecentLogs()
  await fetchPremiumMonitoring()

  // Update time for broker sync status (every 5 seconds)
  timeInterval.value = setInterval(() => {
    now.value = Date.now()
  }, 5000)

  // Only use polling as fallback when WebSocket is disconnected
  refreshInterval.value = setInterval(() => {
    if (!isConnected.value) {
      store.fetchDashboardSummary()
      fetchPremiumMonitoring()
    }
  }, 10000) // Slower polling as fallback
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  if (timeInterval.value) {
    clearInterval(timeInterval.value)
  }
})

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
  // Mark all as read when opening
  if (showNotifications.value) {
    notifications.value.forEach(n => n.read = true)
  }
}

const navigateToBuilder = () => {
  router.push('/autopilot/strategies/new')
}

const navigateToStrategy = (id) => {
  router.push(`/autopilot/strategies/${id}`)
}

const navigateToSettings = () => {
  router.push('/autopilot/settings')
}

const handlePause = (strategyOrId) => {
  const strategyId = typeof strategyOrId === 'object' ? strategyOrId.id : strategyOrId
  const strategy = store.strategies.find(s => s.id === strategyId)
  selectedStrategy.value = strategy
  showPauseModal.value = true
}

const confirmPause = async () => {
  if (selectedStrategy.value) {
    await store.pauseStrategy(selectedStrategy.value.id)
    showPauseModal.value = false
    selectedStrategy.value = null
  }
}

const handleResume = async (strategyOrId) => {
  const strategyId = typeof strategyOrId === 'object' ? strategyOrId.id : strategyOrId
  await store.resumeStrategy(strategyId)
}

const handleExit = (strategyOrId) => {
  const strategyId = typeof strategyOrId === 'object' ? strategyOrId.id : strategyOrId
  const strategy = store.strategies.find(s => s.id === strategyId)
  selectedStrategy.value = strategy
  showExitModal.value = true
}

const confirmExit = async () => {
  if (selectedStrategy.value) {
    await store.exitStrategy(selectedStrategy.value.id)
    showExitModal.value = false
    selectedStrategy.value = null
  }
}

const handleShare = (strategy) => {
  selectedStrategyForShare.value = strategy
  showShareModal.value = true
}

const closeShareModal = () => {
  showShareModal.value = false
  selectedStrategyForShare.value = null
}

const onStrategyShared = () => {
  // Refresh strategies to update share status
  store.fetchStrategies()
}

const onStrategyUnshared = () => {
  // Refresh strategies to update share status
  store.fetchStrategies()
}

const refreshDashboard = async () => {
  await store.fetchDashboardSummary()
  await store.fetchStrategies()
  await fetchPremiumMonitoring()
}

const clearFilters = () => {
  store.filters.status = null
  store.filters.underlying = null
  store.fetchStrategies()
}

const confirmKillSwitch = async () => {
  await store.activateKillSwitch()
  showKillSwitchModal.value = false
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'status-badge status-active',
    waiting: 'status-badge status-waiting',
    pending: 'status-badge status-pending',
    paused: 'status-badge status-paused',
    draft: 'status-badge status-draft',
    completed: 'status-badge status-completed',
    error: 'status-badge status-error'
  }
  return classes[status] || 'status-badge status-paused'
}
</script>

<template>
  <KiteLayout>
  <div class="autopilot-dashboard" data-testid="autopilot-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div>
        <h1 class="dashboard-title">AutoPilot Dashboard</h1>
        <p class="dashboard-subtitle">Automated options trading strategies</p>
      </div>
      <div class="dashboard-actions">
        <!-- Connection Status -->
        <div
          class="connection-status"
          :class="{
            'connection-connected': connectionStatus === 'connected',
            'connection-reconnecting': connectionStatus === 'reconnecting',
            'connection-disconnected': connectionStatus === 'disconnected'
          }"
          data-testid="autopilot-connection-status"
          :data-status="connectionStatus"
        >
          <span
            class="connection-dot"
            :class="{
              'dot-connected': connectionStatus === 'connected',
              'dot-reconnecting': connectionStatus === 'reconnecting',
              'dot-disconnected': connectionStatus === 'disconnected'
            }"
          ></span>
          <span>{{ connectionStatus === 'connected' ? 'Live' : connectionStatus === 'reconnecting' ? 'Reconnecting...' : 'Disconnected' }}</span>
        </div>

        <!-- Notifications -->
        <div class="notifications-wrapper">
          <button
            @click="toggleNotifications"
            class="icon-btn"
            data-testid="autopilot-notifications-button"
          >
            <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
            </svg>
            <span v-if="unreadCount > 0" class="notification-badge">
              {{ unreadCount > 9 ? '9+' : unreadCount }}
            </span>
          </button>

          <!-- Notifications Panel -->
          <div
            v-if="showNotifications"
            class="notifications-panel"
            data-testid="autopilot-notifications-panel"
          >
            <div class="notifications-header">
              <span class="notifications-title">Notifications</span>
              <button @click="clearNotifications" class="link-btn">
                Clear all
              </button>
            </div>
            <div class="notifications-list">
              <div v-if="notifications.length === 0" class="notifications-empty">
                No notifications
              </div>
              <div
                v-for="(notification, index) in notifications.slice(0, 10)"
                :key="notification.id"
                class="notification-item"
                :class="{ 'notification-unread': !notification.read }"
              >
                <div class="notification-content">
                  <span
                    class="notification-dot"
                    :class="{
                      'dot-success': notification.type === 'success',
                      'dot-error': notification.type === 'error',
                      'dot-warning': notification.type === 'warning',
                      'dot-info': notification.type === 'info'
                    }"
                  ></span>
                  <div class="notification-text">
                    <p class="notification-title">{{ notification.title }}</p>
                    <p class="notification-message">{{ notification.message }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Kill Switch Button -->
        <button
          @click="showKillSwitchModal = true"
          :disabled="!hasActiveOrWaitingStrategies"
          data-testid="autopilot-kill-switch-btn"
          class="strategy-btn strategy-btn-danger"
        >
          Kill Switch
        </button>

        <!-- Refresh Button -->
        <button
          @click="refreshDashboard"
          data-testid="autopilot-refresh-btn"
          class="icon-btn"
        >
          <svg class="icon-svg-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
        </button>

        <button
          @click="navigateToSettings"
          data-testid="autopilot-settings-btn"
          class="strategy-btn strategy-btn-outline"
        >
          Settings
        </button>
        <button
          @click="$router.push('/autopilot/option-chain')"
          data-testid="autopilot-nav-optionchain"
          class="strategy-btn strategy-btn-outline"
        >
          Option Chain
        </button>
        <button
          @click="$router.push('/autopilot/orders')"
          data-testid="autopilot-nav-orders"
          class="strategy-btn strategy-btn-outline"
        >
          Order History
        </button>
        <button
          @click="navigateToBuilder"
          :disabled="!store.canCreateStrategy"
          data-testid="autopilot-create-strategy-btn"
          class="strategy-btn strategy-btn-primary"
        >
          + New Strategy
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="store.loading && !store.dashboardSummary" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading dashboard...</p>
    </div>

    <!-- Dashboard Content -->
    <template v-else-if="store.dashboardSummary">
      <!-- Market Status Indicator -->
      <MarketStatusIndicator :index-prices="indexPrices" />

      <!-- Summary Cards -->
      <div class="summary-cards" data-testid="autopilot-summary-section">
        <!-- Today's P&L -->
        <div class="summary-card" data-testid="autopilot-today-pnl-card">
          <p class="summary-label">Today's P&L</p>
          <div class="summary-value-with-trend">
            <p :class="['summary-value', getPnLClass(store.dashboardSummary.today_total_pnl)]" data-testid="autopilot-today-pnl-value">
              {{ formatCurrency(store.dashboardSummary.today_total_pnl) }}
              <!-- Trend Arrow -->
              <span
                v-if="store.dashboardSummary.today_total_pnl !== 0"
                class="trend-arrow"
                :class="store.dashboardSummary.today_total_pnl > 0 ? 'trend-up' : 'trend-down'"
                data-testid="autopilot-pnl-trend-arrow"
              >
                {{ store.dashboardSummary.today_total_pnl > 0 ? '↑' : '↓' }}
              </span>
            </p>
          </div>
          <!-- Sparkline Chart -->
          <div class="pnl-sparkline" data-testid="autopilot-pnl-sparkline">
            <Sparkline
              :data="pnlSparklineData"
              :width="180"
              :height="40"
              :stroke-width="2"
            />
          </div>
        </div>

        <!-- Active Strategies -->
        <div class="summary-card" data-testid="autopilot-active-strategies-card">
          <p class="summary-label">
            Active Strategies
            <span class="tooltip">
              <span class="tooltip-icon">ℹ️</span>
              <span class="tooltip-text">Active + Waiting / Maximum Allowed</span>
            </span>
          </p>
          <p class="summary-value">
            <span data-testid="autopilot-active-count">{{ store.dashboardSummary.active_strategies }}</span>
            <span class="summary-text"> Active</span>
            <span class="summary-separator"> / </span>
            <span data-testid="autopilot-max-count">{{ store.dashboardSummary.risk_metrics.max_active_strategies }}</span>
            <span class="summary-text"> Max</span>
          </p>
          <p v-if="store.dashboardSummary.waiting_strategies > 0" class="summary-subtitle">
            <span data-testid="autopilot-waiting-count">{{ store.dashboardSummary.waiting_strategies }}</span> waiting
          </p>
        </div>

        <!-- Daily Loss Limit / Risk Status -->
        <div class="summary-card" data-testid="autopilot-risk-status-card">
          <p class="summary-label">Daily Loss Used</p>
          <p class="summary-value">
            {{ store.dashboardSummary.risk_metrics.daily_loss_pct.toFixed(0) }}%
          </p>
          <span
            data-testid="autopilot-risk-status-badge"
            class="risk-badge"
            :class="{
              'risk-safe': store.dashboardSummary.risk_metrics.status === 'safe',
              'risk-warning': store.dashboardSummary.risk_metrics.status === 'warning',
              'risk-critical': store.dashboardSummary.risk_metrics.status === 'critical'
            }"
          >
            {{ store.dashboardSummary.risk_metrics.status }}
          </span>
          <div class="progress-bar-bg">
            <div
              class="progress-bar-fill"
              :class="{
                'fill-safe': store.dashboardSummary.risk_metrics.status === 'safe',
                'fill-warning': store.dashboardSummary.risk_metrics.status === 'warning',
                'fill-critical': store.dashboardSummary.risk_metrics.status === 'critical'
              }"
              :style="{ width: Math.min(store.dashboardSummary.risk_metrics.daily_loss_pct, 100) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Capital Used -->
        <div class="summary-card" data-testid="autopilot-capital-used-card">
          <p class="summary-label">Capital Used</p>
          <p class="summary-value" data-testid="autopilot-capital-used-value">
            {{ formatCurrency(store.dashboardSummary.capital_deployed || 0) }}
            <span class="summary-secondary"> / {{ formatCurrency(store.dashboardSummary.available_margin || 0) }}</span>
          </p>
          <!-- Capital Usage Progress Bar -->
          <div class="capital-progress-container" data-testid="autopilot-capital-progress-bar">
            <div class="progress-bar-bg">
              <div
                class="progress-bar-fill fill-safe"
                :style="{
                  width: Math.min(((store.dashboardSummary.capital_deployed || 0) / (store.dashboardSummary.available_margin || 1)) * 100, 100) + '%'
                }"
              ></div>
            </div>
            <p class="capital-usage-pct" data-testid="autopilot-capital-percentage">
              {{ (((store.dashboardSummary.capital_deployed || 0) / (store.dashboardSummary.available_margin || 1)) * 100).toFixed(1) }}% utilized
            </p>
          </div>
          <!-- Broker Status -->
          <div
            class="broker-status-enhanced"
            data-testid="autopilot-broker-status"
            :data-connected="store.dashboardSummary.kite_connected"
            :class="{ 'status-stale': brokerSyncStatus.isStale }"
          >
            <div class="broker-status-content">
              <span
                class="broker-dot"
                :class="store.dashboardSummary.kite_connected ? 'dot-connected' : 'dot-disconnected'"
              ></span>
              <div class="broker-status-text">
                <span class="broker-label">Broker Connection</span>
                <span
                  class="broker-sync-text"
                  :class="{ 'text-warning': brokerSyncStatus.showWarning }"
                  data-testid="autopilot-broker-sync-time"
                >
                  {{ brokerSyncStatus.text }}
                </span>
              </div>
            </div>
            <span
              v-if="brokerSyncStatus.showWarning"
              class="warning-icon"
              title="Sync is stale"
              data-testid="autopilot-broker-stale-warning"
            >⚠️</span>
          </div>
        </div>

        <!-- AI Week 3: AI Status Card -->
        <AIStatusCard />
      </div>

      <!-- Risk Overview Panel -->
      <div class="risk-overview-section" data-testid="autopilot-risk-overview">
        <RiskOverviewPanel :summary="store.dashboardSummary" />
      </div>

      <!-- Premium Monitoring Widgets -->
      <div
        v-if="premiumMonitoring.topCapturers.length > 0"
        class="premium-monitoring-section"
        data-testid="autopilot-premium-monitoring"
      >
        <h2 class="section-title premium-section-title">Premium Monitoring</h2>

        <div class="premium-widgets">
          <!-- Combined Premium Tracker -->
          <div class="premium-widget premium-widget-large" data-testid="autopilot-premium-tracker">
            <div class="premium-widget-header">
              <h3 class="premium-widget-title">Portfolio Premium</h3>
              <span class="premium-widget-badge">{{ premiumMonitoring.topCapturers.length }} Active</span>
            </div>
            <div class="premium-widget-content">
              <div class="premium-stat-large">
                <span class="premium-stat-label">Current Premium</span>
                <span class="premium-stat-value">₹{{ premiumMonitoring.totalPremium.toFixed(2) }}</span>
              </div>
              <div class="premium-stats-row">
                <div class="premium-stat-small">
                  <span class="premium-stat-label">Captured</span>
                  <span class="premium-stat-value success">₹{{ premiumMonitoring.totalCaptured.toFixed(2) }}</span>
                </div>
                <div class="premium-stat-small">
                  <span class="premium-stat-label">Captured %</span>
                  <span class="premium-stat-value success">{{ premiumMonitoring.capturedPct.toFixed(1) }}%</span>
                </div>
              </div>
              <div class="premium-progress-bar">
                <div
                  class="premium-progress-fill"
                  :style="{ width: Math.min(premiumMonitoring.capturedPct, 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>

          <!-- Top Premium Capturers -->
          <div class="premium-widget" data-testid="autopilot-top-capturers">
            <div class="premium-widget-header">
              <h3 class="premium-widget-title">Top Capturers</h3>
              <svg class="premium-widget-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              </svg>
            </div>
            <div class="premium-widget-content">
              <div class="premium-list">
                <div
                  v-for="(capturer, index) in premiumMonitoring.topCapturers.slice(0, 5)"
                  :key="capturer.strategyId"
                  class="premium-list-item"
                  :data-testid="`autopilot-top-capturer-${index}`"
                >
                  <div class="premium-list-left">
                    <span class="premium-rank">{{ index + 1 }}</span>
                    <div class="premium-list-info">
                      <span class="premium-list-name">{{ capturer.strategyName }}</span>
                      <span class="premium-list-meta">{{ capturer.underlying }}</span>
                    </div>
                  </div>
                  <div class="premium-list-right">
                    <span class="premium-list-value success">{{ capturer.capturedPct.toFixed(1) }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Premium at Risk -->
          <div class="premium-widget" data-testid="autopilot-premium-at-risk">
            <div class="premium-widget-header">
              <h3 class="premium-widget-title">At Risk</h3>
              <svg class="premium-widget-icon premium-icon-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
              </svg>
            </div>
            <div class="premium-widget-content">
              <div v-if="premiumMonitoring.atRiskStrategies.length === 0" class="premium-empty">
                <span class="premium-empty-icon">✓</span>
                <span class="premium-empty-text">All strategies performing well</span>
              </div>
              <div v-else class="premium-list">
                <div
                  v-for="(risk, index) in premiumMonitoring.atRiskStrategies.slice(0, 5)"
                  :key="risk.strategyId"
                  class="premium-list-item"
                  :data-testid="`autopilot-at-risk-${index}`"
                >
                  <div class="premium-list-left">
                    <span class="premium-dot premium-dot-warning"></span>
                    <div class="premium-list-info">
                      <span class="premium-list-name">{{ risk.strategyName }}</span>
                      <span class="premium-list-meta">{{ risk.underlying }} • {{ risk.daysToExpiry }}d to expiry</span>
                    </div>
                  </div>
                  <div class="premium-list-right">
                    <span class="premium-list-value warning">{{ risk.decayRate.toFixed(1) }}x decay</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Strategies List -->
      <div class="strategy-list-card" data-testid="autopilot-strategy-list">
        <div class="strategy-list-header">
          <h2 class="section-title">Strategies</h2>
          <div class="filter-group">
            <select
              v-model="store.filters.status"
              @change="store.fetchStrategies()"
              class="strategy-select compact"
              data-testid="autopilot-status-filter"
            >
              <option :value="null">All Status</option>
              <option value="draft">Draft</option>
              <option value="waiting">Waiting</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </select>
            <select
              v-model="store.filters.underlying"
              @change="store.fetchStrategies()"
              class="strategy-select compact"
              data-testid="autopilot-underlying-filter"
            >
              <option :value="null">All Underlying</option>
              <option value="NIFTY">NIFTY</option>
              <option value="BANKNIFTY">BANKNIFTY</option>
              <option value="FINNIFTY">FINNIFTY</option>
              <option value="SENSEX">SENSEX</option>
            </select>
            <button
              v-if="store.filters.status || store.filters.underlying"
              @click="clearFilters"
              data-testid="autopilot-clear-filters-btn"
              class="link-btn"
            >
              Clear
            </button>
          </div>
        </div>

        <!-- Empty State with Quick Deploy Templates -->
        <div v-if="store.strategies.length === 0" class="quick-start-section" data-testid="autopilot-empty-state">
          <div class="quick-start-header">
            <h3 class="quick-start-title">Quick Start</h3>
            <p class="quick-start-subtitle">Deploy a popular options strategy with one click, or build your own from scratch</p>
          </div>

          <!-- Popular Strategy Templates -->
          <div class="template-buttons">
            <button
              @click="$router.push('/autopilot/templates?strategy=short_straddle')"
              class="template-btn"
              data-testid="autopilot-template-short-straddle"
            >
              <span class="template-icon">📊</span>
              <div class="template-info">
                <span class="template-name">Short Straddle</span>
                <span class="template-desc">Sell ATM CE + PE</span>
              </div>
            </button>

            <button
              @click="$router.push('/autopilot/templates?strategy=iron_condor')"
              class="template-btn"
              data-testid="autopilot-template-iron-condor"
            >
              <span class="template-icon">🦅</span>
              <div class="template-info">
                <span class="template-name">Iron Condor</span>
                <span class="template-desc">Sell narrow range</span>
              </div>
            </button>

            <button
              @click="$router.push('/autopilot/templates?strategy=bull_call_spread')"
              class="template-btn"
              data-testid="autopilot-template-bull-call-spread"
            >
              <span class="template-icon">📈</span>
              <div class="template-info">
                <span class="template-name">Bull Call Spread</span>
                <span class="template-desc">Buy ITM, sell OTM CE</span>
              </div>
            </button>

            <button
              @click="$router.push('/autopilot/templates?strategy=short_strangle')"
              class="template-btn"
              data-testid="autopilot-template-short-strangle"
            >
              <span class="template-icon">🎯</span>
              <div class="template-info">
                <span class="template-name">Short Strangle</span>
                <span class="template-desc">Sell OTM CE + PE</span>
              </div>
            </button>
          </div>

          <!-- Divider -->
          <div class="quick-start-divider">
            <span class="divider-text">OR</span>
          </div>

          <!-- Custom Builder Button -->
          <button
            @click="navigateToBuilder"
            data-testid="autopilot-empty-create-btn"
            class="strategy-btn strategy-btn-primary strategy-btn-large"
          >
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
            </svg>
            Build Custom Strategy
          </button>
        </div>

        <div v-else class="strategy-grid">
          <EnhancedStrategyCard
            v-for="strategy in store.strategies"
            :key="strategy.id"
            :strategy="strategy"
            :data-testid="`autopilot-strategy-card-${strategy.id}`"
            @pause="handlePause"
            @resume="handleResume"
            @exit="handleExit"
          />
        </div>
      </div>

      <!-- Activity Timeline -->
      <div class="activity-timeline-section" data-testid="autopilot-activity-feed">
        <ActivityTimeline
          :activities="formattedActivities"
          :max-items="10"
          :is-realtime="isConnected"
          :group-by-strategy="store.strategies.length > 1"
        />
      </div>
    </template>

    <!-- Kill Switch Modal -->
    <div
      v-if="showKillSwitchModal"
      class="modal-overlay"
      data-testid="autopilot-kill-switch-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title modal-title-danger">Activate Kill Switch</h3>
        <p class="modal-text">
          This will immediately pause all active and waiting strategies. Are you sure you want to proceed?
        </p>
        <div class="modal-actions">
          <button
            @click="showKillSwitchModal = false"
            data-testid="autopilot-kill-switch-cancel"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="confirmKillSwitch"
            data-testid="autopilot-kill-switch-confirm"
            class="strategy-btn strategy-btn-danger"
          >
            Confirm Kill Switch
          </button>
        </div>
      </div>
    </div>

    <!-- Pause Strategy Modal -->
    <div
      v-if="showPauseModal"
      class="modal-overlay"
      data-testid="autopilot-pause-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title">Pause Strategy</h3>
        <p class="modal-text">
          Are you sure you want to pause "{{ selectedStrategy?.name || 'this strategy' }}"?
          The strategy will stop monitoring conditions and placing new orders.
        </p>
        <div class="modal-actions">
          <button
            @click="showPauseModal = false"
            data-testid="autopilot-pause-cancel"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="confirmPause"
            data-testid="autopilot-pause-confirm"
            class="strategy-btn strategy-btn-primary"
          >
            Pause Strategy
          </button>
        </div>
      </div>
    </div>

    <!-- Exit Strategy Modal -->
    <div
      v-if="showExitModal"
      class="modal-overlay"
      data-testid="autopilot-exit-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title modal-title-danger">Exit Strategy</h3>
        <p class="modal-text">
          Are you sure you want to exit "{{ selectedStrategy?.name || 'this strategy' }}"?
          This will close all open positions at current market prices.
        </p>
        <div class="modal-actions">
          <button
            @click="showExitModal = false"
            data-testid="autopilot-exit-cancel"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="confirmExit"
            data-testid="autopilot-exit-confirm"
            class="strategy-btn strategy-btn-danger"
          >
            Exit Strategy
          </button>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="store.error" class="error-banner" data-testid="autopilot-error">
      <p class="error-text">{{ store.error }}</p>
      <button @click="store.clearError" class="error-dismiss">Dismiss</button>
    </div>

    <!-- Share Modal -->
    <ShareModal
      :show="showShareModal"
      :strategy-id="selectedStrategyForShare?.id"
      :strategy-name="selectedStrategyForShare?.name"
      :is-shared="!!selectedStrategyForShare?.share_token"
      :existing-token="selectedStrategyForShare?.share_token"
      @close="closeShareModal"
      @shared="onStrategyShared"
      @unshared="onStrategyUnshared"
    />
  </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.autopilot-dashboard {
  padding: 24px;
}

/* ===== Header ===== */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.dashboard-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.dashboard-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.dashboard-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== Connection Status ===== */
.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 9999px;
  font-size: 0.875rem;
}

.connection-connected {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green, #388e3c);
}

.connection-reconnecting {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange, #f57c00);
}

.connection-disconnected {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red, #d32f2f);
}

.connection-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-connected {
  background: var(--kite-green);
  animation: pulse 2s infinite;
}

.dot-reconnecting {
  background: var(--kite-orange);
  animation: pulse 2s infinite;
}

.dot-disconnected {
  background: var(--kite-red);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== Notifications ===== */
.notifications-wrapper {
  position: relative;
}

.icon-btn {
  position: relative;
  padding: 8px;
  color: var(--kite-text-secondary);
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
}

.icon-btn:hover {
  color: var(--kite-text-primary);
  background: var(--kite-table-hover);
}

.icon-svg {
  width: 24px;
  height: 24px;
}

.icon-svg-sm {
  width: 20px;
  height: 20px;
}

.notification-badge {
  position: absolute;
  top: 0;
  right: 0;
  width: 20px;
  height: 20px;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--kite-red);
  color: white;
  border-radius: 50%;
}

.notifications-panel {
  position: absolute;
  right: 0;
  margin-top: 8px;
  width: 320px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid var(--kite-border);
  z-index: 50;
}

.notifications-header {
  padding: 12px;
  border-bottom: 1px solid var(--kite-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notifications-title {
  font-weight: 500;
}

.notifications-list {
  max-height: 320px;
  overflow-y: auto;
}

.notifications-empty {
  padding: 16px;
  text-align: center;
  color: var(--kite-text-secondary);
}

.notification-item {
  padding: 12px;
  border-bottom: 1px solid var(--kite-border-light);
}

.notification-item:hover {
  background: var(--kite-table-hover);
}

.notification-unread {
  background: var(--kite-blue-light, #e3f2fd);
}

.notification-content {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.notification-dot {
  width: 8px;
  height: 8px;
  margin-top: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-success { background: var(--kite-green); }
.dot-error { background: var(--kite-red); }
.dot-warning { background: var(--kite-orange); }
.dot-info { background: var(--kite-blue); }

.notification-text {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.notification-message {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.link-btn {
  font-size: 0.875rem;
  color: var(--kite-blue);
  background: none;
  border: none;
  cursor: pointer;
}

.link-btn:hover {
  color: var(--kite-blue-dark, #1565c0);
}

/* ===== Loading State ===== */
.loading-state {
  text-align: center;
  padding: 48px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 2px solid var(--kite-border);
  border-top-color: var(--kite-blue);
  border-radius: 50%;
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: var(--kite-text-secondary);
}

/* ===== Summary Cards ===== */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(4, 1fr);
  }
}

.summary-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.summary-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.summary-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.summary-text {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--kite-text-secondary);
}

.summary-subtitle {
  font-size: 0.75rem;
  color: var(--kite-text-muted);
  margin-top: 4px;
}

.summary-separator {
  color: var(--kite-text-muted);
  margin: 0 4px;
}

.summary-secondary {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--kite-text-secondary);
}

/* Tooltip */
.tooltip {
  position: relative;
  display: inline-flex;
  cursor: help;
}

.tooltip-icon {
  font-size: 12px;
  opacity: 0.6;
}

.tooltip:hover .tooltip-icon {
  opacity: 1;
}

.tooltip-text {
  visibility: hidden;
  position: absolute;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2937;
  color: white;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
  z-index: 1000;
  opacity: 0;
  transition: opacity 0.2s;
}

.tooltip-text::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -4px;
  border-width: 4px;
  border-style: solid;
  border-color: #1f2937 transparent transparent transparent;
}

.tooltip:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

/* ===== P&L Colors ===== */
.pnl-profit {
  color: var(--kite-green) !important;
}

.pnl-loss {
  color: var(--kite-red) !important;
}

.pnl-neutral {
  color: var(--kite-text-secondary) !important;
}

/* ===== P&L Sparkline & Trend Arrow ===== */
.summary-value-with-trend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trend-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  margin-left: 8px;
  font-weight: 700;
}

.trend-up {
  color: var(--kite-green);
}

.trend-down {
  color: var(--kite-red);
}

.pnl-sparkline {
  display: flex;
  justify-content: center;
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--kite-border-light, #f0f0f0);
}

/* ===== Risk Badge & Progress ===== */
.risk-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
}

.risk-safe {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.risk-warning {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.risk-critical {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.progress-bar-bg {
  margin-top: 8px;
  width: 100%;
  height: 8px;
  background: var(--kite-border-light);
  border-radius: 4px;
}

.progress-bar-fill {
  height: 8px;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.fill-safe { background: var(--kite-green); }
.fill-warning { background: var(--kite-orange); }
.fill-critical { background: var(--kite-red); }

/* ===== Capital Progress ===== */
.capital-progress-container {
  margin-top: 8px;
}

.capital-usage-pct {
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  text-align: center;
}

/* ===== Broker Status ===== */
.broker-status {
  display: flex;
  align-items: center;
  margin-top: 8px;
}

.broker-status-enhanced {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 10px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 6px;
  border: 1px solid var(--kite-border-light, #e5e7eb);
}

.broker-status-enhanced.status-stale {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-color: var(--kite-orange, #f57c00);
}

.broker-status-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.broker-status-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.broker-label {
  font-size: 0.625rem;
  font-weight: 600;
  color: var(--kite-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.broker-sync-text {
  font-size: 0.813rem;
  font-weight: 600;
  color: var(--kite-green);
}

.broker-sync-text.text-warning {
  color: var(--kite-red);
}

.broker-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.warning-icon {
  font-size: 1.125rem;
}

.broker-text {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

/* ===== Strategy List ===== */
.strategy-list-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.strategy-list-header {
  padding: 16px;
  border-bottom: 1px solid var(--kite-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.filter-group {
  display: flex;
  gap: 8px;
}

/* ===== Quick Start / Empty State ===== */
.quick-start-section {
  padding: 40px 32px;
  text-align: center;
}

.quick-start-header {
  margin-bottom: 32px;
}

.quick-start-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
  margin-bottom: 8px;
}

.quick-start-subtitle {
  font-size: 0.938rem;
  color: var(--kite-text-secondary);
  line-height: 1.5;
}

.template-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.template-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border: 2px solid var(--kite-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.template-btn:hover {
  border-color: var(--kite-blue);
  background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.template-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.template-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.template-name {
  font-size: 0.938rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.template-desc {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.quick-start-divider {
  position: relative;
  margin: 24px 0;
  height: 1px;
  background: var(--kite-border);
}

.divider-text {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: white;
  padding: 0 12px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--kite-text-muted);
}

.strategy-btn-large {
  padding: 14px 32px;
  font-size: 1rem;
  font-weight: 600;
}

.btn-icon {
  width: 20px;
  height: 20px;
  margin-right: 8px;
}

.empty-state {
  padding: 32px;
  text-align: center;
}

.empty-state-text {
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

/* ===== Strategy Grid ===== */
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
  padding: 16px;
}

@media (min-width: 768px) {
  .strategy-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1200px) {
  .strategy-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ===== Status Badge ===== */
.status-badge {
  padding: 2px 8px;
  font-size: 0.75rem;
  border-radius: 9999px;
}

.status-active {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.status-waiting {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.status-pending {
  background: #fff8e1;
  color: #f57f17;
}

.status-paused {
  background: var(--kite-border-light);
  color: var(--kite-text-secondary);
}

.status-draft {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.status-completed {
  background: #f3e5f5;
  color: #7b1fa2;
}

.status-error {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

/* ===== Risk Overview Section ===== */
.risk-overview-section {
  margin-bottom: 24px;
}

/* ===== Activity Timeline Section ===== */
.activity-timeline-section {
  margin-top: 24px;
}

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  padding: 24px;
  max-width: 448px;
  width: calc(100% - 32px);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 16px;
}

.modal-title-danger {
  color: var(--kite-red);
}

.modal-text {
  color: var(--kite-text-secondary);
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Error Banner ===== */
.error-banner {
  margin-top: 16px;
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red-border, #ffcdd2);
  border-radius: 4px;
  padding: 16px;
}

.error-text {
  color: var(--kite-red);
}

.error-dismiss {
  color: var(--kite-red);
  background: none;
  border: none;
  text-decoration: underline;
  margin-top: 8px;
  cursor: pointer;
}

/* ===== Button Styles ===== */
.strategy-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.strategy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.strategy-btn-primary {
  background: var(--kite-blue);
  color: white;
  border-color: var(--kite-blue);
}

.strategy-btn-primary:hover:not(:disabled) {
  background: var(--kite-blue-dark, #1565c0);
}

.strategy-btn-danger {
  background: var(--kite-red);
  color: white;
  border-color: var(--kite-red);
}

.strategy-btn-danger:hover:not(:disabled) {
  background: var(--kite-red-dark, #c62828);
}

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

/* ===== Select Styles ===== */
.strategy-select {
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
  cursor: pointer;
}

.strategy-select.compact {
  padding: 6px 10px;
  font-size: 0.75rem;
}

/* ===== Premium Monitoring Widgets ===== */
.premium-monitoring-section {
  margin-bottom: 24px;
}

.premium-section-title {
  margin-bottom: 16px;
}

.premium-widgets {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .premium-widgets {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1200px) {
  .premium-widgets {
    grid-template-columns: repeat(3, 1fr);
  }
}

.premium-widget {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid var(--kite-border);
  overflow: hidden;
}

.premium-widget-large {
  grid-column: span 1;
}

@media (min-width: 768px) {
  .premium-widget-large {
    grid-column: span 2;
  }
}

@media (min-width: 1200px) {
  .premium-widget-large {
    grid-column: span 1;
  }
}

.premium-widget-header {
  padding: 16px;
  border-bottom: 1px solid var(--kite-border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.premium-widget-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin: 0;
}

.premium-widget-badge {
  padding: 4px 8px;
  font-size: 0.75rem;
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
  border-radius: 9999px;
}

.premium-widget-icon {
  width: 20px;
  height: 20px;
  color: var(--kite-blue);
}

.premium-icon-warning {
  color: var(--kite-orange);
}

.premium-widget-content {
  padding: 16px;
}

/* ===== Premium Stats ===== */
.premium-stat-large {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.premium-stat-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.premium-stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.premium-stat-value.success {
  color: var(--kite-green);
}

.premium-stat-value.warning {
  color: var(--kite-orange);
}

.premium-stats-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.premium-stat-small {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.premium-stat-small .premium-stat-value {
  font-size: 1.25rem;
}

/* ===== Premium Progress Bar ===== */
.premium-progress-bar {
  width: 100%;
  height: 8px;
  background: var(--kite-border-light);
  border-radius: 4px;
  overflow: hidden;
}

.premium-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--kite-green), var(--kite-blue));
  transition: width 0.3s ease;
  border-radius: 4px;
}

/* ===== Premium List ===== */
.premium-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.premium-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--kite-table-hover);
  border-radius: 6px;
  transition: background 0.15s ease;
}

.premium-list-item:hover {
  background: #f0f0f0;
}

.premium-list-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.premium-rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.premium-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.premium-dot-warning {
  background: var(--kite-orange);
  animation: pulse 2s infinite;
}

.premium-list-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.premium-list-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.premium-list-meta {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.premium-list-right {
  flex-shrink: 0;
}

.premium-list-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.premium-list-value.success {
  color: var(--kite-green);
}

.premium-list-value.warning {
  color: var(--kite-orange);
}

/* ===== Premium Empty State ===== */
.premium-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  gap: 8px;
}

.premium-empty-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
  border-radius: 50%;
  font-size: 24px;
}

.premium-empty-text {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}
</style>
