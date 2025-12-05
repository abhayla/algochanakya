<template>
  <div
    class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 group"
    @mouseenter="showActions = true"
    @mouseleave="showActions = false"
  >
    <div class="flex items-center justify-between">
      <!-- Left: Symbol -->
      <div class="flex items-center space-x-2 flex-1 min-w-0">
        <span :class="[changeClass, 'font-medium truncate']">
          {{ instrument.symbol || instrument.tradingsymbol }}
        </span>
        <span class="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded flex-shrink-0">
          {{ instrument.exchange }}
        </span>
      </div>

      <!-- Right: Price Data -->
      <div class="flex items-center space-x-3">
        <!-- Change -->
        <span :class="[changeClass, 'text-sm w-16 text-right']">
          {{ formatChange(change) }}
        </span>

        <!-- Percent Change with Arrow -->
        <span :class="[changeClass, 'text-sm w-20 text-right flex items-center justify-end']">
          {{ formatPercent(changePercent) }}
          <svg v-if="change > 0" class="w-3 h-3 ml-1" width="12" height="12" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
          <svg v-else-if="change < 0" class="w-3 h-3 ml-1" width="12" height="12" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </span>

        <!-- LTP -->
        <span :class="[changeClass, 'font-semibold w-20 text-right']">
          {{ formatPrice(ltp) }}
        </span>

        <!-- Actions (show on hover) -->
        <div v-show="showActions" class="flex items-center space-x-1 ml-2">
          <button
            @click.stop="$emit('remove', instrument.token || instrument.instrument_token)"
            class="p-1 text-gray-400 hover:text-red-500 transition-colors"
            title="Remove from watchlist"
          >
            <svg class="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  instrument: {
    type: Object,
    required: true
  },
  tick: {
    type: Object,
    default: () => ({})
  }
})

defineEmits(['remove'])

const showActions = ref(false)

// Computed values
const ltp = computed(() => props.tick?.ltp || 0)
const change = computed(() => props.tick?.change || 0)
const changePercent = computed(() => {
  if (props.tick?.ltp && props.tick?.close) {
    return ((props.tick.ltp - props.tick.close) / props.tick.close) * 100
  }
  return props.tick?.change_percent || 0
})

const changeClass = computed(() => {
  if (change.value > 0) return 'text-green-600'
  if (change.value < 0) return 'text-red-600'
  return 'text-gray-600'
})

// Formatters
const formatPrice = (price) => {
  if (!price) return '--'
  return price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatChange = (val) => {
  if (val === null || val === undefined || val === 0) return '--'
  const sign = val > 0 ? '+' : ''
  return sign + val.toFixed(2)
}

const formatPercent = (val) => {
  if (val === null || val === undefined || val === 0) return '--'
  const sign = val > 0 ? '+' : ''
  return sign + val.toFixed(2) + '%'
}
</script>
