<template>
  <div class="modal-overlay" @click.self="store.closeCompare()">
    <div class="compare-modal" data-testid="strategy-compare-modal">
      <!-- Header -->
      <div class="modal-header">
        <h2 data-testid="strategy-compare-modal-title">Compare Strategies</h2>
        <button class="close-btn" @click="store.closeCompare()" data-testid="strategy-compare-modal-close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="modal-content">
        <!-- Loading State -->
        <div v-if="isLoading" class="loading-state">
          <div class="spinner"></div>
          <p>Comparing strategies...</p>
        </div>

        <!-- Comparison Table -->
        <template v-else>
          <div class="compare-table" :style="{ '--cols': strategies.length }" data-testid="strategy-compare-table">
            <!-- Strategy Headers -->
            <div class="compare-row header-row">
              <div class="row-label"></div>
              <div
                v-for="strategy in strategies"
                :key="strategy.name"
                class="strategy-header"
                :style="{ background: getCategoryColor(strategy.category) }"
              >
                <span class="category">{{ getCategoryIcon(strategy.category) }} {{ strategy.category }}</span>
                <h3>{{ strategy.display_name }}</h3>
              </div>
            </div>

            <!-- Basic Info Section -->
            <div class="section-divider">Basic Information</div>

            <div class="compare-row">
              <div class="row-label">Description</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value desc">
                {{ strategy.description }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Legs</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                <div class="legs-display">
                  <span
                    v-for="(leg, idx) in strategy.legs_config"
                    :key="idx"
                    :class="['leg-badge', leg.position.toLowerCase()]"
                  >
                    {{ leg.position }} {{ leg.type }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Risk & Reward Section -->
            <div class="section-divider">Risk & Reward</div>

            <div class="compare-row">
              <div class="row-label">Max Profit</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value profit">
                {{ strategy.max_profit }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Max Loss</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value loss">
                {{ strategy.max_loss }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Breakeven</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                {{ strategy.breakeven || '--' }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Win Probability</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                {{ strategy.win_probability || '--' }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Risk Level</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                <span :class="['risk-badge', `risk-${strategy.risk_level}`]">
                  {{ strategy.risk_level }}
                </span>
              </div>
            </div>

            <!-- Market Conditions Section -->
            <div class="section-divider">Market Conditions</div>

            <div class="compare-row">
              <div class="row-label">Market Outlook</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value capitalize">
                {{ strategy.market_outlook }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Volatility</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                {{ formatVolatility(strategy.volatility_preference) }}
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Capital Required</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value capitalize">
                {{ strategy.capital_requirement }}
              </div>
            </div>

            <!-- Greeks Section -->
            <div class="section-divider">Greeks Exposure</div>

            <div class="compare-row">
              <div class="row-label">Theta</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                <span :class="['greek-badge', { positive: strategy.theta_positive }]">
                  {{ strategy.theta_positive ? 'Positive' : 'Negative' }}
                </span>
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Vega</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                <span :class="['greek-badge', { positive: strategy.vega_positive }]">
                  {{ strategy.vega_positive ? 'Positive' : 'Negative' }}
                </span>
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Delta</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                <span :class="['greek-badge', { neutral: strategy.delta_neutral }]">
                  {{ strategy.delta_neutral ? 'Neutral' : 'Directional' }}
                </span>
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Gamma Risk</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value capitalize">
                {{ strategy.gamma_risk || '--' }}
              </div>
            </div>

            <!-- Additional Info Section -->
            <div class="section-divider">Additional Info</div>

            <div class="compare-row">
              <div class="row-label">Difficulty</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                <span :class="['difficulty-badge', `level-${strategy.difficulty_level}`]">
                  {{ strategy.difficulty_level }}
                </span>
              </div>
            </div>

            <div class="compare-row">
              <div class="row-label">Profit Target</div>
              <div v-for="strategy in strategies" :key="strategy.name" class="row-value">
                {{ strategy.profit_target || '--' }}
              </div>
            </div>
          </div>

          <!-- Actions Row -->
          <div class="strategy-actions">
            <div
              v-for="strategy in strategies"
              :key="strategy.name"
              class="action-cell"
            >
              <button class="btn-deploy" @click="deployStrategy(strategy)">
                Deploy {{ strategy.display_name }}
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn-secondary" @click="store.closeCompare()">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStrategyLibraryStore } from '@/stores/strategyLibrary'

const store = useStrategyLibraryStore()

const isLoading = ref(false)
const comparisonData = ref(null)

const strategies = computed(() => store.comparisonList)

function getCategoryColor(category) {
  return store.categoryConfig[category]?.color || '#6c757d'
}

function getCategoryIcon(category) {
  return store.categoryConfig[category]?.icon || ''
}

function formatVolatility(vol) {
  if (!vol) return '--'
  return vol.replace('_', ' ').replace('iv', 'IV')
}

function deployStrategy(strategy) {
  store.closeCompare()
  store.openDeploy(strategy)
}

async function loadComparison() {
  isLoading.value = true
  try {
    const result = await store.compareStrategies()
    if (result.success) {
      comparisonData.value = result.data
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadComparison()
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

.compare-modal {
  background: white;
  border-radius: 12px;
  width: 95%;
  max-width: 1000px;
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

/* Content */
.modal-content {
  flex: 1;
  overflow-x: auto;
  overflow-y: auto;
  padding: 24px;
}

/* Comparison Table */
.compare-table {
  min-width: 100%;
  border-collapse: collapse;
}

.compare-row {
  display: grid;
  grid-template-columns: 140px repeat(var(--cols, 2), 1fr);
  border-bottom: 1px solid #e9ecef;
}

.compare-row:last-child {
  border-bottom: none;
}

.row-label {
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #6c757d;
  background: #f8f9fa;
  display: flex;
  align-items: center;
}

.row-value {
  padding: 12px 16px;
  font-size: 13px;
  color: #212529;
  display: flex;
  align-items: center;
  border-left: 1px solid #e9ecef;
}

.row-value.desc {
  font-size: 12px;
  color: #6c757d;
  line-height: 1.4;
}

.row-value.profit {
  color: #00b386;
  font-weight: 500;
}

.row-value.loss {
  color: #e74c3c;
  font-weight: 500;
}

.capitalize {
  text-transform: capitalize;
}

/* Header Row */
.header-row .row-label {
  background: transparent;
}

.strategy-header {
  padding: 16px;
  color: white;
  border-left: 1px solid rgba(255, 255, 255, 0.2);
}

.strategy-header .category {
  font-size: 11px;
  text-transform: uppercase;
  opacity: 0.9;
}

.strategy-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 6px 0 0;
}

/* Section Divider */
.section-divider {
  grid-column: 1 / -1;
  padding: 10px 16px;
  background: #e9ecef;
  font-size: 12px;
  font-weight: 600;
  color: #495057;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Legs Display */
.legs-display {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.leg-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.leg-badge.buy {
  background: #d4edda;
  color: #155724;
}

.leg-badge.sell {
  background: #f8d7da;
  color: #721c24;
}

/* Risk Badge */
.risk-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: capitalize;
}

.risk-badge.risk-low {
  background: #d4edda;
  color: #155724;
}

.risk-badge.risk-medium {
  background: #fff3cd;
  color: #856404;
}

.risk-badge.risk-high {
  background: #f8d7da;
  color: #721c24;
}

/* Greek Badge */
.greek-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  background: #f8d7da;
  color: #721c24;
}

.greek-badge.positive {
  background: #d4edda;
  color: #155724;
}

.greek-badge.neutral {
  background: #e2f0ff;
  color: #0056b3;
}

/* Difficulty Badge */
.difficulty-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: capitalize;
}

.difficulty-badge.level-beginner {
  background: #d4edda;
  color: #155724;
}

.difficulty-badge.level-intermediate {
  background: #fff3cd;
  color: #856404;
}

.difficulty-badge.level-advanced {
  background: #f8d7da;
  color: #721c24;
}

/* Strategy Actions */
.strategy-actions {
  display: grid;
  grid-template-columns: 140px repeat(var(--cols, 2), 1fr);
  margin-top: 24px;
  padding-top: 16px;
  border-top: 2px solid #e9ecef;
}

.strategy-actions::before {
  content: '';
}

.action-cell {
  padding: 0 16px;
}

.btn-deploy {
  width: 100%;
  padding: 10px 16px;
  background: #387ed1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-deploy:hover {
  background: #2c5aa0;
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
</style>
