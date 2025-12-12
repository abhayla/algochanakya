<script setup>
/**
 * AutoPilot Backtests View
 *
 * Phase 4: Run backtests on strategies with historical data.
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

// Backtests list
const backtests = computed(() => store.backtests || [])
const backtestsLoading = ref(false)

// Create backtest modal
const showCreateModal = ref(false)
const createLoading = ref(false)
const backtestForm = ref({
  name: '',
  description: '',
  strategy_config: {
    underlying: 'NIFTY',
    lots: 1,
    legs_config: [],
    entry_conditions: {},
    risk_settings: {}
  },
  start_date: '',
  end_date: '',
  initial_capital: 100000,
  slippage_pct: 0.1,
  charges_per_lot: 50,
  data_interval: '1min'
})

// Backtest detail modal
const showDetailModal = ref(false)
const selectedBacktest = ref(null)

// Status filter
const statusFilter = ref(null)

// Underlyings
const underlyings = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']

// Data intervals
const dataIntervals = [
  { value: '1min', label: '1 Minute' },
  { value: '5min', label: '5 Minutes' },
  { value: '15min', label: '15 Minutes' },
  { value: '30min', label: '30 Minutes' },
  { value: '1hour', label: '1 Hour' },
  { value: '1day', label: '1 Day' }
]

// Status options
const statusOptions = [
  { value: null, label: 'All Status' },
  { value: 'pending', label: 'Pending' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' }
]

// Fetch backtests
const fetchBacktests = async () => {
  backtestsLoading.value = true
  try {
    await store.fetchBacktests({
      status: statusFilter.value
    })
  } finally {
    backtestsLoading.value = false
  }
}

onMounted(async () => {
  // Set default dates
  const today = new Date()
  const ninetyDaysAgo = new Date(today)
  ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90)

  backtestForm.value.end_date = today.toISOString().split('T')[0]
  backtestForm.value.start_date = ninetyDaysAgo.toISOString().split('T')[0]

  await fetchBacktests()
})

watch(statusFilter, fetchBacktests)

const handleCreateBacktest = async () => {
  createLoading.value = true
  try {
    await store.createBacktest({
      name: backtestForm.value.name || `Backtest - ${backtestForm.value.strategy_config.underlying}`,
      description: backtestForm.value.description,
      strategy_config: backtestForm.value.strategy_config,
      start_date: backtestForm.value.start_date,
      end_date: backtestForm.value.end_date,
      initial_capital: backtestForm.value.initial_capital,
      slippage_pct: backtestForm.value.slippage_pct,
      charges_per_lot: backtestForm.value.charges_per_lot,
      data_interval: backtestForm.value.data_interval
    })
    showCreateModal.value = false
    resetForm()
    await fetchBacktests()
  } finally {
    createLoading.value = false
  }
}

const handleCancelBacktest = async (backtest) => {
  if (confirm(`Cancel backtest "${backtest.name}"?`)) {
    await store.cancelBacktest(backtest.id)
    await fetchBacktests()
  }
}

const handleDeleteBacktest = async (backtest) => {
  if (confirm(`Delete backtest "${backtest.name}"?`)) {
    await store.deleteBacktest(backtest.id)
    await fetchBacktests()
  }
}

const openDetail = async (backtest) => {
  selectedBacktest.value = backtest
  showDetailModal.value = true
}

const closeDetail = () => {
  selectedBacktest.value = null
  showDetailModal.value = false
}

const resetForm = () => {
  const today = new Date()
  const ninetyDaysAgo = new Date(today)
  ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90)

  backtestForm.value = {
    name: '',
    description: '',
    strategy_config: {
      underlying: 'NIFTY',
      lots: 1,
      legs_config: [],
      entry_conditions: {},
      risk_settings: {}
    },
    start_date: ninetyDaysAgo.toISOString().split('T')[0],
    end_date: today.toISOString().split('T')[0],
    initial_capital: 100000,
    slippage_pct: 0.1,
    charges_per_lot: 50,
    data_interval: '1min'
  }
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const formatPercent = (value) => {
  if (value === null || value === undefined) return '0%'
  return `${value >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    pending: 'status-badge status-pending',
    running: 'status-badge status-running',
    completed: 'status-badge status-completed',
    failed: 'status-badge status-failed',
    cancelled: 'status-badge status-cancelled'
  }
  return classes[status] || 'status-badge'
}

const navigateToDashboard = () => {
  router.push('/autopilot')
}

const navigateToAnalytics = () => {
  router.push('/autopilot/analytics')
}
</script>

<template>
  <KiteLayout>
    <div class="backtests-view" data-testid="autopilot-backtest-page">
      <!-- Header -->
      <div class="backtests-header" data-testid="autopilot-backtest-header">
        <div>
          <div class="header-breadcrumb">
            <button @click="navigateToDashboard" class="breadcrumb-link">AutoPilot</button>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">Backtests</span>
          </div>
          <h1 class="backtests-title">Strategy Backtests</h1>
          <p class="backtests-subtitle">Test your strategies on historical data</p>
        </div>
        <div class="backtests-actions">
          <button
            @click="navigateToAnalytics"
            class="strategy-btn strategy-btn-outline"
            data-testid="autopilot-backtest-analytics-btn"
          >
            Analytics
          </button>
          <button
            @click="showCreateModal = true"
            class="strategy-btn strategy-btn-primary"
            data-testid="autopilot-backtest-new-btn"
          >
            + New Backtest
          </button>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-section" data-testid="autopilot-backtest-filters">
        <select
          v-model="statusFilter"
          class="filter-select"
          data-testid="autopilot-backtest-filter-completed"
        >
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <button
          @click="fetchBacktests"
          class="icon-btn"
          data-testid="autopilot-backtest-refresh-btn"
        >
          <svg class="icon-svg-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
        </button>
      </div>

      <!-- Backtests List -->
      <div class="backtests-card" data-testid="autopilot-backtest-list">
        <div v-if="backtestsLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p class="loading-text">Loading backtests...</p>
        </div>

        <div v-else-if="backtests.length === 0" class="empty-state" data-testid="autopilot-backtest-empty">
          <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
          </svg>
          <p class="empty-text">No backtests yet. Create your first backtest to analyze strategy performance.</p>
          <button
            @click="showCreateModal = true"
            class="strategy-btn strategy-btn-primary"
          >
            Create Backtest
          </button>
        </div>

        <div v-else class="backtests-grid">
          <div
            v-for="backtest in backtests"
            :key="backtest.id"
            class="backtest-card"
            :data-testid="`autopilot-backtest-row-${backtest.id}`"
            @click="openDetail(backtest)"
          >
            <div class="backtest-header">
              <h3 class="backtest-name">{{ backtest.name }}</h3>
              <span :class="getStatusBadgeClass(backtest.status)">
                {{ backtest.status }}
              </span>
            </div>

            <p class="backtest-dates">
              {{ formatDate(backtest.start_date) }} - {{ formatDate(backtest.end_date) }}
            </p>

            <!-- Progress bar for running backtests -->
            <div v-if="backtest.status === 'running'" class="progress-section">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: (backtest.progress_pct || 0) + '%' }"
                ></div>
              </div>
              <span class="progress-text">{{ backtest.progress_pct || 0 }}%</span>
            </div>

            <!-- Results for completed backtests -->
            <div v-if="backtest.status === 'completed'" class="backtest-results">
              <div class="result-row">
                <span class="result-label">Net P&L</span>
                <span :class="['result-value', getPnLClass(backtest.net_pnl)]">
                  {{ formatCurrency(backtest.net_pnl) }}
                </span>
              </div>
              <div class="result-row">
                <span class="result-label">Win Rate</span>
                <span :class="['result-value', (backtest.win_rate || 0) >= 50 ? 'pnl-profit' : 'pnl-loss']">
                  {{ (backtest.win_rate || 0).toFixed(1) }}%
                </span>
              </div>
              <div class="result-row">
                <span class="result-label">Profit Factor</span>
                <span :class="['result-value', (backtest.profit_factor || 0) >= 1 ? 'pnl-profit' : 'pnl-loss']">
                  {{ (backtest.profit_factor || 0).toFixed(2) }}
                </span>
              </div>
              <div class="result-row">
                <span class="result-label">Max Drawdown</span>
                <span class="result-value pnl-loss">
                  {{ formatPercent(-(backtest.max_drawdown_pct || 0)) }}
                </span>
              </div>
            </div>

            <!-- Error message for failed backtests -->
            <div v-if="backtest.status === 'failed'" class="backtest-error">
              <p class="error-message">{{ backtest.error_message || 'Unknown error' }}</p>
            </div>

            <div class="backtest-footer">
              <span class="backtest-trades" v-if="backtest.total_trades">
                {{ backtest.total_trades }} trades
              </span>
              <span class="backtest-created">
                {{ formatDateTime(backtest.created_at) }}
              </span>
            </div>

            <div class="backtest-actions" @click.stop>
              <button
                v-if="['pending', 'running'].includes(backtest.status)"
                @click="handleCancelBacktest(backtest)"
                class="action-btn action-cancel"
                :data-testid="`autopilot-backtest-cancel-${backtest.id}`"
              >
                Cancel
              </button>
              <button
                v-if="['completed', 'failed', 'cancelled'].includes(backtest.status)"
                @click="handleDeleteBacktest(backtest)"
                class="action-btn action-delete"
                :data-testid="`autopilot-backtest-delete-${backtest.id}`"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Create Backtest Modal -->
      <div
        v-if="showCreateModal"
        class="modal-overlay"
        @click.self="showCreateModal = false"
        data-testid="autopilot-backtest-config-modal"
      >
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h3 class="modal-title">Create New Backtest</h3>
            <button @click="showCreateModal = false" class="modal-close">
              <svg class="close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">Backtest Name</label>
              <input
                v-model="backtestForm.name"
                type="text"
                class="form-input"
                placeholder="e.g., NIFTY Iron Condor Backtest"
                data-testid="autopilot-backtest-name-input"
              />
            </div>

            <div class="form-group">
              <label class="form-label">Description (Optional)</label>
              <textarea
                v-model="backtestForm.description"
                class="form-textarea"
                placeholder="Notes about this backtest..."
                rows="2"
                data-testid="backtest-desc-input"
              ></textarea>
            </div>

            <div class="form-section">
              <h4 class="form-section-title">Strategy Configuration</h4>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Underlying</label>
                  <select
                    v-model="backtestForm.strategy_config.underlying"
                    class="form-select"
                    data-testid="backtest-underlying"
                  >
                    <option v-for="u in underlyings" :key="u" :value="u">
                      {{ u }}
                    </option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Lots</label>
                  <input
                    v-model.number="backtestForm.strategy_config.lots"
                    type="number"
                    min="1"
                    class="form-input"
                    data-testid="backtest-lots"
                  />
                </div>
              </div>
            </div>

            <div class="form-section">
              <h4 class="form-section-title">Date Range</h4>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Start Date</label>
                  <input
                    v-model="backtestForm.start_date"
                    type="date"
                    class="form-input"
                    data-testid="autopilot-backtest-start-date"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">End Date</label>
                  <input
                    v-model="backtestForm.end_date"
                    type="date"
                    class="form-input"
                    data-testid="autopilot-backtest-end-date"
                  />
                </div>
              </div>
            </div>

            <div class="form-section">
              <h4 class="form-section-title">Backtest Settings</h4>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Initial Capital</label>
                  <input
                    v-model.number="backtestForm.initial_capital"
                    type="number"
                    min="10000"
                    class="form-input"
                    data-testid="autopilot-backtest-capital"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">Data Interval</label>
                  <select
                    v-model="backtestForm.data_interval"
                    class="form-select"
                    data-testid="backtest-interval"
                  >
                    <option v-for="int in dataIntervals" :key="int.value" :value="int.value">
                      {{ int.label }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Slippage (%)</label>
                  <input
                    v-model.number="backtestForm.slippage_pct"
                    type="number"
                    min="0"
                    max="5"
                    step="0.01"
                    class="form-input"
                data-testid="autopilot-backtest-slippage"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">Charges Per Lot (₹)</label>
                  <input
                    v-model.number="backtestForm.charges_per_lot"
                    type="number"
                    min="0"
                    class="form-input"
                    data-testid="backtest-charges"
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button
              @click="showCreateModal = false"
              class="strategy-btn strategy-btn-outline"
              data-testid="autopilot-backtest-cancel-btn"
            >
              Cancel
            </button>
            <button
              @click="handleCreateBacktest"
              :disabled="createLoading || !backtestForm.start_date || !backtestForm.end_date"
              class="strategy-btn strategy-btn-primary"
              data-testid="autopilot-backtest-run-btn"
            >
              {{ createLoading ? 'Creating...' : 'Run Backtest' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Backtest Detail Modal -->
      <div
        v-if="showDetailModal && selectedBacktest"
        class="modal-overlay"
        @click.self="closeDetail"
        data-testid="autopilot-backtest-detail-modal"
      >
        <div class="modal-content modal-xl">
          <div class="modal-header">
            <div>
              <h3 class="modal-title">{{ selectedBacktest.name }}</h3>
              <span :class="getStatusBadgeClass(selectedBacktest.status)">
                {{ selectedBacktest.status }}
              </span>
            </div>
            <button @click="closeDetail" class="modal-close">
              <svg class="close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Summary Stats -->
            <div v-if="selectedBacktest.status === 'completed'" class="detail-stats-grid">
              <div class="detail-stat">
                <span class="detail-stat-label">Total Trades</span>
                <span class="detail-stat-value">{{ selectedBacktest.total_trades }}</span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Winning Trades</span>
                <span class="detail-stat-value pnl-profit">{{ selectedBacktest.winning_trades }}</span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Losing Trades</span>
                <span class="detail-stat-value pnl-loss">{{ selectedBacktest.losing_trades }}</span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Win Rate</span>
                <span :class="['detail-stat-value', (selectedBacktest.win_rate || 0) >= 50 ? 'pnl-profit' : 'pnl-loss']">
                  {{ (selectedBacktest.win_rate || 0).toFixed(1) }}%
                </span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Gross P&L</span>
                <span :class="['detail-stat-value', getPnLClass(selectedBacktest.gross_pnl)]">
                  {{ formatCurrency(selectedBacktest.gross_pnl) }}
                </span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Net P&L</span>
                <span :class="['detail-stat-value', getPnLClass(selectedBacktest.net_pnl)]">
                  {{ formatCurrency(selectedBacktest.net_pnl) }}
                </span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Max Drawdown</span>
                <span class="detail-stat-value pnl-loss">
                  {{ formatCurrency(selectedBacktest.max_drawdown) }}
                  ({{ formatPercent(-(selectedBacktest.max_drawdown_pct || 0)) }})
                </span>
              </div>
              <div class="detail-stat">
                <span class="detail-stat-label">Profit Factor</span>
                <span :class="['detail-stat-value', (selectedBacktest.profit_factor || 0) >= 1 ? 'pnl-profit' : 'pnl-loss']">
                  {{ (selectedBacktest.profit_factor || 0).toFixed(2) }}
                </span>
              </div>
            </div>

            <!-- Equity Curve Chart (simplified) -->
            <div v-if="selectedBacktest.equity_curve && selectedBacktest.equity_curve.length > 0" class="equity-section">
              <h4 class="section-subtitle">Equity Curve</h4>
              <div class="equity-chart">
                <svg viewBox="0 0 600 200" class="equity-svg">
                  <polyline
                    :points="selectedBacktest.equity_curve.map((point, i) =>
                      `${(i / (selectedBacktest.equity_curve.length - 1)) * 600},${200 - ((point.equity - Math.min(...selectedBacktest.equity_curve.map(p => p.equity))) / (Math.max(...selectedBacktest.equity_curve.map(p => p.equity)) - Math.min(...selectedBacktest.equity_curve.map(p => p.equity)))) * 180}`
                    ).join(' ')"
                    fill="none"
                    stroke="var(--kite-blue)"
                    stroke-width="2"
                  />
                </svg>
              </div>
            </div>

            <!-- Trade List Preview -->
            <div v-if="selectedBacktest.trades && selectedBacktest.trades.length > 0" class="trades-section">
              <h4 class="section-subtitle">Recent Trades (Last 10)</h4>
              <div class="trades-preview">
                <table class="trades-mini-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>P&L</th>
                      <th>Exit Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(trade, index) in selectedBacktest.trades.slice(-10).reverse()" :key="index">
                      <td>{{ formatDate(trade.date) }}</td>
                      <td :class="getPnLClass(trade.pnl)">{{ formatCurrency(trade.pnl) }}</td>
                      <td>{{ trade.exit_reason }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Configuration Details -->
            <div class="config-section">
              <h4 class="section-subtitle">Backtest Configuration</h4>
              <div class="config-grid">
                <div class="config-item">
                  <span class="config-label">Date Range</span>
                  <span class="config-value">
                    {{ formatDate(selectedBacktest.start_date) }} - {{ formatDate(selectedBacktest.end_date) }}
                  </span>
                </div>
                <div class="config-item">
                  <span class="config-label">Initial Capital</span>
                  <span class="config-value">{{ formatCurrency(selectedBacktest.initial_capital) }}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Slippage</span>
                  <span class="config-value">{{ selectedBacktest.slippage_pct }}%</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Charges Per Lot</span>
                  <span class="config-value">{{ formatCurrency(selectedBacktest.charges_per_lot) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeDetail" class="strategy-btn strategy-btn-outline">
              Close
            </button>
          </div>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="store.error" class="error-banner" data-testid="autopilot-backtest-error">
        <p class="error-text">{{ store.error }}</p>
        <button @click="store.clearError" class="error-dismiss">Dismiss</button>
      </div>
    </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.backtests-view {
  padding: 24px;
}

/* ===== Header ===== */
.backtests-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.breadcrumb-link {
  font-size: 0.875rem;
  color: var(--kite-blue);
  background: none;
  border: none;
  cursor: pointer;
}

