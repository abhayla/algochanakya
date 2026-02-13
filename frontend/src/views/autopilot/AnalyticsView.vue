<script setup>
/**
 * AutoPilot Analytics Dashboard View
 *
 * Phase 4: Performance analytics with charts, metrics, and insights.
 */
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/styles/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

// Date range filter
const dateRange = ref({
  startDate: null,
  endDate: null
})

// Quick date range presets
const datePreset = ref('30d')

// Loading states
const loading = ref(false)

// Chart hover tooltip state
const hoveredBar = ref(null)
const tooltipPosition = ref({ x: 0, y: 0 })

// Export modal state
const showExportModal = ref(false)
const exportFormat = ref('pdf')
const exporting = ref(false)

// Strategy details modal state
const showStrategyModal = ref(false)
const selectedStrategy = ref(null)

// Trade data from store (for distribution chart)
const trades = computed(() => store.analyticsTrades || [])

// Analytics data
const performance = computed(() => store.analyticsPerformance || {})
const dailyPnL = computed(() => store.analyticsDailyPnL || [])
const byStrategy = computed(() => store.analyticsByStrategy || [])
const byWeekday = computed(() => store.analyticsByWeekday || [])
const drawdown = computed(() => store.analyticsDrawdown || {})

// Calculate max P&L for chart scaling
const maxDailyPnL = computed(() => {
  if (!dailyPnL.value.length) return 0
  return Math.max(...dailyPnL.value.map(d => Math.abs(d.pnl)))
})

// Trade distribution - P&L buckets for histogram
const tradeDistribution = computed(() => {
  if (!trades.value.length) return []

  const pnlValues = trades.value.map(t => t.pnl || 0)
  const minPnl = Math.min(...pnlValues)
  const maxPnl = Math.max(...pnlValues)

  // Create buckets based on data range
  const range = maxPnl - minPnl
  const bucketSize = range > 0 ? Math.ceil(range / 8) : 1000 // 8 buckets
  const roundedBucketSize = Math.ceil(bucketSize / 1000) * 1000 // Round to nearest 1000

  const buckets = []
  const startBucket = Math.floor(minPnl / roundedBucketSize) * roundedBucketSize
  const endBucket = Math.ceil(maxPnl / roundedBucketSize) * roundedBucketSize

  for (let start = startBucket; start < endBucket; start += roundedBucketSize) {
    const end = start + roundedBucketSize
    const count = pnlValues.filter(p => p >= start && p < end).length
    buckets.push({
      label: `${formatBucketLabel(start)} to ${formatBucketLabel(end)}`,
      start,
      end,
      count,
      percentage: (count / pnlValues.length) * 100
    })
  }

  return buckets
})

// Max count for distribution chart scaling
const maxDistributionCount = computed(() => {
  if (!tradeDistribution.value.length) return 0
  return Math.max(...tradeDistribution.value.map(b => b.count))
})

// Format bucket labels (e.g., -5k, 0, 5k, 10k)
const formatBucketLabel = (value) => {
  if (value === 0) return '0'
  const absValue = Math.abs(value)
  if (absValue >= 100000) return `${value > 0 ? '' : '-'}${(absValue / 100000).toFixed(0)}L`
  if (absValue >= 1000) return `${value > 0 ? '' : '-'}${(absValue / 1000).toFixed(0)}k`
  return value.toString()
}

// Preset options
const presetOptions = [
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: '90d', label: 'Last 90 Days' },
  { value: 'mtd', label: 'Month to Date' },
  { value: 'ytd', label: 'Year to Date' },
  { value: 'custom', label: 'Custom Range' }
]

// Calculate date range from preset
const calculateDateRange = (preset) => {
  const today = new Date()
  let startDate = new Date()

  switch (preset) {
    case '7d':
      startDate.setDate(today.getDate() - 7)
      break
    case '30d':
      startDate.setDate(today.getDate() - 30)
      break
    case '90d':
      startDate.setDate(today.getDate() - 90)
      break
    case 'mtd':
      startDate = new Date(today.getFullYear(), today.getMonth(), 1)
      break
    case 'ytd':
      startDate = new Date(today.getFullYear(), 0, 1)
      break
    case 'custom':
      return // Don't auto-set for custom
  }

  dateRange.value.startDate = startDate.toISOString().split('T')[0]
  dateRange.value.endDate = today.toISOString().split('T')[0]
}

