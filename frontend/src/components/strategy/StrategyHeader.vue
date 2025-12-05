<template>
  <div class="bg-white shadow">
    <div class="container mx-auto px-4 py-3">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <!-- Navigation and Title -->
        <div class="flex items-center gap-4">
          <!-- Navigation Links -->
          <div class="flex items-center gap-4 mr-4">
            <router-link to="/watchlist" class="text-sm text-gray-600 hover:text-blue-600">Watchlist</router-link>
            <router-link to="/optionchain" class="text-sm text-gray-600 hover:text-blue-600">Option Chain</router-link>
            <router-link to="/strategy" class="text-sm text-blue-600 font-semibold">Strategy Builder</router-link>
          </div>
          <div class="h-6 border-l border-gray-300"></div>
          <div class="flex items-center gap-2">
            <button
              v-for="u in underlyings"
              :key="u"
              :class="[
                'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                underlying === u
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              ]"
              @click="$emit('update:underlying', u)"
            >
              {{ u }}
            </button>
          </div>
        </div>

        <!-- P/L Mode Toggle -->
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600">P/L Mode:</span>
            <button
              :class="[
                'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors',
                pnlMode === 'expiry'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              ]"
              @click="$emit('toggle-mode')"
            >
              At Expiry
            </button>
            <button
              :class="[
                'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors',
                pnlMode === 'current'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              ]"
              @click="$emit('toggle-mode')"
            >
              Current
            </button>
          </div>

          <!-- Loading Indicator -->
          <div v-if="isLoading" class="flex items-center gap-2 text-blue-600">
            <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-sm">Loading...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  underlying: {
    type: String,
    required: true
  },
  pnlMode: {
    type: String,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:underlying', 'toggle-mode'])

const underlyings = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
</script>
