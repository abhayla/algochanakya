<template>
  <div class="modal-overlay" data-testid="strategy-deploy-overlay" @click.self="store.closeDeploy()">
    <div class="deploy-modal" data-testid="strategy-deploy-modal">
      <!-- Header -->
      <div class="modal-header">
        <div>
          <h2 data-testid="strategy-deploy-modal-title">Deploy Strategy</h2>
          <p class="subtitle">{{ template?.display_name }}</p>
        </div>
        <button class="close-btn" @click="store.closeDeploy()" data-testid="strategy-deploy-modal-close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="modal-content">
        <!-- Success State -->
        <div v-if="deploySuccess" class="success-state" data-testid="strategy-deploy-success">
          <div class="success-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
          </div>
          <h3>Strategy Created!</h3>
          <p>Your {{ template?.display_name }} strategy has been set up successfully.</p>
          <div class="success-actions">
            <button class="btn-secondary" @click="store.closeDeploy()">Close</button>
            <button class="btn-primary" @click="goToStrategy" data-testid="strategy-deploy-view-button">
              View Strategy
            </button>
          </div>
        </div>

        <!-- Deploy Form -->
        <template v-else>
          <!-- Strategy Preview -->
          <section class="section preview-section">
            <h3>Strategy Structure</h3>
            <div class="legs-preview" data-testid="strategy-deploy-legs-preview">
              <div
                v-for="(leg, idx) in template?.legs_config"
                :key="idx"
                :class="['leg-row', leg.position.toLowerCase()]"
                :data-testid="`strategy-deploy-leg-${idx}`"
              >
                <span class="leg-type">{{ leg.type }}</span>
                <span class="leg-position">{{ leg.position }}</span>
                <span class="leg-strike">
                  ATM {{ leg.strike_offset > 0 ? '+' : '' }}{{ leg.strike_offset }}
                </span>
              </div>
            </div>
          </section>

          <!-- Configuration -->
          <section class="section">
            <h3>Configuration</h3>
            <div class="config-grid">
              <!-- Underlying -->
              <div class="config-item">
                <label>Underlying</label>
                <select v-model="deployConfig.underlying" data-testid="strategy-deploy-underlying">
                  <option value="NIFTY">NIFTY</option>
                  <option value="BANKNIFTY">BANKNIFTY</option>
                  <option value="FINNIFTY">FINNIFTY</option>
                </select>
              </div>

              <!-- Expiry -->
              <div class="config-item">
                <label>Expiry</label>
                <select v-model="deployConfig.expiry" :disabled="loadingExpiries" data-testid="strategy-deploy-expiry">
                  <option :value="null">{{ loadingExpiries ? 'Loading...' : 'Select Expiry' }}</option>
                  <option v-for="exp in expiries" :key="exp" :value="exp">
                    {{ formatExpiry(exp) }}
                  </option>
                </select>
              </div>

              <!-- Lots -->
              <div class="config-item">
                <label>Lots</label>
                <div class="lots-control">
                  <button @click="decrementLots" :disabled="deployConfig.lots <= 1" data-testid="strategy-deploy-lots-minus">-</button>
                  <input type="number" v-model.number="deployConfig.lots" min="1" max="50" data-testid="strategy-deploy-lots" />
                  <button @click="incrementLots" :disabled="deployConfig.lots >= 50" data-testid="strategy-deploy-lots-plus">+</button>
                </div>
              </div>

              <!-- ATM Strike (optional) -->
              <div class="config-item">
                <label>ATM Strike (Optional)</label>
                <input
                  type="number"
                  v-model.number="deployConfig.atm_strike"
                  placeholder="Auto-detect"
                  :step="strikeStep"
                />
              </div>
            </div>
          </section>

          <!-- Estimated Values -->
          <section class="section">
            <h3>Estimated Values</h3>
            <div class="estimates-grid" data-testid="strategy-deploy-estimates">
              <div class="estimate profit">
                <span class="label">Max Profit</span>
                <span class="value">{{ template?.max_profit }}</span>
              </div>
              <div class="estimate loss">
                <span class="label">Max Loss</span>
                <span class="value">{{ template?.max_loss }}</span>
              </div>
              <div class="estimate">
                <span class="label">Breakeven</span>
                <span class="value">{{ template?.breakeven || '--' }}</span>
              </div>
              <div class="estimate">
                <span class="label">Lot Size</span>
                <span class="value">{{ lotSize }} x {{ deployConfig.lots }} = {{ lotSize * deployConfig.lots }}</span>
              </div>
            </div>
          </section>

          <!-- Warning -->
          <div class="warning-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <div>
              <strong>Note:</strong> This will create a strategy in the Strategy Builder.
              You can review and modify it before placing actual orders.
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div v-if="!deploySuccess" class="modal-footer">
        <button class="btn-secondary" @click="store.closeDeploy()" data-testid="strategy-deploy-cancel-button">Cancel</button>
        <button
          class="btn-primary"
          :disabled="!canDeploy || store.isLoading"
          @click="deploy"
          data-testid="strategy-deploy-confirm-button"
        >
          <span v-if="store.isLoading">Creating...</span>
          <span v-else>Create Strategy</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStrategyLibraryStore } from '@/stores/strategyLibrary'
import api from '@/services/api'

const router = useRouter()
const store = useStrategyLibraryStore()

const template = computed(() => store.selectedTemplate)

const deployConfig = ref({
  underlying: 'NIFTY',
  expiry: null,
  lots: 1,
  atm_strike: null
})

