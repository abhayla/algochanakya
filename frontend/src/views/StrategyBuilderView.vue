<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Header -->
    <StrategyHeader
      :underlying="strategyStore.underlying"
      :pnl-mode="strategyStore.pnlMode"
      :is-loading="strategyStore.isLoading"
      @update:underlying="strategyStore.setUnderlying"
      @toggle-mode="strategyStore.togglePnLMode"
    />

    <!-- Main Content -->
    <div class="container mx-auto px-4 py-4">
      <!-- Error Alert -->
      <div v-if="strategyStore.error" class="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
        {{ strategyStore.error }}
        <button @click="strategyStore.error = null" class="ml-4 text-red-500 hover:text-red-700">&times;</button>
      </div>

      <!-- Strategy Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <!-- Table Header with Filters -->
        <div class="p-4 border-b bg-gray-50">
          <div class="flex flex-wrap items-center gap-4">
            <div class="flex items-center gap-2">
              <label class="text-sm font-medium text-gray-700">Expiry:</label>
              <select v-model="filters.expiry" class="text-sm border rounded px-2 py-1">
                <option value="">All</option>
                <option v-for="exp in strategyStore.expiries" :key="exp" :value="exp">
                  {{ formatDate(exp) }}
                </option>
              </select>
            </div>
            <div class="flex items-center gap-2">
              <label class="text-sm font-medium text-gray-700">Contract:</label>
              <select v-model="filters.contractType" class="text-sm border rounded px-2 py-1">
                <option value="">All</option>
                <option value="CE">CE</option>
                <option value="PE">PE</option>
              </select>
            </div>
            <div class="flex items-center gap-2">
              <label class="text-sm font-medium text-gray-700">Status:</label>
              <select v-model="filters.status" class="text-sm border rounded px-2 py-1">
                <option value="">All</option>
                <option value="open">Open</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Scrollable Table Container -->
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-2 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-10">
                  <input
                    type="checkbox"
                    :checked="allLegsSelected"
                    @change="toggleSelectAll"
                    class="h-4 w-4 text-blue-600 rounded"
                  />
                </th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expiry</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Contract</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trans</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strike</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Lots</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Entry</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Exit</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Qty</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CMP</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">P/L</th>
                <!-- Dynamic P/L Columns -->
                <th
                  v-for="spot in displayedSpotPrices"
                  :key="spot"
                  :class="[
                    'px-2 py-3 text-center text-xs font-medium uppercase tracking-wider min-w-[60px]',
                    isCurrentSpot(spot) ? 'bg-blue-100 text-blue-800' : 'text-gray-500'
                  ]"
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
                  No legs added. Click "Add Row" to add a new leg.
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
        <StrategyActions
          :has-selection="strategyStore.selectedLegIndices.length > 0"
          :has-legs="strategyStore.legs.length > 0"
          :is-loading="strategyStore.isLoading"
          :has-strategy="!!strategyStore.currentStrategy"
          @add-leg="strategyStore.addLeg()"
          @delete-selected="strategyStore.removeSelectedLegs()"
          @recalculate="strategyStore.calculatePnL()"
          @save="showSaveModal = true"
          @update-positions="strategyStore.updateFromPositions()"
          @buy-basket="showOrderModal = true"
          @import-positions="strategyStore.importPositions()"
          @share="handleShare"
        />
      </div>

      <!-- Summary Stats -->
      <div v-if="strategyStore.pnlGrid" class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Max Profit</div>
          <div class="text-xl font-bold text-green-600">{{ formatPnL(strategyStore.maxProfit) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Max Loss</div>
          <div class="text-xl font-bold text-red-600">{{ formatPnL(strategyStore.maxLoss) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Breakeven</div>
          <div class="text-xl font-bold">
            {{ strategyStore.breakevens.length > 0 ? strategyStore.breakevens.join(', ') : '-' }}
          </div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-sm text-gray-500">Risk/Reward</div>
          <div class="text-xl font-bold">
            {{ riskRewardRatio }}
          </div>
        </div>
      </div>

      <!-- Footer -->
      <StrategyFooter
        :last-updated="strategyStore.lastUpdated"
        :current-spot="strategyStore.currentSpot"
        :underlying="strategyStore.underlying"
      />
    </div>

    <!-- Modals -->
    <SaveStrategyModal
      v-if="showSaveModal"
      :strategy-name="strategyStore.currentStrategy?.name"
      @save="handleSave"
      @close="showSaveModal = false"
    />

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
import StrategyActions from '../components/strategy/StrategyActions.vue'
import StrategyFooter from '../components/strategy/StrategyFooter.vue'
import SaveStrategyModal from '../components/strategy/SaveStrategyModal.vue'
import ShareStrategyModal from '../components/strategy/ShareStrategyModal.vue'
import BasketOrderModal from '../components/strategy/BasketOrderModal.vue'

const route = useRoute()
const strategyStore = useStrategyStore()
const watchlistStore = useWatchlistStore()

// Filters
const filters = ref({
  expiry: '',
  contractType: '',
  status: '',
})

// Modals
const showSaveModal = ref(false)
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

const displayedSpotPrices = computed(() => {
  if (!strategyStore.pnlGrid) return []
  // Limit to reasonable number of columns
  const spots = strategyStore.pnlGrid.spot_prices
  if (spots.length <= 15) return spots
  // Sample every nth element to get ~15 columns
  const step = Math.ceil(spots.length / 15)
  return spots.filter((_, i) => i % step === 0)
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

function getStrikesForExpiry(expiry) {
  return strategyStore.strikes[expiry] || []
}

function getLegPnLValues(legIndex) {
  if (!strategyStore.pnlGrid || !strategyStore.pnlGrid.leg_pnl[legIndex]) {
    return []
  }
  return strategyStore.pnlGrid.leg_pnl[legIndex]
}

function getTotalPnLAtSpot(spotIndex) {
  if (!strategyStore.pnlGrid) return null
  // Find the index in the full spot prices array
  const spot = displayedSpotPrices.value[spotIndex]
  const fullIndex = strategyStore.pnlGrid.spot_prices.indexOf(spot)
  if (fullIndex === -1) return null
  return strategyStore.pnlGrid.total_pnl[fullIndex]
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

async function handleSave(name) {
  const result = await strategyStore.saveStrategy(name)
  if (result.success) {
    showSaveModal.value = false
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

// WebSocket for live prices
function handleTicks(ticks) {
  strategyStore.updateLivePrices(ticks)
}

// Lifecycle
onMounted(async () => {
  // Check for shared strategy
  if (route.params.shareCode) {
    await strategyStore.loadSharedStrategy(route.params.shareCode)
  } else if (route.params.id) {
    await strategyStore.loadStrategy(route.params.id)
  } else {
    await strategyStore.fetchExpiries()
  }

  // Connect to WebSocket for live prices if watchlist store is available
  if (watchlistStore.isConnected) {
    // Subscribe to index tokens
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
  // Convert watchlist ticks format to strategy store format
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
</script>
