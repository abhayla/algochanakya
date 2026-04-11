<template>
  <KiteLayout>
    <div class="optionchain-page" data-testid="optionchain-page">

      <BrokerUpgradeBanner screen="optionchain" />
      <MarketStatusBanner :data-freshness="store.dataFreshness" screen="optionchain" />

      <!-- Page Header -->
      <div class="page-header" data-testid="optionchain-header">
        <div class="header-left">
          <h1 class="page-title">Option Chain</h1>

          <!-- Underlying Tabs -->
          <div class="underlying-tabs" data-testid="optionchain-underlying-tabs" role="tablist">
            <button
              v-for="ul in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']"
              :key="ul"
              role="tab"
              :class="['tab-btn', { active: store.underlying === ul }]"
              @click="handleUnderlyingChange(ul)"
              :data-testid="'optionchain-underlying-' + ul.toLowerCase()"
              :aria-selected="store.underlying === ul"
            >
              {{ ul }}
            </button>
          </div>

          <!-- Expiry Select -->
          <select v-model="store.expiry" @change="handleExpiryChange" class="expiry-select" data-testid="optionchain-expiry-select" aria-label="Select expiry date">
            <option v-for="exp in store.expiries" :key="exp" :value="exp">{{ formatExpiry(exp) }}</option>
          </select>
        </div>

        <div class="header-right">
          <DataSourceBadge screen="optionchain" />
          <!-- Spot Price Box -->
          <div class="spot-box" data-testid="optionchain-spot-box">
            <span class="spot-label">Spot</span>
            <span class="spot-price" data-testid="optionchain-spot-price">{{ formatNumber(store.spotPrice) }}</span>
          </div>

          <!-- DTE -->
          <div class="dte-box" data-testid="optionchain-dte-box">
            <span class="dte-label">DTE</span>
            <span class="dte-value" data-testid="optionchain-dte-value">{{ store.daysToExpiry }}</span>
          </div>

          <!-- Greeks Toggle -->
          <label class="toggle-label" data-testid="optionchain-greeks-toggle">
            <input type="checkbox" v-model="store.showGreeks" />
            <span>Greeks</span>
          </label>

          <!-- Live Toggle -->
          <label class="live-toggle" data-testid="optionchain-live-toggle">
            <input type="checkbox" v-model="store.isLiveUpdatesEnabled" />
            <span class="live-label">
              <span v-if="watchlistStore.isConnected && store.isLiveUpdatesEnabled" class="live-dot"></span>
              Live
            </span>
          </label>

          <!-- Find Strike Button -->
          <button @click="store.toggleStrikeFinder()" class="find-strike-btn" data-testid="optionchain-strike-finder-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            Find Strike
          </button>

          <!-- Refresh -->
          <button @click="store.fetchOptionChain()" class="refresh-btn" :disabled="store.isLoading" data-testid="optionchain-refresh-button">
            {{ store.isLoading ? 'Loading...' : 'Refresh' }}
          </button>
        </div>
      </div>

      <!-- Summary Bar -->
      <div class="summary-bar" data-testid="optionchain-summary-bar">
        <div class="summary-item" data-testid="optionchain-pcr">
          <span class="label">PCR</span>
          <span :class="['value', store.summary.pcr > 1 ? 'text-green' : 'text-red']">
            {{ store.summary.pcr }}
          </span>
        </div>
        <div class="summary-item" data-testid="optionchain-max-pain">
          <span class="label">Max Pain</span>
          <span class="value text-purple">{{ formatNumber(store.summary.max_pain) }}</span>
        </div>
        <div class="summary-item" data-testid="optionchain-ce-oi">
          <span class="label">CE OI</span>
          <span class="value text-red">{{ formatOI(store.summary.total_ce_oi) }}</span>
        </div>
        <div class="summary-item" data-testid="optionchain-pe-oi">
          <span class="label">PE OI</span>
          <span class="value text-green">{{ formatOI(store.summary.total_pe_oi) }}</span>
        </div>
        <div class="summary-item" data-testid="optionchain-lot-size">
          <span class="label">Lot Size</span>
          <span class="value">{{ store.lotSize }}</span>
        </div>

        <div class="summary-right">
          <!-- Grid Interval Toggle - only show for underlyings with 50-point strikes -->
          <div v-if="store.has50PointStrikes" class="interval-toggle" data-testid="optionchain-interval-toggle">
            <span class="interval-label">Strike Interval</span>
            <label class="interval-option">
              <input
                type="radio"
                name="grid-interval"
                :value="50"
                :checked="store.effectiveGridInterval === 50"
                @change="store.setLocalGridInterval(50)"
                data-testid="optionchain-interval-50"
              />
              <span>50</span>
            </label>
            <label class="interval-option">
              <input
                type="radio"
                name="grid-interval"
                :value="100"
                :checked="store.effectiveGridInterval === 100"
                @change="store.setLocalGridInterval(100)"
                data-testid="optionchain-interval-100"
              />
              <span>100</span>
            </label>
          </div>

          <select v-model="store.strikesRange" class="range-select" data-testid="optionchain-strikes-range" aria-label="Number of strikes to display">
            <option :value="5">5 Strikes</option>
            <option :value="10">10 Strikes</option>
            <option :value="15">15 Strikes</option>
            <option :value="20">20 Strikes</option>
            <option :value="30">30 Strikes</option>
            <option :value="50">All Strikes</option>
          </select>
        </div>
      </div>

      <!-- Strike Finder Panel -->
      <StrikeFinder @select-strike="handleStrikeSelected" />

      <!-- Error Alert -->
      <div v-if="store.error" class="error-alert" data-testid="optionchain-error">
        <span>{{ store.error }}</span>
        <button @click="store.error = null" class="close-btn">&times;</button>
      </div>

      <!-- Loading State -->
      <div v-if="store.isLoading && store.chain.length === 0" class="loading-state" data-testid="optionchain-loading">
        <div class="spinner"></div>
        <p>Loading option chain...</p>
      </div>

      <!-- Finding #1: Market closed banner when LTPs are 0 -->
      <div v-if="isMarketClosed && store.chain.length > 0" class="market-closed-banner" data-testid="optionchain-market-closed">
        Market Closed — showing last available data. Live prices will update when market opens at 9:15 AM IST.
      </div>

      <!-- Option Chain Table -->
      <div v-if="!store.isLoading || store.chain.length > 0" class="chain-table-container scrollable-container" ref="tableContainer" data-testid="optionchain-table-container">
        <table class="chain-table" data-testid="optionchain-table">
          <thead>
            <!-- Finding #4: CALLS/PUTS header labels -->
            <tr class="side-labels-row">
              <th :colspan="store.showGreeks ? 11 : 7" class="ce-col calls-label">CALLS (CE)</th>
              <th class="strike-col"></th>
              <th :colspan="store.showGreeks ? 11 : 7" class="pe-col puts-label">PUTS (PE)</th>
            </tr>
            <tr>
              <!-- CE Side -->
              <th class="ce-col add-col" title="Add to Strategy Builder"></th>
              <th class="ce-col" title="Open Interest">OI</th>
              <th class="ce-col" title="OI Change">Chg</th>
              <th class="ce-col" title="Volume">Vol</th>
              <th class="ce-col" title="Implied Volatility">IV</th>
              <th v-if="store.showGreeks" class="ce-col greek-col" title="Delta">Delta</th>
              <th v-if="store.showGreeks" class="ce-col greek-col" title="Gamma">Gamma</th>
              <th v-if="store.showGreeks" class="ce-col greek-col" title="Theta">Theta</th>
              <th v-if="store.showGreeks" class="ce-col greek-col" title="Vega">Vega</th>
              <th class="ce-col" title="Last Traded Price">LTP</th>
              <th class="ce-col" title="Price Change %">Chg%</th>

              <!-- Strike -->
              <th class="strike-col">STRIKE</th>

              <!-- PE Side -->
              <th class="pe-col" title="Price Change %">Chg%</th>
              <th class="pe-col" title="Last Traded Price">LTP</th>
              <th v-if="store.showGreeks" class="pe-col greek-col" title="Delta">Delta</th>
              <th v-if="store.showGreeks" class="pe-col greek-col" title="Gamma">Gamma</th>
              <th v-if="store.showGreeks" class="pe-col greek-col" title="Theta">Theta</th>
              <th v-if="store.showGreeks" class="pe-col greek-col" title="Vega">Vega</th>
              <th class="pe-col" title="Implied Volatility">IV</th>
              <th class="pe-col" title="Volume">Vol</th>
              <th class="pe-col" title="OI Change">Chg</th>
              <th class="pe-col" title="Open Interest">OI</th>
              <th class="pe-col add-col" title="Add to Strategy Builder"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in store.filteredChain"
              :key="row.strike"
              :class="[
                'chain-row',
                { 'atm-row': row.is_atm },
                { 'itm-ce': row.is_itm_ce && !row.is_atm },
                { 'itm-pe': row.is_itm_pe && !row.is_atm }
              ]"
              :data-testid="'optionchain-strike-row-' + row.strike"
              :data-atm-row="row.is_atm || undefined"
            >
              <!-- CE Add -->
              <td class="ce-col add-col">
                <button
                  v-if="row.ce"
                  @click="toggleStrike(row.strike, 'CE')"
                  :class="['add-btn', 'ce', { selected: store.isStrikeSelected(row.strike, 'CE') }]"
                  :data-testid="'optionchain-ce-add-' + row.strike"
                  :title="store.isStrikeSelected(row.strike, 'CE') ? 'Remove CE ' + row.strike + ' from Strategy' : 'Add CE ' + row.strike + ' to Strategy Builder'"
                >
                  {{ store.isStrikeSelected(row.strike, 'CE') ? '&#10003;' : '+' }}
                </button>
              </td>

              <!-- CE Data -->
              <td class="ce-col oi-col">
                <div class="oi-cell">
                  <div class="oi-bar ce" :style="{ width: store.getOIBarWidth(row.ce?.oi, 'ce') + 'px' }"></div>
                  <span>{{ formatOI(row.ce?.oi) }}</span>
                </div>
              </td>
              <td class="ce-col" :class="getChangeClass(row.ce?.change)">{{ formatChange(row.ce?.change) }}</td>
              <td class="ce-col text-muted">{{ formatOI(row.ce?.volume) }}</td>
              <td class="ce-col">{{ row.ce?.iv || '-' }}</td>
              <td v-if="store.showGreeks" class="ce-col text-muted" :data-testid="'optionchain-ce-delta-' + row.strike">{{ row.ce?.delta?.toFixed(2) || '-' }}</td>
              <td v-if="store.showGreeks" class="ce-col text-muted" :data-testid="'optionchain-ce-gamma-' + row.strike">{{ row.ce?.gamma?.toFixed(4) || '-' }}</td>
              <td v-if="store.showGreeks" class="ce-col text-muted" :data-testid="'optionchain-ce-theta-' + row.strike">{{ row.ce?.theta?.toFixed(2) || '-' }}</td>
              <td v-if="store.showGreeks" class="ce-col text-muted" :data-testid="'optionchain-ce-vega-' + row.strike">{{ row.ce?.vega?.toFixed(2) || '-' }}</td>
              <td class="ce-col ltp-col" :class="{ 'itm': row.is_itm_ce }" data-testid="optionchain-ltp-cell">{{ formatPrice(row.ce?.ltp) }}</td>
              <td class="ce-col" :class="getChangeClass(row.ce?.change)">{{ formatPct(row.ce?.change_pct) }}</td>

              <!-- Strike -->
              <td class="strike-col">
                <span class="strike-value">{{ row.strike }}</span>
                <span v-if="row.is_atm" class="atm-badge" data-testid="optionchain-atm-badge">ATM</span>
              </td>

              <!-- PE Data -->
              <td class="pe-col" :class="getChangeClass(row.pe?.change)">{{ formatPct(row.pe?.change_pct) }}</td>
              <td class="pe-col ltp-col" :class="{ 'itm': row.is_itm_pe }" data-testid="optionchain-ltp-cell">{{ formatPrice(row.pe?.ltp) }}</td>
              <td v-if="store.showGreeks" class="pe-col text-muted" :data-testid="'optionchain-pe-delta-' + row.strike">{{ row.pe?.delta?.toFixed(2) || '-' }}</td>
              <td v-if="store.showGreeks" class="pe-col text-muted" :data-testid="'optionchain-pe-gamma-' + row.strike">{{ row.pe?.gamma?.toFixed(4) || '-' }}</td>
              <td v-if="store.showGreeks" class="pe-col text-muted" :data-testid="'optionchain-pe-theta-' + row.strike">{{ row.pe?.theta?.toFixed(2) || '-' }}</td>
              <td v-if="store.showGreeks" class="pe-col text-muted" :data-testid="'optionchain-pe-vega-' + row.strike">{{ row.pe?.vega?.toFixed(2) || '-' }}</td>
              <td class="pe-col">{{ row.pe?.iv || '-' }}</td>
              <td class="pe-col text-muted">{{ formatOI(row.pe?.volume) }}</td>
              <td class="pe-col" :class="getChangeClass(row.pe?.change)">{{ formatChange(row.pe?.change) }}</td>
              <td class="pe-col oi-col">
                <div class="oi-cell reverse">
                  <span>{{ formatOI(row.pe?.oi) }}</span>
                  <div class="oi-bar pe" :style="{ width: store.getOIBarWidth(row.pe?.oi, 'pe') + 'px' }"></div>
                </div>
              </td>

              <!-- PE Add -->
              <td class="pe-col add-col">
                <button
                  v-if="row.pe"
                  @click="toggleStrike(row.strike, 'PE')"
                  :class="['add-btn', 'pe', { selected: store.isStrikeSelected(row.strike, 'PE') }]"
                  :data-testid="'optionchain-pe-add-' + row.strike"
                  :title="store.isStrikeSelected(row.strike, 'PE') ? 'Remove PE ' + row.strike + ' from Strategy' : 'Add PE ' + row.strike + ' to Strategy Builder'"
                >
                  {{ store.isStrikeSelected(row.strike, 'PE') ? '&#10003;' : '+' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Empty State -->
        <div v-if="store.chain.length === 0 && !store.isLoading" class="empty-state" data-testid="optionchain-empty-state">
          <p>No option chain data</p>
          <p class="hint">Select an expiry to view option chain</p>
        </div>
      </div>

      <!-- Selected Bar -->
      <div v-if="store.selectedStrikes.length > 0" class="selected-bar" data-testid="optionchain-selected-bar">
        <div class="selected-items">
          <span class="selected-label">Selected:</span>
          <span
            v-for="s in store.selectedStrikes"
            :key="s.key"
            :class="['selected-chip', s.type.toLowerCase()]"
            :data-testid="'optionchain-selected-chip-' + s.strike + '-' + s.type"
          >
            {{ s.type }} {{ s.strike }} @ {{ s.ltp?.toFixed(2) }}
            <button @click="store.toggleStrikeSelection(s.strike, s.type)" class="chip-remove">&times;</button>
          </span>
        </div>
        <div class="selected-actions">
          <button @click="store.clearSelection()" class="btn-clear" data-testid="optionchain-clear-selection">Clear</button>
          <button @click="goToStrategy()" class="btn-add-strategy" data-testid="optionchain-add-to-strategy">Add to Strategy</button>
        </div>
      </div>

    </div>
  </KiteLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import StrikeFinder from '@/components/optionchain/StrikeFinder.vue'
import { useOptionChainStore } from '@/stores/optionchain'
import { useStrategyStore } from '@/stores/strategy'
import BrokerUpgradeBanner from '@/components/common/BrokerUpgradeBanner.vue'
import DataSourceBadge from '@/components/common/DataSourceBadge.vue'
import MarketStatusBanner from '@/components/common/MarketStatusBanner.vue'
import { useWatchlistStore } from '@/stores/watchlist'
import { useScrollIndicator } from '@/composables/useScrollIndicator'

const store = useOptionChainStore()
const strategyStore = useStrategyStore()
const watchlistStore = useWatchlistStore()
const router = useRouter()

// Finding #1: Market closed detection
const isMarketClosed = computed(() => {
  const now = new Date()
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }))
  const hours = ist.getHours()
  const minutes = ist.getMinutes()
  const day = ist.getDay()
  const timeInMinutes = hours * 60 + minutes
  if (day === 0 || day === 6) return true
  return timeInMinutes < 555 || timeInMinutes > 930
})

