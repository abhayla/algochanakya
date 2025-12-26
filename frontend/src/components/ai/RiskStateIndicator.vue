<template>
  <div class="risk-state-indicator" data-testid="risk-state-indicator">
    <div class="state-badge" :class="stateClass" data-testid="state-badge">
      <div class="state-icon">
        <i :class="stateIcon"></i>
      </div>
      <div class="state-content">
        <div class="state-type" data-testid="state-type">{{ stateLabel }}</div>
        <div class="state-metrics" data-testid="state-metrics">
          <span v-if="sharpe !== null">Sharpe: {{ sharpe.toFixed(2) }}</span>
          <span v-if="drawdown !== null"> | DD: {{ drawdown.toFixed(1) }}%</span>
          <span v-if="consecutiveLosses > 0"> | {{ consecutiveLosses }} losses</span>
        </div>
      </div>
    </div>
    <div v-if="reason" class="state-reason" data-testid="state-reason">
      {{ reason }}
    </div>
    <div v-if="showBehavior && state === 'DEGRADED'" class="state-behavior" data-testid="state-behavior">
      <div class="behavior-title">Conservative Mode Active:</div>
      <ul>
        <li>Confidence threshold increased by 15%</li>
        <li>Position sizing reduced by 50%</li>
        <li>Offensive adjustments disabled</li>
      </ul>
    </div>
    <div v-if="showBehavior && state === 'PAUSED'" class="state-behavior" data-testid="state-behavior">
      <div class="behavior-title">Trading Paused:</div>
      <ul>
        <li>All new deployments blocked</li>
        <li>Existing positions monitored</li>
        <li>Manual reset required after recovery</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  state: {
    type: String,
    required: true,
    validator: (value) => ['NORMAL', 'DEGRADED', 'PAUSED'].includes(value)
  },
  reason: {
    type: String,
    default: ''
  },
  sharpe: {
    type: Number,
    default: null
  },
  drawdown: {
    type: Number,
    default: null
  },
  consecutiveLosses: {
    type: Number,
    default: 0
  },
  showBehavior: {
    type: Boolean,
    default: true
  }
})

const stateClass = computed(() => {
  const baseClass = 'state-'
  switch (props.state) {
    case 'NORMAL':
      return `${baseClass}normal`
    case 'DEGRADED':
      return `${baseClass}degraded`
    case 'PAUSED':
      return `${baseClass}paused`
    default:
      return `${baseClass}normal`
  }
})

const stateIcon = computed(() => {
  switch (props.state) {
    case 'NORMAL':
      return 'fas fa-shield-check'
    case 'DEGRADED':
      return 'fas fa-triangle-exclamation'
    case 'PAUSED':
      return 'fas fa-circle-pause'
    default:
      return 'fas fa-circle-question'
  }
})

const stateLabel = computed(() => {
  switch (props.state) {
    case 'NORMAL':
      return 'Normal'
    case 'DEGRADED':
      return 'Degraded Performance'
    case 'PAUSED':
      return 'Trading Paused'
    default:
      return props.state
  }
})
</script>

<style scoped>
.risk-state-indicator {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.state-badge {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 8px;
  font-weight: 500;
  border: 2px solid;
  background: white;
  transition: all 0.2s ease;
}

.state-icon {
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.state-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.state-type {
  font-size: 16px;
  font-weight: 600;
}

.state-metrics {
  font-size: 12px;
  opacity: 0.85;
  font-family: 'Courier New', monospace;
}

.state-reason {
  font-size: 13px;
  color: var(--kite-text-secondary, #666);
  padding: 10px 14px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
  border-left: 4px solid var(--kite-border, #e8e8e8);
}

.state-behavior {
  font-size: 13px;
  padding: 12px 16px;
  border-radius: 6px;
  background: var(--kite-bg-light, #f8f9fa);
}

.behavior-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.state-behavior ul {
  margin: 0;
  padding-left: 20px;
  list-style-type: disc;
}

.state-behavior li {
  margin: 4px 0;
  color: var(--kite-text-secondary, #666);
}

/* State-specific colors */
.state-normal {
  border-color: var(--kite-green, #00b386);
  color: var(--kite-green, #00b386);
  background: rgba(0, 179, 134, 0.05);
}

.state-normal .state-icon {
  color: var(--kite-green, #00b386);
}

.state-degraded {
  border-color: #ff9800;
  color: #ff9800;
  background: rgba(255, 152, 0, 0.08);
}

.state-degraded .state-icon {
  color: #ff9800;
}

.state-degraded .state-reason {
  border-left-color: #ff9800;
}

.state-paused {
  border-color: var(--kite-red, #e53935);
  color: var(--kite-red, #e53935);
  background: rgba(229, 57, 53, 0.08);
}

.state-paused .state-icon {
  color: var(--kite-red, #e53935);
}

.state-paused .state-reason {
  border-left-color: var(--kite-red, #e53935);
}
</style>
