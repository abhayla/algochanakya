<script setup>
/**
 * AutoPilot Strategy Builder View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 2
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import { useStrategyTypes } from '@/constants/strategyTypes'
import AutoPilotLegsTable from '@/components/autopilot/builder/AutoPilotLegsTable.vue'
import ProfitTargetConfig from '@/components/autopilot/builder/ProfitTargetConfig.vue'
import DTEExitConfig from '@/components/autopilot/builder/DTEExitConfig.vue'
import StagedEntryConfig from '@/components/autopilot/builder/StagedEntryConfig.vue'
import ReentryConfig from '@/components/autopilot/builder/ReentryConfig.vue'
import AdjustmentRuleBuilder from '@/components/autopilot/builder/AdjustmentRuleBuilder.vue'
import ConversionModal from '@/components/autopilot/adjustments/ConversionModal.vue'
import RollWizard from '@/components/autopilot/adjustments/RollWizard.vue'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const route = useRoute()
const store = useAutopilotStore()

// Strategy Types from centralized constants
const {
  strategyTypes,
  categories,
  strategiesByCategory,
  loadStrategyTypes,
  getStrategyLegs
} = useStrategyTypes()

// Selected strategy type for auto-populating legs
const selectedStrategyType = ref('')
const previousStrategyType = ref('')
const showReplaceConfirm = ref(false)

// Adjustment modals
const showConversionModal = ref(false)
const showWidenSpreadModal = ref(false)
const showRollWizard = ref(false)

const isEditMode = computed(() => !!route.params.id)
const strategyId = computed(() => route.params.id ? parseInt(route.params.id) : null)

// Validation errors
const validationErrors = ref([])

const steps = [
  { id: 1, name: 'Strategy Setup', description: 'Basic info and legs' },
  { id: 2, name: 'Entry Conditions', description: 'When to enter' },
  { id: 3, name: 'Monitoring', description: 'Alerts and adjustments' },
  { id: 4, name: 'Risk Settings', description: 'Stop loss and targets' },
  { id: 5, name: 'Review', description: 'Review and save' }
]

// Collapsible section state
const basicInfoExpanded = ref(true)

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
  // Load strategy types from backend
  await loadStrategyTypes()

  if (strategyId.value) {
    const strategy = await store.fetchStrategy(strategyId.value)
    store.initBuilder(strategy)
    // Set strategy type if it was saved
    if (strategy?.strategy_type) {
      selectedStrategyType.value = strategy.strategy_type
      previousStrategyType.value = strategy.strategy_type
    }
  } else {
    store.initBuilder()
  }
})

// Handle strategy type change - auto-populate legs
const onStrategyTypeChange = async () => {
  const newType = selectedStrategyType.value

  // If custom or empty, don't auto-populate
  if (!newType || newType === 'custom') {
    store.builder.strategy.strategy_type = newType
    previousStrategyType.value = newType
    return
  }

  // Check if legs exist - show confirmation if so
  if (store.builder.strategy.legs_config.length > 0) {
    showReplaceConfirm.value = true
    return
  }

  // No existing legs - auto-populate directly
  applyStrategyTypeLegs(newType)
}

// Apply legs from strategy type
const applyStrategyTypeLegs = (strategyTypeKey) => {
  const legs = getStrategyLegs(strategyTypeKey)
  if (!legs || legs.length === 0) return

  // Clear existing legs and add new ones from template
  store.builder.strategy.legs_config = legs.map((leg, index) => ({
    id: `leg_${Date.now()}_${index}`,
    transaction_type: leg.action, // BUY or SELL
    contract_type: leg.type, // CE or PE
    strike_selection: {
      mode: 'atm_offset',
      offset: leg.strike_offset || 0
    },
    strike_price: null, // Will be calculated based on spot
    expiry_date: null, // Will use expiry_type
    lots: store.builder.strategy.lots || 1,
    entry_price: null,
    target_price: null,
    stop_loss_price: null,
    trailing_stop: false
  }))

  store.builder.strategy.strategy_type = strategyTypeKey
  previousStrategyType.value = strategyTypeKey
  showReplaceConfirm.value = false
}

// Confirm replace legs
const confirmReplaceLegs = () => {
  applyStrategyTypeLegs(selectedStrategyType.value)
}

// Cancel replace legs - revert selection
const cancelReplaceLegs = () => {
  selectedStrategyType.value = previousStrategyType.value
  showReplaceConfirm.value = false
}

// Validate current step
const validateStep = () => {
  validationErrors.value = []
  const s = store.builder.strategy

  switch (store.builder.step) {
    case 1:
      // Step 1 now includes both Basic Info and Strategy Legs (merged)
      if (!s.name?.trim()) {
        validationErrors.value.push({ field: 'name', message: 'Strategy name is required' })
      }
      if (!s.underlying) {
        validationErrors.value.push({ field: 'underlying', message: 'Underlying is required' })
      }
      if (!s.lots || s.lots <= 0) {
        validationErrors.value.push({ field: 'lots', message: 'Lots must be greater than 0' })
      }
      if (s.legs_config.length === 0) {
        validationErrors.value.push({ field: 'legs', message: 'At least one leg is required' })
      } else {
        // Validate each leg has required fields
        s.legs_config.forEach((leg, idx) => {
          if (!leg.expiry_date) {
            validationErrors.value.push({ field: `leg_${idx}_expiry`, message: `Leg ${idx + 1}: Expiry is required` })
          }
          if (!leg.strike_price) {
            validationErrors.value.push({ field: `leg_${idx}_strike`, message: `Leg ${idx + 1}: Strike is required` })
          }
        })
      }
      break
    case 4:
      // Risk Settings (was step 5)
      if (s.risk_settings.max_loss !== null && s.risk_settings.max_loss < 0) {
        validationErrors.value.push({ field: 'max_loss', message: 'Max loss cannot be negative' })
      }
      break
  }

  return validationErrors.value.length === 0
}

const nextStep = () => {
  if (!validateStep()) {
    return // Show validation errors, don't proceed
  }
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

const getStepTestId = (stepId) => {
  const stepNames = {
    1: 'autopilot-builder-legs-tab',
    2: 'autopilot-builder-conditions-tab',
    3: 'autopilot-builder-monitoring-tab',  // Was adjustments, now monitoring/adjustments
    4: 'autopilot-builder-settings-tab',  // Also aliased as risk-tab for backward compatibility
    5: 'autopilot-builder-review-tab'
  }
  return stepNames[stepId] || `autopilot-builder-step-${stepId}`
}

// Note: addLeg and removeLeg are now handled by AutoPilotLegsTable component

const addCondition = () => {
  store.addCondition({
    variable: 'TIME.CURRENT',
    operator: 'greater_than',
    value: '09:20'
  })
}

// Condition order suggestion state
const conditionSuggestionDismissed = ref(false)

// Show condition order suggestion when conditions are not in optimal order
const showConditionOrderSuggestion = computed(() => {
  if (conditionSuggestionDismissed.value) return false
  const conditions = store.builder.strategy.entry_conditions.conditions
  if (conditions.length < 2) return false

  // Check if conditions are in optimal order: TIME → VIX → SPOT → PREMIUM
  const orderPriority = {
    'TIME.CURRENT': 1,
    'STRATEGY.DTE': 1,
    'STRATEGY.DAYS_IN_TRADE': 1,
    'VOLATILITY.VIX': 2,
    'IV.RANK': 2,
    'IV.PERCENTILE': 2,
    'SPOT.PRICE': 3,
    'SPOT.DISTANCE_TO.BREAKEVEN': 3,
    'OI.PCR': 3,
    'OI.MAX_PAIN': 3,
    'PREMIUM.CAPTURED_PCT': 4,
    'STRATEGY.PNL': 4
  }

  let lastPriority = 0
  for (const condition of conditions) {
    const priority = orderPriority[condition.variable] || 3
    if (priority < lastPriority) {
      return true  // Order is not optimal
    }
    lastPriority = priority
  }
  return false
})

const dismissConditionSuggestion = () => {
  conditionSuggestionDismissed.value = true
}

// Add condition group (placeholder for nested groups feature)
const addConditionGroup = () => {
  // For now, just add a new condition
  // In full implementation, this would create a new condition group
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

// Phase 5D: Update exit rule configurations
const updateExitRuleConfig = (ruleType, config) => {
  if (!store.builder.strategy.exit_rules) {
    store.builder.strategy.exit_rules = {}
  }
  store.builder.strategy.exit_rules[ruleType] = config
}

// Scroll to section within Step 4 (Risk Settings)
const scrollToSection = (sectionId) => {
  const sectionMap = {
    'entry-requirements': 'autopilot-builder-entry-requirements',
    'risk-settings': 'autopilot-builder-risk',
    'exit-rules': 'autopilot-builder-exit-rules',
    'schedule-settings': 'autopilot-builder-schedule'
  }
  const testId = sectionMap[sectionId]
  if (testId) {
    const element = document.querySelector(`[data-testid="${testId}"]`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
}

// Available legs for staged entry configuration
const availableLegsForStaging = computed(() => {
  return store.builder.strategy.legs_config.map((leg, index) => ({
    id: leg.id || `leg_${index + 1}`,
    label: `${leg.contract_type} ${leg.strike_price} ${leg.transaction_type} (${leg.lots} lots)`
  }))
})

const canProceed = computed(() => {
  const s = store.builder.strategy
  switch (store.builder.step) {
    case 1:
      // Step 1 now includes Basic Info + Strategy Legs (merged)
      return s.name?.trim().length > 0 && s.underlying && s.lots > 0 &&
        s.legs_config.length > 0 &&
        s.legs_config.every(leg => leg.expiry_date && leg.strike_price)
    case 2:
      return true // Entry conditions are optional
    case 3:
      return true // Adjustments are optional
    case 4:
      return true // Risk settings are optional
    default:
      return true
  }
})
</script>

<template>
  <KiteLayout>
  <div class="autopilot-builder" data-testid="autopilot-strategy-builder">
    <!-- Header -->
    <div class="builder-header">
      <div>
        <h1 class="builder-title">
          {{ isEditMode ? 'Edit Strategy' : 'Create Strategy' }}
        </h1>
        <p class="builder-subtitle">Configure your automated trading strategy</p>
      </div>
      <div class="builder-header-right">
        <span data-testid="autopilot-builder-step" class="step-indicator-text">
          Step {{ store.builder.step }} of {{ steps.length }}
        </span>
        <button
          @click="router.push('/autopilot')"
          class="strategy-btn strategy-btn-outline"
          data-testid="autopilot-builder-cancel"
        >
          Cancel
        </button>
      </div>
    </div>

    <!-- Progress Steps -->
    <div class="step-progress" data-testid="autopilot-builder-steps">
      <div class="step-progress-track">
        <div
          v-for="step in steps"
          :key="step.id"
          class="step-item step-clickable"
          @click="goToStep(step.id)"
          :data-testid="getStepTestId(step.id)"
        >
          <div class="step-content">
            <div
              :class="[
                'step-circle',
                step.id === store.builder.step ? 'step-active' :
                step.id < store.builder.step ? 'step-completed' :
                'step-pending'
              ]"
            >
              {{ step.id }}
            </div>
            <div class="step-label">
              <p class="step-name">{{ step.name }}</p>
            </div>
          </div>
          <div
            v-if="step.id < steps.length"
            class="step-connector"
            :class="{ 'step-connector-active': step.id < store.builder.step }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Step Content -->
    <div class="strategy-summary-card">
      <!-- Step 1: Strategy Setup (Basic Info + Legs merged) -->
      <div v-if="store.builder.step === 1" data-testid="autopilot-builder-step-1">
        <!-- Collapsible Basic Information Section -->
        <div class="collapsible-section">
          <button
            @click="basicInfoExpanded = !basicInfoExpanded"
            class="collapsible-header"
            data-testid="autopilot-builder-basic-info-toggle"
          >
            <h2 class="section-title">Basic Information</h2>
            <span class="collapse-icon">{{ basicInfoExpanded ? '▼' : '▶' }}</span>
          </button>

          <div v-show="basicInfoExpanded" class="collapsible-content" data-testid="autopilot-builder-basic-info-content">
            <div class="form-grid">
              <div class="form-field form-field-wide">
                <label class="form-label">Strategy Name *</label>
                <input
                  type="text"
                  v-model="store.builder.strategy.name"
                  data-testid="autopilot-builder-name"
                  class="strategy-input"
                  placeholder="e.g., Iron Condor Weekly"
                />
              </div>

              <div class="form-field form-field-wide">
                <label class="form-label">Description</label>
                <input
                  type="text"
                  v-model="store.builder.strategy.description"
                  data-testid="autopilot-builder-description"
                  class="strategy-input"
                  placeholder="Optional description"
                />
              </div>

              <div class="form-field">
                <label class="form-label">Underlying *</label>
                <select
                  v-model="store.builder.strategy.underlying"
                  data-testid="autopilot-builder-underlying"
                  class="strategy-select"
                >
                  <option v-for="u in underlyings" :key="u" :value="u">{{ u }}</option>
                </select>
              </div>

              <div class="form-field">
                <label class="form-label">Strategy Type</label>
                <select
                  v-model="selectedStrategyType"
                  @change="onStrategyTypeChange"
                  data-testid="autopilot-builder-strategy-type"
                  class="strategy-select"
                >
                  <option value="">Custom (Manual)</option>
                  <optgroup
                    v-for="(cat, catKey) in categories"
                    :key="catKey"
                    :label="cat.name"
                  >
                    <option
                      v-for="strategy in strategiesByCategory[catKey]"
                      :key="strategy.key"
                      :value="strategy.key"
                    >
                      {{ strategy.display_name }}
                    </option>
                  </optgroup>
                </select>
              </div>

              <div class="form-field">
                <label class="form-label">Expiry Type</label>
                <select
                  v-model="store.builder.strategy.expiry_type"
                  data-testid="autopilot-builder-expiry-type"
                  class="strategy-select"
                >
                  <option v-for="e in expiryTypes" :key="e.value" :value="e.value">{{ e.label }}</option>
                </select>
              </div>

              <div class="form-field">
                <label class="form-label">Lots *</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.lots"
                  data-testid="autopilot-builder-lots"
                  min="1"
                  max="50"
                  class="strategy-input"
                />
              </div>

              <div class="form-field">
                <label class="form-label">Position Type</label>
                <select
                  v-model="store.builder.strategy.position_type"
                  data-testid="autopilot-builder-position-type"
                  class="strategy-select"
                >
                  <option v-for="p in positionTypes" :key="p.value" :value="p.value">{{ p.label }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Strategy Legs Table -->
        <AutoPilotLegsTable />
      </div>

      <!-- Step 2: Entry Conditions (was Step 3) -->
      <div v-if="store.builder.step === 2" data-testid="autopilot-builder-step-2">
        <div class="section-header">
          <h2 class="section-title">Entry Conditions</h2>
          <button
            @click="addCondition"
            data-testid="autopilot-add-condition-button"
            class="strategy-btn strategy-btn-primary"
          >
            + Add Condition
          </button>
        </div>

        <div data-testid="autopilot-builder-conditions">
          <div class="form-field">
            <label class="form-label">Condition Logic</label>
            <select
              v-model="store.builder.strategy.entry_conditions.logic"
              data-testid="autopilot-condition-logic"
              class="strategy-select"
            >
              <option value="AND">ALL conditions must be true (AND)</option>
              <option value="OR">ANY condition can be true (OR)</option>
            </select>
          </div>

          <!-- Condition Order Suggestion Banner -->
          <div
            v-if="showConditionOrderSuggestion"
            class="condition-order-suggestion"
            data-testid="autopilot-condition-order-suggestion"
          >
            <div class="suggestion-icon">💡</div>
            <div class="suggestion-content">
              <p class="suggestion-text">Suggested condition order: <strong>TIME → VIX → SPOT → PREMIUM</strong></p>
              <p class="suggestion-hint">Time and VIX conditions should be evaluated first for optimal performance.</p>
            </div>
            <button
              @click="dismissConditionSuggestion"
              class="suggestion-dismiss"
              data-testid="autopilot-condition-order-dismiss"
            >
              Dismiss
            </button>
          </div>

          <!-- Multi-condition Logic Toggle -->
          <div
            v-if="store.builder.strategy.entry_conditions.conditions.length > 1"
            class="condition-logic-toggle-container"
          >
            <label class="form-label">Logic Between Conditions</label>
            <select
              v-model="store.builder.strategy.entry_conditions.logic"
              data-testid="autopilot-condition-logic-operator"
              class="strategy-select"
            >
              <option value="AND">AND - All conditions must match</option>
              <option value="OR">OR - Any condition can match</option>
            </select>
          </div>

          <!-- Add Condition Group Button (for nested groups) -->
          <div v-if="store.builder.strategy.entry_conditions.conditions.length > 0" class="condition-group-actions">
            <button
              @click="addConditionGroup"
              class="strategy-btn strategy-btn-outline"
              data-testid="autopilot-condition-group-add"
            >
              + Add Condition Group
            </button>
          </div>

          <div v-if="store.builder.strategy.entry_conditions.conditions.length === 0" class="empty-state-message">
            No conditions added. The strategy will enter immediately when activated.
          </div>

          <div v-else class="condition-list">
            <div
              v-for="(condition, index) in store.builder.strategy.entry_conditions.conditions"
              :key="condition.id"
              class="condition-row"
              :data-testid="`autopilot-condition-row-${index}`"
            >
              <div class="condition-header">
                <span class="condition-label">Condition {{ index + 1 }}</span>
                <button
                  @click="removeCondition(index)"
                  class="strategy-btn strategy-btn-danger-text"
                  :data-testid="`autopilot-condition-delete-${index}`"
                >
                  Remove
                </button>
              </div>

              <div class="condition-fields">
                <select
                  v-model="condition.variable"
                  :data-testid="`autopilot-condition-variable-${index}`"
                  class="strategy-select compact"
                >
                  <optgroup label="Time Conditions">
                    <option value="TIME.CURRENT">Time</option>
                    <option value="STRATEGY.DTE">Days to Expiry (DTE)</option>
                    <option value="STRATEGY.DAYS_IN_TRADE">Days in Trade</option>
                  </optgroup>

                  <optgroup label="Market Conditions">
                    <option value="SPOT.PRICE">Spot Price</option>
                    <option value="SPOT.DISTANCE_TO.BREAKEVEN">Distance to Breakeven (%)</option>
                    <option value="VOLATILITY.VIX">India VIX</option>
                    <option value="IV.RANK">IV Rank (0-100)</option>
                    <option value="IV.PERCENTILE">IV Percentile (0-100)</option>
                  </optgroup>

                  <optgroup label="Open Interest (Phase 5C)">
                    <option value="OI.PCR">Put-Call Ratio (PCR)</option>
                    <option value="OI.MAX_PAIN">Max Pain Strike</option>
                    <option value="OI.CHANGE">OI Change (%)</option>
                  </optgroup>

                  <optgroup label="Position Greeks">
                    <option value="STRATEGY.DELTA">Delta (Net)</option>
                    <option value="STRATEGY.GAMMA">Gamma (Net)</option>
                    <option value="STRATEGY.THETA">Theta (Net)</option>
                    <option value="STRATEGY.VEGA">Vega (Net)</option>
                  </optgroup>

                  <optgroup label="Probability (Phase 5C)">
                    <option value="PROBABILITY.OTM">Probability OTM (Min across legs)</option>
                  </optgroup>

                  <optgroup label="Profit & Loss">
                    <option value="STRATEGY.PNL">Strategy P&L</option>
                    <option value="PREMIUM.CAPTURED_PCT">Premium Captured (%)</option>
                  </optgroup>

                  <optgroup label="Risk Metrics">
                    <option value="STRATEGY.THETA_BURN_RATE">Theta Burn Rate</option>
                  </optgroup>
                </select>

                <select
                  v-model="condition.operator"
                  :data-testid="`autopilot-condition-operator-${index}`"
                  class="strategy-select compact"
                >
                  <option value="greater_than">Greater Than</option>
                  <option value="less_than">Less Than</option>
                  <option value="equals">Equals</option>
                  <option value="between">Between</option>
                </select>

                <!-- Single value input for non-between operators -->
                <input
                  v-if="condition.operator !== 'between'"
                  v-model="condition.value"
                  :data-testid="`autopilot-condition-value-${index}`"
                  class="strategy-input compact"
                  placeholder="Value"
                />

                <!-- Min/Max inputs for between operator -->
                <div v-else class="flex gap-2">
                  <input
                    v-model="condition.min_value"
                    :data-testid="`autopilot-condition-min-value-${index}`"
                    class="strategy-input compact"
                    placeholder="Min"
                    style="width: 80px;"
                  />
                  <span class="text-gray-500">to</span>
                  <input
                    v-model="condition.max_value"
                    :data-testid="`autopilot-condition-max-value-${index}`"
                    class="strategy-input compact"
                    placeholder="Max"
                    style="width: 80px;"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Phase 5I: Staged Entry Configuration -->
        <div class="mt-6">
          <StagedEntryConfig
            v-model="store.builder.strategy.staged_entry_config"
            :available-legs="availableLegsForStaging"
            data-testid="autopilot-staged-entry-config"
          />
        </div>
      </div>

      <!-- Step 3: Monitoring & Adjustments -->
      <div v-if="store.builder.step === 3" data-testid="autopilot-builder-step-3">
        <h2 class="section-title">Monitoring & Adjustments</h2>

        <!-- Spot Distance Monitoring Section -->
        <div class="monitoring-section" data-testid="autopilot-spot-distance-section">
          <h3 class="subsection-title">Spot Distance Alerts</h3>
          <p class="section-description">Configure alerts when spot price approaches your strike prices.</p>

          <div class="form-grid">
            <div class="form-field">
              <label class="form-label">PE Strike Distance Threshold (%)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.monitoring_config.spot_distance_pe_threshold"
                data-testid="autopilot-spot-distance-pe-threshold"
                class="strategy-input"
                placeholder="e.g., 2.0"
                step="0.1"
                min="0"
                max="100"
              />
              <p class="form-hint">Alert when spot is within this % of PE strike price.</p>
            </div>

            <div class="form-field">
              <label class="form-label">CE Strike Distance Threshold (%)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.monitoring_config.spot_distance_ce_threshold"
                data-testid="autopilot-spot-distance-ce-threshold"
                class="strategy-input"
                placeholder="e.g., 2.0"
                step="0.1"
                min="0"
                max="100"
              />
              <p class="form-hint">Alert when spot is within this % of CE strike price.</p>
            </div>
          </div>

          <!-- Visual Indicator Preview -->
          <div class="spot-distance-preview">
            <div class="spot-distance-gauge">
              <div class="gauge-track">
                <div class="gauge-zone gauge-pe-zone" :style="{ width: (store.builder.strategy.monitoring_config.spot_distance_pe_threshold || 2) + '%' }"></div>
                <div class="gauge-zone gauge-safe-zone"></div>
                <div class="gauge-zone gauge-ce-zone" :style="{ width: (store.builder.strategy.monitoring_config.spot_distance_ce_threshold || 2) + '%' }"></div>
              </div>
              <div class="gauge-labels">
                <span class="gauge-label-pe">PE Zone</span>
                <span class="gauge-label-safe">Safe Zone</span>
                <span class="gauge-label-ce">CE Zone</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Adjustment Menu Section -->
        <div class="adjustment-menu-section" data-testid="autopilot-adjustment-menu">
          <h3 class="subsection-title">Strategy Adjustments</h3>
          <p class="section-description">Convert your strategy or apply adjustments.</p>

          <div class="adjustment-actions">
            <button
              class="strategy-btn strategy-btn-outline"
              data-testid="autopilot-convert-strategy-button"
              @click="showConversionModal = true"
            >
              <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              Convert Strategy
            </button>
            <button
              class="strategy-btn strategy-btn-outline"
              data-testid="autopilot-widen-spread-button"
              @click="showWidenSpreadModal = true"
            >
              <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              </svg>
              Widen Spread
            </button>
          </div>
        </div>

        <!-- Adjustment Rules Section (Phase 3) -->
        <div class="adjustment-rules-section">
          <AdjustmentRuleBuilder
            v-model="store.builder.strategy.adjustment_rules"
            data-testid="autopilot-adjustment-rule-builder"
          />
        </div>
      </div>

      <!-- Step 4: Risk Settings (was Step 5) -->
      <div v-if="store.builder.step === 4" data-testid="autopilot-builder-step-4" data-testid-alias="autopilot-builder-settings-tab">
        <h2 class="section-title">Risk Settings</h2>

        <!-- Quick Navigation Tabs -->
        <div class="settings-tabs mb-6">
          <button
            class="settings-tab"
            data-testid="autopilot-builder-entry-requirements-tab"
            @click="scrollToSection('entry-requirements')"
          >
            Entry Requirements
          </button>
          <button
            class="settings-tab"
            data-testid="autopilot-builder-risk-tab"
            @click="scrollToSection('risk-settings')"
          >
            Risk Limits
          </button>
          <button
            class="settings-tab"
            data-testid="autopilot-builder-exit-rules-tab"
            @click="scrollToSection('exit-rules')"
          >
            Exit Rules
          </button>
          <button
            class="settings-tab"
            data-testid="autopilot-builder-schedule-tab"
            @click="scrollToSection('schedule-settings')"
          >
            Schedule
          </button>
        </div>

        <!-- Entry Requirements Section -->
        <div class="entry-requirements-section" data-testid="autopilot-builder-entry-requirements">
          <h3 class="subsection-title">Entry Requirements</h3>

          <!-- DTE Enforcement -->
          <div class="form-grid">
            <div class="form-field">
              <label class="form-label">Min DTE (Days to Expiry)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.entry_requirements.min_dte"
                data-testid="autopilot-settings-min-dte"
                class="strategy-input"
                placeholder="e.g., 30"
                min="0"
                max="365"
              />
              <p class="form-hint">Minimum days to expiry required for entry.</p>
            </div>

            <div class="form-field">
              <label class="form-label">Max DTE (Days to Expiry)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.entry_requirements.max_dte"
                data-testid="autopilot-settings-max-dte"
                class="strategy-input"
                placeholder="e.g., 45"
                min="0"
                max="365"
              />
              <p class="form-hint">Maximum days to expiry allowed for entry.</p>
            </div>
          </div>

          <!-- Delta Neutral Entry -->
          <div class="delta-neutral-section">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="store.builder.strategy.entry_requirements.require_delta_neutral"
                data-testid="autopilot-settings-delta-neutral-entry"
                class="checkbox-input"
              />
              <span class="checkbox-text">Require Delta Neutral Entry</span>
            </label>
            <p class="form-hint checkbox-hint">When enabled, position will only be entered if net delta is within the specified range.</p>

            <div
              v-if="store.builder.strategy.entry_requirements.require_delta_neutral"
              class="delta-neutral-range"
            >
              <div class="form-field">
                <label class="form-label">Min Delta</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.entry_requirements.delta_neutral_min"
                  data-testid="autopilot-settings-delta-neutral-min"
                  class="strategy-input"
                  placeholder="-0.10"
                  step="0.01"
                  min="-1"
                  max="1"
                />
              </div>
              <div class="form-field">
                <label class="form-label">Max Delta</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.entry_requirements.delta_neutral_max"
                  data-testid="autopilot-settings-delta-neutral-max"
                  class="strategy-input"
                  placeholder="0.10"
                  step="0.01"
                  min="-1"
                  max="1"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="risk-settings" data-testid="autopilot-builder-risk">
          <div class="form-grid">
            <div class="form-field">
              <label class="form-label">Max Loss (₹)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_loss"
                data-testid="autopilot-builder-max-loss"
                class="strategy-input"
                placeholder="e.g., 5000"
              />
            </div>

            <div class="form-field">
              <label class="form-label">Target Profit (₹)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_profit"
                data-testid="autopilot-builder-max-profit"
                class="strategy-input"
                placeholder="e.g., 10000"
              />
            </div>

            <div class="form-field">
              <label class="form-label">Max Loss (%)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_loss_pct"
                class="strategy-input"
                placeholder="e.g., 50"
              />
            </div>

            <div class="form-field">
              <label class="form-label">Max Margin (₹)</label>
              <input
                type="number"
                v-model.number="store.builder.strategy.risk_settings.max_margin"
                class="strategy-input"
                placeholder="e.g., 100000"
              />
            </div>

            <div class="form-field">
              <label class="form-label">Time Stop</label>
              <input
                type="time"
                v-model="store.builder.strategy.risk_settings.time_stop"
                class="strategy-input"
              />
            </div>
          </div>

          <div class="trailing-stop-section">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="store.builder.strategy.risk_settings.trailing_stop.enabled"
                class="checkbox-input"
                data-testid="autopilot-builder-trailing-stop"
              />
              <span class="checkbox-text">Enable Trailing Stop</span>
            </label>

            <div
              v-if="store.builder.strategy.risk_settings.trailing_stop.enabled"
              class="trailing-stop-fields"
            >
              <div class="form-field">
                <label class="form-label">Trigger Profit (₹)</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.risk_settings.trailing_stop.trigger_profit"
                  class="strategy-input"
                  data-testid="autopilot-builder-trailing-stop-value"
                />
              </div>
              <div class="form-field">
                <label class="form-label">Trail Amount (₹)</label>
                <input
                  type="number"
                  v-model.number="store.builder.strategy.risk_settings.trailing_stop.trail_amount"
                  class="strategy-input"
                  data-testid="autopilot-builder-trailing-stop-trail"
                />
              </div>
            </div>
          </div>

          <!-- Phase 5D: Exit Rules Section -->
          <div class="exit-rules-section mt-6" data-testid="autopilot-builder-exit-rules">
            <h3 class="subsection-title mb-4">Exit Rules (Phase 5D)</h3>
            <div class="space-y-6">
              <!-- Profit Target Exit (#18-19) -->
              <ProfitTargetConfig
                :config="store.builder.strategy.exit_rules?.profit_target || {}"
                @update="(config) => updateExitRuleConfig('profit_target', config)"
              />

              <!-- DTE & Days in Trade Exit (#23-24) -->
              <DTEExitConfig
                :config="store.builder.strategy.exit_rules?.time_based || {}"
                @update="(config) => updateExitRuleConfig('time_based', config)"
              />
            </div>
          </div>

          <!-- Phase 3: Re-Entry Configuration Section -->
          <div class="reentry-config-section mt-6" data-testid="autopilot-reentry-config-wrapper">
            <ReentryConfig
              v-model="store.builder.strategy.reentry_config"
            />
          </div>

          <!-- Schedule Settings Section -->
          <div class="schedule-settings-section mt-6" data-testid="autopilot-builder-schedule">
            <h3 class="subsection-title">Schedule Settings</h3>
            <div class="form-grid">
              <div class="form-field">
                <label class="form-label">Activation Mode</label>
                <select
                  v-model="store.builder.strategy.schedule_config.activation_mode"
                  class="strategy-select"
                  data-testid="autopilot-builder-activation-mode"
                >
                  <option value="always">Always Active</option>
                  <option value="scheduled">Scheduled Hours</option>
                  <option value="manual">Manual Only</option>
                </select>
              </div>

              <template v-if="store.builder.strategy.schedule_config.activation_mode === 'scheduled'">
                <div class="form-field">
                  <label class="form-label">Start Time</label>
                  <input
                    type="time"
                    v-model="store.builder.strategy.schedule_config.start_time"
                    class="strategy-input"
                    data-testid="autopilot-builder-start-time"
                  />
                </div>

                <div class="form-field">
                  <label class="form-label">End Time</label>
                  <input
                    type="time"
                    v-model="store.builder.strategy.schedule_config.end_time"
                    class="strategy-input"
                    data-testid="autopilot-builder-end-time"
                  />
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 5: Review (was Step 6) -->
      <div v-if="store.builder.step === 5" data-testid="autopilot-builder-step-5">
        <h2 class="section-title">Review Strategy</h2>

        <div class="review-sections">
          <div class="review-card">
            <h3 class="review-card-title">Basic Info</h3>
            <dl class="review-grid">
              <dt class="review-label">Name:</dt>
              <dd class="review-value">{{ store.builder.strategy.name }}</dd>
              <dt class="review-label">Underlying:</dt>
              <dd class="review-value">{{ store.builder.strategy.underlying }}</dd>
              <dt class="review-label">Lots:</dt>
              <dd class="review-value">{{ store.builder.strategy.lots }}</dd>
              <dt class="review-label">Position Type:</dt>
              <dd class="review-value">{{ store.builder.strategy.position_type }}</dd>
            </dl>
          </div>

          <div class="review-card">
            <h3 class="review-card-title">Legs ({{ store.builder.strategy.legs_config.length }})</h3>
            <div v-for="(leg, index) in store.builder.strategy.legs_config" :key="leg.id" class="review-leg-item">
              Leg {{ index + 1 }}: {{ leg.transaction_type }} {{ leg.contract_type }}
              <span v-if="leg.strike_selection?.mode === 'atm_offset'">
                (ATM {{ leg.strike_selection.offset >= 0 ? '+' : '' }}{{ leg.strike_selection.offset }})
              </span>
            </div>
          </div>

          <div class="review-card">
            <h3 class="review-card-title">Entry Conditions</h3>
            <p class="review-text">
              {{ store.builder.strategy.entry_conditions.conditions.length }} condition(s) with
              {{ store.builder.strategy.entry_conditions.logic }} logic
            </p>
          </div>
        </div>
      </div>

      <!-- Validation Errors Display -->
      <div v-if="validationErrors.length > 0" class="validation-errors">
        <div
          v-for="(error, index) in validationErrors"
          :key="index"
          :data-testid="`autopilot-validation-error-${index}`"
          class="validation-error-item"
        >
          {{ error.message }}
        </div>
      </div>

      <!-- Navigation Buttons -->
      <div class="navigation-bar">
        <button
          v-if="store.builder.step > 1"
          @click="prevStep"
          data-testid="autopilot-builder-previous"
          class="strategy-btn strategy-btn-outline"
        >
          Previous
        </button>
        <div v-else></div>

        <div class="navigation-actions">
          <button
            v-if="store.builder.step === steps.length"
            @click="handleSave"
            :disabled="store.saving"
            data-testid="autopilot-builder-save"
            class="strategy-btn strategy-btn-outline"
          >
            {{ store.saving ? 'Saving...' : 'Save as Draft' }}
          </button>

          <button
            v-if="store.builder.step === steps.length"
            @click="handleActivate"
            :disabled="store.saving"
            data-testid="autopilot-builder-activate"
            class="strategy-btn strategy-btn-success"
          >
            {{ store.saving ? 'Activating...' : 'Save & Activate' }}
          </button>

          <button
            v-if="store.builder.step < steps.length"
            @click="nextStep"
            data-testid="autopilot-builder-next"
            class="strategy-btn strategy-btn-primary"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="store.error" class="error-banner">
      <p class="error-text">{{ store.error }}</p>
    </div>

    <!-- Replace Legs Confirmation Modal -->
    <div v-if="showReplaceConfirm" class="modal-overlay" data-testid="autopilot-replace-legs-modal">
      <div class="modal-content">
        <h3 class="modal-title">Replace Existing Legs?</h3>
        <p class="modal-text">
          Changing strategy type will replace your current {{ store.builder.strategy.legs_config.length }} leg(s).
          This action cannot be undone.
        </p>
        <div class="modal-actions">
          <button
            @click="cancelReplaceLegs"
            class="strategy-btn strategy-btn-outline"
            data-testid="autopilot-replace-legs-cancel"
          >
            Cancel
          </button>
          <button
            @click="confirmReplaceLegs"
            class="strategy-btn strategy-btn-primary"
            data-testid="autopilot-replace-legs-confirm"
          >
            Replace Legs
          </button>
        </div>
      </div>
    </div>

    <!-- Strategy Conversion Modal -->
    <ConversionModal
      v-if="showConversionModal"
      :strategy-id="strategyId || 'new'"
      :current-type="store.builder.strategy.strategy_type || 'custom'"
      :legs="store.builder.strategy.legs_config"
      @close="showConversionModal = false"
      @converted="showConversionModal = false"
    />

    <!-- Roll Wizard Modal (Phase 3) -->
    <RollWizard
      v-if="showRollWizard"
      :show="showRollWizard"
      :strategy-id="strategyId"
      :current-positions="store.builder.strategy.legs_config"
      :underlying="store.builder.strategy.underlying"
      :current-expiry="store.builder.strategy.expiry_type"
      @close="showRollWizard = false"
      @roll-executed="showRollWizard = false"
    />
  </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.autopilot-builder {
  padding: 24px;
  max-width: 100%;
}

/* ===== Settings Tabs (Step 4) ===== */
.settings-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  background: var(--kite-bg-secondary, #f5f5f5);
  border-radius: 8px;
}

