<template>
  <div class="regime-attribution-charts" data-testid="regime-attribution-charts">
    <!-- Header with Export -->
    <div class="charts-header">
      <h2 class="section-title">
        <i class="fas fa-chart-pie"></i>
        Regime Attribution
      </h2>
      <div class="header-actions">
        <button
          class="btn-export"
          @click="exportToCSV"
          :disabled="!regimeData.length"
          data-testid="btn-export-csv"
        >
          <i class="fas fa-download"></i>
          Export CSV
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i>
      <p>Loading regime data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state" data-testid="error-state">
      <i class="fas fa-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <button class="btn-retry" @click="fetchData">Retry</button>
    </div>

    <!-- Charts Grid -->
    <div v-else class="charts-grid">
      <!-- P&L Distribution Pie Chart -->
      <div class="chart-card" data-testid="chart-pnl-distribution">
        <h3 class="chart-title">P&L Distribution by Regime</h3>
        <div class="chart-container">
          <canvas ref="pnlPieChart"></canvas>
        </div>
        <div class="chart-legend">
          <div
            v-for="item in pnlLegendItems"
            :key="item.regime"
            class="legend-item"
          >
            <span class="legend-color" :style="{ background: item.color }"></span>
            <span class="legend-label">{{ item.regime }}</span>
            <span class="legend-value" :class="item.pnl >= 0 ? 'profit' : 'loss'">
              {{ formatCurrency(item.pnl) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Win Rate Bar Chart -->
      <div class="chart-card" data-testid="chart-win-rate">
        <h3 class="chart-title">Win Rate by Regime</h3>
        <div class="chart-container">
          <canvas ref="winRateBarChart"></canvas>
        </div>
      </div>

      <!-- Trades Distribution Donut -->
      <div class="chart-card" data-testid="chart-trades-distribution">
        <h3 class="chart-title">Trades Distribution</h3>
        <div class="chart-container">
          <canvas ref="tradesDonutChart"></canvas>
        </div>
        <div class="chart-summary">
          <div class="summary-item">
            <span class="summary-value">{{ totalTrades }}</span>
            <span class="summary-label">Total Trades</span>
          </div>
          <div class="summary-item">
            <span class="summary-value">{{ activeRegimes }}</span>
            <span class="summary-label">Regimes</span>
          </div>
        </div>
      </div>

      <!-- Score Comparison Radar -->
      <div class="chart-card" data-testid="chart-score-radar">
        <h3 class="chart-title">Performance Scores by Regime</h3>
        <div class="chart-container">
          <canvas ref="scoreRadarChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Insights Section -->
    <div v-if="insights.length > 0" class="insights-section" data-testid="insights-section">
      <h3 class="section-subtitle">
        <i class="fas fa-lightbulb"></i>
        Regime Insights
      </h3>
      <div class="insights-list">
        <div
          v-for="(insight, index) in insights"
          :key="index"
          class="insight-item"
        >
          <i class="fas fa-check-circle"></i>
          <span>{{ insight }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import Chart from 'chart.js/auto'
import api from '@/services/api'

const props = defineProps({
  dateRange: {
    type: Number,
    default: 30
  }
})

const emit = defineEmits(['loaded', 'error'])

// State
const loading = ref(true)
const error = ref(null)
const regimeData = ref([])
const insights = ref([])

// Chart refs
const pnlPieChart = ref(null)
const winRateBarChart = ref(null)
const tradesDonutChart = ref(null)
const scoreRadarChart = ref(null)

// Chart instances
let pnlChartInstance = null
let winRateChartInstance = null
let tradesChartInstance = null
let scoreChartInstance = null

// Colors for regimes
const REGIME_COLORS = {
  'TRENDING_BULLISH': '#00b386',
  'TRENDING_BEARISH': '#e53935',
  'RANGEBOUND': '#387ed1',
  'VOLATILE': '#ff9800',
  'PRE_EVENT': '#9c27b0',
  'EVENT_DAY': '#673ab7'
}

// Computed
const totalTrades = computed(() => {
  return regimeData.value.reduce((sum, r) => sum + (r.trades_count || r.total_trades || 0), 0)
})

const activeRegimes = computed(() => {
  return regimeData.value.filter(r => (r.trades_count || r.total_trades || 0) > 0).length
})

const pnlLegendItems = computed(() => {
  return regimeData.value.map(r => ({
    regime: formatRegimeName(r.regime_type),
    pnl: r.total_pnl || 0,
    color: REGIME_COLORS[r.regime_type] || '#666'
  }))
})

// Methods
const fetchData = async () => {
  loading.value = true
  error.value = null

  try {
    // Fetch regime strengths which includes all regime data
    const response = await api.get('/api/v1/ai/regime-quality/regime-strengths', {
      params: { lookback_days: props.dateRange }
    })

    regimeData.value = response.data.all_regimes || []
    insights.value = response.data.insights || []

    await nextTick()
    renderCharts()

    emit('loaded', regimeData.value)
  } catch (e) {
    console.error('[RegimeCharts] Error fetching data:', e)
    error.value = e.response?.data?.detail || 'Failed to load regime data'
    emit('error', error.value)
  } finally {
    loading.value = false
  }
}

const formatRegimeName = (regimeType) => {
  const names = {
    'TRENDING_BULLISH': 'Bullish',
    'TRENDING_BEARISH': 'Bearish',
    'RANGEBOUND': 'Rangebound',
    'VOLATILE': 'Volatile',
    'PRE_EVENT': 'Pre-Event',
    'EVENT_DAY': 'Event Day'
  }
  return names[regimeType] || regimeType
}

const formatCurrency = (value) => {
  if (!value) value = 0
  const sign = value >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const renderCharts = () => {
  if (!regimeData.value.length) return

  renderPnlPieChart()
  renderWinRateBarChart()
  renderTradesDonutChart()
  renderScoreRadarChart()
}

const renderPnlPieChart = () => {
  if (!pnlPieChart.value) return

  if (pnlChartInstance) pnlChartInstance.destroy()

  const ctx = pnlPieChart.value.getContext('2d')
  const labels = regimeData.value.map(r => formatRegimeName(r.regime_type))
  const data = regimeData.value.map(r => Math.abs(r.total_pnl || r.avg_pnl || 0))
  const colors = regimeData.value.map(r => REGIME_COLORS[r.regime_type] || '#666')

  pnlChartInstance = new Chart(ctx, {
    type: 'pie',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => {
              const regime = regimeData.value[context.dataIndex]
              const pnl = regime.total_pnl || regime.avg_pnl || 0
              return `${context.label}: ${formatCurrency(pnl)}`
            }
          }
        }
      }
    }
  })
}

