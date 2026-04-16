<script setup>
/**
 * Roll Wizard Component
 *
 * Interactive wizard for rolling options positions:
 * - Next week expiry (same strikes)
 * - Same expiry (new strikes)
 * - Next week + new strikes
 *
 * Phase 3: Re-Entry & Advanced Adjustments
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const autopilotStore = useAutopilotStore()

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  strategyId: {
    type: Number,
    required: true
  },
  currentPositions: {
    type: Array,
    default: () => []
  },
  underlying: {
    type: String,
    required: true
  },
  currentExpiry: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close', 'roll-executed'])

// State
const rollMode = ref('next_week_new_strikes') // 'next_week_same_strikes', 'same_expiry_new_strikes', 'next_week_new_strikes'
const loading = ref(false)
const error = ref(null)

// New strikes
const newCEStrike = ref(null)
const newPEStrike = ref(null)

// Available expiries and strikes
const availableExpiries = ref([])
const availableStrikes = ref([])
const nextExpiry = ref(null)

// Premium data
const currentPremium = ref({ ce: 0, pe: 0, total: 0 })
const newPremium = ref({ ce: 0, pe: 0, total: 0 })
const estimatedCredit = ref(0)

// Computed properties
const showExpirySelector = computed(() => {
  return rollMode.value === 'next_week_same_strikes' || rollMode.value === 'next_week_new_strikes'
})

const showStrikeSelector = computed(() => {
  return rollMode.value === 'same_expiry_new_strikes' || rollMode.value === 'next_week_new_strikes'
})

const targetExpiry = computed(() => {
  if (rollMode.value === 'same_expiry_new_strikes') {
    return props.currentExpiry
  }
  return nextExpiry.value || availableExpiries.value[0]
})

const currentCEPosition = computed(() => {
  return props.currentPositions.find(p => p.contract_type === 'CE')
})

const currentPEPosition = computed(() => {
  return props.currentPositions.find(p => p.contract_type === 'PE')
})

const canExecuteRoll = computed(() => {
  if (rollMode.value === 'next_week_same_strikes') {
    return targetExpiry.value !== null
  }
  if (rollMode.value === 'same_expiry_new_strikes') {
    return newCEStrike.value !== null && newPEStrike.value !== null
  }
  if (rollMode.value === 'next_week_new_strikes') {
    return targetExpiry.value !== null && newCEStrike.value !== null && newPEStrike.value !== null
  }
  return false
})

const creditDebitText = computed(() => {
  if (estimatedCredit.value > 0) {
    return `+₹${estimatedCredit.value.toFixed(2)} Credit`
  } else if (estimatedCredit.value < 0) {
    return `₹${Math.abs(estimatedCredit.value).toFixed(2)} Debit`
  }
  return '₹0.00'
})

const creditDebitClass = computed(() => {
  if (estimatedCredit.value > 0) return 'credit-positive'
  if (estimatedCredit.value < 0) return 'credit-negative'
  return 'credit-neutral'
})

// Fetch expiries
const fetchExpiries = async () => {
  const result = await autopilotStore.fetchExpiriesFor(props.underlying)
  if (!result.success) {
    console.error('Error fetching expiries:', result.error)
    error.value = 'Failed to load expiries'
    return
  }
  availableExpiries.value = result.expiries

  const currentDate = new Date(props.currentExpiry)
  const nextExpiryOption = availableExpiries.value.find(exp => {
    const expDate = new Date(exp)
    return expDate > currentDate
  })
  nextExpiry.value = nextExpiryOption || availableExpiries.value[0]
}

// Fetch strikes for an expiry
const fetchStrikes = async (expiry) => {
  const result = await autopilotStore.fetchStrikesFor(props.underlying, expiry)
  if (!result.success) {
    console.error('Error fetching strikes:', result.error)
    error.value = 'Failed to load strikes'
    return
  }
  availableStrikes.value = result.strikes

  if (currentCEPosition.value && !newCEStrike.value) {
    newCEStrike.value = currentCEPosition.value.strike
  }
  if (currentPEPosition.value && !newPEStrike.value) {
    newPEStrike.value = currentPEPosition.value.strike
  }
}

// Fetch current premium
const fetchCurrentPremium = async () => {
  if (currentCEPosition.value) {
    const ceRes = await autopilotStore.fetchOrderLTP({
      underlying: props.underlying,
      expiry: props.currentExpiry,
      strike: currentCEPosition.value.strike,
      option_type: 'CE',
    })
    currentPremium.value.ce = ceRes.success ? (ceRes.data?.ltp || 0) : 0
  }

  if (currentPEPosition.value) {
    const peRes = await autopilotStore.fetchOrderLTP({
      underlying: props.underlying,
      expiry: props.currentExpiry,
      strike: currentPEPosition.value.strike,
      option_type: 'PE',
    })
    currentPremium.value.pe = peRes.success ? (peRes.data?.ltp || 0) : 0
  }

  currentPremium.value.total = currentPremium.value.ce + currentPremium.value.pe
}

// Fetch new premium
const fetchNewPremium = async () => {
  newPremium.value = { ce: 0, pe: 0, total: 0 }

  if (newCEStrike.value && targetExpiry.value) {
    const ceRes = await autopilotStore.fetchOrderLTP({
      underlying: props.underlying,
      expiry: targetExpiry.value,
      strike: newCEStrike.value,
      option_type: 'CE',
    })
    newPremium.value.ce = ceRes.success ? (ceRes.data?.ltp || 0) : 0
  }

  if (newPEStrike.value && targetExpiry.value) {
    const peRes = await autopilotStore.fetchOrderLTP({
      underlying: props.underlying,
      expiry: targetExpiry.value,
      strike: newPEStrike.value,
      option_type: 'PE',
    })
    newPremium.value.pe = peRes.success ? (peRes.data?.ltp || 0) : 0
  }

  newPremium.value.total = newPremium.value.ce + newPremium.value.pe

  // Calculate estimated credit/debit
  // Credit = what we receive for closing current - what we pay for opening new
  estimatedCredit.value = currentPremium.value.total - newPremium.value.total
}

// Execute roll
const executeRoll = async () => {
  loading.value = true
  error.value = null

  try {
    const rollConfig = {
      mode: rollMode.value,
      target_expiry: targetExpiry.value,
      new_ce_strike: newCEStrike.value,
      new_pe_strike: newPEStrike.value,
      current_ce_strike: currentCEPosition.value?.strike,
      current_pe_strike: currentPEPosition.value?.strike
    }

    // TODO: Implement actual roll execution endpoint
    // const response = await api.post(`/api/v1/autopilot/strategies/${props.strategyId}/roll`, rollConfig)

    // For now, simulate success
    await new Promise(resolve => setTimeout(resolve, 1000))

    emit('roll-executed', rollConfig)
    close()
  } catch (err) {
    console.error('Error executing roll:', err)
    error.value = err.response?.data?.message || 'Failed to execute roll'
  } finally {
    loading.value = false
  }
}

// Close wizard
const close = () => {
  emit('close')
}

// Preview payoff (placeholder)
const previewPayoff = () => {
  // TODO: Integrate with strategy builder payoff visualization
  alert('Payoff preview coming soon!')
}

// Watch for changes
watch(() => props.show, async (show) => {
  if (show) {
    await fetchExpiries()
    await fetchStrikes(props.currentExpiry)
    await fetchCurrentPremium()
  }
})

watch(rollMode, async () => {
  if (rollMode.value === 'next_week_same_strikes') {
    // Use same strikes as current
    newCEStrike.value = currentCEPosition.value?.strike
    newPEStrike.value = currentPEPosition.value?.strike
  }
  await fetchNewPremium()
})

watch([targetExpiry, newCEStrike, newPEStrike], async () => {
  if (targetExpiry.value) {
    await fetchStrikes(targetExpiry.value)
  }
  await fetchNewPremium()
})

// Initialize
onMounted(async () => {
  if (props.show) {
    await fetchExpiries()
    await fetchStrikes(props.currentExpiry)
    await fetchCurrentPremium()
  }
})
</script>

<template>
  <div v-if="show" class="roll-wizard-overlay" @click.self="close" data-testid="autopilot-roll-wizard">
    <div class="roll-wizard-content">
      <!-- Header -->
      <div class="wizard-header">
        <div class="header-left">
          <h2 class="wizard-title">Roll Strategy</h2>
          <p class="wizard-subtitle">Roll options to new strikes or expiry</p>
        </div>
        <button @click="close" class="close-btn" data-testid="autopilot-roll-close">
          ×
        </button>
      </div>

      <!-- Body -->
      <div class="wizard-body">
        <!-- Current Position -->
        <div class="wizard-section">
          <h3 class="section-title">Current Position</h3>
          <div class="position-display">
            <div v-if="currentCEPosition" class="position-row">
              <span class="position-label">SELL {{ currentCEPosition.strike }} CE</span>
              <span class="position-value">@ ₹{{ currentPremium.ce.toFixed(2) }}</span>
              <span class="position-delta">(Δ {{ currentCEPosition.delta?.toFixed(2) || 'N/A' }})</span>
            </div>
            <div v-if="currentPEPosition" class="position-row">
              <span class="position-label">SELL {{ currentPEPosition.strike }} PE</span>
              <span class="position-value">@ ₹{{ currentPremium.pe.toFixed(2) }}</span>
              <span class="position-delta">(Δ {{ currentPEPosition.delta?.toFixed(2) || 'N/A' }})</span>
            </div>
            <div v-if="!currentCEPosition && !currentPEPosition" class="position-empty">
              No active positions
            </div>
          </div>
        </div>

        <!-- Roll Mode Selection -->
        <div class="wizard-section">
          <h3 class="section-title">Roll To</h3>
          <div class="roll-modes">
            <!-- Next Week Same Strikes -->
            <label class="mode-option">
              <input
                type="radio"
                v-model="rollMode"
                value="next_week_same_strikes"
                data-testid="autopilot-roll-mode-next-week-same"
              />
              <div class="mode-content">
                <span class="mode-icon">📅</span>
                <div class="mode-text">
                  <span class="mode-title">Next Week (Same Strikes)</span>
                  <span class="mode-description">Keep strikes, roll to next expiry</span>
                </div>
              </div>
            </label>

            <!-- Same Expiry New Strikes -->
            <label class="mode-option">
              <input
                type="radio"
                v-model="rollMode"
                value="same_expiry_new_strikes"
                data-testid="autopilot-roll-mode-same-expiry"
              />
              <div class="mode-content">
                <span class="mode-icon">🎯</span>
                <div class="mode-text">
                  <span class="mode-title">Same Expiry (New Strikes)</span>
                  <span class="mode-description">Keep expiry, adjust strikes</span>
                </div>
              </div>
            </label>

            <!-- Next Week + New Strikes -->
            <label class="mode-option">
              <input
                type="radio"
                v-model="rollMode"
                value="next_week_new_strikes"
                data-testid="autopilot-roll-mode-next-week-new"
              />
              <div class="mode-content">
                <span class="mode-icon">🔄</span>
                <div class="mode-text">
                  <span class="mode-title">Next Week + New Strikes</span>
                  <span class="mode-description">Roll expiry and adjust strikes</span>
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- Target Expiry (if applicable) -->
        <div v-if="showExpirySelector" class="wizard-section">
          <h3 class="section-title">Target Expiry</h3>
          <select
            v-model="nextExpiry"
            class="wizard-select"
            data-testid="autopilot-roll-target-expiry"
          >
            <option
              v-for="expiry in availableExpiries"
              :key="expiry"
              :value="expiry"
            >
              {{ new Date(expiry).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) }}
            </option>
          </select>
        </div>

        <!-- New Strikes (if applicable) -->
        <div v-if="showStrikeSelector" class="wizard-section">
          <h3 class="section-title">New Strikes</h3>
          <div class="strikes-grid">
            <!-- CE Strike -->
            <div class="strike-field">
              <label class="strike-label">CE Strike</label>
              <select
                v-model="newCEStrike"
                class="wizard-select"
                data-testid="autopilot-roll-ce-strike"
              >
                <option
                  v-for="strike in availableStrikes"
                  :key="`ce-${strike}`"
                  :value="strike"
                >
                  {{ strike }}
                </option>
              </select>
              <span v-if="newPremium.ce > 0" class="strike-premium">
                ₹{{ newPremium.ce.toFixed(2) }}
              </span>
            </div>

            <!-- PE Strike -->
            <div class="strike-field">
              <label class="strike-label">PE Strike</label>
              <select
                v-model="newPEStrike"
                class="wizard-select"
                data-testid="autopilot-roll-pe-strike"
              >
                <option
                  v-for="strike in availableStrikes"
                  :key="`pe-${strike}`"
                  :value="strike"
                >
                  {{ strike }}
                </option>
              </select>
              <span v-if="newPremium.pe > 0" class="strike-premium">
                ₹{{ newPremium.pe.toFixed(2) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Estimated Credit/Debit -->
        <div class="wizard-section">
          <h3 class="section-title">Estimated Net</h3>
          <div class="credit-display">
            <div class="credit-row">
              <span class="credit-label">Close Current:</span>
              <span class="credit-value">+₹{{ currentPremium.total.toFixed(2) }}</span>
            </div>
            <div class="credit-row">
              <span class="credit-label">Open New:</span>
              <span class="credit-value">-₹{{ newPremium.total.toFixed(2) }}</span>
            </div>
            <div class="credit-divider"></div>
            <div class="credit-row credit-total">
              <span class="credit-label">Net:</span>
              <span :class="['credit-value', creditDebitClass]" data-testid="autopilot-roll-estimated-credit">
                {{ creditDebitText }}
              </span>
            </div>
          </div>
        </div>

        <!-- Error Display -->
        <div v-if="error" class="wizard-error">
          <span class="error-icon">⚠️</span>
          <span class="error-text">{{ error }}</span>
        </div>
      </div>

      <!-- Footer -->
      <div class="wizard-footer">
        <button
          @click="previewPayoff"
          class="wizard-btn wizard-btn-secondary"
          data-testid="autopilot-roll-preview"
        >
          Preview Payoff
        </button>
        <div class="footer-actions">
          <button
            @click="close"
            class="wizard-btn wizard-btn-secondary"
            data-testid="autopilot-roll-cancel"
          >
            Cancel
          </button>
          <button
            @click="executeRoll"
            :disabled="!canExecuteRoll || loading"
            class="wizard-btn wizard-btn-primary"
            data-testid="autopilot-roll-execute"
          >
            <span v-if="loading">Rolling...</span>
            <span v-else>Execute Roll</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.roll-wizard-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}

.roll-wizard-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 700px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

/* ===== Header ===== */
.wizard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.header-left {
  flex: 1;
}

