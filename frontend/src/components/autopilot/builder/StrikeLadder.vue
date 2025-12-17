<template>
  <div class="strike-ladder">
    <div class="ladder-header">
      <div class="header-top">
        <h3 class="ladder-title">
          Strike Ladder - {{ underlying }} {{ formattedExpiry }}
        </h3>
        <div class="spot-price-display">
          <span class="spot-label">Spot:</span>
          <span v-if="loadingSpotPrice" class="spot-skeleton">
            <span class="skeleton-box"></span>
          </span>
          <span v-else class="spot-value">₹{{ formatPrice(spotPrice) }}</span>
        </div>
      </div>
      <div class="ladder-controls">
        <label class="delta-filter">
          <span>Delta Range:</span>
          <select v-model="deltaFilter" @change="applyFilters" class="filter-select">
            <option value="all">All Strikes</option>
            <option value="0.10-0.40">0.10 - 0.40 Δ</option>
            <option value="0.20-0.50">0.20 - 0.50 Δ</option>
            <option value="0.15-0.35">0.15 - 0.35 Δ</option>
          </select>
        </label>
        <label class="greeks-toggle">
          <input type="checkbox" v-model="showGreeks" />
          <span>Show Greeks</span>
        </label>
        <button @click="refreshData" class="refresh-btn" :disabled="loading">
          <span v-if="!loading">↻ Refresh</span>
          <span v-else>Loading...</span>
        </button>
      </div>
    </div>

    <div v-if="loading && !strikes.length" class="loading-state">
      <div class="spinner-large"></div>
      <p>Loading option chain...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="refreshData" class="retry-btn">Retry</button>
    </div>

    <div v-else-if="filteredStrikes.length" class="ladder-table-container">
      <table class="ladder-table" :class="{ 'show-greeks': showGreeks }">
        <thead>
          <tr>
            <th class="text-right">CE Δ</th>
            <th v-if="showGreeks" class="text-right greeks-col">CE Θ</th>
            <th v-if="showGreeks" class="text-right greeks-col">CE IV</th>
            <th class="text-right">CE LTP</th>
            <th class="text-center strike-col">Strike</th>
            <th class="text-left">PE LTP</th>
            <th v-if="showGreeks" class="text-left greeks-col">PE IV</th>
            <th v-if="showGreeks" class="text-left greeks-col">PE Θ</th>
            <th class="text-left">PE Δ</th>
            <th class="text-center">Select</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="strike in filteredStrikes"
            :key="strike.strike"
            class="strike-row"
            :class="{
              'atm-row': strike.isATM,
              'itm-ce': strike.ce && strike.ce.isITM,
              'itm-pe': strike.pe && strike.pe.isITM
            }"
          >
            <!-- CE Delta -->
            <td class="text-right delta-cell">
              <span v-if="strike.ce" class="delta-value">
                {{ formatDelta(strike.ce.delta) }}
              </span>
            </td>

            <!-- CE Theta (Greeks) -->
            <td v-if="showGreeks" class="text-right greeks-cell">
              <span v-if="strike.ce" class="greeks-value" :class="{ 'negative': strike.ce.theta < 0 }">
                {{ formatGreek(strike.ce.theta) }}
              </span>
            </td>

            <!-- CE IV (Greeks) -->
            <td v-if="showGreeks" class="text-right greeks-cell">
              <span v-if="strike.ce" class="greeks-value">
                {{ formatPercent(strike.ce.iv) }}
              </span>
            </td>

            <!-- CE LTP -->
            <td class="text-right ltp-cell">
              <span v-if="strike.ce" class="ltp-value">
                ₹{{ formatPrice(strike.ce.ltp) }}
              </span>
            </td>

            <!-- Strike -->
            <td class="text-center strike-cell">
              <span class="strike-value">
                {{ strike.strike }}
                <span v-if="strike.isATM" class="atm-badge">ATM</span>
              </span>
            </td>

            <!-- PE LTP -->
            <td class="text-left ltp-cell">
              <span v-if="strike.pe" class="ltp-value">
                ₹{{ formatPrice(strike.pe.ltp) }}
              </span>
            </td>

            <!-- PE IV (Greeks) -->
            <td v-if="showGreeks" class="text-left greeks-cell">
              <span v-if="strike.pe" class="greeks-value">
                {{ formatPercent(strike.pe.iv) }}
              </span>
            </td>

            <!-- PE Theta (Greeks) -->
            <td v-if="showGreeks" class="text-left greeks-cell">
              <span v-if="strike.pe" class="greeks-value" :class="{ 'negative': strike.pe.theta < 0 }">
                {{ formatGreek(strike.pe.theta) }}
              </span>
            </td>

            <!-- PE Delta -->
            <td class="text-left delta-cell">
              <span v-if="strike.pe" class="delta-value">
                {{ formatDelta(strike.pe.delta) }}
              </span>
            </td>

            <!-- Select Buttons -->
            <td class="text-center select-cell">
              <div class="select-buttons">
                <button
                  v-if="strike.ce"
                  @click="selectStrike(strike.strike, 'CE', strike.ce)"
                  class="select-btn select-ce"
                  :disabled="!strike.ce.ltp"
                >
                  CE
                </button>
                <button
                  v-if="strike.pe"
                  @click="selectStrike(strike.strike, 'PE', strike.pe)"
                  class="select-btn select-pe"
                  :disabled="!strike.pe.ltp"
                >
                  PE
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Expected Move Indicator -->
      <div v-if="expectedMove" class="expected-move-info">
        <span class="move-label">Expected Move (1σ):</span>
        <span class="move-range">{{ expectedMove.lower }} - {{ expectedMove.upper }}</span>
        <span class="move-percent">(±{{ expectedMove.percent }}%)</span>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>No strikes found for the selected criteria</p>
    </div>
  </div>
