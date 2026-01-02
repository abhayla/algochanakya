<template>
  <KiteLayout>
    <div class="ofo-page" data-testid="ofo-page">

      <!-- Page Header -->
      <div class="page-header" data-testid="ofo-header">
        <div class="header-left">
          <h1 class="page-title">OFO</h1>
          <span class="page-subtitle">Options For Options</span>

          <!-- Underlying Tabs -->
          <div class="underlying-tabs" data-testid="ofo-underlying-tabs">
            <button
              v-for="ul in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']"
              :key="ul"
              :class="['tab-btn', { active: store.underlying === ul }]"
              @click="handleUnderlyingChange(ul)"
              :data-testid="'ofo-underlying-' + ul.toLowerCase()"
            >
              {{ ul }}
            </button>
          </div>
        </div>

        <div class="header-right">
          <!-- Spot Price Box -->
          <div class="spot-box" data-testid="ofo-spot-box">
            <span class="spot-label">Spot</span>
            <span class="spot-price" data-testid="ofo-spot-price">
              {{ store.spotPrice ? formatNumber(store.spotPrice) : '-' }}
            </span>
          </div>

          <!-- Lot Size -->
          <div class="lot-box" data-testid="ofo-lot-box">
            <span class="lot-label">Lot Size</span>
            <span class="lot-value">{{ store.lotSize }}</span>
          </div>

          <!-- Calculation Time -->
          <div v-if="store.calculationTimeMs > 0" class="calc-time-box" data-testid="ofo-calc-time">
            <span class="calc-label">Calc Time</span>
            <span class="calc-value">{{ store.calculationTimeMs }}ms</span>
          </div>
        </div>
      </div>

      <!-- Controls Bar -->
      <div class="controls-bar" data-testid="ofo-controls">
        <!-- Expiry Select -->
        <div class="control-group">
          <label class="control-label">Expiry</label>
          <select
            v-model="store.expiry"
            class="expiry-select"
            data-testid="ofo-expiry-select"
          >
            <option v-for="exp in store.expiries" :key="exp" :value="exp">
              {{ formatExpiry(exp) }}
            </option>
          </select>
        </div>

        <!-- Strategy Multi-Select -->
        <div class="control-group">
          <label class="control-label">Strategies</label>
          <StrategyMultiSelect />
        </div>

        <!-- Strike Range -->
        <div class="control-group">
          <label class="control-label">Strike Range</label>
          <select
            v-model.number="store.strikeRange"
            class="range-select"
            data-testid="ofo-strike-range"
          >
            <option :value="5">±5 strikes</option>
            <option :value="10">±10 strikes</option>
            <option :value="15">±15 strikes</option>
            <option :value="20">±20 strikes</option>
          </select>
        </div>

        <!-- Lots Input -->
        <div class="control-group">
          <label class="control-label">Lots</label>
          <input
            type="number"
            v-model.number="store.lots"
            min="1"
            max="50"
            class="lots-input"
            data-testid="ofo-lots-input"
          />
        </div>

        <!-- Calculate Button -->
        <button
          class="calculate-btn"
          :disabled="store.isLoading || store.selectedCount === 0"
          @click="handleCalculate"
          data-testid="ofo-calculate-btn"
        >
          <svg v-if="store.isLoading" class="spinner" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="30 70" />
          </svg>
          {{ store.isLoading ? 'Calculating...' : 'Calculate' }}
        </button>

        <!-- Auto-Refresh -->
        <div class="auto-refresh-group">
          <label class="auto-refresh-toggle" data-testid="ofo-auto-refresh">
            <input
              type="checkbox"
              :checked="store.autoRefreshEnabled"
              @change="store.toggleAutoRefresh()"
            />
            <span>Auto</span>
          </label>
          <select
            v-model.number="store.autoRefreshInterval"
            class="interval-select"
            :disabled="!store.autoRefreshEnabled"
            @change="store.setAutoRefreshInterval(store.autoRefreshInterval)"
            data-testid="ofo-refresh-interval"
          >
            <option :value="5">5 min</option>
            <option :value="10">10 min</option>
            <option :value="15">15 min</option>
            <option :value="30">30 min</option>
          </select>
        </div>

        <!-- Last Calculated -->
        <div
          v-if="store.lastCalculatedFormatted"
          class="last-calculated"
          data-testid="ofo-last-calculated"
        >
          <span class="calc-label">Last:</span>
          <span class="calc-time">{{ store.lastCalculatedFormatted }}</span>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="store.error" class="error-message" data-testid="ofo-error">
        {{ store.error }}
      </div>

      <!-- Loading State -->
      <div v-if="store.isLoading" class="loading-state" data-testid="ofo-loading">
        <div class="loading-spinner"></div>
        <p>Calculating best strategies...</p>
        <p class="loading-hint">Evaluating {{ store.selectedCount }} strategy type(s)</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="!store.hasResults && store.selectedCount === 0" class="empty-state" data-testid="ofo-empty">
        <div class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="7.5 4.21 12 6.81 16.5 4.21"></polyline>
            <polyline points="7.5 19.79 7.5 14.6 3 12"></polyline>
            <polyline points="21 12 16.5 14.6 16.5 19.79"></polyline>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
          </svg>
        </div>
        <h2>Select Strategies to Begin</h2>
        <p>Choose one or more strategy types from the dropdown above, then click "Calculate" to find the best combinations.</p>
      </div>

      <!-- Results Section -->
      <div v-else class="results-section" data-testid="ofo-results">
        <!-- Strategy Groups -->
        <div
          v-for="strategyType in store.selectedStrategies"
          :key="strategyType"
          class="strategy-group"
          :data-testid="`ofo-group-${strategyType}`"
        >
          <h2 class="group-title">
            {{ store.getStrategyName(strategyType) }}
            <span v-if="store.results[strategyType]" class="result-count">
              ({{ store.results[strategyType].length }} results)
            </span>
          </h2>

          <div v-if="store.results[strategyType]?.length > 0" class="cards-row">
            <OFOResultCard
              v-for="(result, idx) in store.results[strategyType]"
              :key="`${strategyType}-${idx}`"
              :result="result"
              :rank="idx + 1"
              @open-in-builder="handleOpenInBuilder"
              @place-order="handlePlaceOrder"
            />
          </div>

          <div v-else class="no-results">
            <p>No valid combinations found for {{ store.getStrategyName(strategyType) }}</p>
          </div>
        </div>
      </div>

    </div>
  </KiteLayout>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import StrategyMultiSelect from '@/components/ofo/StrategyMultiSelect.vue'
