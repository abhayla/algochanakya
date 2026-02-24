<template>
  <KiteLayout>
    <AISubNav />
    <div class="ai-settings-view" data-testid="ai-settings-view">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">AI Trading Configuration</h1>
      <p class="page-subtitle">
        Configure autonomous AI trading settings, deployment schedule, and position sizing
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div>Loading configuration...</div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-banner">
      <p>{{ error }}</p>
    </div>

    <!-- Configuration Form -->
    <div v-if="!loading && config" class="settings-content">
      <!-- Autonomy Settings Panel -->
      <div class="settings-card" data-testid="ai-autonomy-panel">
        <h2 class="section-title">Autonomy Settings</h2>

        <div class="field-group">
          <!-- AI Enabled Toggle -->
          <div class="field-row">
            <div>
              <label class="field-label">Enable AI Trading</label>
              <p class="field-hint">Activate autonomous trading</p>
            </div>
            <label class="toggle-switch">
              <input
                v-model="config.ai_enabled"
                type="checkbox"
                data-testid="ai-enabled-toggle"
                @change="handleConfigUpdate"
              />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <div class="field-group">
          <!-- Autonomy Mode -->
          <div>
            <label class="field-label">Trading Mode</label>
            <div class="radio-group">
              <label class="radio-label">
                <input
                  v-model="config.autonomy_mode"
                  type="radio"
                  value="paper"
                  data-testid="mode-paper"
                  @change="handleConfigUpdate"
                />
                Paper Trading
              </label>
              <label class="radio-label" :class="{ disabled: !canGraduateToLive }">
                <input
                  v-model="config.autonomy_mode"
                  type="radio"
                  value="live"
                  data-testid="mode-live"
                  :disabled="!canGraduateToLive"
                  @change="handleConfigUpdate"
                />
                Live Trading
                <span v-if="!canGraduateToLive" class="graduation-warning">
                  (Requires graduation)
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Deployment Schedule Panel -->
      <div class="settings-card" data-testid="ai-deployment-panel">
        <h2 class="section-title">Deployment Schedule</h2>

        <div class="field-group">
          <!-- Auto-Deploy Toggle -->
          <div class="field-row">
            <label class="field-label">Auto-Deploy Strategies</label>
            <input
              v-model="config.auto_deploy_enabled"
              type="checkbox"
              data-testid="auto-deploy-toggle"
              @change="handleConfigUpdate"
            />
          </div>
        </div>

        <div class="field-group">
          <!-- Deploy Time -->
          <div>
            <label class="field-label">Deploy Time</label>
            <input
              v-model="config.deploy_time"
              type="time"
              class="settings-input"
              data-testid="deploy-time-input"
              @change="handleConfigUpdate"
            />
          </div>
        </div>

        <div class="field-group">
          <!-- Deploy Days -->
          <div>
            <label class="field-label">Deploy Days</label>
            <div class="day-selector">
              <label
                v-for="day in ['MON', 'TUE', 'WED', 'THU', 'FRI']"
                :key="day"
                class="day-label"
              >
                <input
                  :checked="config.deploy_days?.includes(day)"
                  type="checkbox"
                  :data-testid="`deploy-day-${day.toLowerCase()}`"
                  @change="toggleDeployDay(day)"
                />
                {{ day }}
              </label>
            </div>
          </div>
        </div>

        <div class="field-group">
          <!-- Skip Options -->
          <div>
            <label class="checkbox-label">
              <input
                v-model="config.skip_event_days"
                type="checkbox"
                data-testid="skip-event-days"
                @change="handleConfigUpdate"
              />
              Skip event days (Budget, RBI, etc.)
            </label>
          </div>
          <div>
            <label class="checkbox-label">
              <input
                v-model="config.skip_weekly_expiry"
                type="checkbox"
                data-testid="skip-weekly-expiry"
                @change="handleConfigUpdate"
              />
              Skip weekly expiry (Thursday)
            </label>
          </div>
        </div>
      </div>

      <!-- Position Sizing Panel -->
      <div class="settings-card" data-testid="ai-sizing-panel">
        <h2 class="section-title">Position Sizing</h2>

        <div class="field-group">
          <!-- Sizing Mode -->
          <div>
            <label class="field-label">Sizing Mode</label>
            <select
              v-model="config.sizing_mode"
              class="settings-select"
              data-testid="sizing-mode-select"
              @change="handleConfigUpdate"
            >
              <option value="fixed">Fixed</option>
              <option value="tiered">Tiered (Confidence-based)</option>
              <option value="kelly">Kelly Criterion</option>
            </select>
          </div>
        </div>

        <div class="field-group">
          <!-- Base Lots -->
          <div>
            <label class="field-label">Base Lots</label>
            <input
              v-model.number="config.base_lots"
              type="number"
              min="1"
              class="settings-input"
              data-testid="base-lots-input"
              @change="handleConfigUpdate"
            />
          </div>
        </div>

        <div class="field-group" v-if="config.sizing_mode === 'tiered'">
          <!-- Confidence Tiers (simplified display) -->
          <div>
            <label class="field-label">Confidence Tiers</label>
            <div class="tiers-display">
              <div class="tier-row" v-for="(tier, index) in config.confidence_tiers" :key="index">
                {{ tier.name }}: {{ tier.min }}-{{ tier.max }}% = {{ tier.multiplier }}x lots
              </div>
            </div>
            <p class="tier-hint">
              (Advanced tier editing in Phase 3)
            </p>
          </div>
        </div>
      </div>

      <!-- Limits Panel -->
      <div class="settings-card" data-testid="ai-limits-panel">
        <h2 class="section-title">Trading Limits</h2>

        <div class="limits-grid">
          <div>
            <label class="field-label">Max Lots/Strategy</label>
            <input
              v-model.number="config.max_lots_per_strategy"
              type="number"
              min="1"
              class="settings-input"
              data-testid="max-lots-strategy-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="field-label">Max Lots/Day</label>
            <input
              v-model.number="config.max_lots_per_day"
              type="number"
              min="1"
              class="settings-input"
              data-testid="max-lots-day-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="field-label">Max Strategies/Day</label>
            <input
              v-model.number="config.max_strategies_per_day"
              type="number"
              min="1"
              class="settings-input"
              data-testid="max-strategies-day-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="field-label">Min Confidence (%)</label>
            <input
              v-model.number="config.min_confidence_to_trade"
              type="number"
              min="0"
              max="100"
              class="settings-input"
              data-testid="min-confidence-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="field-label">Max VIX</label>
            <input
              v-model.number="config.max_vix_to_trade"
              type="number"
              min="0"
              step="0.1"
              class="settings-input"
              data-testid="max-vix-input"
              @change="handleConfigUpdate"
            />
          </div>

          <div>
            <label class="field-label">Weekly Loss Limit (₹)</label>
            <input
              v-model.number="config.weekly_loss_limit"
              type="number"
              min="0"
              step="1000"
              class="settings-input"
              data-testid="weekly-loss-limit-input"
              @change="handleConfigUpdate"
            />
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons">
        <button
          class="btn-secondary"
          data-testid="reset-button"
          @click="resetToDefaults"
        >
          Reset to Defaults
        </button>
        <button
          :disabled="saving"
          class="btn-primary"
          data-testid="save-button"
          @click="saveConfiguration"
        >
          {{ saving ? 'Saving...' : 'Save Configuration' }}
        </button>
      </div>
    </div>
    </div>
  </KiteLayout>
