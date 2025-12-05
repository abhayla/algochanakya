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

    <!-- Main Scrollable Content -->
    <div class="flex-1 overflow-y-auto p-4">
      <!-- Error Alert -->
      <div v-if="strategyStore.error" class="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
        {{ strategyStore.error }}
        <button @click="strategyStore.error = null" class="ml-4 text-red-500 hover:text-red-700">&times;</button>
      </div>

      <!-- FULL WIDTH STRATEGY TABLE -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-4 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-3 py-3 text-center w-10 border-r border-gray-200">
                  <input
                    type="checkbox"
                    :checked="allLegsSelected"
                    @change="toggleSelectAll"
                    class="h-4 w-4 text-blue-600 rounded"
                  />
                </th>
                <th class="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 100px;">Expiry</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 70px;">Type</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 60px;">B/S</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 100px;">Strike</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 60px;">Lots</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 80px;">Entry</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 60px;">Qty</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 70px;">CMP</th>
                <th class="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase border-r border-gray-200" style="min-width: 80px;">Exit P/L</th>
                <!-- Dynamic P/L Columns -->
                <th
                  v-for="spot in displayedSpotPrices"
                  :key="spot"
                  :class="[
                    'px-2 py-3 text-center text-xs font-semibold uppercase whitespace-nowrap border-r border-gray-200',
                    isCurrentSpot(spot) ? 'bg-yellow-200 text-yellow-900' : 'text-gray-600'
                  ]"
                  style="min-width: 70px;"
                >
                  <div v-if="isCurrentSpot(spot)" class="text-[10px] text-yellow-700 font-bold">SPOT</div>
                  {{ spot }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <!-- Strategy Leg Rows -->
              <tr
                v-for="(leg, index) in filteredLegs"
                :key="leg.temp_id || leg.id"
                :class="[
                  'transition-colors border-l-4',
                  leg.transaction_type === 'BUY'
                    ? 'bg-blue-50 hover:bg-blue-100 border-l-blue-500'
                    : 'bg-amber-50 hover:bg-amber-100 border-l-amber-500'
                ]"
              >
                <td class="px-3 py-2 text-center border-r border-gray-200">
                  <input
                    type="checkbox"
                    :checked="strategyStore.selectedLegIndices.includes(index)"
                    @change="strategyStore.toggleLegSelection(index)"
                    class="h-4 w-4 text-blue-600 rounded"
                  />
                </td>
                <td class="px-2 py-2 border-r border-gray-200">
                  <select
                    :value="leg.expiry_date"
                    @change="handleLegUpdate(index, 'expiry_date', $event.target.value)"
                    class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
                  >
                    <option value="">Select</option>
                    <option v-for="exp in strategyStore.expiries" :key="exp" :value="exp">
                      {{ formatDate(exp) }}
                    </option>
                  </select>
                </td>
                <td class="px-2 py-2 text-center border-r border-gray-200">
                  <select
                    :value="leg.contract_type"
                    @change="handleLegUpdate(index, 'contract_type', $event.target.value)"
                    :class="[
                      'w-full px-2 py-1.5 text-xs font-bold rounded border',
                      leg.contract_type === 'CE' ? 'bg-green-100 text-green-800 border-green-300' : 'bg-rose-100 text-rose-800 border-rose-300'
                    ]"
                  >
                    <option value="CE">CE</option>
                    <option value="PE">PE</option>
                  </select>
                </td>
                <td class="px-2 py-2 text-center border-r border-gray-200">
                  <select
                    :value="leg.transaction_type"
                    @change="handleLegUpdate(index, 'transaction_type', $event.target.value)"
                    :class="[
                      'w-full px-2 py-1.5 text-xs font-bold rounded border',
                      leg.transaction_type === 'BUY' ? 'bg-blue-100 text-blue-800 border-blue-300' : 'bg-amber-100 text-amber-800 border-amber-300'
                    ]"
                  >
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </td>
                <td class="px-2 py-2 border-r border-gray-200">
                  <select
                    :value="leg.strike_price"
                    @change="handleLegUpdate(index, 'strike_price', $event.target.value)"
                    class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
                  >
                    <option value="">Select</option>
                    <option v-for="s in getStrikesForExpiry(leg.expiry_date)" :key="s" :value="s">
                      {{ s }}
                    </option>
                  </select>
                </td>
                <td class="px-2 py-2 border-r border-gray-200">
                  <input
                    type="number"
                    :value="leg.lots"
                    @input="handleLegUpdate(index, 'lots', parseInt($event.target.value) || 1)"
                    min="1"
                    class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded text-center"
                  />
                </td>
                <td class="px-2 py-2 border-r border-gray-200">
                  <input
                    type="number"
                    :value="leg.entry_price"
                    @input="handleLegUpdate(index, 'entry_price', parseFloat($event.target.value))"
                    @blur="handleLegUpdate(index, 'entry_price', parseFloat($event.target.value))"
                    step="0.05"
                    placeholder="Entry"
                    class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded text-right"
                  />
                </td>
                <td class="px-3 py-2 text-center font-semibold border-r border-gray-200">
                  {{ leg.lots * strategyStore.lotSize }}
                </td>
                <td class="px-3 py-2 text-right font-medium border-r border-gray-200">
                  <span v-if="strategyStore.getLegCMP(leg)" class="text-blue-600">
                    {{ formatPrice(strategyStore.getLegCMP(leg)) }}
                  </span>
                  <span v-else class="text-gray-400">-</span>
                </td>
                <td class="px-3 py-2 text-right font-semibold border-r border-gray-200">
                  <span :class="getPnLClass(strategyStore.getLegPnL(leg))">
                    {{ formatPnL(strategyStore.getLegPnL(leg)) }}
                  </span>
                </td>
                <!-- Dynamic P/L Cells -->
                <PnLCell
                  v-for="(spot, spotIdx) in displayedSpotPrices"
                  :key="'cell-' + index + '-' + spot"
                  :value="getLegPnLValues(index)[spotIdx]"
                  :max-profit="strategyStore.maxProfit"
                  :max-loss="strategyStore.maxLoss"
                  :is-spot-column="isCurrentSpot(spot)"
                />
              </tr>

              <!-- Empty State -->
              <tr v-if="strategyStore.legs.length === 0">
                <td colspan="100" class="px-6 py-12 text-center text-gray-500">
                  No legs added. Click "+ Add Row" to start building your strategy.
                </td>
              </tr>

              <!-- Total Row -->
              <tr v-if="strategyStore.legs.length > 0" class="bg-gray-100 border-t-2 border-gray-300 font-semibold">
                <td colspan="7" class="px-4 py-3 text-right text-gray-700 border-r border-gray-200">Total:</td>
                <td class="px-3 py-3 text-center font-bold border-r border-gray-200">{{ strategyStore.totalQty }}</td>
                <td class="px-3 py-3 text-center text-gray-400 border-r border-gray-200">-</td>
                <td class="px-3 py-3 text-right font-bold border-r border-gray-200" :class="getPnLClass(totalCurrentPnL)">
                  {{ formatPnL(totalCurrentPnL) }}
                </td>
                <!-- Total P/L Cells -->
                <PnLCell
                  v-for="(spot, idx) in displayedSpotPrices"
                  :key="'total-' + spot"
                  :value="getTotalPnLAtSpot(idx)"
                  :max-profit="strategyStore.maxProfit"
                  :max-loss="strategyStore.maxLoss"
                  :is-spot-column="isCurrentSpot(spot)"
                  :is-total="true"
                />
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ACTION BUTTONS -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-4 px-4 py-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <button
              @click="strategyStore.removeSelectedLegs()"
              :disabled="strategyStore.selectedLegIndices.length === 0"
              class="px-3 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Delete
            </button>
            <button
              @click="strategyStore.addLeg()"
              class="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100"
            >
              + Add Row
            </button>
            <button
              @click="handleRecalculate"
              :disabled="strategyStore.legs.length === 0 || strategyStore.isLoading"
              class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ strategyStore.isLoading ? 'Calculating...' : 'ReCalculate' }}
            </button>
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="strategyStore.importPositions()"
              class="px-3 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Import Positions
            </button>
            <button
              @click="strategyStore.updateFromPositions()"
              class="px-3 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Update Positions
            </button>
            <button
              @click="handleSaveStrategy"
              :disabled="strategyStore.legs.length === 0 || !strategyName || isSaving"
              class="px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {{ isSaving ? 'Saving...' : 'Save' }}
            </button>
            <button
              @click="handleShare"
              :disabled="!strategyStore.currentStrategy"
              class="px-3 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Share
            </button>
            <button
              @click="showOrderModal = true"
              :disabled="strategyStore.legs.length === 0 || !allLegsComplete"
              class="px-4 py-2 text-sm font-semibold text-white bg-orange-500 rounded-lg hover:bg-orange-600 disabled:opacity-50"
            >
              Buy Basket Order
            </button>
          </div>
        </div>
      </div>

      <!-- PAYOFF CHART (FULL WIDTH, BELOW TABLE) -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-4 p-4" v-if="displayedSpotPrices.length > 0">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold text-gray-800">Payoff Diagram</h3>
          <div class="flex gap-4 text-sm">
            <span class="flex items-center text-green-600">
              <span class="w-4 h-1 bg-green-500 mr-2 rounded"></span> Profit Zone
            </span>
            <span class="flex items-center text-red-600">
              <span class="w-4 h-1 bg-red-500 mr-2 rounded"></span> Loss Zone
            </span>
            <span class="flex items-center text-yellow-600">
              <span class="w-3 h-3 bg-yellow-400 mr-2 rounded-full"></span> Current Spot
            </span>
          </div>
        </div>
        <div class="h-56">
          <PayoffChart
            :spot-prices="chartSpotPrices"
            :total-pnl="chartTotalPnl"
            :current-spot="strategyStore.currentSpot"
          />
        </div>
      </div>

      <!-- SUMMARY CARDS (FULL WIDTH, 5 COLUMNS) -->
      <div class="grid grid-cols-5 gap-4">
        <!-- Max Profit Card -->
        <div class="bg-white rounded-xl border border-green-200 p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
              </svg>
            </div>
            <span class="text-xs font-semibold text-gray-500 uppercase">Max Profit</span>
          </div>
          <div class="text-2xl font-bold text-green-600">{{ formatNumber(strategyStore.maxProfit) }}</div>
        </div>

        <!-- Max Loss Card -->
        <div class="bg-white rounded-xl border border-red-200 p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/>
              </svg>
            </div>
            <span class="text-xs font-semibold text-gray-500 uppercase">Max Loss</span>
          </div>
          <div class="text-2xl font-bold text-red-600">{{ formatNumber(strategyStore.maxLoss) }}</div>
        </div>

        <!-- Breakeven Card -->
        <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/>
              </svg>
            </div>
            <span class="text-xs font-semibold text-gray-500 uppercase">Breakeven</span>
          </div>
          <div class="text-lg font-bold text-gray-800">
            {{ strategyStore.breakevens.length >= 2 ? formatNumber(strategyStore.breakevens[0]) + ' - ' + formatNumber(strategyStore.breakevens[1]) : (strategyStore.breakevens.length === 1 ? formatNumber(strategyStore.breakevens[0]) : '-') }}
          </div>
        </div>

        <!-- Risk/Reward Card -->
        <div class="bg-white rounded-xl border border-blue-200 p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
            </div>
            <span class="text-xs font-semibold text-gray-500 uppercase">Risk/Reward</span>
          </div>
          <div class="text-2xl font-bold text-blue-600">{{ riskRewardRatio }}</div>
        </div>

        <!-- Current Spot Card -->
        <div class="bg-gradient-to-br from-yellow-50 to-amber-100 rounded-xl border-2 border-yellow-400 p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-10 h-10 rounded-lg bg-yellow-200 flex items-center justify-center">
              <div class="w-3 h-3 rounded-full bg-yellow-500 animate-pulse"></div>
            </div>
            <span class="text-xs font-semibold text-yellow-700 uppercase">{{ strategyStore.underlying }} Spot</span>
          </div>
          <div class="text-2xl font-bold text-yellow-700">{{ formatNumber(strategyStore.currentSpot) }}</div>
          <div class="text-xs text-yellow-600 mt-1">{{ strategyStore.lastUpdated }}</div>
        </div>
      </div>

    </div><!-- End Main Scrollable Content -->

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
import ShareStrategyModal from '../components/strategy/ShareStrategyModal.vue'
import BasketOrderModal from '../components/strategy/BasketOrderModal.vue'
import PayoffChart from '../components/strategy/PayoffChart.vue'
import PnLCell from '../components/strategy/PnLCell.vue'

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

