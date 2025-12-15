<script setup>
/**
 * AutoPilot Settings View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 4
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

const localSettings = ref(null)
const hasChanges = ref(false)

onMounted(async () => {
  await store.fetchSettings()
  localSettings.value = { ...store.settings }
})

const handleChange = () => {
  hasChanges.value = true
}

const handleSave = async () => {
  try {
    await store.updateSettings(localSettings.value)
    hasChanges.value = false
  } catch (error) {
    console.error('Failed to save settings:', error)
  }
}

const handleReset = () => {
  localSettings.value = { ...store.settings }
  hasChanges.value = false
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

// Delta bands visual gauge computed properties
// Scale: -1.0 to +1.0 maps to 0% to 100%
const getNegativeZoneWidth = computed(() => {
  const lower = localSettings.value?.delta_band_lower ?? -0.20
  // -1.0 maps to 0%, lower band maps to its percentage
  return ((lower + 1) / 2) * 100
})

const getNeutralZoneWidth = computed(() => {
  const lower = localSettings.value?.delta_band_lower ?? -0.20
  const upper = localSettings.value?.delta_band_upper ?? 0.20
  // Width from lower to upper
  return ((upper - lower) / 2) * 100
})

const getPositiveZoneWidth = computed(() => {
  const upper = localSettings.value?.delta_band_upper ?? 0.20
  // +1.0 maps to 100%, upper band maps to its percentage
  return ((1 - upper) / 2) * 100
})
</script>

<template>
  <KiteLayout>
  <div class="settings-page" data-testid="autopilot-settings">
    <!-- Header -->
    <div class="settings-header">
      <div>
        <div class="settings-title-row">
          <button
            @click="router.push('/autopilot')"
            class="back-btn"
            data-testid="autopilot-settings-back"
          >
            &larr;
          </button>
          <h1 class="page-title">AutoPilot Settings</h1>
        </div>
        <p class="page-subtitle">Configure global settings for automated trading</p>
      </div>

      <div class="header-actions">
        <button
          v-if="hasChanges"
          @click="handleReset"
          data-testid="autopilot-settings-reset"
          class="strategy-btn strategy-btn-outline"
        >
          Reset
        </button>
        <button
          @click="handleSave"
          :disabled="!hasChanges || store.saving"
          data-testid="autopilot-settings-save"
          class="strategy-btn strategy-btn-primary"
        >
          {{ store.saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading && !localSettings" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading settings...</p>
    </div>

    <!-- Settings Form -->
    <div v-else-if="localSettings" class="settings-sections">
      <!-- Risk Limits -->
      <div class="settings-card" data-testid="autopilot-settings-risk">
        <h2 class="section-title">Risk Limits</h2>

        <div class="form-grid">
          <div class="form-field">
            <label class="form-label">Daily Loss Limit (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.daily_loss_limit"
              @input="handleChange"
              data-testid="autopilot-settings-max-daily-loss"
              class="strategy-input"
            />
            <p class="form-hint">Maximum loss allowed per day. AutoPilot will stop all strategies if breached.</p>
          </div>

          <div class="form-field">
            <label class="form-label">Per Strategy Loss Limit (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.per_strategy_loss_limit"
              @input="handleChange"
              data-testid="autopilot-settings-strategy-loss"
              class="strategy-input"
            />
            <p class="form-hint">Maximum loss per individual strategy.</p>
          </div>

          <div class="form-field">
            <label class="form-label">Max Capital Deployed (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.max_capital_deployed"
              @input="handleChange"
              data-testid="autopilot-settings-max-capital"
              class="strategy-input"
            />
            <p class="form-hint">Maximum margin/capital that can be used across all strategies.</p>
          </div>

          <div class="form-field">
            <label class="form-label">Max Active Strategies</label>
            <input
              type="number"
              v-model.number="localSettings.max_active_strategies"
              @input="handleChange"
              min="1"
              max="10"
              data-testid="autopilot-settings-max-active"
              class="strategy-input"
            />
            <p class="form-hint">Maximum number of strategies that can be active at once (1-10).</p>
          </div>
        </div>
      </div>

      <!-- Delta Bands Settings -->
      <div class="settings-card" data-testid="autopilot-settings-delta-bands">
        <h2 class="section-title">Delta Bands</h2>
        <p class="section-description">Configure delta band limits for position monitoring. When portfolio delta moves outside these bands, alerts will trigger.</p>

        <div class="form-grid">
          <div class="form-field">
            <label class="form-label">Upper Delta Band</label>
            <input
              type="number"
              v-model.number="localSettings.delta_band_upper"
              @input="handleChange"
              step="0.01"
              min="-1"
              max="1"
              data-testid="autopilot-settings-delta-band-upper"
              class="strategy-input"
            />
            <p class="form-hint">Maximum positive delta threshold (e.g., 0.20 for +20 delta).</p>
          </div>

          <div class="form-field">
            <label class="form-label">Lower Delta Band</label>
            <input
              type="number"
              v-model.number="localSettings.delta_band_lower"
              @input="handleChange"
              step="0.01"
              min="-1"
              max="1"
              data-testid="autopilot-settings-delta-band-lower"
              class="strategy-input"
            />
            <p class="form-hint">Minimum negative delta threshold (e.g., -0.20 for -20 delta).</p>
          </div>
        </div>

        <!-- Visual Preview of Delta Bands -->
        <div class="delta-bands-preview" data-testid="autopilot-settings-delta-bands-preview">
          <div class="delta-gauge">
            <div class="delta-gauge-track">
              <div class="delta-gauge-zone delta-zone-negative" :style="{ width: getNegativeZoneWidth + '%' }"></div>
              <div class="delta-gauge-zone delta-zone-neutral" :style="{ width: getNeutralZoneWidth + '%', left: getNegativeZoneWidth + '%' }"></div>
              <div class="delta-gauge-zone delta-zone-positive" :style="{ width: getPositiveZoneWidth + '%', left: (getNegativeZoneWidth + getNeutralZoneWidth) + '%' }"></div>
            </div>
            <div class="delta-gauge-labels">
              <span>-1.0</span>
              <span class="delta-label-lower">{{ (localSettings.delta_band_lower || -0.20).toFixed(2) }}</span>
              <span>0</span>
              <span class="delta-label-upper">{{ (localSettings.delta_band_upper || 0.20).toFixed(2) }}</span>
              <span>+1.0</span>
            </div>
          </div>
          <div class="delta-legend">
            <span class="legend-item"><span class="legend-color legend-negative"></span> Bearish Zone</span>
            <span class="legend-item"><span class="legend-color legend-neutral"></span> Neutral Zone</span>
            <span class="legend-item"><span class="legend-color legend-positive"></span> Bullish Zone</span>
          </div>
        </div>
      </div>

      <!-- Time Restrictions -->
      <div class="settings-card" data-testid="autopilot-settings-time">
        <h2 class="section-title">Time Restrictions</h2>

        <div class="form-grid">
          <div class="form-field">
            <label class="form-label">No Trade First Minutes</label>
            <input
              type="number"
              v-model.number="localSettings.no_trade_first_minutes"
              @input="handleChange"
              min="0"
              max="60"
              class="strategy-input"
            />
            <p class="form-hint">Don't enter trades during first N minutes of market open.</p>
          </div>

          <div class="form-field">
            <label class="form-label">No Trade Last Minutes</label>
            <input
              type="number"
              v-model.number="localSettings.no_trade_last_minutes"
              @input="handleChange"
              min="0"
              max="60"
              class="strategy-input"
            />
            <p class="form-hint">Don't enter trades during last N minutes before market close.</p>
          </div>
        </div>
      </div>

      <!-- Cooldown Settings -->
      <div class="settings-card" data-testid="autopilot-settings-cooldown">
        <h2 class="section-title">Cooldown Settings</h2>

        <div class="checkbox-group">
          <label class="checkbox-label">
            <input
              type="checkbox"
              v-model="localSettings.cooldown_after_loss"
              @change="handleChange"
              class="checkbox-input"
            />
            <span class="checkbox-text">Enable cooldown after significant loss</span>
          </label>
        </div>

        <div v-if="localSettings.cooldown_after_loss" class="form-grid">
          <div class="form-field">
            <label class="form-label">Cooldown Duration (minutes)</label>
            <input
              type="number"
              v-model.number="localSettings.cooldown_minutes"
              @input="handleChange"
              min="5"
              max="240"
              class="strategy-input"
            />
          </div>

          <div class="form-field">
            <label class="form-label">Cooldown Threshold (₹)</label>
            <input
              type="number"
              v-model.number="localSettings.cooldown_threshold"
              @input="handleChange"
              class="strategy-input"
            />
            <p class="form-hint">Trigger cooldown if loss exceeds this amount.</p>
          </div>
        </div>
      </div>

      <!-- Feature Flags -->
      <div class="settings-card" data-testid="autopilot-settings-features">
        <h2 class="section-title">Features</h2>

        <div class="feature-list">
          <div class="feature-item">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="localSettings.paper_trading_mode"
                @change="handleChange"
                data-testid="autopilot-settings-paper-trading"
                class="checkbox-input"
              />
              <span class="checkbox-text">Paper Trading Mode</span>
            </label>
            <p class="feature-hint">Simulate trades without placing real orders. Great for testing strategies.</p>
          </div>

          <div class="feature-item">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="localSettings.show_advanced_features"
                @change="handleChange"
                class="checkbox-input"
              />
              <span class="checkbox-text">Show Advanced Features</span>
            </label>
            <p class="feature-hint">Enable advanced configuration options and detailed analytics.</p>
          </div>
        </div>
      </div>

      <!-- Current Values Summary -->
      <div class="summary-card">
        <h3 class="summary-title">Current Limits Summary</h3>
        <div class="summary-grid">
          <div class="summary-item">
            <p class="summary-label">Daily Loss Limit</p>
            <p class="summary-value">{{ formatCurrency(localSettings.daily_loss_limit) }}</p>
          </div>
          <div class="summary-item">
            <p class="summary-label">Max Capital</p>
            <p class="summary-value">{{ formatCurrency(localSettings.max_capital_deployed) }}</p>
          </div>
          <div class="summary-item">
            <p class="summary-label">Max Strategies</p>
            <p class="summary-value">{{ localSettings.max_active_strategies }}</p>
          </div>
          <div class="summary-item">
            <p class="summary-label">Mode</p>
            <p class="summary-value">{{ localSettings.paper_trading_mode ? 'Paper Trading' : 'Live Trading' }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="error-banner" data-testid="autopilot-settings-error">
      <p class="error-text">{{ store.error }}</p>
      <button @click="store.clearError" class="error-dismiss">Dismiss</button>
    </div>
  </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.settings-page {
  padding: 24px;
}

/* ===== Header ===== */
.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.settings-title-row {
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

/* ===== Settings Sections ===== */
.settings-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 16px;
}

