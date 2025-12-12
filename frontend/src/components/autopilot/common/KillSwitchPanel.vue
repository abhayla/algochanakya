<script setup>
/**
 * Kill Switch Panel Component - Phase 3
 *
 * Shows kill switch status and provides trigger/reset controls.
 * Includes animated visual indicator and confirmation modals.
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const props = defineProps({
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['triggered', 'reset'])

const store = useAutopilotStore()

// State
const status = ref(null)
const loading = ref(false)
const showTriggerModal = ref(false)
const showResetModal = ref(false)
const triggerReason = ref('')

// Computed
const isEnabled = computed(() => status.value?.enabled || false)
const triggeredAt = computed(() => {
  if (!status.value?.triggered_at) return null
  return new Date(status.value.triggered_at).toLocaleString()
})
const affectedStrategies = computed(() => status.value?.affected_strategies || 0)

// Methods
const fetchStatus = async () => {
  try {
    status.value = await store.getKillSwitchStatus()
  } catch (error) {
    console.error('Failed to fetch kill switch status:', error)
  }
}

const openTriggerModal = () => {
  triggerReason.value = ''
  showTriggerModal.value = true
}

const confirmTrigger = async () => {
  loading.value = true
  try {
    await store.triggerKillSwitch(triggerReason.value || null, true)
    await fetchStatus()
    showTriggerModal.value = false
    emit('triggered')
  } catch (error) {
    console.error('Failed to trigger kill switch:', error)
  } finally {
    loading.value = false
  }
}

const openResetModal = () => {
  showResetModal.value = true
}

const confirmReset = async () => {
  loading.value = true
  try {
    await store.resetKillSwitch()
    await fetchStatus()
    showResetModal.value = false
    emit('reset')
  } catch (error) {
    console.error('Failed to reset kill switch:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
})

// Refresh status when dashboard updates
watch(
  () => store.dashboardSummary,
  () => fetchStatus(),
  { deep: true }
)
</script>

<template>
  <div
    class="kill-switch-panel"
    :class="{ 'compact': compact, 'enabled': isEnabled }"
    data-testid="autopilot-kill-switch-panel"
  >
    <!-- Status Indicator -->
    <div class="kill-switch-status">
      <div
        class="status-indicator"
        :class="isEnabled ? 'indicator-active' : 'indicator-inactive'"
      >
        <div class="indicator-ring"></div>
        <div class="indicator-core"></div>
      </div>

      <div class="status-text">
        <span class="status-label">Kill Switch</span>
        <span
          class="status-value"
          :class="isEnabled ? 'value-active' : 'value-inactive'"
        >
          {{ isEnabled ? 'ACTIVE' : 'Ready' }}
        </span>
      </div>
    </div>

    <!-- Details (not in compact mode) -->
    <div v-if="!compact && status" class="kill-switch-details">
      <div v-if="isEnabled" class="detail-row">
        <span class="detail-label">Triggered at:</span>
        <span class="detail-value">{{ triggeredAt }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Active strategies:</span>
        <span class="detail-value">{{ affectedStrategies }}</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="kill-switch-actions">
      <button
        v-if="!isEnabled"
        @click="openTriggerModal"
        :disabled="affectedStrategies === 0"
        class="trigger-btn"
        data-testid="autopilot-kill-switch-trigger-btn"
      >
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
        </svg>
        <span>{{ compact ? 'Kill' : 'Trigger Kill Switch' }}</span>
      </button>

      <button
        v-else
        @click="openResetModal"
        class="reset-btn"
        data-testid="autopilot-kill-switch-reset-btn"
      >
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
        <span>{{ compact ? 'Reset' : 'Reset Kill Switch' }}</span>
      </button>
    </div>

    <!-- Trigger Confirmation Modal -->
    <div
      v-if="showTriggerModal"
      class="modal-overlay"
      data-testid="autopilot-kill-switch-trigger-modal"
    >
      <div class="modal-content">
        <div class="modal-header danger">
          <svg class="modal-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
          </svg>
          <h3 class="modal-title">Activate Kill Switch</h3>
        </div>

        <div class="modal-body">
          <p class="warning-text">
            This will immediately:
          </p>
          <ul class="warning-list">
            <li>Exit all active positions at market price</li>
            <li>Pause all waiting strategies</li>
            <li>Block new strategy activations</li>
          </ul>

          <div class="form-group">
            <label class="form-label">Reason (optional)</label>
            <input
              v-model="triggerReason"
              type="text"
              class="form-input"
              placeholder="e.g., Market volatility, Risk limit reached"
              data-testid="autopilot-kill-switch-reason-input"
            />
          </div>

          <p class="affected-count">
            <strong>{{ affectedStrategies }}</strong> strategies will be affected.
          </p>
        </div>

        <div class="modal-actions">
          <button
            @click="showTriggerModal = false"
            class="btn-cancel"
            :disabled="loading"
          >
            Cancel
          </button>
          <button
            @click="confirmTrigger"
            class="btn-danger"
            :disabled="loading"
            data-testid="autopilot-kill-switch-confirm-trigger"
          >
            {{ loading ? 'Activating...' : 'Activate Kill Switch' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Reset Confirmation Modal -->
    <div
      v-if="showResetModal"
      class="modal-overlay"
      data-testid="autopilot-kill-switch-reset-modal"
    >
      <div class="modal-content">
        <div class="modal-header info">
          <svg class="modal-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
          </svg>
          <h3 class="modal-title">Reset Kill Switch</h3>
        </div>

        <div class="modal-body">
          <p class="info-text">
            This will allow new strategy activations again.
          </p>
          <p class="info-text">
            Paused strategies will remain paused - you'll need to resume them manually.
          </p>
        </div>

        <div class="modal-actions">
          <button
            @click="showResetModal = false"
            class="btn-cancel"
            :disabled="loading"
          >
            Cancel
          </button>
          <button
            @click="confirmReset"
            class="btn-primary"
            :disabled="loading"
            data-testid="autopilot-kill-switch-confirm-reset"
          >
            {{ loading ? 'Resetting...' : 'Reset Kill Switch' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kill-switch-panel {
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--kite-border);
}

.kill-switch-panel.enabled {
  border-color: var(--kite-red);
  background: linear-gradient(135deg, #fff5f5 0%, white 100%);
}

.kill-switch-panel.compact {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Status Indicator */
.kill-switch-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  position: relative;
  width: 40px;
  height: 40px;
}

