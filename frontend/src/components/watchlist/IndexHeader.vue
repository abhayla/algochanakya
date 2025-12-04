<template>
  <div class="flex items-center gap-8 px-6 py-3 bg-white border-b border-gray-200 shadow-sm">
    <!-- NIFTY 50 -->
    <div class="flex items-center gap-3">
      <span class="text-sm font-medium text-gray-700">NIFTY 50</span>
      <div class="flex items-center gap-2">
        <span class="text-base font-semibold" :class="niftyPriceClass">
          {{ formatPrice(nifty50.ltp) }}
        </span>
        <span class="text-xs font-medium" :class="niftyChangeClass">
          {{ formatChange(nifty50.change) }} ({{ formatPercent(nifty50.change_percent) }}%)
        </span>
      </div>
    </div>

    <!-- NIFTY BANK -->
    <div class="flex items-center gap-3">
      <span class="text-sm font-medium text-gray-700">NIFTY BANK</span>
      <div class="flex items-center gap-2">
        <span class="text-base font-semibold" :class="bankNiftyPriceClass">
          {{ formatPrice(niftyBank.ltp) }}
        </span>
        <span class="text-xs font-medium" :class="bankNiftyChangeClass">
          {{ formatChange(niftyBank.change) }} ({{ formatPercent(niftyBank.change_percent) }}%)
        </span>
      </div>
    </div>

    <!-- Connection Status -->
    <div class="ml-auto flex items-center gap-2">
      <div
        class="w-2 h-2 rounded-full"
        :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
      ></div>
      <span class="text-xs text-gray-600">
        {{ isConnected ? 'Live' : 'Disconnected' }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useWatchlistStore } from '../../stores/watchlist'

const watchlistStore = useWatchlistStore()

// Computed properties
const nifty50 = computed(() => watchlistStore.indexTicks.nifty50)
const niftyBank = computed(() => watchlistStore.indexTicks.niftyBank)
const isConnected = computed(() => watchlistStore.isConnected)

const niftyPriceClass = computed(() => {
  if (!nifty50.value.ltp) return 'text-gray-800'
  const change = nifty50.value.change_percent
  return change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-800'
})

const niftyChangeClass = computed(() => {
  const change = nifty50.value.change_percent
  return change > 0
    ? 'text-green-600 bg-green-50 px-2 py-0.5 rounded'
    : change < 0
    ? 'text-red-600 bg-red-50 px-2 py-0.5 rounded'
    : 'text-gray-600'
})

const bankNiftyPriceClass = computed(() => {
  if (!niftyBank.value.ltp) return 'text-gray-800'
  const change = niftyBank.value.change_percent
  return change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-800'
})

const bankNiftyChangeClass = computed(() => {
  const change = niftyBank.value.change_percent
  return change > 0
    ? 'text-green-600 bg-green-50 px-2 py-0.5 rounded'
    : change < 0
    ? 'text-red-600 bg-red-50 px-2 py-0.5 rounded'
    : 'text-gray-600'
})

// Helper functions
const formatPrice = (price) => {
  if (price === null || price === undefined) return '---'
  return price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatChange = (change) => {
  if (change === null || change === undefined) return '---'
  const sign = change > 0 ? '+' : ''
  return sign + change.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatPercent = (percent) => {
  if (percent === null || percent === undefined) return '---'
  const sign = percent > 0 ? '+' : ''
  return sign + percent.toFixed(2)
}
</script>