</template>

<script>
import api from '@/services/api'

export default {
  name: 'StrikeLadder',
  props: {
    underlying: {
      type: String,
      required: true
    },
    expiry: {
      type: String,
      required: true
    },
    spotPrice: {
      type: Number,
      default: null
    },
    loadingSpotPrice: {
      type: Boolean,
      default: false
    },
    loadingOptionChain: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      strikes: [],
      filteredStrikes: [],
      atmStrike: null,
      expectedMove: null,
      deltaFilter: 'all',
      showGreeks: false,
      loading: false,
      error: null
    }
  },
  computed: {
    formattedExpiry() {
      if (!this.expiry) return ''
      try {
        const date = new Date(this.expiry)
        return date.toLocaleDateString('en-IN', {
          day: '2-digit',
          month: 'short',
          year: 'numeric'
        })
      } catch {
        return this.expiry
      }
    },
    strikeStep() {
      const steps = {
        'NIFTY': 50,
        'BANKNIFTY': 100,
        'FINNIFTY': 50,
        'SENSEX': 100
      }
      return steps[this.underlying?.toUpperCase()] || 50
    }
  },
  watch: {
    underlying() {
      this.fetchOptionChain()
    },
    expiry() {
      this.fetchOptionChain()
    },
    spotPrice() {
      this.calculateATM()
    }
  },
  methods: {
    async fetchOptionChain() {
      if (!this.underlying || !this.expiry) return

      this.loading = true
      this.error = null

      try {
        // Fetch real option chain data from API
        const response = await api.get(`/api/v1/autopilot/option-chain/${this.underlying}/${this.expiry}`)

        // Process the API response
        this.strikes = this.processOptionChain(response.data)
        this.calculateATM()
        this.calculateExpectedMove()
        this.applyFilters()
      } catch (error) {
        console.error('Error fetching option chain:', error)
        this.error = 'Failed to load option chain. Please try again.'
        this.strikes = []
        this.filteredStrikes = []
      } finally {
        this.loading = false
      }
    },
    processOptionChain(apiResponse) {
      // Transform API response to component format
      if (!apiResponse || !apiResponse.options) {
        console.warn('Invalid API response format')
        return []
      }

      const strikes = []
      const strikeMap = {}

      // Group options by strike
      apiResponse.options.forEach(option => {
        const strike = option.strike
        if (!strikeMap[strike]) {
          strikeMap[strike] = {
            strike: parseInt(strike),
            ce: null,
            pe: null,
            isATM: false
          }
        }

        const optionData = {
          ltp: parseFloat(option.ltp || 0),
          delta: parseFloat(option.delta || 0),
          gamma: parseFloat(option.gamma || 0),
          theta: parseFloat(option.theta || 0),
          vega: parseFloat(option.vega || 0),
          iv: parseFloat(option.iv || 0),
          oi: parseInt(option.oi || 0),
          volume: parseInt(option.volume || 0),
          isITM: false // Will calculate below
        }

        if (option.option_type === 'CE') {
          strikeMap[strike].ce = optionData
          if (this.spotPrice) {
            strikeMap[strike].ce.isITM = strike < this.spotPrice
          }
        } else if (option.option_type === 'PE') {
          strikeMap[strike].pe = optionData
          if (this.spotPrice) {
            strikeMap[strike].pe.isITM = strike > this.spotPrice
          }
        }
      })

      // Convert to array
      for (const strike in strikeMap) {
        strikes.push(strikeMap[strike])
      }

      // Sort by strike
      strikes.sort((a, b) => a.strike - b.strike)

      return strikes
    },
    calculateATM() {
      if (!this.spotPrice || !this.strikes.length) return

      const atm = Math.round(this.spotPrice / this.strikeStep) * this.strikeStep
      this.atmStrike = atm

      // Mark ATM strike
      this.strikes = this.strikes.map(s => ({
        ...s,
        isATM: s.strike === atm
      }))
    },
    calculateExpectedMove() {
      if (!this.spotPrice) return

      // 1 SD move approximation (±2% for short term)
      const movePercent = 2.0
      const movePoints = this.spotPrice * (movePercent / 100)

      this.expectedMove = {
        lower: Math.round((this.spotPrice - movePoints) / this.strikeStep) * this.strikeStep,
        upper: Math.round((this.spotPrice + movePoints) / this.strikeStep) * this.strikeStep,
        percent: movePercent.toFixed(1)
      }
    },
    applyFilters() {
      let filtered = [...this.strikes]

      if (this.deltaFilter !== 'all') {
        const [minDelta, maxDelta] = this.deltaFilter.split('-').map(parseFloat)

        filtered = filtered.filter(strike => {
          const ceDelta = strike.ce?.delta || 0
          const peDelta = Math.abs(strike.pe?.delta || 0)

          return (
            (ceDelta >= minDelta && ceDelta <= maxDelta) ||
            (peDelta >= minDelta && peDelta <= maxDelta)
          )
        })
      }

      // Sort by strike (ascending)
      filtered.sort((a, b) => a.strike - b.strike)

      this.filteredStrikes = filtered
    },
    refreshData() {
      this.fetchOptionChain()
    },
    selectStrike(strike, optionType, data) {
      this.$emit('strike-selected', {
        strike,
        optionType,
        ltp: data.ltp,
        delta: data.delta,
        gamma: data.gamma,
        theta: data.theta,
        iv: data.iv
      })
    },
    formatDelta(delta) {
      if (!delta) return '-'
      return delta.toFixed(2)
    },
    formatPrice(price) {
      if (!price) return '-'
      return price.toFixed(2)
    },
    formatGreek(value) {
      if (!value && value !== 0) return '-'
      return value.toFixed(2)
    },
    formatPercent(value) {
      if (!value && value !== 0) return '-'
      return value.toFixed(1) + '%'
    }
  },
  mounted() {
    this.fetchOptionChain()
  }
}
</script>