// Fetch all analytics data
const fetchAnalytics = async () => {
  loading.value = true
  try {
    await Promise.all([
      store.fetchAnalyticsPerformance({
        start_date: dateRange.value.startDate,
        end_date: dateRange.value.endDate
      }),
      store.fetchDailyPnL({
        start_date: dateRange.value.startDate,
        end_date: dateRange.value.endDate
      }),
      store.fetchAnalyticsByStrategy({
        start_date: dateRange.value.startDate,
        end_date: dateRange.value.endDate
      }),
      store.fetchAnalyticsByWeekday({
        start_date: dateRange.value.startDate,
        end_date: dateRange.value.endDate
      }),
      store.fetchAnalyticsDrawdown({
        start_date: dateRange.value.startDate,
        end_date: dateRange.value.endDate
      })
    ])
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  calculateDateRange('30d')
  fetchAnalytics()
})

// Watch preset changes
watch(datePreset, (newPreset) => {
  if (newPreset !== 'custom') {
    calculateDateRange(newPreset)
    fetchAnalytics()
  }
})

// Watch custom date changes
watch(
  () => [dateRange.value.startDate, dateRange.value.endDate],
  () => {
    if (datePreset.value === 'custom') {
      fetchAnalytics()
    }
  }
)

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
    month: 'short'
  })
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getBarHeight = (value) => {
  if (!maxDailyPnL.value) return 0
  return (Math.abs(value) / maxDailyPnL.value) * 100
}

const getWeekdayName = (day) => {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
  return days[day] || day
}

const navigateToDashboard = () => {
  router.push('/autopilot')
}

const navigateToReports = () => {
  router.push('/autopilot/reports')
}

const navigateToJournal = () => {
  router.push('/autopilot/journal')
}

// Chart hover handlers
const handleBarHover = (event, day, index) => {
  hoveredBar.value = { day, index }
  const rect = event.target.getBoundingClientRect()
  tooltipPosition.value = {
    x: rect.left + rect.width / 2,
    y: rect.top - 10
  }
}

const handleBarLeave = () => {
  hoveredBar.value = null
}

// Strategy details modal
const openStrategyDetails = (strategy) => {
  selectedStrategy.value = strategy
  showStrategyModal.value = true
}

const closeStrategyModal = () => {
  showStrategyModal.value = false
  selectedStrategy.value = null
}

// Export modal handlers
const openExportModal = () => {
  showExportModal.value = true
}

const closeExportModal = () => {
  showExportModal.value = false
  exportFormat.value = 'pdf'
}