/* ===== Form Elements ===== */
.form-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .form-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.form-field {
  display: flex;
  flex-direction: column;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.form-hint {
  font-size: 0.75rem;
  color: var(--kite-text-muted);
  margin-top: 4px;
}

/* ===== Checkbox ===== */
.checkbox-group {
  margin-bottom: 16px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.checkbox-input {
  border-radius: 4px;
  border-color: var(--kite-border);
  color: var(--kite-blue);
}

.checkbox-text {
  margin-left: 8px;
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Feature List ===== */
.feature-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.feature-hint {
  font-size: 0.75rem;
  color: var(--kite-text-muted);
  margin-left: 24px;
}

/* ===== Summary Card ===== */
.summary-card {
  background: var(--kite-blue-light, #e3f2fd);
  border-radius: 4px;
  padding: 16px;
}

.summary-title {
  font-weight: 500;
  color: var(--kite-blue-dark, #1565c0);
  margin-bottom: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  font-size: 0.875rem;
}

@media (min-width: 768px) {
  .summary-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.summary-item {
  display: flex;
  flex-direction: column;
}

.summary-label {
  color: var(--kite-blue);
}

.summary-value {
  font-weight: 500;
  color: var(--kite-blue-dark, #1565c0);
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

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

/* ===== Input Styles ===== */
.strategy-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
  transition: border-color 0.15s ease;
}

.strategy-input:focus {
  outline: none;
  border-color: var(--kite-blue);
}

/* ===== Section Description ===== */
.section-description {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

/* ===== Delta Bands Preview ===== */
.delta-bands-preview {
  margin-top: 24px;
  padding: 16px;
  background: var(--kite-bg-secondary, #f9fafb);
  border-radius: 4px;
}

.delta-gauge {
  margin-bottom: 12px;
}

.delta-gauge-track {
  position: relative;
  height: 24px;
  background: var(--kite-border);
  border-radius: 4px;
  overflow: hidden;
}

.delta-gauge-zone {
  position: absolute;
  top: 0;
  height: 100%;
}

.delta-zone-negative {
  background: linear-gradient(90deg, var(--kite-red, #e53935), var(--kite-red-light, #ffcdd2));
}

.delta-zone-neutral {
  background: linear-gradient(90deg, var(--kite-green-light, #c8e6c9), var(--kite-green, #43a047), var(--kite-green-light, #c8e6c9));
}

.delta-zone-positive {
  background: linear-gradient(90deg, var(--kite-blue-light, #bbdefb), var(--kite-blue, #1e88e5));
}

.delta-gauge-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--kite-text-muted);
}

.delta-label-lower,
.delta-label-upper {
  font-weight: 500;
  color: var(--kite-text-primary);
}

.delta-legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-negative {
  background: var(--kite-red, #e53935);
}

.legend-neutral {
  background: var(--kite-green, #43a047);
}

.legend-positive {
  background: var(--kite-blue, #1e88e5);
}
</style>