<style scoped>
.strike-ladder {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.ladder-header {
  padding: 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.ladder-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.spot-price-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.spot-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.spot-value {
  font-size: 16px;
  font-weight: 700;
  color: #059669;
}

.spot-skeleton {
  display: inline-block;
}

.skeleton-box {
  display: inline-block;
  width: 80px;
  height: 20px;
  background: linear-gradient(
    90deg,
    #e5e7eb 0%,
    #f3f4f6 50%,
    #e5e7eb 100%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.ladder-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.greeks-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
  user-select: none;
}

.greeks-toggle input[type="checkbox"] {
  cursor: pointer;
}

.delta-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
}

.filter-select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  background: white;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: #3b82f6;
}

.refresh-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  background: white;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state,
.error-state,
.empty-state {
  padding: 48px 24px;
  text-align: center;
  color: #6b7280;
}

.spinner-large {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  color: #dc2626;
  margin-bottom: 12px;
}

.retry-btn {
  padding: 8px 16px;
  border: 1px solid #dc2626;
  border-radius: 4px;
  background: #fef2f2;
  color: #dc2626;
  font-weight: 500;
  cursor: pointer;
}

.retry-btn:hover {
  background: #fee2e2;
}

.ladder-table-container {
  overflow-x: auto;
}

.ladder-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ladder-table thead {
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

.ladder-table th {
  padding: 12px 8px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.05em;
}

.ladder-table tbody tr {
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.15s;
}

.ladder-table tbody tr:hover {
  background: #f9fafb;
}

.ladder-table tbody tr.atm-row {
  background: #dbeafe;
  font-weight: 600;
}

.ladder-table tbody tr.atm-row:hover {
  background: #bfdbfe;
}

.ladder-table tbody tr.itm-ce .ltp-cell:first-of-type {
  background: #dcfce7;
}

.ladder-table tbody tr.itm-pe .ltp-cell:last-of-type {
  background: #fee2e2;
}

.ladder-table td {
  padding: 10px 8px;
}

.text-right {
  text-align: right;
}

.text-left {
  text-align: left;
}

.text-center {
  text-align: center;
}

.strike-col {
  min-width: 100px;
}

.delta-cell {
  min-width: 60px;
  color: #6b7280;
  font-weight: 500;
}

.ltp-cell {
  min-width: 80px;
  color: #111827;
  font-weight: 500;
}

.strike-cell {
  font-weight: 600;
  color: #111827;
  font-size: 14px;
}

.atm-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 2px 6px;
  background: #3b82f6;
  color: white;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}

.greeks-col {
  min-width: 60px;
  font-size: 12px;
  color: #9ca3af;
}

.greeks-cell {
  min-width: 60px;
  color: #6b7280;
  font-size: 13px;
}

.greeks-value {
  font-family: 'Courier New', monospace;
}

.greeks-value.negative {
  color: #dc2626;
}

.select-cell {
  min-width: 120px;
}

.select-buttons {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.select-btn {
  padding: 4px 12px;
  border: 1px solid;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 40px;
}

.select-ce {
  border-color: #10b981;
  color: #10b981;
  background: white;
}

.select-ce:hover:not(:disabled) {
  background: #10b981;
  color: white;
}

.select-pe {
  border-color: #ef4444;
  color: #ef4444;
  background: white;
}

.select-pe:hover:not(:disabled) {
  background: #ef4444;
  color: white;
}

.select-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.expected-move-info {
  padding: 12px 16px;
  background: #f0fdf4;
  border-top: 1px solid #bbf7d0;
  font-size: 13px;
  color: #166534;
  display: flex;
  align-items: center;
  gap: 8px;
}

.move-label {
  font-weight: 600;
}

.move-range {
  font-weight: 600;
  color: #15803d;
}

.move-percent {
  color: #16a34a;
}
</style>