// Finding #10: Keyboard shortcuts for tab switching
const handleKeyDown = (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return
  if (e.key === '1') store.setUnderlying('NIFTY')
  else if (e.key === '2') store.setUnderlying('BANKNIFTY')
  else if (e.key === '3') store.setUnderlying('FINNIFTY')
  else if (e.key === 'g' || e.key === 'G') store.showGreeks = !store.showGreeks
}

// Track subscribed tokens to avoid re-subscribing
const subscribedTokens = ref(new Set())

// Table scroll indicator
const tableContainer = ref(null)
useScrollIndicator(tableContainer)

// Format helpers
const formatNumber = (num) => {
  if (!num) return '-'
  return new Intl.NumberFormat('en-IN').format(Math.round(num))
}

const formatPrice = (price) => {
  if (!price && price !== 0) return '-'
  return price.toFixed(2)
}

const formatOI = (oi) => {
  if (!oi) return '-'
  if (oi >= 10000000) return (oi / 10000000).toFixed(2) + 'Cr'
  if (oi >= 100000) return (oi / 100000).toFixed(2) + 'L'
  if (oi >= 1000) return (oi / 1000).toFixed(1) + 'K'
  return oi.toString()
}

const formatOIChange = (change) => {
  if (!change) return '-'
  return (change > 0 ? '+' : '') + formatOI(change)
}

