<template>
  <div class="dte-exit-config" data-testid="dte-exit-config">
    <div class="config-header">
      <h4 class="text-sm font-medium text-gray-900">Time-Based Exit Rules (#23-24)</h4>
      <p class="text-xs text-gray-500 mt-1">
        Exit position based on DTE or days in trade
      </p>
    </div>

    <div class="config-body mt-4 space-y-6">
      <!-- DTE-Based Exit (#23) -->
      <div class="dte-section">
        <div class="flex items-center justify-between mb-3">
          <div>
            <label class="text-sm font-medium text-gray-700">DTE Exit Rule</label>
            <p class="text-xs text-gray-500 mt-0.5">
              Exit when days to expiry reaches threshold
            </p>
          </div>
          <input
            type="checkbox"
            v-model="localConfig.dte_exit.enabled"
            @change="emitUpdate"
            data-testid="dte-exit-enabled"
            class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
          />
        </div>

        <div v-if="localConfig.dte_exit.enabled" class="space-y-3">
          <!-- DTE Presets -->
          <div class="preset-buttons">
            <label class="block text-sm text-gray-700 mb-2">Quick Presets</label>
            <div class="grid grid-cols-4 gap-2">
              <button
                @click="setDTEPreset(7)"
                :class="getDTEPresetClass(7)"
                data-testid="dte-preset-7"
              >
                7 DTE
                <span class="block text-xs opacity-75">Expiry Week</span>
              </button>
              <button
                @click="setDTEPreset(14)"
                :class="getDTEPresetClass(14)"
                data-testid="dte-preset-14"
              >
                14 DTE
                <span class="block text-xs opacity-75">Two Weeks</span>
              </button>
              <button
                @click="setDTEPreset(21)"
                :class="getDTEPresetClass(21)"
                data-testid="dte-preset-21"
              >
                21 DTE
                <span class="block text-xs opacity-75">Optimal (Recommended)</span>
              </button>
              <button
                @click="setDTEPreset(30)"
                :class="getDTEPresetClass(30)"
                data-testid="dte-preset-30"
              >
                30 DTE
                <span class="block text-xs opacity-75">One Month</span>
              </button>
            </div>
          </div>

          <!-- Custom DTE Value -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Custom DTE Threshold
            </label>
            <div class="flex items-center space-x-3">
              <input
                type="range"
                v-model="localConfig.dte_exit.dte_threshold"
                @input="emitUpdate"
                min="1"
                max="45"
                step="1"
                data-testid="dte-exit-slider"
                class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <span class="text-sm font-medium text-gray-900 w-20 text-right">
                {{ localConfig.dte_exit.dte_threshold }} DTE
              </span>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Exit when DTE drops to {{ localConfig.dte_exit.dte_threshold }} or below
            </p>
          </div>

          <!-- Auto Close -->
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <label class="text-sm font-medium text-gray-700">Auto Close at DTE</label>
              <p class="text-xs text-gray-500 mt-0.5">
                Automatically exit when DTE threshold reached
              </p>
            </div>
            <input
              type="checkbox"
              v-model="localConfig.dte_exit.auto_close"
              @change="emitUpdate"
              data-testid="dte-exit-auto-close"
              class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
            />
          </div>

          <!-- Research Note for 21 DTE -->
          <div v-if="localConfig.dte_exit.dte_threshold === 21"
               class="research-note p-3 bg-green-50 border border-green-200 rounded-lg">
            <p class="text-xs font-medium text-green-900 mb-1">📊 Research Insight:</p>
            <p class="text-xs text-green-800">
              <strong>21 DTE exit rule</strong> captures 75-80% of max profit while avoiding expiry week gamma risk.
              Theta decay slows significantly after 21 DTE, making it optimal to exit and recycle capital.
            </p>
          </div>
        </div>
      </div>

      <div class="border-t border-gray-200"></div>

      <!-- Days in Trade Exit (#24) -->
      <div class="days-in-trade-section">
        <div class="flex items-center justify-between mb-3">
          <div>
            <label class="text-sm font-medium text-gray-700">Days in Trade Exit</label>
            <p class="text-xs text-gray-500 mt-0.5">
              Exit after holding position for X days
            </p>
          </div>
          <input
            type="checkbox"
            v-model="localConfig.days_in_trade.enabled"
            @change="emitUpdate"
            data-testid="days-in-trade-enabled"
            class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
          />
        </div>

        <div v-if="localConfig.days_in_trade.enabled" class="space-y-3">
          <!-- Days Presets -->
          <div class="preset-buttons">
            <label class="block text-sm text-gray-700 mb-2">Quick Presets</label>
            <div class="grid grid-cols-4 gap-2">
              <button
                @click="setDaysPreset(7)"
                :class="getDaysPresetClass(7)"
                data-testid="days-preset-7"
              >
                7 Days
                <span class="block text-xs opacity-75">Weekly</span>
              </button>
              <button
                @click="setDaysPreset(14)"
                :class="getDaysPresetClass(14)"
                data-testid="days-preset-14"
              >
                14 Days
                <span class="block text-xs opacity-75">Bi-weekly</span>
              </button>
              <button
                @click="setDaysPreset(30)"
                :class="getDaysPresetClass(30)"
                data-testid="days-preset-30"
              >
                30 Days
                <span class="block text-xs opacity-75">Monthly (Recommended)</span>
              </button>
              <button
                @click="setDaysPreset(45)"
                :class="getDaysPresetClass(45)"
                data-testid="days-preset-45"
              >
                45 Days
                <span class="block text-xs opacity-75">Extended</span>
              </button>
            </div>
          </div>

          <!-- Custom Days Value -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Custom Days Threshold
            </label>
            <div class="flex items-center space-x-3">
              <input
                type="range"
                v-model="localConfig.days_in_trade.max_days"
                @input="emitUpdate"
                min="1"
                max="60"
                step="1"
                data-testid="days-in-trade-slider"
                class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <span class="text-sm font-medium text-gray-900 w-20 text-right">
                {{ localConfig.days_in_trade.max_days }} Days
              </span>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Exit after holding position for {{ localConfig.days_in_trade.max_days }} days
            </p>
          </div>

          <!-- Auto Close -->
          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <label class="text-sm font-medium text-gray-700">Auto Close after Days</label>
              <p class="text-xs text-gray-500 mt-0.5">
                Automatically exit when max days reached
              </p>
            </div>
            <input
              type="checkbox"
              v-model="localConfig.days_in_trade.auto_close"
              @change="emitUpdate"
              data-testid="days-in-trade-auto-close"
              class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
            />
          </div>

          <!-- Capital Recycling Note -->
          <div class="info-note p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p class="text-xs font-medium text-blue-900 mb-1">💡 Capital Recycling:</p>
            <p class="text-xs text-blue-800">
              Setting max days in trade (typically 30 days) forces capital recycling. Even if position
              is profitable, exiting and opening a new trade can yield better annualized returns.
            </p>
          </div>
        </div>
      </div>

      <!-- Combined Example -->
      <div v-if="localConfig.dte_exit.enabled || localConfig.days_in_trade.enabled"
           class="example-box p-3 bg-purple-50 border border-purple-200 rounded-lg">
        <p class="text-xs font-medium text-purple-900 mb-2">📋 Your Exit Rules:</p>
        <ul class="text-xs text-purple-800 space-y-1">
          <li v-if="localConfig.dte_exit.enabled">
            ✓ Exit when DTE ≤ {{ localConfig.dte_exit.dte_threshold }} days
            {{ localConfig.dte_exit.auto_close ? '(Automatic)' : '(Manual Confirmation)' }}
          </li>
          <li v-if="localConfig.days_in_trade.enabled">
            ✓ Exit after {{ localConfig.days_in_trade.max_days }} days in trade
            {{ localConfig.days_in_trade.auto_close ? '(Automatic)' : '(Manual Confirmation)' }}
          </li>
          <li v-if="localConfig.dte_exit.enabled && localConfig.days_in_trade.enabled">
            ℹ️ Whichever condition hits first will trigger the exit
          </li>
        </ul>
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
      dte_exit: {
        enabled: false,
        dte_threshold: 21,
        auto_close: true
      },
      days_in_trade: {
        enabled: false,
        max_days: 30,
        auto_close: true
      }
    })
  }
})

