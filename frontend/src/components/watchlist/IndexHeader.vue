<template>
  <div class="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
    <div class="flex items-center">
      <!-- NIFTY 50 -->
      <div class="flex items-center mr-10">
        <span class="text-gray-600 font-medium text-sm mr-3">NIFTY 50</span>
        <span :class="niftyChangeClass" class="font-semibold text-base mr-2">
          {{ formatPrice(niftyPrice) }}
        </span>
        <span :class="niftyChangeClass" class="text-sm mr-1">
          {{ formatChange(niftyChange) }}
        </span>
        <span :class="niftyChangeClass" class="text-sm">
          ({{ formatPercent(niftyChangePercent) }})
        </span>
      </div>

      <!-- NIFTY BANK -->
      <div class="flex items-center mr-10">
        <span class="text-gray-600 font-medium text-sm mr-3">NIFTY BANK</span>
        <span :class="bankNiftyChangeClass" class="font-semibold text-base mr-2">
          {{ formatPrice(bankNiftyPrice) }}
        </span>
        <span :class="bankNiftyChangeClass" class="text-sm mr-1">
          {{ formatChange(bankNiftyChange) }}
        </span>
        <span :class="bankNiftyChangeClass" class="text-sm">
          ({{ formatPercent(bankNiftyChangePercent) }})
        </span>
      </div>

      <!-- FIN NIFTY -->
      <div class="flex items-center mr-10">
        <span class="text-gray-600 font-medium text-sm mr-3">FIN NIFTY</span>
        <span :class="finNiftyChangeClass" class="font-semibold text-base mr-2">
          {{ formatPrice(finNiftyPrice) }}
        </span>
        <span :class="finNiftyChangeClass" class="text-sm mr-1">
          {{ formatChange(finNiftyChange) }}
        </span>
        <span :class="finNiftyChangeClass" class="text-sm">
          ({{ formatPercent(finNiftyChangePercent) }})
        </span>
      </div>

      <!-- SENSEX -->
      <div class="flex items-center">
        <span class="text-gray-600 font-medium text-sm mr-3">SENSEX</span>
        <span :class="sensexChangeClass" class="font-semibold text-base mr-2">
          {{ formatPrice(sensexPrice) }}
        </span>
        <span :class="sensexChangeClass" class="text-sm mr-1">
          {{ formatChange(sensexChange) }}
        </span>
        <span :class="sensexChangeClass" class="text-sm">
          ({{ formatPercent(sensexChangePercent) }})
        </span>
      </div>
    </div>

    <div class="flex items-center">
      <span class="text-xs text-gray-400 mr-2">{{ isConnected ? 'Live' : 'Disconnected' }}</span>
      <span
        class="w-2 h-2 rounded-full"
        :class="isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'"
      ></span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useWatchlistStore } from '../../stores/watchlist'
import { fetchIndexPrices } from '@/services/priceService'
import { getIndexToken } from '@/constants/trading'

const store = useWatchlistStore()

// Connection status
const isConnected = computed(() => store.isConnected)

// NIFTY 50
const niftyTick = computed(() => store.ticks[getIndexToken('NIFTY')] || {})
const niftyPrice = computed(() => niftyTick.value.ltp || 0)
const niftyChange = computed(() => niftyTick.value.change || 0)
const niftyChangePercent = computed(() => {
  if (niftyTick.value.ltp && niftyTick.value.close) {
    return ((niftyTick.value.ltp - niftyTick.value.close) / niftyTick.value.close) * 100
  }
  return niftyTick.value.change_percent || 0
})
const niftyChangeClass = computed(() =>
  niftyChange.value >= 0 ? 'text-green-600' : 'text-red-600'
)

// NIFTY BANK
const bankNiftyTick = computed(() => store.ticks[getIndexToken('BANKNIFTY')] || {})
const bankNiftyPrice = computed(() => bankNiftyTick.value.ltp || 0)
const bankNiftyChange = computed(() => bankNiftyTick.value.change || 0)
const bankNiftyChangePercent = computed(() => {
  if (bankNiftyTick.value.ltp && bankNiftyTick.value.close) {
    return ((bankNiftyTick.value.ltp - bankNiftyTick.value.close) / bankNiftyTick.value.close) * 100
  }
  return bankNiftyTick.value.change_percent || 0
})
const bankNiftyChangeClass = computed(() =>
  bankNiftyChange.value >= 0 ? 'text-green-600' : 'text-red-600'
)

// FIN NIFTY
const finNiftyTick = computed(() => store.ticks[getIndexToken('FINNIFTY')] || {})
const finNiftyPrice = computed(() => finNiftyTick.value.ltp || 0)
const finNiftyChange = computed(() => finNiftyTick.value.change || 0)
const finNiftyChangePercent = computed(() => {
  if (finNiftyTick.value.ltp && finNiftyTick.value.close) {
    return ((finNiftyTick.value.ltp - finNiftyTick.value.close) / finNiftyTick.value.close) * 100
  }
  return finNiftyTick.value.change_percent || 0
})
const finNiftyChangeClass = computed(() =>
  finNiftyChange.value >= 0 ? 'text-green-600' : 'text-red-600'
)

// SENSEX
const sensexTick = computed(() => store.ticks[getIndexToken('SENSEX')] || {})
const sensexPrice = computed(() => sensexTick.value.ltp || 0)
const sensexChange = computed(() => sensexTick.value.change || 0)
const sensexChangePercent = computed(() => {
  if (sensexTick.value.ltp && sensexTick.value.close) {
    return ((sensexTick.value.ltp - sensexTick.value.close) / sensexTick.value.close) * 100
  }
  return sensexTick.value.change_percent || 0
})
const sensexChangeClass = computed(() =>
  sensexChange.value >= 0 ? 'text-green-600' : 'text-red-600'
)

// Formatters
const formatPrice = (price) => {
  if (!price) return '--'
  return price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatChange = (change) => {
  if (change === null || change === undefined) return '--'
  const sign = change >= 0 ? '+' : ''
  return sign + change.toFixed(2)
}

const formatPercent = (percent) => {
  if (percent === null || percent === undefined) return '--'
  const sign = percent >= 0 ? '+' : ''
  return sign + percent.toFixed(2) + '%'
}

// Fallback: fetch index prices via API if WebSocket data not available after 2s
onMounted(() => {
  setTimeout(() => {
    if (!niftyTick.value?.ltp) {
      fetchIndexPrices((token, tick) => store.updateTick(token, tick))
    }
  }, 2000)
})
</script>