const formatChange = (change) => {
  if (!change && change !== 0) return '-'
  return (change > 0 ? '+' : '') + change.toFixed(2)
}

const formatPct = (pct) => {
  if (!pct && pct !== 0) return '-'
  return (pct > 0 ? '+' : '') + pct.toFixed(2) + '%'
}

const formatExpiry = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

const getChangeClass = (value) => {
  if (!value && value !== 0) return 'text-muted'
  if (value > 0) return 'text-green'
  if (value < 0) return 'text-red'
  return 'text-muted'
}

// Actions
const handleUnderlyingChange = async (ul) => {
  await store.setUnderlying(ul)
  if (store.expiry) {
    await store.fetchOptionChain()
  }
}

const handleExpiryChange = async () => {
  if (store.expiry) {
    await store.fetchOptionChain()
  }
}

const toggleStrike = (strike, type) => {
  store.toggleStrikeSelection(strike, type)
}

const goToStrategy = () => {
  const payload = store.getAddToStrategyPayload()

  // Set underlying in strategy store
  strategyStore.setUnderlying(store.underlying)

  // Add each selected strike as a leg
  payload.forEach(leg => {
    strategyStore.addLegFromOptionChain(leg)
  })

  store.clearSelection()
  router.push('/strategy')
}

const handleStrikeSelected = (strike) => {
  // Close the strike finder
  store.toggleStrikeFinder()

  // Scroll to the selected strike row if it exists
  if (typeof strike === 'object' && strike.strike) {
    const strikeValue = strike.strike
    const tableEl = tableContainer.value
    if (tableEl) {
      const strikeRow = tableEl.querySelector(`[data-strike="${strikeValue}"]`)
      if (strikeRow) {
        strikeRow.scrollIntoView({ behavior: 'smooth', block: 'center' })
        // Optionally highlight the row briefly
        strikeRow.classList.add('highlight-strike')
        setTimeout(() => strikeRow.classList.remove('highlight-strike'), 2000)
      }
    }
  }
}