.settings-tab {
  padding: 8px 16px;
  background: white;
  border: 1px solid var(--kite-border, #e0e0e0);
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary, #666);
  cursor: pointer;
  transition: all 0.2s ease;
}

.settings-tab:hover {
  border-color: var(--kite-primary, #387ed1);
  color: var(--kite-primary, #387ed1);
  background: var(--kite-primary-light, #e8f0fe);
}

/* ===== Header ===== */
.builder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.builder-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.builder-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.builder-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.step-indicator-text {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Progress Steps ===== */
.step-progress {
  margin-bottom: 32px;
}

.step-progress-track {
  display: flex;
  justify-content: space-between;
}

.step-item {
  flex: 1;
  position: relative;
}

.step-clickable {
  cursor: pointer;
}

.step-content {
  display: flex;
  align-items: center;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.step-active {
  background: var(--kite-blue);
  color: white;
}

.step-completed {
  background: var(--kite-green);
  color: white;
}

.step-pending {
  background: var(--kite-border-light);
  color: var(--kite-text-secondary);
}

.step-label {
  margin-left: 8px;
  display: none;
}

@media (min-width: 768px) {
  .step-label {
    display: block;
  }
}

.step-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.step-connector {
  position: absolute;
  top: 16px;
  left: 32px;
  width: 100%;
  height: 2px;
  background: var(--kite-border-light);
}

.step-connector-active {
  background: var(--kite-green);
}

/* ===== Form Elements ===== */
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.form-field-wide {
  grid-column: span 2;
}

@media (min-width: 768px) {
  .form-field-wide {
    grid-column: span 1;
  }
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

/* ===== Collapsible Section ===== */
.collapsible-section {
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  margin-bottom: 16px;
}

.collapsible-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--kite-table-header-bg);
  border: none;
  cursor: pointer;
  border-radius: 4px 4px 0 0;
}

.collapsible-header:hover {
  background: var(--kite-table-hover);
}

.collapsible-content {
  padding: 16px;
}

.collapse-icon {
  color: var(--kite-text-secondary);
  font-size: 1rem;
}

/* ===== Section Styling ===== */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 16px;
}

/* ===== Empty State ===== */
.empty-state-message {
  text-align: center;
  padding: 32px;
  color: var(--kite-text-secondary);
}

.empty-state-hint {
  font-size: 0.875rem;
  margin-top: 8px;
}

/* ===== Conditions ===== */
.condition-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.condition-row {
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  padding: 12px;
}

.condition-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.condition-label {
  font-size: 0.875rem;
  font-weight: 500;
}

.condition-fields {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

/* ===== Entry Requirements ===== */
.entry-requirements-section {
  background: var(--kite-bg-secondary, #f9fafb);
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 24px;
}

.subsection-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 16px;
}

.delta-neutral-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border);
}

.delta-neutral-range {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 12px;
}

.checkbox-hint {
  margin-left: 24px;
  margin-top: 4px;
}

.form-hint {
  font-size: 0.75rem;
  color: var(--kite-text-muted);
  margin-top: 4px;
}

/* ===== Monitoring Section ===== */
.monitoring-section {
  background: var(--kite-bg-secondary, #f9fafb);
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 24px;
}

.section-description {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

.adjustment-rules-section {
  margin-top: 24px;
}

/* Spot Distance Preview */
.spot-distance-preview {
  margin-top: 20px;
  padding: 16px;
  background: white;
  border-radius: 4px;
  border: 1px solid var(--kite-border);
}

.spot-distance-gauge {
  width: 100%;
}

.gauge-track {
  display: flex;
  height: 24px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--kite-border-light);
}

.gauge-zone {
  height: 100%;
  transition: width 0.2s ease;
}

.gauge-pe-zone {
  background: var(--kite-red, #e53935);
  min-width: 10px;
}

.gauge-safe-zone {
  flex: 1;
  background: var(--kite-green, #43a047);
}

.gauge-ce-zone {
  background: var(--kite-blue, #1e88e5);
  min-width: 10px;
}

.gauge-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--kite-text-muted);
}

.gauge-label-pe {
  color: var(--kite-red);
}

.gauge-label-safe {
  color: var(--kite-green);
}

.gauge-label-ce {
  color: var(--kite-blue);
}

/* ===== Condition Order Suggestion ===== */
.condition-order-suggestion {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.suggestion-icon {
  font-size: 1.25rem;
}

.suggestion-content {
  flex: 1;
}

.suggestion-text {
  font-size: 0.875rem;
  color: var(--kite-text-primary);
  margin: 0;
}

.suggestion-hint {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin: 4px 0 0 0;
}

.suggestion-dismiss {
  background: none;
  border: none;
  color: #f57f17;
  font-size: 0.75rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.suggestion-dismiss:hover {
  background: rgba(245, 127, 23, 0.1);
}

/* Condition Logic Toggle */
.condition-logic-toggle-container {
  margin-bottom: 16px;
}

/* Condition Group Actions */
.condition-group-actions {
  margin-bottom: 16px;
}

/* ===== Risk Settings ===== */
.risk-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.trailing-stop-section {
  border-top: 1px solid var(--kite-border);
  padding-top: 16px;
  margin-top: 16px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox-input {
  border-radius: 4px;
  border-color: var(--kite-border);
  color: var(--kite-blue);
}

.checkbox-text {
  margin-left: 8px;
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.trailing-stop-fields {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 12px;
}

/* ===== Review Step ===== */
.review-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-card {
  background: var(--kite-table-header-bg);
  border-radius: 4px;
  padding: 16px;
}

.review-card-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--kite-text-primary);
}

.review-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  font-size: 0.875rem;
}

.review-label {
  color: var(--kite-text-secondary);
}

.review-value {
  color: var(--kite-text-primary);
}

.review-leg-item {
  font-size: 0.875rem;
  color: var(--kite-text-primary);
}

.review-text {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Validation Errors ===== */
.validation-errors {
  margin-bottom: 16px;
}

.validation-error-item {
  color: var(--kite-red);
  font-size: 0.875rem;
  margin-bottom: 4px;
}

/* ===== Navigation ===== */
.navigation-bar {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border);
}

.navigation-actions {
  display: flex;
  gap: 8px;
}

/* ===== Error Banner ===== */
.error-banner {
  margin-top: 16px;
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red-border, #ffcdd2);
  border-radius: 4px;
  padding: 16px;
}

.error-text {
  color: var(--kite-red);
}

/* ===== Modal Styles ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.modal-text {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 20px;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Button Styles (extend strategy-table.css) ===== */
.strategy-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.strategy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.strategy-btn-primary {
  background: var(--kite-blue);
  color: white;
  border-color: var(--kite-blue);
}

.strategy-btn-primary:hover:not(:disabled) {
  background: var(--kite-blue-dark, #1565c0);
}

.strategy-btn-success {
  background: var(--kite-green);
  color: white;
  border-color: var(--kite-green);
}

.strategy-btn-success:hover:not(:disabled) {
  background: var(--kite-green-dark, #388e3c);
}

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

.strategy-btn-danger-text {
  background: transparent;
  color: var(--kite-red);
  border: none;
  padding: 4px 8px;
}

.strategy-btn-danger-text:hover:not(:disabled) {
  color: var(--kite-red-dark, #c62828);
}

/* ===== Input & Select Styles ===== */
.strategy-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
  transition: border-color 0.15s ease;
}

.strategy-input:focus {
  outline: none;
  border-color: var(--kite-blue);
}

.strategy-input.compact {
  padding: 6px 10px;
  font-size: 0.75rem;
}

.strategy-select {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
  cursor: pointer;
}

.strategy-select:focus {
  outline: none;
  border-color: var(--kite-blue);
}

.strategy-select.compact {
  padding: 6px 10px;
  font-size: 0.75rem;
}

/* ===== Card Styles ===== */
.strategy-summary-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

/* ===== Adjustment Menu Section ===== */
.adjustment-menu-section {
  margin-top: 24px;
  padding: 16px;
  background: var(--kite-body-bg, #f9fafb);
  border-radius: 8px;
}

.adjustment-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.adjustment-actions .strategy-btn {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-svg {
  width: 20px;
  height: 20px;
}
</style>
