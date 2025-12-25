<template>
  <div class="market-regime-indicator" data-testid="market-regime-indicator">
    <div class="regime-badge" :class="regimeClass" data-testid="regime-badge">
      <div class="regime-icon">
        <i :class="regimeIcon"></i>
      </div>
      <div class="regime-content">
        <div class="regime-type" data-testid="regime-type">{{ regimeLabel }}</div>
        <div class="regime-confidence" data-testid="regime-confidence">
          {{ confidence }}% confidence
        </div>
      </div>
    </div>
    <div v-if="reasoning" class="regime-reasoning" data-testid="regime-reasoning">
      {{ reasoning }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  regimeType: {
    type: String,
    required: true,
    validator: (value) => [
      'TRENDING_BULLISH',
      'TRENDING_BEARISH',
      'RANGEBOUND',
      'VOLATILE',
      'PRE_EVENT',
      'EVENT_DAY'
    ].includes(value)
  },
  confidence: {
    type: Number,
    required: true,
    default: 0
  },
  reasoning: {
    type: String,
    default: ''
  }
})

const regimeClass = computed(() => {
  const baseClass = 'regime-'
  switch (props.regimeType) {
    case 'TRENDING_BULLISH':
      return `${baseClass}bullish`
    case 'TRENDING_BEARISH':
      return `${baseClass}bearish`
    case 'RANGEBOUND':
      return `${baseClass}neutral`
    case 'VOLATILE':
      return `${baseClass}volatile`
    case 'PRE_EVENT':
    case 'EVENT_DAY':
      return `${baseClass}event`
    default:
      return `${baseClass}neutral`
  }
})

const regimeIcon = computed(() => {
  switch (props.regimeType) {
    case 'TRENDING_BULLISH':
      return 'fas fa-arrow-trend-up'
    case 'TRENDING_BEARISH':
      return 'fas fa-arrow-trend-down'
    case 'RANGEBOUND':
      return 'fas fa-arrows-left-right'
    case 'VOLATILE':
      return 'fas fa-wave-square'
    case 'PRE_EVENT':
    case 'EVENT_DAY':
      return 'fas fa-calendar-day'
    default:
      return 'fas fa-circle-question'
  }
})

const regimeLabel = computed(() => {
  return props.regimeType.replace(/_/g, ' ').toLowerCase()
    .replace(/\b\w/g, l => l.toUpperCase())
})
</script>

<style scoped>
.market-regime-indicator {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.regime-badge {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  font-weight: 500;
  border: 2px solid;
  background: white;
  transition: all 0.2s ease;
}

.regime-icon {
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.regime-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.regime-type {
  font-size: 15px;
  font-weight: 600;
  text-transform: capitalize;
}

.regime-confidence {
  font-size: 12px;
  opacity: 0.8;
}

.regime-reasoning {
  font-size: 13px;
  color: var(--kite-text-secondary, #666);
  padding: 8px 12px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
  border-left: 3px solid var(--kite-border, #e8e8e8);
}

/* Regime-specific colors */
.regime-bullish {
  border-color: var(--kite-green, #00b386);
  color: var(--kite-green, #00b386);
  background: rgba(0, 179, 134, 0.05);
}

.regime-bearish {
  border-color: var(--kite-red, #e53935);
  color: var(--kite-red, #e53935);
  background: rgba(229, 57, 53, 0.05);
}

.regime-neutral {
  border-color: var(--kite-primary, #387ed1);
  color: var(--kite-primary, #387ed1);
  background: rgba(56, 126, 209, 0.05);
}

.regime-volatile {
  border-color: #ff9800;
  color: #ff9800;
  background: rgba(255, 152, 0, 0.05);
}

.regime-event {
  border-color: #9c27b0;
  color: #9c27b0;
  background: rgba(156, 39, 176, 0.05);
}
</style>