// Subscribe to option tokens for live updates
function subscribeToOptionTokens() {
  if (!watchlistStore.isConnected) return

  const tokens = store.getAllOptionTokens()
  const indexToken = store.getIndexToken()

  // Add index token for spot price updates
  const allTokens = [indexToken, ...tokens]

  // Filter out already subscribed tokens
  const newTokens = allTokens.filter(t => !subscribedTokens.value.has(t))

  if (newTokens.length > 0) {
    watchlistStore.subscribeToTokens(newTokens, 'quote')
    newTokens.forEach(t => subscribedTokens.value.add(t))
    console.log(`[OptionChain] Subscribed to ${newTokens.length} tokens`)
  }
}

// Watch for WebSocket ticks and update option chain prices
watch(() => watchlistStore.ticks, (newTicks) => {
  if (!store.isLiveUpdatesEnabled) return

  const ticksArray = Object.entries(newTicks).map(([token, data]) => ({
    token: parseInt(token),
    ltp: data.ltp,
    change: data.change,
    change_percent: data.change_percent
  }))

  if (ticksArray.length > 0) {
    store.updateLivePrices(ticksArray)
  }
}, { deep: true })

// Watch for chain changes to subscribe to new tokens
watch(() => store.chain, (newChain) => {
  if (newChain.length > 0) {
    // Small delay to ensure WebSocket is ready
    setTimeout(() => {
      subscribeToOptionTokens()
    }, 100)
  }
}, { deep: true })