.compact .status-indicator {
  width: 24px;
  height: 24px;
}

.indicator-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid currentColor;
  opacity: 0.3;
}

.indicator-core {
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: currentColor;
}

.compact .indicator-core {
  inset: 4px;
}

.indicator-inactive {
  color: var(--kite-green);
}

.indicator-active {
  color: var(--kite-red);
}

.indicator-active .indicator-ring {
  animation: pulse-ring 1.5s ease-out infinite;
}

.indicator-active .indicator-core {
  animation: pulse-core 1.5s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.2); opacity: 0.1; }
  100% { transform: scale(1); opacity: 0.3; }
}

@keyframes pulse-core {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.status-text {
  display: flex;
  flex-direction: column;
}

.compact .status-text {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-value {
  font-size: 1rem;
  font-weight: 600;
}

.compact .status-value {
  font-size: 0.875rem;
}

.value-active {
  color: var(--kite-red);
}

.value-inactive {
  color: var(--kite-green);
}

/* Details */
.kill-switch-details {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.detail-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

/* Actions */
.kill-switch-actions {
  margin-top: 16px;
}

.compact .kill-switch-actions {
  margin-top: 0;
  margin-left: auto;
}

.trigger-btn,
.reset-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.compact .trigger-btn,
.compact .reset-btn {
  width: auto;
  padding: 6px 12px;
}

.trigger-btn {
  background: var(--kite-red);
  color: white;
}

.trigger-btn:hover:not(:disabled) {
  background: #c62828;
}

.trigger-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reset-btn {
  background: var(--kite-blue);
  color: white;
}

.reset-btn:hover:not(:disabled) {
  background: #1565c0;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

/* Modal */
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
  border-radius: 12px;
  width: 100%;
  max-width: 420px;
  margin: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--kite-border-light);
}

.modal-header.danger {
  background: linear-gradient(135deg, #fff5f5 0%, white 100%);
}

.modal-header.info {
  background: linear-gradient(135deg, #e3f2fd 0%, white 100%);
}

.modal-icon {
  width: 32px;
  height: 32px;
}

.modal-header.danger .modal-icon {
  color: var(--kite-red);
}

.modal-header.info .modal-icon {
  color: var(--kite-blue);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.modal-body {
  padding: 24px;
}

.warning-text,
.info-text {
  font-size: 0.9375rem;
  color: var(--kite-text-secondary);
  margin-bottom: 12px;
}

.warning-list {
  margin: 16px 0;
  padding-left: 20px;
  color: var(--kite-text-secondary);
}

.warning-list li {
  margin-bottom: 8px;
  font-size: 0.875rem;
}

.form-group {
  margin-top: 20px;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 6px;
  color: var(--kite-text-primary);
}

.form-input:focus {
  outline: none;
  border-color: var(--kite-blue);
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
}

.affected-count {
  margin-top: 16px;
  padding: 12px;
  background: var(--kite-red-light, #ffebee);
  border-radius: 6px;
  font-size: 0.875rem;
  color: var(--kite-red);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--kite-border-light);
  background: var(--kite-bg-subtle, #fafafa);
  border-radius: 0 0 12px 12px;
}

.btn-cancel,
.btn-primary,
.btn-danger {
  padding: 10px 20px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-cancel {
  background: white;
  border: 1px solid var(--kite-border);
  color: var(--kite-text-primary);
}

.btn-cancel:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

.btn-primary {
  background: var(--kite-blue);
  border: none;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-danger {
  background: var(--kite-red);
  border: none;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c62828;
}

.btn-cancel:disabled,
.btn-primary:disabled,
.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
