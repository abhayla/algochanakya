<template>
  <KiteLayout>
    <div class="strategy-page" data-testid="strategy-page">
      <div class="strategy-container">
        <!-- Underlying Selector + P/L Mode Toggle -->
        <div class="strategy-toolbar" data-testid="strategy-toolbar">
          <div class="toolbar-left">
            <div class="underlying-tabs" data-testid="strategy-underlying-tabs">
              <button
                v-for="u in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']"
                :key="u"
                :class="['underlying-tab', { active: strategyStore.underlying === u }]"
                @click="strategyStore.setUnderlying(u)"
                :data-testid="'strategy-underlying-' + u.toLowerCase()"
              >
                {{ u }}
              </button>
            </div>
          </div>
          <div class="toolbar-right">
            <span class="mode-label">P/L Mode:</span>
            <button
              :class="['mode-btn', { active: strategyStore.pnlMode === 'expiry' }]"
              @click="strategyStore.pnlMode !== 'expiry' && strategyStore.togglePnLMode()"
              data-testid="strategy-pnl-mode-expiry"
            >
              At Expiry
            </button>
            <button
              :class="['mode-btn', { active: strategyStore.pnlMode === 'current' }]"
              @click="strategyStore.pnlMode !== 'current' && strategyStore.togglePnLMode()"
              data-testid="strategy-pnl-mode-current"
            >
              Current
            </button>
            <span v-if="strategyStore.isLoading" class="loading-indicator" data-testid="strategy-loading">Loading...</span>
          </div>
        </div>

        <!-- Strategy Selector Bar -->
        <div class="strategy-selector-bar" data-testid="strategy-selector-bar">
          <div class="selector-row">
            <div class="selector-left">
              <!-- Strategy Dropdown -->
              <div class="form-group">
                <label class="form-label">Strategy:</label>
                <select
                  v-model="selectedStrategyId"
                  @change="handleStrategyChange"
                  class="strategy-select"
                  data-testid="strategy-select"
                >
                  <option value="">New Strategy</option>
                  <option v-for="s in savedStrategies" :key="s.id" :value="s.id">
                    {{ s.name }} ({{ s.underlying }})
                  </option>
                </select>
              </div>

              <!-- Strategy Name Input -->
              <div class="form-group">
                <label class="form-label">Name:</label>
                <input
                  v-model="strategyName"
                  type="text"
                  placeholder="Enter strategy name"
                  class="strategy-input"
                  style="width: 200px;"
                  data-testid="strategy-name-input"
                />
              </div>

              <!-- Strategy Type Dropdown -->
              <div class="form-group">
                <label class="form-label">Type:</label>
                <select
                  v-model="selectedStrategyType"
                  @change="onStrategyTypeChange"
                  class="strategy-select"
                  data-testid="strategy-type-select"
                >
                  <option value="">Custom (Manual)</option>
                  <optgroup
                    v-for="(cat, catKey) in categories"
                    :key="catKey"
                    :label="cat.name"
                  >
                    <option
                      v-for="strategy in strategiesByCategory[catKey]"
                      :key="strategy.key"
                      :value="strategy.key"
                    >
                      {{ strategy.display_name }}
                    </option>
                  </optgroup>
                </select>
              </div>

              <!-- Save and Delete Buttons -->
              <div class="form-group" style="display: flex; gap: 8px; align-items: center;">
                <button
                  @click="handleSaveStrategy"
                  :disabled="strategyStore.legs.length === 0 || !strategyName || isSaving"
                  class="strategy-btn strategy-btn-success"
                  data-testid="strategy-save-button"
                >
                  {{ isSaving ? 'Saving...' : 'Save' }}
                </button>
                <button
                  @click="handleDeleteStrategy"
                  :disabled="!selectedStrategyId"
                  class="strategy-btn strategy-btn-danger"
                  data-testid="strategy-delete-button"
                >
                  Delete
                </button>
              </div>
            </div>

            <!-- Filter Dropdowns -->
            <div class="selector-right">
              <div class="form-group compact">
                <label class="form-label-sm">Expiry:</label>
                <select v-model="filters.expiry" class="strategy-select compact">
                  <option value="">All</option>
                  <option v-for="exp in strategyStore.expiries" :key="exp" :value="exp">
                    {{ formatDate(exp) }}
                  </option>
                </select>
              </div>
              <div class="form-group compact">
                <label class="form-label-sm">Contract:</label>
                <select v-model="filters.contractType" class="strategy-select compact">
                  <option value="">All</option>
                  <option value="CE">CE</option>
                  <option value="PE">PE</option>
                </select>
              </div>
              <div class="form-group compact">
                <label class="form-label-sm">Status:</label>
                <select v-model="filters.status" class="strategy-select compact">
                  <option value="">All</option>
                  <option value="open">Open</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Error Alert -->
        <div v-if="strategyStore.error" class="error-alert" data-testid="strategy-error">
          {{ strategyStore.error }}
          <button @click="strategyStore.error = null" class="error-close">&times;</button>
        </div>

        <!-- Strategy Table -->
        <div class="strategy-table-wrapper" data-testid="strategy-table-wrapper">
          <!-- Scroll Indicators -->
          <div v-if="canScrollLeft" class="scroll-indicator scroll-indicator-left"></div>
          <div class="table-scroll" ref="tableScrollRef">
            <table class="strategy-table" data-testid="strategy-table">
              <thead>
              <tr>
                <th class="th-checkbox">
                  <input
                    type="checkbox"
                    :checked="allLegsSelected"
                    @change="toggleSelectAll"
                  />
                </th>
                <th>Expiry</th>
                <th>Type</th>
                <th>B/S</th>
                <th>Strike</th>
                <th>Lots</th>
                <th>Entry</th>
                <th>Qty</th>
                <th>CMP</th>
                <th>Exit P/L</th>
                <!-- Dynamic P/L Columns -->
                <th
                  v-for="spot in displayedSpotPrices"
                  :key="spot"
                  :class="['th-spot', { 'th-current-spot': isCurrentSpot(spot) }]"
                >
                  <div v-if="isCurrentSpot(spot)" class="spot-label">SPOT</div>
                  {{ formatSpotHeader(spot) }}
                </th>
              </tr>
              </thead>
            <tbody>
              <!-- Strategy Leg Rows -->
              <tr
                v-for="(leg, index) in filteredLegs"
                :key="leg.temp_id || leg.id"
                :class="['leg-row', leg.transaction_type === 'BUY' ? 'leg-buy' : 'leg-sell']"
              >
                <td class="td-checkbox">
                  <input
                    type="checkbox"
                    :checked="strategyStore.selectedLegIndices.includes(index)"
                    @change="strategyStore.toggleLegSelection(index)"
                  />
                </td>
                <td>
                  <select
                    :value="leg.expiry_date"
                    @change="handleLegUpdate(index, 'expiry_date', $event.target.value)"
                    class="strategy-select compact"
                  >
                    <option value="">Select</option>
                    <option v-for="exp in strategyStore.expiries" :key="exp" :value="exp">
                      {{ formatDate(exp) }}
                    </option>
                  </select>
                </td>
                <td>
                  <select
                    :value="leg.contract_type"
                    @change="handleLegUpdate(index, 'contract_type', $event.target.value)"
                    :class="['tag-select', leg.contract_type === 'CE' ? 'tag-ce' : 'tag-pe']"
                  >
                    <option value="CE">CE</option>
                    <option value="PE">PE</option>
                  </select>
                </td>
                <td>
                  <select
                    :value="leg.transaction_type"
                    @change="handleLegUpdate(index, 'transaction_type', $event.target.value)"
                    :class="['tag-select', leg.transaction_type === 'BUY' ? 'tag-buy' : 'tag-sell']"
                  >
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </td>
                <td>
                  <select
                    :value="leg.strike_price"
                    @change="handleLegUpdate(index, 'strike_price', $event.target.value)"
                    class="strategy-select compact"
                  >
                    <option value="">Select</option>
                    <option v-for="s in getStrikesForExpiry(leg.expiry_date)" :key="s" :value="s">
                      {{ s }}
                    </option>
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    :value="leg.lots"
                    @input="handleLegUpdate(index, 'lots', parseInt($event.target.value) || 1)"
                    min="1"
                    class="strategy-input compact text-center"
                    style="width: 60px;"
                  />
                </td>
                <td class="relative">
                  <input
                    type="number"
                    :value="leg.entry_price"
                    @input="handleLegUpdate(index, 'entry_price', parseFloat($event.target.value))"
                    @blur="handleLegUpdate(index, 'entry_price', parseFloat($event.target.value))"
                    step="0.05"
                    placeholder="Entry"
                    class="strategy-input compact text-right"
                    style="width: 80px;"
                  />
                  <!-- CMP indicator - shows when using CMP as entry price for calculation -->
                  <span
                    v-if="strategyStore.isLegUsingCMPEntry(leg)"
                    class="cmp-entry-indicator"
                    title="Using CMP as entry price for calculation"
                  >
                    ?
                  </span>
                </td>
                <td class="text-center font-semibold">
                  {{ leg.lots * strategyStore.lotSize }}
                </td>
                <td class="text-right">
                  <span v-if="strategyStore.getLegCMP(leg)" class="cmp-value">
                    {{ formatPrice(strategyStore.getLegCMP(leg)) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right font-semibold">
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
              <tr v-if="strategyStore.legs.length === 0" class="empty-state" data-testid="strategy-empty-state">
                <td colspan="100">
                  No legs added. Click "+ Add Row" to start building your strategy.
                </td>
              </tr>

              <!-- Total Row -->
              <tr v-if="strategyStore.legs.length > 0" class="total-row" data-testid="strategy-total-row">
                <td colspan="7" class="text-right">Total:</td>
                <td class="text-center font-bold">{{ strategyStore.totalQty }}</td>
                <td class="text-center">-</td>
                <td class="text-right font-bold" :class="getPnLClass(totalCurrentPnL)">
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
          <div v-if="canScrollRight" class="scroll-indicator scroll-indicator-right"></div>
        </div>

        <!-- Action Buttons -->
        <div class="action-bar" data-testid="strategy-action-bar">
          <div class="action-left">
            <button
              @click="strategyStore.removeSelectedLegs()"
              :disabled="strategyStore.selectedLegIndices.length === 0"
              class="strategy-btn strategy-btn-outline"
              data-testid="strategy-delete-legs-button"
            >
              Delete
            </button>
            <button
              @click="strategyStore.addLeg()"
              :disabled="!strategyStore.canAddRow"
              class="strategy-btn strategy-btn-outline"
              :style="strategyStore.canAddRow ? 'color: var(--kite-blue);' : 'opacity: 0.5; cursor: not-allowed;'"
              :title="strategyStore.canAddRow ? 'Add a new leg to the strategy' : 'Select an underlying first'"
              data-testid="strategy-add-row-button"
            >
              + Add Row
            </button>
            <button
              @click="handleRecalculate"
              :disabled="strategyStore.legs.length === 0 || strategyStore.isLoading"
              class="strategy-btn strategy-btn-primary"
              data-testid="strategy-recalculate-button"
            >
              {{ strategyStore.isLoading ? 'Calculating...' : 'ReCalculate' }}
            </button>
          </div>
          <div class="action-right">
            <button
              @click="strategyStore.importPositions()"
              class="strategy-btn strategy-btn-outline"
              data-testid="strategy-import-positions-button"
            >
              Import Positions
            </button>
            <button
              @click="strategyStore.updateFromPositions()"
              class="strategy-btn strategy-btn-outline"
              data-testid="strategy-update-positions-button"
            >
              Update Positions
            </button>
            <button
              @click="handleSaveStrategy"
              :disabled="strategyStore.legs.length === 0 || !strategyName || isSaving"
              class="strategy-btn strategy-btn-success"
              data-testid="strategy-save-button-bottom"
            >
              {{ isSaving ? 'Saving...' : 'Save' }}
            </button>
            <button
              @click="handleShare"
              :disabled="!strategyStore.currentStrategy"
              class="strategy-btn strategy-btn-outline"
              data-testid="strategy-share-button"
            >
              Share
            </button>
            <button
              @click="showOrderModal = true"
              :disabled="strategyStore.legs.length === 0 || !allLegsComplete"
              class="strategy-btn strategy-btn-primary"
              data-testid="strategy-basket-order-button"
            >
              Buy Basket Order
            </button>
          </div>
        </div>

        <!-- Payoff Chart -->
        <div class="payoff-section" v-if="displayedSpotPrices.length > 0" data-testid="strategy-payoff-section">
          <div class="payoff-header">
            <h3 class="section-title">Payoff Diagram</h3>
            <div class="payoff-legend">
              <span class="legend-item profit">
                <span class="legend-line"></span> Profit Zone
              </span>
              <span class="legend-item loss">
                <span class="legend-line"></span> Loss Zone
              </span>
              <span class="legend-item spot">
                <span class="legend-dot"></span> Current Spot
              </span>
            </div>
          </div>
          <div class="payoff-chart">
            <PayoffChart
              :spot-prices="chartSpotPrices"
              :total-pnl="chartTotalPnl"
              :current-spot="strategyStore.currentSpot"
            />
          </div>
        </div>

        <!-- Summary Cards -->
        <div class="summary-grid" data-testid="strategy-summary-grid">
          <!-- Max Profit Card -->
          <div class="strategy-summary-card profit" data-testid="strategy-max-profit-card">
            <div class="card-header">
              <div class="card-icon profit">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                </svg>
              </div>
              <span class="label">Max Profit</span>
            </div>
            <div class="value">{{ formatNumber(strategyStore.maxProfit) }}</div>
          </div>

          <!-- Max Loss Card -->
          <div class="strategy-summary-card loss" data-testid="strategy-max-loss-card">
            <div class="card-header">
              <div class="card-icon loss">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/>
                </svg>
              </div>
              <span class="label">Max Loss</span>
            </div>
            <div class="value">{{ formatNumber(strategyStore.maxLoss) }}</div>
          </div>

          <!-- Breakeven Card -->
          <div class="strategy-summary-card" data-testid="strategy-breakeven-card">
            <div class="card-header">
              <div class="card-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/>
                </svg>
              </div>
              <span class="label">Breakeven</span>
            </div>
            <div class="value" style="font-size: 18px;">
              {{ strategyStore.breakevens.length >= 2 ? formatNumber(strategyStore.breakevens[0]) + ' - ' + formatNumber(strategyStore.breakevens[1]) : (strategyStore.breakevens.length === 1 ? formatNumber(strategyStore.breakevens[0]) : '-') }}
            </div>
          </div>

          <!-- Risk/Reward Card -->
          <div class="strategy-summary-card" data-testid="strategy-risk-reward-card">
            <div class="card-header">
              <div class="card-icon" style="background: var(--kite-blue-light); color: var(--kite-blue);">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                </svg>
              </div>
              <span class="label">Risk/Reward</span>
            </div>
            <div class="value" style="color: var(--kite-blue);">{{ riskRewardRatio }}</div>
          </div>

          <!-- Current Spot Card -->
          <div class="strategy-summary-card spot" data-testid="strategy-spot-card">
            <div class="card-header">
              <div class="card-icon spot">
                <div class="pulse-dot"></div>
              </div>
              <span class="label">{{ strategyStore.underlying }} Spot</span>
            </div>
            <div class="value">{{ formatNumber(strategyStore.currentSpot) }}</div>
            <div class="timestamp">{{ strategyStore.lastUpdated }}</div>
          </div>
        </div>

      </div><!-- End strategy-container -->

      <!-- Save Success Toast -->
      <div v-if="showSaveSuccess" class="toast-success">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

      <!-- Replace Legs Confirmation Modal -->
      <div v-if="showReplaceConfirm" class="modal-overlay" data-testid="strategy-replace-legs-modal">
        <div class="modal-content">
          <h3 class="modal-title">Replace Existing Legs?</h3>
          <p class="modal-text">
            Changing strategy type will replace your current {{ strategyStore.legs.length }} leg(s).
            This action cannot be undone.
          </p>
          <div class="modal-actions">
            <button
              @click="cancelReplaceLegs"
              class="strategy-btn strategy-btn-outline"
              data-testid="strategy-replace-legs-cancel"
            >
              Cancel
            </button>
            <button
              @click="confirmReplaceLegs"
              class="strategy-btn strategy-btn-primary"
              data-testid="strategy-replace-legs-confirm"
            >
              Replace Legs
            </button>
          </div>
        </div>
      </div>
    </div><!-- End strategy-page -->
  </KiteLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useStrategyStore } from '../stores/strategy'
import { useWatchlistStore } from '../stores/watchlist'
import { useStrategyTypes } from '@/constants/strategyTypes'
import KiteLayout from '../components/layout/KiteLayout.vue'
import ShareStrategyModal from '../components/strategy/ShareStrategyModal.vue'
import BasketOrderModal from '../components/strategy/BasketOrderModal.vue'
import PayoffChart from '../components/strategy/PayoffChart.vue'
import PnLCell from '../components/strategy/PnLCell.vue'
import '@/assets/css/strategy-table.css'

const route = useRoute()
const strategyStore = useStrategyStore()
const watchlistStore = useWatchlistStore()

// Strategy Types from centralized constants
const {
  strategyTypes,
  categories,
  strategiesByCategory,
  loadStrategyTypes,
  getStrategyLegs
} = useStrategyTypes()

// Selected strategy type for auto-populating legs
const selectedStrategyType = ref('')
const previousStrategyType = ref('')
const showReplaceConfirm = ref(false)

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

// Table scroll refs
const tableScrollRef = ref(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

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

  // ALWAYS add breakeven values as columns (keep exact values for P/L = 0)
  breakevens.forEach(be => {
    // Keep exact breakeven value, not rounded, so P/L calculates to exactly 0
    // Use tolerance check for duplicates since we're dealing with floats
    if (!result.some(s => Math.abs(s - be) < 0.1)) {
      result.push(be)
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
  // Parse strike_price as number for consistent matching with dropdown options
  const parsedValue = field === 'strike_price' && value ? parseFloat(value) : value
  const updates = { [field]: parsedValue }
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
    // First try exact match (use tolerance for floating point breakeven values)
    const exactIndex = spots.findIndex(s => Math.abs(s - spot) < 0.01)
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

  // First try exact match (use tolerance for floating point breakeven values)
  const fullIndex = spots.findIndex(s => Math.abs(s - spot) < 0.01)
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

// Format spot value for column header display
// Rounds decimals (breakevens) but keeps integers as-is
function formatSpotHeader(spot) {
  return Number.isInteger(spot) ? spot : Math.round(spot)
}

// Scroll indicator functions
function updateScrollIndicators() {
  const container = tableScrollRef.value
  if (!container) return

  canScrollLeft.value = container.scrollLeft > 0
  canScrollRight.value = container.scrollLeft < (container.scrollWidth - container.clientWidth - 1)
}

function scrollToCurrentSpot() {
  nextTick(() => {
    const container = tableScrollRef.value
    if (!container) return

    const spotColumn = container.querySelector('.th-current-spot')
    if (spotColumn) {
      const containerWidth = container.clientWidth
      const columnLeft = spotColumn.offsetLeft
      const columnWidth = spotColumn.offsetWidth

      // Center the current spot column in view
      const scrollPosition = columnLeft - (containerWidth / 2) + (columnWidth / 2)
      container.scrollTo({ left: scrollPosition, behavior: 'smooth' })
    }

    // Update scroll indicators after scrolling
    setTimeout(updateScrollIndicators, 300)
  })
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

// Handle strategy type change - auto-populate legs
function onStrategyTypeChange() {
  const newType = selectedStrategyType.value

  // If custom or empty, don't auto-populate
  if (!newType || newType === 'custom') {
    previousStrategyType.value = newType
    return
  }

  // Check if legs exist - show confirmation if so
  if (strategyStore.legs.length > 0) {
    showReplaceConfirm.value = true
    return
  }

  // No existing legs - auto-populate directly
  applyStrategyTypeLegs(newType)
}

// Apply legs from strategy type template
async function applyStrategyTypeLegs(strategyTypeKey) {
  const templateLegs = getStrategyLegs(strategyTypeKey)
  if (!templateLegs || templateLegs.length === 0) return

  // Get the first available expiry
  const expiry = strategyStore.expiries[0] || null

  // Ensure we have spot price for ATM calculation
  if (!strategyStore.currentSpot) {
    await strategyStore.fetchSpotPrice()
  }

  // Ensure strikes are loaded for the expiry
  if (expiry && (!strategyStore.strikes[expiry] || strategyStore.strikes[expiry].length === 0)) {
    await strategyStore.fetchStrikes(expiry)
  }

  // Get ATM strike
  const strikesArray = expiry ? strategyStore.strikes[expiry] : []
  const atmStrike = strategyStore.findNearestStrike(strategyStore.currentSpot, strikesArray)

  // Clear existing legs by removing all
  while (strategyStore.legs.length > 0) {
    strategyStore.removeLeg(0)
  }

  // Add new legs from template with calculated strikes
  for (const leg of templateLegs) {
    // Calculate strike based on ATM + offset
    let calculatedStrike = null
    if (atmStrike && leg.strike_offset !== undefined) {
      const targetStrike = atmStrike + leg.strike_offset
      // Find the nearest available strike to the target
      calculatedStrike = strategyStore.findNearestStrike(targetStrike, strikesArray)
    }

    await strategyStore.addLeg({
      temp_id: `leg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      transaction_type: leg.action, // BUY or SELL
      contract_type: leg.type, // CE or PE
      strike_price: calculatedStrike, // Calculated from ATM + offset
      expiry_date: expiry,
      lots: 1,
      entry_price: null
    })
  }

  previousStrategyType.value = strategyTypeKey
  showReplaceConfirm.value = false
}

// Confirm replace legs
function confirmReplaceLegs() {
  applyStrategyTypeLegs(selectedStrategyType.value)
}

// Cancel replace legs - revert selection
function cancelReplaceLegs() {
  selectedStrategyType.value = previousStrategyType.value
  showReplaceConfirm.value = false
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
  // Auto-scroll to center current spot after calculation
  scrollToCurrentSpot()
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

async function handleDeleteStrategy() {
  if (!selectedStrategyId.value) return

  if (!confirm('Are you sure you want to delete this strategy?')) return

  const result = await strategyStore.deleteStrategy(selectedStrategyId.value)
  if (result.success) {
    // Reset to new strategy state
    selectedStrategyId.value = ''
    strategyName.value = ''
    strategyStore.clearLegs()
    await loadSavedStrategies()
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
  // Load strategy types from backend (non-blocking - will use fallback if API fails)
  loadStrategyTypes().catch(() => {
    // Silently use fallback data which is set in strategyTypes.js
  })

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

    // Auto-calculate if legs exist (e.g., from Option Chain navigation)
    if (strategyStore.legs.length > 0) {
      await strategyStore.calculatePnL()
    }
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

  // Setup scroll event listener for indicators
  nextTick(() => {
    if (tableScrollRef.value) {
      tableScrollRef.value.addEventListener('scroll', updateScrollIndicators)
      updateScrollIndicators()
    }
  })
})

onUnmounted(() => {
  strategyStore.clearStrategy()
  // Cleanup scroll event listener
  if (tableScrollRef.value) {
    tableScrollRef.value.removeEventListener('scroll', updateScrollIndicators)
  }
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
/* ===== Strategy Page Layout ===== */
.strategy-page {
  min-height: calc(100vh - 48px);
  background: var(--kite-body-bg, #ffffff);
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: hidden;
}

.strategy-container {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 20px 24px;
}

/* ===== Toolbar ===== */
.strategy-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 20px;
  background: white;
  border: 1px solid var(--kite-border-light);
  border-radius: 4px;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex-shrink: 1;
}

.underlying-tabs {
  display: flex;
  gap: 4px;
}

.underlying-tab {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--kite-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.underlying-tab:hover {
  color: var(--kite-text-primary);
}

.underlying-tab.active {
  color: var(--kite-blue);
  border-bottom-color: var(--kite-blue);
  background: transparent;
}

.mode-label {
  font-size: 12px;
  color: var(--kite-text-secondary);
}

.mode-btn {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--kite-text-secondary);
  background: transparent;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.mode-btn.active {
  background: var(--kite-blue-light);
  color: var(--kite-blue);
  border-color: var(--kite-blue);
}

.loading-indicator {
  font-size: 12px;
  color: var(--kite-text-muted);
}

/* ===== Selector Bar ===== */
.strategy-selector-bar {
  background: white;
  border: 1px solid var(--kite-border-light);
  border-radius: 4px;
  padding: 12px 20px;
  margin-bottom: 16px;
}

.selector-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selector-left, .selector-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.form-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-group.compact {
  gap: 4px;
}

.form-label {
  font-size: 13px;
  color: var(--kite-text-secondary);
  font-weight: 500;
}

.form-label-sm {
  font-size: 11px;
  color: var(--kite-text-muted);
}

/* ===== Strategy Table ===== */
.strategy-table-wrapper {
  background: white;
  border: 1px solid var(--kite-border-light);
  border-radius: 4px;
  margin-bottom: 16px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  position: relative;
  overflow: hidden;  /* Prevent wrapper from overflowing container */
}

.table-scroll {
  overflow-x: auto;
  scroll-behavior: smooth;
}

/* Scroll Indicators */
.scroll-indicator {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 40px;
  pointer-events: none;
  z-index: 10;
}

.scroll-indicator-left {
  left: 0;
  background: linear-gradient(to right, rgba(255, 255, 255, 0.95), transparent);
  border-radius: 4px 0 0 4px;
}

.scroll-indicator-right {
  right: 0;
  background: linear-gradient(to left, rgba(255, 255, 255, 0.95), transparent);
  border-radius: 0 4px 4px 0;
}

.strategy-table {
  width: 100%;
  border-collapse: collapse;
}

.strategy-table thead {
  background: var(--kite-table-header-bg);
}

.strategy-table th {
  padding: 8px 10px;
  font-size: 10px;
  font-weight: 600;
  color: var(--kite-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  text-align: center;
  white-space: nowrap;
  border-bottom: 1px solid var(--kite-border);
}

.strategy-table td {
  padding: 6px 10px;
  font-size: 12px;
  color: var(--kite-text-primary);
  vertical-align: middle;
}

.strategy-table tbody tr {
  border-bottom: 1px solid var(--kite-border-light);
  transition: background 0.15s ease;
}

.strategy-table tbody tr:hover {
  background: var(--kite-table-hover, #f5f8fa);
}

.leg-row.leg-buy {
  background: #f8fbff;
  border-left: 3px solid var(--kite-blue);
}

.leg-row.leg-sell {
  background: #fffbf8;
  border-left: 3px solid var(--kite-orange, #ff9800);
}

.th-checkbox, .td-checkbox {
  width: 40px;
  text-align: center;
}

.th-spot {
  min-width: 70px;
}

.th-current-spot {
  background: #fff3cd !important;
  color: #856404;
}

.spot-label {
  font-size: 9px;
  font-weight: 700;
  color: #856404;
}

.total-row {
  background: var(--kite-table-header-bg);
  font-weight: 600;
  border-top: 2px solid var(--kite-border);
}

.empty-state td {
  padding: 48px;
  text-align: center;
  color: var(--kite-text-muted);
}

/* ===== Tags ===== */
.tag {
  display: inline-block;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
}

.tag-select {
  appearance: none;
  -webkit-appearance: none;
  border: none;
  background: transparent;
  font-weight: 600;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  text-align: center;
}

.tag-select.tag-ce {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue, #1976d2);
}

.tag-select.tag-pe {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red, #d32f2f);
}

.tag-select.tag-buy {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue, #1976d2);
}

.tag-select.tag-sell {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange, #f57c00);
}

/* ===== Values ===== */
.cmp-value {
  color: var(--kite-blue);
  font-weight: 500;
}

.cmp-entry-indicator {
  position: absolute;
  top: -2px;
  right: -6px;
  width: 14px;
  height: 14px;
  background: var(--kite-blue, #2962ff);
  color: white;
  font-size: 10px;
  font-weight: bold;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: help;
}

.no-value {
  color: var(--kite-text-muted);
}

/* ===== Form Controls ===== */
.strategy-select.compact,
.strategy-input.compact {
  padding: 6px 10px;
  font-size: 12px;
}

/* ===== Action Bar ===== */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  border: 1px solid var(--kite-border-light);
  border-radius: 4px;
  padding: 12px 20px;
  margin-bottom: 16px;
}

.action-left, .action-right {
  display: flex;
  gap: 8px;
}

/* ===== Error Alert ===== */
.error-alert {
  background: var(--kite-red-light);
  border: 1px solid var(--kite-red);
  color: #c62828;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.error-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #c62828;
  cursor: pointer;
}

/* ===== Payoff Section ===== */
.payoff-section {
  background: white;
  border: 1px solid var(--kite-border-light);
  border-radius: 4px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.payoff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.payoff-legend {
  display: flex;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.legend-item.profit { color: var(--kite-green); }
.legend-item.loss { color: var(--kite-red); }
.legend-item.spot { color: #f0ad4e; }

.legend-line {
  width: 16px;
  height: 3px;
  border-radius: 2px;
}

.legend-item.profit .legend-line { background: var(--kite-green); }
.legend-item.loss .legend-line { background: var(--kite-red); }

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #f0ad4e;
}

.payoff-chart {
  height: 220px;
}

/* ===== Summary Grid ===== */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.card-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--kite-text-muted);
}

.card-icon svg {
  width: 18px;
  height: 18px;
}

.card-icon.profit {
  background: transparent;
  color: var(--kite-green);
}

.card-icon.loss {
  background: transparent;
  color: var(--kite-red);
}

.card-icon.spot {
  background: transparent;
}

.pulse-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #f0ad4e;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
  100% { opacity: 1; transform: scale(1); }
}

.strategy-summary-card.spot {
  background: #fffdf5;
  border-color: var(--kite-border);
}

.strategy-summary-card.spot .label {
  color: var(--kite-text-secondary);
}

.strategy-summary-card.spot .value {
  color: var(--kite-text-primary);
}

.timestamp {
  font-size: 11px;
  color: var(--kite-text-muted);
  margin-top: 4px;
}

/* ===== Toast ===== */
.toast-success {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: var(--kite-green);
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: var(--kite-shadow-lg);
  z-index: 1000;
}

.toast-success svg {
  width: 20px;
  height: 20px;
}

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .strategy-toolbar {
    flex-direction: column;
    gap: 12px;
  }

  .selector-row {
    flex-direction: column;
    gap: 12px;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-bar {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
