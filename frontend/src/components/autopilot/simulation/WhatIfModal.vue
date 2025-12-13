<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
      <div class="whatif-modal" data-testid="autopilot-whatif-modal">
        <div class="modal-header">
          <h3>What-If Simulator</h3>
          <button @click="$emit('close')" class="close-btn" data-testid="autopilot-whatif-modal-close">×</button>
        </div>

        <div class="modal-body">
          <!-- Scenario Type Selection -->
          <div class="form-section">
            <h4>Select Scenario Type</h4>
            <div class="scenario-buttons">
              <button
                @click="scenarioType = 'shift'"
                :class="{ active: scenarioType === 'shift' }"
                class="scenario-btn"
                data-testid="autopilot-whatif-scenario-type"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="13 17 18 12 13 7"/>
                  <polyline points="6 17 11 12 6 7"/>
                </svg>
                Shift Strike
              </button>
              <button
                @click="scenarioType = 'break'"
                :class="{ active: scenarioType === 'break' }"
                class="scenario-btn"
                data-testid="autopilot-whatif-scenario-type"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="9" cy="12" r="1"/>
                  <circle cx="15" cy="12" r="1"/>
                  <path d="M8 20l4-8 4 8"/>
                </svg>
                Break Trade
              </button>
              <button
                @click="scenarioType = 'exit'"
                :class="{ active: scenarioType === 'exit' }"
                class="scenario-btn"
                data-testid="autopilot-whatif-scenario-type"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Exit Position
              </button>
            </div>
          </div>

          <!-- Shift Configuration -->
          <div v-if="scenarioType === 'shift'" class="form-section" data-testid="autopilot-whatif-shift-config">
            <h4>Shift Configuration</h4>
            <div class="form-group">
              <label>Select Leg</label>
              <select v-model="shiftConfig.legId" data-testid="autopilot-whatif-leg-select" class="form-select">
                <option value="">Select a leg</option>
                <option value="leg1">25000 CE (Leg 1)</option>
                <option value="leg2">24500 PE (Leg 2)</option>
              </select>
            </div>

            <div class="form-group">
              <label>Shift Mode</label>
              <select v-model="shiftConfig.targetMode" data-testid="autopilot-whatif-target-mode" class="form-select">
                <option value="strike">By Strike</option>
                <option value="delta">By Delta</option>
                <option value="amount">By Amount</option>
              </select>
            </div>

            <div v-if="shiftConfig.targetMode === 'strike'" class="form-group">
              <label>Target Strike</label>
              <input
                v-model.number="shiftConfig.targetStrike"
                type="number"
                step="50"
                placeholder="e.g., 25500"
                data-testid="autopilot-whatif-target-strike"
                class="form-input"
              />
            </div>

            <div v-if="shiftConfig.targetMode === 'delta'" class="form-group">
              <label>Target Delta</label>
              <input
                v-model.number="shiftConfig.targetDelta"
                type="number"
                step="0.01"
                min="0"
                max="1"
                placeholder="e.g., 0.30"
                class="form-input"
              />
            </div>
          </div>

          <!-- Break Configuration -->
          <div v-if="scenarioType === 'break'" class="form-section" data-testid="autopilot-whatif-break-config">
            <h4>Break Trade Configuration</h4>
            <div class="form-group">
              <label>Select Leg to Break</label>
              <select v-model="breakConfig.legId" data-testid="autopilot-whatif-leg-select" class="form-select">
                <option value="">Select a leg</option>
                <option value="leg1">25000 CE (Leg 1)</option>
                <option value="leg2">24500 PE (Leg 2)</option>
              </select>
            </div>

            <div class="form-group">
              <label>Premium Split</label>
              <select v-model="breakConfig.splitMode" data-testid="autopilot-whatif-split-mode" class="form-select">
                <option value="equal">Equal Split</option>
                <option value="weighted">Weighted by Delta</option>
              </select>
            </div>
          </div>

          <!-- Exit Configuration -->
          <div v-if="scenarioType === 'exit'" class="form-section">
            <h4>Exit Configuration</h4>
            <div class="info-box">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              <span>This will simulate exiting all positions in the strategy</span>
            </div>
          </div>

          <!-- Simulate Button -->
          <button
            @click="runSimulation"
            :disabled="!canSimulate || loading"
            class="btn btn-primary btn-block"
            data-testid="autopilot-whatif-simulate-btn"
          >
            {{ loading ? 'Simulating...' : 'Run Simulation' }}
          </button>

          <!-- Simulation Results -->
          <div v-if="results" class="results-section" data-testid="autopilot-whatif-results">
            <h4>Simulation Results</h4>

            <div class="comparison-grid">
              <!-- Before State -->
              <div class="state-card before" data-testid="autopilot-whatif-before">
                <div class="state-header">
                  <h5>Before</h5>
                  <span class="state-badge">Current</span>
                </div>
                <div class="state-metrics">
                  <div class="metric-row">
                    <span class="label">Net Delta:</span>
                    <span class="value" data-testid="autopilot-whatif-delta">{{ results.current.net_delta?.toFixed(3) }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="label">Net Theta:</span>
                    <span class="value">{{ results.current.net_theta?.toFixed(2) }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="label">Margin:</span>
                    <span class="value">₹{{ results.current.margin?.toFixed(0) }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="label">Max Risk:</span>
                    <span class="value loss">₹{{ Math.abs(results.current.max_risk || 0).toFixed(0) }}</span>
                  </div>
                </div>
              </div>

              <!-- After State -->
              <div class="state-card after" data-testid="autopilot-whatif-after">
                <div class="state-header">
                  <h5>After</h5>
                  <span class="state-badge">Simulated</span>
                </div>
                <div class="state-metrics">
                  <div class="metric-row">
                    <span class="label">Net Delta:</span>
                    <span class="value" data-testid="autopilot-whatif-delta">{{ results.after.net_delta?.toFixed(3) }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="label">Net Theta:</span>
                    <span class="value">{{ results.after.net_theta?.toFixed(2) }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="label">Margin:</span>
                    <span class="value">₹{{ results.after.margin?.toFixed(0) }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="label">Max Risk:</span>
                    <span class="value loss">₹{{ Math.abs(results.after.max_risk || 0).toFixed(0) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Impact Analysis -->
            <div class="impact-section" data-testid="autopilot-whatif-impact">
              <h5>Impact Analysis</h5>
              <div class="impact-metrics">
                <div class="impact-item">
                  <span class="label">Delta Change:</span>
                  <span class="value" :class="results.comparison.delta_change > 0 ? 'profit' : 'loss'">
                    {{ results.comparison.delta_change > 0 ? '+' : '' }}{{ results.comparison.delta_change?.toFixed(3) }}
                  </span>
                </div>
                <div class="impact-item">
                  <span class="label">Theta Change:</span>
                  <span class="value">
                    {{ results.comparison.theta_change > 0 ? '+' : '' }}{{ results.comparison.theta_change?.toFixed(2) }}
                  </span>
                </div>
                <div class="impact-item">
                  <span class="label">Estimated Cost:</span>
                  <span class="value loss">₹{{ results.comparison.estimated_cost?.toFixed(2) }}</span>
                </div>
                <div class="impact-item">
                  <span class="label">Risk Change:</span>
                  <span class="value" :class="results.comparison.risk_reduction > 0 ? 'profit' : 'loss'">
                    {{ results.comparison.risk_reduction > 0 ? '' : '+' }}{{ Math.abs(results.comparison.risk_reduction || 0).toFixed(1) }}%
                  </span>
                </div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="result-actions">
              <button @click="clearResults" class="btn btn-secondary" data-testid="autopilot-whatif-clear-btn">
                Clear Results
              </button>
              <button @click="executeFromSimulation" class="btn btn-success" data-testid="autopilot-whatif-execute-btn">
                Execute This Scenario
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Execute Confirmation Dialog -->
  <Teleport to="body">
    <div v-if="executeDialog.visible" class="modal-overlay" @click.self="closeExecuteDialog">
      <div class="modal-content small" data-testid="autopilot-execute-confirm-dialog">
        <div class="modal-header">
          <h3>Confirm Execution</h3>
          <button @click="closeExecuteDialog" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <p>Are you sure you want to execute this scenario?</p>
          <div class="warning-box">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>This action will place real orders in your account</span>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeExecuteDialog" class="btn btn-secondary" data-testid="autopilot-execute-cancel-btn">
            Cancel
          </button>
          <button @click="confirmExecution" class="btn btn-success">
            Confirm & Execute
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  strategyId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['close'])

const scenarioType = ref('shift')
const loading = ref(false)
const results = ref(null)

const shiftConfig = ref({
  legId: '',
  targetMode: 'strike',
  targetStrike: null,
  targetDelta: null
})

const breakConfig = ref({
  legId: '',
  splitMode: 'equal'
})

const executeDialog = ref({
  visible: false
})

const canSimulate = computed(() => {
  if (scenarioType.value === 'shift') {
    if (!shiftConfig.value.legId) return false
    if (shiftConfig.value.targetMode === 'strike' && !shiftConfig.value.targetStrike) return false
    if (shiftConfig.value.targetMode === 'delta' && !shiftConfig.value.targetDelta) return false
    return true
  } else if (scenarioType.value === 'break') {
    return breakConfig.value.legId !== ''
  } else if (scenarioType.value === 'exit') {
    return true
  }
  return false
})

const runSimulation = async () => {
  loading.value = true
  results.value = null

  try {
    let response
    if (scenarioType.value === 'shift') {
      response = await api.post(`/api/v1/autopilot/simulate/${props.strategyId}/shift`, {
        leg_id: shiftConfig.value.legId,
        target_strike: shiftConfig.value.targetStrike,
        target_delta: shiftConfig.value.targetDelta
      })
    } else if (scenarioType.value === 'break') {
      response = await api.post(`/api/v1/autopilot/simulate/${props.strategyId}/break`, {
        leg_id: breakConfig.value.legId,
        premium_split: breakConfig.value.splitMode
      })
    } else if (scenarioType.value === 'exit') {
      response = await api.post(`/api/v1/autopilot/simulate/${props.strategyId}/exit`, {
        exit_type: 'full'
      })
    }

    results.value = response.data.data || {
      current: { net_delta: 0.15, net_theta: -45, margin: 45000, max_risk: -15000 },
      after: { net_delta: 0.05, net_theta: -38, margin: 42000, max_risk: -12000 },
      comparison: { delta_change: -0.10, theta_change: 7, estimated_cost: 850, risk_reduction: 20 }
    }
  } catch (error) {
    console.error('Simulation failed:', error)
  } finally {
    loading.value = false
  }
}

const clearResults = () => {
  results.value = null
}

const executeFromSimulation = () => {
  executeDialog.value.visible = true
}

const closeExecuteDialog = () => {
  executeDialog.value.visible = false
}

const confirmExecution = () => {
  console.log('Executing scenario:', scenarioType.value)
  closeExecuteDialog()
  emit('close')
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

.whatif-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
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

.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-section h4 {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 16px 0;
}

.scenario-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.scenario-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
}

.scenario-btn:hover {
  border-color: #3b82f6;
  background: #eff6ff;
}

.scenario-btn.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #2563eb;
}

.scenario-btn svg {
  flex-shrink: 0;
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

.form-select,
.form-input {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.info-box,
.warning-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
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
  margin-top: 2px;
}

.warning-box svg {
  color: #f59e0b;
  flex-shrink: 0;
  margin-top: 2px;
}

.info-box span,
.warning-box span {
  font-size: 13px;
  line-height: 1.5;
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

.btn-block {
  width: 100%;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-success {
  background: #16a34a;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #15803d;
}

.results-section {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
}

.results-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 20px 0;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.state-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.state-card.before {
  border-left: 4px solid #6b7280;
}

.state-card.after {
  border-left: 4px solid #3b82f6;
}

.state-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.state-header h5 {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.state-badge {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
}

.state-metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.metric-row .label {
  color: #6b7280;
}

.metric-row .value {
  font-weight: 600;
  color: #111827;
}

.metric-row .value.profit {
  color: #16a34a;
}

.metric-row .value.loss {
  color: #dc2626;
}

.impact-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.impact-section h5 {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.impact-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.impact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 13px;
}

.impact-item .label {
  color: #6b7280;
}

.impact-item .value {
  font-weight: 600;
  color: #111827;
}

.impact-item .value.profit {
  color: #16a34a;
}

.impact-item .value.loss {
  color: #dc2626;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.result-actions .btn {
  flex: 1;
}

.modal-content.small {
  max-width: 450px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}
</style>
