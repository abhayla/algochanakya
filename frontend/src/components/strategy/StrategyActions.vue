<template>
  <div class="p-4 bg-gray-50 border-t flex flex-wrap items-center justify-between gap-4">
    <!-- Left Actions -->
    <div class="flex items-center gap-2">
      <button
        v-if="hasSelection"
        @click="$emit('delete-selected')"
        class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
      >
        Delete Selected
      </button>
      <button
        @click="$emit('add-leg')"
        class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
      >
        + Add Row
      </button>
      <button
        @click="$emit('recalculate')"
        :disabled="!hasLegs || isLoading"
        :class="[
          'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
          hasLegs && !isLoading
            ? 'text-white bg-blue-600 hover:bg-blue-700'
            : 'text-gray-400 bg-gray-200 cursor-not-allowed'
        ]"
      >
        {{ isLoading ? 'Calculating...' : 'ReCalculate' }}
      </button>
    </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-2">
      <button
        @click="$emit('import-positions')"
        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        Import Positions
      </button>
      <button
        @click="$emit('update-positions')"
        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        Update Positions
      </button>
      <button
        @click="$emit('save')"
        :disabled="!hasLegs"
        :class="[
          'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
          hasLegs
            ? 'text-white bg-purple-600 hover:bg-purple-700'
            : 'text-gray-400 bg-gray-200 cursor-not-allowed'
        ]"
      >
        {{ hasStrategy ? 'Update' : 'Save' }}
      </button>
      <button
        v-if="hasStrategy"
        @click="$emit('share')"
        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        Share
      </button>
      <button
        @click="$emit('buy-basket')"
        :disabled="!hasLegs"
        :class="[
          'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
          hasLegs
            ? 'text-white bg-orange-600 hover:bg-orange-700'
            : 'text-gray-400 bg-gray-200 cursor-not-allowed'
        ]"
      >
        Buy Basket Order
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  hasSelection: {
    type: Boolean,
    default: false
  },
  hasLegs: {
    type: Boolean,
    default: false
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  hasStrategy: {
    type: Boolean,
    default: false
  }
})

defineEmits([
  'add-leg',
  'delete-selected',
  'recalculate',
  'save',
  'update-positions',
  'buy-basket',
  'import-positions',
  'share'
])
</script>
