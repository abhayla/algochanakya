<template>
  <div class="h-screen flex flex-col bg-gray-100 overflow-hidden">
    <!-- Header -->
    <StrategyHeader
      :underlying="strategyStore.underlying"
      :pnl-mode="strategyStore.pnlMode"
      :is-loading="strategyStore.isLoading"
      @update:underlying="strategyStore.setUnderlying"
      @toggle-mode="strategyStore.togglePnLMode"
    />

    <!-- Strategy Selector Bar -->
    <div class="bg-white border-b border-gray-200 px-4 py-2 flex-shrink-0">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <!-- Strategy Dropdown -->
          <div class="flex items-center space-x-2">
            <label class="text-sm text-gray-600">Strategy:</label>
            <select
              v-model="selectedStrategyId"
              @change="handleStrategyChange"
              class="px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">New Strategy</option>
              <option v-for="s in savedStrategies" :key="s.id" :value="s.id">
                {{ s.name }} ({{ s.underlying }})
              </option>
            </select>
          </div>

          <!-- Strategy Name Input -->
          <div class="flex items-center space-x-2">
            <label class="text-sm text-gray-600">Name:</label>
            <input
              v-model="strategyName"
              type="text"
              placeholder="Enter strategy name"
              class="px-3 py-1.5 text-sm border border-gray-300 rounded w-48 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <!-- Filter Dropdowns -->
        <div class="flex items-center space-x-3">
          <div class="flex items-center space-x-1">
            <label class="text-xs text-gray-500">Expiry:</label>
            <select v-model="filters.expiry" class="px-2 py-1 text-xs border border-gray-300 rounded">
              <option value="">All</option>
              <option v-for="exp in strategyStore.expiries" :key="exp" :value="exp">
                {{ formatDate(exp) }}
              </option>
            </select>
          </div>
          <div class="flex items-center space-x-1">
            <label class="text-xs text-gray-500">Contract:</label>
            <select v-model="filters.contractType" class="px-2 py-1 text-xs border border-gray-300 rounded">
              <option value="">All</option>
              <option value="CE">CE</option>
              <option value="PE">PE</option>
            </select>
          </div>
          <div class="flex items-center space-x-1">
            <label class="text-xs text-gray-500">Status:</label>
            <select v-model="filters.status" class="px-2 py-1 text-xs border border-gray-300 rounded">
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Error Alert -->
      <div v-if="strategyStore.error" class="mx-4 mt-2 p-3 bg-red-100 border border-red-400 text-red-700 rounded flex-shrink-0">
        {{ strategyStore.error }}
        <button @click="strategyStore.error = null" class="ml-4 text-red-500 hover:text-red-700">&times;</button>
      </div>

      <!-- Strategy Table Container with Horizontal Scroll -->
      <div class="flex-1 overflow-auto mx-4 mt-2 bg-white rounded-lg shadow">
        <table class="min-w-max border-collapse text-sm w-full">
          <thead class="bg-gray-50 sticky top-0 z-10">
            <tr>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-10 bg-gray-50">
                <input
                  type="checkbox"
                  :checked="allLegsSelected"
                  @change="toggleSelectAll"
                  class="h-4 w-4 text-blue-600 rounded"
                />
              </th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 100px;">Expiry</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 80px;">Contract</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 70px;">Trans</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 100px;">Strike</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 60px;">Lots</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 110px;">Strategy</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 80px;">Entry</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 80px;">Exit</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 60px;">Qty</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 70px;">CMP</th>
              <th class="border-b border-gray-200 px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50" style="min-width: 80px;">P/L</th>
              <!-- Dynamic P/L Columns -->
              <th
                v-for="spot in displayedSpotPrices"
                :key="spot"
                :class="[
                  'border-b border-gray-200 px-2 py-3 text-center text-xs font-medium uppercase tracking-wider bg-gray-50',
                  isCurrentSpot(spot) ? 'bg-blue-100 text-blue-800' : 'text-gray-500'
                ]"
                style="min-width: 70px;"
              >
                {{ spot }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <!-- Leg Rows -->
            <StrategyLegRow
              v-for="(leg, index) in filteredLegs"
              :key="leg.temp_id || leg.id"
              :leg="leg"
              :index="index"
              :expiries="strategyStore.expiries"
              :strikes="getStrikesForExpiry(leg.expiry_date)"
              :strategy-types="strategyStore.strategyTypes"
              :lot-size="strategyStore.lotSize"
              :is-selected="strategyStore.selectedLegIndices.includes(index)"
              :spot-prices="displayedSpotPrices"
              :pnl-values="getLegPnLValues(index)"
              :current-spot="strategyStore.currentSpot"
              :cmp="strategyStore.getLegCMP(leg)"
              :leg-pnl="strategyStore.getLegPnL(leg)"
              @update="(updates) => strategyStore.updateLeg(index, updates)"
              @toggle-select="strategyStore.toggleLegSelection(index)"
              @fetch-strikes="strategyStore.fetchStrikes"
            />

            <!-- Empty State -->
            <tr v-if="strategyStore.legs.length === 0">
              <td colspan="100" class="px-6 py-8 text-center text-gray-500">
                No legs added. Click "+ Add Row" to add a new leg.
              </td>
            </tr>

            <!-- Summary Row -->
            <tr v-if="strategyStore.legs.length > 0" class="bg-gray-100 font-semibold">
              <td colspan="9" class="px-3 py-2 text-right text-sm">Total:</td>
              <td class="px-3 py-2 text-sm">{{ strategyStore.totalQty }}</td>
              <td class="px-3 py-2 text-sm">-</td>
              <td class="px-3 py-2 text-sm" :class="totalPnLClass">{{ formatPnL(totalCurrentPnL) }}</td>
              <!-- Summary P/L Columns -->
              <td
                v-for="(spot, idx) in displayedSpotPrices"
                :key="'sum-' + spot"
                :class="[
                  'px-2 py-2 text-center text-sm',
                  getPnLCellClass(getTotalPnLAtSpot(idx)),
                  isCurrentSpot(spot) ? 'ring-2 ring-blue-400' : ''
                ]"
              >
                {{ formatPnL(getTotalPnLAtSpot(idx)) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Actions Bar -->
      <div class="bg-white border-t border-gray-200 px-4 py-2 flex-shrink-0 mx-4 mb-2 rounded-b-lg shadow">
        <div class="flex items-center justify-between">
          <!-- Left Buttons -->
          <div class="flex items-center space-x-2">
            <button
              @click="strategyStore.removeSelectedLegs()"
              :disabled="strategyStore.selectedLegIndices.length === 0"
              class="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Delete
            </button>
            <button
              @click="strategyStore.addLeg()"
              class="px-3 py-1.5 text-sm font-medium border border-blue-600 rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              + Add Row
            </button>
            <button
              @click="handleRecalculate"
              :disabled="strategyStore.legs.length === 0 || strategyStore.isLoading"
              class="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {{ strategyStore.isLoading ? 'Calculating...' : 'ReCalculate' }}
            </button>
          </div>

          <!-- Right Buttons -->
          <div class="flex items-center space-x-2">
            <button
              @click="strategyStore.importPositions()"
              class="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50"
            >
              Import Positions
            </button>
            <button
              @click="strategyStore.updateFromPositions()"
              class="px-3 py-1.5 text-sm font-medium border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50"
            >
              Update Positions
            </button>
            <button
              @click="handleSaveStrategy"
              :disabled="strategyStore.legs.length === 0 || !strategyName || isSaving"
              class="px-3 py-1.5 text-sm font-medium border border-green-600 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
            >
              {{ isSaving ? 'Saving...' : 'Save' }}
            </button>
            <button
              @click="handleShare"
              :disabled="!strategyStore.currentStrategy"
              class="px-3 py-1.5 text-sm font-medium border border-purple-600 rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
            >
              Share
            </button>
            <button
              @click="showOrderModal = true"
              :disabled="strategyStore.legs.length === 0 || !allLegsComplete"
              class="px-3 py-1.5 text-sm font-medium border border-orange-600 rounded bg-orange-600 text-white hover:bg-orange-700 disabled:opacity-50"
            >
              Buy Basket Order
            </button>
          </div>
        </div>
      </div>

      <!-- Summary Stats -->
      <div v-if="strategyStore.pnlGrid" class="mx-4 mb-2 grid grid-cols-2 md:grid-cols-5 gap-3 flex-shrink-0">
        <div class="bg-white rounded-lg shadow p-3">
          <div class="text-xs text-gray-500">Max Profit</div>
          <div class="text-lg font-bold text-green-600">{{ formatPnL(strategyStore.maxProfit) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-3">
          <div class="text-xs text-gray-500">Max Loss</div>
          <div class="text-lg font-bold text-red-600">{{ formatPnL(strategyStore.maxLoss) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-3">
          <div class="text-xs text-gray-500">Breakeven</div>
          <div class="text-lg font-bold">
            {{ strategyStore.breakevens.length > 0 ? strategyStore.breakevens.join(', ') : '-' }}
          </div>
        </div>
        <div class="bg-white rounded-lg shadow p-3">
          <div class="text-xs text-gray-500">Risk/Reward</div>
          <div class="text-lg font-bold">{{ riskRewardRatio }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-3">
          <div class="text-xs text-gray-500">Current Spot</div>
          <div class="text-lg font-bold">{{ formatPrice(strategyStore.currentSpot) }}</div>
        </div>
      </div>

      <!-- Footer -->
      <StrategyFooter
        :last-updated="strategyStore.lastUpdated"
        :current-spot="strategyStore.currentSpot"
        :underlying="strategyStore.underlying"
        class="flex-shrink-0"
      />
    </div>

    <!-- Save Success Toast -->
    <div
      v-if="showSaveSuccess"
      class="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2 z-50"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
      </svg>
      <span>Strategy saved successfully!</span>
    </div>

    <!-- Modals -->
    <ShareStrategyModal
      v-if="showShareModal"
      :share-url="shareUrl"
      @close="showShareModal = false"
    />

    <BasketOrderModal
      v-if="showOrderModal"
      :legs="strategyStore.legs"
      :lot-size="strategyStore.lotSize"
      :is-loading="strategyStore.isLoading"
      @confirm="handlePlaceOrder"
      @close="showOrderModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useStrategyStore } from '../stores/strategy'
import { useWatchlistStore } from '../stores/watchlist'
import StrategyHeader from '../components/strategy/StrategyHeader.vue'
import StrategyLegRow from '../components/strategy/StrategyLegRow.vue'
import StrategyFooter from '../components/strategy/StrategyFooter.vue'
import ShareStrategyModal from '../components/strategy/ShareStrategyModal.vue'
import BasketOrderModal from '../components/strategy/BasketOrderModal.vue'

const route = useRoute()
const strategyStore = useStrategyStore()
const watchlistStore = useWatchlistStore()

// Strategy management
const savedStrategies = ref([])
const selectedStrategyId = ref('')
const strategyName = ref('')
const isSaving = ref(false)
const showSaveSuccess = ref(false)

// Filters
const filters = ref({
  expiry: '',
  contractType: '',
  status: '',
})

// Modals
const showShareModal = ref(false)
const showOrderModal = ref(false)
const shareUrl = ref('')

// Computed
const filteredLegs = computed(() => {
  let result = strategyStore.legs
  if (filters.value.expiry) {
    result = result.filter(leg => leg.expiry_date === filters.value.expiry)
  }
  if (filters.value.contractType) {
    result = result.filter(leg => leg.contract_type === filters.value.contractType)
  }
  return result
})

const allLegsSelected = computed(() => {
  return strategyStore.legs.length > 0 &&
    strategyStore.selectedLegIndices.length === strategyStore.legs.length
})

const allLegsComplete = computed(() => {
  return strategyStore.legs.every(leg =>
    leg.expiry_date && leg.strike_price && leg.entry_price
  )
})

const displayedSpotPrices = computed(() => {
  if (!strategyStore.pnlGrid) return []

  const spots = strategyStore.pnlGrid.spot_prices
  const breakevens = strategyStore.pnlGrid.breakeven || []
  const currentSpot = strategyStore.pnlGrid.current_spot

  // Get strike prices from legs
  const strikes = strategyStore.legs
    .map(leg => parseFloat(leg.strike_price))
    .filter(s => !isNaN(s))

  // Start with all spots if count is reasonable, otherwise sample
  let result = []

  if (spots.length <= 25) {
    result = [...spots]
  } else {
    // Sample at regular intervals
    const step = Math.ceil(spots.length / 15)
    result = spots.filter((spot, i) => i % step === 0)
  }

  // ALWAYS add breakeven values as columns (they are important for the strategy)
  breakevens.forEach(be => {
    const rounded = Math.round(be)
    if (!result.includes(rounded)) {
      result.push(rounded)
    }
  })

  // Add strike prices as columns
  strikes.forEach(s => {
    if (!result.includes(s)) {
      result.push(s)
    }
  })

  // Add current spot
  if (currentSpot) {
    const rounded = Math.round(currentSpot)
    if (!result.includes(rounded)) {
      result.push(rounded)
    }
  }

  // Return unique sorted spots
  return [...new Set(result)].sort((a, b) => a - b)
})

const totalCurrentPnL = computed(() => {
  return strategyStore.legs.reduce((sum, leg) => {
    const pnl = strategyStore.getLegPnL(leg)
    return sum + (pnl || 0)
  }, 0)
})

const totalPnLClass = computed(() => {
  if (totalCurrentPnL.value > 0) return 'text-green-600'
  if (totalCurrentPnL.value < 0) return 'text-red-600'
  return 'text-gray-600'
})

const riskRewardRatio = computed(() => {
  if (!strategyStore.maxLoss || strategyStore.maxLoss === 0) return '-'
  const ratio = Math.abs(strategyStore.maxProfit / strategyStore.maxLoss)
  return `1:${ratio.toFixed(2)}`
})

// Methods
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })
}

function formatPnL(value) {
  if (value === null || value === undefined) return '-'
  const formatted = Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })
  return value < 0 ? `-${formatted}` : formatted
}

function formatPrice(value) {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function getStrikesForExpiry(expiry) {
  return strategyStore.strikes[expiry] || []
}

function getLegPnLValues(legIndex) {
  if (!strategyStore.pnlGrid || !strategyStore.pnlGrid.leg_pnl[legIndex]) {
    return []
  }

  const spots = strategyStore.pnlGrid.spot_prices
  const legPnL = strategyStore.pnlGrid.leg_pnl[legIndex]

  // Map displayedSpotPrices to corresponding P/L values with interpolation
  return displayedSpotPrices.value.map(spot => {
    // First try exact match
    const exactIndex = spots.indexOf(spot)
    if (exactIndex !== -1) {
      return legPnL[exactIndex]
    }

    // If not found (breakeven/strike column), interpolate between neighbors
    let lowerIdx = -1
    let upperIdx = -1

    for (let i = 0; i < spots.length; i++) {
      if (spots[i] < spot) lowerIdx = i
      if (spots[i] > spot && upperIdx === -1) upperIdx = i
    }

    // If we have both neighbors, interpolate
    if (lowerIdx !== -1 && upperIdx !== -1) {
      const lowerSpot = spots[lowerIdx]
      const upperSpot = spots[upperIdx]
      const lowerPnL = legPnL[lowerIdx]
      const upperPnL = legPnL[upperIdx]

      // Linear interpolation
      const ratio = (spot - lowerSpot) / (upperSpot - lowerSpot)
      return Math.round(lowerPnL + ratio * (upperPnL - lowerPnL))
    }

    // Edge cases: use nearest value
    if (lowerIdx !== -1) return legPnL[lowerIdx]
    if (upperIdx !== -1) return legPnL[upperIdx]

    return null
  })
}

function getTotalPnLAtSpot(spotIndex) {
  if (!strategyStore.pnlGrid) return null

  const spot = displayedSpotPrices.value[spotIndex]
  const spots = strategyStore.pnlGrid.spot_prices
  const pnlValues = strategyStore.pnlGrid.total_pnl

  // First try exact match
  const fullIndex = spots.indexOf(spot)
  if (fullIndex !== -1) {
    return pnlValues[fullIndex]
  }

  // If not found (breakeven/strike column), interpolate between neighbors
  // Find the two surrounding spots
  let lowerIdx = -1
  let upperIdx = -1

  for (let i = 0; i < spots.length; i++) {
    if (spots[i] < spot) lowerIdx = i
    if (spots[i] > spot && upperIdx === -1) upperIdx = i
  }

  // If we have both neighbors, interpolate
  if (lowerIdx !== -1 && upperIdx !== -1) {
    const lowerSpot = spots[lowerIdx]
    const upperSpot = spots[upperIdx]
    const lowerPnL = pnlValues[lowerIdx]
    const upperPnL = pnlValues[upperIdx]

    // Linear interpolation
    const ratio = (spot - lowerSpot) / (upperSpot - lowerSpot)
    return Math.round(lowerPnL + ratio * (upperPnL - lowerPnL))
  }

  // Edge cases: use nearest value
  if (lowerIdx !== -1) return pnlValues[lowerIdx]
  if (upperIdx !== -1) return pnlValues[upperIdx]

  return null
}

function isCurrentSpot(spot) {
  if (!strategyStore.currentSpot) return false
  return Math.abs(spot - strategyStore.currentSpot) < 50
}

function getPnLCellClass(pnl) {
  if (pnl === null || pnl === undefined) return 'bg-gray-50'
  if (pnl < 0) return 'bg-red-100 text-red-800'
  if (pnl > 0) return 'bg-green-50 text-green-800'
  return 'bg-gray-50'
}

function toggleSelectAll() {
  if (allLegsSelected.value) {
    strategyStore.deselectAllLegs()
  } else {
    strategyStore.selectAllLegs()
  }
}

async function loadSavedStrategies() {
  try {
    const result = await strategyStore.fetchStrategies()
    if (result.success) {
      savedStrategies.value = strategyStore.strategies
    }
  } catch (error) {
    console.error('Error loading saved strategies:', error)
  }
}

async function handleStrategyChange() {
  if (!selectedStrategyId.value) {
    // New strategy - clear everything
    strategyStore.clearStrategy()
    strategyName.value = ''
    return
  }

  const result = await strategyStore.loadStrategy(selectedStrategyId.value)
  if (result.success) {
    strategyName.value = strategyStore.currentStrategy?.name || ''
  }
}

async function handleRecalculate() {
  await strategyStore.calculatePnL()
}

async function handleSaveStrategy() {
  if (!strategyName.value || strategyStore.legs.length === 0) return

  isSaving.value = true

  try {
    let result
    if (selectedStrategyId.value && strategyStore.currentStrategy) {
      // Update existing strategy
      result = await strategyStore.updateStrategy(selectedStrategyId.value, {
        name: strategyName.value,
        underlying: strategyStore.underlying,
        legs: strategyStore.legs.map(leg => ({
          expiry_date: leg.expiry_date,
          contract_type: leg.contract_type,
          transaction_type: leg.transaction_type,
          strike_price: leg.strike_price ? parseFloat(leg.strike_price) : null,
          lots: leg.lots,
          strategy_type: leg.strategy_type,
          entry_price: leg.entry_price ? parseFloat(leg.entry_price) : null,
          exit_price: leg.exit_price ? parseFloat(leg.exit_price) : null,
          instrument_token: leg.instrument_token,
        })),
      })
    } else {
      // Create new strategy
      result = await strategyStore.saveStrategy(strategyName.value)
    }

    if (result.success) {
      showSaveSuccess.value = true
      setTimeout(() => { showSaveSuccess.value = false }, 3000)

      // Update the selected strategy ID
      if (result.data?.id) {
        selectedStrategyId.value = result.data.id
      }

      // Reload saved strategies list
      await loadSavedStrategies()
    }
  } catch (error) {
    console.error('Error saving strategy:', error)
  } finally {
    isSaving.value = false
  }
}

async function handleShare() {
  const result = await strategyStore.shareStrategy()
  if (result.success) {
    shareUrl.value = window.location.origin + result.shareUrl
    showShareModal.value = true
  }
}

async function handlePlaceOrder() {
  const result = await strategyStore.placeBasketOrder()
  if (result.success) {
    showOrderModal.value = false
    alert(`Orders placed: ${result.data.successful_orders}/${result.data.total_orders} successful`)
  } else {
    alert(`Order failed: ${result.error}`)
  }
}

// Lifecycle
onMounted(async () => {
  // Check for shared strategy
  if (route.params.shareCode) {
    await strategyStore.loadSharedStrategy(route.params.shareCode)
    strategyName.value = strategyStore.currentStrategy?.name || ''
  } else if (route.params.id) {
    await strategyStore.loadStrategy(route.params.id)
    strategyName.value = strategyStore.currentStrategy?.name || ''
    selectedStrategyId.value = route.params.id
  } else {
    await strategyStore.fetchExpiries()
  }

  // Load saved strategies for dropdown
  await loadSavedStrategies()

  // Connect to WebSocket for live prices if watchlist store is available
  if (watchlistStore.isConnected) {
    const indexTokens = {
      'NIFTY': 256265,
      'BANKNIFTY': 260105,
      'FINNIFTY': 257801,
    }
    const token = indexTokens[strategyStore.underlying]
    if (token) {
      watchlistStore.subscribeToTokens([token], 'quote')
    }
  }
})

onUnmounted(() => {
  strategyStore.clearStrategy()
})

// Watch for underlying changes to update subscriptions
watch(() => strategyStore.underlying, (newUnderlying) => {
  if (watchlistStore.isConnected) {
    const indexTokens = {
      'NIFTY': 256265,
      'BANKNIFTY': 260105,
      'FINNIFTY': 257801,
    }
    const token = indexTokens[newUnderlying]
    if (token) {
      watchlistStore.subscribeToTokens([token], 'quote')
    }
  }
})

// Watch for tick updates from watchlist store
watch(() => watchlistStore.ticks, (newTicks) => {
  const ticksArray = Object.entries(newTicks).map(([token, data]) => ({
    token: parseInt(token),
    ltp: data.ltp,
    change: data.change,
    change_percent: data.change_percent,
  }))
  if (ticksArray.length > 0) {
    strategyStore.updateLivePrices(ticksArray)
  }
}, { deep: true })

// Watch for leg token changes to subscribe to option prices
watch(
  () => strategyStore.getLegTokens(),
  (tokens) => {
    if (tokens.length > 0 && watchlistStore.isConnected) {
      // Subscribe to leg option tokens for live CMP
      watchlistStore.subscribeToTokens(tokens, 'quote')
    }
  },
  { deep: true }
)

// Watch for leg instrument_token changes to fetch LTP as fallback
watch(
  () => strategyStore.legs.map(l => l.instrument_token),
  (newTokens, oldTokens) => {
    // Fetch LTP for any legs with instrument_token (fallback when WebSocket unavailable)
    strategyStore.legs.forEach(leg => {
      if (leg.instrument_token) {
        strategyStore.fetchLegLTP(leg)
      }
    })
  },
  { deep: true }
)
</script>

<style scoped>
/* Ensure the main container doesn't cause browser horizontal scroll */
.overflow-hidden {
  overflow: hidden;
}

/* Only the table container should scroll horizontally */
.overflow-auto {
  overflow: auto;
}
</style>
