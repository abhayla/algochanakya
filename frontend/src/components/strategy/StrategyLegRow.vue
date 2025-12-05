<template>
  <tr :class="{ 'bg-blue-50': isSelected }">
    <!-- Checkbox -->
    <td class="px-2 py-2 w-10">
      <input
        type="checkbox"
        :checked="isSelected"
        @change="$emit('toggle-select')"
        class="h-4 w-4 text-blue-600 rounded"
      />
    </td>

    <!-- Expiry -->
    <td class="px-1 py-1" style="min-width: 100px;">
      <select
        :value="leg.expiry_date"
        @change="handleExpiryChange($event.target.value)"
        class="w-full text-xs border rounded px-1 py-1"
      >
        <option value="">Select</option>
        <option v-for="exp in expiries" :key="exp" :value="exp">
          {{ formatDate(exp) }}
        </option>
      </select>
    </td>

    <!-- Contract Type -->
    <td class="px-1 py-1" style="min-width: 80px;">
      <select
        :value="leg.contract_type"
        @change="$emit('update', { contract_type: $event.target.value })"
        :class="[
          'w-full text-xs border rounded px-1 py-1 font-medium',
          leg.contract_type === 'CE' ? 'text-green-700' : 'text-red-700'
        ]"
      >
        <option value="CE">CE</option>
        <option value="PE">PE</option>
      </select>
    </td>

    <!-- Transaction Type -->
    <td class="px-1 py-1" style="min-width: 70px;">
      <select
        :value="leg.transaction_type"
        @change="$emit('update', { transaction_type: $event.target.value })"
        :class="[
          'w-full text-xs border rounded px-1 py-1 font-medium',
          leg.transaction_type === 'BUY' ? 'text-blue-700' : 'text-orange-700'
        ]"
      >
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>
    </td>

    <!-- Strike Price -->
    <td class="px-1 py-1" style="min-width: 100px;">
      <select
        :value="leg.strike_price"
        @change="handleStrikeChange($event.target.value)"
        class="w-full text-xs border rounded px-1 py-1"
      >
        <option value="">Select</option>
        <option v-for="strike in strikes" :key="strike" :value="strike">
          {{ strike }}
        </option>
      </select>
    </td>

    <!-- Lots -->
    <td class="px-1 py-1" style="min-width: 60px;">
      <select
        :value="leg.lots"
        @change="$emit('update', { lots: parseInt($event.target.value) })"
        class="w-full text-xs border rounded px-1 py-1"
      >
        <option v-for="n in 50" :key="n" :value="n">{{ n }}</option>
      </select>
    </td>

    <!-- Strategy Type -->
    <td class="px-1 py-1" style="min-width: 110px;">
      <select
        :value="leg.strategy_type"
        @change="$emit('update', { strategy_type: $event.target.value })"
        class="w-full text-xs border rounded px-1 py-1"
      >
        <option v-for="type in strategyTypes" :key="type" :value="type">
          {{ type }}
        </option>
      </select>
    </td>

    <!-- Entry Price -->
    <td class="px-1 py-1" style="min-width: 80px;">
      <input
        type="number"
        :value="leg.entry_price"
        @input="$emit('update', { entry_price: $event.target.value ? parseFloat($event.target.value) : null })"
        step="0.05"
        class="w-full text-xs border rounded px-1 py-1 text-right"
        placeholder="0.00"
      />
    </td>

    <!-- Exit Price - Shows calculated P/L when CMP available, click to override -->
    <td class="px-1 py-1" style="min-width: 80px;">
      <div class="relative">
        <!-- Show calculated P/L if available and not editing -->
        <span
          v-if="exitPnL !== null && !isEditingExitPrice"
          @click="isEditingExitPrice = true"
          class="block w-full text-xs px-1 py-1 text-right cursor-pointer hover:bg-gray-100 rounded"
          :class="exitPnL > 0 ? 'text-green-600 font-medium' : exitPnL < 0 ? 'text-red-600 font-medium' : 'text-gray-500'"
          :title="'Click to override. Calculated: ' + formatPnL(exitPnL)"
        >
          {{ formatPnL(exitPnL) }}
        </span>
        <!-- Input for manual override or when no CMP -->
        <input
          v-else
          type="number"
          :value="leg.exit_price"
          @input="$emit('update', { exit_price: $event.target.value ? parseFloat($event.target.value) : null })"
          @blur="isEditingExitPrice = false"
          step="0.05"
          class="w-full text-xs border rounded px-1 py-1 text-right"
          placeholder="0.00"
        />
      </div>
    </td>

    <!-- Qty -->
    <td class="px-2 py-2 text-xs text-gray-900 text-right" style="min-width: 60px;">
      {{ leg.lots * lotSize }}
    </td>

    <!-- CMP -->
    <td class="px-2 py-2 text-xs font-medium text-right" style="min-width: 70px;" :class="cmp ? 'text-gray-900' : 'text-gray-400'">
      {{ cmp ? cmp.toFixed(2) : '-' }}
    </td>

    <!-- P/L -->
    <td class="px-2 py-2 text-xs font-medium text-right" style="min-width: 80px;" :class="pnlClass">
      {{ formatPnL(legPnl) }}
    </td>

    <!-- Dynamic P/L Columns -->
    <td
      v-for="(spot, idx) in spotPrices"
      :key="'pnl-' + spot"
      :class="[
        'px-2 py-2 text-center text-sm',
        getPnLCellClass(getPnLAtSpot(idx)),
        isCurrentSpotCol(spot) ? 'ring-2 ring-blue-400' : ''
      ]"
      style="min-width: 70px;"
    >
      {{ formatPnL(getPnLAtSpot(idx)) }}
    </td>
  </tr>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  leg: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  expiries: {
    type: Array,
    default: () => []
  },
  strikes: {
    type: Array,
    default: () => []
  },
  strategyTypes: {
    type: Array,
    default: () => []
  },
  lotSize: {
    type: Number,
    default: 75
  },
  isSelected: {
    type: Boolean,
    default: false
  },
  spotPrices: {
    type: Array,
    default: () => []
  },
  pnlValues: {
    type: Array,
    default: () => []
  },
  currentSpot: {
    type: Number,
    default: 0
  },
  cmp: {
    type: Number,
    default: null
  },
  legPnl: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update', 'toggle-select', 'fetch-strikes'])

