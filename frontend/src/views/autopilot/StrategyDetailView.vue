<script setup>
/**
 * AutoPilot Strategy Detail View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 3
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import ShareModal from '@/components/autopilot/common/ShareModal.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const route = useRoute()
const store = useAutopilotStore()

const strategyId = computed(() => parseInt(route.params.id))
const refreshInterval = ref(null)
const showExitModal = ref(false)
const showDeleteModal = ref(false)
const showShareModal = ref(false)

onMounted(async () => {
  await store.fetchStrategy(strategyId.value)

  // Refresh every 5 seconds for active strategies
  refreshInterval.value = setInterval(async () => {
    if (store.currentStrategy?.status === 'active') {
      await store.fetchStrategy(strategyId.value)
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})

const handlePause = async () => {
  await store.pauseStrategy(strategyId.value)
}

const handleResume = async () => {
  await store.resumeStrategy(strategyId.value)
}

const handleEdit = () => {
  router.push(`/autopilot/strategies/${strategyId.value}/edit`)
}

const handleClone = async () => {
  const cloned = await store.cloneStrategy(strategyId.value)
  router.push(`/autopilot/strategies/${cloned.id}/edit`)
}

const handleActivate = async () => {
  await store.activateStrategy(strategyId.value)
}

const handleDelete = async () => {
  await store.deleteStrategy(strategyId.value)
  showDeleteModal.value = false
  router.push('/autopilot')
}

const handleExit = async () => {
  // Force exit all positions - this would call an exit endpoint
  showExitModal.value = false
  // For now, just pause the strategy
  await store.pauseStrategy(strategyId.value)
}

const handleShare = () => {
  showShareModal.value = true
}

const closeShareModal = () => {
  showShareModal.value = false
}

const onStrategyShared = () => {
  // Refresh strategy to update share status
  store.fetchStrategy(strategyId.value)
}

const onStrategyUnshared = () => {
  // Refresh strategy to update share status
  store.fetchStrategy(strategyId.value)
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('en-IN')
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'status-badge status-active',
    waiting: 'status-badge status-waiting',
    pending: 'status-badge status-pending',
    paused: 'status-badge status-paused',
    draft: 'status-badge status-draft',
    completed: 'status-badge status-completed',
    error: 'status-badge status-error'
  }
  return classes[status] || 'status-badge status-paused'
}
</script>

<template>
  <KiteLayout>
  <div class="detail-page" data-testid="autopilot-strategy-detail">
    <!-- Loading -->
    <div v-if="store.loading && !store.currentStrategy" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading strategy...</p>
    </div>

    <!-- Strategy Detail -->
    <template v-else-if="store.currentStrategy">
      <!-- Header -->
      <div class="detail-header">
        <div>
          <div class="detail-title-row">
            <button
              @click="router.push('/autopilot')"
              class="back-btn"
              data-testid="autopilot-detail-back"
            >
              &larr;
            </button>
            <h1 class="page-title" data-testid="autopilot-detail-name">
              {{ store.currentStrategy.name }}
            </h1>
            <span
              :class="getStatusBadgeClass(store.currentStrategy.status)"
              data-testid="autopilot-detail-status"
            >
              {{ store.currentStrategy.status }}
            </span>
          </div>
          <p class="page-subtitle">{{ store.currentStrategy.description || 'No description' }}</p>
        </div>

        <div class="header-actions">
          <button
            v-if="store.currentStrategy.status === 'draft'"
            @click="handleEdit"
            data-testid="autopilot-detail-edit"
            class="strategy-btn strategy-btn-outline"
          >
            Edit
          </button>

          <button
            v-if="store.currentStrategy.status === 'draft'"
            @click="handleActivate"
            data-testid="autopilot-detail-activate"
            class="strategy-btn strategy-btn-success"
          >
            Activate
          </button>

          <button
            v-if="['active', 'waiting', 'pending'].includes(store.currentStrategy.status)"
            @click="handlePause"
            data-testid="autopilot-detail-pause"
            class="strategy-btn strategy-btn-warning"
          >
            Pause
          </button>

          <button
            v-if="store.currentStrategy.status === 'paused'"
            @click="handleResume"
            data-testid="autopilot-detail-resume"
            class="strategy-btn strategy-btn-success"
          >
            Resume
          </button>

          <button
            v-if="['active', 'paused'].includes(store.currentStrategy.status)"
            @click="showExitModal = true"
            data-testid="autopilot-detail-exit"
            class="strategy-btn strategy-btn-exit"
          >
            Exit
          </button>

          <button
            @click="handleClone"
            data-testid="autopilot-detail-clone"
            class="strategy-btn strategy-btn-outline"
          >
            Clone
          </button>

          <button
            @click="handleShare"
            :data-testid="store.currentStrategy.share_token ? 'autopilot-detail-unshare' : 'autopilot-detail-share'"
            class="strategy-btn strategy-btn-outline"
          >
            {{ store.currentStrategy.share_token ? 'Manage Share' : 'Share' }}
          </button>

          <button
            v-if="['draft', 'completed', 'error'].includes(store.currentStrategy.status)"
            @click="showDeleteModal = true"
            data-testid="autopilot-detail-delete"
            class="strategy-btn strategy-btn-danger"
          >
            Delete
          </button>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards-grid">
        <div class="summary-card" data-testid="autopilot-strategy-pnl">
          <p class="summary-label">Current P&L</p>
          <p :class="['summary-value-large', getPnLClass(store.currentStrategy.runtime_state?.current_pnl)]">
            {{ formatCurrency(store.currentStrategy.runtime_state?.current_pnl) }}
          </p>
        </div>

        <div class="summary-card">
          <p class="summary-label">Margin Used</p>
          <p class="summary-value-large">
            {{ formatCurrency(store.currentStrategy.runtime_state?.margin_used) }}
          </p>
        </div>

        <div class="summary-card">
          <p class="summary-label">Underlying</p>
          <p class="summary-value-large">{{ store.currentStrategy.underlying }}</p>
          <p class="summary-label">{{ store.currentStrategy.lots }} lot(s)</p>
        </div>

        <div class="summary-card">
          <p class="summary-label">Activated</p>
          <p class="summary-value">
            {{ formatDateTime(store.currentStrategy.activated_at) }}
          </p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="detail-card">
        <div class="tabs-header">
          <nav class="tabs-nav">
            <button class="tab-btn tab-btn-active">
              Configuration
            </button>
          </nav>
        </div>

        <div class="tab-content">
          <!-- Legs -->
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
                    <tr v-for="(leg, index) in store.currentStrategy.legs_config" :key="leg.id">
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
          <div class="section">
            <h3 class="section-title">Entry Conditions</h3>
            <div v-if="store.currentStrategy.entry_conditions?.conditions?.length > 0">
              <p class="logic-label">
                Logic: {{ store.currentStrategy.entry_conditions.logic }}
              </p>
              <div class="conditions-list">
                <div
                  v-for="(cond, index) in store.currentStrategy.entry_conditions.conditions"
                  :key="cond.id"
                  class="condition-item"
                >
                  <span class="condition-number">{{ index + 1 }}.</span>
                  {{ cond.variable }} {{ cond.operator }} {{ cond.value }}
                  <span :class="['condition-status', cond.enabled ? 'condition-enabled' : 'condition-disabled']">
                    {{ cond.enabled ? 'Active' : 'Disabled' }}
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="empty-text">No entry conditions configured. Strategy enters immediately.</p>
          </div>

          <!-- Risk Settings -->
          <div class="section">
            <h3 class="section-title">Risk Settings</h3>
            <dl class="risk-grid">
              <div class="risk-item">
                <dt class="risk-label">Max Loss</dt>
                <dd class="risk-value">
                  {{ store.currentStrategy.risk_settings?.max_loss
                    ? formatCurrency(store.currentStrategy.risk_settings.max_loss)
                    : 'Not set' }}
                </dd>
              </div>
              <div class="risk-item">
                <dt class="risk-label">Max Loss %</dt>
                <dd class="risk-value">
                  {{ store.currentStrategy.risk_settings?.max_loss_pct
                    ? store.currentStrategy.risk_settings.max_loss_pct + '%'
                    : 'Not set' }}
                </dd>
              </div>
              <div class="risk-item">
                <dt class="risk-label">Trailing Stop</dt>
                <dd class="risk-value">
                  {{ store.currentStrategy.risk_settings?.trailing_stop?.enabled ? 'Enabled' : 'Disabled' }}
                </dd>
              </div>
              <div class="risk-item">
                <dt class="risk-label">Time Stop</dt>
                <dd class="risk-value">
                  {{ store.currentStrategy.risk_settings?.time_stop || 'Not set' }}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <!-- Timestamps -->
      <div class="timestamps">
        <p>Created: {{ formatDateTime(store.currentStrategy.created_at) }}</p>
        <p>Last Updated: {{ formatDateTime(store.currentStrategy.updated_at) }}</p>
        <p>Version: {{ store.currentStrategy.version }}</p>
      </div>
    </template>

    <!-- Error -->
    <div v-if="store.error" class="error-banner">
      <p class="error-text">{{ store.error }}</p>
      <button @click="store.clearError" class="error-dismiss">Dismiss</button>
    </div>

    <!-- Delete Modal -->
    <div
      v-if="showDeleteModal"
      class="modal-overlay"
      data-testid="autopilot-delete-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title">Delete Strategy</h3>
        <p class="modal-text">
          Are you sure you want to delete "{{ store.currentStrategy?.name }}"? This action cannot be undone.
        </p>
        <div class="modal-actions">
          <button
            @click="showDeleteModal = false"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="handleDelete"
            data-testid="autopilot-delete-confirm"
            class="strategy-btn strategy-btn-danger"
          >
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Exit Modal -->
    <div
      v-if="showExitModal"
      class="modal-overlay"
      data-testid="autopilot-exit-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title">Exit Strategy</h3>
        <p class="modal-text">
          Are you sure you want to exit all positions for "{{ store.currentStrategy?.name }}"?
          This will close all active positions at market price.
        </p>
        <div class="modal-actions">
          <button
            @click="showExitModal = false"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="handleExit"
            data-testid="autopilot-exit-confirm"
            class="strategy-btn strategy-btn-exit"
          >
            Exit All Positions
          </button>
        </div>
      </div>
    </div>

    <!-- Share Modal -->
    <ShareModal
      :show="showShareModal"
      :strategy-id="store.currentStrategy?.id"
      :strategy-name="store.currentStrategy?.name"
      :is-shared="!!store.currentStrategy?.share_token"
      :existing-token="store.currentStrategy?.share_token"
      @close="closeShareModal"
      @shared="onStrategyShared"
      @unshared="onStrategyUnshared"
    />
  </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.detail-page {
  padding: 24px;
}

/* ===== Loading State ===== */
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

