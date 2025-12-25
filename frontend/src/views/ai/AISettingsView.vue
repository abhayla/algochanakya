<template>
  <div class="ai-settings-view p-6" data-testid="ai-settings-view">
    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">AI Trading Configuration</h1>
      <p class="text-gray-600 mt-1">
        Configure autonomous AI trading settings, deployment schedule, and position sizing
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="text-gray-600">Loading configuration...</div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <p class="text-red-800">{{ error }}</p>
    </div>

    <!-- Configuration Form -->
    <div v-if="!loading && config" class="space-y-6">
      <!-- Autonomy Settings Panel -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="ai-autonomy-panel">
        <h2 class="text-lg font-semibold mb-4">Autonomy Settings</h2>

        <div class="space-y-4">
          <!-- AI Enabled Toggle -->
          <div class="flex items-center justify-between">
            <div>
              <label class="font-medium text-gray-900">Enable AI Trading</label>
              <p class="text-sm text-gray-600">Activate autonomous trading</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                v-model="config.ai_enabled"
                type="checkbox"
                class="sr-only peer"
                data-testid="ai-enabled-toggle"
                @change="handleConfigUpdate"
              />
              <div
                class="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"
              ></div>
            </label>
          </div>

          <!-- Autonomy Mode -->
          <div>
            <label class="block font-medium text-gray-900 mb-2">Trading Mode</label>
            <div class="flex gap-4">
              <label class="flex items-center">
                <input
                  v-model="config.autonomy_mode"
                  type="radio"
                  value="paper"
                  class="mr-2"
                  data-testid="mode-paper"
                  @change="handleConfigUpdate"
                />
                Paper Trading
              </label>
              <label class="flex items-center">
                <input
                  v-model="config.autonomy_mode"
                  type="radio"
                  value="live"
                  class="mr-2"
                  data-testid="mode-live"
                  :disabled="!canGraduateToLive"
                  @change="handleConfigUpdate"
                />
                Live Trading
                <span v-if="!canGraduateToLive" class="ml-2 text-xs text-red-600">
                  (Requires graduation)
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Deployment Schedule Panel -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="ai-deployment-panel">
        <h2 class="text-lg font-semibold mb-4">Deployment Schedule</h2>

        <div class="space-y-4">
          <!-- Auto-Deploy Toggle -->
          <div class="flex items-center justify-between">
            <label class="font-medium text-gray-900">Auto-Deploy Strategies</label>
            <input
              v-model="config.auto_deploy_enabled"
              type="checkbox"
              class="h-4 w-4"
              data-testid="auto-deploy-toggle"
              @change="handleConfigUpdate"
            />
          </div>

          <!-- Deploy Time -->
          <div>
            <label class="block font-medium text-gray-900 mb-2">Deploy Time</label>
            <input
              v-model="config.deploy_time"
              type="time"
              class="border rounded px-3 py-2"
              data-testid="deploy-time-input"
              @change="handleConfigUpdate"
            />
          </div>

          <!-- Deploy Days -->
          <div>
            <label class="block font-medium text-gray-900 mb-2">Deploy Days</label>
            <div class="flex gap-2">
              <label
                v-for="day in ['MON', 'TUE', 'WED', 'THU', 'FRI']"
                :key="day"
                class="flex items-center"
              >
                <input
                  :checked="config.deploy_days?.includes(day)"
                  type="checkbox"
                  class="mr-1"
                  :data-testid="`deploy-day-${day.toLowerCase()}`"
                  @change="toggleDeployDay(day)"
                />
                {{ day }}
              </label>
            </div>
          </div>

          <!-- Skip Options -->
          <div class="space-y-2">
            <label class="flex items-center">
              <input
                v-model="config.skip_event_days"
                type="checkbox"
                class="mr-2"
                data-testid="skip-event-days"
                @change="handleConfigUpdate"
              />
              Skip event days (Budget, RBI, etc.)
            </label>
            <label class="flex items-center">
              <input
                v-model="config.skip_weekly_expiry"
                type="checkbox"
                class="mr-2"
                data-testid="skip-weekly-expiry"
                @change="handleConfigUpdate"
              />
              Skip weekly expiry (Thursday)
            </label>
          </div>
        </div>
      </div>

      <!-- Position Sizing Panel -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="ai-sizing-panel">
        <h2 class="text-lg font-semibold mb-4">Position Sizing</h2>

        <div class="space-y-4">
          <!-- Sizing Mode -->
          <div>
            <label class="block font-medium text-gray-900 mb-2">Sizing Mode</label>
            <select
              v-model="config.sizing_mode"
              class="border rounded px-3 py-2 w-full"
              data-testid="sizing-mode-select"
              @change="handleConfigUpdate"
            >
              <option value="fixed">Fixed</option>
              <option value="tiered">Tiered (Confidence-based)</option>
              <option value="kelly">Kelly Criterion (Week 9)</option>
            </select>
          </div>

          <!-- Base Lots -->
          <div>
            <label class="block font-medium text-gray-900 mb-2">Base Lots</label>
            <input
              v-model.number="config.base_lots"
              type="number"
              min="1"
              class="border rounded px-3 py-2 w-full"
              data-testid="base-lots-input"
              @change="handleConfigUpdate"
            />
          </div>

          <!-- Confidence Tiers (simplified display) -->
          <div v-if="config.sizing_mode === 'tiered'">
            <label class="block font-medium text-gray-900 mb-2">Confidence Tiers</label>
            <div class="text-sm text-gray-600 space-y-1">
              <div v-for="(tier, index) in config.confidence_tiers" :key="index">
                {{ tier.name }}: {{ tier.min }}-{{ tier.max }}% = {{ tier.multiplier }}x lots
              </div>
            </div>
            <p class="text-xs text-gray-500 mt-2">
              (Advanced tier editing in Phase 3)
            </p>
          </div>
        </div>
      </div>

      <!-- Limits Panel -->
      <div class="bg-white rounded-lg shadow p-6" data-testid="ai-limits-panel">
        <h2 class="text-lg font-semibold mb-4">Trading Limits</h2>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block font-medium text-gray-900 mb-2">Max Lots/Strategy</label>
            <input
              v-model.number="config.max_lots_per_strategy"
              type="number"
              min="1"
              class="border rounded px-3 py-2 w-full"
              data-testid="max-lots-strategy-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="block font-medium text-gray-900 mb-2">Max Lots/Day</label>
            <input
              v-model.number="config.max_lots_per_day"
              type="number"
              min="1"
              class="border rounded px-3 py-2 w-full"
              data-testid="max-lots-day-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="block font-medium text-gray-900 mb-2">Max Strategies/Day</label>
            <input
              v-model.number="config.max_strategies_per_day"
              type="number"
              min="1"
              class="border rounded px-3 py-2 w-full"
              data-testid="max-strategies-day-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="block font-medium text-gray-900 mb-2">Min Confidence (%)</label>
            <input
              v-model.number="config.min_confidence_to_trade"
              type="number"
              min="0"
              max="100"
              class="border rounded px-3 py-2 w-full"
              data-testid="min-confidence-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="block font-medium text-gray-900 mb-2">Max VIX</label>
            <input
              v-model.number="config.max_vix_to_trade"
              type="number"
              min="0"
              step="0.1"
              class="border rounded px-3 py-2 w-full"
              data-testid="max-vix-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="block font-medium text-gray-900 mb-2">Weekly Loss Limit (₹)</label>
            <input
              v-model.number="config.weekly_loss_limit"
              type="number"
              min="0"
              step="1000"
              class="border rounded px-3 py-2 w-full"
              data-testid="weekly-loss-limit-input"
              @change="handleConfigUpdate"
            />
          </div>
        </div>
      </div>

      <!-- Save Button -->
      <div class="flex justify-end gap-4">
        <button
          class="px-6 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          data-testid="reset-button"
          @click="resetToDefaults"
        >
          Reset to Defaults
        </button>
        <button
          :disabled="saving"
          class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          data-testid="save-button"
          @click="saveConfiguration"
        >
          {{ saving ? 'Saving...' : 'Save Configuration' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAIConfigStore } from '@/stores/aiConfig'
import { storeToRefs } from 'pinia'

const aiConfigStore = useAIConfigStore()
const { config, loading, saving, error, canGraduateToLive } = storeToRefs(aiConfigStore)

// Load configuration on mount
onMounted(async () => {
  try {
    await aiConfigStore.fetchConfig()
  } catch (err) {
    console.error('Failed to load AI configuration:', err)
  }
})

// Toggle deploy day
function toggleDeployDay(day) {
  if (!config.value.deploy_days) {
    config.value.deploy_days = []
  }

  const index = config.value.deploy_days.indexOf(day)
  if (index > -1) {
    config.value.deploy_days.splice(index, 1)
  } else {
    config.value.deploy_days.push(day)
  }

  handleConfigUpdate()
}

// Handle configuration updates (debounced auto-save)
let saveTimeout = null
function handleConfigUpdate() {
  // Clear existing timeout
  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }

  // Set new timeout for auto-save (2 seconds)
  saveTimeout = setTimeout(() => {
    saveConfiguration()
  }, 2000)
}

// Save configuration
async function saveConfiguration() {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
    saveTimeout = null
  }

  try {
    await aiConfigStore.saveConfig(config.value)
    console.log('Configuration saved successfully')
  } catch (err) {
    console.error('Failed to save configuration:', err)
  }
}

// Reset to defaults
async function resetToDefaults() {
  if (confirm('Are you sure you want to reset all settings to defaults?')) {
    try {
      await aiConfigStore.resetToDefaults()
    } catch (err) {
      console.error('Failed to reset configuration:', err)
    }
  }
}
</script>

<style scoped>
/* Toggle switch styling handled by Tailwind classes */
</style>