// State for Exit Price editing
const isEditingExitPrice = ref(false)

// Calculated Exit P/L based on CMP
const exitPnL = computed(() => {
  if (!props.cmp || !props.leg.entry_price) return null
  const qty = props.leg.lots * props.lotSize
  const multiplier = props.leg.transaction_type === 'BUY' ? 1 : -1
  return (props.cmp - parseFloat(props.leg.entry_price)) * qty * multiplier
})

const pnlClass = computed(() => {
  if (props.legPnl === null) return 'text-gray-400'
  if (props.legPnl > 0) return 'text-green-600'
  if (props.legPnl < 0) return 'text-red-600'
  return 'text-gray-600'
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

function formatPnL(value) {
  if (value === null || value === undefined) return '-'
  const formatted = Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })
  return value < 0 ? `-${formatted}` : formatted
}

function handleExpiryChange(expiry) {
  emit('update', { expiry_date: expiry, strike_price: null })
  if (expiry) {
    emit('fetch-strikes', expiry)
  }
}

function handleStrikeChange(value) {
  // Keep as string to match option values for proper binding
  // The value will be like "23750.00" which matches the option values
  emit('update', { strike_price: value || null })
}

function getPnLAtSpot(spotIndex) {
  if (!props.pnlValues || props.pnlValues.length === 0) return null
  // pnlValues is now pre-interpolated to match spotPrices (displayedSpotPrices)
  return props.pnlValues[spotIndex] ?? null
}

function isCurrentSpotCol(spot) {
  if (!props.currentSpot) return false
  return Math.abs(spot - props.currentSpot) < 50
}

function getPnLCellClass(pnl) {
  if (pnl === null || pnl === undefined) return 'bg-gray-50'
  if (pnl < 0) return 'bg-red-100 text-red-800'
  if (pnl > 0) return 'bg-green-50 text-green-800'
  return 'bg-gray-50'
}
</script>

<style scoped>
/* Ensure dropdowns show full text */
select {
  min-width: 0;
  cursor: pointer;
}

/* Remove number input spinners for cleaner look */
input[type="number"] {
  -moz-appearance: textfield;
}
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
