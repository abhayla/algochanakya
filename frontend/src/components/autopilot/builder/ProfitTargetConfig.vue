<template>
  <div class="border border-gray-200 rounded-lg p-4" data-testid="autopilot-profit-target-section">
    <div>
      <h4 class="text-sm font-medium text-gray-900">Profit Target Exit (#18-22)</h4>
      <p class="text-xs text-gray-500 mt-1">
        Close position when profit reaches target threshold
      </p>
    </div>

    <div class="config-body mt-4 space-y-4">
      <!-- Profit % Exit -->
      <div class="exit-rule-item">
        <div class="flex items-center justify-between">
          <label class="text-sm text-gray-700">Enable Profit % Target</label>
          <input
            type="checkbox"
            v-model="localConfig.enabled"
            @change="emitUpdate"
            data-testid="autopilot-exit-profit-pct-enable"
            class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
          />
        </div>

        <div v-if="localConfig.enabled" class="mt-3 space-y-3">
          <!-- Quick Presets -->
          <div class="preset-buttons">
            <label class="block text-sm text-gray-700 mb-2">Quick Presets</label>
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

          <!-- Custom Value Input -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Custom Target %
            </label>
            <div class="flex items-center space-x-3">
              <input
                type="number"
                v-model.number="localConfig.target_pct"
                @input="emitUpdate"
                min="10"
                max="100"
                step="5"
                data-testid="autopilot-exit-profit-pct-value"
                class="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
              />
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
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Exit when profit reaches {{ localConfig.target_pct }}% of max profit
            </p>
          </div>
        </div>
      </div>

      <div class="border-t border-gray-200 my-4"></div>

      <!-- Premium Captured % Exit (#20) -->
      <div class="exit-rule-item">
        <div class="flex items-center justify-between">
          <div>
            <label class="text-sm text-gray-700">Premium Captured %</label>
            <p class="text-xs text-gray-500">Exit when X% of premium collected is captured</p>
          </div>
          <input
            type="checkbox"
            v-model="localConfig.premium_captured_enabled"
            @change="emitUpdate"
            data-testid="autopilot-exit-premium-captured-enable"
            class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
          />
        </div>

        <div v-if="localConfig.premium_captured_enabled" class="mt-3">
          <div class="flex items-center space-x-3">
            <input
              type="number"
              v-model.number="localConfig.premium_captured_pct"
              @input="emitUpdate"
              min="10"
              max="100"
              step="5"
              data-testid="autopilot-exit-premium-captured-value"
              class="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="text-sm text-gray-600">% of premium captured</span>
          </div>
        </div>
      </div>

      <div class="border-t border-gray-200 my-4"></div>

      <!-- Return on Margin % Exit (#21) -->
      <div class="exit-rule-item">
        <div class="flex items-center justify-between">
          <div>
            <label class="text-sm text-gray-700">Target Return on Margin %</label>
            <p class="text-xs text-gray-500">Exit when return on margin reaches target</p>
          </div>
          <input
            type="checkbox"
            v-model="localConfig.return_on_margin_enabled"
            @change="emitUpdate"
            data-testid="autopilot-exit-return-on-margin-enable"
            class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
          />
        </div>

        <div v-if="localConfig.return_on_margin_enabled" class="mt-3">
          <div class="flex items-center space-x-3">
            <input
              type="number"
              v-model.number="localConfig.return_on_margin_pct"
              @input="emitUpdate"
              min="1"
              max="100"
              step="1"
              data-testid="autopilot-exit-return-on-margin-value"
              class="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="text-sm text-gray-600">% return on margin</span>
          </div>
        </div>
      </div>

      <div class="border-t border-gray-200 my-4"></div>

      <!-- Auto Close Toggle -->
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div>
          <label class="text-sm font-medium text-gray-700">Auto Close</label>
          <p class="text-xs text-gray-500 mt-0.5">
            Automatically exit when any target is reached
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
      auto_close: true,
      premium_captured_enabled: false,
      premium_captured_pct: 50,
      return_on_margin_enabled: false,
      return_on_margin_pct: 10
    })
  }
})

const emit = defineEmits(['update'])

// Local state
const localConfig = ref({
  enabled: props.config.enabled ?? false,
  target_pct: props.config.target_pct ?? 50,
  auto_close: props.config.auto_close ?? true,
  premium_captured_enabled: props.config.premium_captured_enabled ?? false,
  premium_captured_pct: props.config.premium_captured_pct ?? 50,
  return_on_margin_enabled: props.config.return_on_margin_enabled ?? false,
  return_on_margin_pct: props.config.return_on_margin_pct ?? 10
})

// Watch for external config changes
watch(() => props.config, (newConfig) => {
  localConfig.value = {
    enabled: newConfig.enabled ?? false,
    target_pct: newConfig.target_pct ?? 50,
    auto_close: newConfig.auto_close ?? true,
    premium_captured_enabled: newConfig.premium_captured_enabled ?? false,
    premium_captured_pct: newConfig.premium_captured_pct ?? 50,
    return_on_margin_enabled: newConfig.return_on_margin_enabled ?? false,
    return_on_margin_pct: newConfig.return_on_margin_pct ?? 10
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
/* Range slider styling */
input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  width: 1rem;
  height: 1rem;
  background-color: #2563eb;
  border-radius: 9999px;
  cursor: pointer;
}

input[type="range"]::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  background-color: #2563eb;
  border-radius: 9999px;
  cursor: pointer;
  border: 0;
}

/* Preset button hover effects */
.preset-buttons button:hover {
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}

/* Checkbox styling */
input[type="checkbox"]:checked {
  background-color: #2563eb;
  border-color: #2563eb;
}

/* Exit rule items */
.exit-rule-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}
</style>