// Watch for WebSocket connection and subscribe when connected
watch(() => watchlistStore.isConnected, (connected) => {
  if (connected && store.chain.length > 0) {
    subscribeToOptionTokens()
  }
})

// Initialize
onMounted(async () => {
  // Finding #10: Keyboard shortcuts
  document.addEventListener('keydown', handleKeyDown)

  // Connect to WebSocket if not already connected
  if (!watchlistStore.isConnected) {
    watchlistStore.connectWebSocket()
  }

  await store.fetchExpiries()
  if (store.expiry) {
    await store.fetchOptionChain()
  }
})

// Cleanup subscriptions on unmount
onUnmounted(() => {
  // Finding #10: Remove keyboard shortcuts
  document.removeEventListener('keydown', handleKeyDown)

  // Unsubscribe from option tokens (keep index tokens as they're shared)
  const optionTokens = store.getAllOptionTokens()
  if (optionTokens.length > 0 && watchlistStore.isConnected) {
    watchlistStore.unsubscribeFromTokens(optionTokens)
  }
  subscribedTokens.value.clear()
})
</script>

<style scoped>
.optionchain-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px - 32px);
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: hidden;
  padding: 0 16px;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  margin-bottom: 12px;
  min-width: 0;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex-shrink: 1;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #212529;
  margin: 0;
}

