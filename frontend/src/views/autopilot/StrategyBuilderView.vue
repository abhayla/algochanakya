<script setup>
/**
 * AutoPilot Strategy Builder View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 2
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'

const router = useRouter()
const route = useRoute()
const store = useAutopilotStore()

const isEditMode = computed(() => !!route.params.id)
const strategyId = computed(() => route.params.id ? parseInt(route.params.id) : null)

const steps = [
  { id: 1, name: 'Basic Info', description: 'Strategy name and underlying' },
  { id: 2, name: 'Strategy Legs', description: 'Configure option legs' },
  { id: 3, name: 'Entry Conditions', description: 'When to enter' },
  { id: 4, name: 'Adjustments', description: 'Adjustment rules' },
  { id: 5, name: 'Risk Settings', description: 'Stop loss and targets' },
  { id: 6, name: 'Review', description: 'Review and save' }
]

const underlyings = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']
const expiryTypes = [
  { value: 'current_week', label: 'Current Week' },
  { value: 'next_week', label: 'Next Week' },
  { value: 'monthly', label: 'Monthly' }
]
const positionTypes = [
  { value: 'intraday', label: 'Intraday' },
  { value: 'positional', label: 'Positional' }
]

onMounted(async () => {
  if (strategyId.value) {
    const strategy = await store.fetchStrategy(strategyId.value)
    store.initBuilder(strategy)
  } else {
    store.initBuilder()
  }
})

const nextStep = () => {
  if (store.builder.step < steps.length) {
    store.setBuilderStep(store.builder.step + 1)
  }
}

const prevStep = () => {
  if (store.builder.step > 1) {
    store.setBuilderStep(store.builder.step - 1)
  }
}

const goToStep = (step) => {
  store.setBuilderStep(step)
}

const addLeg = () => {
  store.addLeg({
    contract_type: 'CE',
    transaction_type: 'SELL',
    strike_selection: { mode: 'atm_offset', offset: 0 },
    quantity_multiplier: 1,
    execution_order: store.builder.strategy.legs_config.length + 1
  })
}

const removeLeg = (index) => {
  store.removeLeg(index)
}

const addCondition = () => {
  store.addCondition({
    variable: 'TIME.CURRENT',
    operator: 'greater_than',
    value: '09:20'
  })
}

const removeCondition = (index) => {
  store.removeCondition(index)
}

const handleSave = async () => {
  try {
    const strategyData = {
      ...store.builder.strategy,
      legs_config: store.builder.strategy.legs_config.map(leg => ({
        ...leg,
        strike_selection: typeof leg.strike_selection === 'object'
          ? leg.strike_selection
          : { mode: 'atm_offset', offset: 0 }
      }))
    }

    if (isEditMode.value) {
      await store.updateStrategy(strategyId.value, strategyData)
    } else {
      const created = await store.createStrategy(strategyData)
      router.push(`/autopilot/strategies/${created.id}`)
      return
    }

    router.push('/autopilot')
  } catch (error) {
    console.error('Failed to save strategy:', error)
  }
}

const handleActivate = async () => {
  if (!isEditMode.value) {
    // Save first
    const created = await store.createStrategy(store.builder.strategy)
    await store.activateStrategy(created.id)
    router.push(`/autopilot/strategies/${created.id}`)
  } else {
    await store.activateStrategy(strategyId.value)
    router.push(`/autopilot/strategies/${strategyId.value}`)
  }
}

const canProceed = computed(() => {
  const s = store.builder.strategy
  switch (store.builder.step) {
    case 1:
      return s.name?.trim().length > 0 && s.underlying && s.lots > 0
    case 2:
      return s.legs_config.length > 0
    case 3:
      return true // Entry conditions are optional
    case 4:
      return true // Adjustments are optional
    case 5:
      return true // Risk settings are optional
    default:
      return true
  }
})
</script>

<template>
  <div class="p-6" data-testid="autopilot-strategy-builder">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">
          {{ isEditMode ? 'Edit Strategy' : 'Create Strategy' }}
        </h1>
        <p class="text-gray-500 mt-1">Configure your automated trading strategy</p>
      </div>
      <button
        @click="router.push('/autopilot')"
        class="text-gray-500 hover:text-gray-700"
        data-testid="autopilot-builder-close"
      >
        Cancel
      </button>
    </div>

    <!-- Progress Steps -->
    <div class="mb-8" data-testid="autopilot-builder-steps">
      <div class="flex justify-between">
        <div
          v-for="step in steps"
          :key="step.id"
          class="flex-1 relative"
          :class="{ 'cursor-pointer': step.id <= store.builder.step }"
          @click="step.id <= store.builder.step && goToStep(step.id)"
        >
          <div class="flex items-center">
            <div
              :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                step.id === store.builder.step ? 'bg-blue-600 text-white' :
                step.id < store.builder.step ? 'bg-green-500 text-white' :
                'bg-gray-200 text-gray-600'
              ]"
            >
              {{ step.id }}
            </div>
            <div class="ml-2 hidden md:block">
              <p class="text-sm font-medium text-gray-900">{{ step.name }}</p>
            </div>
          </div>
          <div
            v-if="step.id < steps.length"
            class="absolute top-4 left-8 w-full h-0.5 bg-gray-200"
            :class="{ 'bg-green-500': step.id < store.builder.step }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Step Content -->
    <div class="bg-white rounded-lg shadow p-6">
      <!-- Step 1: Basic Info -->
      <div v-if="store.builder.step === 1" data-testid="autopilot-builder-step-1">
        <h2 class="text-lg font-semibold mb-4">Basic Information</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Strategy Name *</label>
            <input
              type="text"
              v-model="store.builder.strategy.name"
              data-testid="autopilot-builder-name"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., Iron Condor Weekly"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              v-model="store.builder.strategy.description"
              data-testid="autopilot-builder-description"
              rows="2"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="Optional description"
            ></textarea>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Underlying *</label>
              <select
                v-model="store.builder.strategy.underlying"
                data-testid="autopilot-builder-underlying"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              >
                <option v-for="u in underlyings" :key="u" :value="u">{{ u }}</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Expiry Type</label>
              <select
                v-model="store.builder.strategy.expiry_type"
                data-testid="autopilot-builder-expiry-type"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              >
                <option v-for="e in expiryTypes" :key="e.value" :value="e.value">{{ e.label }}</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Lots *</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.lots"
                data-testid="autopilot-builder-lots"
                min="1"
                max="50"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Position Type</label>
              <select
                v-model="store.builder.strategy.position_type"
                data-testid="autopilot-builder-position-type"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              >
                <option v-for="p in positionTypes" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: Strategy Legs -->
      <div v-if="store.builder.step === 2" data-testid="autopilot-builder-step-2">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">Strategy Legs</h2>
          <button
            @click="addLeg"
            data-testid="autopilot-builder-add-leg"
            class="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            + Add Leg
          </button>
        </div>

        <div v-if="store.builder.strategy.legs_config.length === 0" class="text-center py-8 text-gray-500">
          No legs added yet. Click "Add Leg" to start.
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="(leg, index) in store.builder.strategy.legs_config"
            :key="leg.id"
            class="border border-gray-200 rounded-lg p-4"
            :data-testid="`autopilot-builder-leg-${index}`"
          >
            <div class="flex justify-between items-start mb-3">
              <span class="font-medium">Leg {{ index + 1 }}</span>
              <button
                @click="removeLeg(index)"
                class="text-red-500 hover:text-red-700 text-sm"
              >
                Remove
              </button>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label class="block text-xs text-gray-500 mb-1">Type</label>
                <select
                  v-model="leg.contract_type"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                >
                  <option value="CE">CE</option>
                  <option value="PE">PE</option>
                </select>
              </div>

              <div>
                <label class="block text-xs text-gray-500 mb-1">Action</label>
                <select
                  v-model="leg.transaction_type"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>

              <div>
                <label class="block text-xs text-gray-500 mb-1">Strike Selection</label>
                <select
                  v-model="leg.strike_selection.mode"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                >
                  <option value="atm_offset">ATM Offset</option>
                  <option value="fixed">Fixed Strike</option>
                  <option value="premium_based">Premium Based</option>
                </select>
              </div>

              <div v-if="leg.strike_selection.mode === 'atm_offset'">
                <label class="block text-xs text-gray-500 mb-1">Offset</label>
                <input
                  type="number"
                  v-model.number="leg.strike_selection.offset"
                  step="50"
                  class="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: Entry Conditions -->
      <div v-if="store.builder.step === 3" data-testid="autopilot-builder-step-3">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">Entry Conditions</h2>
          <button
            @click="addCondition"
            data-testid="autopilot-builder-add-condition"
            class="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            + Add Condition
          </button>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Condition Logic</label>
          <select
            v-model="store.builder.strategy.entry_conditions.logic"
            class="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value="AND">ALL conditions must be true (AND)</option>
            <option value="OR">ANY condition can be true (OR)</option>
          </select>
        </div>

        <div v-if="store.builder.strategy.entry_conditions.conditions.length === 0" class="text-center py-8 text-gray-500">
          No conditions added. The strategy will enter immediately when activated.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="(condition, index) in store.builder.strategy.entry_conditions.conditions"
            :key="condition.id"
            class="border border-gray-200 rounded-lg p-3"
          >
            <div class="flex justify-between items-center mb-2">
              <span class="text-sm font-medium">Condition {{ index + 1 }}</span>
              <button
                @click="removeCondition(index)"
                class="text-red-500 hover:text-red-700 text-sm"
              >
                Remove
              </button>
            </div>

            <div class="grid grid-cols-3 gap-3">
              <select
                v-model="condition.variable"
                class="px-2 py-1 text-sm border border-gray-300 rounded"
              >
                <option value="TIME.CURRENT">Time</option>
                <option value="SPOT.PRICE">Spot Price</option>
                <option value="VOLATILITY.VIX">India VIX</option>
                <option value="STRATEGY.PNL">Strategy P&L</option>
              </select>

              <select
                v-model="condition.operator"
                class="px-2 py-1 text-sm border border-gray-300 rounded"
              >
                <option value="greater_than">Greater Than</option>
                <option value="less_than">Less Than</option>
                <option value="equals">Equals</option>
                <option value="between">Between</option>
              </select>

              <input
                v-model="condition.value"
                class="px-2 py-1 text-sm border border-gray-300 rounded"
                placeholder="Value"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: Adjustments (Simplified) -->
      <div v-if="store.builder.step === 4" data-testid="autopilot-builder-step-4">
        <h2 class="text-lg font-semibold mb-4">Adjustment Rules</h2>
        <div class="text-center py-8 text-gray-500">
          <p>Adjustment rules configuration coming soon.</p>
          <p class="text-sm mt-2">You can add stop-loss and target rules in the Risk Settings step.</p>
        </div>
      </div>

      <!-- Step 5: Risk Settings -->
      <div v-if="store.builder.step === 5" data-testid="autopilot-builder-step-5">
        <h2 class="text-lg font-semibold mb-4">Risk Settings</h2>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Max Loss (₹)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_loss"
                data-testid="autopilot-builder-max-loss"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="e.g., 5000"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Max Loss (%)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_loss_pct"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="e.g., 50"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Max Margin (₹)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_margin"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="e.g., 100000"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Time Stop</label>
              <input
                type="time"
                v-model="store.builder.strategy.risk_settings.time_stop"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>

          <div class="border-t pt-4 mt-4">
            <label class="flex items-center">
              <input
                type="checkbox"
                v-model="store.builder.strategy.risk_settings.trailing_stop.enabled"
                class="rounded border-gray-300 text-blue-600"
              />
              <span class="ml-2 text-sm text-gray-700">Enable Trailing Stop</span>
            </label>

            <div
              v-if="store.builder.strategy.risk_settings.trailing_stop.enabled"
              class="grid grid-cols-2 gap-4 mt-3"
            >
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Trigger Profit (₹)</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.risk_settings.trailing_stop.trigger_profit"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Trail Amount (₹)</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.risk_settings.trailing_stop.trail_amount"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 6: Review -->
      <div v-if="store.builder.step === 6" data-testid="autopilot-builder-step-6">
        <h2 class="text-lg font-semibold mb-4">Review Strategy</h2>

        <div class="space-y-4">
          <div class="bg-gray-50 rounded-lg p-4">
            <h3 class="font-medium mb-2">Basic Info</h3>
            <dl class="grid grid-cols-2 gap-2 text-sm">
              <dt class="text-gray-500">Name:</dt>
              <dd>{{ store.builder.strategy.name }}</dd>
              <dt class="text-gray-500">Underlying:</dt>
              <dd>{{ store.builder.strategy.underlying }}</dd>
              <dt class="text-gray-500">Lots:</dt>
              <dd>{{ store.builder.strategy.lots }}</dd>
              <dt class="text-gray-500">Position Type:</dt>
              <dd>{{ store.builder.strategy.position_type }}</dd>
            </dl>
          </div>

          <div class="bg-gray-50 rounded-lg p-4">
            <h3 class="font-medium mb-2">Legs ({{ store.builder.strategy.legs_config.length }})</h3>
            <div v-for="(leg, index) in store.builder.strategy.legs_config" :key="leg.id" class="text-sm">
              Leg {{ index + 1 }}: {{ leg.transaction_type }} {{ leg.contract_type }}
              <span v-if="leg.strike_selection?.mode === 'atm_offset'">
                (ATM {{ leg.strike_selection.offset >= 0 ? '+' : '' }}{{ leg.strike_selection.offset }})
              </span>
            </div>
          </div>

          <div class="bg-gray-50 rounded-lg p-4">
            <h3 class="font-medium mb-2">Entry Conditions</h3>
            <p class="text-sm text-gray-600">
              {{ store.builder.strategy.entry_conditions.conditions.length }} condition(s) with
              {{ store.builder.strategy.entry_conditions.logic }} logic
            </p>
          </div>
        </div>
      </div>

      <!-- Navigation Buttons -->
      <div class="flex justify-between mt-6 pt-4 border-t">
        <button
          v-if="store.builder.step > 1"
          @click="prevStep"
          data-testid="autopilot-builder-prev"
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
        >
          Previous
        </button>
        <div v-else></div>

        <div class="flex gap-2">
          <button
            v-if="store.builder.step === steps.length"
            @click="handleSave"
            :disabled="store.saving"
            data-testid="autopilot-builder-save"
            class="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50"
          >
            {{ store.saving ? 'Saving...' : 'Save as Draft' }}
          </button>

          <button
            v-if="store.builder.step === steps.length"
            @click="handleActivate"
            :disabled="store.saving"
            data-testid="autopilot-builder-activate"
            class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {{ store.saving ? 'Activating...' : 'Save & Activate' }}
          </button>

          <button
            v-if="store.builder.step < steps.length"
            @click="nextStep"
            :disabled="!canProceed"
            data-testid="autopilot-builder-next"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="store.error" class="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-red-800">{{ store.error }}</p>
    </div>
  </div>
</template>
