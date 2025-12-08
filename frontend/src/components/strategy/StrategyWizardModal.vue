<template>
  <div class="modal-overlay" @click.self="store.closeWizard()">
    <div class="wizard-modal" data-testid="strategy-wizard-modal">
      <!-- Header -->
      <div class="modal-header">
        <h2 data-testid="strategy-wizard-modal-title">Strategy Wizard</h2>
        <button class="close-btn" @click="store.closeWizard()" data-testid="strategy-wizard-modal-close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Progress -->
      <div class="wizard-progress">
        <div
          v-for="step in 3"
          :key="step"
          :class="['progress-step', { active: store.wizardStep >= step, current: store.wizardStep === step }]"
        >
          <div class="step-number">{{ step }}</div>
          <span class="step-label">{{ stepLabels[step - 1] }}</span>
        </div>
      </div>

      <!-- Step Content -->
      <div class="wizard-content">
        <!-- Recommendations (Step 4) -->
        <div v-if="store.hasRecommendations" class="step-content recommendations-step" data-testid="strategy-wizard-recommendations">
          <h3>Recommended Strategies</h3>
          <p class="step-desc">Based on your preferences, here are the best matches</p>

          <div class="recommendations-list">
            <div
              v-for="(rec, index) in store.recommendations"
              :key="rec.template.name"
              class="recommendation-item"
              :data-testid="`strategy-wizard-recommendation-${index}`"
            >
              <div class="rec-header">
                <span class="rec-name">{{ rec.template.display_name }}</span>
                <span class="rec-score" :data-testid="`strategy-wizard-recommendation-${index}-score`">{{ rec.score }}% Match</span>
              </div>
              <p class="rec-desc">{{ rec.template.description }}</p>
              <div v-if="rec.match_reasons" class="rec-reasons" :data-testid="`strategy-wizard-recommendation-${index}-reasons`">
                <span v-for="reason in rec.match_reasons" :key="reason" class="reason-tag">{{ reason }}</span>
              </div>
              <div class="rec-actions">
                <button class="btn-secondary" @click="store.openDetails(rec.template)" :data-testid="`strategy-wizard-recommendation-${index}-details`">Details</button>
                <button class="btn-primary" @click="deployFromWizard(rec.template)" :data-testid="`strategy-wizard-recommendation-${index}-deploy`">Deploy</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 1: Market Outlook -->
        <div v-else-if="store.wizardStep === 1" class="step-content" data-testid="strategy-wizard-step-1">
          <h3>What's your market outlook?</h3>
          <p class="step-desc">Select how you expect the market to move</p>

          <div class="options-grid">
            <button
              v-for="option in outlookOptions"
              :key="option.value"
              :class="['option-card', { selected: selectedOutlook === option.value }]"
              @click="selectOutlook(option.value)"
              :data-testid="`strategy-wizard-outlook-${option.value}`"
            >
              <span class="option-icon">{{ option.icon }}</span>
              <span class="option-label">{{ option.label }}</span>
              <span class="option-desc">{{ option.description }}</span>
            </button>
          </div>
        </div>

        <!-- Step 2: Volatility View -->
        <div v-else-if="store.wizardStep === 2" class="step-content" data-testid="strategy-wizard-step-2">
          <h3>What's your volatility view?</h3>
          <p class="step-desc">Do you expect volatility to increase or decrease?</p>

          <div class="options-grid">
            <button
              v-for="option in volatilityOptions"
              :key="option.value"
              :class="['option-card', { selected: selectedVolatility === option.value }]"
              @click="selectVolatility(option.value)"
              :data-testid="`strategy-wizard-volatility-${option.value === 'high_iv' ? 'high' : option.value === 'low_iv' ? 'low' : option.value}`"
            >
              <span class="option-icon">{{ option.icon }}</span>
              <span class="option-label">{{ option.label }}</span>
              <span class="option-desc">{{ option.description }}</span>
            </button>
          </div>
        </div>

        <!-- Step 3: Risk Tolerance -->
        <div v-else-if="store.wizardStep === 3" class="step-content" data-testid="strategy-wizard-step-3">
          <h3>What's your risk tolerance?</h3>
          <p class="step-desc">How much risk are you comfortable with?</p>

          <div class="options-grid risk-grid">
            <button
              v-for="option in riskOptions"
              :key="option.value"
              :class="['option-card', 'risk-card', option.value, { selected: selectedRisk === option.value }]"
              @click="selectRisk(option.value)"
              :data-testid="`strategy-wizard-risk-${option.value}`"
            >
              <span class="option-label">{{ option.label }}</span>
              <span class="option-desc">{{ option.description }}</span>
              <div class="risk-meter">
                <div class="meter-fill" :style="{ width: option.meter + '%' }"></div>
              </div>
            </button>
          </div>

          <!-- Optional: Experience Level -->
          <div class="optional-section">
            <label>Experience Level (optional)</label>
            <div class="experience-pills">
              <button
                v-for="level in ['beginner', 'intermediate', 'advanced']"
                :key="level"
                :class="['pill', { active: selectedExperience === level }]"
                @click="store.setWizardInput('experience_level', level)"
              >
                {{ level }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button
          v-if="store.wizardStep > 1"
          class="btn-secondary"
          @click="store.prevWizardStep()"
          data-testid="strategy-wizard-back-button"
        >
          Back
        </button>
        <div class="spacer"></div>
        <button
          v-if="store.wizardStep < 3"
          class="btn-primary"
          :disabled="!canProceed"
          @click="store.nextWizardStep()"
          data-testid="strategy-wizard-next-button"
        >
          Next
        </button>
        <button
          v-else
          class="btn-primary"
          :disabled="!store.wizardComplete || store.isLoading"
          @click="findStrategies"
          data-testid="strategy-wizard-get-recommendations"
        >
          <span v-if="store.isLoading">Finding...</span>
          <span v-else>Find Strategies</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useStrategyLibraryStore } from '@/stores/strategyLibrary'