.underlying-tabs {
  display: flex;
  gap: 2px;
  background: #f0f0f0;
  padding: 2px;
  border-radius: 4px;
}

.tab-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: transparent;
  border: none;
  color: #495057; /* Darker gray for better contrast (4.5:1 on #f0f0f0) */
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: #212529;
}

.tab-btn.active {
  background: white;
  color: #212529;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.expiry-select {
  padding: 6px 12px;
  font-size: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  background: white;
  cursor: pointer;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex-shrink: 1;
  flex-wrap: wrap;
}

.spot-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 4px;
}

.spot-label {
  font-size: 11px;
  color: #1976d2;
  text-transform: uppercase;
}

.spot-price {
  font-size: 15px;
  font-weight: 700;
  color: #1565c0;
}

.dte-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #f5f5f5;
  border-radius: 4px;
}

.dte-label {
  font-size: 11px;
  color: #495057; /* Darker gray for better contrast (4.5:1) */
}

.dte-value {
  font-size: 13px;
  font-weight: 600;
  color: #212529;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #495057; /* Darker gray for better contrast */
  cursor: pointer;
}

.toggle-label input {
  width: 14px;
  height: 14px;
  accent-color: #2196f3;
}

.live-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #495057; /* Darker gray for better contrast */
  cursor: pointer;
}

.live-toggle input {
  width: 14px;
  height: 14px;
  accent-color: #00b386;
}