</template>

<script setup>
import KiteLayout from '@/components/layout/KiteLayout.vue'
import AISubNav from '@/components/ai/AISubNav.vue'

import { ref, computed, onMounted } from 'vue'
import { useAIConfigStore } from '@/stores/aiConfig'
import { storeToRefs } from 'pinia'

const aiConfigStore = useAIConfigStore()
const { config, loading, saving, error, canGraduateToLive } = storeToRefs(aiConfigStore)

// Load configuration on mount
onMounted(async () => {
  try {
    await aiConfigStore.fetchConfig()
  } catch (err) {
    console.error('Failed to load AI configuration:', err)
  }
})

// Toggle deploy day
function toggleDeployDay(day) {
  if (!config.value.deploy_days) {
    config.value.deploy_days = []
  }

  const index = config.value.deploy_days.indexOf(day)
  if (index > -1) {
    config.value.deploy_days.splice(index, 1)
  } else {
    config.value.deploy_days.push(day)
  }

  handleConfigUpdate()
}

// Handle configuration updates (debounced auto-save)
let saveTimeout = null
function handleConfigUpdate() {
  // Clear existing timeout
  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }

  // Set new timeout for auto-save (2 seconds)
  saveTimeout = setTimeout(() => {
    saveConfiguration()
  }, 2000)
}

