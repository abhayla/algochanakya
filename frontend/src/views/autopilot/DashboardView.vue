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
import '@/assets/css/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

// WebSocket connection for real-time updates
const { isConnected, connectionStatus, notifications, clearNotifications } = useWebSocket()

// Fallback polling interval (only when WS disconnected)
const refreshInterval = ref(null)

// Show notification panel
const showNotifications = ref(false)

// Kill switch modal
const showKillSwitchModal = ref(false)

// Share modal state
const showShareModal = ref(false)
const selectedStrategyForShare = ref(null)

// Unread notifications count
const unreadCount = computed(() =>
  notifications.value.filter(n => !n.read).length
)

// Check if there are active or waiting strategies
const hasActiveOrWaitingStrategies = computed(() => {
  if (!store.dashboardSummary) return false
  return store.dashboardSummary.active_strategies > 0 || store.dashboardSummary.waiting_strategies > 0
})

onMounted(async () => {
  await store.fetchDashboardSummary()
  await store.fetchStrategies()
  await store.fetchRecentLogs()

  // Only use polling as fallback when WebSocket is disconnected
  refreshInterval.value = setInterval(() => {
    if (!isConnected.value) {
      store.fetchDashboardSummary()
    }
  }, 10000) // Slower polling as fallback
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
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

const handlePause = async (strategy) => {
  if (confirm(`Pause strategy "${strategy.name}"?`)) {
    await store.pauseStrategy(strategy.id)
  }
}

const handleResume = async (strategy) => {
  await store.resumeStrategy(strategy.id)
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
      <!-- Summary Cards -->
      <div class="summary-cards" data-testid="autopilot-summary-section">
        <!-- Today's P&L -->
        <div class="summary-card" data-testid="autopilot-today-pnl-card">
          <p class="summary-label">Today's P&L</p>
          <p :class="['summary-value', getPnLClass(store.dashboardSummary.today_total_pnl)]" data-testid="autopilot-today-pnl-value">
            {{ formatCurrency(store.dashboardSummary.today_total_pnl) }}
          </p>
        </div>

        <!-- Active Strategies -->
        <div class="summary-card" data-testid="autopilot-active-strategies-card">
          <p class="summary-label">Active Strategies</p>
          <p class="summary-value">
            <span data-testid="autopilot-active-count">{{ store.dashboardSummary.active_strategies }}</span>
            <span class="summary-separator">+</span>
            <span data-testid="autopilot-waiting-count">{{ store.dashboardSummary.waiting_strategies }}</span>
            <span class="summary-secondary">
              / {{ store.dashboardSummary.risk_metrics.max_active_strategies }}
            </span>
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
          </p>
          <!-- Broker Status -->
          <div
            class="broker-status"
            data-testid="autopilot-broker-status"
            :data-connected="store.dashboardSummary.kite_connected"
          >
            <span
              class="broker-dot"
              :class="store.dashboardSummary.kite_connected ? 'dot-connected' : 'dot-disconnected'"
            ></span>
            <span class="broker-text">
              Broker: {{ store.dashboardSummary.kite_connected ? 'Connected' : 'Disconnected' }}
            </span>
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

        <!-- Empty State -->
        <div v-if="store.strategies.length === 0" class="empty-state" data-testid="autopilot-empty-state">
          <p class="empty-state-text">No strategies yet. Create your first AutoPilot strategy!</p>
          <button
            @click="navigateToBuilder"
            data-testid="autopilot-empty-create-btn"
            class="strategy-btn strategy-btn-primary"
          >
            Create Strategy
          </button>
        </div>

        <div v-else class="strategy-items">
          <div
            v-for="strategy in store.strategies"
            :key="strategy.id"
            class="strategy-item"
            :data-testid="`autopilot-strategy-card-${strategy.id}`"
            @click="navigateToStrategy(strategy.id)"
          >
            <div class="strategy-item-content">
              <div>
                <div class="strategy-item-header">
                  <h3 class="strategy-name">{{ strategy.name }}</h3>
                  <span
                    :class="getStatusBadgeClass(strategy.status)"
                    :data-testid="`autopilot-strategy-status-${strategy.id}`"
                  >
                    {{ strategy.status }}
                  </span>
                </div>
                <p class="strategy-meta">
                  {{ strategy.underlying }} • {{ strategy.lots }} lot(s) • {{ strategy.leg_count }} legs
                </p>
              </div>

              <div class="strategy-item-right">
                <p :class="['strategy-pnl', getPnLClass(strategy.current_pnl)]" :data-testid="`autopilot-strategy-pnl-${strategy.id}`">
                  {{ formatCurrency(strategy.current_pnl) }}
                </p>
                <div class="strategy-actions" @click.stop :data-testid="`autopilot-strategy-actions-${strategy.id}`">
                  <button
                    v-if="['active', 'waiting', 'pending'].includes(strategy.status)"
                    @click="handlePause(strategy)"
                    :data-testid="`autopilot-pause-strategy-${strategy.id}`"
                    class="action-btn action-pause"
                  >
                    Pause
                  </button>
                  <button
                    v-if="strategy.status === 'paused'"
                    @click="handleResume(strategy)"
                    :data-testid="`autopilot-resume-strategy-${strategy.id}`"
                    class="action-btn action-resume"
                  >
                    Resume
                  </button>
                  <button
                    v-if="strategy.share_token"
                    @click="handleShare(strategy)"
                    :data-testid="`autopilot-strategy-unshare-btn-${strategy.id}`"
                    class="action-btn action-unshare"
                  >
                    Unshare
                  </button>
                  <button
                    v-else
                    @click="handleShare(strategy)"
                    :data-testid="`autopilot-strategy-share-btn-${strategy.id}`"
                    class="action-btn action-share"
                  >
                    Share
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Activity Feed -->
      <div class="activity-feed-card" data-testid="autopilot-activity-feed">
        <div class="activity-feed-header">
          <h2 class="section-title">Recent Activity</h2>
        </div>
        <div class="activity-feed-content">
          <div v-if="store.recentLogs && store.recentLogs.length > 0" class="activity-list">
            <div
              v-for="(log, index) in store.recentLogs.slice(0, 5)"
              :key="log.id"
              class="activity-item"
              :data-testid="`autopilot-activity-item-${index}`"
            >
              <span
                class="activity-dot"
                :class="{
                  'dot-info': log.severity === 'info',
                  'dot-warning': log.severity === 'warning',
                  'dot-error': log.severity === 'error'
                }"
              ></span>
              <div class="activity-text">
                <p class="activity-message">{{ log.message }}</p>
                <p class="activity-time">{{ new Date(log.created_at).toLocaleString() }}</p>
              </div>
            </div>
          </div>
          <div v-else class="activity-empty">
            No recent activity
          </div>
        </div>
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
}

.summary-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
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

/* ===== Broker Status ===== */
.broker-status {
  display: flex;
  align-items: center;
  margin-top: 8px;
}

.broker-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
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

/* ===== Empty State ===== */
.empty-state {
  padding: 32px;
  text-align: center;
}

.empty-state-text {
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

/* ===== Strategy Items ===== */
.strategy-items {
  border-top: 1px solid var(--kite-border-light);
}

.strategy-item {
  padding: 16px;
  border-bottom: 1px solid var(--kite-border-light);
  cursor: pointer;
}

.strategy-item:hover {
  background: var(--kite-table-hover);
}

.strategy-item-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.strategy-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-name {
  font-weight: 500;
  color: var(--kite-text-primary);
}

.strategy-meta {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.strategy-item-right {
  text-align: right;
}

.strategy-pnl {
  font-weight: 500;
}

.strategy-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.action-btn {
  padding: 4px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.action-pause {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.action-pause:hover {
  background: #ffe0b2;
}

.action-resume {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.action-resume:hover {
  background: #c8e6c9;
}

.action-share {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.action-share:hover {
  background: #bbdefb;
}

.action-unshare {
  background: var(--kite-purple-light, #f3e5f5);
  color: #7b1fa2;
}

.action-unshare:hover {
  background: #e1bee7;
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

/* ===== Activity Feed ===== */
.activity-feed-card {
  margin-top: 24px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.activity-feed-header {
  padding: 16px;
  border-bottom: 1px solid var(--kite-border);
}

.activity-feed-content {
  padding: 16px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.activity-dot {
  width: 8px;
  height: 8px;
  margin-top: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.activity-text {
  flex: 1;
}

.activity-message {
  font-size: 0.875rem;
  color: var(--kite-text-primary);
}

.activity-time {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.activity-empty {
  text-align: center;
  color: var(--kite-text-secondary);
  padding: 16px;
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
</style>