import OFOResultCard from '@/components/ofo/OFOResultCard.vue'
import { useOFOStore } from '@/stores/ofo'

const router = useRouter()
const store = useOFOStore()

// Initialize on mount
onMounted(async () => {
  await store.fetchExpiries()
})

// Cleanup on unmount
onUnmounted(() => {
  store.stopAutoRefresh()
})

// Handlers
async function handleUnderlyingChange(ul) {
  await store.setUnderlying(ul)
}

async function handleCalculate() {
  await store.calculate()
}

async function handleOpenInBuilder(result) {
  const route = await store.openInStrategyBuilder(result)
  router.push(route)
}

function handlePlaceOrder(result) {
  // TODO: Open basket order modal
  console.log('[OFO] Place order:', result)
  alert('Place Order functionality coming soon!')
}

// Formatters
function formatExpiry(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function formatNumber(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('en-IN').format(value)
}
</script>

<style scoped>
.ofo-page {
  padding: 16px 24px;
  min-height: calc(100vh - 60px);
  background: var(--kite-body-bg, #ffffff);
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--kite-text-secondary, #6c757d);
}

.underlying-tabs {
  display: flex;
  gap: 4px;
  background: var(--kite-table-header-bg, #fafbfc);
  padding: 4px;
  border-radius: 3px;
  border: 1px solid var(--kite-border, #e8e8e8);
}

.tab-btn {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: var(--kite-text-secondary, #6c757d);
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: var(--kite-text-primary, #394046);
  background: var(--kite-border-light, #f5f5f5);
}

.tab-btn.active {
  background: var(--kite-primary, #2d68b0);
  color: white;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.spot-box,
.lot-box,
.calc-time-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 12px;
  background: var(--kite-table-header-bg, #fafbfc);
  border-radius: 4px;
  border: 1px solid var(--kite-border, #e8e8e8);
}

.spot-label,
.lot-label,
.calc-label {
  font-size: 11px;
  color: var(--kite-text-secondary, #6c757d);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.spot-price {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

.lot-value,
.calc-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

/* Controls Bar */
.controls-bar {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 16px;
  background: var(--kite-card-bg, #ffffff);
  border-radius: 4px;
  border: 1px solid var(--kite-border, #e8e8e8);
  box-shadow: var(--kite-shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.control-label {
  font-size: 11px;
  color: var(--kite-text-secondary, #6c757d);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.expiry-select,
.range-select,
.interval-select {
  padding: 8px 12px;
  font-size: 14px;
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 3px;
  color: var(--kite-text-primary, #394046);
  cursor: pointer;
  min-width: 120px;
  transition: border-color 0.15s ease;
}

.expiry-select:focus,
.range-select:focus,
.interval-select:focus {
  outline: none;
  border-color: var(--kite-primary, #2d68b0);
}

.lots-input {
  width: 70px;
  padding: 8px 12px;
  font-size: 14px;
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 3px;
  color: var(--kite-text-primary, #394046);
  text-align: center;
  transition: border-color 0.15s ease;
}

.lots-input:focus {
  outline: none;
  border-color: var(--kite-primary, #2d68b0);
}

.calculate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  background: var(--kite-primary, #2d68b0);
  border: none;
  border-radius: 3px;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
}

.calculate-btn:hover:not(:disabled) {
  background: var(--kite-primary-dark, #245290);
}

.calculate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auto-refresh-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auto-refresh-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--kite-text-secondary, #6c757d);
  cursor: pointer;
}

.auto-refresh-toggle input {
  accent-color: var(--kite-primary, #2d68b0);
}

.interval-select:disabled {
  opacity: 0.5;
}

.last-calculated {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: var(--kite-text-secondary, #6c757d);
}

.calc-time {
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

/* Error Message */
.error-message {
  padding: 12px 16px;
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red, #e53935);
  border-radius: 4px;
  color: var(--kite-red-text, #d43f3a);
  margin-bottom: 16px;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid var(--kite-border, #e8e8e8);
  border-top-color: var(--kite-primary, #2d68b0);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.loading-state p {
  color: var(--kite-text-secondary, #6c757d);
  margin: 4px 0;
}

.loading-hint {
  font-size: 13px;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 24px;
  color: var(--kite-text-muted, #727272);
}

.empty-state h2 {
  font-size: 20px;
  color: var(--kite-text-primary, #394046);
  margin: 0 0 8px 0;
}

.empty-state p {
  color: var(--kite-text-secondary, #6c757d);
  max-width: 400px;
}

/* Results Section */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.strategy-group {
  background: var(--kite-card-bg, #ffffff);
  border-radius: 4px;
  border: 1px solid var(--kite-border, #e8e8e8);
  box-shadow: var(--kite-shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
  padding: 20px;
}

.group-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-count {
  font-size: 14px;
  font-weight: 400;
  color: var(--kite-text-secondary, #6c757d);
}

.cards-row {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.no-results {
  padding: 24px;
  text-align: center;
  color: var(--kite-text-secondary, #6c757d);
}

.no-results p {
  margin: 0;
}

/* Scrollbar Styling */
.cards-row::-webkit-scrollbar {
  height: 6px;
}

.cards-row::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.cards-row::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.cards-row::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
