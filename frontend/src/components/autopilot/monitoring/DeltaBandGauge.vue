<template>
  <div class="delta-band-gauge" :class="`severity-${severity}`">
    <div class="gauge-header">
      <span class="gauge-title">Net Delta Monitor</span>
      <span class="gauge-value" :class="`delta-${deltaSign}`">
        {{ formatDelta(netDelta) }}
      </span>
    </div>

    <div class="gauge-visual">
      <div class="band-range">
        <span class="band-limit">-{{ threshold }}</span>
        <div class="band-bar">
          <div class="safe-zone" :style="safeZoneStyle"></div>
          <div class="current-delta-marker" :style="deltaMarkerStyle">
            <div class="delta-dot"></div>
          </div>
        </div>
        <span class="band-limit">+{{ threshold }}</span>
      </div>
    </div>

    <div v-if="outOfBand" class="rebalance-alert" :class="`severity-${severity}`">
      <div class="alert-icon">⚠️</div>
      <div class="alert-content">
        <div class="alert-title">
          {{ severity === 'critical' ? 'CRITICAL' : 'WARNING' }}: Delta Out of Band
        </div>
        <div class="alert-suggestion" v-if="suggestedAction">
          {{ suggestedAction }}
        </div>
        <div class="alert-alternative" v-if="alternativeAction">
          Alternative: {{ alternativeAction }}
        </div>
      </div>
    </div>

    <div v-else class="status-ok">
      <span class="ok-icon">✓</span>
      <span>Delta within acceptable range</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  netDelta: {
    type: Number,
    default: 0
  },
  threshold: {
    type: Number,
    default: 0.15
  },
  outOfBand: {
    type: Boolean,
    default: false
  },
  severity: {
    type: String,
    default: 'ok', // 'ok', 'warning', 'critical'
    validator: (value) => ['ok', 'warning', 'critical'].includes(value)
  },
  suggestedAction: {
    type: String,
    default: null
  },
  alternativeAction: {
    type: String,
    default: null
  }
})

const deltaSign = computed(() => {
  if (props.netDelta > 0) return 'positive'
  if (props.netDelta < 0) return 'negative'
  return 'neutral'
})

const formatDelta = (delta) => {
  const sign = delta >= 0 ? '+' : ''
  return `${sign}${delta.toFixed(3)}`
}

// Calculate position of delta marker (0-100%)
const deltaMarkerStyle = computed(() => {
  // Map delta to position on the bar
  // -threshold -> 0%, 0 -> 50%, +threshold -> 100%
  const range = props.threshold * 2
  const position = ((props.netDelta + props.threshold) / range) * 100
  const clampedPosition = Math.max(0, Math.min(100, position))

  return {
    left: `${clampedPosition}%`
  }
})

// Safe zone (within threshold) highlighting
const safeZoneStyle = computed(() => {
  // Safe zone is middle 50% (from 25% to 75%)
  const safeZoneStart = 25
  const safeZoneWidth = 50

  return {
    left: `${safeZoneStart}%`,
    width: `${safeZoneWidth}%`
  }
})
</script>

<style scoped>
.delta-band-gauge {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border: 2px solid #e5e7eb;
}

.delta-band-gauge.severity-warning {
  border-color: #f59e0b;
}

.delta-band-gauge.severity-critical {
  border-color: #ef4444;
}

.gauge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.gauge-title {
  font-weight: 600;
  color: #374151;
  font-size: 14px;
}

.gauge-value {
  font-size: 20px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.gauge-value.delta-positive {
  color: #10b981;
}

.gauge-value.delta-negative {
  color: #ef4444;
}

.gauge-value.delta-neutral {
  color: #6b7280;
}

.gauge-visual {
  margin: 16px 0;
}

.band-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.band-limit {
  font-size: 12px;
  color: #6b7280;
  font-family: 'Courier New', monospace;
  min-width: 45px;
  text-align: center;
}

.band-bar {
  flex: 1;
  height: 32px;
  background: linear-gradient(to right,
    #fecaca 0%,
    #fef3c7 25%,
    #d1fae5 25%,
    #d1fae5 75%,
    #fef3c7 75%,
    #fecaca 100%
  );
  border-radius: 16px;
  position: relative;
  border: 1px solid #d1d5db;
}

.safe-zone {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(16, 185, 129, 0.2);
  border-left: 2px dashed #10b981;
  border-right: 2px dashed #10b981;
}

.current-delta-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  transition: left 0.3s ease;
}

.delta-dot {
  width: 16px;
  height: 16px;
  background: #3b82f6;
  border: 3px solid white;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.rebalance-alert {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.rebalance-alert.severity-warning {
  background: #fef3c7;
  border: 1px solid #f59e0b;
}

.rebalance-alert.severity-critical {
  background: #fee2e2;
  border: 1px solid #ef4444;
}

.alert-icon {
  font-size: 20px;
  line-height: 1;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
  color: #1f2937;
}

.alert-suggestion {
  font-size: 13px;
  color: #374151;
  margin-bottom: 4px;
}

.alert-alternative {
  font-size: 12px;
  color: #6b7280;
  font-style: italic;
}

.status-ok {
  margin-top: 12px;
  padding: 8px 12px;
  background: #d1fae5;
  border: 1px solid #10b981;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #065f46;
}

.ok-icon {
  font-size: 16px;
  color: #10b981;
  font-weight: bold;
}
</style>
