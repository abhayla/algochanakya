<script setup>
/**
 * Risk Overview Panel (Phase 4)
 *
 * Displays margin usage, delta exposure, and risk metrics
 */
import { computed, ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// Update time tracking
const now = ref(Date.now())
let updateInterval = null

onMounted(() => {
  // Update "now" every 5 seconds for relative time calculation
  updateInterval = setInterval(() => {
    now.value = Date.now()
  }, 5000)
})

onUnmounted(() => {
  if (updateInterval) clearInterval(updateInterval)
})

// Calculate relative update time
const updateTime = computed(() => {
  if (!props.summary.last_updated) return 'Updated just now'

  const lastUpdated = new Date(props.summary.last_updated).getTime()
  const diffMs = now.value - lastUpdated
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 10) return 'Updated just now'
  if (diffSec < 60) return `Updated ${diffSec}s ago`

  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `Updated ${diffMin}m ago`

  const diffHour = Math.floor(diffMin / 60)
  return `Updated ${diffHour}h ago`
})

// Calculate risk metrics
const marginUsage = computed(() => {
  if (!props.summary.total_margin || !props.summary.available_margin) return 0
  return ((props.summary.total_margin / props.summary.available_margin) * 100).toFixed(1)
})

const marginColor = computed(() => {
  const usage = parseFloat(marginUsage.value)
  if (usage >= 80) return '#ef4444'
  if (usage >= 60) return '#f59e0b'
  return '#10b981'
})

const netDelta = computed(() => props.summary.net_delta || 0)
const netDeltaAbs = computed(() => Math.abs(netDelta.value))

const deltaColor = computed(() => {
  if (Math.abs(netDelta.value) > 0.5) return '#ef4444'
  if (Math.abs(netDelta.value) > 0.3) return '#f59e0b'
  return '#10b981'
})

const totalPnL = computed(() => props.summary.total_pnl || 0)
const pnlColor = computed(() => totalPnL.value >= 0 ? '#10b981' : '#ef4444')
</script>

