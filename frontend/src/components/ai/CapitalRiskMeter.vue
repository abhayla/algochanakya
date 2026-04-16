<template>
  <div class="capital-risk-meter" data-testid="capital-risk-meter">
    <!-- Header -->
    <div class="meter-header">
      <h3 class="meter-title">
        <i class="fas fa-shield-alt"></i>
        Capital at Risk
      </h3>
      <button
        class="btn-refresh"
        @click="fetchRiskData"
        :disabled="loading"
        data-testid="btn-refresh-risk"
      >
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !riskData" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i>
      <p>Calculating risk...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state" data-testid="error-state">
      <i class="fas fa-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <button class="btn-retry" @click="fetchRiskData">Retry</button>
    </div>

    <!-- Risk Gauge -->
    <div v-else-if="riskData" class="meter-content">
      <!-- Visual Gauge -->
      <div class="gauge-container" data-testid="risk-gauge">
        <svg viewBox="0 0 200 120" class="gauge-svg">
          <!-- Background arc -->
          <path
            :d="backgroundArc"
            fill="none"
            stroke="#e8e8e8"
            stroke-width="12"
            stroke-linecap="round"
          />
          <!-- Colored arc -->
          <path
            :d="valueArc"
            fill="none"
            :stroke="gaugeColor"
            stroke-width="12"
            stroke-linecap="round"
          />
          <!-- Alert zones -->
          <path
            :d="warningZoneArc"
            fill="none"
            stroke="#ff980020"
            stroke-width="14"
          />
          <path
            :d="criticalZoneArc"
            fill="none"
            stroke="#e5393520"
            stroke-width="14"
          />
        </svg>

        <!-- Center Value -->
        <div class="gauge-center">
          <div class="gauge-value" :style="{ color: gaugeColor }">
            {{ Math.round(riskData.capital_at_risk_pct) }}%
          </div>
          <div class="gauge-label">of Capital</div>
        </div>
      </div>

      <!-- Alert Badge -->
      <div
        v-if="riskData.alert_level !== 'LOW'"
        class="alert-badge"
        :class="alertBadgeClass"
        data-testid="alert-badge"
      >
        <i :class="alertIcon"></i>
        {{ alertLabel }}
      </div>

      <!-- Key Metrics -->
      <div class="metrics-grid">
        <div class="metric-item" data-testid="metric-utilization">
          <div class="metric-value">{{ riskData.capital_utilization_pct.toFixed(1) }}%</div>
          <div class="metric-label">Utilization</div>
        </div>
        <div class="metric-item" data-testid="metric-positions">
          <div class="metric-value">{{ riskData.open_positions_count }}</div>
          <div class="metric-label">Positions</div>
        </div>
        <div class="metric-item" data-testid="metric-stress">
          <div class="metric-value" :class="stressClass">{{ riskData.stress_risk_score.toFixed(0) }}</div>
          <div class="metric-label">Stress Score</div>
        </div>
      </div>

      <!-- Worst Case -->
      <div class="worst-case" data-testid="worst-case">
        <div class="worst-case-label">Worst-Case Loss (Stress)</div>
        <div class="worst-case-value loss">
          {{ formatCurrency(riskData.worst_case_loss) }}
        </div>
      </div>

      <!-- Alerts List -->
      <div v-if="riskData.alerts.length > 0" class="alerts-list" data-testid="alerts-list">
        <div class="alerts-header">
          <i class="fas fa-bell"></i>
          Active Alerts ({{ riskData.alerts.length }})
        </div>
        <div
          v-for="(alert, index) in riskData.alerts.slice(0, 3)"
          :key="index"
          class="alert-item"
          :class="'alert-' + alert.severity.toLowerCase()"
        >
          <i :class="getAlertIcon(alert.severity)"></i>
          <span class="alert-message">{{ alert.message }}</span>
        </div>
        <div
          v-if="riskData.alerts.length > 3"
          class="alerts-more"
        >
          +{{ riskData.alerts.length - 3 }} more alerts
        </div>
      </div>

      <!-- Status Message -->
      <div class="status-message" :class="'status-' + riskData.alert_level.toLowerCase()">
        {{ statusMessage }}
      </div>
    </div>

    <!-- Default Empty State -->
    <div v-else class="empty-state">
      <i class="fas fa-chart-pie"></i>
      <p>No risk data available</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAIAnalyticsStore } from '@/stores/aiAnalytics'

const aiAnalytics = useAIAnalyticsStore()

