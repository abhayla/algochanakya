<template>
  <div class="break-trade-wizard-overlay" @click.self="handleCancel">
    <div class="wizard-container">
      <!-- Header -->
      <div class="wizard-header">
        <h2>
          <i class="fas fa-arrows-split-up-and-left"></i>
          Break/Split Trade Recovery
        </h2>
        <button class="close-btn" @click="handleCancel" aria-label="Close wizard">
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
        <!-- Step 1: Leg Selection -->
        <div v-if="currentStep === 1" class="wizard-step">
          <h3>Step 1: Select Losing Leg to Break</h3>
          <p class="step-description">
            Choose the leg that has breached or is under pressure. This leg will be exited
            and split into two new positions.
          </p>

          <div v-if="!legs || legs.length === 0" class="empty-state">
            <i class="fas fa-exclamation-circle"></i>
            <p>No open legs found for this strategy</p>
          </div>

          <div v-else class="leg-selection-grid">
            <div
              v-for="leg in legs"
              :key="leg.leg_id"
              class="leg-card"
              :class="{ selected: selectedLeg?.leg_id === leg.leg_id }"
              @click="selectLeg(leg)"
            >
              <div class="leg-header">
                <div class="leg-title">
                  <span class="option-type" :class="leg.contract_type.toLowerCase()">
                    {{ leg.contract_type }}
                  </span>
                  <span class="strike">{{ formatStrike(leg.strike) }}</span>
                </div>
                <div class="leg-pnl" :class="getPnLClass(leg.unrealized_pnl)">
                  {{ formatCurrency(leg.unrealized_pnl) }}
                </div>
              </div>

              <div class="leg-details">
                <div class="detail-row">
                  <span class="label">Entry:</span>
                  <span class="value">{{ formatCurrency(leg.entry_price) }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">LTP:</span>
                  <span class="value">{{ formatCurrency(leg.ltp) }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">Qty:</span>
                  <span class="value">{{ leg.quantity }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">Delta:</span>
                  <span class="value">{{ formatDelta(leg.delta) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Exit Cost Preview -->
        <div v-if="currentStep === 2" class="wizard-step">
          <h3>Step 2: Exit Cost Preview</h3>
          <p class="step-description">
            Review the cost of exiting the selected leg and the recovery premium calculation.
          </p>

          <div v-if="simulationLoading" class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Calculating exit cost and recovery options...</p>
          </div>

          <div v-else-if="simulationError" class="error-state">
            <i class="fas fa-exclamation-triangle"></i>
            <p>{{ simulationError }}</p>
            <button @click="loadSimulation" class="retry-btn">
              <i class="fas fa-redo"></i> Retry
            </button>
          </div>

          <div v-else-if="simulation" class="simulation-summary">
            <div class="summary-card exit-cost-card">
              <h4>Exit Cost</h4>
              <div class="cost-breakdown">
                <div class="cost-row">
                  <span class="label">Leg Exit Price:</span>
                  <span class="value">{{ formatCurrency(simulation.exit_cost) }}</span>
                </div>
                <div class="cost-row">
                  <span class="label">Total Exit Cost:</span>
                  <span class="value total">{{ formatCurrency(simulation.total_exit_cost) }}</span>
                </div>
              </div>
            </div>

            <div class="summary-card recovery-card">
              <h4>Recovery Plan</h4>
              <div class="recovery-breakdown">
                <div class="recovery-row highlight">
                  <span class="label">Recovery Premium (50%):</span>
                  <span class="value">{{ formatCurrency(simulation.recovery_premium) }}</span>
                </div>
                <div class="recovery-row">
                  <span class="label">PUT Premium:</span>
                  <span class="value">{{ formatCurrency(simulation.put_premium) }}</span>
                </div>
                <div class="recovery-row">
                  <span class="label">CALL Premium:</span>
                  <span class="value">{{ formatCurrency(simulation.call_premium) }}</span>
                </div>
                <div class="recovery-row total">
                  <span class="label">Net Cost:</span>
                  <span class="value" :class="getNetCostClass(simulation.net_cost)">
                    {{ formatCurrency(simulation.net_cost) }}
                  </span>
                </div>
              </div>
            </div>

            <div class="info-box">
              <i class="fas fa-info-circle"></i>
              <p>
                The break trade will exit the losing leg and create two new positions
                (PUT + CALL strangle) to recover approximately 50% of the loss immediately.
              </p>
            </div>
          </div>
        </div>

        <!-- Step 3: Strike Selection -->
        <div v-if="currentStep === 3" class="wizard-step">
          <h3>Step 3: Select New Strikes</h3>
          <p class="step-description">
            Review or customize the suggested strikes for the new PUT and CALL positions.
          </p>

          <div v-if="simulation" class="strike-selection">
            <!-- PUT Strike -->
            <div class="strike-section">
              <h4>
                <span class="option-type pe">PUT</span>
                Strike Selection
              </h4>
              <div class="strike-options">
                <div class="suggested-strike" :class="{ selected: useCustomStrikes === false }">
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="put-strike"
                      :value="false"
                      v-model="useCustomStrikes"
                    />
                    <div class="strike-details">
                      <div class="strike-header">
                        <span class="strike-value">{{ formatStrike(simulation.suggested_put_strike) }}</span>
                        <span class="badge recommended">Recommended</span>
                      </div>
                      <div class="strike-metrics">
                        <span>Premium: {{ formatCurrency(simulation.put_premium) }}</span>
                        <span>Delta: {{ formatDelta(simulation.put_delta) }}</span>
                      </div>
                    </div>
                  </label>
                </div>

                <div class="custom-strike" :class="{ selected: useCustomStrikes === true }">
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="put-strike"
                      :value="true"
                      v-model="useCustomStrikes"
                    />
                    <div class="strike-details">
                      <span class="strike-label">Custom Strike</span>
                      <input
                        v-if="useCustomStrikes"
                        type="number"
                        v-model.number="customPutStrike"
                        class="strike-input"
                        :step="strikeStep"
                        placeholder="Enter strike"
                      />
                    </div>
                  </label>
                </div>
              </div>
            </div>

            <!-- CALL Strike -->
            <div class="strike-section">
              <h4>
                <span class="option-type ce">CALL</span>
                Strike Selection
              </h4>
              <div class="strike-options">
                <div class="suggested-strike" :class="{ selected: useCustomStrikes === false }">
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="call-strike"
                      :value="false"
                      v-model="useCustomStrikes"
                    />
                    <div class="strike-details">
                      <div class="strike-header">
                        <span class="strike-value">{{ formatStrike(simulation.suggested_call_strike) }}</span>
                        <span class="badge recommended">Recommended</span>
                      </div>
                      <div class="strike-metrics">
                        <span>Premium: {{ formatCurrency(simulation.call_premium) }}</span>
                        <span>Delta: {{ formatDelta(simulation.call_delta) }}</span>
                      </div>
                    </div>
                  </label>
                </div>

                <div class="custom-strike" :class="{ selected: useCustomStrikes === true }">
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="call-strike"
                      :value="true"
                      v-model="useCustomStrikes"
                    />
                    <div class="strike-details">
                      <span class="strike-label">Custom Strike</span>
                      <input
                        v-if="useCustomStrikes"
                        type="number"
                        v-model.number="customCallStrike"
                        class="strike-input"
                        :step="strikeStep"
                        placeholder="Enter strike"
                      />
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 4: Confirmation -->
        <div v-if="currentStep === 4" class="wizard-step">
          <h3>Step 4: Review & Confirm</h3>
          <p class="step-description">
            Review all details before executing the break trade.
          </p>

          <div class="confirmation-summary">
            <div class="summary-section">
              <h4>Exit Transaction</h4>
              <div class="transaction-details">
                <div class="detail-row">
                  <span class="label">Leg to Exit:</span>
                  <span class="value">
                    {{ selectedLeg?.contract_type }} {{ formatStrike(selectedLeg?.strike) }}
                  </span>
                </div>
                <div class="detail-row">
                  <span class="label">Exit Price:</span>
                  <span class="value">{{ formatCurrency(simulation?.exit_cost) }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">Quantity:</span>
                  <span class="value">{{ selectedLeg?.quantity }}</span>
                </div>
              </div>
            </div>

            <div class="summary-section">
              <h4>New Positions</h4>
              <div class="new-positions">
                <div class="position-card">
                  <div class="position-header">
                    <span class="option-type pe">PUT</span>
                    <span class="strike">
                      {{ formatStrike(useCustomStrikes ? customPutStrike : simulation?.suggested_put_strike) }}
                    </span>
                  </div>
                  <div class="position-details">
                    <span>Premium: {{ formatCurrency(simulation?.put_premium) }}</span>
                    <span>Qty: {{ selectedLeg?.quantity }}</span>
                  </div>
                </div>

                <div class="position-card">
                  <div class="position-header">
                    <span class="option-type ce">CALL</span>
                    <span class="strike">
                      {{ formatStrike(useCustomStrikes ? customCallStrike : simulation?.suggested_call_strike) }}
                    </span>
                  </div>
                  <div class="position-details">
                    <span>Premium: {{ formatCurrency(simulation?.call_premium) }}</span>
                    <span>Qty: {{ selectedLeg?.quantity }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="summary-section total-section">
              <h4>Net Impact</h4>
              <div class="net-impact">
                <div class="impact-row">
                  <span class="label">Total Premium Received:</span>
                  <span class="value credit">
                    {{ formatCurrency((simulation?.put_premium || 0) + (simulation?.call_premium || 0)) }}
                  </span>
                </div>
                <div class="impact-row">
                  <span class="label">Exit Cost:</span>
                  <span class="value debit">{{ formatCurrency(simulation?.total_exit_cost) }}</span>
                </div>
                <div class="impact-row total">
                  <span class="label">Net Cost:</span>
                  <span class="value" :class="getNetCostClass(simulation?.net_cost)">
                    {{ formatCurrency(simulation?.net_cost) }}
                  </span>
                </div>
              </div>
            </div>

            <div class="warning-box">
              <i class="fas fa-exclamation-triangle"></i>
              <p>
                <strong>Important:</strong> This action is irreversible. The break trade will
                immediately exit the losing leg and create two new positions. Ensure you have
                reviewed all details carefully.
              </p>
            </div>
          </div>
        </div>

        <!-- Step 5: Execution -->
        <div v-if="currentStep === 5" class="wizard-step execution-step">
          <div v-if="executing" class="executing-state">
            <div class="spinner-large">
              <i class="fas fa-spinner fa-spin"></i>
            </div>
            <h3>Executing Break Trade...</h3>
            <p>Please wait while we process your break trade.</p>
            <div class="execution-progress">
              <div class="progress-item" :class="{ active: executionProgress >= 1 }">
                <i class="fas fa-check-circle"></i>
                <span>Exiting losing leg</span>
              </div>
              <div class="progress-item" :class="{ active: executionProgress >= 2 }">
                <i class="fas fa-check-circle"></i>
                <span>Creating PUT position</span>
              </div>
              <div class="progress-item" :class="{ active: executionProgress >= 3 }">
                <i class="fas fa-check-circle"></i>
                <span>Creating CALL position</span>
              </div>
              <div class="progress-item" :class="{ active: executionProgress >= 4 }">
                <i class="fas fa-check-circle"></i>
                <span>Updating strategy</span>
              </div>
            </div>
          </div>

          <div v-else-if="executionError" class="execution-error">
            <div class="error-icon">
              <i class="fas fa-times-circle"></i>
            </div>
            <h3>Execution Failed</h3>
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
            <h3>Break Trade Executed Successfully!</h3>
            <p class="success-message">
              Your break trade has been completed. The losing leg has been exited and
              two new positions have been created.
            </p>

            <div class="execution-summary">
              <div class="summary-card">
                <h4>Execution Results</h4>
                <div class="result-details">
                  <div class="detail-row">
                    <span class="label">Break Trade ID:</span>
                    <span class="value">{{ executionResult.break_trade_id }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">Exit Order ID:</span>
                    <span class="value">{{ executionResult.exit_order?.order_id }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">New Positions:</span>
                    <span class="value">{{ executionResult.new_positions?.length || 0 }}</span>
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
        </div>
      </div>

      <!-- Footer Actions -->
      <div v-if="currentStep < 5" class="wizard-footer">
        <button
          v-if="currentStep > 1"
          @click="previousStep"
          class="btn-secondary"
          :disabled="simulationLoading || executing"
        >
          <i class="fas fa-arrow-left"></i>
          Back
        </button>

        <button
          v-if="currentStep < 4"
          @click="nextStep"
          class="btn-primary"
          :disabled="!canProceed || simulationLoading"
        >
          Next
          <i class="fas fa-arrow-right"></i>
        </button>

        <button
          v-if="currentStep === 4"
          @click="executeBreakTrade"
          class="btn-execute"
          :disabled="executing"
        >
          <i class="fas fa-bolt"></i>
          Execute Break Trade
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  },
  legs: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'success'])

// Wizard state
const currentStep = ref(1)
const steps = ['Select Leg', 'Preview Cost', 'Choose Strikes', 'Confirm', 'Execute']

// Step 1: Leg selection
const selectedLeg = ref(null)

// Step 2: Simulation
const simulationLoading = ref(false)
const simulationError = ref(null)
const simulation = ref(null)

// Step 3: Strike selection
const useCustomStrikes = ref(false)
const customPutStrike = ref(null)
const customCallStrike = ref(null)
const strikeStep = ref(50) // Strike increment

// Step 5: Execution
const executing = ref(false)
const executionProgress = ref(0)
const executionError = ref(null)
const executionResult = ref(null)

// Computed
const canProceed = computed(() => {
  if (currentStep.value === 1) return selectedLeg.value !== null
  if (currentStep.value === 2) return simulation.value !== null && !simulationError.value
  if (currentStep.value === 3) {
    if (!useCustomStrikes.value) return true
    return customPutStrike.value && customCallStrike.value
  }
  return true
})

// Methods
function selectLeg(leg) {
  selectedLeg.value = leg
}

async function loadSimulation() {
  if (!selectedLeg.value) return

  simulationLoading.value = true
  simulationError.value = null

  try {
    const response = await api.post(
      `/api/v1/autopilot/strategies/${props.strategyId}/legs/${selectedLeg.value.leg_id}/break/simulate`,
      {
        premium_split: 'equal',
        prefer_round_strikes: true,
        max_delta: 0.30
      }
    )
    simulation.value = response.data
  } catch (error) {
    simulationError.value = error.response?.data?.detail || 'Failed to load simulation'
    console.error('Simulation error:', error)
  } finally {
    simulationLoading.value = false
  }
}

async function executeBreakTrade() {
  executing.value = true
  executionError.value = null
  executionProgress.value = 0

  try {
    // Simulate progress
    setTimeout(() => { executionProgress.value = 1 }, 500)
    setTimeout(() => { executionProgress.value = 2 }, 1500)
    setTimeout(() => { executionProgress.value = 3 }, 2500)

    const response = await api.post(
      `/api/v1/autopilot/strategies/${props.strategyId}/legs/${selectedLeg.value.leg_id}/break`,
      {
        execution_mode: 'market',
        new_positions: 'auto',
        new_put_strike: useCustomStrikes.value ? customPutStrike.value : null,
        new_call_strike: useCustomStrikes.value ? customCallStrike.value : null,
        premium_split: 'equal',
        prefer_round_strikes: !useCustomStrikes.value,
        max_delta: 0.30
      }
    )

    executionProgress.value = 4
    executionResult.value = response.data
    currentStep.value = 5
  } catch (error) {
    executionError.value = error.response?.data?.detail || 'Failed to execute break trade'
    console.error('Execution error:', error)
    currentStep.value = 5
  } finally {
    executing.value = false
  }
}

function retryExecution() {
  executionError.value = null
  executionResult.value = null
  currentStep.value = 4
}

function nextStep() {
  if (!canProceed.value) return

  if (currentStep.value === 1) {
    // Moving to step 2: Load simulation
    currentStep.value = 2
    loadSimulation()
  } else if (currentStep.value === 2 && simulation.value) {
    // Moving to step 3: Set default custom strikes
    customPutStrike.value = simulation.value.suggested_put_strike
    customCallStrike.value = simulation.value.suggested_call_strike
    currentStep.value = 3
  } else {
    currentStep.value++
  }
}

function previousStep() {
  currentStep.value--
}

function handleCancel() {
  if (executing.value) return
  emit('close')
}

function handleSuccess() {
  emit('success', executionResult.value)
  emit('close')
}

// Formatters
function formatStrike(strike) {
  return strike ? Number(strike).toFixed(0) : '-'
}

function formatCurrency(value) {
  if (value == null) return '₹0'
  return `₹${Math.abs(Number(value)).toFixed(2)}`
}

function formatDelta(delta) {
  if (delta == null) return '-'
  return Number(delta).toFixed(3)
}

function getPnLClass(pnl) {
  if (pnl == null) return ''
  return Number(pnl) >= 0 ? 'profit' : 'loss'
}

function getNetCostClass(netCost) {
  if (netCost == null) return ''
  return Number(netCost) < 0 ? 'profit' : 'loss'
}

onMounted(() => {
  // Auto-select leg if only one is in loss
  const losingLegs = props.legs.filter(leg => leg.unrealized_pnl && Number(leg.unrealized_pnl) < 0)
  if (losingLegs.length === 1) {
    selectedLeg.value = losingLegs[0]
  }
})
</script>

<style scoped>
.break-trade-wizard-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.wizard-container {
  background: #1a1d2e;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.wizard-header {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.wizard-header h2 {
  margin: 0;
  font-size: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

/* Progress Steps */
.wizard-progress {
  display: flex;
  padding: 24px;
  background: #151825;
  border-bottom: 1px solid #2d3142;
  gap: 8px;
}

.progress-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.progress-step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 16px;
  left: calc(50% + 20px);
  width: calc(100% - 40px);
  height: 2px;
  background: #2d3142;
  z-index: 0;
}

.progress-step.completed:not(:last-child)::after {
  background: #10b981;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2d3142;
  color: #8b92ab;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  z-index: 1;
  transition: all 0.3s;
}

.progress-step.active .step-number {
  background: #6366f1;
  color: white;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
}

.progress-step.completed .step-number {
  background: #10b981;
  color: white;
}

.step-label {
  font-size: 12px;
  color: #8b92ab;
  font-weight: 500;
}

.progress-step.active .step-label {
  color: white;
}

/* Body */
.wizard-body {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  background: #1a1d2e;
}

.wizard-step h3 {
  margin: 0 0 8px 0;
  color: white;
  font-size: 20px;
}

.step-description {
  color: #8b92ab;
  margin: 0 0 24px 0;
  line-height: 1.6;
}

/* Leg Selection Grid */
.leg-selection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.leg-card {
  background: #151825;
  border: 2px solid #2d3142;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.leg-card:hover {
  border-color: #6366f1;
  transform: translateY(-2px);
}

.leg-card.selected {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
}

.leg-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.leg-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-type {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.option-type.ce {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.option-type.pe {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.strike {
  color: white;
  font-weight: 600;
  font-size: 18px;
}

.leg-pnl {
  font-weight: 700;
  font-size: 16px;
}

.leg-pnl.profit {
  color: #10b981;
}

.leg-pnl.loss {
  color: #ef4444;
}

.leg-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.detail-row .label {
  color: #8b92ab;
}

.detail-row .value {
  color: white;
  font-weight: 500;
}

/* Simulation Summary */
.simulation-summary {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-card {
  background: #151825;
  border: 1px solid #2d3142;
  border-radius: 8px;
  padding: 20px;
}

.summary-card h4 {
  margin: 0 0 16px 0;
  color: white;
  font-size: 16px;
}

.cost-breakdown,
.recovery-breakdown {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cost-row,
.recovery-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2d3142;
}

.cost-row:last-child,
.recovery-row:last-child {
  border-bottom: none;
}

.recovery-row.highlight {
  background: rgba(99, 102, 241, 0.1);
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 8px;
}

.cost-row .label,
.recovery-row .label {
  color: #8b92ab;
  font-size: 14px;
}

.cost-row .value,
.recovery-row .value {
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.cost-row.total,
.recovery-row.total {
  padding-top: 12px;
  margin-top: 4px;
  border-top: 2px solid #6366f1;
  border-bottom: none;
}

.cost-row.total .label,
.recovery-row.total .label {
  color: white;
  font-weight: 600;
  font-size: 16px;
}

.cost-row.total .value,
.recovery-row.total .value {
  font-size: 18px;
  font-weight: 700;
}

/* Strike Selection */
.strike-selection {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.strike-section h4 {
  margin: 0 0 16px 0;
  color: white;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.strike-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggested-strike,
.custom-strike {
  background: #151825;
  border: 2px solid #2d3142;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
}

.suggested-strike.selected,
.custom-strike.selected {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
}

.radio-label {
  display: flex;
  gap: 12px;
  cursor: pointer;
  align-items: center;
}

.radio-label input[type="radio"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.strike-details {
  flex: 1;
}

.strike-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.strike-value {
  color: white;
  font-weight: 700;
  font-size: 18px;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.badge.recommended {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.strike-metrics {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #8b92ab;
}

.strike-input {
  width: 100%;
  padding: 8px 12px;
  background: #1a1d2e;
  border: 1px solid #2d3142;
  border-radius: 6px;
  color: white;
  font-size: 16px;
  margin-top: 8px;
}

/* Confirmation */
.confirmation-summary {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.summary-section h4 {
  margin: 0 0 12px 0;
  color: white;
  font-size: 16px;
}

.transaction-details {
  background: #151825;
  border: 1px solid #2d3142;
  border-radius: 8px;
  padding: 16px;
}

.new-positions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.position-card {
  background: #151825;
  border: 1px solid #2d3142;
  border-radius: 8px;
  padding: 16px;
}

.position-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.position-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #8b92ab;
}

.net-impact {
  background: #151825;
  border: 1px solid #2d3142;
  border-radius: 8px;
  padding: 16px;
}

.impact-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #2d3142;
}

.impact-row:last-child {
  border-bottom: none;
}

.impact-row.total {
  border-top: 2px solid #6366f1;
  padding-top: 16px;
  margin-top: 8px;
}

.impact-row .value.credit {
  color: #10b981;
}

.impact-row .value.debit {
  color: #ef4444;
}

/* Execution Step */
.execution-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.executing-state,
.execution-error,
.execution-success {
  text-align: center;
  max-width: 500px;
}

.spinner-large {
  font-size: 64px;
  color: #6366f1;
  margin-bottom: 24px;
}

.success-icon,
.error-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.success-icon {
  color: #10b981;
}

.error-icon {
  color: #ef4444;
}

.execution-progress {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 32px;
  text-align: left;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #8b92ab;
  font-size: 14px;
}

.progress-item.active {
  color: #10b981;
}

.progress-item i {
  font-size: 20px;
}

.execution-summary {
  margin-top: 24px;
  width: 100%;
}

.result-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Info/Warning Boxes */
.info-box,
.warning-box {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.info-box {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
}

.warning-box {
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fde68a;
}

.info-box i,
.warning-box i {
  color: inherit;
  font-size: 20px;
  flex-shrink: 0;
}

/* Loading/Empty States */
.loading-state,
.empty-state,
.error-state {
  text-align: center;
  padding: 48px 24px;
  color: #8b92ab;
}

.loading-state i {
  font-size: 32px;
  margin-bottom: 16px;
  color: #6366f1;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 16px;
  color: #ef4444;
}

.error-state i {
  font-size: 48px;
  margin-bottom: 16px;
  color: #ef4444;
}

/* Footer */
.wizard-footer {
  background: #151825;
  border-top: 1px solid #2d3142;
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

/* Buttons */
button {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
}

.btn-primary {
  background: #6366f1;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #4f46e5;
  transform: translateY(-1px);
}

.btn-secondary {
  background: #2d3142;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #3d4252;
}

.btn-execute {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  font-size: 16px;
  padding: 14px 32px;
}

.btn-execute:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
}

.btn-full {
  width: 100%;
  justify-content: center;
  font-size: 16px;
  padding: 14px;
}

.btn-retry,
.btn-cancel {
  padding: 10px 20px;
}

.btn-retry {
  background: #6366f1;
  color: white;
}

.btn-cancel {
  background: #2d3142;
  color: white;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}
</style>
