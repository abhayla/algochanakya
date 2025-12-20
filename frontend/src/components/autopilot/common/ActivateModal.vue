<template>
  <div v-if="show" class="modal-overlay" data-testid="autopilot-activate-modal" @click.self="handleCancel">
    <div class="modal-content">
      <!-- Header -->
      <div class="modal-header">
        <h3 class="modal-title">Activate Strategy</h3>
        <button @click="handleCancel" class="close-btn" data-testid="autopilot-activate-close">
          &times;
        </button>
      </div>

      <!-- Body -->
      <div class="modal-body">
        <p class="strategy-name">{{ strategyName }}</p>

        <!-- Trading Mode Selection -->
        <div class="trading-mode-section" data-testid="autopilot-activate-mode-section">
          <label class="section-label">Trading Mode</label>

          <div class="mode-options">
            <!-- Paper Trading Option -->
            <label
              class="mode-option"
              :class="{ 'mode-selected': tradingMode === 'paper' }"
              data-testid="autopilot-activate-paper-option"
            >
              <input
                type="radio"
                v-model="tradingMode"
                value="paper"
                class="mode-radio"
                data-testid="autopilot-activate-paper-radio"
              />
              <div class="mode-content">
                <div class="mode-header">
                  <span class="mode-indicator paper-indicator"></span>
                  <span class="mode-label">Paper Trading</span>
                </div>
                <p class="mode-description">Simulated orders. No real money at risk.</p>
              </div>
            </label>

            <!-- Live Trading Option -->
            <label
              class="mode-option"
              :class="{ 'mode-selected': tradingMode === 'live' }"
              data-testid="autopilot-activate-live-option"
            >
              <input
                type="radio"
                v-model="tradingMode"
                value="live"
                class="mode-radio"
                data-testid="autopilot-activate-live-radio"
              />
              <div class="mode-content">
                <div class="mode-header">
                  <span class="mode-indicator live-indicator"></span>
                  <span class="mode-label">Live Trading</span>
                </div>
                <p class="mode-description">Real orders placed with your broker.</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Live Mode Warning -->
        <div
          v-if="showLiveWarning"
          class="live-warning"
          data-testid="autopilot-activate-live-warning"
        >
          <span class="warning-icon">⚠️</span>
          <div class="warning-content">
            <p class="warning-title">Live Trading Warning</p>
            <p class="warning-text">
              Real orders will be placed with your broker.
              Ensure you understand the strategy's risk parameters before proceeding.
            </p>
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="error-message" data-testid="autopilot-activate-error">
          {{ error }}
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button
          @click="handleCancel"
          class="btn-secondary"
          data-testid="autopilot-activate-cancel"
        >
          Cancel
        </button>
        <button
          @click="handleActivate"
          :disabled="isActivating"
          :class="['btn-primary', tradingMode === 'live' ? 'btn-live' : 'btn-paper']"
          data-testid="autopilot-activate-confirm"
        >
          {{ isActivating ? 'Activating...' : `Activate (${tradingMode === 'live' ? 'Live' : 'Paper'})` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const props = defineProps({
  show: { type: Boolean, default: false },
  strategyId: { type: Number, required: true },
  strategyName: { type: String, default: '' }
})

const emit = defineEmits(['close', 'activated'])
const store = useAutopilotStore()

// Trading mode: 'live' or 'paper'
const tradingMode = ref('paper')
const isActivating = ref(false)
const error = ref(null)

// Reset state when modal opens
watch(() => props.show, (newVal) => {
  if (newVal) {
    // Default to paper mode from settings
    tradingMode.value = store.settings?.paper_trading_mode ? 'paper' : 'live'
    error.value = null
    isActivating.value = false
  }
})

// Computed: Warning visibility
const showLiveWarning = computed(() => tradingMode.value === 'live')

const handleActivate = async () => {
  isActivating.value = true
  error.value = null

  try {
    const result = await store.activateStrategy(props.strategyId, {
      paperTrading: tradingMode.value === 'paper'
    })
    emit('activated', result)
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to activate strategy'
  } finally {
    isActivating.value = false
  }
}

const handleCancel = () => {
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
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
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
  transition: all 0.2s;
}

.close-btn:hover {
  background-color: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 24px;
}

.strategy-name {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 20px 0;
}

.trading-mode-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
}

.mode-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mode-option {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.mode-option:hover {
  border-color: #d1d5db;
  background-color: #f9fafb;
}

.mode-option.mode-selected {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.mode-radio {
  margin-top: 2px;
  cursor: pointer;
}

.mode-content {
  flex: 1;
}

.mode-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mode-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.paper-indicator {
  background-color: #f59e0b;
}

.live-indicator {
  background-color: #10b981;
}

.mode-label {
  font-weight: 600;
  font-size: 15px;
  color: #111827;
}

.mode-description {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

.live-warning {
  background-color: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    max-height: 0;
    opacity: 0;
  }
  to {
    max-height: 200px;
    opacity: 1;
  }
}

.warning-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 14px;
  font-weight: 600;
  color: #92400e;
  margin: 0 0 4px 0;
}

.warning-text {
  font-size: 13px;
  color: #78350f;
  margin: 0;
  line-height: 1.5;
}

.error-message {
  background-color: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 12px;
  color: #991b1b;
  font-size: 14px;
  margin-bottom: 16px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-secondary,
.btn-primary {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-secondary {
  background-color: white;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.btn-primary {
  color: white;
}

.btn-paper {
  background-color: #f59e0b;
}

.btn-paper:hover {
  background-color: #d97706;
}

.btn-live {
  background-color: #10b981;
}

.btn-live:hover {
  background-color: #059669;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