const props = defineProps({
  refreshInterval: {
    type: Number,
    default: 30000 // 30 seconds
  },
  currentSpot: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['alert', 'loaded', 'error'])

// State
const loading = ref(false)
const error = ref(null)
const riskData = ref(null)
let refreshTimer = null

// Gauge calculations
const gaugeStartAngle = -140
const gaugeEndAngle = 140
const gaugeRadius = 80
const gaugeCenterX = 100
const gaugeCenterY = 90

// Computed
const valuePercent = computed(() => {
  if (!riskData.value) return 0
  return Math.min(100, Math.max(0, riskData.value.capital_at_risk_pct))
})

const gaugeColor = computed(() => {
  if (!riskData.value) return '#666'
  const level = riskData.value.alert_level
  const colors = {
    'CRITICAL': '#e53935',
    'HIGH': '#ff9800',
    'ELEVATED': '#ffeb3b',
    'NORMAL': '#4caf50',
    'LOW': '#00b386'
  }
  return colors[level] || '#666'
})

const backgroundArc = computed(() => {
  return describeArc(gaugeCenterX, gaugeCenterY, gaugeRadius, gaugeStartAngle, gaugeEndAngle)
})

const valueArc = computed(() => {
  const angle = gaugeStartAngle + (valuePercent.value / 100) * (gaugeEndAngle - gaugeStartAngle)
  return describeArc(gaugeCenterX, gaugeCenterY, gaugeRadius, gaugeStartAngle, angle)
})

const warningZoneArc = computed(() => {
  if (!riskData.value) return ''
  const startAngle = gaugeStartAngle + (riskData.value.warning_threshold_pct / 100) * (gaugeEndAngle - gaugeStartAngle)
  const endAngle = gaugeStartAngle + (riskData.value.critical_threshold_pct / 100) * (gaugeEndAngle - gaugeStartAngle)
  return describeArc(gaugeCenterX, gaugeCenterY, gaugeRadius + 8, startAngle, endAngle)
})

const criticalZoneArc = computed(() => {
  if (!riskData.value) return ''
  const startAngle = gaugeStartAngle + (riskData.value.critical_threshold_pct / 100) * (gaugeEndAngle - gaugeStartAngle)
  return describeArc(gaugeCenterX, gaugeCenterY, gaugeRadius + 8, startAngle, gaugeEndAngle)
})

const alertBadgeClass = computed(() => {
  if (!riskData.value) return ''
  return `badge-${riskData.value.alert_level.toLowerCase()}`
})

const alertIcon = computed(() => {
  if (!riskData.value) return 'fas fa-info-circle'
  const icons = {
    'CRITICAL': 'fas fa-exclamation-circle',
    'HIGH': 'fas fa-exclamation-triangle',
    'ELEVATED': 'fas fa-info-circle',
    'NORMAL': 'fas fa-check-circle',
    'LOW': 'fas fa-check-circle'
  }
  return icons[riskData.value.alert_level] || 'fas fa-info-circle'
})

const alertLabel = computed(() => {
  if (!riskData.value) return ''
  const labels = {
    'CRITICAL': 'Critical Risk',
    'HIGH': 'High Risk',
    'ELEVATED': 'Elevated',
    'NORMAL': 'Normal',
    'LOW': 'Low Risk'
  }
  return labels[riskData.value.alert_level] || riskData.value.alert_level
})

const stressClass = computed(() => {
  if (!riskData.value) return ''
  const score = riskData.value.stress_risk_score
  if (score >= 75) return 'stress-high'
  if (score >= 50) return 'stress-medium'
  return 'stress-low'
})

const statusMessage = computed(() => {
  if (!riskData.value) return ''
  const messages = {
    'CRITICAL': 'Reduce exposure immediately',
    'HIGH': 'Consider reducing positions',
    'ELEVATED': 'Monitor closely',
    'NORMAL': 'Within normal range',
    'LOW': 'Low risk exposure'
  }
  return messages[riskData.value.alert_level] || ''
})

// Methods
const fetchRiskData = async () => {
  loading.value = true
  error.value = null

  const params = props.currentSpot ? { current_spot: props.currentSpot } : {}
  const result = await aiAnalytics.fetchCapitalRisk(params)
  loading.value = false

  if (!result.success) {
    console.error('[CapitalRiskMeter] Error fetching risk data:', result.error)
    error.value = result.error || 'Failed to load risk data'
    emit('error', error.value)
    return
  }

  riskData.value = result.data
  emit('loaded', riskData.value)

  if (riskData.value.alert_level === 'CRITICAL') {
    emit('alert', {
      level: 'CRITICAL',
      message: 'Capital at risk exceeds critical threshold',
      data: riskData.value,
    })
  }
}

const formatCurrency = (value) => {
  if (!value) return '₹0'
  const sign = value >= 0 ? '' : '-'
  return `${sign}₹${Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const getAlertIcon = (severity) => {
  const icons = {
    'CRITICAL': 'fas fa-exclamation-circle',
    'HIGH': 'fas fa-exclamation-triangle',
    'ELEVATED': 'fas fa-info-circle'
  }
  return icons[severity] || 'fas fa-bell'
}

// SVG arc helper
function describeArc(x, y, radius, startAngle, endAngle) {
  const start = polarToCartesian(x, y, radius, endAngle)
  const end = polarToCartesian(x, y, radius, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1'

  return [
    'M', start.x, start.y,
    'A', radius, radius, 0, largeArcFlag, 0, end.x, end.y
  ].join(' ')
}

function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
  const angleInRadians = (angleInDegrees - 90) * Math.PI / 180
  return {
    x: centerX + (radius * Math.cos(angleInRadians)),
    y: centerY + (radius * Math.sin(angleInRadians))
  }
}

// Lifecycle
onMounted(() => {
  fetchRiskData()

  // Set up auto-refresh
  if (props.refreshInterval > 0) {
    refreshTimer = setInterval(fetchRiskData, props.refreshInterval)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})

// Watch for spot price changes
watch(() => props.currentSpot, () => {
  fetchRiskData()
})

// Expose for parent
defineExpose({
  refresh: fetchRiskData
})
</script>

<style scoped>
.capital-risk-meter {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.meter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.meter-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.meter-title i {
  color: var(--kite-primary, #387ed1);
}

.btn-refresh {
  width: 28px;
  height: 28px;
  padding: 0;
  background: transparent;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  color: var(--kite-text-secondary, #666);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-refresh:hover:not(:disabled) {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-primary, #387ed1);
  color: var(--kite-primary, #387ed1);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state,
.error-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--kite-text-secondary, #666);
  gap: 8px;
}

.loading-state i,
.error-state i,
.empty-state i {
  font-size: 24px;
}

.error-state {
  color: var(--kite-red, #e53935);
}

.btn-retry {
  margin-top: 8px;
  padding: 6px 14px;
  background: var(--kite-primary, #387ed1);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.meter-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Gauge */
.gauge-container {
  position: relative;
  width: 100%;
  max-width: 200px;
  margin: 0 auto;
}

.gauge-svg {
  width: 100%;
  height: auto;
}

.gauge-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -30%);
  text-align: center;
}

.gauge-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.gauge-label {
  font-size: 11px;
  color: var(--kite-text-secondary, #999);
  margin-top: 2px;
}

/* Alert Badge */
.alert-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  margin: 0 auto;
}

.badge-critical {
  background: rgba(229, 57, 53, 0.1);
  color: #e53935;
}

.badge-high {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}

.badge-elevated {
  background: rgba(255, 235, 59, 0.15);
  color: #c8a300;
}

.badge-normal {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 8px;
}

.metric-item {
  text-align: center;
  padding: 8px 4px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
}

.metric-value.stress-high {
  color: var(--kite-red, #e53935);
}

.metric-value.stress-medium {
  color: #ff9800;
}

.metric-value.stress-low {
  color: var(--kite-green, #00b386);
}

.metric-label {
  font-size: 10px;
  color: var(--kite-text-secondary, #999);
  text-transform: uppercase;
  margin-top: 2px;
}

/* Worst Case */
.worst-case {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(229, 57, 53, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(229, 57, 53, 0.1);
}

.worst-case-label {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
}

.worst-case-value {
  font-size: 14px;
  font-weight: 600;
}

.worst-case-value.loss {
  color: var(--kite-red, #e53935);
}

/* Alerts List */
.alerts-list {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
}

.alerts-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--kite-text-secondary, #666);
  margin-bottom: 8px;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 11px;
  margin-bottom: 4px;
}

.alert-item i {
  margin-top: 1px;
  flex-shrink: 0;
}

.alert-critical {
  background: rgba(229, 57, 53, 0.1);
  color: #e53935;
}

.alert-high {
  background: rgba(255, 152, 0, 0.1);
  color: #e65100;
}

.alert-elevated {
  background: rgba(255, 235, 59, 0.15);
  color: #9a7b00;
}

.alert-message {
  flex: 1;
  line-height: 1.3;
}

.alerts-more {
  text-align: center;
  font-size: 11px;
  color: var(--kite-text-secondary, #999);
  padding-top: 4px;
}

/* Status Message */
.status-message {
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  padding: 8px 12px;
  border-radius: 6px;
  margin-top: 8px;
}

.status-critical {
  background: rgba(229, 57, 53, 0.1);
  color: #e53935;
}

.status-high {
  background: rgba(255, 152, 0, 0.1);
  color: #e65100;
}

.status-elevated {
  background: rgba(255, 235, 59, 0.15);
  color: #9a7b00;
}

.status-normal {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

.status-low {
  background: rgba(0, 179, 134, 0.1);
  color: var(--kite-green, #00b386);
}
</style>
