<template>
  <KiteLayout>
    <div class="optionchain-page">

      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">Option Chain</h1>

          <!-- Underlying Tabs -->
          <div class="underlying-tabs">
            <button
              v-for="ul in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']"
              :key="ul"
              :class="['tab-btn', { active: store.underlying === ul }]"
              @click="handleUnderlyingChange(ul)"
            >
              {{ ul }}
            </button>
          </div>

          <!-- Expiry Select -->
          <select v-model="store.expiry" @change="handleExpiryChange" class="expiry-select">
            <option v-for="exp in store.expiries" :key="exp" :value="exp">{{ formatExpiry(exp) }}</option>
          </select>
        </div>

        <div class="header-right">
          <!-- Spot Price Box -->
          <div class="spot-box">
            <span class="spot-label">Spot</span>
            <span class="spot-price">{{ formatNumber(store.spotPrice) }}</span>
          </div>

          <!-- DTE -->
          <div class="dte-box">
            <span class="dte-label">DTE</span>
            <span class="dte-value">{{ store.daysToExpiry }}</span>
          </div>

          <!-- Greeks Toggle -->
          <label class="toggle-label">
            <input type="checkbox" v-model="store.showGreeks" />
            <span>Greeks</span>
          </label>

          <!-- Refresh -->
          <button @click="store.fetchOptionChain()" class="refresh-btn" :disabled="store.isLoading">
            {{ store.isLoading ? 'Loading...' : 'Refresh' }}
          </button>
        </div>
      </div>

      <!-- Summary Bar -->
      <div class="summary-bar">
        <div class="summary-item">
          <span class="label">PCR</span>
          <span :class="['value', store.summary.pcr > 1 ? 'text-green' : 'text-red']">
            {{ store.summary.pcr }}
          </span>
        </div>
        <div class="summary-item">
          <span class="label">Max Pain</span>
          <span class="value text-purple">{{ formatNumber(store.summary.max_pain) }}</span>
        </div>
        <div class="summary-item">
          <span class="label">CE OI</span>
          <span class="value text-red">{{ formatOI(store.summary.total_ce_oi) }}</span>
        </div>
        <div class="summary-item">
          <span class="label">PE OI</span>
          <span class="value text-green">{{ formatOI(store.summary.total_pe_oi) }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Lot Size</span>
          <span class="value">{{ store.lotSize }}</span>
        </div>

        <div class="summary-right">
          <select v-model="store.strikesRange" class="range-select">
            <option :value="10">10 Strikes</option>
            <option :value="15">15 Strikes</option>
            <option :value="20">20 Strikes</option>
            <option :value="30">30 Strikes</option>
            <option :value="50">All Strikes</option>
          </select>
        </div>
      </div>

      <!-- Error Alert -->
      <div v-if="store.error" class="error-alert">
        <span>{{ store.error }}</span>
        <button @click="store.error = null" class="close-btn">&times;</button>
      </div>

      <!-- Loading State -->
      <div v-if="store.isLoading && store.chain.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>Loading option chain...</p>
      </div>

      <!-- Option Chain Table -->
      <div v-else class="chain-table-container">
        <table class="chain-table">
          <thead>
            <tr>
              <!-- CE Side -->
              <th class="ce-col add-col"></th>
              <th class="ce-col">OI</th>
              <th class="ce-col">Chg</th>
              <th class="ce-col">Vol</th>
              <th class="ce-col">IV</th>
              <th v-if="store.showGreeks" class="ce-col greek-col">Delta</th>
              <th class="ce-col">LTP</th>
              <th class="ce-col">Chg%</th>

              <!-- Strike -->
              <th class="strike-col">STRIKE</th>

              <!-- PE Side -->
              <th class="pe-col">Chg%</th>
              <th class="pe-col">LTP</th>
              <th v-if="store.showGreeks" class="pe-col greek-col">Delta</th>
              <th class="pe-col">IV</th>
              <th class="pe-col">Vol</th>
              <th class="pe-col">Chg</th>
              <th class="pe-col">OI</th>
              <th class="pe-col add-col"></th>
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
            >
              <!-- CE Add -->
              <td class="ce-col add-col">
                <button
                  v-if="row.ce"
                  @click="toggleStrike(row.strike, 'CE')"
                  :class="['add-btn', 'ce', { selected: store.isStrikeSelected(row.strike, 'CE') }]"
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
              <td class="ce-col" :class="getChangeClass(row.ce?.oi_change)">{{ formatOIChange(row.ce?.oi_change) }}</td>
              <td class="ce-col text-muted">{{ formatOI(row.ce?.volume) }}</td>
              <td class="ce-col">{{ row.ce?.iv || '-' }}</td>
              <td v-if="store.showGreeks" class="ce-col text-muted">{{ row.ce?.delta?.toFixed(2) || '-' }}</td>
              <td class="ce-col ltp-col" :class="{ 'itm': row.is_itm_ce }">{{ formatPrice(row.ce?.ltp) }}</td>
              <td class="ce-col" :class="getChangeClass(row.ce?.change)">{{ formatPct(row.ce?.change_pct) }}</td>

              <!-- Strike -->
              <td class="strike-col">
                <span class="strike-value">{{ row.strike }}</span>
                <span v-if="row.is_atm" class="atm-badge">ATM</span>
              </td>

              <!-- PE Data -->
              <td class="pe-col" :class="getChangeClass(row.pe?.change)">{{ formatPct(row.pe?.change_pct) }}</td>
              <td class="pe-col ltp-col" :class="{ 'itm': row.is_itm_pe }">{{ formatPrice(row.pe?.ltp) }}</td>
              <td v-if="store.showGreeks" class="pe-col text-muted">{{ row.pe?.delta?.toFixed(2) || '-' }}</td>
              <td class="pe-col">{{ row.pe?.iv || '-' }}</td>
              <td class="pe-col text-muted">{{ formatOI(row.pe?.volume) }}</td>
              <td class="pe-col" :class="getChangeClass(row.pe?.oi_change)">{{ formatOIChange(row.pe?.oi_change) }}</td>
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
                >
                  {{ store.isStrikeSelected(row.strike, 'PE') ? '&#10003;' : '+' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Empty State -->
        <div v-if="store.chain.length === 0 && !store.isLoading" class="empty-state">
          <p>No option chain data</p>
          <p class="hint">Select an expiry to view option chain</p>
        </div>
      </div>

      <!-- Selected Bar -->
      <div v-if="store.selectedStrikes.length > 0" class="selected-bar">
        <div class="selected-items">
          <span class="selected-label">Selected:</span>
          <span
            v-for="s in store.selectedStrikes"
            :key="s.key"
            :class="['selected-chip', s.type.toLowerCase()]"
          >
            {{ s.type }} {{ s.strike }} @ {{ s.ltp?.toFixed(2) }}
            <button @click="store.toggleStrikeSelection(s.strike, s.type)" class="chip-remove">&times;</button>
          </span>
        </div>
        <div class="selected-actions">
          <button @click="store.clearSelection()" class="btn-clear">Clear</button>
          <button @click="goToStrategy()" class="btn-add-strategy">Add to Strategy</button>
        </div>
      </div>

    </div>
  </KiteLayout>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import { useOptionChainStore } from '@/stores/optionchain'
import { useStrategyStore } from '@/stores/strategy'

const store = useOptionChainStore()
const strategyStore = useStrategyStore()
const router = useRouter()

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

// Initialize
onMounted(async () => {
  await store.fetchExpiries()
  if (store.expiry) {
    await store.fetchOptionChain()
  }
})
</script>

<style scoped>
.optionchain-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px - 32px);
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
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
  color: #6c757d;
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
  color: #6c757d;
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
  color: #6c757d;
  cursor: pointer;
}

.toggle-label input {
  width: 14px;
  height: 14px;
  accent-color: #2196f3;
}

.refresh-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.refresh-btn:hover {
  background: #1976d2;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
.text-red { color: #e74c3c; }
.text-purple { color: #9c27b0; }
.text-muted { color: #adb5bd; }

.summary-right {
  margin-left: auto;
}

.range-select {
  padding: 4px 8px;
  font-size: 11px;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  background: white;
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

.oi-bar.ce { background: #ef9a9a; }
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
</style>