.breadcrumb-link:hover {
  text-decoration: underline;
}

.breadcrumb-separator {
  color: var(--kite-text-muted);
}

.breadcrumb-current {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.backtests-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.backtests-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.backtests-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== Filters ===== */
.filters-section {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 24px;
}

.filter-select {
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
}

/* ===== Backtests Card ===== */
.backtests-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

/* ===== Backtests Grid ===== */
.backtests-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .backtests-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .backtests-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.backtest-card {
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.backtest-card:hover {
  border-color: var(--kite-blue);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.backtest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.backtest-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.backtest-dates {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

/* ===== Progress ===== */
.progress-section {
  margin-bottom: 12px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--kite-border-light);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 8px;
  background: var(--kite-blue);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
  display: block;
}

/* ===== Results ===== */
.backtest-results {
  background: var(--kite-table-header);
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
}

.result-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.result-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.result-value {
  font-size: 0.875rem;
  font-weight: 600;
}

/* ===== Error ===== */
.backtest-error {
  background: var(--kite-red-light, #ffebee);
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
}

.error-message {
  font-size: 0.75rem;
  color: var(--kite-red);
}

/* ===== Footer ===== */
.backtest-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.backtest-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 4px 12px;
  font-size: 0.75rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.action-cancel {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.action-cancel:hover {
  background: #ffe0b2;
}

.action-delete {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.action-delete:hover {
  background: #ffcdd2;
}

/* ===== Status Badge ===== */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
}

.status-pending {
  background: #fff8e1;
  color: #f57f17;
}

.status-running {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.status-completed {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.status-failed {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.status-cancelled {
  background: var(--kite-border-light);
  color: var(--kite-text-secondary);
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
  width: calc(100% - 32px);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.modal-lg {
  max-width: 600px;
}

.modal-content.modal-xl {
  max-width: 800px;
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--kite-border);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
}

.modal-close {
  padding: 4px;
  background: transparent;
  border: none;
  color: var(--kite-text-secondary);
  cursor: pointer;
}

.modal-close:hover {
  color: var(--kite-text-primary);
}

.close-icon {
  width: 20px;
  height: 20px;
}

.modal-body {
  padding: 24px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--kite-border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Detail Modal ===== */
.detail-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

@media (min-width: 640px) {
  .detail-stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.detail-stat {
  padding: 12px;
  background: var(--kite-table-header);
  border-radius: 4px;
}

.detail-stat-label {
  display: block;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.detail-stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.section-subtitle {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.equity-section {
  margin-bottom: 24px;
}

.equity-chart {
  width: 100%;
  height: 200px;
  background: var(--kite-table-header);
  border-radius: 4px;
  padding: 10px;
}

.equity-svg {
  width: 100%;
  height: 100%;
}

.trades-section {
  margin-bottom: 24px;
}

.trades-preview {
  overflow-x: auto;
}

.trades-mini-table {
  width: 100%;
  border-collapse: collapse;
}

.trades-mini-table th,
.trades-mini-table td {
  padding: 8px 12px;
  text-align: left;
  font-size: 0.75rem;
  border-bottom: 1px solid var(--kite-border-light);
}

.trades-mini-table th {
  background: var(--kite-table-header);
  color: var(--kite-text-secondary);
  font-weight: 500;
}

.config-section {
  margin-bottom: 16px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.config-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.config-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

/* ===== Form Styles ===== */
.form-group {
  margin-bottom: 16px;
}

.form-section {
  margin-bottom: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.form-section:first-child {
  border-top: none;
  padding-top: 0;
}

.form-section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 4px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
}

.form-textarea {
  resize: vertical;
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

/* ===== Loading & Empty States ===== */
.loading-state {
  text-align: center;
  padding: 48px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
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

.empty-state {
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--kite-text-muted);
  margin: 0 auto 16px;
}

.empty-text {
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
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

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

.icon-btn {
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

.icon-svg-sm {
  width: 20px;
  height: 20px;
}
</style>
