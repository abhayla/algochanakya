<template>
  <div class="shift-leg-modal-overlay" @click.self="handleClose">
    <div class="modal-container">
      <!-- Header -->
      <div class="modal-header">
        <h3>
          <i class="fas fa-arrows-left-right"></i>
          Shift Leg Position
        </h3>
        <button class="close-btn" @click="handleClose" aria-label="Close modal">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <!-- Current Leg Info -->
      <div v-if="leg" class="current-leg-info">
        <h4>Current Position</h4>
        <div class="leg-details">
          <div class="detail-item">
            <span class="label">Type:</span>
            <span class="value">
              <span class="option-type" :class="leg.contract_type.toLowerCase()">
                {{ leg.contract_type }}
              </span>
            </span>
          </div>
          <div class="detail-item">
            <span class="label">Current Strike:</span>
            <span class="value strike">{{ formatStrike(leg.strike) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">Entry Price:</span>
            <span class="value">{{ formatCurrency(leg.entry_price) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">LTP:</span>
            <span class="value">{{ formatCurrency(leg.ltp) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">Delta:</span>
            <span class="value">{{ formatDelta(leg.delta) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">P&L:</span>
            <span class="value" :class="getPnLClass(leg.unrealized_pnl)">
              {{ formatCurrency(leg.unrealized_pnl) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Shift Mode Selection -->
      <div class="shift-modes">
        <h4>Shift Method</h4>
        <div class="mode-tabs">
          <button
            v-for="mode in shiftModes"
            :key="mode.id"
            class="mode-tab"
            :class="{ active: selectedMode === mode.id }"
            @click="selectMode(mode.id)"
          >
            <i :class="mode.icon"></i>
            <span>{{ mode.label }}</span>
          </button>
        </div>
      </div>

      <!-- Mode Content -->
      <div class="mode-content">
        <!-- Mode 1: Shift by Strike -->
        <div v-if="selectedMode === 'strike'" class="shift-mode-panel">
          <h4>Shift to Specific Strike</h4>
          <p class="mode-description">
            Enter the exact strike price you want to shift this leg to.
          </p>

          <div class="input-group">
            <label for="target-strike">Target Strike</label>
            <input
              id="target-strike"
              type="number"
              v-model.number="targetStrike"
              :step="strikeStep"
              placeholder="Enter strike price"
              class="strike-input"
            />
          </div>

          <div v-if="targetStrike && targetStrike !== leg?.strike" class="shift-preview">
            <div class="preview-row">
              <span class="label">Current Strike:</span>
              <span class="value">{{ formatStrike(leg?.strike) }}</span>
            </div>
            <div class="preview-row arrow">
              <i class="fas fa-arrow-down"></i>
            </div>
            <div class="preview-row">
              <span class="label">New Strike:</span>
              <span class="value highlight">{{ formatStrike(targetStrike) }}</span>
            </div>
            <div class="preview-row">
              <span class="label">Strike Difference:</span>
              <span class="value">
                {{ formatStrikeDiff(targetStrike - (leg?.strike || 0)) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Mode 2: Shift by Delta -->
        <div v-if="selectedMode === 'delta'" class="shift-mode-panel">
          <h4>Shift to Target Delta</h4>
          <p class="mode-description">
            Find a new strike that matches your desired delta value.
          </p>

          <div class="input-group">
            <label for="target-delta">Target Delta</label>
            <input
              id="target-delta"
              type="number"
              v-model.number="targetDelta"
              step="0.01"
              min="-1"
              max="1"
              placeholder="e.g., 0.30"
              class="delta-input"
            />
            <span class="input-hint">
              Delta range: -1.00 (deep ITM PUT) to 1.00 (deep ITM CALL)
            </span>
          </div>

          <div class="delta-presets">
            <span class="preset-label">Common Deltas:</span>
            <button
              v-for="preset in deltaPresets"
              :key="preset.value"
              class="preset-btn"
              @click="targetDelta = preset.value"
              :class="{ active: targetDelta === preset.value }"
            >
              {{ preset.label }}
            </button>
          </div>

          <div v-if="targetDelta" class="shift-preview">
            <div class="preview-row">
              <span class="label">Current Delta:</span>
              <span class="value">{{ formatDelta(leg?.delta) }}</span>
            </div>
            <div class="preview-row arrow">
              <i class="fas fa-arrow-down"></i>
            </div>
            <div class="preview-row">
              <span class="label">Target Delta:</span>
              <span class="value highlight">{{ formatDelta(targetDelta) }}</span>
            </div>
            <div class="preview-row">
              <span class="label">Delta Change:</span>
              <span class="value">
                {{ formatDelta(Math.abs(targetDelta - (leg?.delta || 0))) }}
              </span>
            </div>
          </div>

          <div class="info-box">
            <i class="fas fa-info-circle"></i>
            <p>
              The system will automatically find the closest strike that matches your
              target delta based on current market conditions.
            </p>
          </div>
        </div>

        <!-- Mode 3: Shift by Direction -->
        <div v-if="selectedMode === 'direction'" class="shift-mode-panel">
          <h4>Shift by Direction & Amount</h4>
          <p class="mode-description">
            Move the leg closer to or farther from the current spot price by a specific number of points.
          </p>

          <div class="direction-controls">
            <div class="control-group">
              <label>Direction</label>
              <div class="direction-buttons">
                <button
                  class="direction-btn"
                  :class="{ active: shiftDirection === 'closer' }"
                  @click="shiftDirection = 'closer'"
                >
                  <i class="fas fa-compress-arrows-alt"></i>
                  <span>Closer to Spot</span>
                  <small>More aggressive</small>
                </button>
                <button
                  class="direction-btn"
                  :class="{ active: shiftDirection === 'farther' }"
                  @click="shiftDirection = 'farther'"
                >
                  <i class="fas fa-expand-arrows-alt"></i>
                  <span>Farther from Spot</span>
                  <small>More conservative</small>
                </button>
              </div>
            </div>

            <div class="control-group">
              <label for="shift-amount">Shift Amount (points)</label>
              <input
                id="shift-amount"
                type="number"
                v-model.number="shiftAmount"
                :step="strikeStep"
                min="0"
                placeholder="Enter points to shift"
                class="amount-input"
              />
              <span class="input-hint">
                How many points to move from current strike
              </span>
            </div>

            <div class="amount-presets">
              <span class="preset-label">Quick Amounts:</span>
              <button
                v-for="preset in amountPresets"
                :key="preset"
                class="preset-btn"
                @click="shiftAmount = preset"
                :class="{ active: shiftAmount === preset }"
              >
                {{ preset }}
              </button>
            </div>
          </div>

          <div v-if="shiftDirection && shiftAmount" class="shift-preview">
            <div class="preview-row">
              <span class="label">Current Strike:</span>
              <span class="value">{{ formatStrike(leg?.strike) }}</span>
            </div>
            <div class="preview-row arrow">
              <i class="fas fa-arrow-down"></i>
            </div>
            <div class="preview-row">
              <span class="label">New Strike (approx):</span>
              <span class="value highlight">
                {{ formatStrike(calculateNewStrike()) }}
              </span>
            </div>
            <div class="preview-row">
              <span class="label">Direction:</span>
              <span class="value">
                {{ shiftDirection === 'closer' ? 'Toward ATM' : 'Away from ATM' }}
                ({{ shiftAmount }} points)
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Execution Mode -->
      <div class="execution-mode">
        <h4>Execution Mode</h4>
        <div class="mode-radios">
          <label class="radio-label">
            <input
              type="radio"
              value="market"
              v-model="executionMode"
            />
            <div class="radio-content">
              <span class="radio-title">Market Order</span>
              <span class="radio-description">Execute immediately at current market price</span>
            </div>
          </label>
          <label class="radio-label">
            <input
              type="radio"
              value="limit"
              v-model="executionMode"
            />
            <div class="radio-content">
              <span class="radio-title">Limit Order</span>
              <span class="radio-description">Set a price limit for execution</span>
            </div>
          </label>
        </div>

        <div v-if="executionMode === 'limit'" class="limit-price-input">
          <label for="limit-offset">Limit Price Offset (%)</label>
          <input
            id="limit-offset"
            type="number"
            v-model.number="limitOffset"
            step="0.1"
            placeholder="e.g., 2.0"
            class="offset-input"
          />
          <span class="input-hint">
            Percentage offset from LTP for limit price (positive = higher price)
          </span>
        </div>
      </div>

      <!-- Cost Preview (placeholder) -->
      <div v-if="canShift" class="cost-preview">
        <div class="preview-item">
          <span class="label">Estimated Cost:</span>
          <span class="value">₹ TBD</span>
        </div>
        <div class="preview-item">
          <span class="label">Execution Type:</span>
          <span class="value">{{ executionMode === 'market' ? 'Market' : 'Limit' }}</span>
        </div>
      </div>

      <!-- Footer Actions -->
      <div class="modal-footer">
        <button @click="handleClose" class="btn-secondary" :disabled="shifting">
          <i class="fas fa-times"></i>
          Cancel
        </button>
        <button
          @click="executeShift"
          class="btn-primary"
          :disabled="!canShift || shifting"
        >
          <i v-if="!shifting" class="fas fa-arrows-left-right"></i>
          <i v-else class="fas fa-spinner fa-spin"></i>
          {{ shifting ? 'Shifting...' : 'Execute Shift' }}
        </button>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="error-banner">
        <i class="fas fa-exclamation-circle"></i>
        <span>{{ error }}</span>
        <button @click="error = null" class="error-close">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  },
  leg: {
    type: Object,
    required: true
  },
  spotPrice: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['close', 'success'])

// Shift modes
const shiftModes = [
  { id: 'strike', label: 'By Strike', icon: 'fas fa-hashtag' },
  { id: 'delta', label: 'By Delta', icon: 'fas fa-chart-line' },
  { id: 'direction', label: 'By Direction', icon: 'fas fa-arrows-alt-h' }
]

// State
const selectedMode = ref('strike')
const targetStrike = ref(null)
const targetDelta = ref(null)
const shiftDirection = ref('farther')
const shiftAmount = ref(null)
const executionMode = ref('market')
const limitOffset = ref(0)
const shifting = ref(false)
const error = ref(null)

// Constants
const strikeStep = ref(50)
const deltaPresets = [
  { label: '0.10', value: 0.10 },
  { label: '0.20', value: 0.20 },
  { label: '0.30', value: 0.30 },
  { label: '0.40', value: 0.40 },
  { label: '0.50', value: 0.50 }
]
const amountPresets = [50, 100, 150, 200, 250, 300]

// Computed
const canShift = computed(() => {
  if (selectedMode.value === 'strike') {
    return targetStrike.value && targetStrike.value !== props.leg?.strike
  }
  if (selectedMode.value === 'delta') {
    return targetDelta.value !== null && targetDelta.value >= -1 && targetDelta.value <= 1
  }
  if (selectedMode.value === 'direction') {
    return shiftDirection.value && shiftAmount.value && shiftAmount.value > 0
  }
  return false
})

// Methods
function selectMode(mode) {
  selectedMode.value = mode
  error.value = null
}

function calculateNewStrike() {
  if (!props.leg?.strike || !shiftAmount.value) return null

  const currentStrike = Number(props.leg.strike)
  const amount = Number(shiftAmount.value)

  // Determine if we should add or subtract based on option type and direction
  const isCE = props.leg.contract_type === 'CE'

  if (shiftDirection.value === 'closer') {
    // Closer to spot means:
    // - For CE: decrease strike (move down toward spot)
    // - For PE: increase strike (move up toward spot)
    return isCE ? currentStrike - amount : currentStrike + amount
  } else {
    // Farther from spot means:
    // - For CE: increase strike (move up away from spot)
    // - For PE: decrease strike (move down away from spot)
    return isCE ? currentStrike + amount : currentStrike - amount
  }
}

async function executeShift() {
  error.value = null
  shifting.value = true

  try {
    const payload = {
      execution_mode: executionMode.value
    }

    if (executionMode.value === 'limit') {
      payload.limit_offset = limitOffset.value
    }

    // Set parameters based on mode
    if (selectedMode.value === 'strike') {
      payload.target_strike = targetStrike.value
    } else if (selectedMode.value === 'delta') {
      payload.target_delta = targetDelta.value
    } else if (selectedMode.value === 'direction') {
      payload.shift_direction = shiftDirection.value
      payload.shift_amount = shiftAmount.value
    }

    const response = await api.post(
      `/api/v1/autopilot/strategies/${props.strategyId}/legs/${props.leg.leg_id}/shift`,
      payload
    )

    emit('success', response.data)
    emit('close')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to execute shift'
    console.error('Shift error:', err)
  } finally {
    shifting.value = false
  }
}

function handleClose() {
  if (!shifting.value) {
    emit('close')
  }
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

function formatStrikeDiff(diff) {
  if (!diff) return '0'
  const sign = diff > 0 ? '+' : ''
  return `${sign}${diff.toFixed(0)}`
}

function getPnLClass(pnl) {
  if (pnl == null) return ''
  return Number(pnl) >= 0 ? 'profit' : 'loss'
}
</script>

<style scoped>
.shift-leg-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
  padding: 20px;
}

.modal-container {
  background: #1a1d2e;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

/* Header */
.modal-header {
  background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
  color: white;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: 12px 12px 0 0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Current Leg Info */
.current-leg-info {
  padding: 20px 24px;
  background: #151825;
  border-bottom: 1px solid #2d3142;
}

.current-leg-info h4 {
  margin: 0 0 12px 0;
  color: white;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.leg-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item .label {
  font-size: 12px;
  color: #8b92ab;
}

.detail-item .value {
  font-size: 14px;
  color: white;
  font-weight: 600;
}

.option-type {
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
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
  color: #a5b4fc;
}

.profit {
  color: #10b981;
}

.loss {
  color: #ef4444;
}

/* Shift Modes */
.shift-modes {
  padding: 20px 24px;
  border-bottom: 1px solid #2d3142;
}

.shift-modes h4 {
  margin: 0 0 16px 0;
  color: white;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.mode-tab {
  padding: 12px;
  background: #151825;
  border: 2px solid #2d3142;
  border-radius: 8px;
  color: #8b92ab;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}

.mode-tab:hover {
  border-color: #8b5cf6;
  color: #a78bfa;
}

.mode-tab.active {
  background: rgba(139, 92, 246, 0.1);
  border-color: #8b5cf6;
  color: #a78bfa;
}

.mode-tab i {
  font-size: 18px;
}

/* Mode Content */
.mode-content {
  padding: 24px;
}

.shift-mode-panel h4 {
  margin: 0 0 8px 0;
  color: white;
  font-size: 16px;
}

.mode-description {
  color: #8b92ab;
  font-size: 14px;
  margin: 0 0 20px 0;
  line-height: 1.5;
}

/* Input Groups */
.input-group,
.control-group {
  margin-bottom: 20px;
}

.input-group label,
.control-group label {
  display: block;
  color: white;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.strike-input,
.delta-input,
.amount-input,
.offset-input {
  width: 100%;
  padding: 12px 16px;
  background: #151825;
  border: 2px solid #2d3142;
  border-radius: 8px;
  color: white;
  font-size: 16px;
  transition: all 0.2s;
}

.strike-input:focus,
.delta-input:focus,
.amount-input:focus,
.offset-input:focus {
  outline: none;
  border-color: #8b5cf6;
  background: #1a1d2e;
}

.input-hint {
  display: block;
  font-size: 12px;
  color: #8b92ab;
  margin-top: 6px;
}

/* Delta Presets */
.delta-presets,
.amount-presets {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.preset-label {
  font-size: 13px;
  color: #8b92ab;
  font-weight: 500;
}

.preset-btn {
  padding: 6px 12px;
  background: #151825;
  border: 1px solid #2d3142;
  border-radius: 6px;
  color: #8b92ab;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.preset-btn:hover {
  border-color: #8b5cf6;
  color: #a78bfa;
}

.preset-btn.active {
  background: rgba(139, 92, 246, 0.2);
  border-color: #8b5cf6;
  color: #a78bfa;
}

/* Direction Controls */
.direction-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 8px;
}

.direction-btn {
  padding: 16px;
  background: #151825;
  border: 2px solid #2d3142;
  border-radius: 8px;
  color: #8b92ab;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}

.direction-btn i {
  font-size: 24px;
}

.direction-btn span {
  font-weight: 600;
  font-size: 14px;
}

.direction-btn small {
  font-size: 12px;
  color: #6b7280;
}

.direction-btn:hover {
  border-color: #8b5cf6;
  color: #a78bfa;
}

.direction-btn.active {
  background: rgba(139, 92, 246, 0.1);
  border-color: #8b5cf6;
  color: #a78bfa;
}

/* Shift Preview */
.shift-preview {
  background: #151825;
  border: 1px solid #2d3142;
  border-radius: 8px;
  padding: 16px;
  margin-top: 20px;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #2d3142;
}

.preview-row:last-child {
  border-bottom: none;
}

.preview-row.arrow {
  justify-content: center;
  color: #8b5cf6;
  font-size: 20px;
  padding: 4px 0;
  border-bottom: none;
}

.preview-row .label {
  color: #8b92ab;
  font-size: 14px;
}

.preview-row .value {
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.preview-row .value.highlight {
  color: #a78bfa;
  font-size: 16px;
}

/* Execution Mode */
.execution-mode {
  padding: 20px 24px;
  border-top: 1px solid #2d3142;
  background: #151825;
}

.execution-mode h4 {
  margin: 0 0 16px 0;
  color: white;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mode-radios {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #1a1d2e;
  border: 2px solid #2d3142;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-label:hover {
  border-color: #8b5cf6;
}

.radio-label input[type="radio"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.radio-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.radio-title {
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.radio-description {
  color: #8b92ab;
  font-size: 12px;
}

.limit-price-input {
  margin-top: 16px;
}

/* Cost Preview */
.cost-preview {
  padding: 16px 24px;
  background: rgba(139, 92, 246, 0.05);
  border-top: 1px solid #2d3142;
  display: flex;
  justify-content: space-between;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preview-item .label {
  font-size: 12px;
  color: #8b92ab;
}

.preview-item .value {
  font-size: 16px;
  color: white;
  font-weight: 600;
}

/* Info Box */
.info-box {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  margin-top: 16px;
}

.info-box i {
  color: #a5b4fc;
  font-size: 18px;
  flex-shrink: 0;
}

.info-box p {
  margin: 0;
  color: #a5b4fc;
  font-size: 13px;
  line-height: 1.5;
}

/* Footer */
.modal-footer {
  padding: 20px 24px;
  background: #151825;
  border-top: 1px solid #2d3142;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  position: sticky;
  bottom: 0;
}

/* Buttons */
button {
  padding: 10px 20px;
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
  background: #8b5cf6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #7c3aed;
  transform: translateY(-1px);
}

.btn-secondary {
  background: #2d3142;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #3d4252;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Error Banner */
.error-banner {
  position: sticky;
  bottom: 80px;
  margin: 0 24px 20px 24px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fca5a5;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.error-banner i {
  font-size: 18px;
  flex-shrink: 0;
}

.error-close {
  margin-left: auto;
  background: transparent;
  padding: 4px 8px;
  color: #fca5a5;
}

.error-close:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* Responsive */
@media (max-width: 768px) {
  .leg-details {
    grid-template-columns: repeat(2, 1fr);
  }

  .mode-tabs {
    grid-template-columns: 1fr;
  }

  .direction-buttons {
    grid-template-columns: 1fr;
  }
}
</style>