const expiries = ref([])
const loadingExpiries = ref(false)
const deploySuccess = ref(false)
const deployedStrategyId = ref(null)

const lotSize = computed(() => {
  const sizes = { NIFTY: 75, BANKNIFTY: 15, FINNIFTY: 25 }
  return sizes[deployConfig.value.underlying] || 75
})

const strikeStep = computed(() => {
  const steps = { NIFTY: 100, BANKNIFTY: 100, FINNIFTY: 100, SENSEX: 100 }
  return steps[deployConfig.value.underlying] || 100
})

const canDeploy = computed(() => {
  return deployConfig.value.underlying &&
         deployConfig.value.expiry &&
         deployConfig.value.lots >= 1
})

async function fetchExpiries() {
  loadingExpiries.value = true
  try {
    const response = await api.get(`/api/options/expiries?underlying=${deployConfig.value.underlying}`)
    expiries.value = response.data.expiries || []
    // Auto-select first expiry
    if (expiries.value.length > 0 && !deployConfig.value.expiry) {
      deployConfig.value.expiry = expiries.value[0]
    }
  } catch (err) {
    console.error('Failed to fetch expiries:', err)
    expiries.value = []
  } finally {
    loadingExpiries.value = false
  }
}

function formatExpiry(expiry) {
  const date = new Date(expiry)
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function incrementLots() {
  if (deployConfig.value.lots < 50) {
    deployConfig.value.lots++
  }
}

function decrementLots() {
  if (deployConfig.value.lots > 1) {
    deployConfig.value.lots--
  }
}

async function deploy() {
  const result = await store.deployStrategy(template.value.name, {
    underlying: deployConfig.value.underlying,
    expiry: deployConfig.value.expiry,
    lots: deployConfig.value.lots,
    atm_strike: deployConfig.value.atm_strike
  })

  if (result.success) {
    deploySuccess.value = true
    deployedStrategyId.value = result.data.strategy_id
  }
}

function goToStrategy() {
  store.closeDeploy()
  if (deployedStrategyId.value) {
    router.push(`/strategy/${deployedStrategyId.value}`)
  }
}

// Watch for underlying changes to refresh expiries
watch(() => deployConfig.value.underlying, () => {
  deployConfig.value.expiry = null
  fetchExpiries()
})

onMounted(() => {
  fetchExpiries()
})
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
}

.deploy-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 560px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #212529;
  margin: 0;
}

.subtitle {
  font-size: 14px;
  color: #6c757d;
  margin: 4px 0 0;
}

.close-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: #6c757d;
}

.close-btn:hover {
  color: #212529;
}

.close-btn svg {
  width: 24px;
  height: 24px;
}

/* Content */
.modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.section {
  margin-bottom: 24px;
}

.section h3 {
  font-size: 14px;
  font-weight: 600;
  color: #212529;
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Legs Preview */
.legs-preview {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.leg-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 13px;
}

.leg-row.buy {
  background: #d4edda;
}

.leg-row.sell {
  background: #f8d7da;
}

.leg-type {
  font-weight: 600;
}

.leg-position {
  color: #6c757d;
}

.leg-strike {
  font-family: monospace;
}

/* Config Grid */
.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-item label {
  font-size: 12px;
  font-weight: 500;
  color: #6c757d;
}

.config-item select,
.config-item input {
  padding: 10px 12px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.config-item select:focus,
.config-item input:focus {
  border-color: #387ed1;
  outline: none;
}

/* Lots Control */
.lots-control {
  display: flex;
  align-items: center;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  overflow: hidden;
}

.lots-control button {
  padding: 10px 14px;
  background: #f8f9fa;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #495057;
}

.lots-control button:hover:not(:disabled) {
  background: #e9ecef;
}

.lots-control button:disabled {
  color: #adb5bd;
  cursor: not-allowed;
}

.lots-control input {
  width: 60px;
  text-align: center;
  border: none;
  border-left: 1px solid #dee2e6;
  border-right: 1px solid #dee2e6;
  padding: 10px;
  font-size: 14px;
}

.lots-control input:focus {
  outline: none;
}

/* Estimates Grid */
.estimates-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.estimate {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  text-align: center;
}

.estimate .label {
  display: block;
  font-size: 11px;
  color: #6c757d;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.estimate .value {
  font-size: 14px;
  font-weight: 600;
  color: #212529;
}

.estimate.profit {
  background: #d4edda;
}

.estimate.profit .value {
  color: #155724;
}

.estimate.loss {
  background: #f8d7da;
}

.estimate.loss .value {
  color: #721c24;
}

/* Warning Box */
.warning-box {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  font-size: 13px;
  color: #856404;
}

.warning-box svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: #ffc107;
}

/* Success State */
.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 40px 20px;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #d4edda;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.success-icon svg {
  width: 32px;
  height: 32px;
  color: #00b386;
}

.success-state h3 {
  font-size: 20px;
  font-weight: 600;
  color: #212529;
  margin: 0 0 8px;
}

.success-state p {
  font-size: 14px;
  color: #6c757d;
  margin: 0 0 24px;
}

.success-actions {
  display: flex;
  gap: 12px;
}

/* Footer */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e9ecef;
}

.btn-secondary {
  padding: 10px 20px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  color: #495057;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #f8f9fa;
}

.btn-primary {
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  background: #387ed1;
  font-size: 14px;
  font-weight: 500;
  color: white;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: #2c5aa0;
}

.btn-primary:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}
</style>