.live-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.live-dot {
  width: 8px;
  height: 8px;
  background: #00b386;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.refresh-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: #2563eb; /* Darker blue for better contrast (4.5:1 with white) */
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.refresh-btn:hover {
  background: #1d4ed8;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.find-strike-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: #2563eb; /* Darker blue for better contrast (4.5:1 with white) */
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.find-strike-btn:hover {
  background: #1d4ed8;
}

.find-strike-btn svg {
  flex-shrink: 0;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 10px 16px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 12px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-item .label {
  font-size: 11px;
  color: #6c757d;
  text-transform: uppercase;
}

.summary-item .value {
  font-size: 14px;
  font-weight: 600;
}

.text-green { color: #00b386; }
.text-red { color: #dc2626; } /* Darker red for better contrast (4.5:1 on white) */
.text-purple { color: #9c27b0; }
.text-muted { color: #6b7280; } /* Darker gray for better contrast */

.summary-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-select {
  padding: 4px 8px;
  font-size: 11px;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  background: white;
}

/* Grid Interval Toggle */
.interval-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 4px 8px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.interval-label {
  font-size: 11px;
  color: #495057; /* Darker gray for better contrast */
  text-transform: uppercase;
  margin-right: 4px;
}

.interval-option {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  cursor: pointer;
  font-size: 11px;
  color: #495057;
}

.interval-option input[type="radio"] {
  cursor: pointer;
  margin: 0;
  width: 14px;
  height: 14px;
}

.interval-option span {
  font-weight: 500;
}

/* Error Alert */
.error-alert {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #fdeaea;
  border: 1px solid #e74c3c;
  border-radius: 4px;
  margin-bottom: 12px;
  color: #c62828;
  font-size: 13px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #c62828;
}

/* Loading State */
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #6c757d;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e0e0e0;
  border-top-color: #2196f3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Chain Table */
.chain-table-container {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.chain-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

/* Finding #1: Market closed banner */
.market-closed-banner {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  padding: 10px 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #92400e;
  font-weight: 500;
  text-align: center;
}

/* Finding #4: CALLS/PUTS labels */
.side-labels-row th {
  padding: 4px 10px !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 1px !important;
  border-bottom: none !important;
}

.calls-label {
  color: #c62828;
  text-align: center !important;
}

.puts-label {
  color: #2e7d32;
  text-align: center !important;
}

.chain-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
}

.chain-table th {
  padding: 8px 10px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e0e0e0;
}

.ce-col {
  background: #fff5f5;
  text-align: right;
}

.pe-col {
  background: #f0fff4;
  text-align: left;
}

.strike-col {
  background: #fafafa;
  text-align: center;
  font-weight: 600;
  border-left: 2px solid #e0e0e0;
  border-right: 2px solid #e0e0e0;
  min-width: 80px;
}

.chain-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
}

.chain-row:hover {
  background: #fafafa;
}

.chain-row:hover .ce-col { background: #ffebee; }
.chain-row:hover .pe-col { background: #e8f5e9; }

.atm-row {
  background: #fffde7 !important;
}
.atm-row .ce-col { background: #fff8e1 !important; }
.atm-row .pe-col { background: #fff8e1 !important; }
.atm-row .strike-col { background: #ffeb3b !important; }

.itm-ce .ce-col { background: #ffcdd2; }
.itm-pe .pe-col { background: #c8e6c9; }

.strike-value {
  font-size: 13px;
  font-weight: 600;
}

.atm-badge {
  display: inline-block;
  margin-left: 4px;
  padding: 1px 4px;
  font-size: 9px;
  font-weight: 600;
  background: #ffc107;
  color: #212529;
  border-radius: 2px;
}

.ltp-col {
  font-weight: 600;
}

.ltp-col.itm {
  color: #c62828;
}

.pe-col.ltp-col.itm {
  color: #2e7d32;
}

/* OI Bar */
.oi-col {
  min-width: 90px;
}

.oi-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.oi-cell.reverse {
  flex-direction: row-reverse;
}

.oi-bar {
  height: 6px;
  border-radius: 2px;
  max-width: 40px;
  min-width: 2px;
}

.oi-bar.ce { background: #e53935; }
.oi-bar.pe { background: #a5d6a7; }

/* Add Button */
.add-col {
  width: 32px;
  padding: 4px !important;
}

.add-btn {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-btn.ce {
  background: #ffcdd2;
  color: #c62828;
}

.add-btn.ce:hover,
.add-btn.ce.selected {
  background: #e74c3c;
  color: white;
}

.add-btn.pe {
  background: #c8e6c9;
  color: #2e7d32;
}

.add-btn.pe:hover,
.add-btn.pe.selected {
  background: #00b386;
  color: white;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #6c757d;
  font-size: 14px;
}

.empty-state .hint {
  font-size: 12px;
  color: #adb5bd;
  margin-top: 8px;
}

/* Selected Bar */
.selected-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-top: 12px;
}

.selected-items {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.selected-label {
  font-size: 12px;
  color: #6c757d;
}

.selected-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 3px;
}

.selected-chip.ce {
  background: #ffcdd2;
  color: #c62828;
}

.selected-chip.pe {
  background: #c8e6c9;
  color: #2e7d32;
}

.chip-remove {
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.selected-actions {
  display: flex;
  gap: 8px;
}

.btn-clear {
  padding: 6px 12px;
  font-size: 12px;
  background: transparent;
  border: none;
  color: #6c757d;
  cursor: pointer;
}

.btn-clear:hover {
  color: #212529;
}

.btn-add-strategy {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: #00b386;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.btn-add-strategy:hover {
  background: #009973;
}

.greek-col {
  min-width: 50px;
}

/* Highlight strike animation */
.chain-row.highlight-strike {
  animation: highlightStrike 2s ease-in-out;
}

@keyframes highlightStrike {
  0% {
    background-color: #fff3cd;
    box-shadow: 0 0 0 3px #ffc107;
  }
  50% {
    background-color: #fff3cd;
  }
  100% {
    background-color: transparent;
    box-shadow: none;
  }
}
</style>
