<script setup>
/**
 * AutoPilot Settings View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 4
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'

const router = useRouter()
const store = useAutopilotStore()

const localSettings = ref(null)
const hasChanges = ref(false)

onMounted(async () => {
  await store.fetchSettings()
  localSettings.value = { ...store.settings }
})

const handleChange = () => {
  hasChanges.value = true
}

const handleSave = async () => {
  try {
    await store.updateSettings(localSettings.value)
    hasChanges.value = false
  } catch (error) {
    console.error('Failed to save settings:', error)
  }
}

const handleReset = () => {
  localSettings.value = { ...store.settings }
  hasChanges.value = false
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}
</script>

<template>
  <div class="p-6" data-testid="autopilot-settings">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <div class="flex items-center gap-3">
          <button
            @click="router.push('/autopilot')"
            class="text-gray-500 hover:text-gray-700"
          >
            &larr;
          </button>
          <h1 class="text-2xl font-bold text-gray-900">AutoPilot Settings</h1>
        </div>
        <p class="text-gray-500 mt-1">Configure global settings for automated trading</p>
      </div>

      <div class="flex gap-2">
        <button
          v-if="hasChanges"
          @click="handleReset"
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
        >
          Reset
        </button>
        <button
          @click="handleSave"
          :disabled="!hasChanges || store.saving"
          data-testid="autopilot-settings-save"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ store.saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading && !localSettings" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-500">Loading settings...</p>
    </div>

    <!-- Settings Form -->
    <div v-else-if="localSettings" class="space-y-6">
      <!-- Risk Limits -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="autopilot-settings-risk">
        <h2 class="text-lg font-semibold mb-4">Risk Limits</h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Daily Loss Limit (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.daily_loss_limit"
              @input="handleChange"
              data-testid="autopilot-settings-daily-loss"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Maximum loss allowed per day. AutoPilot will stop all strategies if breached.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Per Strategy Loss Limit (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.per_strategy_loss_limit"
              @input="handleChange"
              data-testid="autopilot-settings-strategy-loss"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Maximum loss per individual strategy.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Max Capital Deployed (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.max_capital_deployed"
              @input="handleChange"
              data-testid="autopilot-settings-max-capital"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Maximum margin/capital that can be used across all strategies.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Max Active Strategies</label>
            <input
              type="number"
              v-model.number="localSettings.max_active_strategies"
              @input="handleChange"
              min="1"
              max="10"
              data-testid="autopilot-settings-max-strategies"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Maximum number of strategies that can be active at once (1-10).</p>
          </div>
        </div>
      </div>

      <!-- Time Restrictions -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="autopilot-settings-time">
        <h2 class="text-lg font-semibold mb-4">Time Restrictions</h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">No Trade First Minutes</label>
            <input
              type="number"
              v-model.number="localSettings.no_trade_first_minutes"
              @input="handleChange"
              min="0"
              max="60"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Don't enter trades during first N minutes of market open.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">No Trade Last Minutes</label>
            <input
              type="number"
              v-model.number="localSettings.no_trade_last_minutes"
              @input="handleChange"
              min="0"
              max="60"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Don't enter trades during last N minutes before market close.</p>
          </div>
        </div>
      </div>

      <!-- Cooldown Settings -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="autopilot-settings-cooldown">
        <h2 class="text-lg font-semibold mb-4">Cooldown Settings</h2>

        <div class="mb-4">
          <label class="flex items-center">
            <input
              type="checkbox"
              v-model="localSettings.cooldown_after_loss"
              @change="handleChange"
              class="rounded border-gray-300 text-blue-600"
            />
            <span class="ml-2 text-sm text-gray-700">Enable cooldown after significant loss</span>
          </label>
        </div>

        <div v-if="localSettings.cooldown_after_loss" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Cooldown Duration (minutes)</label>
            <input
              type="number"
              v-model.number="localSettings.cooldown_minutes"
              @input="handleChange"
              min="5"
              max="240"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Cooldown Threshold (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.cooldown_threshold"
              @input="handleChange"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="text-xs text-gray-500 mt-1">Trigger cooldown if loss exceeds this amount.</p>
          </div>
        </div>
      </div>

      <!-- Feature Flags -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="autopilot-settings-features">
        <h2 class="text-lg font-semibold mb-4">Features</h2>

        <div class="space-y-4">
          <label class="flex items-center">
            <input
              type="checkbox"
              v-model="localSettings.paper_trading_mode"
              @change="handleChange"
              data-testid="autopilot-settings-paper-trading"
              class="rounded border-gray-300 text-blue-600"
            />
            <span class="ml-2 text-sm text-gray-700">Paper Trading Mode</span>
          </label>
          <p class="text-xs text-gray-500 ml-6">Simulate trades without placing real orders. Great for testing strategies.</p>

          <label class="flex items-center">
            <input
              type="checkbox"
              v-model="localSettings.show_advanced_features"
              @change="handleChange"
              class="rounded border-gray-300 text-blue-600"
            />
            <span class="ml-2 text-sm text-gray-700">Show Advanced Features</span>
          </label>
          <p class="text-xs text-gray-500 ml-6">Enable advanced configuration options and detailed analytics.</p>
        </div>
      </div>

      <!-- Current Values Summary -->
      <div class="bg-blue-50 rounded-lg p-4">
        <h3 class="font-medium text-blue-900 mb-2">Current Limits Summary</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p class="text-blue-700">Daily Loss Limit</p>
            <p class="font-medium text-blue-900">{{ formatCurrency(localSettings.daily_loss_limit) }}</p>
          </div>
          <div>
            <p class="text-blue-700">Max Capital</p>
            <p class="font-medium text-blue-900">{{ formatCurrency(localSettings.max_capital_deployed) }}</p>
          </div>
          <div>
            <p class="text-blue-700">Max Strategies</p>
            <p class="font-medium text-blue-900">{{ localSettings.max_active_strategies }}</p>
          </div>
          <div>
            <p class="text-blue-700">Mode</p>
            <p class="font-medium text-blue-900">{{ localSettings.paper_trading_mode ? 'Paper Trading' : 'Live Trading' }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-red-800">{{ store.error }}</p>
      <button @click="store.clearError" class="text-red-600 underline mt-2">Dismiss</button>
    </div>
  </div>
</template>