const handleExport = async () => {
  exporting.value = true
  try {
    // Call store export action based on format
    await store.exportAnalytics({
      format: exportFormat.value,
      start_date: dateRange.value.startDate,
      end_date: dateRange.value.endDate
    })
    closeExportModal()
  } catch (error) {
    console.error('Export failed:', error)
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <KiteLayout>
    <div class="analytics-dashboard" data-testid="autopilot-analytics-page">
      <!-- Header -->
      <div class="analytics-header" data-testid="autopilot-analytics-header">
        <div>
          <div class="header-breadcrumb">
            <button @click="navigateToDashboard" class="breadcrumb-link">AutoPilot</button>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">Analytics</span>
          </div>
          <h1 class="analytics-title">Performance Analytics</h1>
          <p class="analytics-subtitle">Track your trading performance and insights</p>
        </div>
        <div class="analytics-actions">
          <button
            @click="navigateToJournal"
            class="strategy-btn strategy-btn-outline"
            data-testid="autopilot-analytics-journal-btn"
          >
            Trade Journal
          </button>
          <button
            @click="navigateToReports"
            class="strategy-btn strategy-btn-outline"
            data-testid="autopilot-analytics-reports-btn"
          >
            Reports
          </button>
          <button
            @click="openExportModal"
            class="strategy-btn strategy-btn-outline"
            data-testid="autopilot-analytics-export-btn"
          >
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
            </svg>
            Export
          </button>
          <button
            @click="fetchAnalytics"
            class="icon-btn"
            data-testid="autopilot-analytics-refresh-btn"
          >
            <svg class="icon-svg-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- Date Range Filter -->
      <div class="date-filter-section" data-testid="autopilot-analytics-date-range">
        <div class="preset-buttons">
          <button
            v-for="preset in presetOptions"
            :key="preset.value"
            @click="datePreset = preset.value"
            :class="['preset-btn', { active: datePreset === preset.value }]"
            :data-testid="`autopilot-analytics-range-${preset.value}`"
          >
            {{ preset.label }}
          </button>
        </div>
        <div v-if="datePreset === 'custom'" class="custom-date-range">
          <input
            v-model="dateRange.startDate"
            type="date"
            class="filter-input date-input"
            data-testid="autopilot-analytics-start-date"
          />
          <span class="date-separator">to</span>
          <input
            v-model="dateRange.endDate"
            type="date"
            class="filter-input date-input"
            data-testid="autopilot-analytics-end-date"
          />
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p class="loading-text">Loading analytics...</p>
      </div>

      <template v-else>
        <!-- Key Metrics Cards -->
        <div class="metrics-cards" data-testid="autopilot-analytics-summary">
          <div class="metric-card" data-testid="autopilot-analytics-total-pnl">
            <p class="metric-label">Net P&L</p>
            <p class="metric-value" :class="getPnLClass(performance.net_pnl)">
              {{ formatCurrency(performance.net_pnl) }}
            </p>
            <p class="metric-secondary">
              {{ performance.total_trades || 0 }} trades
            </p>
          </div>

          <div class="metric-card" data-testid="autopilot-analytics-win-rate">
            <p class="metric-label">Win Rate</p>
            <p class="metric-value" :class="(performance.win_rate || 0) >= 50 ? 'pnl-profit' : 'pnl-loss'">
              {{ (performance.win_rate || 0).toFixed(1) }}%
            </p>
            <div class="win-rate-visual">
              <div class="win-rate-bar">
                <div
                  class="win-rate-fill"
                  :style="{ width: (performance.win_rate || 0) + '%' }"
                ></div>
              </div>
              <span class="win-rate-text">
                {{ performance.winning_trades || 0 }}W / {{ performance.losing_trades || 0 }}L
              </span>
            </div>
          </div>

          <div class="metric-card" data-testid="autopilot-analytics-profit-factor">
            <p class="metric-label">Profit Factor</p>
            <p class="metric-value" :class="(performance.profit_factor || 0) >= 1 ? 'pnl-profit' : 'pnl-loss'">
              {{ (performance.profit_factor || 0).toFixed(2) }}
            </p>
            <p class="metric-secondary">
              Risk/Reward Ratio
            </p>
          </div>

          <div class="metric-card" data-testid="autopilot-analytics-max-drawdown">
            <p class="metric-label">Max Drawdown</p>
            <p class="metric-value pnl-loss">
              {{ formatPercent(-(drawdown.max_drawdown_pct || 0)) }}
            </p>
            <p class="metric-secondary">
              {{ formatCurrency(drawdown.max_drawdown) }}
            </p>
          </div>

          <div class="metric-card" data-testid="autopilot-analytics-avg-profit">
            <p class="metric-label">Avg Win</p>
            <p class="metric-value pnl-profit">
              {{ formatCurrency(performance.avg_win) }}
            </p>
            <p class="metric-secondary">
              {{ performance.winning_trades || 0 }} winning trades
            </p>
          </div>

          <div class="metric-card" data-testid="autopilot-analytics-avg-loss">
            <p class="metric-label">Avg Loss</p>
            <p class="metric-value pnl-loss">
              {{ formatCurrency(performance.avg_loss) }}
            </p>
            <p class="metric-secondary">
              {{ performance.losing_trades || 0 }} losing trades
            </p>
          </div>
        </div>

        <!-- Daily P&L Chart -->
        <div class="chart-card" data-testid="autopilot-analytics-daily-pnl-chart">
          <div class="chart-header">
            <h2 class="section-title">Daily P&L</h2>
            <div class="chart-legend">
              <span class="legend-item">
                <span class="legend-dot legend-profit"></span>
                Profit
              </span>
              <span class="legend-item">
                <span class="legend-dot legend-loss"></span>
                Loss
              </span>
            </div>
          </div>

          <div v-if="dailyPnL.length === 0" class="chart-empty">
            No trading data for the selected period
          </div>

          <div v-else class="daily-pnl-chart">
            <div class="chart-container">
              <div
                v-for="(day, index) in dailyPnL"
                :key="day.date"
                class="chart-bar-wrapper"
                :data-testid="`autopilot-analytics-daily-pnl-bar-${index}`"
              >
                <div class="chart-bar-container">
                  <!-- Profit bar (above zero line) -->
                  <div class="chart-bar-positive">
                    <div
                      v-if="day.pnl > 0"
                      class="chart-bar bar-profit"
                      :style="{ height: getBarHeight(day.pnl) + '%' }"
                      @mouseenter="(e) => handleBarHover(e, day, index)"
                      @mouseleave="handleBarLeave"
                    ></div>
                  </div>
                  <!-- Zero line -->
                  <div class="chart-zero-line"></div>
                  <!-- Loss bar (below zero line) -->
                  <div class="chart-bar-negative">
                    <div
                      v-if="day.pnl < 0"
                      class="chart-bar bar-loss"
                      :style="{ height: getBarHeight(day.pnl) + '%' }"
                      @mouseenter="(e) => handleBarHover(e, day, index)"
                      @mouseleave="handleBarLeave"
                    ></div>
                  </div>
                </div>
                <span class="chart-bar-label">{{ formatDate(day.date) }}</span>
              </div>
            </div>
            <!-- Chart Tooltip -->
            <Teleport to="body">
              <div
                v-if="hoveredBar"
                class="chart-tooltip"
                :style="{
                  left: tooltipPosition.x + 'px',
                  top: tooltipPosition.y + 'px'
                }"
                data-testid="autopilot-analytics-chart-tooltip"
              >
                <div class="tooltip-date">{{ formatDate(hoveredBar.day.date) }}</div>
                <div class="tooltip-pnl" :class="getPnLClass(hoveredBar.day.pnl)">
                  {{ formatCurrency(hoveredBar.day.pnl) }}
                </div>
                <div class="tooltip-trades" v-if="hoveredBar.day.trades">
                  {{ hoveredBar.day.trades }} trades
                </div>
              </div>
            </Teleport>
          </div>
        </div>

        <!-- Two column layout for strategy and weekday breakdown -->
        <div class="analytics-grid">
          <!-- Performance by Strategy -->
          <div class="chart-card" data-testid="autopilot-analytics-strategy-breakdown">
            <div class="chart-header">
              <h2 class="section-title">By Strategy</h2>
            </div>

            <div v-if="byStrategy.length === 0" class="chart-empty">
              No strategy data available
            </div>

            <div v-else class="strategy-breakdown">
              <div
                v-for="strategy in byStrategy"
                :key="strategy.strategy_id"
                class="strategy-row strategy-row-clickable"
                :data-testid="`autopilot-analytics-strategy-row-${strategy.strategy_id}`"
                @click="openStrategyDetails(strategy)"
              >
                <div class="strategy-info">
                  <span class="strategy-name">{{ strategy.strategy_name }}</span>
                  <span class="strategy-trades">{{ strategy.total_trades }} trades</span>
                </div>
                <div class="strategy-stats">
                  <span :class="['strategy-pnl', getPnLClass(strategy.net_pnl)]">
                    {{ formatCurrency(strategy.net_pnl) }}
                  </span>
                  <span :class="['strategy-winrate', strategy.win_rate >= 50 ? 'pnl-profit' : 'pnl-loss']">
                    {{ strategy.win_rate.toFixed(0) }}%
                  </span>
                </div>
                <div class="strategy-bar">
                  <div
                    class="strategy-bar-fill"
                    :class="strategy.net_pnl >= 0 ? 'fill-profit' : 'fill-loss'"
                    :style="{ width: Math.min(Math.abs(strategy.contribution_pct || 0), 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Performance by Weekday -->
          <div class="chart-card" data-testid="autopilot-analytics-weekday-chart">
            <div class="chart-header">
              <h2 class="section-title">By Weekday</h2>
            </div>

            <div v-if="byWeekday.length === 0" class="chart-empty">
              No weekday data available
            </div>

            <div v-else class="weekday-breakdown">
              <div
                v-for="day in byWeekday"
                :key="day.weekday"
                class="weekday-row"
              >
                <div class="weekday-info">
                  <span class="weekday-name">{{ getWeekdayName(day.weekday) }}</span>
                  <span class="weekday-trades">{{ day.total_trades }} trades</span>
                </div>
                <div class="weekday-stats">
                  <span :class="['weekday-pnl', getPnLClass(day.net_pnl)]">
                    {{ formatCurrency(day.net_pnl) }}
                  </span>
                  <span :class="['weekday-winrate', day.win_rate >= 50 ? 'pnl-profit' : 'pnl-loss']">
                    {{ day.win_rate.toFixed(0) }}%
                  </span>
                </div>
                <div class="weekday-bar">
                  <div
                    class="weekday-bar-fill"
                    :class="day.net_pnl >= 0 ? 'fill-profit' : 'fill-loss'"
                    :style="{ width: Math.min(day.win_rate, 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Drawdown Analysis -->
        <div class="chart-card" data-testid="autopilot-analytics-drawdown">
          <div class="chart-header">
            <h2 class="section-title">Drawdown Analysis</h2>
          </div>

          <div class="drawdown-stats">
            <div class="drawdown-stat">
              <span class="drawdown-label">Maximum Drawdown</span>
              <span class="drawdown-value pnl-loss">
                {{ formatCurrency(drawdown.max_drawdown) }}
                ({{ formatPercent(-(drawdown.max_drawdown_pct || 0)) }})
              </span>
            </div>
            <div class="drawdown-stat">
              <span class="drawdown-label">Current Drawdown</span>
              <span class="drawdown-value" :class="drawdown.current_drawdown < 0 ? 'pnl-loss' : 'pnl-neutral'">
                {{ formatCurrency(drawdown.current_drawdown) }}
              </span>
            </div>
            <div class="drawdown-stat">
              <span class="drawdown-label">Peak Equity</span>
              <span class="drawdown-value">
                {{ formatCurrency(drawdown.peak_equity) }}
              </span>
            </div>
            <div class="drawdown-stat">
              <span class="drawdown-label">Recovery Status</span>
              <span class="drawdown-value" :class="drawdown.current_drawdown === 0 ? 'pnl-profit' : 'pnl-loss'">
                {{ drawdown.current_drawdown === 0 ? 'At Peak' : 'In Drawdown' }}
              </span>
            </div>
          </div>

          <!-- Equity Curve (simplified) -->
          <div v-if="drawdown.equity_curve && drawdown.equity_curve.length > 0" class="equity-curve">
            <h4 class="curve-title">Equity Curve</h4>
            <div class="curve-container">
              <svg viewBox="0 0 400 100" class="curve-svg">
                <polyline
                  :points="drawdown.equity_curve.map((val, i) =>
                    `${(i / (drawdown.equity_curve.length - 1)) * 400},${100 - ((val - Math.min(...drawdown.equity_curve)) / (Math.max(...drawdown.equity_curve) - Math.min(...drawdown.equity_curve))) * 100}`
                  ).join(' ')"
                  fill="none"
                  stroke="var(--kite-blue)"
                  stroke-width="2"
                />
              </svg>
            </div>
          </div>
        </div>

        <!-- Additional Insights -->
        <div class="insights-section" data-testid="autopilot-analytics-risk-metrics">
          <h2 class="section-title">Insights</h2>
          <div class="insights-grid">
            <div class="insight-card">
              <div class="insight-icon insight-icon-green">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                </svg>
              </div>
              <div class="insight-content">
                <h4 class="insight-title">Best Trading Day</h4>
                <p class="insight-value pnl-profit">
                  {{ performance.best_day ? formatCurrency(performance.best_day.pnl) : 'N/A' }}
                </p>
                <p class="insight-date">
                  {{ performance.best_day ? formatDate(performance.best_day.date) : '-' }}
                </p>
              </div>
            </div>

            <div class="insight-card">
              <div class="insight-icon insight-icon-red">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
                </svg>
              </div>
              <div class="insight-content">
                <h4 class="insight-title">Worst Trading Day</h4>
                <p class="insight-value pnl-loss">
                  {{ performance.worst_day ? formatCurrency(performance.worst_day.pnl) : 'N/A' }}
                </p>
                <p class="insight-date">
                  {{ performance.worst_day ? formatDate(performance.worst_day.date) : '-' }}
                </p>
              </div>
            </div>

            <div class="insight-card">
              <div class="insight-icon insight-icon-blue">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
              </div>
              <div class="insight-content">
                <h4 class="insight-title">Expectancy</h4>
                <p class="insight-value" :class="getPnLClass(performance.expectancy)">
                  {{ formatCurrency(performance.expectancy) }}
                </p>
                <p class="insight-date">per trade</p>
              </div>
            </div>

            <div class="insight-card">
              <div class="insight-icon insight-icon-purple">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div class="insight-content">
                <h4 class="insight-title">Avg Hold Time</h4>
                <p class="insight-value">
                  {{ performance.avg_holding_minutes ? Math.round(performance.avg_holding_minutes) + 'm' : 'N/A' }}
                </p>
                <p class="insight-date">per trade</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Trade Distribution Chart -->
        <div class="chart-card" data-testid="autopilot-analytics-distribution-chart">
          <div class="chart-header">
            <h2 class="section-title">Trade P&L Distribution</h2>
          </div>

          <div v-if="tradeDistribution.length === 0" class="chart-empty">
            No trade data for distribution analysis
          </div>

          <div v-else class="distribution-chart">
            <div
              v-for="(bucket, index) in tradeDistribution"
              :key="index"
              class="distribution-row"
            >
              <span class="distribution-label">{{ bucket.label }}</span>
              <div class="distribution-bar-container">
                <div
                  class="distribution-bar"
                  :class="bucket.start >= 0 ? 'bar-profit' : 'bar-loss'"
                  :style="{ width: (bucket.count / maxDistributionCount * 100) + '%' }"
                ></div>
              </div>
              <span class="distribution-count">{{ bucket.count }} ({{ bucket.percentage.toFixed(1) }}%)</span>
            </div>
          </div>
        </div>
      </template>

      <!-- Export Modal -->
      <Teleport to="body">
        <div
          v-if="showExportModal"
          class="modal-overlay"
          @click.self="closeExportModal"
        >
          <div class="modal-container" data-testid="autopilot-analytics-export-modal">
            <div class="modal-header">
              <h3 class="modal-title">Export Analytics</h3>
              <button @click="closeExportModal" class="modal-close">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <div class="form-group">
                <label class="form-label">Export Format</label>
                <div class="export-formats">
                  <label class="export-option">
                    <input
                      type="radio"
                      v-model="exportFormat"
                      value="pdf"
                      data-testid="autopilot-export-format-pdf"
                    />
                    <span class="export-option-label">
                      <svg class="export-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                      </svg>
                      PDF Report
                    </span>
                  </label>
                  <label class="export-option">
                    <input
                      type="radio"
                      v-model="exportFormat"
                      value="excel"
                      data-testid="autopilot-export-format-excel"
                    />
                    <span class="export-option-label">
                      <svg class="export-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path>
                      </svg>
                      Excel Spreadsheet
                    </span>
                  </label>
                  <label class="export-option">
                    <input
                      type="radio"
                      v-model="exportFormat"
                      value="csv"
                      data-testid="autopilot-export-format-csv"
                    />
                    <span class="export-option-label">
                      <svg class="export-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path>
                      </svg>
                      CSV Data
                    </span>
                  </label>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">Date Range</label>
                <p class="form-hint">
                  {{ dateRange.startDate }} to {{ dateRange.endDate }}
                </p>
              </div>
            </div>
            <div class="modal-footer">
              <button
                @click="closeExportModal"
                class="strategy-btn strategy-btn-outline"
                data-testid="autopilot-export-cancel-btn"
              >
                Cancel
              </button>
              <button
                @click="handleExport"
                class="strategy-btn strategy-btn-primary"
                :disabled="exporting"
                data-testid="autopilot-export-submit-btn"
              >
                {{ exporting ? 'Exporting...' : 'Export' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Strategy Details Modal -->
      <Teleport to="body">
        <div
          v-if="showStrategyModal && selectedStrategy"
          class="modal-overlay"
          @click.self="closeStrategyModal"
        >
          <div class="modal-container modal-lg" data-testid="autopilot-analytics-strategy-details">
            <div class="modal-header">
              <h3 class="modal-title">{{ selectedStrategy.strategy_name }}</h3>
              <button @click="closeStrategyModal" class="modal-close">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <!-- Strategy Performance Summary -->
              <div class="strategy-details-summary">
                <div class="detail-stat">
                  <span class="detail-label">Net P&L</span>
                  <span class="detail-value" :class="getPnLClass(selectedStrategy.net_pnl)">
                    {{ formatCurrency(selectedStrategy.net_pnl) }}
                  </span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Win Rate</span>
                  <span class="detail-value" :class="selectedStrategy.win_rate >= 50 ? 'pnl-profit' : 'pnl-loss'">
                    {{ selectedStrategy.win_rate.toFixed(1) }}%
                  </span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Total Trades</span>
                  <span class="detail-value">{{ selectedStrategy.total_trades }}</span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Winning</span>
                  <span class="detail-value pnl-profit">{{ selectedStrategy.winning_trades || 0 }}</span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Losing</span>
                  <span class="detail-value pnl-loss">{{ selectedStrategy.losing_trades || 0 }}</span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Avg Win</span>
                  <span class="detail-value pnl-profit">{{ formatCurrency(selectedStrategy.avg_win) }}</span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Avg Loss</span>
                  <span class="detail-value pnl-loss">{{ formatCurrency(selectedStrategy.avg_loss) }}</span>
                </div>
                <div class="detail-stat">
                  <span class="detail-label">Profit Factor</span>
                  <span class="detail-value" :class="(selectedStrategy.profit_factor || 0) >= 1 ? 'pnl-profit' : 'pnl-loss'">
                    {{ (selectedStrategy.profit_factor || 0).toFixed(2) }}
                  </span>
                </div>
              </div>

              <!-- Trade History (if available) -->
              <div v-if="selectedStrategy.trades && selectedStrategy.trades.length" class="strategy-trades-section">
                <h4 class="trades-section-title">Recent Trades</h4>
                <div class="trades-table-wrapper">
                  <table class="trades-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th class="text-right">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="trade in selectedStrategy.trades.slice(0, 10)" :key="trade.id">
                        <td>{{ formatDate(trade.entry_time) }}</td>
                        <td>{{ formatCurrency(trade.entry_price) }}</td>
                        <td>{{ formatCurrency(trade.exit_price) }}</td>
                        <td class="text-right" :class="getPnLClass(trade.pnl)">
                          {{ formatCurrency(trade.pnl) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button
                @click="closeStrategyModal"
                class="strategy-btn strategy-btn-outline"
              >
                Close
              </button>
              <button
                @click="router.push(`/autopilot/strategies/${selectedStrategy.strategy_id}`)"
                class="strategy-btn strategy-btn-primary"
              >
                View Full Details
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Error State -->
      <div v-if="store.error" class="error-banner" data-testid="autopilot-analytics-error">
        <p class="error-text">{{ store.error }}</p>
        <button @click="store.clearError" class="error-dismiss">Dismiss</button>
      </div>
    </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.analytics-dashboard {
  padding: 24px;
}

/* ===== Header ===== */
.analytics-header {
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

.analytics-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.analytics-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.analytics-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== Date Filter ===== */
.date-filter-section {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  margin-bottom: 24px;
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  background: white;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  cursor: pointer;
  color: var(--kite-text-primary);
  transition: all 0.15s ease;
}

.preset-btn:hover {
  background: var(--kite-table-hover);
}

.preset-btn.active {
  background: var(--kite-blue);
  color: white;
  border-color: var(--kite-blue);
}

.custom-date-range {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.filter-input {
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
}

.date-input {
  width: 140px;
}

.date-separator {
  color: var(--kite-text-secondary);
}

/* ===== Metrics Cards ===== */
.metrics-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .metrics-cards {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1024px) {
  .metrics-cards {
    grid-template-columns: repeat(6, 1fr);
  }
}

.metric-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
  margin-top: 4px;
}

.metric-secondary {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.win-rate-visual {
  margin-top: 8px;
}

.win-rate-bar {
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

.win-rate-text {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
  display: block;
}

/* ===== Chart Card ===== */
.chart-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.chart-header {
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

.chart-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-profit {
  background: var(--kite-green);
}

.legend-loss {
  background: var(--kite-red);
}

.chart-empty {
  padding: 48px;
  text-align: center;
  color: var(--kite-text-secondary);
}

/* ===== Daily P&L Chart ===== */
.daily-pnl-chart {
  padding: 16px;
  overflow-x: auto;
}

.chart-container {
  display: flex;
  gap: 4px;
  min-height: 200px;
  align-items: center;
}

.chart-bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 24px;
  flex: 1;
}

.chart-bar-container {
  width: 100%;
  height: 160px;
  display: flex;
  flex-direction: column;
}

.chart-bar-positive {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.chart-zero-line {
  height: 1px;
  background: var(--kite-border);
  width: 100%;
}

.chart-bar-negative {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.chart-bar {
  width: 80%;
  max-width: 20px;
  border-radius: 2px;
  transition: height 0.3s ease;
}

.bar-profit {
  background: var(--kite-green);
}

.bar-loss {
  background: var(--kite-red);
}

.chart-bar-label {
  font-size: 0.625rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
  white-space: nowrap;
}

/* ===== Analytics Grid ===== */
.analytics-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .analytics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ===== Strategy Breakdown ===== */
.strategy-breakdown,
.weekday-breakdown {
  padding: 16px;
}

.strategy-row,
.weekday-row {
  padding: 12px 0;
  border-bottom: 1px solid var(--kite-border-light);
}

.strategy-row:last-child,
.weekday-row:last-child {
  border-bottom: none;
}

.strategy-info,
.weekday-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.strategy-name,
.weekday-name {
  font-weight: 500;
  color: var(--kite-text-primary);
}

.strategy-trades,
.weekday-trades {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.strategy-stats,
.weekday-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.strategy-pnl,
.weekday-pnl {
  font-weight: 600;
}

.strategy-winrate,
.weekday-winrate {
  font-size: 0.875rem;
}

.strategy-bar,
.weekday-bar {
  width: 100%;
  height: 4px;
  background: var(--kite-border-light);
  border-radius: 2px;
  overflow: hidden;
}

.strategy-bar-fill,
.weekday-bar-fill {
  height: 4px;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.fill-profit {
  background: var(--kite-green);
}

.fill-loss {
  background: var(--kite-red);
}

/* ===== Drawdown ===== */
.drawdown-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 16px;
}

@media (min-width: 768px) {
  .drawdown-stats {
    grid-template-columns: repeat(4, 1fr);
  }
}

.drawdown-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.drawdown-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.drawdown-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.equity-curve {
  padding: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.curve-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.curve-container {
  width: 100%;
  height: 100px;
}

.curve-svg {
  width: 100%;
  height: 100%;
}

/* ===== Insights ===== */
.insights-section {
  margin-bottom: 24px;
}

.insights-section .section-title {
  margin-bottom: 16px;
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .insights-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.insight-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  display: flex;
  gap: 12px;
}

.insight-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.insight-icon svg {
  width: 20px;
  height: 20px;
}

.insight-icon-green {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.insight-icon-red {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.insight-icon-blue {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.insight-icon-purple {
  background: #f3e5f5;
  color: #7b1fa2;
}

.insight-content {
  flex: 1;
}

.insight-title {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.insight-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.insight-date {
  font-size: 0.75rem;
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

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: 6px;
  vertical-align: middle;
}

/* ===== Chart Tooltip ===== */
.chart-tooltip {
  position: fixed;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.75rem;
  z-index: 1000;
  pointer-events: none;
  transform: translate(-50%, -100%);
  white-space: nowrap;
}

.tooltip-date {
  font-weight: 500;
  margin-bottom: 4px;
}

.tooltip-pnl {
  font-size: 0.875rem;
  font-weight: 600;
}

.tooltip-trades {
  margin-top: 4px;
  opacity: 0.8;
}

/* ===== Trade Distribution Chart ===== */
.distribution-chart {
  padding: 16px;
}

.distribution-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.distribution-label {
  width: 120px;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  text-align: right;
  flex-shrink: 0;
}

.distribution-bar-container {
  flex: 1;
  height: 20px;
  background: var(--kite-border-light);
  border-radius: 4px;
  overflow: hidden;
}

.distribution-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.distribution-count {
  width: 80px;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  flex-shrink: 0;
}

/* ===== Strategy Row Clickable ===== */
.strategy-row-clickable {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.strategy-row-clickable:hover {
  background-color: var(--kite-table-hover);
}

/* ===== Modal Styles ===== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-lg {
  max-width: 640px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--kite-border);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.modal-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: var(--kite-text-secondary);
}

.modal-close:hover {
  color: var(--kite-text-primary);
}

.modal-close svg {
  width: 20px;
  height: 20px;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--kite-border);
}

/* ===== Form Styles ===== */
.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 8px;
}

.form-hint {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Export Format Options ===== */
.export-formats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.export-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.export-option:hover {
  background: var(--kite-table-hover);
}

.export-option input[type="radio"] {
  accent-color: var(--kite-blue);
}

.export-option-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  color: var(--kite-text-primary);
}

.export-icon {
  width: 20px;
  height: 20px;
  color: var(--kite-text-secondary);
}

/* ===== Strategy Details Modal ===== */
.strategy-details-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 480px) {
  .strategy-details-summary {
    grid-template-columns: repeat(4, 1fr);
  }
}

.detail-stat {
  text-align: center;
  padding: 12px;
  background: var(--kite-bg-secondary, #f5f5f5);
  border-radius: 4px;
}

.detail-label {
  display: block;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.detail-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

/* ===== Trades Table in Modal ===== */
.strategy-trades-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border);
}

.trades-section-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.trades-table-wrapper {
  overflow-x: auto;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.trades-table th,
.trades-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--kite-border-light);
}

.trades-table th {
  font-weight: 500;
  color: var(--kite-text-secondary);
  background: var(--kite-bg-secondary, #f5f5f5);
}

.trades-table .text-right {
  text-align: right;
}

/* ===== Primary Button ===== */
.strategy-btn-primary {
  background: var(--kite-blue);
  color: white;
  border-color: var(--kite-blue);
}

.strategy-btn-primary:hover:not(:disabled) {
  background: var(--kite-blue-hover, #1565c0);
}
</style>
