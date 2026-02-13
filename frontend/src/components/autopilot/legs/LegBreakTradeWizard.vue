<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
      <div class="wizard-modal" data-testid="autopilot-break-trade-wizard">
        <div class="wizard-header">
          <h3>Break Trade Wizard</h3>
          <button @click="$emit('close')" class="close-btn">×</button>
        </div>

        <!-- Step Indicator -->
        <div class="step-indicator">
          <div
            v-for="step in steps"
            :key="step.number"
            class="step"
            :class="{ active: currentStep === step.number, completed: currentStep > step.number }"
          >
            <div class="step-number">{{ step.number }}</div>
            <div class="step-label">{{ step.label }}</div>
          </div>
        </div>

        <!-- Step 1: Confirmation -->
        <div v-if="currentStep === 1" class="wizard-body" data-testid="autopilot-break-step-1">
          <h4>Confirm Break Trade</h4>
          <p class="description">
            Breaking this trade will exit the current position and create new recovery positions.
          </p>

          <div class="info-box">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <div>
              <p><strong>What is a Break Trade?</strong></p>
              <p>A break trade exits a losing position and creates new positions on both sides to recover the loss gradually.</p>
            </div>
          </div>

          <div class="config-options">
            <div class="form-group">
              <label>Execution Mode</label>
              <select v-model="config.executionMode" class="form-select">
                <option value="market">Market Order</option>
                <option value="limit">Limit Order</option>
              </select>
            </div>

            <div class="form-group">
              <label>Premium Split</label>
              <select v-model="config.premiumSplit" class="form-select">
                <option value="equal">Equal Split</option>
                <option value="weighted">Weighted Split</option>
              </select>
            </div>

            <div class="form-group checkbox-group">
              <label>
                <input type="checkbox" v-model="config.preferRoundStrikes" />
                <span>Prefer Round Strikes</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Step 2: Exit Cost Preview -->
        <div v-else-if="currentStep === 2" class="wizard-body" data-testid="autopilot-break-step-2">
          <h4>Exit Cost Estimate</h4>
          <p class="description">Review the estimated cost to exit the current position</p>

          <div class="cost-summary">
            <div class="cost-item">
              <span class="label">Current Position Loss:</span>
              <span class="value loss">-₹2,450.00</span>
            </div>
            <div class="cost-item">
              <span class="label">Exit Slippage (Est.):</span>
              <span class="value">₹150.00</span>
            </div>
            <div class="cost-item total">
              <span class="label">Total Exit Cost:</span>
              <span class="value loss">-₹2,600.00</span>
            </div>
          </div>

          <div class="warning-box">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>Actual cost may vary based on market conditions at execution time</span>
          </div>
        </div>

        <!-- Step 3: New Strikes Preview -->
        <div v-else-if="currentStep === 3" class="wizard-body" data-testid="autopilot-break-step-3">
          <h4>Recovery Strategy</h4>
          <p class="description">Preview of new positions to recover the loss</p>

          <div class="preview-section" data-testid="autopilot-break-preview">
            <h5>Current Position (To Exit)</h5>
            <div class="position-card current">
              <div class="position-info">
                <span class="type">SELL CE</span>
                <span class="strike">25000</span>
                <span class="qty">75 qty</span>
              </div>
              <div class="position-pnl loss">-₹2,450</div>
            </div>

            <div class="arrow-down">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <polyline points="19 12 12 19 5 12"/>
              </svg>
            </div>

            <h5>New Positions (To Create)</h5>
            <div class="new-positions" data-testid="autopilot-break-new-strikes">
              <div class="position-card new">
                <div class="position-info">
                  <span class="type call">SELL CE</span>
                  <span class="strike">25500</span>
                  <span class="qty">37 qty</span>
                </div>
                <div class="position-premium">₹180 premium</div>
              </div>
              <div class="position-card new">
                <div class="position-info">
                  <span class="type put">SELL PE</span>
                  <span class="strike">24500</span>
                  <span class="qty">38 qty</span>
                </div>
                <div class="position-premium">₹175 premium</div>
              </div>
            </div>

            <div class="recovery-stats">
              <div class="stat-item">
                <span class="label">Recovery Target:</span>
                <span class="value">₹2,600</span>
              </div>
              <div class="stat-item">
                <span class="label">Initial Credit:</span>
                <span class="value profit">+₹1,330</span>
              </div>
              <div class="stat-item">
                <span class="label">Remaining to Recover:</span>
                <span class="value">₹1,270</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Wizard Footer -->
        <div class="wizard-footer">
          <button
            v-if="currentStep > 1"
            @click="previousStep"
            class="btn btn-secondary"
            data-testid="autopilot-break-back-btn"
          >
            Back
          </button>
          <button
            v-if="currentStep < 3"
            @click="nextStep"
            class="btn btn-primary"
            data-testid="autopilot-break-next-btn"
          >
            Next
          </button>
          <button
            v-if="currentStep === 3"
            @click="handleExecute"
            :disabled="loading"
            class="btn btn-success"
            data-testid="autopilot-break-execute-btn"
          >
            {{ loading ? 'Executing...' : 'Execute Break Trade' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  legId: {
    type: String,
    default: null
  },
  strategyId: {
    type: Number,
    required: true
  },
  simulation: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['execute', 'close'])

const currentStep = ref(1)
const loading = ref(false)

const config = ref({
  executionMode: 'market',
  premiumSplit: 'equal',
  preferRoundStrikes: true,
  maxDelta: 0.30
})

const steps = [
  { number: 1, label: 'Configure' },
  { number: 2, label: 'Exit Cost' },
  { number: 3, label: 'Preview' }
]

const nextStep = () => {
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

const previousStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const handleExecute = async () => {
  loading.value = true
  try {
    await emit('execute', {
      legId: props.legId,
      ...config.value
    })
    emit('close')
  } catch (error) {
    console.error('Failed to execute break trade:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.wizard-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.wizard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.wizard-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.step-indicator {
  display: flex;
  justify-content: space-between;
  padding: 24px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 16px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: #e5e7eb;
  z-index: 0;
}

.step.completed:not(:last-child)::after {
  background: #3b82f6;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  position: relative;
  z-index: 1;
}

.step.active .step-number {
  background: #3b82f6;
  color: white;
}

.step.completed .step-number {
  background: #3b82f6;
  color: white;
}

.step-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.step.active .step-label {
  color: #111827;
  font-weight: 600;
}

.wizard-body {
  padding: 32px;
}

.wizard-body h4 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.description {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 24px 0;
}

.info-box,
.warning-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.info-box {
  background: #dbeafe;
  border: 1px solid #93c5fd;
}

.warning-box {
  background: #fef3c7;
  border: 1px solid #fde047;
}

.info-box svg {
  color: #2563eb;
  flex-shrink: 0;
}

.warning-box svg {
  color: #f59e0b;
  flex-shrink: 0;
}

.info-box p,
.warning-box span {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.info-box p:first-child {
  font-weight: 600;
  margin-bottom: 4px;
}

.config-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-select {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.cost-summary {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #e5e7eb;
}

.cost-item:last-child {
  border-bottom: none;
}

.cost-item.total {
  padding-top: 16px;
  border-top: 2px solid #d1d5db;
  margin-top: 8px;
}

.cost-item .label {
  font-size: 14px;
  color: #6b7280;
}

.cost-item .value {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.cost-item.total .value {
  font-size: 18px;
}

.cost-item .value.loss {
  color: #dc2626;
}

.cost-item .value.profit {
  color: #16a34a;
}

.preview-section h5 {
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.position-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.position-card.current {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.position-card.new {
  background: #f0fdf4;
  border: 1px solid #86efac;
}

.position-info {
  display: flex;
  gap: 12px;
  align-items: center;
}

.position-info .type {
  background: #374151;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.position-info .type.call {
  background: #2563eb;
}

.position-info .type.put {
  background: #dc2626;
}

.position-info .strike {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.position-info .qty {
  font-size: 13px;
  color: #6b7280;
}

.position-pnl {
  font-size: 16px;
  font-weight: 700;
}

.position-pnl.loss {
  color: #dc2626;
}

.position-premium {
  font-size: 14px;
  font-weight: 600;
  color: #166534;
}

.arrow-down {
  display: flex;
  justify-content: center;
  margin: 20px 0;
  color: #9ca3af;
}

.new-positions {
  margin-bottom: 24px;
}

.recovery-stats {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-item .label {
  font-size: 13px;
  color: #6b7280;
}

.stat-item .value {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.stat-item .value.profit {
  color: #16a34a;
}

.wizard-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-success {
  background: #16a34a;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #15803d;
}
</style>
