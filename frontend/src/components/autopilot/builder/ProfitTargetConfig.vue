<template>
  <div class="profit-target-config" data-testid="profit-target-config">
    <div class="config-header">
      <h4 class="text-sm font-medium text-gray-900">Profit Target Exit (#18-19)</h4>
      <p class="text-xs text-gray-500 mt-1">
        Close position when profit reaches X% of max profit
      </p>
    </div>

    <div class="config-body mt-4 space-y-4">
      <!-- Enable/Disable -->
      <div class="flex items-center justify-between">
        <label class="text-sm text-gray-700">Enable Profit Target Exit</label>
        <input
          type="checkbox"
          v-model="localConfig.enabled"
          @change="emitUpdate"
          data-testid="profit-target-enabled"
          class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
        />
      </div>

      <!-- Quick Presets -->
      <div v-if="localConfig.enabled" class="preset-buttons">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Quick Presets
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            @click="setPreset(25)"
            :class="[
              'px-3 py-2 text-sm rounded-lg border transition-colors',
              localConfig.target_pct === 25
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            ]"
            data-testid="profit-target-preset-25"
          >
            25%
            <span class="block text-xs opacity-75">Fast Recycling</span>
          </button>
          <button
            @click="setPreset(50)"
            :class="[
              'px-3 py-2 text-sm rounded-lg border transition-colors',
              localConfig.target_pct === 50
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            ]"
            data-testid="profit-target-preset-50"
          >
            50%
            <span class="block text-xs opacity-75">Optimal (Backtested)</span>
          </button>
          <button
            @click="setPreset(75)"
            :class="[
              'px-3 py-2 text-sm rounded-lg border transition-colors',
              localConfig.target_pct === 75
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            ]"
            data-testid="profit-target-preset-75"
          >
            75%
            <span class="block text-xs opacity-75">Conservative</span>
          </button>
        </div>
      </div>

      <!-- Custom Value -->
      <div v-if="localConfig.enabled">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Custom Target %
        </label>
        <div class="flex items-center space-x-3">
          <input
            type="range"
            v-model="localConfig.target_pct"
            @input="emitUpdate"
            min="10"
            max="100"
            step="5"
            data-testid="profit-target-slider"
            class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <span class="text-sm font-medium text-gray-900 w-16 text-right">
            {{ localConfig.target_pct }}%
          </span>
        </div>
        <p class="text-xs text-gray-500 mt-1">
          Exit when profit reaches {{ localConfig.target_pct }}% of max profit
        </p>
      </div>

      <!-- Auto Close Toggle -->
      <div v-if="localConfig.enabled" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div>
          <label class="text-sm font-medium text-gray-700">Auto Close</label>
          <p class="text-xs text-gray-500 mt-0.5">
            Automatically exit when target is reached
          </p>
        </div>
        <input
          type="checkbox"
          v-model="localConfig.auto_close"
          @change="emitUpdate"
          data-testid="profit-target-auto-close"
          class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
        />
      </div>

      <!-- Example Calculation -->
      <div v-if="localConfig.enabled" class="example-box p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p class="text-xs font-medium text-blue-900 mb-1">Example:</p>
        <p class="text-xs text-blue-800">
          If max profit is ₹10,000, position will {{ localConfig.auto_close ? 'automatically exit' : 'alert you' }}
          when current P&L reaches ₹{{ (10000 * localConfig.target_pct / 100).toLocaleString() }}
          ({{ localConfig.target_pct }}% of ₹10,000)
        </p>
      </div>

      <!-- Research Note -->
      <div class="research-note p-3 bg-green-50 border border-green-200 rounded-lg">
        <p class="text-xs font-medium text-green-900 mb-1">📊 Research Insight:</p>
        <p class="text-xs text-green-800">
          <strong>50% profit target</strong> is backtested optimal for Iron Condors and credit spreads
          (Option Alpha study: Higher win rate, 8.3% lower max drawdown vs holding to expiration)
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  config: {
    type: Object,
    default: () => ({
      enabled: false,
      target_pct: 50,
      auto_close: true
    })
  }
})

const emit = defineEmits(['update'])

// Local state
const localConfig = ref({
  enabled: props.config.enabled ?? false,
  target_pct: props.config.target_pct ?? 50,
  auto_close: props.config.auto_close ?? true
})

// Watch for external config changes
watch(() => props.config, (newConfig) => {
  localConfig.value = {
    enabled: newConfig.enabled ?? false,
    target_pct: newConfig.target_pct ?? 50,
    auto_close: newConfig.auto_close ?? true
  }
}, { deep: true })

function setPreset(percentage) {
  localConfig.value.target_pct = percentage
  emitUpdate()
}

function emitUpdate() {
  emit('update', { ...localConfig.value })
}
</script>

<style scoped>
.profit-target-config {
  @apply border border-gray-200 rounded-lg p-4;
}

.config-header h4 {
  @apply text-sm font-semibold text-gray-900;
}

/* Range slider styling */
input[type="range"]::-webkit-slider-thumb {
  @apply appearance-none w-4 h-4 bg-blue-600 rounded-full cursor-pointer;
}

input[type="range"]::-moz-range-thumb {
  @apply w-4 h-4 bg-blue-600 rounded-full cursor-pointer border-0;
}

/* Preset button hover effects */
.preset-buttons button:hover {
  @apply shadow-sm;
}

/* Checkbox styling */
input[type="checkbox"]:checked {
  @apply bg-blue-600 border-blue-600;
}
</style>
