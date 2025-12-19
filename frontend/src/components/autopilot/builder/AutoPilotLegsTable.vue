<script setup>
/**
 * AutoPilot Legs Table Component
 * Main table container for AutoPilot legs configuration
 * Matches UI/UX pattern from Strategy Builder
 */
import { computed, ref, onMounted, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import { useWatchlistStore } from '@/stores/watchlist'
import api from '@/services/api'
import AutoPilotLegRow from './AutoPilotLegRow.vue'
import StrikeLadder from './StrikeLadder.vue'
import '@/assets/css/strategy-table.css'

const store = useAutopilotStore()
const watchlistStore = useWatchlistStore()

// Legs from builder strategy
const legs = computed(() => store.builder.strategy.legs_config)

// Get all leg tokens for subscription
const legTokens = computed(() => {
  return legs.value
    .filter(leg => leg.instrument_token)
    .map(leg => leg.instrument_token)
})

// All legs selected?
const allLegsSelected = computed(() => {
  return legs.value.length > 0 &&
    store.selectedLegIndices.length === legs.value.length
})

// Expected move data from API
const expectedMoveData = ref({ lower_bound: 0, upper_bound: 0 })

// StrikeLadder modal state
const showStrikeLadder = ref(false)
const currentLegIndex = ref(null)
const currentSpotPrice = ref(0)
const loadingSpotPrice = ref(false)
const loadingOptionChain = ref(false)

// Open strike ladder for a specific leg
const openStrikeLadder = async (legIndex) => {
  currentLegIndex.value = legIndex
  loadingSpotPrice.value = true

  // Fetch current spot price from API
  try {
    const underlying = store.builder.strategy.underlying || 'NIFTY'
    const response = await api.get(`/api/v1/autopilot/spot-price/${underlying}`)
    currentSpotPrice.value = response.data.data.ltp
  } catch (error) {
    console.error('Error fetching spot price:', error)
    // Fallback to approximate values
    const fallbackPrices = {
      'NIFTY': 24200,
      'BANKNIFTY': 52000,
      'FINNIFTY': 21000,
      'SENSEX': 80000
    }
    currentSpotPrice.value = fallbackPrices[store.builder.strategy.underlying] || 24200
  } finally {
    loadingSpotPrice.value = false
  }

  showStrikeLadder.value = true
}

// Handle strike selection from ladder
const onStrikeSelected = (strikeData) => {
  if (currentLegIndex.value !== null) {
    const leg = legs.value[currentLegIndex.value]
    handleLegUpdate(currentLegIndex.value, {
      strike_price: strikeData.strike,
      entry_price: strikeData.ltp,
      strike_selection: {
        mode: 'fixed',
        fixed_strike: strikeData.strike
      }
    })
    showStrikeLadder.value = false
    currentLegIndex.value = null
  }
}

// Fetch expiries on mount
onMounted(async () => {
  await store.fetchExpiries()
})

// Refetch expiries when underlying changes
watch(
  () => store.builder.strategy.underlying,
  async () => {
    await store.fetchExpiries()
  }
)

// Watch for legs being loaded and populate their expiry dates
watch(
  () => store.builder.strategy.legs_config.length,
  (newLength, oldLength) => {
    // When legs are loaded (length changes from 0 to non-zero), populate expiries
    if (newLength > 0 && oldLength === 0 && store.expiries.length > 0) {
      store.populateLegExpiries()
    }
  }
)

// Fetch expected move range when underlying, expiry_type, or expiries changes
watch(
  () => [
    store.builder.strategy.underlying,
    store.builder.strategy.expiry_type,
    store.builder.expiry,
    store.expiries
  ],
  async ([underlying, expiryType]) => {
    // Resolve expiry from expiry_type, or use explicit builder.expiry
    const expiry = store.getExpiryFromType(expiryType) || store.builder.expiry

    if (underlying && expiry) {
      try {
        const response = await api.get(
          `/api/v1/autopilot/option-chain/expected-move-range/${underlying}/${expiry}`
        )
        expectedMoveData.value = {
          lower_bound: response.data.lower_bound,
          upper_bound: response.data.upper_bound
        }
      } catch (error) {
        console.error('Error fetching expected move:', error)
        // Reset on error
        expectedMoveData.value = { lower_bound: 0, upper_bound: 0 }
      }
    }
  },
  { immediate: true }
)

// Subscribe to leg tokens for live prices
watch(
  legTokens,
  (tokens) => {
    if (tokens.length > 0 && watchlistStore.isConnected) {
      watchlistStore.subscribeToTokens(tokens, 'quote')
    }
  },
  { deep: true }
)

// Watch for tick updates and update live prices in store
watch(
  () => watchlistStore.ticks,
  (newTicks) => {
    const ticksArray = Object.entries(newTicks).map(([token, data]) => ({
      token: parseInt(token),
      ltp: data.ltp,
      change: data.change,
      change_percent: data.change_percent,
    }))
    if (ticksArray.length > 0) {
      store.updateLivePrices(ticksArray)
    }
  },
  { deep: true }
)

// Fetch LTP as fallback when instrument_token changes
watch(
  () => legs.value.map(l => l.instrument_token),
  () => {
    legs.value.forEach(leg => {
      if (leg.instrument_token && leg.tradingsymbol) {
        store.fetchLegLTP(leg)
      }
    })
  },
  { deep: true }
)

// Add a new leg
const addLeg = () => {
  store.addLeg({
    contract_type: 'CE',
    transaction_type: 'SELL',
    strike_price: null,
    expiry_date: store.getExpiryFromType(store.builder.strategy.expiry_type) || store.expiries[0] || null,
    lots: 1,
    entry_price: null,
    instrument_token: null,
    tradingsymbol: null,
    // AutoPilot-specific fields
    target_price: null,
    stop_loss_price: null,
    trailing_stop_loss: { enabled: false, trigger_profit: null, trail_amount: null },
    target_pct: null,
    stop_loss_pct: null,
    max_loss_amount: null,
    execution_order: legs.value.length + 1
  })
}

// Update a leg
const handleLegUpdate = (index, updates) => {
  store.updateLeg(index, updates)
}

// Delete a leg
const handleLegDelete = (index) => {
  store.removeLeg(index)
}

// Toggle leg selection
const toggleLegSelection = (index) => {
  store.toggleLegSelection(index)
}

// Toggle select all
const toggleSelectAll = () => {
  if (allLegsSelected.value) {
    store.deselectAllLegs()
  } else {
    store.selectAllLegs()
  }
}

// Delete selected legs
const deleteSelectedLegs = () => {
  store.removeSelectedLegs()
}

// Format expected move value from API data
const formatExpectedMove = (position) => {
  if (position === 'lower') {
    return Math.round(expectedMoveData.value.lower_bound || 0).toLocaleString()
  } else {
    return Math.round(expectedMoveData.value.upper_bound || 0).toLocaleString()
  }
}
</script>

<template>
  <div data-testid="autopilot-legs-section">
    <!-- Section Header -->
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-lg font-semibold">Strategy Legs</h2>
    </div>

    <!-- Expected Move Display -->
    <div
      v-if="store.builder.strategy.underlying"
      class="expected-move-display"
      data-testid="autopilot-expected-move-display"
    >
      <div class="expected-move-label">Expected Move Range:</div>
      <div class="expected-move-range">
        <span class="em-lower">{{ formatExpectedMove('lower') }}</span>
        <span class="em-separator">-</span>
        <span class="em-upper">{{ formatExpectedMove('upper') }}</span>
      </div>
      <div class="expected-move-hint">
        Based on ATM IV and DTE (Formula: Spot × IV × √(DTE/365))
      </div>
    </div>

    <!-- Table -->
    <div class="strategy-table-wrapper" data-testid="autopilot-legs-table">
      <div class="table-scroll">
        <table class="strategy-table">
          <thead>
            <tr>
              <th class="th-checkbox">
                <input
                  type="checkbox"
                  :checked="allLegsSelected"
                  @change="toggleSelectAll"
                  :disabled="legs.length === 0"
                  data-testid="autopilot-legs-select-all"
                />
              </th>
              <th>Action</th>
              <th>Expiry</th>
              <th>Strike</th>
              <th>Type</th>
              <th>Lots</th>
              <th>Entry</th>
              <th>CMP</th>
              <th>Exit P/L</th>
              <th>Target ₹</th>
              <th>SL ₹</th>
              <th>Trail</th>
              <th>Target %</th>
              <th>SL %</th>
              <th>Max Loss</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <!-- Leg Rows -->
            <AutoPilotLegRow
              v-for="(leg, index) in legs"
              :key="leg.id"
              :leg="leg"
              :index="index"
              @update="handleLegUpdate"
              @delete="handleLegDelete"
              @toggle-select="toggleLegSelection"
              @open-strike-ladder="openStrikeLadder"
            />

            <!-- Empty State -->
            <tr v-if="legs.length === 0" class="empty-state" data-testid="autopilot-legs-empty-state">
              <td colspan="16">
                No legs added. Click "+ Add Row" to start building your strategy.
              </td>
            </tr>

            <!-- Total Row -->
            <tr v-if="legs.length > 0" class="total-row" data-testid="autopilot-legs-total-row">
              <td colspan="5" class="text-right font-semibold">Total:</td>
              <td class="text-center font-bold">{{ legs.reduce((sum, leg) => sum + (leg.lots || 1), 0) }}</td>
              <td></td>
              <td class="text-center">-</td>
              <td class="text-right font-bold">-</td>
              <td colspan="7"></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Action Bar -->
    <div class="action-bar" data-testid="autopilot-legs-action-bar">
      <div class="action-left">
        <button
          @click="deleteSelectedLegs"
          :disabled="store.selectedLegIndices.length === 0"
          class="strategy-btn strategy-btn-outline"
          data-testid="autopilot-legs-delete-selected-button"
        >
          Delete Selected
        </button>
        <button
          @click="addLeg"
          class="strategy-btn strategy-btn-outline"
          style="color: var(--kite-blue);"
          data-testid="autopilot-legs-add-row-button"
        >
          + Add Row
        </button>
      </div>
      <div class="action-right">
        <span class="text-sm text-gray-500">
          {{ legs.length }} leg(s) | Total Qty: {{ store.totalQty }}
        </span>
      </div>
    </div>

    <!-- StrikeLadder Modal -->
    <div v-if="showStrikeLadder" class="modal-overlay" data-testid="autopilot-strike-ladder-modal" @click.self="showStrikeLadder = false">
      <div class="modal-content-large">
        <div class="modal-header">
          <h3 class="modal-title">Strike Ladder - {{ store.builder.strategy.underlying }}</h3>
          <button
            @click="showStrikeLadder = false"
            class="modal-close"
            data-testid="autopilot-strike-ladder-close"
          >
            &times;
          </button>
        </div>
        <StrikeLadder
          v-if="currentLegIndex !== null && legs[currentLegIndex]"
          :underlying="store.builder.strategy.underlying"
          :expiry="legs[currentLegIndex].expiry_date"
          :spot-price="currentSpotPrice"
          :loading-spot-price="loadingSpotPrice"
          :loading-option-chain="loadingOptionChain"
          @strike-selected="onStrikeSelected"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.text-lg {
  font-size: 1.125rem;
}

.font-semibold {
  font-weight: 600;
}

.font-bold {
  font-weight: 700;
}

.font-medium {
  font-weight: 500;
}

.text-sm {
  font-size: 0.875rem;
}

.text-gray-500 {
  color: var(--kite-text-secondary);
}

.text-gray-900 {
  color: var(--kite-text-primary);
}

.text-right {
  text-align: right;
}

.text-center {
  text-align: center;
}

.mb-4 {
  margin-bottom: 1rem;
}

.mx-2 {
  margin-left: 0.5rem;
  margin-right: 0.5rem;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

/* Expected Move Display */
.expected-move-display {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.expected-move-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-blue-dark, #1565c0);
}

.expected-move-range {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
}

.em-lower,
.em-upper {
  background: white;
  padding: 4px 12px;
  border-radius: 4px;
  color: var(--kite-text-primary);
}

.em-separator {
  color: var(--kite-text-secondary);
}

.expected-move-hint {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-left: auto;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content-large {
  background: white;
  border-radius: 8px;
  width: 100%;
  max-width: 1200px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--kite-border, #e0e0e0);
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  color: var(--kite-text-secondary);
  padding: 4px 8px;
  transition: color 0.2s ease;
}

.modal-close:hover {
  color: var(--kite-text-primary);
}
</style>