const emit = defineEmits(['update'])

// Local state
const localConfig = ref({
  dte_exit: {
    enabled: props.config.dte_exit?.enabled ?? false,
    dte_threshold: props.config.dte_exit?.dte_threshold ?? 21,
    auto_close: props.config.dte_exit?.auto_close ?? true
  },
  days_in_trade: {
    enabled: props.config.days_in_trade?.enabled ?? false,
    max_days: props.config.days_in_trade?.max_days ?? 30,
    auto_close: props.config.days_in_trade?.auto_close ?? true
  }
})

// Watch for external config changes
watch(() => props.config, (newConfig) => {
  localConfig.value = {
    dte_exit: {
      enabled: newConfig.dte_exit?.enabled ?? false,
      dte_threshold: newConfig.dte_exit?.dte_threshold ?? 21,
      auto_close: newConfig.dte_exit?.auto_close ?? true
    },
    days_in_trade: {
      enabled: newConfig.days_in_trade?.enabled ?? false,
      max_days: newConfig.days_in_trade?.max_days ?? 30,
      auto_close: newConfig.days_in_trade?.auto_close ?? true
    }
  }
}, { deep: true })

function setDTEPreset(dte) {
  localConfig.value.dte_exit.dte_threshold = dte
  emitUpdate()
}

function setDaysPreset(days) {
  localConfig.value.days_in_trade.max_days = days
  emitUpdate()
}

function getDTEPresetClass(dte) {
  return [
    'px-3 py-2 text-sm rounded-lg border transition-colors',
    localConfig.value.dte_exit.dte_threshold === dte
      ? 'bg-blue-600 text-white border-blue-600'
      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
  ]
}

function getDaysPresetClass(days) {
  return [
    'px-3 py-2 text-sm rounded-lg border transition-colors',
    localConfig.value.days_in_trade.max_days === days
      ? 'bg-blue-600 text-white border-blue-600'
      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
  ]
}

function emitUpdate() {
  emit('update', { ...localConfig.value })
}
</script>

<style scoped>
.dte-exit-config {
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
