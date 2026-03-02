<template>
  <div
    class="leg-card"
    :class="[legStatusClass, { 'show-greeks': showGreeks }]"
    :data-testid="`autopilot-leg-card-${leg.leg_id}`"
  >
    <!-- Leg Info Section -->
    <div class="leg-info">
      <div class="leg-type" :class="leg.action.toLowerCase()">
        {{ leg.action }} {{ leg.contract_type }}
      </div>
      <div class="leg-details">
        <span class="leg-strike">{{ leg.strike }}</span>
        <span class="leg-expiry">{{ formatExpiry(leg.expiry) }}</span>
        <span class="leg-lots">{{ leg.lots }} lot(s)</span>
      </div>
    </div>

    <!-- P&L Section -->
    <div class="leg-metrics">
      <div class="metric-item">
        <span class="metric-label">Entry</span>
        <span class="metric-value">₹{{ leg.entry_price?.toFixed(2) }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">CMP</span>
        <span class="metric-value">₹{{ currentPrice?.toFixed(2) || '-' }}</span>
      </div>
      <div
        class="metric-item pnl-item"
        :data-testid="`autopilot-leg-pnl-${leg.leg_id}`"
        :data-pnl-polarity="unrealizedPnL >= 0 ? 'positive' : 'negative'"
      >
        <span class="metric-label">P&L</span>
        <span class="metric-value" :class="pnlClass">
          {{ formatPnL(unrealizedPnL) }}
        </span>
      </div>
    </div>

    <!-- Greeks Section (conditional) -->
    <div v-if="showGreeks" class="leg-greeks">
      <div class="greek-item" :data-testid="`autopilot-leg-delta-${leg.leg_id}`">
        <span class="greek-label">Δ</span>
        <span class="greek-value">{{ formatGreek(leg.delta) }}</span>
      </div>
      <div class="greek-item" :data-testid="`autopilot-leg-gamma-${leg.leg_id}`">
        <span class="greek-label">Γ</span>
        <span class="greek-value">{{ formatGreek(leg.gamma) }}</span>
      </div>
      <div class="greek-item" :data-testid="`autopilot-leg-theta-${leg.leg_id}`">
        <span class="greek-label">Θ</span>
        <span class="greek-value">{{ formatGreek(leg.theta) }}</span>
      </div>
      <div class="greek-item" :data-testid="`autopilot-leg-vega-${leg.leg_id}`">
        <span class="greek-label">V</span>
        <span class="greek-value">{{ formatGreek(leg.vega) }}</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="leg-actions">
      <button
        @click="$emit('exit')"
        class="action-btn exit-btn"
        :data-testid="`autopilot-leg-exit-btn-${leg.leg_id}`"
        title="Exit this leg"
      >
        Exit
      </button>
      <button
        @click="$emit('shift')"
        class="action-btn shift-btn"
        :data-testid="`autopilot-leg-shift-btn-${leg.leg_id}`"
        title="Shift to new strike"
      >
        Shift
      </button>
      <button
        @click="$emit('roll')"
        class="action-btn roll-btn"
        :data-testid="`autopilot-leg-roll-btn-${leg.leg_id}`"
        title="Roll to new expiry"
      >
        Roll
      </button>
      <button
        @click="$emit('break')"
        class="action-btn break-btn"
        :data-testid="`autopilot-leg-break-btn-${leg.leg_id}`"
        title="Break trade"
      >
        Break
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  leg: {
    type: Object,
    required: true
  },
  livePrices: {
    type: Object,
    default: () => ({})
  },
  showGreeks: {
    type: Boolean,
    default: false
  }
})

// Get live CMP from WebSocket or fall back to leg's current_price
const currentPrice = computed(() => {
  if (props.leg.instrument_token && props.livePrices[props.leg.instrument_token]?.ltp) {
    return props.livePrices[props.leg.instrument_token].ltp
  }
  return props.leg.current_price
})

// Calculate live unrealized P/L based on current price
const unrealizedPnL = computed(() => {
  const cmp = currentPrice.value
  if (!cmp || !props.leg.entry_price) return props.leg.unrealized_pnl || 0

  const qty = props.leg.quantity || (props.leg.lots * 50) // lot size fallback
  const multiplier = props.leg.action === 'BUY' ? 1 : -1
  return (cmp - props.leg.entry_price) * Math.abs(qty) * multiplier
})

const emit = defineEmits(['exit', 'shift', 'roll', 'break'])

const legStatusClass = computed(() => {
  return props.leg.status ? `status-${props.leg.status}` : ''
})

const pnlClass = computed(() => {
  const pnl = unrealizedPnL.value || 0
  if (pnl > 0) return 'profit positive green'
  if (pnl < 0) return 'loss negative red'
  return ''
})

const formatExpiry = (expiry) => {
  if (!expiry) return '-'
  const date = new Date(expiry)
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })
}

const formatPnL = (pnl) => {
  if (pnl === null || pnl === undefined) return '₹0'
  const prefix = pnl >= 0 ? '+' : ''
  return `${prefix}₹${pnl.toFixed(2)}`
}

const formatGreek = (value) => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(4)
}
</script>

<style scoped>
.leg-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.2s;
}

.leg-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.leg-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.leg-type {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
  width: fit-content;
}

.leg-type.buy {
  background: #dbeafe;
  color: #1e40af;
}

.leg-type.sell {
  background: #fee2e2;
  color: #991b1b;
}

.leg-details {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.leg-strike {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.leg-expiry {
  font-size: 13px;
  color: #6b7280;
}

.leg-lots {
  font-size: 13px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
}

.leg-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 11px;
  color: #9ca3af;
  text-transform: uppercase;
  font-weight: 500;
}

.metric-value {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.pnl-item .metric-value.profit,
.pnl-item .metric-value.positive,
.pnl-item .metric-value.green {
  color: #16a34a;
}

.pnl-item .metric-value.loss,
.pnl-item .metric-value.negative,
.pnl-item .metric-value.red {
  color: #dc2626;
}

.leg-greeks {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.greek-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.greek-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}

.greek-value {
  font-size: 14px;
  font-family: 'Courier New', monospace;
  color: #111827;
  font-weight: 600;
}

.leg-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.action-btn {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.exit-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.shift-btn:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #2563eb;
}

.roll-btn:hover {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #16a34a;
}

.break-btn:hover {
  background: #fefce8;
  border-color: #fde047;
  color: #ca8a04;
}

.status-open {
  border-left: 4px solid #16a34a;
}

.status-closed {
  opacity: 0.7;
  border-left: 4px solid #9ca3af;
}

.status-pending {
  border-left: 4px solid #f59e0b;
}
</style>