const renderWinRateBarChart = () => {
  if (!winRateBarChart.value) return

  if (winRateChartInstance) winRateChartInstance.destroy()

  const ctx = winRateBarChart.value.getContext('2d')
  const labels = regimeData.value.map(r => formatRegimeName(r.regime_type))
  const data = regimeData.value.map(r => r.avg_win_rate || r.win_rate || 0)
  const colors = regimeData.value.map(r => REGIME_COLORS[r.regime_type] || '#666')

  winRateChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Win Rate %',
        data,
        backgroundColor: colors,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          title: { display: true, text: 'Win Rate %' }
        }
      }
    }
  })
}

const renderTradesDonutChart = () => {
  if (!tradesDonutChart.value) return

  if (tradesChartInstance) tradesChartInstance.destroy()

  const ctx = tradesDonutChart.value.getContext('2d')
  const labels = regimeData.value.map(r => formatRegimeName(r.regime_type))
  const data = regimeData.value.map(r => r.trades_count || r.total_trades || 0)
  const colors = regimeData.value.map(r => REGIME_COLORS[r.regime_type] || '#666')

  tradesChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '60%',
      plugins: {
        legend: { display: false }
      }
    }
  })
}

const renderScoreRadarChart = () => {
  if (!scoreRadarChart.value) return

  if (scoreChartInstance) scoreChartInstance.destroy()

  const ctx = scoreRadarChart.value.getContext('2d')

  // Build datasets - one for each regime
  const datasets = regimeData.value.slice(0, 4).map((r, i) => ({
    label: formatRegimeName(r.regime_type),
    data: [
      r.avg_score || r.avg_overall_score || 0,
      r.avg_win_rate || r.win_rate || 0,
      Math.min(100, (r.trades_count || r.total_trades || 0) * 2), // Scale trades
    ],
    backgroundColor: `${REGIME_COLORS[r.regime_type]}30`,
    borderColor: REGIME_COLORS[r.regime_type],
    borderWidth: 2,
    pointBackgroundColor: REGIME_COLORS[r.regime_type]
  }))

  scoreChartInstance = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['Avg Score', 'Win Rate', 'Activity'],
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        r: {
          beginAtZero: true,
          max: 100
        }
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 12, padding: 8, font: { size: 11 } }
        }
      }
    }
  })
}

