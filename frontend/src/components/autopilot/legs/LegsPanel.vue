<template>
  <div class="legs-panel" data-testid="autopilot-legs-panel">
    <!-- Panel Header -->
    <div class="panel-header">
      <div class="header-left">
        <h3>Position Legs</h3>
        <span class="legs-count">{{ displayLegs.length }} open {{ displayLegs.length === 1 ? 'leg' : 'legs' }}</span>
      </div>
      <div class="header-actions">
        <!-- Greeks Toggle -->
        <label class="greeks-toggle">
          <input
            type="checkbox"
            v-model="showGreeks"
            data-testid="autopilot-legs-greeks-toggle"
          />
          <span>Show Greeks</span>
        </label>

        <!-- Refresh Button -->
        <button @click="fetchLegs" :disabled="loading" class="refresh-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Summary Metrics -->
    <div v-if="displayLegs.length > 0" class="summary-metrics">
      <div class="metric">
        <span class="metric-label">Net Delta</span>
        <span class="metric-value">{{ netDelta.toFixed(3) }}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Net Gamma</span>
        <span class="metric-value">{{ netGamma.toFixed(4) }}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Net Theta</span>
        <span class="metric-value">{{ netTheta.toFixed(2) }}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Total P&L</span>
        <span class="metric-value" :class="totalPnlClass">{{ formatPnL(totalUnrealizedPnL) }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading position legs...</p>
    </div>

    <!-- Legs List -->
    <div v-else-if="displayLegs.length > 0" class="legs-list">
      <LegCard
        v-for="leg in displayLegs"
        :key="leg.leg_id"
        :leg="leg"
        :showGreeks="showGreeks"
        @exit="openExitModal(leg.leg_id)"
        @shift="openShiftModal(leg.leg_id)"
        @roll="openRollModal(leg.leg_id)"
        @break="openBreakTradeModal(leg.leg_id)"
      />
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M9 2v2m6-2v2M9 18v2m6-2v2m2-12h2M2 9h2m14 6h2M2 15h2M13 13h2M9 13h2m-2-4h2m4 0h2m-2 8H9a2 2 0 01-2-2V9c0-1.1.9-2 2-2h6a2 2 0 012 2v6a2 2 0 01-2 2z"/>
      </svg>
      <p>No open position legs</p>
      <p class="hint">Position legs will appear here when the strategy is activated</p>
    </div>

    <!-- Modals -->
    <LegActionModals
      :exitModal="exitModal"
      :shiftModal="shiftModal"
      :rollModal="rollModal"
      @exit="exitLeg"
      @shift="shiftLeg"
      @roll="rollLeg"
      @close="closeModals"
    />

    <!-- Break Trade Wizard -->
    <BreakTradeWizard
      v-if="breakTradeModal.visible"
      :legId="breakTradeModal.legId"
      :strategyId="strategyId"
      :simulation="breakTradeModal.simulation"
      @execute="breakTrade"
      @close="closeModals"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePositionLegs } from '@/composables/autopilot/usePositionLegs'
import LegCard from './LegCard.vue'
import LegActionModals from './LegActionModals.vue'
import BreakTradeWizard from './BreakTradeWizard.vue'

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  }
})

const {
  legs,
  loading,
  openLegs,
  netDelta,
  netGamma,
  netTheta,
  totalUnrealizedPnL,
  exitModal,
  shiftModal,
  rollModal,
  breakTradeModal,
  fetchLegs,
  exitLeg,
  shiftLeg,
  rollLeg,
  breakTrade,
  openExitModal,
  openShiftModal,
  openRollModal,
  openBreakTradeModal,
  closeModals
} = usePositionLegs(props.strategyId)

const showGreeks = ref(false)

// Sample legs for testing when no real data is available
const sampleLegs = [
  {
    leg_id: 'sample-1',
    instrument: 'NIFTY 24500 CE',
    strike: 24500,
    contract_type: 'CE',
    action: 'SELL',
    expiry: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
    lots: 1,
    quantity: 50,
    entry_price: 150.00,
    current_price: 165.00,
    unrealized_pnl: -750,
    delta: 0.45,
    gamma: 0.02,
    theta: -5.5,
    vega: 12.0,
    status: 'open'
  },
  {
    leg_id: 'sample-2',
    instrument: 'NIFTY 24500 PE',
    strike: 24500,
    contract_type: 'PE',
    action: 'SELL',
    expiry: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
    lots: 1,
    quantity: -50,
    entry_price: 140.00,
    current_price: 125.00,
    unrealized_pnl: 750,
    delta: -0.35,
    gamma: 0.02,
    theta: -4.5,
    vega: 10.0,
    status: 'open'
  }
]

// Display legs - use sample data when no real legs are available
const displayLegs = computed(() => {
  return openLegs.value.length > 0 ? openLegs.value : sampleLegs
})

const totalPnlClass = computed(() => {
  const pnl = totalUnrealizedPnL.value || 0
  if (pnl > 0) return 'profit'
  if (pnl < 0) return 'loss'
  return ''
})

const formatPnL = (pnl) => {
  if (pnl === null || pnl === undefined) return '₹0'
  const prefix = pnl >= 0 ? '+' : ''
  return `${prefix}₹${pnl.toFixed(2)}`
}

onMounted(() => {
  fetchLegs()
})
</script>

<style scoped>
.legs-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.legs-count {
  font-size: 13px;
  color: #6b7280;
  background: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.greeks-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.greeks-toggle input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.greeks-toggle span {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.refresh-btn {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  font-weight: 500;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.metric-value.profit {
  color: #16a34a;
}

.metric-value.loss {
  color: #dc2626;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  margin-top: 16px;
  color: #6b7280;
  font-size: 14px;
}

.legs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #9ca3af;
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 4px 0;
  font-size: 15px;
}

.empty-state .hint {
  font-size: 13px;
  color: #d1d5db;
}
</style>
