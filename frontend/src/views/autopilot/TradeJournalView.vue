<script setup>
/**
 * AutoPilot Trade Journal View
 *
 * Phase 4: Trade journal with complete trade history, filters, and export.
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

// Filters
const filters = ref({
  underlying: null,
  exitReason: null,
  startDate: null,
  endDate: null,
  search: ''
})

// Pagination
const currentPage = ref(1)
const pageSize = ref(20)

// Trade detail modal
const selectedTrade = ref(null)
const showTradeDetail = ref(false)
const tradeNotes = ref('')
const savingNotes = ref(false)

// Sort state
const sortField = ref('exit_time')
const sortDirection = ref('desc')

// Export modal
const showExportModal = ref(false)
const exportFormat = ref('csv')
const exportLoading = ref(false)

// Loading state
const loading = ref(false)

// Exit reasons options
const exitReasons = [
  { value: null, label: 'All Exit Reasons' },
  { value: 'target_hit', label: 'Target Hit' },
  { value: 'stop_loss', label: 'Stop Loss' },
  { value: 'trailing_stop', label: 'Trailing Stop' },
  { value: 'expiry', label: 'Expiry' },
  { value: 'manual', label: 'Manual Exit' },
  { value: 'kill_switch', label: 'Kill Switch' },
  { value: 'daily_loss_limit', label: 'Daily Loss Limit' }
]

// Underlying options
const underlyings = [
  { value: null, label: 'All Underlyings' },
  { value: 'NIFTY', label: 'NIFTY' },
  { value: 'BANKNIFTY', label: 'BANKNIFTY' },
  { value: 'FINNIFTY', label: 'FINNIFTY' },
  { value: 'SENSEX', label: 'SENSEX' }
]

// Computed trades list from store
const trades = computed(() => store.journalTrades || [])
const stats = computed(() => store.journalStats || {})
const totalPages = computed(() => store.journalPagination?.total_pages || 1)
const totalTrades = computed(() => store.journalPagination?.total || 0)

// Fetch trades with current filters
const fetchTrades = async () => {
  loading.value = true
  try {
    await store.fetchJournalTrades({
      underlying: filters.value.underlying,
      exit_reason: filters.value.exitReason,
      start_date: filters.value.startDate,
      end_date: filters.value.endDate,
      page: currentPage.value,
      page_size: pageSize.value
    })
  } finally {
    loading.value = false
  }
}

// Fetch stats
const fetchStats = async () => {
  await store.fetchJournalStats({
    start_date: filters.value.startDate,
    end_date: filters.value.endDate
  })
}

onMounted(async () => {
  // Set default date range (last 30 days)
  const today = new Date()
  const thirtyDaysAgo = new Date(today)
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  filters.value.endDate = today.toISOString().split('T')[0]
  filters.value.startDate = thirtyDaysAgo.toISOString().split('T')[0]

  await Promise.all([fetchTrades(), fetchStats()])
})

// Watch filters and refetch
watch(
  () => [filters.value.underlying, filters.value.exitReason, filters.value.startDate, filters.value.endDate],
  () => {
    currentPage.value = 1
    fetchTrades()
    fetchStats()
  }
)

// Watch page changes
watch(currentPage, fetchTrades)

const handlePageChange = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

const clearFilters = () => {
  filters.value.underlying = null
  filters.value.exitReason = null
  filters.value.search = ''
  // Reset to last 30 days
  const today = new Date()
  const thirtyDaysAgo = new Date(today)
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  filters.value.endDate = today.toISOString().split('T')[0]
  filters.value.startDate = thirtyDaysAgo.toISOString().split('T')[0]
}

const openTradeDetail = (trade) => {
  selectedTrade.value = trade
  tradeNotes.value = trade.notes || ''
  showTradeDetail.value = true
}

const closeTradeDetail = () => {
  selectedTrade.value = null
  tradeNotes.value = ''
  showTradeDetail.value = false
}

// Save notes for a trade
const saveTradeNotes = async () => {
  if (!selectedTrade.value) return
  savingNotes.value = true
  try {
    await store.updateTradeNotes(selectedTrade.value.id, tradeNotes.value)
    // Update the local trade object
    selectedTrade.value.notes = tradeNotes.value
  } finally {
    savingNotes.value = false
  }
}

// Toggle sort direction
const toggleSort = (field) => {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDirection.value = 'desc'
  }
  fetchTrades()
}

// Computed cumulative P&L data for chart
const cumulativePnlData = computed(() => {
  if (!trades.value || trades.value.length === 0) return []

  let cumulative = 0
  return trades.value
    .slice()
    .sort((a, b) => new Date(a.exit_time) - new Date(b.exit_time))
    .map(trade => {
      cumulative += trade.net_pnl || 0
      return {
        date: trade.exit_time,
        pnl: trade.net_pnl || 0,
        cumulative
      }
    })
})

const handleExport = async () => {
  exportLoading.value = true
  try {
    await store.exportJournalTrades({
      format: exportFormat.value,
      start_date: filters.value.startDate,
      end_date: filters.value.endDate,
      underlying: filters.value.underlying
    })
    showExportModal.value = false
  } finally {
    exportLoading.value = false
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
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
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

const formatDuration = (minutes) => {
  if (!minutes) return '-'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getExitReasonBadgeClass = (reason) => {
  const classes = {
    target_hit: 'exit-badge exit-target',
    stop_loss: 'exit-badge exit-stoploss',
    trailing_stop: 'exit-badge exit-trailing',
    expiry: 'exit-badge exit-expiry',
    manual: 'exit-badge exit-manual',
    kill_switch: 'exit-badge exit-killswitch',
    daily_loss_limit: 'exit-badge exit-daily'
  }
  return classes[reason] || 'exit-badge exit-default'
}

const formatExitReason = (reason) => {
  const labels = {
    target_hit: 'Target Hit',
    stop_loss: 'Stop Loss',
    trailing_stop: 'Trailing Stop',
    expiry: 'Expiry',
    manual: 'Manual',
    kill_switch: 'Kill Switch',
    daily_loss_limit: 'Daily Limit'
  }
  return labels[reason] || reason
}

const navigateToDashboard = () => {
  router.push('/autopilot')
}
</script>

<template>
  <KiteLayout>
    <div class="trade-journal" data-testid="autopilot-journal-page">
      <!-- Header -->
      <div class="journal-header" data-testid="autopilot-journal-header">
        <div>
          <div class="header-breadcrumb">
            <button @click="navigateToDashboard" class="breadcrumb-link">AutoPilot</button>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">Trade Journal</span>
          </div>
          <h1 class="journal-title">Trade Journal</h1>
          <p class="journal-subtitle">Complete history of all your automated trades</p>
        </div>
        <div class="journal-actions">
          <button
            @click="showExportModal = true"
            data-testid="autopilot-journal-export-btn"
            class="strategy-btn strategy-btn-outline"
          >
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
            </svg>
            Export
          </button>
          <button
            @click="fetchTrades"
            data-testid="autopilot-journal-refresh-btn"
            class="icon-btn"
          >
            <svg class="icon-svg-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- Stats Summary Cards -->
      <div class="stats-cards" data-testid="autopilot-journal-stats">
        <div class="stats-card" data-testid="autopilot-journal-total-trades">
          <p class="stats-label">Total Trades</p>
          <p class="stats-value">{{ stats.total_trades || 0 }}</p>
          <p class="stats-secondary">
            <span class="stat-win">{{ stats.winning_trades || 0 }} wins</span>
            <span class="stats-divider">•</span>
            <span class="stat-loss">{{ stats.losing_trades || 0 }} losses</span>
          </p>
        </div>

        <div class="stats-card" data-testid="autopilot-journal-win-rate">
          <p class="stats-label">Win Rate</p>
          <p class="stats-value" :class="stats.win_rate >= 50 ? 'pnl-profit' : 'pnl-loss'">
            {{ (stats.win_rate || 0).toFixed(1) }}%
          </p>
          <div class="win-rate-bar">
            <div
              class="win-rate-fill"
              :style="{ width: (stats.win_rate || 0) + '%' }"
            ></div>
          </div>
        </div>

        <div class="stats-card" data-testid="autopilot-journal-net-pnl">
          <p class="stats-label">Net P&L</p>
          <p class="stats-value" :class="getPnLClass(stats.net_pnl)">
            {{ formatCurrency(stats.net_pnl) }}
          </p>
          <p class="stats-secondary">
            Gross: {{ formatCurrency(stats.gross_pnl) }}
          </p>
        </div>

        <div class="stats-card" data-testid="autopilot-journal-profit-factor">
          <p class="stats-label">Profit Factor</p>
          <p class="stats-value" :class="(stats.profit_factor || 0) >= 1 ? 'pnl-profit' : 'pnl-loss'">
            {{ (stats.profit_factor || 0).toFixed(2) }}
          </p>
          <p class="stats-secondary">
            Avg Win/Loss Ratio
          </p>
        </div>
      </div>

      <!-- Cumulative P&L Chart -->
      <div class="chart-card" data-testid="autopilot-journal-cumulative-chart">
        <h3 class="chart-title">Cumulative P&L</h3>
        <div class="chart-container">
          <div v-if="cumulativePnlData.length === 0" class="chart-empty">
            No trade data available for chart
          </div>
          <div v-else class="cumulative-chart">
            <div class="chart-bars">
              <div
                v-for="(point, index) in cumulativePnlData"
                :key="index"
                class="chart-bar-wrapper"
                :title="`${formatDate(point.date)}: ${formatCurrency(point.cumulative)}`"
              >
                <div
                  class="chart-bar"
                  :class="point.cumulative >= 0 ? 'bar-positive' : 'bar-negative'"
                  :style="{
                    height: Math.min(Math.abs(point.cumulative) / (Math.max(...cumulativePnlData.map(p => Math.abs(p.cumulative))) || 1) * 100, 100) + '%'
                  }"
                ></div>
              </div>
            </div>
            <div class="chart-summary">
              <span :class="cumulativePnlData[cumulativePnlData.length - 1]?.cumulative >= 0 ? 'pnl-profit' : 'pnl-loss'">
                Total: {{ formatCurrency(cumulativePnlData[cumulativePnlData.length - 1]?.cumulative || 0) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-section" data-testid="autopilot-journal-filters">
        <div class="filters-row">
          <div class="filter-group">
            <label class="filter-label">Date Range</label>
            <div class="date-range">
              <input
                v-model="filters.startDate"
                type="date"
                class="filter-input date-input"
                data-testid="autopilot-journal-start-date"
              />
              <span class="date-separator">to</span>
              <input
                v-model="filters.endDate"
                type="date"
                class="filter-input date-input"
                data-testid="autopilot-journal-end-date"
              />
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">Underlying</label>
            <select
              v-model="filters.underlying"
              class="filter-select"
              data-testid="autopilot-journal-underlying-filter"
            >
              <option v-for="opt in underlyings" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div class="filter-group">
            <label class="filter-label">Exit Reason</label>
            <select
              v-model="filters.exitReason"
              class="filter-select"
              data-testid="autopilot-journal-outcome-filter"
            >
              <option v-for="opt in exitReasons" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div class="filter-actions">
            <button
              v-if="filters.underlying || filters.exitReason"
              @click="clearFilters"
              class="link-btn"
              data-testid="autopilot-journal-clear-filters"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      <!-- Trades Table -->
      <div class="trades-card" data-testid="autopilot-journal-trades-table">
        <div class="trades-header">
          <h2 class="section-title">Trade History</h2>
          <span class="trades-count">{{ totalTrades }} trades</span>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <p class="loading-text">Loading trades...</p>
        </div>

        <!-- Empty State -->
        <div v-else-if="trades.length === 0" class="empty-state" data-testid="autopilot-journal-empty-state">
          <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <p class="empty-text">No trades found for the selected filters</p>
          <button @click="clearFilters" class="strategy-btn strategy-btn-outline">
            Clear Filters
          </button>
        </div>

        <!-- Trades Table -->
        <div v-else class="trades-table-wrapper">
          <table class="trades-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Underlying</th>
                <th>Entry</th>
                <th
                  class="sortable-header"
                  data-testid="autopilot-journal-sort-date"
                  @click="toggleSort('exit_time')"
                >
                  Exit
                  <span class="sort-indicator" v-if="sortField === 'exit_time'">
                    {{ sortDirection === 'asc' ? '↑' : '↓' }}
                  </span>
                </th>
                <th>Duration</th>
                <th>Lots</th>
                <th class="text-right">Gross P&L</th>
                <th class="text-right">Net P&L</th>
                <th>Exit Reason</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="trade in trades"
                :key="trade.id"
                class="trade-row"
                :data-testid="`autopilot-journal-trade-row-${trade.id}`"
                @click="openTradeDetail(trade)"
              >
                <td>
                  <span class="trade-strategy">{{ trade.strategy_name }}</span>
                </td>
                <td>
                  <span class="trade-underlying">{{ trade.underlying }}</span>
                </td>
                <td>
                  <span class="trade-time">{{ formatDateTime(trade.entry_time) }}</span>
                </td>
                <td>
                  <span class="trade-time">{{ formatDateTime(trade.exit_time) }}</span>
                </td>
                <td>
                  <span class="trade-duration">{{ formatDuration(trade.holding_duration_minutes) }}</span>
                </td>
                <td>
                  <span class="trade-lots">{{ trade.lots }}</span>
                </td>
                <td class="text-right">
                  <span :class="getPnLClass(trade.gross_pnl)">
                    {{ formatCurrency(trade.gross_pnl) }}
                  </span>
                </td>
                <td class="text-right">
                  <span :class="['trade-pnl', getPnLClass(trade.net_pnl)]">
                    {{ formatCurrency(trade.net_pnl) }}
                  </span>
                </td>
                <td>
                  <span :class="getExitReasonBadgeClass(trade.exit_reason)">
                    {{ formatExitReason(trade.exit_reason) }}
                  </span>
                </td>
                <td>
                  <button class="view-btn" @click.stop="openTradeDetail(trade)">
                    <svg class="view-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination" data-testid="autopilot-journal-pagination">
          <button
            @click="handlePageChange(currentPage - 1)"
            :disabled="currentPage <= 1"
            class="pagination-btn"
          >
            Previous
          </button>
          <span class="pagination-info">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <button
            @click="handlePageChange(currentPage + 1)"
            :disabled="currentPage >= totalPages"
            class="pagination-btn"
          >
            Next
          </button>
        </div>
      </div>

      <!-- Trade Detail Modal -->
      <div
        v-if="showTradeDetail && selectedTrade"
        class="modal-overlay"
        @click.self="closeTradeDetail"
        data-testid="autopilot-journal-trade-details"
      >
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h3 class="modal-title">Trade Details</h3>
            <button @click="closeTradeDetail" class="modal-close">
              <svg class="close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>

          <div class="trade-detail-content">
            <!-- Trade Summary -->
            <div class="detail-section">
              <h4 class="detail-section-title">Summary</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">Strategy</span>
                  <span class="detail-value">{{ selectedTrade.strategy_name }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Underlying</span>
                  <span class="detail-value">{{ selectedTrade.underlying }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Position Type</span>
                  <span class="detail-value">{{ selectedTrade.position_type }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Lots</span>
                  <span class="detail-value">{{ selectedTrade.lots }}</span>
                </div>
              </div>
            </div>

            <!-- Timing -->
            <div class="detail-section">
              <h4 class="detail-section-title">Timing</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">Entry Time</span>
                  <span class="detail-value">{{ formatDateTime(selectedTrade.entry_time) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Exit Time</span>
                  <span class="detail-value">{{ formatDateTime(selectedTrade.exit_time) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Duration</span>
                  <span class="detail-value">{{ formatDuration(selectedTrade.holding_duration_minutes) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Exit Reason</span>
                  <span :class="getExitReasonBadgeClass(selectedTrade.exit_reason)">
                    {{ formatExitReason(selectedTrade.exit_reason) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Prices -->
            <div class="detail-section">
              <h4 class="detail-section-title">Prices</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">Entry Premium</span>
                  <span class="detail-value">{{ formatCurrency(selectedTrade.entry_premium) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Exit Premium</span>
                  <span class="detail-value">{{ formatCurrency(selectedTrade.exit_premium) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Entry Spot</span>
                  <span class="detail-value">{{ selectedTrade.entry_spot ? formatCurrency(selectedTrade.entry_spot) : '-' }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Exit Spot</span>
                  <span class="detail-value">{{ selectedTrade.exit_spot ? formatCurrency(selectedTrade.exit_spot) : '-' }}</span>
                </div>
              </div>
            </div>

            <!-- Trade P&L Chart -->
            <div class="detail-section" data-testid="autopilot-journal-trade-pnl-chart">
              <h4 class="detail-section-title">P&L Visual</h4>
              <div class="trade-pnl-chart">
                <div class="pnl-bar-container">
                  <div class="pnl-bar-label">Entry</div>
                  <div class="pnl-bar-track">
                    <div
                      class="pnl-bar-fill bar-neutral"
                      :style="{ width: '50%' }"
                    >
                      {{ formatCurrency(selectedTrade.entry_premium) }}
                    </div>
                  </div>
                </div>
                <div class="pnl-bar-container">
                  <div class="pnl-bar-label">Exit</div>
                  <div class="pnl-bar-track">
                    <div
                      class="pnl-bar-fill"
                      :class="selectedTrade.net_pnl >= 0 ? 'bar-positive' : 'bar-negative'"
                      :style="{ width: Math.min(100, Math.abs((selectedTrade.exit_premium / (selectedTrade.entry_premium || 1)) * 50)) + '%' }"
                    >
                      {{ formatCurrency(selectedTrade.exit_premium) }}
                    </div>
                  </div>
                </div>
                <div class="pnl-result">
                  <span class="pnl-result-label">Result:</span>
                  <span :class="['pnl-result-value', getPnLClass(selectedTrade.net_pnl)]">
                    {{ formatCurrency(selectedTrade.net_pnl) }}
                    ({{ formatPercent(selectedTrade.pnl_percentage) }})
                  </span>
                </div>
              </div>
            </div>

            <!-- P&L Breakdown -->
            <div class="detail-section">
              <h4 class="detail-section-title">P&L Breakdown</h4>
              <div class="pnl-breakdown">
                <div class="pnl-row">
                  <span>Gross P&L</span>
                  <span :class="getPnLClass(selectedTrade.gross_pnl)">
                    {{ formatCurrency(selectedTrade.gross_pnl) }}
                  </span>
                </div>
                <div class="pnl-row pnl-deduction">
                  <span>Brokerage</span>
                  <span>- {{ formatCurrency(selectedTrade.brokerage) }}</span>
                </div>
                <div class="pnl-row pnl-deduction">
                  <span>Taxes & Charges</span>
                  <span>- {{ formatCurrency(selectedTrade.taxes) }}</span>
                </div>
                <div class="pnl-row pnl-total">
                  <span>Net P&L</span>
                  <span :class="getPnLClass(selectedTrade.net_pnl)">
                    {{ formatCurrency(selectedTrade.net_pnl) }}
                  </span>
                </div>
                <div class="pnl-row pnl-percentage">
                  <span>Return</span>
                  <span :class="getPnLClass(selectedTrade.pnl_percentage)">
                    {{ formatPercent(selectedTrade.pnl_percentage) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Editable Notes -->
            <div class="detail-section">
              <h4 class="detail-section-title">Notes</h4>
              <textarea
                v-model="tradeNotes"
                class="notes-textarea"
                placeholder="Add your notes about this trade..."
                rows="3"
                data-testid="autopilot-journal-trade-notes"
              ></textarea>
              <button
                @click="saveTradeNotes"
                :disabled="savingNotes"
                class="save-notes-btn"
                data-testid="autopilot-journal-trade-save-notes"
              >
                {{ savingNotes ? 'Saving...' : 'Save Notes' }}
              </button>
            </div>

            <!-- Tags (if any) -->
            <div v-if="selectedTrade.tags && selectedTrade.tags.length > 0" class="detail-section">
              <h4 class="detail-section-title">Tags</h4>
              <div class="trade-tags">
                <span v-for="tag in selectedTrade.tags" :key="tag" class="trade-tag">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeTradeDetail" class="strategy-btn strategy-btn-outline">
              Close
            </button>
          </div>
        </div>
      </div>

      <!-- Export Modal -->
      <div
        v-if="showExportModal"
        class="modal-overlay"
        @click.self="showExportModal = false"
        data-testid="autopilot-journal-export-modal"
      >
        <div class="modal-content">
          <h3 class="modal-title">Export Trades</h3>
          <p class="modal-text">
            Export your trade history for the selected date range.
          </p>

          <div class="export-options">
            <div class="export-info">
              <p><strong>Date Range:</strong> {{ formatDate(filters.startDate) }} - {{ formatDate(filters.endDate) }}</p>
              <p><strong>Underlying:</strong> {{ filters.underlying || 'All' }}</p>
            </div>

            <div class="export-format">
              <label class="filter-label">Export Format</label>
              <div class="format-options">
                <label class="format-option">
                  <input
                    type="radio"
                    v-model="exportFormat"
                    value="csv"
                  />
                  <span>CSV</span>
                </label>
                <label class="format-option">
                  <input
                    type="radio"
                    v-model="exportFormat"
                    value="excel"
                  />
                  <span>Excel</span>
                </label>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button
              @click="showExportModal = false"
              class="strategy-btn strategy-btn-outline"
            >
              Cancel
            </button>
            <button
              @click="handleExport"
              :disabled="exportLoading"
              class="strategy-btn strategy-btn-primary"
              data-testid="autopilot-journal-export-confirm"
            >
              {{ exportLoading ? 'Exporting...' : 'Export' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="store.error" class="error-banner" data-testid="autopilot-journal-error">
        <p class="error-text">{{ store.error }}</p>
        <button @click="store.clearError" class="error-dismiss">Dismiss</button>
      </div>
    </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.trade-journal {
  padding: 24px;
}

/* ===== Header ===== */
.journal-header {
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

.journal-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.journal-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.journal-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-icon {
  width: 18px;
  height: 18px;
  margin-right: 6px;
}

/* ===== Stats Cards ===== */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(4, 1fr);
  }
}

