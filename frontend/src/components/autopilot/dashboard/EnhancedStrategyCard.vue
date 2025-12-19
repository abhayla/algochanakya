<script setup>
/**
 * Enhanced Strategy Card Component (Phase 4)
 *
 * Displays strategy with live P&L, delta gauge, premium captured
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  strategy: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['pause', 'resume', 'exit'])

// Status badge styling
const statusConfig = computed(() => {
  const configs = {
    active: { color: '#10b981', bg: '#d1fae5', label: 'Active' },
    waiting: { color: '#3b82f6', bg: '#dbeafe', label: 'Waiting' },
    paused: { color: '#f59e0b', bg: '#fef3c7', label: 'Paused' },
    completed: { color: '#6b7280', bg: '#f3f4f6', label: 'Completed' },
    error: { color: '#ef4444', bg: '#fee2e2', label: 'Error' },
    reentry_waiting: { color: '#8b5cf6', bg: '#ede9fe', label: 'Re-Entry Waiting' }
  }
  return configs[props.strategy.status] || configs.waiting
})

// P&L color
const pnlColor = computed(() => {
  const pnl = props.strategy.pnl || 0
  if (pnl > 0) return '#10b981'
  if (pnl < 0) return '#ef4444'
  return '#6b7280'
})

// Delta gauge percentage (normalized to -1 to 1 range)
const deltaPercentage = computed(() => {
  const delta = props.strategy.net_delta || 0
  // Clamp between -100 and 100
  return Math.max(-100, Math.min(100, delta * 100))
})

// Premium captured progress
const premiumCapturedPct = computed(() => {
  return props.strategy.premium_captured_pct || 0
})

// Navigate to detail
const viewDetails = () => {
  router.push(`/autopilot/strategies/${props.strategy.id}`)
}

// Quick actions
const pauseStrategy = () => emit('pause', props.strategy.id)
const resumeStrategy = () => emit('resume', props.strategy.id)
const exitStrategy = () => emit('exit', props.strategy.id)
</script>

<template>
  <div class="strategy-card" @click="viewDetails">
    <!-- Header -->
    <div class="card-header">
      <div class="header-left">
        <h3 class="strategy-name">{{ strategy.name }}</h3>
        <div class="strategy-meta">
          <span class="underlying-badge">{{ strategy.underlying }}</span>
          <span class="lots-badge">{{ strategy.lots }} lots</span>
        </div>
      </div>
      <div class="header-right">
        <span class="status-badge" :style="{ color: statusConfig.color, background: statusConfig.bg }">
          {{ statusConfig.label }}
        </span>
      </div>
    </div>

    <!-- P&L Section -->
    <div class="pnl-section">
      <div class="pnl-label">P&L</div>
      <div class="pnl-value" :style="{ color: pnlColor }">
        {{ strategy.pnl >= 0 ? '+' : '' }}₹{{ strategy.pnl?.toFixed(2) || '0.00' }}
      </div>
      <div class="pnl-pct" :style="{ color: pnlColor }">
        ({{ strategy.pnl_pct?.toFixed(2) || '0.00' }}%)
      </div>
    </div>

    <!-- Metrics Grid -->
    <div class="metrics-grid">
      <!-- Delta Gauge -->
      <div class="metric-card">
        <div class="metric-label">Net Delta</div>
        <div class="delta-gauge">
          <div class="gauge-track">
            <div class="gauge-fill" :style="{
              width: Math.abs(deltaPercentage) + '%',
              left: deltaPercentage < 0 ? (50 - Math.abs(deltaPercentage)) + '%' : '50%',
              background: deltaPercentage < 0 ? '#ef4444' : '#10b981'
            }"></div>
            <div class="gauge-center"></div>
          </div>
          <div class="delta-value">{{ (strategy.net_delta || 0).toFixed(2) }}Δ</div>
        </div>
      </div>

      <!-- Premium Captured -->
      <div class="metric-card">
        <div class="metric-label">Premium Captured</div>
        <div class="premium-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: premiumCapturedPct + '%' }"></div>
          </div>
          <div class="premium-value">{{ premiumCapturedPct.toFixed(1) }}%</div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="card-actions" @click.stop>
      <button
        v-if="strategy.status === 'active'"
        @click="pauseStrategy"
        class="action-btn pause-btn"
        title="Pause Strategy"
      >
        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6"></path>
        </svg>
      </button>
      <button
        v-if="strategy.status === 'paused'"
        @click="resumeStrategy"
        class="action-btn resume-btn"
        title="Resume Strategy"
      >
        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path>
        </svg>
      </button>
      <button
        v-if="['active', 'waiting'].includes(strategy.status)"
        @click="exitStrategy"
        class="action-btn exit-btn"
        title="Exit Strategy"
      >
        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
        </svg>
      </button>
      <button
        @click="viewDetails"
        class="action-btn view-btn"
        title="View Details"
      >
        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.strategy-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.strategy-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  border-color: #3b82f6;
}

/* Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}

.header-left {
  flex: 1;
}

.strategy-name {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.strategy-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.underlying-badge,
.lots-badge {
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
}

.status-badge {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* P&L Section */
.pnl-section {
  text-align: center;
  padding: 16px 0;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 8px;
}

.pnl-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.pnl-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 2px;
}

.pnl-pct {
  font-size: 14px;
  font-weight: 500;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #f3f4f6;
}

.metric-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

/* Delta Gauge */
.delta-gauge {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gauge-track {
  position: relative;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: visible;
}

.gauge-fill {
  position: absolute;
  height: 100%;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.gauge-center {
  position: absolute;
  left: 50%;
  top: -2px;
  width: 2px;
  height: 12px;
  background: #374151;
  transform: translateX(-50%);
}

.delta-value {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  text-align: center;
}

/* Premium Progress */
.premium-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.premium-value {
  font-size: 14px;
  font-weight: 600;
  color: #10b981;
  text-align: center;
}

/* Actions */
.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.action-btn .icon {
  width: 18px;
  height: 18px;
}

.pause-btn {
  color: #f59e0b;
  border-color: #f59e0b;
}

.pause-btn:hover {
  background: #fef3c7;
}

.resume-btn {
  color: #10b981;
  border-color: #10b981;
}

.resume-btn:hover {
  background: #d1fae5;
}

.exit-btn {
  color: #ef4444;
  border-color: #ef4444;
}

.exit-btn:hover {
  background: #fee2e2;
}

.view-btn {
  color: #3b82f6;
  border-color: #3b82f6;
}

.view-btn:hover {
  background: #dbeafe;
}
</style>