<template>
  <div class="risk-panel">
    <div class="panel-header">
      <h3 class="panel-title">Risk Overview</h3>
      <span class="update-time">{{ updateTime }}</span>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="risk-metrics">
      <div class="risk-metric" v-for="i in 3" :key="i">
        <div class="skeleton-header">
          <div class="skeleton-circle"></div>
          <div class="skeleton-text-group">
            <div class="skeleton-text skeleton-text-sm"></div>
            <div class="skeleton-text skeleton-text-lg"></div>
          </div>
        </div>
        <div class="skeleton-bar"></div>
        <div class="skeleton-text skeleton-text-xs"></div>
      </div>
    </div>

    <!-- Actual Content -->
    <div v-else class="risk-metrics">
      <!-- Margin Usage -->
      <div class="risk-metric">
        <div class="metric-header">
          <span class="metric-icon">💰</span>
          <div>
            <div class="metric-label">
              Margin Usage
              <span class="tooltip">
                <span class="tooltip-icon">ℹ️</span>
                <span class="tooltip-text">Percentage of available margin currently blocked for active strategies</span>
              </span>
            </div>
            <div class="metric-value" :style="{ color: marginColor }">
              {{ marginUsage }}%
            </div>
          </div>
        </div>
        <div class="metric-bar">
          <div
            class="metric-bar-fill"
            :style="{ width: marginUsage + '%', background: marginColor }"
          ></div>
        </div>
        <div class="metric-detail">
          <span class="detail-label">Used:</span>
          <span class="detail-value">₹{{ summary.total_margin?.toLocaleString() || 0 }}</span>
          <span class="detail-separator">|</span>
          <span class="detail-label">Available:</span>
          <span class="detail-value">₹{{ summary.available_margin?.toLocaleString() || 0 }}</span>
        </div>
      </div>

      <!-- Delta Exposure -->
      <div class="risk-metric">
        <div class="metric-header">
          <span class="metric-icon">Δ</span>
          <div>
            <div class="metric-label">
              Net Delta
              <span class="tooltip">
                <span class="tooltip-icon">ℹ️</span>
                <span class="tooltip-text">Combined directional exposure across all strategies (-1 to +1)</span>
              </span>
            </div>
            <div class="metric-value" :style="{ color: deltaColor }">
              {{ netDelta.toFixed(2) }}
            </div>
          </div>
        </div>
        <div class="delta-gauge">
          <div class="gauge-track">
            <div
              class="gauge-indicator"
              :style="{
                left: (50 + (netDelta * 50)) + '%',
                background: deltaColor
              }"
            ></div>
            <div class="gauge-center-line"></div>
            <div class="gauge-label gauge-label-left">-1</div>
            <div class="gauge-label gauge-label-center">0</div>
            <div class="gauge-label gauge-label-right">+1</div>
          </div>
        </div>
        <div class="metric-detail">
          <span
            class="delta-status"
            :style="{
              color: netDeltaAbs < 0.2 ? '#10b981' : netDeltaAbs < 0.4 ? '#f59e0b' : '#ef4444'
            }"
          >
            {{ netDeltaAbs < 0.2 ? '✓ Balanced' : netDeltaAbs < 0.4 ? '⚠️ Moderate' : '⚠️ High Risk' }}
          </span>
        </div>
      </div>

      <!-- Total P&L -->
      <div class="risk-metric">
        <div class="metric-header">
          <span class="metric-icon">📊</span>
          <div>
            <div class="metric-label">
              Total P&L
              <span class="tooltip">
                <span class="tooltip-icon">ℹ️</span>
                <span class="tooltip-text">Combined realized and unrealized profit/loss across all AutoPilot strategies</span>
              </span>
            </div>
            <div class="metric-value large" :style="{ color: pnlColor }">
              {{ totalPnL >= 0 ? '+' : '' }}₹{{ totalPnL.toLocaleString() }}
            </div>
          </div>
        </div>
        <div class="pnl-breakdown">
          <div class="breakdown-item">
            <span class="breakdown-label">Realized:</span>
            <span class="breakdown-value" style="color: #10b981">
              +₹{{ (summary.realized_pnl || 0).toLocaleString() }}
            </span>
          </div>
          <div class="breakdown-item">
            <span class="breakdown-label">Unrealized:</span>
            <span
              class="breakdown-value"
              :style="{ color: (summary.unrealized_pnl || 0) >= 0 ? '#10b981' : '#ef4444' }"
            >
              {{ (summary.unrealized_pnl || 0) >= 0 ? '+' : '' }}₹{{ (summary.unrealized_pnl || 0).toLocaleString() }}
            </span>
          </div>
        </div>
      </div>

      <!-- Active Strategies Count -->
      <div class="risk-metric compact">
        <div class="compact-stat">
          <span class="compact-label">Active Strategies</span>
          <span class="compact-value">{{ summary.active_strategies || 0 }}</span>
        </div>
        <div class="compact-stat">
          <span class="compact-label">Waiting</span>
          <span class="compact-value waiting">{{ summary.waiting_strategies || 0 }}</span>
        </div>
        <div class="compact-stat">
          <span class="compact-label">Total Positions</span>
          <span class="compact-value">{{ summary.total_positions || 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.risk-panel {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.update-time {
  font-size: 12px;
  color: #9ca3af;
}

.risk-metrics {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.risk-metric {
  padding: 16px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.metric-icon {
  font-size: 28px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 8px;
  flex-shrink: 0;
}

.metric-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
}

.metric-value.large {
  font-size: 28px;
}

.metric-bar {
  height: 10px;
  background: #e5e7eb;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 8px;
}

.metric-bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.3s ease;
}

.metric-detail {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.detail-label {
  font-weight: 500;
}

.detail-value {
  font-weight: 600;
  color: #1f2937;
}

.detail-separator {
  color: #d1d5db;
  margin: 0 2px;
}

/* Delta Gauge */
.delta-gauge {
  margin: 12px 0;
}

.gauge-track {
  position: relative;
  height: 32px;
  background: linear-gradient(90deg, #fee2e2 0%, #fef3c7 50%, #d1fae5 100%);
  border-radius: 16px;
  border: 2px solid #e5e7eb;
}

.gauge-indicator {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  transition: left 0.3s ease;
}

.gauge-center-line {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #374151;
  opacity: 0.3;
}

.gauge-label {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  font-weight: 600;
  color: #6b7280;
}

.gauge-label-left {
  left: 8px;
}

.gauge-label-center {
  left: 50%;
  transform: translate(-50%, -50%);
}

.gauge-label-right {
  right: 8px;
}

.delta-status {
  font-weight: 600;
  font-size: 13px;
}

/* P&L Breakdown */
.pnl-breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.breakdown-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.breakdown-value {
  font-size: 14px;
  font-weight: 600;
}

/* Compact Stats */
.risk-metric.compact {
  display: flex;
  justify-content: space-between;
  padding: 12px;
}

.compact-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.compact-label {
  font-size: 10px;
  color: #9ca3af;
  font-weight: 500;
  text-transform: uppercase;
  text-align: center;
}

.compact-value {
  font-size: 20px;
  font-weight: 700;
  color: #10b981;
}

.compact-value.waiting {
  color: #3b82f6;
}

/* Tooltip Styles */
.tooltip {
  position: relative;
  display: inline-flex;
  cursor: help;
  margin-left: 4px;
}

.tooltip-icon {
  font-size: 10px;
  opacity: 0.5;
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

/* Loading Skeleton Styles */
.skeleton-header {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.skeleton-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
}

.skeleton-text-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-text {
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
}

.skeleton-text-xs {
  width: 60%;
  height: 12px;
}

.skeleton-text-sm {
  width: 40%;
  height: 14px;
}

.skeleton-text-lg {
  width: 60%;
  height: 20px;
}

.skeleton-bar {
  height: 8px;
  border-radius: 4px;
  margin: 8px 0;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
