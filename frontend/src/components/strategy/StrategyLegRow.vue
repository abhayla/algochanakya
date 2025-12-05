<template>
  <tr :class="{ 'bg-blue-50': isSelected }">
    <!-- Checkbox -->
    <td class="px-2 py-2">
      <input
        type="checkbox"
        :checked="isSelected"
        @change="$emit('toggle-select')"
        class="h-4 w-4 text-blue-600 rounded"
      />
    </td>

    <!-- Expiry -->
    <td class="px-3 py-2">
      <select
        :value="leg.expiry_date"
        @change="handleExpiryChange($event.target.value)"
        class="w-full text-sm border rounded px-2 py-1"
      >
        <option value="">Select</option>
        <option v-for="exp in expiries" :key="exp" :value="exp">
          {{ formatDate(exp) }}
        </option>
      </select>
    </td>

    <!-- Contract Type -->
    <td class="px-3 py-2">
      <select
        :value="leg.contract_type"
        @change="$emit('update', { contract_type: $event.target.value })"
        :class="[
          'w-full text-sm border rounded px-2 py-1 font-medium',
          leg.contract_type === 'CE' ? 'text-green-700' : 'text-red-700'
        ]"
      >
        <option value="CE">CE</option>
        <option value="PE">PE</option>
      </select>
    </td>

    <!-- Transaction Type -->
    <td class="px-3 py-2">
      <select
        :value="leg.transaction_type"
        @change="$emit('update', { transaction_type: $event.target.value })"
        :class="[
          'w-full text-sm border rounded px-2 py-1 font-medium',
          leg.transaction_type === 'BUY' ? 'text-blue-700' : 'text-orange-700'
        ]"
      >
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>
    </td>

    <!-- Strike Price -->
    <td class="px-3 py-2">
      <select
        :value="leg.strike_price"
        @change="$emit('update', { strike_price: parseFloat($event.target.value) })"
        class="w-full text-sm border rounded px-2 py-1"
      >
        <option value="">Select</option>
        <option v-for="strike in strikes" :key="strike" :value="strike">
          {{ strike }}
        </option>
      </select>
    </td>

    <!-- Lots -->
    <td class="px-3 py-2">
      <select
        :value="leg.lots"
        @change="$emit('update', { lots: parseInt($event.target.value) })"
        class="w-full text-sm border rounded px-2 py-1"
      >
        <option v-for="n in 50" :key="n" :value="n">{{ n }}</option>
      </select>
    </td>

    <!-- Strategy Type -->
    <td class="px-3 py-2">
      <select
        :value="leg.strategy_type"
        @change="$emit('update', { strategy_type: $event.target.value })"
        class="w-full text-sm border rounded px-2 py-1"
      >
        <option v-for="type in strategyTypes" :key="type" :value="type">
          {{ type }}
        </option>
      </select>
    </td>

    <!-- Entry Price -->
    <td class="px-3 py-2">
      <input
        type="number"
        :value="leg.entry_price"
        @input="$emit('update', { entry_price: $event.target.value ? parseFloat($event.target.value) : null })"
        step="0.05"
        class="w-20 text-sm border rounded px-2 py-1 text-right"
        placeholder="0.00"
      />
    </td>

    <!-- Exit Price -->
    <td class="px-3 py-2">
      <input
        type="number"
        :value="leg.exit_price"
        @input="$emit('update', { exit_price: $event.target.value ? parseFloat($event.target.value) : null })"
        step="0.05"
        class="w-20 text-sm border rounded px-2 py-1 text-right"
        placeholder="0.00"
      />
    </td>

    <!-- Qty -->
    <td class="px-3 py-2 text-sm text-gray-900">
      {{ leg.lots * lotSize }}
    </td>

    <!-- CMP -->
    <td class="px-3 py-2 text-sm font-medium" :class="cmp ? 'text-gray-900' : 'text-gray-400'">
      {{ cmp ? cmp.toFixed(2) : '-' }}
    </td>

    <!-- P/L -->
    <td class="px-3 py-2 text-sm font-medium" :class="pnlClass">
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
    >
      {{ formatPnL(getPnLAtSpot(idx)) }}
    </td>
  </tr>
</template>

<script setup>
import { computed } from 'vue'

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

function getPnLAtSpot(spotIndex) {
  if (!props.pnlValues || props.pnlValues.length === 0) return null
  // Find matching index from full pnl values
  // This assumes spotPrices are a subset of the full spot prices array
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