// Save configuration
async function saveConfiguration() {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
    saveTimeout = null
  }

  try {
    await aiConfigStore.saveConfig(config.value)
    console.log('Configuration saved successfully')
  } catch (err) {
    console.error('Failed to save configuration:', err)
  }
}

// Reset to defaults
async function resetToDefaults() {
  if (confirm('Are you sure you want to reset all settings to defaults?')) {
    try {
      await aiConfigStore.resetToDefaults()
    } catch (err) {
      console.error('Failed to reset configuration:', err)
    }
  }
}
</script>

<style scoped>
.ai-settings-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--kite-text-secondary, #6c757d);
  margin-top: 4px;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-card {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0 0 20px 0;
}

.field-group {
  margin-bottom: 20px;
}

.field-group:last-child {
  margin-bottom: 0;
}

.field-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 8px;
}

.field-hint {
  font-size: 13px;
  color: var(--kite-text-secondary, #6c757d);
  margin-top: 2px;
}

.settings-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  background: white;
  color: var(--kite-text-primary, #394046);
  transition: border-color 0.2s ease;
}

.settings-input:focus {
  outline: none;
  border-color: var(--kite-primary, #387ed1);
}

.settings-select {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  background: white;
  color: var(--kite-text-primary, #394046);
  cursor: pointer;
}

.settings-select:focus {
  outline: none;
  border-color: var(--kite-primary, #387ed1);
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: var(--kite-primary, #387ed1);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

/* Buttons */
.btn-primary {
  padding: 10px 20px;
  background: var(--kite-primary, #387ed1);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-primary:hover {
  background: var(--kite-primary-dark, #2c6cb8);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 10px 20px;
  background: white;
  color: var(--kite-text-primary, #394046);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: #d0d0d0;
}

/* Grid layouts */
.limits-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

@media (max-width: 768px) {
  .limits-grid {
    grid-template-columns: 1fr;
  }
}

/* Radio buttons */
.radio-group {
  display: flex;
  gap: 20px;
  margin-top: 8px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--kite-text-primary, #394046);
  cursor: pointer;
}

.radio-label input[type="radio"] {
  accent-color: var(--kite-primary, #387ed1);
}

.radio-label.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Checkbox */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--kite-text-primary, #394046);
  cursor: pointer;
  margin-bottom: 8px;
}

.checkbox-label input[type="checkbox"] {
  accent-color: var(--kite-primary, #387ed1);
}

/* Day selector */
.day-selector {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.day-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--kite-text-primary, #394046);
}

/* Confidence tiers */
.tiers-display {
  font-size: 13px;
  color: var(--kite-text-secondary, #6c757d);
}

.tier-row {
  padding: 4px 0;
}

.tier-hint {
  font-size: 12px;
  color: var(--kite-text-muted, #9aa3ad);
  margin-top: 8px;
}

/* Action buttons row */
.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* Error state */
.error-banner {
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red, #e53935);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
  color: var(--kite-red, #e53935);
}

/* Loading state */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--kite-text-secondary, #6c757d);
}

/* Graduation warning */
.graduation-warning {
  font-size: 12px;
  color: var(--kite-red, #e53935);
  margin-left: 8px;
}
</style>
