<template>
  <div class="conversion-modal-overlay" @click.self="handleCancel" data-testid="autopilot-conversion-modal">
    <div class="wizard-container">
      <!-- Header -->
      <div class="wizard-header">
        <h2>
          <i class="fas fa-exchange-alt"></i>
          Strategy Conversion
        </h2>
        <button class="close-btn" @click="handleCancel" aria-label="Close wizard" data-testid="autopilot-conversion-cancel-button">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <!-- Progress Steps -->
      <div class="wizard-progress">
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="progress-step"
          :class="{
            active: currentStep === index + 1,
            completed: currentStep > index + 1
          }"
        >
          <div class="step-number">
            <i v-if="currentStep > index + 1" class="fas fa-check"></i>
            <span v-else>{{ index + 1 }}</span>
          </div>
          <span class="step-label">{{ step }}</span>
        </div>
      </div>

      <!-- Step Content -->
      <div class="wizard-body">
        <!-- Step 1: Select Target Strategy Type -->
        <div v-if="currentStep === 1" class="wizard-step">
          <h3>Step 1: Select Target Strategy Type</h3>
          <p class="step-description">
            Choose the strategy type you want to convert to. Current strategy: <strong>{{ currentType }}</strong>
          </p>

          <div class="strategy-types-grid">
            <!-- Iron Condor -->
            <div
              class="strategy-card"
              :class="{ selected: selectedType === 'iron_condor', disabled: currentType === 'iron_condor' }"
              @click="selectStrategyType('iron_condor')"
            >
              <div class="card-header">
                <i class="fas fa-layer-group"></i>
                <h4>Iron Condor</h4>
                <span v-if="currentType === 'iron_condor'" class="badge current">Current</span>
              </div>
              <div class="card-body">
                <p class="description">Defined risk spread with wings</p>
                <div class="characteristics">
                  <div class="char-item">
                    <i class="fas fa-shield-alt text-green-500"></i>
                    <span>Lower margin</span>
                  </div>
                  <div class="char-item">
                    <i class="fas fa-chart-line text-blue-500"></i>
                    <span>Defined max loss</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Strangle -->
            <div
              class="strategy-card"
              :class="{ selected: selectedType === 'strangle', disabled: currentType === 'strangle' }"
              @click="selectStrategyType('strangle')"
              data-testid="autopilot-conversion-type-strangle"
            >
              <div class="card-header">
                <i class="fas fa-compress-arrows-alt"></i>
                <h4>Strangle</h4>
                <span v-if="currentType === 'strangle'" class="badge current">Current</span>
              </div>
              <div class="card-body">
                <p class="description">Undefined risk, higher premium</p>
                <div class="characteristics">
                  <div class="char-item">
                    <i class="fas fa-coins text-yellow-500"></i>
                    <span>Higher premium</span>
                  </div>
                  <div class="char-item">
                    <i class="fas fa-exclamation-triangle text-red-500"></i>
                    <span>Unlimited risk</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Iron Fly -->
            <div
              class="strategy-card"
              :class="{ selected: selectedType === 'iron_fly', disabled: currentType === 'iron_fly' }"
              @click="selectStrategyType('iron_fly')"
              data-testid="autopilot-convert-butterfly-button"
            >
              <div class="card-header">
                <i class="fas fa-bullseye"></i>
                <h4>Iron Fly</h4>
                <span v-if="currentType === 'iron_fly'" class="badge current">Current</span>
              </div>
              <div class="card-body">
                <p class="description">ATM strikes with wings</p>
                <div class="characteristics">
                  <div class="char-item">
                    <i class="fas fa-coins text-yellow-500"></i>
                    <span>Higher premium</span>
                  </div>
                  <div class="char-item">
                    <i class="fas fa-crosshairs text-purple-500"></i>
                    <span>Tight profit zone</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Ratio Spread -->
            <div
              class="strategy-card"
              :class="{ selected: selectedType === 'ratio_spread' }"
              @click="selectStrategyType('ratio_spread')"
              data-testid="autopilot-convert-ratio-spread-button"
            >
              <div class="card-header">
                <i class="fas fa-chart-bar"></i>
                <h4>Ratio Spread</h4>
              </div>
              <div class="card-body">
                <p class="description">Extra short contracts for premium</p>
                <div class="characteristics">
                  <div class="char-item">
                    <i class="fas fa-coins text-yellow-500"></i>
                    <span>Extra premium</span>
                  </div>
                  <div class="char-item">
                    <i class="fas fa-exclamation-triangle text-red-500"></i>
                    <span>Unlimited risk</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Configure Parameters -->
        <div v-if="currentStep === 2" class="wizard-step">
          <h3>Step 2: Configure Conversion</h3>
          <p class="step-description">
            Configure parameters for {{ selectedType }} conversion
          </p>

          <!-- Iron Condor Parameters -->
          <div v-if="selectedType === 'iron_condor'" class="config-section">
            <h4>Wing Width Configuration</h4>
            <p class="text-sm text-gray-600 mb-4">
              Distance from short strikes to protective wings
            </p>

            <div class="wing-width-selector">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Wing Width (points)
              </label>
              <div class="flex items-center space-x-4">
                <input
                  type="range"
                  v-model="conversionParams.wing_width"
                  min="50"
                  max="500"
                  step="50"
                  class="flex-1"
                />
                <span class="text-lg font-semibold w-20 text-center">
                  {{ conversionParams.wing_width }}
                </span>
              </div>

              <div class="preset-buttons mt-3">
                <button
                  v-for="width in [50, 100, 200, 300]"
                  :key="width"
                  @click="conversionParams.wing_width = width"
                  :class="getPresetClass(conversionParams.wing_width, width)"
                >
                  {{ width }}
                </button>
              </div>
            </div>
          </div>

          <!-- Ratio Spread Parameters -->
          <div v-if="selectedType === 'ratio_spread'" class="config-section">
            <h4>Ratio Configuration</h4>
            <p class="text-sm text-gray-600 mb-4">
              Number of extra short contracts to add
            </p>

            <div class="ratio-selector">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Ratio (Shorts : Longs)
              </label>
              <div class="ratio-buttons">
                <button
                  v-for="ratio in [2, 3, 4]"
                  :key="ratio"
                  @click="conversionParams.ratio = ratio"
                  :class="getRatioClass(ratio)"
                >
                  {{ ratio }}:1
                </button>
              </div>
            </div>

            <div class="warning-box mt-4">
              <i class="fas fa-exclamation-triangle"></i>
              <p>Ratio spreads have unlimited risk on the extra short contracts</p>
            </div>
          </div>

          <!-- Default message for other conversions -->
          <div v-if="!['iron_condor', 'ratio_spread'].includes(selectedType)" class="config-section">
            <div class="info-box">
              <i class="fas fa-info-circle"></i>
              <p>This conversion requires no additional parameters. Click Next to preview.</p>
            </div>
          </div>
        </div>

        <!-- Step 3: Preview -->
        <div v-if="currentStep === 3" class="wizard-step">
          <h3>Step 3: Preview Conversion</h3>
          <p class="step-description">
            Review the changes before executing
          </p>

          <div v-if="previewLoading" class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Calculating conversion preview...</p>
          </div>

          <div v-else-if="previewError" class="error-state">
            <i class="fas fa-exclamation-triangle"></i>
            <p>{{ previewError }}</p>
            <button @click="loadPreview" class="retry-btn">
              <i class="fas fa-redo"></i> Retry
            </button>
          </div>

          <div v-else-if="preview" class="preview-content">
            <!-- Conversion Summary -->
            <div class="summary-grid">
              <div class="summary-card">
                <h4>Legs to Close</h4>
                <div class="legs-list">
                  <div v-if="preview.legs_to_close.length === 0" class="empty-text">
                    No legs to close
                  </div>
                  <div
                    v-for="legId in preview.legs_to_close"
                    :key="legId"
                    class="leg-item"
                  >
                    <i class="fas fa-times-circle text-red-500"></i>
                    <span>{{ getLegName(legId) }}</span>
                  </div>
                </div>
              </div>

              <div class="summary-card">
                <h4>Legs to Open</h4>
                <div class="legs-list">
                  <div v-if="preview.legs_to_open.length === 0" class="empty-text">
                    No new legs
                  </div>
                  <div
                    v-for="(newLeg, index) in preview.legs_to_open"
                    :key="index"
                    class="leg-item"
                  >
                    <i class="fas fa-plus-circle text-green-500"></i>
                    <span>
                      {{ newLeg.buy_sell }} {{ newLeg.contract_type }} {{ newLeg.strike }}
                      (Qty: {{ newLeg.quantity }})
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Cost Summary -->
            <div class="cost-summary mt-6">
              <div class="cost-card">
                <h4>Cost Analysis</h4>
                <div class="cost-details">
                  <div class="cost-row">
                    <span class="label">Net Cost:</span>
                    <span class="value" :class="getNetCostClass(preview.net_cost)">
                      {{ formatCurrency(preview.net_cost) }}
                    </span>
                  </div>
                  <div class="cost-row">
                    <span class="label">Margin Impact:</span>
                    <span class="value" :class="getMarginImpactClass(preview.margin_impact)">
                      {{ formatCurrency(preview.margin_impact) }}
                    </span>
                  </div>
                  <div v-if="preview.new_max_profit" class="cost-row">
                    <span class="label">New Max Profit:</span>
                    <span class="value text-green-600">
                      {{ formatCurrency(preview.new_max_profit) }}
                    </span>
                  </div>
                  <div v-if="preview.new_max_loss" class="cost-row">
                    <span class="label">New Max Loss:</span>
                    <span class="value text-red-600">
                      {{ formatCurrency(preview.new_max_loss) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Warnings -->
            <div v-if="preview.warnings && preview.warnings.length > 0" class="warnings-section mt-4">
              <h4>Warnings</h4>
              <div
                v-for="(warning, index) in preview.warnings"
                :key="index"
                class="warning-item"
              >
                <i class="fas fa-exclamation-triangle"></i>
                <span>{{ warning }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 4: Confirm & Execute -->
        <div v-if="currentStep === 4" class="wizard-step">
          <h3>Step 4: Confirm & Execute</h3>
          <p class="step-description">
            Review and confirm the conversion
          </p>

          <div v-if="executing" class="execution-progress">
            <div class="progress-header">
              <i class="fas fa-spinner fa-spin"></i>
              <h4>Executing Conversion...</h4>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: executionProgress + '%' }"></div>
            </div>
            <p class="progress-text">{{ executionProgress }}% complete</p>
          </div>

          <div v-else-if="executionError" class="execution-error">
            <i class="fas fa-times-circle"></i>
            <h3>Conversion Failed</h3>
            <p class="error-message">{{ executionError }}</p>
            <div class="error-actions">
              <button @click="retryExecution" class="btn-retry">
                <i class="fas fa-redo"></i> Retry
              </button>
              <button @click="handleCancel" class="btn-cancel">
                <i class="fas fa-times"></i> Close
              </button>
            </div>
          </div>

          <div v-else-if="executionResult" class="execution-success">
            <div class="success-icon">
              <i class="fas fa-check-circle"></i>
            </div>
            <h3>Conversion Successful!</h3>
            <p class="success-message">
              Your strategy has been converted to {{ selectedType }}.
            </p>

            <div class="execution-summary">
              <div class="summary-card">
                <h4>Execution Results</h4>
                <div class="result-details">
                  <div class="detail-row">
                    <span class="label">Conversion Type:</span>
                    <span class="value">{{ executionResult.conversion_type }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">Legs Closed:</span>
                    <span class="value">{{ executionResult.closed_legs?.length || 0 }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">Legs Opened:</span>
                    <span class="value">{{ executionResult.opened_legs?.length || 0 }}</span>
                  </div>
                  <div class="detail-row total">
                    <span class="label">Net Cost:</span>
                    <span class="value" :class="getNetCostClass(executionResult.net_cost)">
                      {{ formatCurrency(executionResult.net_cost) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <button @click="handleSuccess" class="btn-primary btn-full">
              <i class="fas fa-check"></i> Done
            </button>
          </div>

          <!-- Confirmation (before executing) -->
          <div v-else class="confirmation-section">
            <div class="confirmation-box">
              <i class="fas fa-exclamation-circle"></i>
              <h4>Ready to Execute</h4>
              <p>
                You are about to convert your {{ currentType }} strategy to {{ selectedType }}.
                This action cannot be undone.
              </p>
            </div>

            <div class="confirmation-details mt-4">
              <div class="detail-item">
                <i class="fas fa-exchange-alt"></i>
                <span>{{ preview?.legs_to_close.length || 0 }} legs will be closed</span>
              </div>
              <div class="detail-item">
                <i class="fas fa-plus-circle"></i>
                <span>{{ preview?.legs_to_open.length || 0 }} new legs will be opened</span>
              </div>
              <div class="detail-item">
                <i class="fas fa-wallet"></i>
                <span>Net cost: {{ formatCurrency(preview?.net_cost || 0) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer Actions -->
      <div v-if="currentStep < 4 || (currentStep === 4 && !executionResult)" class="wizard-footer">
        <button
          v-if="currentStep > 1"
          @click="previousStep"
          class="btn-secondary"
          :disabled="previewLoading || executing"
        >
          <i class="fas fa-arrow-left"></i>
          Back
        </button>

        <button
          v-if="currentStep < 4"
          @click="nextStep"
          class="btn-primary"
          :disabled="!canProceed || previewLoading"
        >
          Next
          <i class="fas fa-arrow-right"></i>
        </button>

        <button
          v-if="currentStep === 4 && !executing && !executionResult"
          @click="executeConversion"
          class="btn-execute"
          :disabled="executing"
          data-testid="autopilot-execute-conversion-button"
        >
          <i class="fas fa-bolt"></i>
          Execute Conversion
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/services/api'

const props = defineProps({
  strategyId: {
    type: [Number, String],
    required: true
  },
  currentType: {
    type: String,
    required: true
  },
  legs: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'converted'])

// Wizard state
const currentStep = ref(1)
const steps = ['Select Type', 'Configure', 'Preview', 'Execute']

// Step 1: Strategy type selection
const selectedType = ref(null)

// Step 2: Configuration
const conversionParams = ref({
  wing_width: 100,
  ratio: 2
})

// Step 3: Preview
const previewLoading = ref(false)
const previewError = ref(null)
const preview = ref(null)

// Step 4: Execution
const executing = ref(false)
const executionProgress = ref(0)
const executionError = ref(null)
const executionResult = ref(null)

// Computed
const canProceed = computed(() => {
  if (currentStep.value === 1) return selectedType.value !== null
  if (currentStep.value === 2) return true
  if (currentStep.value === 3) return preview.value !== null && !previewError.value
  return true
})

// Watch for step changes
watch(currentStep, (newStep) => {
  if (newStep === 3) {
    loadPreview()
  }
})

// Methods
function selectStrategyType(type) {
  if (type === props.currentType) return
  selectedType.value = type
}

function getPresetClass(currentValue, presetValue) {
  return [
    'preset-btn',
    currentValue === presetValue ? 'preset-btn-active' : 'preset-btn-inactive'
  ]
}

function getRatioClass(ratio) {
  return [
    'ratio-btn',
    conversionParams.value.ratio === ratio ? 'ratio-btn-active' : 'ratio-btn-inactive'
  ]
}

async function loadPreview() {
  if (!selectedType.value) return

  previewLoading.value = true
  previewError.value = null

  try {
    const response = await api.post(
      `/api/v1/autopilot/strategies/${props.strategyId}/convert/preview`,
      {
        target_type: selectedType.value,
        ...conversionParams.value
      }
    )

    preview.value = response.data
  } catch (error) {
    console.error('Preview error:', error)
    previewError.value = error.response?.data?.detail || 'Failed to load preview'
  } finally {
    previewLoading.value = false
  }
}

async function executeConversion() {
  executing.value = true
  executionError.value = null
  executionProgress.value = 0

  try {
    // Simulate progress
    const progressInterval = setInterval(() => {
      if (executionProgress.value < 90) {
        executionProgress.value += 10
      }
    }, 500)

    const response = await api.post(
      `/api/v1/autopilot/strategies/${props.strategyId}/convert/execute`,
      {
        target_type: selectedType.value,
        execution_mode: 'market',
        ...conversionParams.value
      }
    )

    clearInterval(progressInterval)
    executionProgress.value = 100

    executionResult.value = response.data

    setTimeout(() => {
      currentStep.value = 5
    }, 500)
  } catch (error) {
    console.error('Execution error:', error)
    executionError.value = error.response?.data?.detail || 'Conversion failed'
  } finally {
    executing.value = false
  }
}

function retryExecution() {
  executionError.value = null
  executeConversion()
}

function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

function nextStep() {
  if (canProceed.value && currentStep.value < 4) {
    currentStep.value++
  }
}

function handleCancel() {
  emit('close')
}

function handleSuccess() {
  emit('converted', executionResult.value)
  emit('close')
}

function getLegName(legId) {
  const leg = props.legs.find(l => l.leg_id === legId)
  if (!leg) return legId
  return `${leg.buy_sell} ${leg.contract_type} ${leg.strike}`
}

// Formatting helpers
function formatCurrency(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0
  }).format(value)
}

function getNetCostClass(cost) {
  return cost < 0 ? 'text-green-600' : 'text-red-600'
}

function getMarginImpactClass(impact) {
  return impact < 0 ? 'text-green-600' : 'text-red-600'
}
</script>

<style scoped>
.conversion-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.wizard-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  width: 90%;
  max-width: 900px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.wizard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e5e7eb;
}

.wizard-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.wizard-progress {
  display: flex;
  justify-content: space-between;
  padding: 2rem 3rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.progress-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  position: relative;
}

.progress-step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 20px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: #e5e7eb;
  z-index: 0;
}

.progress-step.completed:not(:last-child)::after {
  background: #10b981;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  z-index: 1;
  transition: all 0.3s;
}

.progress-step.active .step-number {
  background: #3b82f6;
  color: white;
}

.progress-step.completed .step-number {
  background: #10b981;
  color: white;
}

.step-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.progress-step.active .step-label {
  color: #1f2937;
  font-weight: 600;
}

.wizard-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.wizard-step h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.step-description {
  color: #6b7280;
  margin-bottom: 1.5rem;
}

.strategy-types-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.strategy-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.strategy-card:hover:not(.disabled) {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.strategy-card.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.strategy-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.card-header i {
  font-size: 1.25rem;
  color: #3b82f6;
}

.card-header h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
}

.badge {
  margin-left: auto;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 4px;
  font-weight: 500;
}

.badge.current {
  background: #dbeafe;
  color: #1e40af;
}

.description {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.75rem;
}

.characteristics {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.char-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.config-section h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.preset-buttons,
.ratio-buttons {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.preset-btn,
.ratio-btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-btn-active,
.ratio-btn-active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.info-box,
.warning-box {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 6px;
}

.info-box {
  background: #eff6ff;
  color: #1e40af;
}

.warning-box {
  background: #fef3c7;
  color: #92400e;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.summary-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
}

.summary-card h4 {
  font-size: 0.875rem;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.legs-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.leg-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #1f2937;
}

.empty-text {
  font-size: 0.875rem;
  color: #9ca3af;
  font-style: italic;
}

.cost-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
}

.cost-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cost-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.cost-row:last-child {
  border-bottom: none;
}

.cost-row .label {
  font-size: 0.875rem;
  color: #6b7280;
}

.cost-row .value {
  font-weight: 600;
  font-size: 1rem;
}

.warnings-section h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #dc2626;
  margin-bottom: 0.75rem;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #fef2f2;
  border-left: 3px solid #dc2626;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #991b1b;
}

.confirmation-box {
  background: #fffbeb;
  border: 1px solid #fbbf24;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}

.confirmation-box i {
  font-size: 3rem;
  color: #f59e0b;
  margin-bottom: 1rem;
}

.confirmation-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #1f2937;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 3rem;
}

.loading-state i,
.error-state i {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.loading-state i {
  color: #3b82f6;
}

.error-state i {
  color: #dc2626;
}

.retry-btn,
.btn-cancel {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn {
  background: #3b82f6;
  color: white;
  border: none;
}

.btn-cancel {
  background: #e5e7eb;
  color: #1f2937;
  border: none;
}

.execution-progress {
  text-align: center;
  padding: 2rem;
}

.progress-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.progress-header i {
  font-size: 3rem;
  color: #3b82f6;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s;
}

.execution-success {
  text-align: center;
  padding: 2rem;
}

.success-icon i {
  font-size: 4rem;
  color: #10b981;
  margin-bottom: 1rem;
}

.execution-summary {
  margin: 1.5rem 0;
}

.wizard-footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-top: 1px solid #e5e7eb;
}

.btn-secondary,
.btn-primary,
.btn-execute {
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-secondary {
  background: white;
  border: 1px solid #d1d5db;
  color: #1f2937;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
}

.btn-primary {
  background: #3b82f6;
  border: none;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-execute {
  background: #10b981;
  border: none;
  color: white;
}

.btn-execute:hover:not(:disabled) {
  background: #059669;
}

.btn-primary:disabled,
.btn-secondary:disabled,
.btn-execute:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-full {
  width: 100%;
  justify-content: center;
}
</style>
