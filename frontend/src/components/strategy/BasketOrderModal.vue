<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen px-4">
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-black bg-opacity-50" @click="$emit('close')"></div>

      <!-- Modal -->
      <div class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Confirm Basket Order</h3>

        <div class="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div class="flex items-start">
            <svg class="h-5 w-5 text-yellow-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
            <div class="ml-3">
              <h4 class="text-sm font-medium text-yellow-800">Warning: Real Trading</h4>
              <p class="text-sm text-yellow-700 mt-1">
                This will place real orders with your broker. Please review the orders carefully before confirming.
              </p>
            </div>
          </div>
        </div>

        <!-- Order Summary -->
        <div class="mb-4 overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Order</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(leg, index) in legs" :key="index">
                <td class="px-3 py-2 text-sm" :class="leg.contract_type === 'CE' ? 'text-green-700' : 'text-red-700'">
                  {{ leg.contract_type }}
                </td>
                <td class="px-3 py-2 text-sm">{{ leg.strike_price || '-' }}</td>
                <td class="px-3 py-2 text-sm" :class="leg.transaction_type === 'BUY' ? 'text-blue-700' : 'text-orange-700'">
                  {{ leg.transaction_type }}
                </td>
                <td class="px-3 py-2 text-sm">{{ leg.lots * lotSize }}</td>
                <td class="px-3 py-2 text-sm">{{ leg.entry_price || 'Market' }}</td>
                <td class="px-3 py-2 text-sm">{{ leg.entry_price ? 'LIMIT' : 'MARKET' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Total Summary -->
        <div class="mb-4 p-4 bg-gray-50 rounded-lg">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Total Legs:</span>
            <span class="font-medium">{{ legs.length }}</span>
          </div>
          <div class="flex justify-between text-sm mt-1">
            <span class="text-gray-600">Total Quantity:</span>
            <span class="font-medium">{{ totalQuantity }}</span>
          </div>
          <div class="flex justify-between text-sm mt-1">
            <span class="text-gray-600">Estimated Premium:</span>
            <span class="font-medium">{{ formatNumber(estimatedPremium) }}</span>
          </div>
        </div>

        <!-- Confirmation Checkbox -->
        <div class="mb-4">
          <label class="flex items-center">
            <input
              v-model="confirmed"
              type="checkbox"
              class="h-4 w-4 text-blue-600 rounded"
            />
            <span class="ml-2 text-sm text-gray-700">
              I understand this will place real orders and I accept the risks
            </span>
          </label>
        </div>

        <div class="flex justify-end gap-3">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            @click="handleConfirm"
            :disabled="!confirmed || isLoading"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-lg',
              confirmed && !isLoading
                ? 'text-white bg-orange-600 hover:bg-orange-700'
                : 'text-gray-400 bg-gray-200 cursor-not-allowed'
            ]"
          >
            {{ isLoading ? 'Placing Orders...' : 'Place Orders' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  legs: {
    type: Array,
    required: true
  },
  lotSize: {
    type: Number,
    default: 75
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirm', 'close'])

const confirmed = ref(false)

const totalQuantity = computed(() => {
  return props.legs.reduce((sum, leg) => sum + (leg.lots * props.lotSize), 0)
})

const estimatedPremium = computed(() => {
  return props.legs.reduce((sum, leg) => {
    if (!leg.entry_price) return sum
    const qty = leg.lots * props.lotSize
    const multiplier = leg.transaction_type === 'BUY' ? -1 : 1
    return sum + (parseFloat(leg.entry_price) * qty * multiplier)
  }, 0)
})

function formatNumber(value) {
  if (value === null || value === undefined) return '-'
  const formatted = Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })
  return value < 0 ? `-${formatted}` : formatted
}

function handleConfirm() {
  if (confirmed.value) {
    emit('confirm')
  }
}
</script>
