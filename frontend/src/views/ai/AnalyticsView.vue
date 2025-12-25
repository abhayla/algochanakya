<template>
  <KiteLayout>
    <AISubNav />
    <div class="analytics-view" data-testid="analytics-view">
    <div class="page-header">
      <h1 class="page-title">AI Performance Analytics</h1>
      <div class="header-actions">
        <button class="btn-date-range" @click="showDatePicker = !showDatePicker" data-testid="btn-date-range">
          <i class="fas fa-calendar"></i>
          {{ dateRangeLabel }}
        </button>
        <button class="btn-refresh" @click="refreshData" :disabled="loading" data-testid="btn-refresh">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
          Refresh
        </button>
      </div>
    </div>

    <!-- Date Range Picker (Simple) -->
    <div v-if="showDatePicker" class="date-picker-dropdown" data-testid="date-picker">
      <div class="date-picker-presets">
        <button @click="selectDateRange(7)" class="preset-btn">Last 7 Days</button>
        <button @click="selectDateRange(30)" class="preset-btn">Last 30 Days</button>
        <button @click="selectDateRange(90)" class="preset-btn">Last 90 Days</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i>
      <p>Loading analytics...</p>
    </div>

    <div v-else class="analytics-content">
      <!-- Performance Summary Section -->
      <section class="section-summary">
        <h2 class="section-title">Performance Summary</h2>
        <div class="summary-grid">
          <div class="summary-card" data-testid="summary-total-pnl">
            <div class="card-icon profit">
              <i class="fas fa-chart-line"></i>
            </div>
            <div class="card-content">
              <div class="card-value" :class="totalPnlClass">{{ formatCurrency(performanceMetrics.total_pnl) }}</div>
              <div class="card-label">Total P&L</div>
            </div>
          </div>

          <div class="summary-card" data-testid="summary-win-rate">
            <div class="card-icon">
              <i class="fas fa-percentage"></i>
            </div>
            <div class="card-content">
              <div class="card-value">{{ performanceMetrics.win_rate.toFixed(1) }}%</div>
              <div class="card-label">Win Rate</div>
            </div>
          </div>

          <div class="summary-card" data-testid="summary-trades">
            <div class="card-icon">
              <i class="fas fa-exchange-alt"></i>
            </div>
            <div class="card-content">
              <div class="card-value">{{ performanceMetrics.total_trades }}</div>
              <div class="card-label">Total Trades</div>
              <div class="card-detail">{{ performanceMetrics.winning_trades }}W / {{ performanceMetrics.losing_trades }}L</div>
            </div>
          </div>

          <div class="summary-card" data-testid="summary-sharpe">
            <div class="card-icon">
              <i class="fas fa-chart-bar"></i>
            </div>
            <div class="card-content">
              <div class="card-value">{{ performanceMetrics.sharpe_ratio?.toFixed(2) || 'N/A' }}</div>
              <div class="card-label">Sharpe Ratio</div>
            </div>
          </div>

          <div class="summary-card" data-testid="summary-avg-score">
            <div class="card-icon">
              <i class="fas fa-star"></i>
            </div>
            <div class="card-content">
              <div class="card-value" :class="scoreClass">{{ performanceMetrics.avg_decision_score.toFixed(1) }}</div>
              <div class="card-label">Avg Decision Quality</div>
            </div>
          </div>

          <div class="summary-card" data-testid="summary-avg-pnl">
            <div class="card-icon">
              <i class="fas fa-coins"></i>
            </div>
            <div class="card-content">
              <div class="card-value" :class="avgPnlClass">{{ formatCurrency(performanceMetrics.avg_pnl_per_trade) }}</div>
              <div class="card-label">Avg P&L per Trade</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Charts Grid -->
      <div class="charts-grid">
        <!-- Decision Quality Trend -->
        <section class="chart-section">
          <h2 class="section-title">Decision Quality Trend</h2>
          <div class="chart-container" data-testid="chart-quality-trend">
            <canvas ref="qualityTrendChart"></canvas>
          </div>
        </section>

        <!-- Learning Progress -->
        <section class="chart-section">
          <h2 class="section-title">ML Model Progress</h2>
          <div class="learning-stats" data-testid="learning-stats">
            <div class="stat-row">
              <span class="stat-label">Model Version:</span>
              <span class="stat-value">{{ learningProgress.model_version }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Accuracy:</span>
              <span class="stat-value">{{ (learningProgress.accuracy * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Precision:</span>
              <span class="stat-value">{{ (learningProgress.precision * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Recall:</span>
              <span class="stat-value">{{ (learningProgress.recall * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">F1 Score:</span>
              <span class="stat-value">{{ (learningProgress.f1_score * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Training Samples:</span>
              <span class="stat-value">{{ learningProgress.total_training_samples }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Trend:</span>
              <span class="stat-value" :class="trendClass">
                <i :class="trendIcon"></i>
                {{ learningProgress.performance_trend }}
              </span>
            </div>
          </div>
        </section>
      </div>

      <!-- Regime Performance Section -->
      <section class="section-table">
        <h2 class="section-title">Performance by Market Regime</h2>
        <div class="table-container">
          <table class="performance-table" data-testid="regime-table">
            <thead>
              <tr>
                <th>Regime</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Avg P&L</th>
                <th>Total P&L</th>
                <th>Avg Score</th>
                <th>Best Strategy</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="regime in regimePerformance" :key="regime.regime_type">
                <td>
                  <span class="regime-badge" :class="regimeBadgeClass(regime.regime_type)">
                    {{ regime.regime_type }}
                  </span>
                </td>
                <td>{{ regime.trades_count }}</td>
                <td>{{ regime.win_rate.toFixed(1) }}%</td>
                <td :class="pnlClass(regime.avg_pnl)">{{ formatCurrency(regime.avg_pnl) }}</td>
                <td :class="pnlClass(regime.total_pnl)">{{ formatCurrency(regime.total_pnl) }}</td>
                <td>{{ regime.avg_score.toFixed(1) }}</td>
                <td>{{ regime.best_strategy || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Strategy Performance Section -->
      <section class="section-table">
        <h2 class="section-title">Performance by Strategy</h2>
        <div class="table-container">
          <table class="performance-table" data-testid="strategy-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Avg P&L</th>
                <th>Total P&L</th>
                <th>Avg Score</th>
                <th>Best Regime</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="strategy in strategyPerformance" :key="strategy.strategy_name">
                <td><strong>{{ strategy.strategy_name }}</strong></td>
                <td>{{ strategy.trades_count }}</td>
                <td>{{ strategy.win_rate.toFixed(1) }}%</td>
                <td :class="pnlClass(strategy.avg_pnl)">{{ formatCurrency(strategy.avg_pnl) }}</td>
                <td :class="pnlClass(strategy.total_pnl)">{{ formatCurrency(strategy.total_pnl) }}</td>
                <td>{{ strategy.avg_score.toFixed(1) }}</td>
                <td>{{ strategy.best_regime || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
    </div>
  </KiteLayout>
</template>

<script setup>
import KiteLayout from '@/components/layout/KiteLayout.vue'
import AISubNav from '@/components/ai/AISubNav.vue'

import { ref, computed, onMounted, watch, nextTick } from 'vue'
import Chart from 'chart.js/auto'
import { useToast } from '@/composables/useToast'
import api from '@/services/api'

const { showToast } = useToast()

// State
const loading = ref(false)
const showDatePicker = ref(false)
const dateRange = ref(30) // days

const performanceMetrics = ref({
  total_trades: 0,
  winning_trades: 0,
  losing_trades: 0,
  win_rate: 0,
  total_pnl: 0,
  avg_pnl_per_trade: 0,
  max_win: 0,
  max_loss: 0,
  avg_decision_score: 0,
  sharpe_ratio: null,
  total_days_active: 0,
  last_trade_date: null
})

const regimePerformance = ref([])
const strategyPerformance = ref([])
const decisionQuality = ref([])
const learningProgress = ref({
  model_version: 'N/A',
  trained_at: null,
  accuracy: 0,
  precision: 0,
  recall: 0,
  f1_score: 0,
  total_training_samples: 0,
  performance_trend: 'unknown'
})

// Chart instances
const qualityTrendChart = ref(null)
let qualityChartInstance = null

// Computed
const dateRangeLabel = computed(() => {
  return `Last ${dateRange.value} Days`
})

const totalPnlClass = computed(() => {
  return performanceMetrics.value.total_pnl >= 0 ? 'profit' : 'loss'
})

const avgPnlClass = computed(() => {
  return performanceMetrics.value.avg_pnl_per_trade >= 0 ? 'profit' : 'loss'
})

const scoreClass = computed(() => {
  const score = performanceMetrics.value.avg_decision_score
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-ok'
  return 'score-bad'
})

const trendClass = computed(() => {
  const trend = learningProgress.value.performance_trend
  if (trend === 'improving') return 'trend-up'
  if (trend === 'declining') return 'trend-down'
  return ''
})

const trendIcon = computed(() => {
  const trend = learningProgress.value.performance_trend
  if (trend === 'improving') return 'fas fa-arrow-up'
  if (trend === 'declining') return 'fas fa-arrow-down'
  return 'fas fa-minus'
})

// Methods
const formatCurrency = (value) => {
  if (!value) value = 0
  const sign = value >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(value).toFixed(2)}`
}

const pnlClass = (value) => {
  return value >= 0 ? 'profit' : 'loss'
}

const regimeBadgeClass = (regimeType) => {
  const map = {
    'TRENDING_BULLISH': 'regime-bullish',
    'TRENDING_BEARISH': 'regime-bearish',
    'RANGEBOUND': 'regime-rangebound',
    'VOLATILE': 'regime-volatile',
    'PRE_EVENT': 'regime-event',
    'EVENT_DAY': 'regime-event'
  }
  return map[regimeType] || ''
}

const selectDateRange = (days) => {
  dateRange.value = days
  showDatePicker.value = false
  refreshData()
}

const refreshData = async () => {
  loading.value = true

  try {
    // Calculate date range
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - dateRange.value * 24 * 60 * 60 * 1000)
      .toISOString().split('T')[0]

    // Fetch all analytics data in parallel
    const [metrics, regimes, strategies, quality, learning] = await Promise.all([
      api.get(`/api/v1/ai/analytics/performance?start_date=${startDate}&end_date=${endDate}`),
      api.get(`/api/v1/ai/analytics/by-regime?start_date=${startDate}&end_date=${endDate}`),
      api.get(`/api/v1/ai/analytics/by-strategy?start_date=${startDate}&end_date=${endDate}`),
      api.get(`/api/v1/ai/analytics/decisions?start_date=${startDate}&end_date=${endDate}`),
      api.get('/api/v1/ai/analytics/learning')
    ])

    performanceMetrics.value = metrics.data
    regimePerformance.value = regimes.data
    strategyPerformance.value = strategies.data
    decisionQuality.value = quality.data
    learningProgress.value = learning.data

    // Update chart
    await nextTick()
    updateQualityChart()

  } catch (error) {
    console.error('Error fetching analytics:', error)
    showToast('Failed to load analytics data', 'error')
  } finally {
    loading.value = false
  }
}

const updateQualityChart = () => {
  if (!qualityTrendChart.value) return

  const ctx = qualityTrendChart.value.getContext('2d')

  // Destroy existing chart
  if (qualityChartInstance) {
    qualityChartInstance.destroy()
  }

  // Create new chart
  qualityChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: decisionQuality.value.map(d => d.date),
      datasets: [{
        label: 'Decision Quality Score',
        data: decisionQuality.value.map(d => d.avg_score),
        borderColor: 'rgb(56, 126, 209)',
        backgroundColor: 'rgba(56, 126, 209, 0.1)',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          title: {
            display: true,
            text: 'Score (0-100)'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        }
      }
    }
  })
}

// Lifecycle
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.analytics-view {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn-date-range,
.btn-refresh {
  padding: 8px 16px;
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  color: var(--kite-text-primary, #394046);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-date-range:hover,
.btn-refresh:hover {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-primary, #387ed1);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.date-picker-dropdown {
  position: absolute;
  right: 24px;
  top: 80px;
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 8px;
  z-index: 100;
}

.date-picker-presets {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preset-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  font-size: 14px;
  transition: all 0.2s ease;
}

.preset-btn:hover {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-primary, #387ed1);
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--kite-text-secondary, #666);
}

.loading-state i {
  font-size: 36px;
  margin-bottom: 12px;
}

.analytics-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0 0 16px 0;
}

/* Summary Grid */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.summary-card {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  gap: 16px;
  align-items: center;
}

.card-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(56, 126, 209, 0.1);
  color: var(--kite-primary, #387ed1);
  font-size: 20px;
}

.card-icon.profit {
  background: rgba(0, 179, 134, 0.1);
  color: var(--kite-green, #00b386);
}

.card-content {
  flex: 1;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 4px;
}

.card-value.profit {
  color: var(--kite-green, #00b386);
}

.card-value.loss {
  color: var(--kite-red, #e53935);
}

.card-value.score-good {
  color: var(--kite-green, #00b386);
}

.card-value.score-ok {
  color: #ff9800;
}

.card-value.score-bad {
  color: var(--kite-red, #e53935);
}

.card-label {
  font-size: 13px;
  color: var(--kite-text-secondary, #666);
}

.card-detail {
  font-size: 12px;
  color: var(--kite-text-secondary, #999);
  margin-top: 2px;
}

/* Charts Grid */
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

@media (max-width: 1024px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

.chart-section {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
}

.chart-container {
  height: 300px;
}

.learning-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: 14px;
  color: var(--kite-text-secondary, #666);
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

.trend-up {
  color: var(--kite-green, #00b386);
}

.trend-down {
  color: var(--kite-red, #e53935);
}

/* Tables */
.section-table {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
}

.table-container {
  overflow-x: auto;
}

.performance-table {
  width: 100%;
  border-collapse: collapse;
}

.performance-table th {
  text-align: left;
  padding: 12px;
  border-bottom: 2px solid var(--kite-border, #e8e8e8);
  font-size: 13px;
  font-weight: 600;
  color: var(--kite-text-secondary, #666);
}

.performance-table td {
  padding: 12px;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
  font-size: 14px;
}

.performance-table tbody tr:hover {
  background: var(--kite-bg-light, #f8f9fa);
}

.regime-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.regime-bullish {
  background: rgba(0, 179, 134, 0.1);
  color: var(--kite-green, #00b386);
}

.regime-bearish {
  background: rgba(229, 57, 53, 0.1);
  color: var(--kite-red, #e53935);
}

.regime-rangebound {
  background: rgba(56, 126, 209, 0.1);
  color: var(--kite-primary, #387ed1);
}

.regime-volatile {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}

.regime-event {
  background: rgba(156, 39, 176, 0.1);
  color: #9c27b0;
}
</style>