.stats-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.stats-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.stats-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.stats-secondary {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.stats-divider {
  margin: 0 6px;
}

.stat-win {
  color: var(--kite-green);
}

.stat-loss {
  color: var(--kite-red);
}

.win-rate-bar {
  margin-top: 8px;
  width: 100%;
  height: 6px;
  background: var(--kite-red-light, #ffebee);
  border-radius: 3px;
  overflow: hidden;
}

.win-rate-fill {
  height: 6px;
  background: var(--kite-green);
  border-radius: 3px;
  transition: width 0.3s ease;
}

/* ===== Filters ===== */
.filters-section {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  margin-bottom: 24px;
}

.filters-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
}

.filter-input,
.filter-select {
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-input {
  width: 140px;
}

.date-separator {
  color: var(--kite-text-secondary);
}

.filter-actions {
  display: flex;
  align-items: flex-end;
  margin-left: auto;
}

/* ===== Trades Card ===== */
.trades-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.trades-header {
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

.trades-count {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Trades Table ===== */
.trades-table-wrapper {
  overflow-x: auto;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
}

.trades-table th {
  padding: 12px 16px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: var(--kite-text-secondary);
  background: var(--kite-table-header);
  text-align: left;
  white-space: nowrap;
}

.trades-table th.text-right {
  text-align: right;
}

.trades-table td {
  padding: 12px 16px;
  font-size: 0.875rem;
  color: var(--kite-text-primary);
  border-bottom: 1px solid var(--kite-border-light);
}

.trades-table td.text-right {
  text-align: right;
}

.trade-row {
  cursor: pointer;
}

.trade-row:hover {
  background: var(--kite-table-hover);
}

.trade-strategy {
  font-weight: 500;
}

.trade-underlying {
  font-weight: 500;
  color: var(--kite-blue);
}

.trade-time {
  color: var(--kite-text-secondary);
  font-size: 0.8125rem;
}

.trade-duration {
  color: var(--kite-text-secondary);
}

.trade-lots {
  text-align: center;
}

.trade-pnl {
  font-weight: 600;
}

.view-btn {
  padding: 4px;
  background: transparent;
  border: none;
  color: var(--kite-text-secondary);
  cursor: pointer;
}

.view-btn:hover {
  color: var(--kite-blue);
}

.view-icon {
  width: 16px;
  height: 16px;
}

/* ===== Exit Badge ===== */
.exit-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  white-space: nowrap;
}

.exit-target {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.exit-stoploss {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.exit-trailing {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.exit-expiry {
  background: #f3e5f5;
  color: #7b1fa2;
}

.exit-manual {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.exit-killswitch {
  background: #ffebee;
  color: #c62828;
}

.exit-daily {
  background: #fff3e0;
  color: #e65100;
}

.exit-default {
  background: var(--kite-border-light);
  color: var(--kite-text-secondary);
}

/* ===== Pagination ===== */
.pagination {
  padding: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.pagination-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  background: white;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  cursor: pointer;
  color: var(--kite-text-primary);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 0.875rem;
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
  padding: 24px;
  max-width: 448px;
  width: calc(100% - 32px);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.modal-lg {
  max-width: 640px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
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

.modal-text {
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

.modal-footer {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* ===== Trade Detail ===== */
.trade-detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-section {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--kite-border-light);
}

.detail-section:last-of-type {
  border-bottom: none;
  padding-bottom: 0;
}

.detail-section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.detail-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.pnl-breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pnl-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.pnl-deduction {
  color: var(--kite-text-secondary);
}

.pnl-total {
  padding-top: 8px;
  border-top: 1px solid var(--kite-border);
  font-weight: 600;
}

.pnl-percentage {
  font-size: 0.8125rem;
  color: var(--kite-text-secondary);
}

.trade-notes {
  font-size: 0.875rem;
  color: var(--kite-text-primary);
  line-height: 1.5;
}

.trade-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trade-tag {
  padding: 4px 10px;
  font-size: 0.75rem;
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
  border-radius: 9999px;
}

/* ===== Export Modal ===== */
.export-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.export-info {
  padding: 12px;
  background: var(--kite-table-header);
  border-radius: 4px;
}

.export-info p {
  font-size: 0.875rem;
  margin-bottom: 4px;
}

.export-info p:last-child {
  margin-bottom: 0;
}

.export-format {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.format-options {
  display: flex;
  gap: 16px;
}

.format-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.format-option input {
  cursor: pointer;
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

/* ===== Loading State ===== */
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

/* ===== Empty State ===== */
.empty-state {
  padding: 48px;
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
  display: inline-flex;
  align-items: center;
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

.link-btn {
  font-size: 0.875rem;
  color: var(--kite-blue);
  background: none;
  border: none;
  cursor: pointer;
}

.link-btn:hover {
  color: var(--kite-blue-dark, #1565c0);
  text-decoration: underline;
}

/* ===== Cumulative Chart ===== */
.chart-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  margin-bottom: 24px;
}

.chart-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 16px;
}

.chart-container {
  min-height: 120px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  color: var(--kite-text-secondary);
}

.cumulative-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 100px;
  padding: 0 4px;
}

.chart-bar-wrapper {
  flex: 1;
  min-width: 4px;
  max-width: 20px;
  height: 100%;
  display: flex;
  align-items: flex-end;
}

.chart-bar {
  width: 100%;
  min-height: 4px;
  border-radius: 2px 2px 0 0;
  transition: height 0.3s ease;
}

.bar-positive {
  background: var(--kite-green);
}

.bar-negative {
  background: var(--kite-red);
}

.bar-neutral {
  background: var(--kite-blue);
}

.chart-summary {
  text-align: center;
  font-weight: 600;
}

/* ===== Trade P&L Chart ===== */
.trade-pnl-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pnl-bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pnl-bar-label {
  width: 50px;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.pnl-bar-track {
  flex: 1;
  height: 28px;
  background: var(--kite-table-header);
  border-radius: 4px;
  overflow: hidden;
}

.pnl-bar-fill {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 8px;
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
  min-width: fit-content;
  transition: width 0.3s ease;
}

.pnl-result {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--kite-border-light);
}

.pnl-result-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.pnl-result-value {
  font-size: 1rem;
  font-weight: 600;
}

/* ===== Editable Notes ===== */
.notes-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
}

.notes-textarea:focus {
  outline: none;
  border-color: var(--kite-blue);
}

.save-notes-btn {
  margin-top: 8px;
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  background: var(--kite-blue);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.save-notes-btn:hover:not(:disabled) {
  background: var(--kite-blue-dark, #1565c0);
}

.save-notes-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== Sortable Header ===== */
.sortable-header {
  cursor: pointer;
  user-select: none;
}

.sortable-header:hover {
  color: var(--kite-blue);
}

.sort-indicator {
  margin-left: 4px;
}
</style>