import { storeToRefs } from 'pinia'

const store = useStrategyLibraryStore()
// Use storeToRefs for reactive binding to store state
const { wizardInputs } = storeToRefs(store)

const stepLabels = ['Outlook', 'Volatility', 'Risk']

// Computed properties for selections to ensure reactivity
const selectedOutlook = computed(() => wizardInputs.value.market_outlook)
const selectedVolatility = computed(() => wizardInputs.value.volatility_view)
const selectedRisk = computed(() => wizardInputs.value.risk_tolerance)
const selectedExperience = computed(() => wizardInputs.value.experience_level)

const outlookOptions = [
  { value: 'bullish', label: 'Bullish', icon: '📈', description: 'I expect the market to go up' },
  { value: 'bearish', label: 'Bearish', icon: '📉', description: 'I expect the market to go down' },
  { value: 'neutral', label: 'Neutral', icon: '⚖️', description: 'I expect sideways movement' },
  { value: 'volatile', label: 'Volatile', icon: '🌊', description: 'I expect a big move, unsure of direction' }
]

const volatilityOptions = [
  { value: 'high_iv', label: 'High IV', icon: '📊', description: 'IV is high, I expect it to drop' },
  { value: 'low_iv', label: 'Low IV', icon: '📉', description: 'IV is low, I expect it to rise' },
  { value: 'any', label: 'No View', icon: '🤷', description: 'I don\'t have a volatility view' }
]

const riskOptions = [
  { value: 'low', label: 'Conservative', description: 'Limited risk, defined outcomes', meter: 33 },
  { value: 'medium', label: 'Moderate', description: 'Balanced risk and reward', meter: 66 },
  { value: 'high', label: 'Aggressive', description: 'Higher risk for higher potential', meter: 100 }
]