/* ===== Header ===== */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  color: var(--kite-text-secondary);
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
}

.back-btn:hover {
  color: var(--kite-text-primary);
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

.header-actions {
  display: flex;
  gap: 8px;
}

/* ===== Status Badges ===== */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-active {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.status-waiting {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.status-pending {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.status-paused {
  background: var(--kite-gray-light, #f5f5f5);
  color: var(--kite-text-secondary);
}

.status-draft {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.status-completed {
  background: #f3e5f5;
  color: #7b1fa2;
}

.status-error {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

/* ===== P&L Colors ===== */
.pnl-profit {
  color: var(--kite-green);
}

.pnl-loss {
  color: var(--kite-red);
}

.pnl-neutral {
  color: var(--kite-text-secondary);
}

/* ===== Summary Cards ===== */
.summary-cards-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .summary-cards-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.summary-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.summary-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.summary-value-large {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

/* ===== Detail Card ===== */
.detail-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* ===== Tabs ===== */
.tabs-header {
  border-bottom: 1px solid var(--kite-border);
}

.tabs-nav {
  display: flex;
  margin-bottom: -1px;
}

.tab-btn {
  padding: 12px 24px;
  border: none;
  background: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab-btn:hover {
  color: var(--kite-text-primary);
}

.tab-btn-active {
  color: var(--kite-blue);
  border-bottom-color: var(--kite-blue);
}

.tab-content {
  padding: 24px;
}

/* ===== Sections ===== */
.section {
  margin-bottom: 24px;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

/* ===== Entry Conditions ===== */
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

.condition-status {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.condition-enabled {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.condition-disabled {
  background: var(--kite-gray-light, #f5f5f5);
  color: var(--kite-text-secondary);
}

.empty-text {
  color: var(--kite-text-secondary);
}

/* ===== Risk Settings ===== */
.risk-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .risk-grid {
    grid-template-columns: repeat(4, 1fr);
  }
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

/* ===== Timestamps ===== */
.timestamps {
  margin-top: 16px;
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
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

.error-dismiss {
  color: var(--kite-red);
  background: none;
  border: none;
  text-decoration: underline;
  margin-top: 8px;
  cursor: pointer;
}

/* ===== Modal ===== */
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
  margin-bottom: 16px;
}

.modal-text {
  color: var(--kite-text-secondary);
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Button Styles ===== */
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
  background: #388e3c;
}

.strategy-btn-warning {
  background: var(--kite-orange);
  color: white;
  border-color: var(--kite-orange);
}

.strategy-btn-warning:hover:not(:disabled) {
  background: #f57c00;
}

.strategy-btn-danger {
  background: var(--kite-red);
  color: white;
  border-color: var(--kite-red);
}

.strategy-btn-danger:hover:not(:disabled) {
  background: #c62828;
}

.strategy-btn-exit {
  background: var(--kite-orange);
  color: white;
  border-color: var(--kite-orange);
}

.strategy-btn-exit:hover:not(:disabled) {
  background: #e65100;
}

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}
</style>
