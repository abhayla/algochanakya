<template>
  <div class="option-chain-table">
    <!-- Header with spot price and ATM info -->
    <div class="chain-header" v-if="spotPrice">
      <div class="spot-info">
        <span class="label">Spot Price:</span>
        <span class="value">{{ spotPrice.toFixed(2) }}</span>
      </div>
      <div class="atm-info" v-if="atmStrike">
        <span class="label">ATM Strike:</span>
        <span class="value">{{ atmStrike }}</span>
      </div>
      <div class="cache-indicator" v-if="isCached">
        <span class="cache-badge">Cached</span>
        <span class="cache-time">{{ formatCacheTime(cachedAt) }}</span>
      </div>
    </div>

    <!-- Option Chain Table -->
    <div class="chain-table-wrapper">
      <table class="chain-table">
        <thead>
          <tr>
            <th colspan="5" class="section-header call-section">CALLS (CE)</th>
            <th class="strike-header">STRIKE</th>
            <th colspan="5" class="section-header put-section">PUTS (PE)</th>
          </tr>
          <tr class="column-headers">
            <!-- CE Headers -->
            <th @click="sortBy('oi', 'CE')" class="sortable">OI</th>
            <th @click="sortBy('volume', 'CE')" class="sortable">Vol</th>
            <th @click="sortBy('ltp', 'CE')" class="sortable">LTP</th>
            <th @click="sortBy('iv', 'CE')" class="sortable" v-if="showGreeks">IV</th>
            <th @click="sortBy('delta', 'CE')" class="sortable" v-if="showGreeks">Δ</th>

            <!-- Strike -->
            <th class="strike-column">Strike</th>

            <!-- PE Headers -->
            <th @click="sortBy('delta', 'PE')" class="sortable" v-if="showGreeks">Δ</th>
            <th @click="sortBy('iv', 'PE')" class="sortable" v-if="showGreeks">IV</th>
            <th @click="sortBy('ltp', 'PE')" class="sortable">LTP</th>
            <th @click="sortBy('volume', 'PE')" class="sortable">Vol</th>
            <th @click="sortBy('oi', 'PE')" class="sortable">OI</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in groupedByStrike"
            :key="row.strike"
            :class="getRowClass(row.strike)"
          >
            <!-- CE Data -->
            <td class="oi-cell ce-cell" :class="{ 'no-data': !row.CE }">
              {{ row.CE ? formatNumber(row.CE.oi) : '-' }}
            </td>
            <td class="volume-cell ce-cell" :class="{ 'no-data': !row.CE }">
              {{ row.CE ? formatNumber(row.CE.volume) : '-' }}
            </td>
            <td class="ltp-cell ce-cell" :class="{ 'no-data': !row.CE, 'clickable': row.CE }"
                @click="row.CE && selectOption(row.CE)">
              {{ row.CE ? row.CE.ltp.toFixed(2) : '-' }}
            </td>
            <td class="iv-cell ce-cell" v-if="showGreeks" :class="{ 'no-data': !row.CE }">
              {{ row.CE && row.CE.iv ? (row.CE.iv * 100).toFixed(1) + '%' : '-' }}
            </td>
            <td class="delta-cell ce-cell" v-if="showGreeks" :class="{ 'no-data': !row.CE }">
              {{ row.CE && row.CE.delta ? row.CE.delta.toFixed(3) : '-' }}
            </td>

            <!-- Strike -->
            <td class="strike-cell" :class="{ 'atm-strike': row.strike === atmStrike }">
              {{ row.strike }}
            </td>

            <!-- PE Data -->
            <td class="delta-cell pe-cell" v-if="showGreeks" :class="{ 'no-data': !row.PE }">
              {{ row.PE && row.PE.delta ? row.PE.delta.toFixed(3) : '-' }}
            </td>
            <td class="iv-cell pe-cell" v-if="showGreeks" :class="{ 'no-data': !row.PE }">
              {{ row.PE && row.PE.iv ? (row.PE.iv * 100).toFixed(1) + '%' : '-' }}
            </td>
            <td class="ltp-cell pe-cell" :class="{ 'no-data': !row.PE, 'clickable': row.PE }"
                @click="row.PE && selectOption(row.PE)">
              {{ row.PE ? row.PE.ltp.toFixed(2) : '-' }}
            </td>
            <td class="volume-cell pe-cell" :class="{ 'no-data': !row.PE }">
              {{ row.PE ? formatNumber(row.PE.volume) : '-' }}
            </td>
            <td class="oi-cell pe-cell" :class="{ 'no-data': !row.PE }">
              {{ row.PE ? formatNumber(row.PE.oi) : '-' }}
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Empty State -->
      <div v-if="!groupedByStrike || groupedByStrike.length === 0" class="empty-state">
        <p>No option chain data available</p>
        <p class="hint">Select an underlying and expiry to load option chain</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Loading option chain...</p>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'OptionChainTable',
  props: {
    groupedByStrike: {
      type: Array,
      default: () => []
    },
    spotPrice: {
      type: Number,
      default: null
    },
    atmStrike: {
      type: Number,
      default: null
    },
    showGreeks: {
      type: Boolean,
      default: true
    },
    loading: {
      type: Boolean,
      default: false
    },
    isCached: {
      type: Boolean,
      default: false
    },
    cachedAt: {
      type: String,
      default: null
    }
  },
  emits: ['option-selected', 'sort'],
  setup(props, { emit }) {
    const getRowClass = (strike) => {
      if (!props.spotPrice) return ''

      const classes = []

      // ATM row
      if (strike === props.atmStrike) {
        classes.push('atm-row')
      }

      // ITM/OTM highlighting
      if (strike < props.spotPrice) {
        classes.push('ce-itm') // CE is ITM
      } else if (strike > props.spotPrice) {
        classes.push('pe-itm') // PE is ITM
      }

      return classes.join(' ')
    }

    const formatNumber = (num) => {
      if (!num) return '0'
      if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M'
      if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
      return num.toString()
    }

    const formatCacheTime = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    }

    const selectOption = (option) => {
      emit('option-selected', option)
    }

    const sortBy = (field, optionType) => {
      emit('sort', { field, optionType })
    }

    return {
      getRowClass,
      formatNumber,
      formatCacheTime,
      selectOption,
      sortBy
    }
  }
}
</script>

