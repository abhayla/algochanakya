<script setup>
/**
 * Theta Decay Chart Component
 *
 * Visualizes expected vs actual theta decay for AutoPilot strategies.
 * Shows:
 * - Expected decay curve (dotted line)
 * - Actual decay curve (solid line)
 * - Decay rate comparison
 * - Premium capture percentage
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import api from '@/services/api'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  },
  autoRefresh: {
    type: Boolean,
    default: true
  },
  refreshInterval: {
    type: Number,
    default: 5000 // 5 seconds
  }
})

// State
const chartCanvas = ref(null)
const chartInstance = ref(null)
const chartData = ref(null)
const loading = ref(false)
const error = ref(null)
const decayCurveData = ref(null)
const refreshTimer = ref(null)

// Computed properties
const decayRateMultiplier = computed(() => {
  if (!decayCurveData.value) return 1.0
  return decayCurveData.value.decay_rate
})

const decayRateText = computed(() => {
  const multiplier = decayRateMultiplier.value
  if (multiplier > 1.1) {
    return `${multiplier.toFixed(1)}x faster than expected`
  } else if (multiplier < 0.9) {
    return `${multiplier.toFixed(1)}x slower than expected`
  } else {
    return 'On track with expected decay'
  }
})

const premiumCaptured = computed(() => {
  if (!decayCurveData.value) return 0
  return decayCurveData.value.premium_captured_pct || 0
})

const daysToExpiry = computed(() => {
  if (!decayCurveData.value) return 0
  return decayCurveData.value.days_to_expiry || 0
})

// Chart options
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 15
      }
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#fff',
      bodyColor: '#fff',
      borderColor: '#8b5cf6',
      borderWidth: 1,
      padding: 10,
      displayColors: true,
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || ''
          if (label) {
            label += ': '
          }
          if (context.parsed.y !== null) {
            label += context.parsed.y.toFixed(1) + '%'
          }
          return label
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        display: false
      },
      ticks: {
        maxRotation: 0,
        autoSkip: false
      }
    },
    y: {
      min: 0,
      max: 100,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)'
      },
      ticks: {
        callback: function(value) {
          return value + '%'
        }
      }
    }
  }
}))

// Fetch decay curve data
const fetchDecayCurve = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await api.get(`/api/v1/autopilot/strategies/${props.strategyId}/premium/decay-curve`)

    if (response.data && response.data.data) {
      decayCurveData.value = response.data.data
      updateChartData(response.data.data)
    }
  } catch (err) {
    console.error('Error fetching decay curve:', err)
    error.value = 'Failed to load decay curve data'
  } finally {
    loading.value = false
  }
}

// Create or update chart
const createChart = () => {
  if (!chartCanvas.value) return

  // Destroy existing chart
  if (chartInstance.value) {
    chartInstance.value.destroy()
  }

  // Create new chart
  chartInstance.value = new ChartJS(chartCanvas.value, {
    type: 'line',
    data: chartData.value || {
      labels: [],
      datasets: []
    },
    options: chartOptions.value
  })
}

// Update chart data
const updateChartData = (data) => {
  if (!data) {
    // No data, show empty state
    chartData.value = {
      labels: ['No Data'],
      datasets: [{
        label: 'Decay',
        data: [0],
        borderColor: '#8b5cf6',
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        tension: 0.4
      }]
    }

    if (chartInstance.value) {
      chartInstance.value.data = chartData.value
      chartInstance.value.update()
    }
    return
  }

  const entryPremium = parseFloat(data.entry_premium)
  const currentPremium = parseFloat(data.current_premium)
  const expectedPremium = parseFloat(data.expected_premium)

  // Calculate percentage of premium remaining
  const currentPct = (currentPremium / entryPremium) * 100
  const expectedPct = (expectedPremium / entryPremium) * 100

  // Create labels: Entry, Mid-point, Expiry
  const labels = ['Entry', 'Mid-point', 'Expiry']

  // Expected decay line (linear): 100% → expectedPct → 0%
  const expectedDecayData = [100, expectedPct, 0]

  // Actual decay line: 100% → currentPct → projected 0%
  // For simplicity, we'll show the current point and project linearly to zero
  const actualDecayData = [100, currentPct, 0]

  const datasets = [
    {
      label: 'Expected Decay',
      data: expectedDecayData,
      borderColor: '#9ca3af',
      backgroundColor: 'transparent',
      borderDash: [5, 5],
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      tension: 0
    },
    {
      label: 'Actual Decay',
      data: actualDecayData,
      borderColor: '#8b5cf6',
      backgroundColor: 'rgba(139, 92, 246, 0.1)',
      fill: false,
      borderWidth: 3,
      pointRadius: 5,
      pointHoverRadius: 7,
      tension: 0
    }
  ]

  chartData.value = {
    labels,
    datasets
  }

  // Update chart if already created
  if (chartInstance.value) {
    chartInstance.value.data = chartData.value
    chartInstance.value.update()
  }
}

// Refresh data
const refresh = async () => {
  await fetchDecayCurve()
}

// Start auto-refresh
const startAutoRefresh = () => {
  if (props.autoRefresh && !refreshTimer.value) {
    refreshTimer.value = setInterval(() => {
      refresh()
    }, props.refreshInterval)
  }
}

// Stop auto-refresh
const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
    refreshTimer.value = null
  }
}

// Lifecycle
onMounted(async () => {
  await refresh()
  await nextTick()
  createChart()
  startAutoRefresh()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
  if (chartInstance.value) {
    chartInstance.value.destroy()
  }
})

// Watch for strategy ID changes
watch(() => props.strategyId, async () => {
  stopAutoRefresh()
  await refresh()
  startAutoRefresh()
})

// Watch for autoRefresh changes
watch(() => props.autoRefresh, (newValue) => {
  if (newValue) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})
</script>

<template>
  <div class="theta-decay-chart">
    <!-- Header -->
    <div class="chart-header">
      <div class="header-left">
        <h3 class="chart-title">Theta Decay Analysis</h3>
        <button
          @click="refresh"
          :disabled="loading"
          class="refresh-btn"
          :class="{ 'refreshing': loading }"
        >
          <span class="refresh-icon">↻</span>
          <span v-if="!loading">Refresh</span>
          <span v-else>Loading...</span>
        </button>
      </div>
      <div class="header-right">
        <div class="stat-box">
          <span class="stat-label">Captured:</span>
          <span class="stat-value success">{{ premiumCaptured.toFixed(1) }}%</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Days to Expiry:</span>
          <span class="stat-value">{{ daysToExpiry }}</span>
        </div>
        <div class="stat-box" :class="{ 'warning': decayRateMultiplier > 1.1, 'success': decayRateMultiplier <= 1.1 }">
          <span class="stat-label">Decay Rate:</span>
          <span class="stat-value">{{ decayRateText }}</span>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span class="error-message">{{ error }}</span>
      <button @click="refresh" class="retry-btn">Retry</button>
    </div>

    <!-- Chart -->
    <div v-else-if="chartData" class="chart-container">
      <canvas ref="chartCanvas"></canvas>
    </div>

    <!-- Loading State -->
    <div v-else class="loading-state">
      <div class="spinner"></div>
      <span>Loading decay curve...</span>
    </div>

    <!-- Info Box -->
    <div v-if="decayCurveData && !error" class="info-box">
      <div class="info-row">
        <span class="info-label">Entry Premium:</span>
        <span class="info-value">₹{{ parseFloat(decayCurveData.entry_premium).toFixed(2) }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Current Premium:</span>
        <span class="info-value">₹{{ parseFloat(decayCurveData.current_premium).toFixed(2) }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Expected Premium:</span>
        <span class="info-value">₹{{ parseFloat(decayCurveData.expected_premium).toFixed(2) }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Premium Captured:</span>
        <span class="info-value highlight">₹{{ (parseFloat(decayCurveData.entry_premium) - parseFloat(decayCurveData.current_premium)).toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.theta-decay-chart {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  min-height: 400px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-icon {
  font-size: 16px;
  display: inline-block;
}

.refreshing .refresh-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.header-right {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-box {
  padding: 8px 16px;
  background: #f3f4f6;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-box.success {
  background: #ecfdf5;
}

.stat-box.warning {
  background: #fef3c7;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
}

.stat-value.success {
  color: #10b981;
}

.stat-box.success .stat-value {
  color: #10b981;
}

.stat-box.warning .stat-value {
  color: #f59e0b;
}

.chart-container {
  height: 300px;
  position: relative;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 15px;
}

.error-icon {
  font-size: 48px;
}

.error-message {
  font-size: 14px;
  color: #ef4444;
}

.retry-btn {
  padding: 8px 16px;
  background: #8b5cf6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #7c3aed;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 15px;
  color: #6b7280;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #8b5cf6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.info-box {
  margin-top: 20px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 6px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.info-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.info-value.highlight {
  color: #10b981;
  font-size: 15px;
}
</style>