.wizard-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 4px 0;
}

.wizard-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.close-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  font-size: 32px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

/* ===== Body ===== */
.wizard-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.wizard-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

/* ===== Current Position ===== */
.position-display {
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.position-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: white;
  border-radius: 6px;
}

.position-label {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.position-value {
  font-size: 15px;
  font-weight: 600;
  color: #3b82f6;
}

.position-delta {
  font-size: 13px;
  color: #6b7280;
}

.position-empty {
  padding: 16px;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}

/* ===== Roll Modes ===== */
.roll-modes {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mode-option {
  position: relative;
  display: block;
  cursor: pointer;
}

.mode-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.mode-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  transition: all 0.2s;
}

.mode-option input[type="radio"]:checked + .mode-content {
  background: #eff6ff;
  border-color: #3b82f6;
}

.mode-content:hover {
  border-color: #3b82f6;
}

.mode-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.mode-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mode-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.mode-description {
  font-size: 13px;
  color: #6b7280;
}

/* ===== Selects ===== */
.wizard-select {
  width: 100%;
  padding: 12px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #1f2937;
  background: white;
  cursor: pointer;
  transition: border-color 0.15s;
}

.wizard-select:hover {
  border-color: #9ca3af;
}

.wizard-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* ===== Strikes Grid ===== */
.strikes-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.strike-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.strike-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.strike-premium {
  font-size: 13px;
  font-weight: 600;
  color: #10b981;
  padding: 8px 12px;
  background: #d1fae5;
  border-radius: 6px;
  text-align: center;
}

/* ===== Credit Display ===== */
.credit-display {
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.credit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.credit-label {
  color: #6b7280;
}

.credit-value {
  font-weight: 600;
  color: #1f2937;
}

.credit-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 0;
}

.credit-total {
  font-size: 16px;
}

.credit-positive {
  color: #10b981 !important;
}

.credit-negative {
  color: #ef4444 !important;
}

.credit-neutral {
  color: #6b7280 !important;
}

/* ===== Error ===== */
.wizard-error {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fee2e2;
  border-radius: 6px;
  border: 1px solid #fca5a5;
}

.error-icon {
  font-size: 20px;
}

.error-text {
  flex: 1;
  font-size: 14px;
  color: #dc2626;
}

/* ===== Footer ===== */
.wizard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.wizard-btn {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.wizard-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.wizard-btn-primary {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.wizard-btn-primary:hover:not(:disabled) {
  background: #2563eb;
  border-color: #2563eb;
}

.wizard-btn-secondary {
  background: white;
  color: #374151;
  border-color: #d1d5db;
}

.wizard-btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}
</style>