<style scoped>
.option-chain-table {
  width: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chain-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 8px 8px 0 0;
}

.spot-info, .atm-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.value {
  font-size: 15px;
  color: #111827;
  font-weight: 600;
}

.cache-indicator {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.cache-badge {
  background: #fef3c7;
  color: #92400e;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.cache-time {
  font-size: 12px;
  color: #6b7280;
}

.chain-table-wrapper {
  position: relative;
  overflow-x: auto;
  max-height: 600px;
  overflow-y: auto;
}

.chain-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.chain-table thead {
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}

.section-header {
  padding: 12px 8px;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e5e7eb;
}

.call-section {
  background: #dbeafe;
  color: #1e40af;
  text-align: right;
}

.put-section {
  background: #fee2e2;
  color: #991b1b;
  text-align: left;
}

.strike-header {
  background: #f3f4f6;
  color: #374151;
  font-weight: 700;
  border-bottom: 2px solid #e5e7eb;
}

.column-headers th {
  padding: 8px 6px;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  background: #f3f4f6;
}

.chain-table tbody tr {
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.15s;
}

.chain-table tbody tr:hover {
  background: #fafafa;
}

.chain-table td {
  padding: 10px 8px;
  text-align: center;
}

.strike-cell {
  font-weight: 700;
  font-size: 14px;
  background: #f9fafb;
  color: #111827;
}

.atm-strike {
  background: #fef3c7;
  color: #92400e;
}

.atm-row {
  background: #fffbeb;
}

.ce-cell {
  background: #eff6ff;
}

.pe-cell {
  background: #fef2f2;
}

.ce-itm .ce-cell {
  background: #dbeafe;
  font-weight: 500;
}

.pe-itm .pe-cell {
  background: #fecaca;
  font-weight: 500;
}

.no-data {
  color: #d1d5db;
  background: #fafafa !important;
}

.clickable {
  cursor: pointer;
  font-weight: 600;
}

.clickable:hover {
  background: #3b82f6 !important;
  color: white;
}

.oi-cell, .volume-cell {
  font-size: 12px;
}

.ltp-cell {
  font-size: 14px;
  font-weight: 600;
}

.iv-cell, .delta-cell {
  font-size: 12px;
  font-family: 'Courier New', monospace;
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: #9ca3af;
}

.empty-state p {
  margin: 8px 0;
}

.hint {
  font-size: 13px;
  color: #d1d5db;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 20;
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

.loading-overlay p {
  margin-top: 16px;
  color: #6b7280;
  font-size: 14px;
}
</style>
