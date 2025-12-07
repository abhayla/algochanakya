<template>
  <div class="modal-overlay" @click.self="store.closeDetails()">
    <div class="details-modal" data-testid="strategy-details-modal">
      <!-- Header -->
      <div class="modal-header" :style="{ background: categoryColor }">
        <div class="header-content">
          <span class="category-badge">{{ categoryIcon }} {{ template?.category }}</span>
          <h2 data-testid="strategy-details-modal-title">{{ template?.display_name }}</h2>
          <p class="description" data-testid="strategy-details-description">{{ template?.description }}</p>
        </div>
        <button class="close-btn" @click="store.closeDetails()" data-testid="strategy-details-modal-close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="modal-content">
        <!-- Loading State -->
        <div v-if="store.isLoading" class="loading-state">
          <div class="spinner"></div>
          <p>Loading details...</p>
        </div>

        <template v-else-if="template">
          <!-- Key Metrics -->
          <section class="section">
            <h3>Key Metrics</h3>
            <div class="metrics-grid">
              <div class="metric-card profit">
                <span class="label">Max Profit</span>
                <span class="value">{{ template.max_profit }}</span>
              </div>
              <div class="metric-card loss">
                <span class="label">Max Loss</span>
                <span class="value">{{ template.max_loss }}</span>
              </div>
              <div class="metric-card">
                <span class="label">Breakeven</span>
                <span class="value">{{ template.breakeven || '--' }}</span>
              </div>
              <div class="metric-card">
                <span class="label">Win Probability</span>
                <span class="value">{{ template.win_probability || '--' }}</span>
              </div>
            </div>
          </section>

          <!-- Strategy Details -->
          <section class="section">
            <h3>Strategy Details</h3>
            <div class="details-grid">
              <div class="detail-item">
                <span class="label">Market Outlook</span>
                <span class="value capitalize">{{ template.market_outlook }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Volatility</span>
                <span class="value">{{ formatVolatility(template.volatility_preference) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Risk Level</span>
                <span :class="['value', 'risk-' + template.risk_level]">{{ template.risk_level }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Capital</span>
                <span class="value capitalize">{{ template.capital_requirement }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Difficulty</span>
                <span class="value capitalize">{{ template.difficulty_level }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Profit Target</span>
                <span class="value">{{ template.profit_target || '--' }}</span>
              </div>
            </div>
          </section>

          <!-- Greeks Exposure -->
          <section class="section">
            <h3>Greeks Exposure</h3>
            <div class="greeks-grid">
              <div :class="['greek-chip', { positive: template.theta_positive }]">
                <span class="greek-name">Theta</span>
                <span class="greek-value">{{ template.theta_positive ? 'Positive' : 'Negative' }}</span>
              </div>
              <div :class="['greek-chip', { positive: template.vega_positive }]">
                <span class="greek-name">Vega</span>
                <span class="greek-value">{{ template.vega_positive ? 'Positive' : 'Negative' }}</span>
              </div>
              <div :class="['greek-chip', { neutral: template.delta_neutral }]">
                <span class="greek-name">Delta</span>
                <span class="greek-value">{{ template.delta_neutral ? 'Neutral' : 'Directional' }}</span>
              </div>
              <div class="greek-chip">
                <span class="greek-name">Gamma Risk</span>
                <span class="greek-value capitalize">{{ template.gamma_risk || '--' }}</span>
              </div>
            </div>
          </section>

          <!-- Legs Structure -->
          <section class="section">
            <h3>Legs Structure</h3>
            <div class="legs-table">
              <div class="leg-row header">
                <span>Type</span>
                <span>Position</span>
                <span>Strike Offset</span>
              </div>
              <div
                v-for="(leg, idx) in template.legs_config"
                :key="idx"
                class="leg-row"
              >
                <span :class="['leg-type', leg.type.toLowerCase()]">{{ leg.type }}</span>
                <span :class="['leg-position', leg.position.toLowerCase()]">{{ leg.position }}</span>
                <span class="leg-offset">
                  {{ leg.strike_offset > 0 ? '+' : '' }}{{ leg.strike_offset }} pts
                </span>
              </div>
            </div>
          </section>

          <!-- When to Use -->
          <section class="section" data-testid="strategy-details-when-to-use">
            <h3>When to Use</h3>
            <p class="text-content">{{ template.when_to_use || `Use the ${template.display_name} strategy when you have a ${template.market_outlook} outlook on the market with ${template.volatility_preference?.replace('_', ' ') || 'moderate'} volatility expectations.` }}</p>
          </section>

          <!-- Pros & Cons -->
          <section v-if="template.pros || template.cons" class="section pros-cons">
            <div v-if="template.pros" class="pros" data-testid="strategy-details-pros">
              <h4>Pros</h4>
              <ul>
                <li v-for="pro in template.pros" :key="pro">{{ pro }}</li>
              </ul>
            </div>
            <div v-if="template.cons" class="cons" data-testid="strategy-details-cons">
              <h4>Cons</h4>
              <ul>
                <li v-for="con in template.cons" :key="con">{{ con }}</li>
              </ul>
            </div>
          </section>

          <!-- Exit Rules -->
          <section v-if="template.exit_rules" class="section" data-testid="strategy-details-exit-rules">
            <h3>Exit Rules</h3>
            <ul class="rules-list">
              <li v-for="rule in template.exit_rules" :key="rule">{{ rule }}</li>
            </ul>
          </section>

          <!-- Common Mistakes -->
          <section v-if="template.common_mistakes" class="section" data-testid="strategy-details-common-mistakes">
            <h3>Common Mistakes to Avoid</h3>
            <ul class="mistakes-list">
              <li v-for="mistake in template.common_mistakes" :key="mistake">{{ mistake }}</li>
            </ul>
          </section>

          <!-- Example -->
          <section v-if="template.example_setup" class="section example">
            <h3>Example Trade</h3>
            <div class="example-box">
              <div class="example-header">
                {{ template.example_underlying }} @ {{ template.example_spot }}
              </div>
              <p>{{ template.example_setup }}</p>
            </div>
          </section>
        </template>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn-secondary" @click="store.closeDetails()">Close</button>
        <button class="btn-primary" @click="deployStrategy" data-testid="strategy-details-deploy-button">
          Deploy This Strategy
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useStrategyLibraryStore } from '@/stores/strategyLibrary'

const store = useStrategyLibraryStore()

const template = computed(() => store.selectedTemplate)

const categoryColor = computed(() => {
  const config = store.categoryConfig[template.value?.category]
  return config?.color || '#6c757d'
})

const categoryIcon = computed(() => {
  const config = store.categoryConfig[template.value?.category]
  return config?.icon || ''
})

function formatVolatility(vol) {
  if (!vol) return '--'
  return vol.replace('_', ' ').replace('iv', 'IV')
}

function deployStrategy() {
  store.closeDetails()
  store.openDeploy(template.value)
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

.details-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Header */
.modal-header {
  position: relative;
  padding: 24px;
  color: white;
}

.header-content {
  position: relative;
  z-index: 1;
}

.category-badge {
  display: inline-block;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 11px;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.modal-header h2 {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px;
}

.modal-header .description {
  font-size: 14px;
  opacity: 0.9;
  margin: 0;
  line-height: 1.5;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 50%;
  padding: 6px;
  cursor: pointer;
  color: white;
  z-index: 2;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.close-btn svg {
  width: 20px;
  height: 20px;
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
  font-size: 16px;
  font-weight: 600;
  color: #212529;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e9ecef;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  text-align: center;
}

.metric-card .label {
  display: block;
  font-size: 11px;
  color: #6c757d;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.metric-card .value {
  font-size: 14px;
  font-weight: 600;
  color: #212529;
}

.metric-card.profit {
  background: #d4edda;
}

.metric-card.profit .value {
  color: #155724;
}

.metric-card.loss {
  background: #f8d7da;
}

.metric-card.loss .value {
  color: #721c24;
}

/* Details Grid */
.details-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.detail-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
}

.detail-item .label {
  display: block;
  font-size: 10px;
  color: #6c757d;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.detail-item .value {
  font-size: 13px;
  font-weight: 500;
  color: #212529;
}

.capitalize {
  text-transform: capitalize;
}

.risk-low { color: #00b386; }
.risk-medium { color: #f39c12; }
.risk-high { color: #e74c3c; }

/* Greeks */
.greeks-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.greek-chip {
  padding: 10px;
  background: #f8d7da;
  border-radius: 6px;
  text-align: center;
}

.greek-chip.positive {
  background: #d4edda;
}

.greek-chip.neutral {
  background: #e2f0ff;
}

.greek-name {
  display: block;
  font-size: 10px;
  color: #6c757d;
  text-transform: uppercase;
}

.greek-value {
  font-size: 12px;
  font-weight: 600;
  color: #212529;
}

/* Legs Table */
.legs-table {
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
}

.leg-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  padding: 10px 16px;
  border-bottom: 1px solid #e9ecef;
}

.leg-row.header {
  background: #e9ecef;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: #6c757d;
}

.leg-row:last-child {
  border-bottom: none;
}

.leg-type.ce { color: #00b386; }
.leg-type.pe { color: #e74c3c; }

.leg-position.buy { color: #00b386; }
.leg-position.sell { color: #e74c3c; }

/* Text Content */
.text-content {
  font-size: 14px;
  line-height: 1.6;
  color: #495057;
}

/* Pros & Cons */
.pros-cons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.pros h4, .cons h4 {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 8px;
}

.pros h4 { color: #00b386; }
.cons h4 { color: #e74c3c; }

.pros ul, .cons ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #495057;
}

.pros li, .cons li {
  margin-bottom: 4px;
}

/* Rules & Mistakes */
.rules-list, .mistakes-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #495057;
}

.rules-list li, .mistakes-list li {
  margin-bottom: 6px;
}

.mistakes-list {
  color: #856404;
}

/* Example */
.example-box {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.example-header {
  background: #e9ecef;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #495057;
}

.example-box p {
  padding: 12px 16px;
  margin: 0;
  font-size: 13px;
  color: #212529;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #387ed1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
</style>
