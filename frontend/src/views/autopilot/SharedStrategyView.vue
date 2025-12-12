<script setup>
/**
 * AutoPilot Shared Strategy View
 *
 * Public view for a shared strategy that can be cloned
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const route = useRoute()
const store = useAutopilotStore()

const shareToken = computed(() => route.params.token)
const strategy = ref(null)
const loading = ref(true)
const error = ref(null)

// Clone modal state
const showCloneModal = ref(false)
const cloneName = ref('')
const cloning = ref(false)

onMounted(async () => {
  await loadSharedStrategy()
})

const loadSharedStrategy = async () => {
  loading.value = true
  error.value = null

  try {
    strategy.value = await store.fetchSharedStrategy(shareToken.value)
  } catch (e) {
    error.value = e.message || 'Strategy not found or link has expired'
  } finally {
    loading.value = false
  }
}

const openCloneModal = () => {
  cloneName.value = strategy.value ? `Copy of ${strategy.value.name}` : ''
  showCloneModal.value = true
}

const closeCloneModal = () => {
  showCloneModal.value = false
  cloneName.value = ''
}

const handleClone = async () => {
  if (!cloneName.value.trim()) {
    return
  }

  cloning.value = true

  try {
    const cloned = await store.cloneSharedStrategy(shareToken.value, {
      name: cloneName.value.trim()
    })
    closeCloneModal()
    // Redirect to the cloned strategy
    router.push(`/autopilot/strategies/${cloned.id}`)
  } catch (e) {
    error.value = e.message || 'Failed to clone strategy'
  } finally {
    cloning.value = false
  }
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}
</script>

<template>
  <KiteLayout>
  <div class="shared-page" data-testid="autopilot-shared-strategy-page">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading shared strategy...</p>
    </div>

    <!-- Error / Not Found -->
    <div v-else-if="error" class="error-state" data-testid="autopilot-shared-not-found">
      <h2 class="error-title">Strategy Not Found</h2>
      <p class="error-message">{{ error }}</p>
      <p class="error-hint">The share link may have expired or been revoked.</p>
    </div>

    <!-- Strategy Details -->
    <template v-else-if="strategy">
      <div class="shared-header">
        <div>
          <div class="shared-title-row">
            <h1 class="page-title">{{ strategy.name }}</h1>
            <span class="readonly-badge" data-testid="autopilot-shared-readonly-badge">
              Read Only
            </span>
          </div>
          <p class="page-subtitle">{{ strategy.description || 'Shared strategy' }}</p>
        </div>

        <div class="header-actions">
          <button
            @click="openCloneModal"
            data-testid="autopilot-clone-btn"
            class="strategy-btn strategy-btn-primary"
          >
            Clone to My Strategies
          </button>
        </div>
      </div>

      <!-- Strategy Info -->
      <div class="shared-details" data-testid="autopilot-shared-strategy-details">
        <div class="info-grid">
          <div class="info-card">
            <p class="info-label">Underlying</p>
            <p class="info-value">{{ strategy.underlying }}</p>
          </div>
          <div class="info-card">
            <p class="info-label">Lots</p>
            <p class="info-value">{{ strategy.lots }}</p>
          </div>
          <div class="info-card">
            <p class="info-label">Legs</p>
            <p class="info-value">{{ strategy.legs_config?.length || 0 }}</p>
          </div>
          <div class="info-card">
            <p class="info-label">Position Type</p>
            <p class="info-value">{{ strategy.position_type }}</p>
          </div>
        </div>

        <!-- Legs Table -->
        <div class="section">
          <h3 class="section-title">Strategy Legs</h3>
          <div class="strategy-table-wrapper">
            <div class="table-scroll">
              <table class="strategy-table">
                <thead>
                  <tr>
                    <th>Leg</th>
                    <th>Type</th>
                    <th>Action</th>
                    <th>Strike Selection</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(leg, index) in strategy.legs_config" :key="leg.id">
                    <td>{{ index + 1 }}</td>
                    <td>{{ leg.contract_type }}</td>
                    <td>
                      <span :class="['tag-select', leg.transaction_type === 'BUY' ? 'tag-buy' : 'tag-sell']">
                        {{ leg.transaction_type }}
                      </span>
                    </td>
                    <td>
                      {{ leg.strike_selection?.mode }}
                      <span v-if="leg.strike_selection?.offset !== undefined">
                        ({{ leg.strike_selection.offset >= 0 ? '+' : '' }}{{ leg.strike_selection.offset }})
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Entry Conditions -->
        <div class="section" v-if="strategy.entry_conditions?.conditions?.length > 0">
          <h3 class="section-title">Entry Conditions</h3>
          <p class="logic-label">Logic: {{ strategy.entry_conditions.logic }}</p>
          <div class="conditions-list">
            <div
              v-for="(cond, index) in strategy.entry_conditions.conditions"
              :key="cond.id"
              class="condition-item"
            >
              <span class="condition-number">{{ index + 1 }}.</span>
              {{ cond.variable }} {{ cond.operator }} {{ cond.value }}
            </div>
          </div>
        </div>

        <!-- Risk Settings -->
        <div class="section">
          <h3 class="section-title">Risk Settings</h3>
          <dl class="risk-grid">
            <div class="risk-item">
              <dt class="risk-label">Max Loss</dt>
              <dd class="risk-value">
                {{ strategy.risk_settings?.max_loss
                  ? formatCurrency(strategy.risk_settings.max_loss)
                  : 'Not set' }}
              </dd>
            </div>
            <div class="risk-item">
              <dt class="risk-label">Trailing Stop</dt>
              <dd class="risk-value">
                {{ strategy.risk_settings?.trailing_stop?.enabled ? 'Enabled' : 'Disabled' }}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </template>

    <!-- Clone Modal -->
    <div
      v-if="showCloneModal"
      class="modal-overlay"
      data-testid="autopilot-clone-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title">Clone Strategy</h3>
        <p class="modal-text">
          Enter a name for your copy of this strategy.
        </p>

        <div class="form-field">
          <label class="form-label">Strategy Name</label>
          <input
            type="text"
            v-model="cloneName"
            class="clone-input"
            data-testid="autopilot-clone-name-input"
            placeholder="Enter strategy name"
          />
        </div>

        <div class="modal-actions">
          <button
            @click="closeCloneModal"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="handleClone"
            data-testid="autopilot-clone-submit-btn"
            class="strategy-btn strategy-btn-primary"
            :disabled="!cloneName.trim() || cloning"
          >
            {{ cloning ? 'Cloning...' : 'Clone' }}
          </button>
        </div>
      </div>
    </div>
  </div>
  </KiteLayout>
</template>

<style scoped>
.shared-page {
  padding: 24px;
}

.loading-state {
  text-align: center;
  padding: 48px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 2px solid var(--kite-border);
  border-top-color: var(--kite-blue);
  border-radius: 50%;
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: var(--kite-text-secondary);
}

.error-state {
  text-align: center;
  padding: 48px;
}

.error-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.error-message {
  color: var(--kite-red);
  margin-bottom: 8px;
}

.error-hint {
  color: var(--kite-text-secondary);
  font-size: 0.875rem;
}

.shared-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.shared-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.page-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.readonly-badge {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.shared-details {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .info-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.info-card {
  padding: 16px;
  background: var(--kite-table-hover);
  border-radius: 4px;
}

.info-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.info-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--kite-border-light);
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.logic-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 8px;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-item {
  background: var(--kite-table-hover);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 0.875rem;
}

.condition-number {
  font-weight: 500;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.risk-item {
  display: flex;
  flex-direction: column;
}

.risk-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.risk-value {
  font-weight: 500;
  color: var(--kite-text-primary);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  padding: 24px;
  max-width: 448px;
  width: calc(100% - 32px);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.modal-text {
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 6px;
}

.clone-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
}

.clone-input:focus {
  outline: none;
  border-color: var(--kite-blue);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Buttons */
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

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

/* Tags */
.tag-select {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.tag-buy {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.tag-sell {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}
</style>
