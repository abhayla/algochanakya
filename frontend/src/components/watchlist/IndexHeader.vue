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
      <div class="flex items-center">
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
import { fetchIndexPrices } from '@/composables/usePriceFallback'

const store = useWatchlistStore()

// Connection status
const isConnected = computed(() => store.isConnected)

// NIFTY 50 (token: 256265)
const niftyTick = computed(() => store.ticks[256265] || {})
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

// NIFTY BANK (token: 260105)
const bankNiftyTick = computed(() => store.ticks[260105] || {})
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