// Chart data computed properties
const chartSpotPrices = computed(() => {
  if (!strategyStore.pnlGrid) return []
  return strategyStore.pnlGrid.spot_prices
})

const chartTotalPnl = computed(() => {
  if (!strategyStore.pnlGrid) return []
  return strategyStore.pnlGrid.total_pnl
})

const totalCurrentPnL = computed(() => {
  return strategyStore.legs.reduce((sum, leg) => {
    const pnl = strategyStore.getLegPnL(leg)
    return sum + (pnl || 0)
  }, 0)
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

function formatNumber(num) {
  if (!num && num !== 0) return '-'
  return new Intl.NumberFormat('en-IN').format(Math.round(num))
}

function getPnLClass(value) {
  if (value > 0) return 'text-green-600'
  if (value < 0) return 'text-red-600'
  return 'text-gray-600'
}

function getStrikesForExpiry(expiry) {
  return strategyStore.strikes[expiry] || []
}

function handleLegUpdate(index, field, value) {
  const updates = { [field]: value }
  strategyStore.updateLeg(index, updates)

  // Fetch strikes when expiry changes
  if (field === 'expiry_date' && value) {
    strategyStore.fetchStrikes(value)
  }
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
/* Smooth scrolling for P/L grid */
.overflow-x-auto {
  scroll-behavior: smooth;
}
</style>