const canProceed = computed(() => {
  if (store.wizardStep === 1) return selectedOutlook.value
  if (store.wizardStep === 2) return selectedVolatility.value
  return true
})

function selectOutlook(value) {
  store.setWizardInput('market_outlook', value)
}

function selectVolatility(value) {
  store.setWizardInput('volatility_view', value)
}

function selectRisk(value) {
  store.setWizardInput('risk_tolerance', value)
}

async function findStrategies() {
  await store.runWizard()
  // Don't close wizard - show recommendations inside it
}

function deployFromWizard(template) {
  store.closeWizard()
  store.openDeploy(template)
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
}

.wizard-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #212529;
  margin: 0;
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

/* Progress */
.wizard-progress {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 20px;
  background: #f8f9fa;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  opacity: 0.4;
}

.progress-step.active {
  opacity: 1;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #dee2e6;
  color: #495057;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.progress-step.active .step-number {
  background: #387ed1;
  color: white;
}

.progress-step.current .step-number {
  box-shadow: 0 0 0 3px rgba(56, 126, 209, 0.3);
}

.step-label {
  font-size: 12px;
  color: #6c757d;
}

/* Content */
.wizard-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.step-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: #212529;
  margin: 0 0 8px;
}

.step-desc {
  font-size: 14px;
  color: #6c757d;
  margin: 0 0 24px;
}

/* Options Grid */
.options-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.option-card {
  padding: 16px;
  border: 2px solid #e9ecef;
  border-radius: 10px;
  background: white;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.option-card:hover {
  border-color: #adb5bd;
  background: #f8f9fa;
}

.option-card.selected {
  border-color: #387ed1;
  background: #e7f1ff;
}

.option-icon {
  font-size: 28px;
}

.option-label {
  font-size: 15px;
  font-weight: 600;
  color: #212529;
}

.option-desc {
  font-size: 12px;
  color: #6c757d;
}

/* Risk Grid */
.risk-grid {
  grid-template-columns: repeat(3, 1fr);
}

.risk-card {
  text-align: center;
  align-items: center;
}

.risk-meter {
  width: 100%;
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
}

.meter-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.risk-card.low .meter-fill {
  background: #00b386;
}

.risk-card.medium .meter-fill {
  background: #f39c12;
}

.risk-card.high .meter-fill {
  background: #e74c3c;
}

/* Optional Section */
.optional-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e9ecef;
}

.optional-section label {
  display: block;
  font-size: 13px;
  color: #6c757d;
  margin-bottom: 12px;
}

.experience-pills {
  display: flex;
  gap: 8px;
}

.pill {
  padding: 8px 16px;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  background: white;
  font-size: 13px;
  color: #495057;
  cursor: pointer;
  text-transform: capitalize;
}

.pill:hover {
  background: #f8f9fa;
}

.pill.active {
  background: #387ed1;
  border-color: #387ed1;
  color: white;
}

/* Footer */
.modal-footer {
  display: flex;
  padding: 16px 24px;
  border-top: 1px solid #e9ecef;
  gap: 12px;
}

.spacer {
  flex: 1;
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

.btn-primary:hover {
  background: #2c5aa0;
}

.btn-primary:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

/* Recommendations */
.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.recommendation-item {
  padding: 16px;
  border: 1px solid #e9ecef;
  border-radius: 10px;
  background: white;
}

.rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rec-name {
  font-size: 16px;
  font-weight: 600;
  color: #212529;
}

.rec-score {
  font-size: 13px;
  font-weight: 600;
  color: #00b386;
  background: #d4edda;
  padding: 4px 8px;
  border-radius: 4px;
}

.rec-desc {
  font-size: 13px;
  color: #6c757d;
  margin: 0 0 12px;
  line-height: 1.4;
}

.rec-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.reason-tag {
  font-size: 11px;
  color: #495057;
  background: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
}

.rec-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.rec-actions .btn-secondary,
.rec-actions .btn-primary {
  padding: 8px 16px;
  font-size: 13px;
}
</style>
