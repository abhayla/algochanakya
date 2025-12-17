<script setup>
/**
 * Straddle Premium Chart Component
 *
 * Real-time premium monitoring chart for AutoPilot strategies.
 * Shows:
 * - Premium evolution over time
 * - Entry premium marker
 * - Target profit line
 * - Stop-loss line
 * - Premium captured percentage
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
  Legend,
  Filler
} from 'chart.js'
import api from '@/services/api'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
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
const entryPremium = ref(null)
const currentPremium = ref(null)
const targetPremium = ref(null)
const stopLossPremium = ref(null)
const premiumCapturedPct = ref(0)
const refreshTimer = ref(null)

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
      borderColor: '#3b82f6',
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
            label += '₹' + context.parsed.y.toFixed(2)
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
        autoSkip: true,
        maxTicksLimit: 8
      }
    },
    y: {
      beginAtZero: false,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)'
      },
      ticks: {
        callback: function(value) {
          return '₹' + value.toFixed(0)
        }
      }
    }
  }
}))

// Fetch premium history
const fetchPremiumHistory = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await api.get(`/api/v1/autopilot/strategies/${props.strategyId}/premium/history`, {
      params: {
        interval: '1m',
        lookback_hours: 6
      }
    })

    if (response.data && response.data.data) {
      const data = response.data.data
      updateChartData(data.snapshots)
    }
  } catch (err) {
    console.error('Error fetching premium history:', err)
    error.value = 'Failed to load premium data'
  } finally {
    loading.value = false
  }
}

// Fetch decay curve for entry/target/SL data
const fetchDecayCurve = async () => {
  try {
    const response = await api.get(`/api/v1/autopilot/strategies/${props.strategyId}/premium/decay-curve`)

    if (response.data && response.data.data) {
      const data = response.data.data
      entryPremium.value = parseFloat(data.entry_premium)
      currentPremium.value = parseFloat(data.current_premium)
      premiumCapturedPct.value = parseFloat(data.premium_captured_pct)

      // Calculate target (50% of entry) and stop-loss (150% of entry) as examples
      // TODO: Get actual targets from strategy config
      targetPremium.value = entryPremium.value * 0.5
      stopLossPremium.value = entryPremium.value * 1.5
    }
  } catch (err) {
    console.error('Error fetching decay curve:', err)
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
const updateChartData = (snapshots) => {
  if (!snapshots || snapshots.length === 0) {
    // No data, show empty state
    chartData.value = {
      labels: ['No Data'],
      datasets: [{
        label: 'Premium',
        data: [0],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4
      }]
    }

    if (chartInstance.value) {
      chartInstance.value.data = chartData.value
      chartInstance.value.update()
    }
    return
  }

  // Extract timestamps and premium values
  const labels = snapshots.map(snap => {
    const date = new Date(snap.timestamp)
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  })

  const premiumData = snapshots.map(snap => parseFloat(snap.total_premium))

  const datasets = [
    {
      label: 'Total Premium',
      data: premiumData,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5
    }
  ]

  // Add entry premium line if available
  if (entryPremium.value !== null) {
    datasets.push({
      label: 'Entry Premium',
      data: Array(labels.length).fill(entryPremium.value),
      borderColor: '#10b981',
      borderDash: [5, 5],
      borderWidth: 2,
      pointRadius: 0,
      fill: false
    })
  }

  // Add target premium line if available
  if (targetPremium.value !== null) {
    datasets.push({
      label: 'Target (50%)',
      data: Array(labels.length).fill(targetPremium.value),
      borderColor: '#f59e0b',
      borderDash: [5, 5],
      borderWidth: 2,
      pointRadius: 0,
      fill: false
    })
  }

  // Add stop-loss premium line if available
  if (stopLossPremium.value !== null) {
    datasets.push({
      label: 'Stop Loss',
      data: Array(labels.length).fill(stopLossPremium.value),
      borderColor: '#ef4444',
      borderDash: [5, 5],
      borderWidth: 2,
      pointRadius: 0,
      fill: false
    })
  }

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
  await Promise.all([
    fetchPremiumHistory(),
    fetchDecayCurve()
  ])
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
  <div class="straddle-premium-chart">
    <!-- Header -->
    <div class="chart-header">
      <div class="header-left">
        <h3 class="chart-title">Premium Monitor</h3>
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
          <span class="stat-label">Entry:</span>
          <span class="stat-value">₹{{ entryPremium?.toFixed(2) || '-' }}</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Current:</span>
          <span class="stat-value">₹{{ currentPremium?.toFixed(2) || '-' }}</span>
        </div>
        <div class="stat-box success">
          <span class="stat-label">Captured:</span>
          <span class="stat-value">{{ premiumCapturedPct.toFixed(1) }}%</span>
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
      <span>Loading premium data...</span>
    </div>
  </div>
</template>

<style scoped>
.straddle-premium-chart {
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

.stat-box.success .stat-value {
  color: #10b981;
}

.chart-container {
  height: 350px;
  position: relative;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 350px;
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
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #2563eb;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 350px;
  gap: 15px;
  color: #6b7280;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
