<template>
  <div class="graduation-progress" data-testid="graduation-progress">
    <div class="progress-header">
      <h3 class="progress-title">Paper Trading Progress</h3>
      <div v-if="isGraduated" class="graduation-badge" data-testid="graduation-badge">
        <i class="fas fa-graduation-cap"></i> Graduated
      </div>
    </div>

    <div class="progress-metrics">
      <div class="metric-card" data-testid="metric-trades">
        <div class="metric-icon">
          <i class="fas fa-chart-line"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ tradesCompleted }} / {{ tradesTarget }}</div>
          <div class="metric-label">Trades Completed</div>
          <div class="metric-bar">
            <div class="metric-bar-fill" :style="{ width: tradesProgress + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="metric-card" data-testid="metric-winrate">
        <div class="metric-icon" :class="winRateClass">
          <i class="fas fa-percentage"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ winRate.toFixed(1) }}%</div>
          <div class="metric-label">Win Rate (Target: {{ winRateTarget }}%)</div>
          <div class="metric-bar">
            <div class="metric-bar-fill" :class="winRateClass" :style="{ width: winRateProgress + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="metric-card" data-testid="metric-pnl">
        <div class="metric-icon" :class="pnlClass">
          <i class="fas fa-indian-rupee-sign"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value" :class="pnlClass">{{ formatPnl(totalPnl) }}</div>
          <div class="metric-label">Total P&L</div>
          <div class="metric-bar">
            <div class="metric-bar-fill" :class="pnlClass" :style="{ width: Math.min(100, Math.abs(totalPnl) / 1000) + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="metric-card" data-testid="metric-days">
        <div class="metric-icon">
          <i class="fas fa-calendar-days"></i>
        </div>
        <div class="metric-content">
          <div class="metric-value">{{ daysPassed }} days</div>
          <div class="metric-label">Since Started</div>
          <div class="metric-subtext">{{ startDate }}</div>
        </div>
      </div>
    </div>

    <div class="graduation-status" data-testid="graduation-status">
      <div v-if="isGraduated" class="status-message success">
        <i class="fas fa-check-circle"></i>
        <span>Congratulations! You've met all requirements for live trading. Ready to graduate?</span>
      </div>
      <div v-else class="status-message pending">
        <i class="fas fa-hourglass-half"></i>
        <span>{{ nextRequirement }}</span>
      </div>
    </div>

    <div v-if="isGraduated && !graduationApproved" class="graduation-actions" data-testid="graduation-actions">
      <button class="btn-graduate" @click="$emit('graduate')" data-testid="btn-graduate">
        <i class="fas fa-rocket"></i>
        Graduate to Live Trading
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tradesCompleted: {
    type: Number,
    default: 0
  },
  tradesTarget: {
    type: Number,
    default: 30
  },
  winRate: {
    type: Number,
    default: 0
  },
  winRateTarget: {
    type: Number,
    default: 65
  },
  totalPnl: {
    type: Number,
    default: 0
  },
  startDate: {
    type: String,
    default: ''
  },
  graduationApproved: {
    type: Boolean,
    default: false
  }
})

defineEmits(['graduate'])

const daysPassed = computed(() => {
  if (!props.startDate) return 0
  const start = new Date(props.startDate)
  const now = new Date()
  const diff = now - start
  return Math.floor(diff / (1000 * 60 * 60 * 24))
})

const tradesProgress = computed(() => {
  return Math.min(100, (props.tradesCompleted / props.tradesTarget) * 100)
})

const winRateProgress = computed(() => {
  return Math.min(100, (props.winRate / props.winRateTarget) * 100)
})

const isGraduated = computed(() => {
  return props.tradesCompleted >= props.tradesTarget &&
         props.winRate >= props.winRateTarget &&
         props.totalPnl >= 0
})

const winRateClass = computed(() => {
  if (props.winRate >= props.winRateTarget) return 'success'
  if (props.winRate >= props.winRateTarget * 0.8) return 'warning'
  return 'danger'
})

const pnlClass = computed(() => {
  return props.totalPnl >= 0 ? 'success' : 'danger'
})

const nextRequirement = computed(() => {
  const requirements = []

  if (props.tradesCompleted < props.tradesTarget) {
    const remaining = props.tradesTarget - props.tradesCompleted
    requirements.push(`${remaining} more trades`)
  }

  if (props.winRate < props.winRateTarget) {
    const gap = (props.winRateTarget - props.winRate).toFixed(1)
    requirements.push(`${gap}% win rate improvement`)
  }

  if (props.totalPnl < 0) {
    requirements.push('positive P&L')
  }

  if (requirements.length === 0) {
    return 'All requirements met!'
  }

  return `You need: ${requirements.join(', ')}`
})

const formatPnl = (pnl) => {
  const sign = pnl >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(pnl).toFixed(2)}`
}
</script>

<style scoped>
.graduation-progress {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.progress-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.graduation-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.progress-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 8px;
}

.metric-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 8px;
  font-size: 18px;
  color: var(--kite-primary, #387ed1);
  flex-shrink: 0;
}

.metric-icon.success {
  color: var(--kite-green, #00b386);
}

.metric-icon.warning {
  color: #ff9800;
}

.metric-icon.danger {
  color: var(--kite-red, #e53935);
}

.metric-content {
  flex: 1;
  min-width: 0;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 4px;
}

.metric-value.success {
  color: var(--kite-green, #00b386);
}

.metric-value.danger {
  color: var(--kite-red, #e53935);
}

.metric-label {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
  margin-bottom: 6px;
}

.metric-subtext {
  font-size: 11px;
  color: var(--kite-text-secondary, #999);
  margin-top: 4px;
}

.metric-bar {
  height: 4px;
  background: white;
  border-radius: 2px;
  overflow: hidden;
}

.metric-bar-fill {
  height: 100%;
  background: var(--kite-primary, #387ed1);
  transition: width 0.3s ease;
}

.metric-bar-fill.success {
  background: var(--kite-green, #00b386);
}

.metric-bar-fill.warning {
  background: #ff9800;
}

.metric-bar-fill.danger {
  background: var(--kite-red, #e53935);
}

.graduation-status {
  margin-bottom: 16px;
}

.status-message {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
}

.status-message.success {
  background: rgba(0, 179, 134, 0.1);
  color: var(--kite-green, #00b386);
  border-left: 4px solid var(--kite-green, #00b386);
}

.status-message.pending {
  background: rgba(255, 152, 0, 0.1);
  color: #f57c00;
  border-left: 4px solid #ff9800;
}

.graduation-actions {
  display: flex;
  justify-content: center;
}

.btn-graduate {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-graduate:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-graduate:active {
  transform: translateY(0);
}
</style>
