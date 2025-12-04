<template>
  <div class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
    <!-- Main Row -->
    <div
      class="flex items-center px-4 py-3 cursor-pointer"
      @click="toggleExpand"
    >
      <!-- Symbol & Exchange -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="font-medium text-gray-900">{{ instrument.symbol }}</span>
          <span class="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
            {{ instrument.exchange }}
          </span>
        </div>
      </div>

      <!-- LTP -->
      <div class="w-32 text-right">
        <span class="text-base font-semibold" :class="priceClass">
          {{ formatPrice(tick.ltp) }}
        </span>
      </div>

      <!-- Change -->
      <div class="w-28 text-right">
        <span class="text-sm font-medium" :class="changeClass">
          {{ formatChange(tick.change) }}
        </span>
      </div>

      <!-- Change % -->
      <div class="w-24 text-right">
        <span
          class="inline-block text-xs font-semibold px-2 py-1 rounded"
          :class="changePercentClass"
        >
          {{ formatPercent(tick.change_percent) }}%
        </span>
      </div>

      <!-- Expand Indicator -->
      <div class="w-8 text-center">
        <span class="text-gray-400 text-sm">
          {{ expanded ? '▲' : '▼' }}
        </span>
      </div>
    </div>

    <!-- Expanded Actions -->
    <div
      v-if="expanded"
      class="flex items-center gap-2 px-4 py-3 bg-gray-50 border-t border-gray-100"
    >
      <button
        class="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors"
        @click.stop="handleBuy"
      >
        B
      </button>
      <button
        class="px-3 py-1.5 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors"
        @click.stop="handleSell"
      >
        S
      </button>
      <button
        class="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded transition-colors"
        @click.stop="handleChart"
      >
        Chart
      </button>
      <button
        class="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded transition-colors"
        @click.stop="handleOptionChain"
      >
        Option Chain
      </button>
      <button
        class="ml-auto px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
        @click.stop="handleDelete"
      >
        ✕ Remove
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  instrument: {
    type: Object,
    required: true
  },
  tick: {
    type: Object,
    default: () => ({ ltp: null, change: null, change_percent: null })
  }
})

const emit = defineEmits(['delete'])

const expanded = ref(false)

// Computed classes
const priceClass = computed(() => {
  if (!props.tick.ltp) return 'text-gray-800'
  const change = props.tick.change_percent
  return change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-800'
})

const changeClass = computed(() => {
  const change = props.tick.change_percent
  return change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-600'
})

const changePercentClass = computed(() => {
  const change = props.tick.change_percent
  return change > 0
    ? 'text-green-700 bg-green-100'
    : change < 0
    ? 'text-red-700 bg-red-100'
    : 'text-gray-700 bg-gray-100'
})

// Methods
const toggleExpand = () => {
  expanded.value = !expanded.value
}

const formatPrice = (price) => {
  if (price === null || price === undefined) return '---'
  return price.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatChange = (change) => {
  if (change === null || change === undefined) return '---'
  const sign = change > 0 ? '+' : ''
  return sign + change.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatPercent = (percent) => {
  if (percent === null || percent === undefined) return '---'
  const sign = percent > 0 ? '+' : ''
  return sign + percent.toFixed(2)
}

// Action handlers
const handleBuy = () => {
  console.log('Buy:', props.instrument.symbol)
  // TODO: Implement buy functionality
}

const handleSell = () => {
  console.log('Sell:', props.instrument.symbol)
  // TODO: Implement sell functionality
}

const handleChart = () => {
  console.log('Chart:', props.instrument.symbol)
  // TODO: Implement chart view
}

const handleOptionChain = () => {
  console.log('Option Chain:', props.instrument.symbol)
  // TODO: Implement option chain view
}

const handleDelete = () => {
  emit('delete', props.instrument.token)
}
</script>
