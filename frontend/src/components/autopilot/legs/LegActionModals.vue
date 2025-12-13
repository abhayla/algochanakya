<template>
  <div>
    <!-- Exit Leg Modal -->
    <Teleport to="body">
      <div v-if="exitModal.visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-content" data-testid="autopilot-exit-leg-modal">
          <div class="modal-header">
            <h3>Exit Leg</h3>
            <button @click="$emit('close')" class="close-btn">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label>Execution Mode</label>
              <select
                v-model="exitModal.executionMode"
                data-testid="autopilot-exit-mode-select"
                class="form-select"
              >
                <option value="market">Market Order</option>
                <option value="limit">Limit Order</option>
              </select>
            </div>

            <div v-if="exitModal.executionMode === 'limit'" class="form-group">
              <label>Limit Price</label>
              <input
                v-model.number="exitModal.limitPrice"
                type="number"
                step="0.5"
                placeholder="Enter limit price"
                data-testid="autopilot-exit-limit-price"
                class="form-input"
              />
            </div>

            <div class="warning-box">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>This will place an order to exit the selected leg</span>
            </div>
          </div>

          <div class="modal-footer">
            <button
              @click="$emit('close')"
              class="btn btn-secondary"
              data-testid="autopilot-exit-modal-cancel"
            >
              Cancel
            </button>
            <button
              @click="handleExit"
              :disabled="exitModal.loading"
              class="btn btn-primary"
              data-testid="autopilot-exit-modal-confirm"
            >
              {{ exitModal.loading ? 'Exiting...' : 'Exit Leg' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Shift Leg Modal -->
    <Teleport to="body">
      <div v-if="shiftModal.visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-content" data-testid="autopilot-shift-leg-modal">
          <div class="modal-header">
            <h3>Shift Leg</h3>
            <button @click="$emit('close')" class="close-btn">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label>Shift Mode</label>
              <select
                v-model="shiftMode"
                data-testid="autopilot-shift-mode-select"
                class="form-select"
              >
                <option value="strike">By Strike</option>
                <option value="delta">By Delta</option>
                <option value="amount">By Amount</option>
              </select>
            </div>

            <div v-if="shiftMode === 'strike'" class="form-group">
              <label>Target Strike</label>
              <input
                v-model.number="shiftModal.targetStrike"
                type="number"
                step="50"
                placeholder="e.g., 25000"
                data-testid="autopilot-shift-target-strike"
                class="form-input"
              />
            </div>

            <div v-if="shiftMode === 'delta'" class="form-group">
              <label>Target Delta (0-1)</label>
              <input
                v-model.number="shiftModal.targetDelta"
                type="number"
                step="0.01"
                min="0"
                max="1"
                placeholder="e.g., 0.30"
                data-testid="autopilot-shift-target-delta"
                class="form-input"
              />
            </div>

            <div v-if="shiftMode === 'amount'" class="form-group">
              <label>Shift Amount (points)</label>
              <input
                v-model.number="shiftModal.shiftAmount"
                type="number"
                step="50"
                placeholder="e.g., 100"
                data-testid="autopilot-shift-amount"
                class="form-input"
              />
              <div class="form-group" style="margin-top: 12px;">
                <label>Direction</label>
                <select v-model="shiftModal.shiftDirection" class="form-select">
                  <option value="closer">Closer to Spot</option>
                  <option value="further">Further from Spot</option>
                </select>
              </div>
            </div>

            <!-- Preview Section -->
            <div v-if="shiftPreview" class="preview-box" data-testid="autopilot-shift-preview">
              <h4>Preview</h4>
              <div class="preview-content">
                <div class="preview-item">
                  <span>New Strike:</span>
                  <strong>{{ shiftPreview.newStrike }}</strong>
                </div>
                <div class="preview-item">
                  <span>Estimated Cost:</span>
                  <strong>₹{{ shiftPreview.estimatedCost?.toFixed(2) }}</strong>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="$emit('close')" class="btn btn-secondary">
              Cancel
            </button>
            <button
              @click="handleShift"
              :disabled="!canShift || shiftModal.loading"
              class="btn btn-primary"
            >
              {{ shiftModal.loading ? 'Shifting...' : 'Shift Leg' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Roll Leg Modal -->
    <Teleport to="body">
      <div v-if="rollModal.visible" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-content" data-testid="autopilot-roll-leg-modal">
          <div class="modal-header">
            <h3>Roll Leg</h3>
            <button @click="$emit('close')" class="close-btn">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label>Target Expiry</label>
              <select
                v-model="rollModal.targetExpiry"
                data-testid="autopilot-roll-expiry-select"
                class="form-select"
              >
                <option value="">Select expiry</option>
                <option value="2024-12-26">26 Dec 2024</option>
                <option value="2025-01-02">02 Jan 2025</option>
                <option value="2025-01-09">09 Jan 2025</option>
              </select>
            </div>

            <div class="form-group">
              <label>Target Strike (Optional)</label>
              <input
                v-model.number="rollModal.targetStrike"
                type="number"
                step="50"
                placeholder="Leave blank to keep same strike"
                data-testid="autopilot-roll-target-strike"
                class="form-input"
              />
              <small class="hint">If blank, will roll to same strike in new expiry</small>
            </div>

            <div class="info-box">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              <span>Rolling will exit current position and enter new position in selected expiry</span>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="$emit('close')" class="btn btn-secondary">
              Cancel
            </button>
            <button
              @click="handleRoll"
              :disabled="!rollModal.targetExpiry || rollModal.loading"
              class="btn btn-primary"
            >
              {{ rollModal.loading ? 'Rolling...' : 'Roll Leg' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  exitModal: {
    type: Object,
    required: true
  },
  shiftModal: {
    type: Object,
    required: true
  },
  rollModal: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['exit', 'shift', 'roll', 'close'])

const shiftMode = ref('strike')
const shiftPreview = ref(null)

const canShift = computed(() => {
  if (shiftMode.value === 'strike') {
    return props.shiftModal.targetStrike !== null && props.shiftModal.targetStrike > 0
  } else if (shiftMode.value === 'delta') {
    return props.shiftModal.targetDelta !== null && props.shiftModal.targetDelta >= 0 && props.shiftModal.targetDelta <= 1
  } else if (shiftMode.value === 'amount') {
    return props.shiftModal.shiftAmount !== null && props.shiftModal.shiftDirection
  }
  return false
})

const handleExit = () => {
  emit('exit', {
    legId: props.exitModal.legId,
    executionMode: props.exitModal.executionMode,
    limitPrice: props.exitModal.limitPrice
  })
}

const handleShift = () => {
  const payload = {
    legId: props.shiftModal.legId,
    mode: shiftMode.value
  }

  if (shiftMode.value === 'strike') {
    payload.targetStrike = props.shiftModal.targetStrike
  } else if (shiftMode.value === 'delta') {
    payload.targetDelta = props.shiftModal.targetDelta
  } else if (shiftMode.value === 'amount') {
    payload.shiftAmount = props.shiftModal.shiftAmount
    payload.shiftDirection = props.shiftModal.shiftDirection
  }

  emit('shift', payload)
}

const handleRoll = () => {
  emit('roll', {
    legId: props.rollModal.legId,
    targetExpiry: props.rollModal.targetExpiry,
    targetStrike: props.rollModal.targetStrike
  })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  font-size: 18px;
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
  gap: 20px;
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

.hint {
  font-size: 12px;
  color: #6b7280;
}

.warning-box,
.info-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
}

.warning-box {
  background: #fef3c7;
  border: 1px solid #fde047;
  color: #92400e;
}

.info-box {
  background: #dbeafe;
  border: 1px solid #93c5fd;
  color: #1e40af;
}

.warning-box svg,
.info-box svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.warning-box span,
.info-box span {
  font-size: 13px;
  line-height: 1.5;
}

.preview-box {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 16px;
}

.preview-box h4 {
  font-size: 14px;
  font-weight: 600;
  color: #166534;
  margin: 0 0 12px 0;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.preview-item span {
  color: #6b7280;
}

.preview-item strong {
  color: #111827;
  font-weight: 600;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
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
</style>