const exportToCSV = () => {
  if (!regimeData.value.length) return

  // Build CSV content
  const headers = ['Regime', 'Trades', 'Win Rate %', 'Avg P&L', 'Total P&L', 'Avg Score']
  const rows = regimeData.value.map(r => [
    r.regime_type,
    r.trades_count || r.total_trades || 0,
    (r.avg_win_rate || r.win_rate || 0).toFixed(1),
    (r.avg_pnl || r.avg_pnl_per_trade || 0).toFixed(2),
    (r.total_pnl || 0).toFixed(2),
    (r.avg_score || r.avg_overall_score || 0).toFixed(1)
  ])

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')

  // Download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  link.setAttribute('href', url)
  link.setAttribute('download', `regime_attribution_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Cleanup charts on unmount
onUnmounted(() => {
  if (pnlChartInstance) pnlChartInstance.destroy()
  if (winRateChartInstance) winRateChartInstance.destroy()
  if (tradesChartInstance) tradesChartInstance.destroy()
  if (scoreChartInstance) scoreChartInstance.destroy()
})

// Watch for date range changes
watch(() => props.dateRange, () => {
  fetchData()
})

// Lifecycle
onMounted(() => {
  fetchData()
})

// Expose for parent
defineExpose({
  refresh: fetchData
})
</script>

<style scoped>
.regime-attribution-charts {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
}

.charts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.section-title i {
  color: var(--kite-primary, #387ed1);
}

.btn-export {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  color: var(--kite-text-primary, #394046);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-export:hover:not(:disabled) {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-primary, #387ed1);
  color: var(--kite-primary, #387ed1);
}

.btn-export:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--kite-text-secondary, #666);
}

.loading-state i,
.error-state i {
  font-size: 32px;
  margin-bottom: 12px;
}

.error-state {
  color: var(--kite-red, #e53935);
}

.btn-retry {
  margin-top: 12px;
  padding: 8px 16px;
  background: var(--kite-primary, #387ed1);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 8px;
  padding: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0 0 12px 0;
}

.chart-container {
  height: 200px;
  position: relative;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-label {
  color: var(--kite-text-secondary, #666);
}

.legend-value {
  font-weight: 600;
}

.legend-value.profit {
  color: var(--kite-green, #00b386);
}

.legend-value.loss {
  color: var(--kite-red, #e53935);
}

.chart-summary {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
}

.summary-item {
  text-align: center;
}

.summary-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
}

.summary-label {
  font-size: 11px;
  color: var(--kite-text-secondary, #999);
  text-transform: uppercase;
}

/* Insights Section */
.insights-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
}

.section-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0 0 12px 0;
}

.section-subtitle i {
  color: #ff9800;
}

.insights-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.insight-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
  font-size: 13px;
  color: var(--kite-text-primary, #394046);
}

.insight-item i {
  color: var(--kite-green, #00b386);
  margin-top: 2px;
}
</style>
