<template>
  <div class="ai-decision-card" :class="decisionClass" data-testid="ai-decision-card">
    <div class="decision-header">
      <div class="decision-type-badge" data-testid="decision-type-badge">
        <i :class="typeIcon"></i>
        <span>{{ typeLabel }}</span>
      </div>
      <div class="decision-time" data-testid="decision-time">
        {{ formattedTime }}
      </div>
    </div>

    <div class="decision-body">
      <div class="decision-action" data-testid="decision-action">
        {{ decision.action_taken }}
      </div>

      <div class="decision-confidence" data-testid="decision-confidence">
        <div class="confidence-label">Confidence</div>
        <div class="confidence-bar-container">
          <div class="confidence-bar" :style="{ width: decision.confidence + '%' }"></div>
        </div>
        <div class="confidence-value">{{ decision.confidence }}%</div>
      </div>

      <div v-if="decision.reasoning" class="decision-reasoning" data-testid="decision-reasoning">
        <div class="reasoning-label">
          <i class="fas fa-lightbulb"></i> AI Reasoning
        </div>
        <div class="reasoning-text">{{ decision.reasoning }}</div>
      </div>

      <div class="decision-context" data-testid="decision-context">
        <div class="context-item" v-if="decision.regime_at_decision">
          <span class="context-label">Regime:</span>
          <span class="context-value">{{ formatRegime(decision.regime_at_decision) }}</span>
        </div>
        <div class="context-item" v-if="decision.vix_at_decision">
          <span class="context-label">VIX:</span>
          <span class="context-value">{{ decision.vix_at_decision }}</span>
        </div>
        <div class="context-item" v-if="decision.spot_at_decision">
          <span class="context-label">Spot:</span>
          <span class="context-value">{{ decision.spot_at_decision }}</span>
        </div>
      </div>

      <div v-if="decision.outcome_pnl !== null && decision.outcome_pnl !== undefined" class="decision-outcome" data-testid="decision-outcome">
        <div class="outcome-label">Outcome</div>
        <div class="outcome-pnl" :class="decision.outcome_pnl >= 0 ? 'profit' : 'loss'">
          {{ formatPnl(decision.outcome_pnl) }}
        </div>
        <div v-if="decision.was_correct !== null" class="outcome-correctness">
          <i :class="decision.was_correct ? 'fas fa-check-circle correct' : 'fas fa-times-circle incorrect'"></i>
          {{ decision.was_correct ? 'Correct' : 'Incorrect' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  decision: {
    type: Object,
    required: true
  }
})

const decisionClass = computed(() => {
  return `decision-${props.decision.decision_type}`
})

const typeIcon = computed(() => {
  switch (props.decision.decision_type) {
    case 'strategy_selection':
      return 'fas fa-chess-knight'
    case 'entry':
      return 'fas fa-door-open'
    case 'adjustment':
      return 'fas fa-sliders'
    case 'exit':
      return 'fas fa-door-closed'
    case 'regime_change':
      return 'fas fa-exchange-alt'
    case 'health_alert':
      return 'fas fa-exclamation-triangle'
    default:
      return 'fas fa-robot'
  }
})

const typeLabel = computed(() => {
  return props.decision.decision_type.replace(/_/g, ' ').toUpperCase()
})

const formattedTime = computed(() => {
  if (!props.decision.decision_time) return ''
  const date = new Date(props.decision.decision_time)
  return date.toLocaleString('en-IN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
})

const formatRegime = (regime) => {
  return regime.replace(/_/g, ' ').toLowerCase()
    .replace(/\b\w/g, l => l.toUpperCase())
}

const formatPnl = (pnl) => {
  const sign = pnl >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(pnl).toFixed(2)}`
}
</script>

<style scoped>
.ai-decision-card {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.ai-decision-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.decision-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.decision-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

.decision-time {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
}

.decision-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.decision-action {
  font-size: 15px;
  font-weight: 500;
  color: var(--kite-text-primary, #394046);
}

.decision-confidence {
  display: flex;
  align-items: center;
  gap: 10px;
}

.confidence-label {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
  min-width: 70px;
}

.confidence-bar-container {
  flex: 1;
  height: 6px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--kite-primary, #387ed1), var(--kite-green, #00b386));
  transition: width 0.3s ease;
}

.confidence-value {
  font-size: 13px;
  font-weight: 600;
  min-width: 45px;
  text-align: right;
}

.decision-reasoning {
  background: #fffbf0;
  border-left: 3px solid #ffc107;
  padding: 10px 12px;
  border-radius: 4px;
}

.reasoning-label {
  font-size: 12px;
  font-weight: 600;
  color: #f57c00;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.reasoning-text {
  font-size: 13px;
  color: var(--kite-text-primary, #394046);
  line-height: 1.5;
}

.decision-context {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding: 8px 0;
  border-top: 1px solid var(--kite-border, #e8e8e8);
}

.context-item {
  display: flex;
  gap: 6px;
  font-size: 12px;
}

.context-label {
  color: var(--kite-text-secondary, #666);
}

.context-value {
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

.decision-outcome {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
}

.outcome-label {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
}

.outcome-pnl {
  font-size: 16px;
  font-weight: 700;
}

.outcome-pnl.profit {
  color: var(--kite-green, #00b386);
}

.outcome-pnl.loss {
  color: var(--kite-red, #e53935);
}

.outcome-correctness {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.outcome-correctness .correct {
  color: var(--kite-green, #00b386);
}

.outcome-correctness .incorrect {
  color: var(--kite-red, #e53935);
}
</style>
