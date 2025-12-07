<template>
  <KiteLayout>
  <div class="strategy-library" data-testid="strategy-library-page">
    <!-- Header -->
    <div class="library-header" data-testid="strategy-library-header">
      <div class="header-left">
        <h1>Strategy Library</h1>
        <p class="subtitle">Pre-built options strategies for every market condition</p>
      </div>
      <div class="header-actions">
        <button
          class="wizard-btn"
          @click="store.openWizard()"
          data-testid="strategy-library-wizard-button"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
          Strategy Wizard
        </button>
      </div>
    </div>

    <!-- Recommendations Section (when wizard has results) -->
    <div v-if="store.hasRecommendations" class="recommendations-section" data-testid="strategy-library-recommendations">
      <div class="section-header">
        <h2>Recommended For You</h2>
        <button class="clear-btn" @click="store.resetWizard()">Clear</button>
      </div>
      <div class="recommendations-grid">
        <div
          v-for="rec in store.recommendations"
          :key="rec.template.name"
          class="recommendation-card"
          :data-testid="`strategy-library-rec-${rec.template.name}`"
        >
          <div class="rec-score">
            <span class="score">{{ rec.score }}%</span>
            <span class="match">Match</span>
          </div>
          <StrategyCard
            :template="rec.template"
            :match-reasons="rec.match_reasons"
            @click="store.openDetails(rec.template)"
            @deploy="store.openDeploy(rec.template)"
          />
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-section" data-testid="strategy-library-filters">
      <!-- Category Pills -->
      <div class="category-pills" data-testid="strategy-library-categories">
        <button
          :class="['pill', { active: !store.activeFilters.category }]"
          @click="store.setFilter('category', null)"
          data-testid="strategy-library-category-all"
        >
          All
        </button>
        <button
          v-for="cat in store.categories"
          :key="cat.category"
          :class="['pill', { active: store.activeFilters.category === cat.category }]"
          :style="{ '--cat-color': store.categoryConfig[cat.category]?.color }"
          @click="store.setFilter('category', cat.category)"
          :data-testid="`strategy-library-category-${cat.category}`"
        >
          {{ store.categoryConfig[cat.category]?.icon }} {{ cat.display_name }}
          <span class="count">{{ cat.count }}</span>
        </button>
      </div>

      <!-- Search and Filters Row -->
      <div class="filters-row">
        <div class="search-box" data-testid="strategy-library-search-container">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            type="text"
            v-model="store.activeFilters.search"
            placeholder="Search strategies..."
            data-testid="strategy-library-search-input"
          />
          <button
            v-if="store.activeFilters.search"
            class="search-clear"
            @click="store.activeFilters.search = ''"
            data-testid="strategy-library-search-clear"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="filter-dropdowns">
          <select
            v-model="store.activeFilters.riskLevel"
            data-testid="strategy-library-risk-filter"
          >
            <option :value="null">All Risk Levels</option>
            <option value="low">Low Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="high">High Risk</option>
          </select>

          <select
            v-model="store.activeFilters.difficulty"
            data-testid="strategy-library-difficulty-filter"
          >
            <option :value="null">All Levels</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>

          <label class="theta-toggle">
            <input
              type="checkbox"
              :checked="store.activeFilters.thetaPositive === true"
              @change="store.setFilter('thetaPositive', $event.target.checked ? true : null)"
            />
            <span>Theta Positive Only</span>
          </label>
        </div>
      </div>
    </div>

    <!-- Strategies Grid -->
    <div class="strategies-section">
      <div v-if="store.isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading strategies...</p>
      </div>

      <div v-else-if="store.error" class="error-state">
        <p>{{ store.error }}</p>
        <button @click="loadData">Retry</button>
      </div>

      <div v-else-if="store.filteredTemplates.length === 0" class="empty-state" data-testid="strategy-library-empty-state">
        <p>No strategies match your filters</p>
        <button @click="store.clearFilters()">Clear Filters</button>
      </div>

      <div v-else class="strategies-grid" data-testid="strategy-library-cards-grid">
        <StrategyCard
          v-for="template in store.filteredTemplates"
          :key="template.name"
          :template="template"
          :in-comparison="store.isInComparison(template)"
          @click="store.openDetails(template)"
          @deploy="store.openDeploy(template)"
          @compare="toggleComparison(template)"
        />
      </div>
    </div>

    <!-- Comparison Bar -->
    <Transition name="slide-up">
      <div v-if="store.comparisonCount > 0" class="comparison-bar" data-testid="strategy-comparison-bar">
        <div class="comparison-items">
          <span class="compare-label">Compare:</span>
          <span class="compare-count" data-testid="strategy-comparison-count">{{ store.comparisonCount }}</span>
          <div
            v-for="template in store.comparisonList"
            :key="template.name"
            class="compare-chip"
          >
            {{ template.display_name }}
            <button @click="store.removeFromComparison(template)">&times;</button>
          </div>
        </div>
        <div class="comparison-actions">
          <button class="clear-compare" @click="store.clearComparison()" data-testid="strategy-comparison-clear">Clear</button>
          <button
            class="compare-btn"
            :disabled="!store.canCompare"
            @click="store.openCompare()"
            data-testid="strategy-comparison-compare-button"
          >
            Compare {{ store.comparisonCount }} Strategies
          </button>
        </div>
      </div>
    </Transition>

    <!-- Modals -->
    <StrategyWizardModal v-if="store.showWizardModal" />
    <StrategyDetailsModal v-if="store.showDetailsModal" />
    <StrategyDeployModal v-if="store.showDeployModal" />
    <StrategyCompareModal v-if="store.showCompareModal" />
  </div>
  </KiteLayout>
</template>

<script setup>
import { onMounted } from 'vue'
import { useStrategyLibraryStore } from '@/stores/strategyLibrary'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import StrategyCard from '@/components/strategy/StrategyCard.vue'
import StrategyWizardModal from '@/components/strategy/StrategyWizardModal.vue'
import StrategyDetailsModal from '@/components/strategy/StrategyDetailsModal.vue'
import StrategyDeployModal from '@/components/strategy/StrategyDeployModal.vue'
import StrategyCompareModal from '@/components/strategy/StrategyCompareModal.vue'

const store = useStrategyLibraryStore()

async function loadData() {
  await Promise.all([
    store.fetchTemplates(),
    store.fetchCategories()
  ])
}

function toggleComparison(template) {
  if (store.isInComparison(template)) {
    store.removeFromComparison(template)
  } else {
    store.addToComparison(template)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.strategy-library {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 80px;
}

/* Header */
.library-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.library-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #212529;
  margin: 0;
}

.subtitle {
  font-size: 14px;
  color: #6c757d;
  margin: 4px 0 0;
}

.wizard-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #387ed1 0%, #2c5aa0 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.wizard-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(56, 126, 209, 0.3);
}

.wizard-btn svg {
  width: 18px;
  height: 18px;
}

/* Recommendations */
.recommendations-section {
  margin-bottom: 32px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  border: 1px solid #dee2e6;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #212529;
  margin: 0;
}

.clear-btn {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-size: 13px;
  color: #6c757d;
  cursor: pointer;
}

.clear-btn:hover {
  background: #f8f9fa;
  border-color: #adb5bd;
}

.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.recommendation-card {
  position: relative;
}

.rec-score {
  position: absolute;
  top: -8px;
  right: 12px;
  background: #387ed1;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  z-index: 1;
  display: flex;
  gap: 4px;
  align-items: center;
}

.rec-score .match {
  font-weight: 400;
  opacity: 0.9;
}

/* Filters */
.filters-section {
  margin-bottom: 24px;
}

.category-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.pill {
  padding: 8px 16px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  font-size: 13px;
  color: #495057;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.pill:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.pill.active {
  background: var(--cat-color, #387ed1);
  border-color: var(--cat-color, #387ed1);
  color: white;
}

.pill .count {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.pill.active .count {
  background: rgba(255, 255, 255, 0.3);
}

.filters-row {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  flex: 1;
  min-width: 200px;
  max-width: 400px;
}

.search-box svg {
  width: 18px;
  height: 18px;
  color: #6c757d;
}

.search-box input {
  border: none;
  background: transparent;
  font-size: 14px;
  width: 100%;
  outline: none;
}

.search-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #6c757d;
  border-radius: 4px;
}

.search-clear:hover {
  background: #e9ecef;
  color: #495057;
}

.search-clear svg {
  width: 16px;
  height: 16px;
}

.filter-dropdowns {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-dropdowns select {
  padding: 8px 12px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  cursor: pointer;
}

.theta-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #495057;
  cursor: pointer;
}

.theta-toggle input {
  cursor: pointer;
}

/* Strategies Grid */
.strategies-section {
  min-height: 300px;
}

.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* Loading, Error, Empty States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #6c757d;
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

.error-state button,
.empty-state button {
  margin-top: 12px;
  padding: 8px 16px;
  background: #387ed1;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

/* Comparison Bar */
.comparison-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #dee2e6;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 100;
}

.comparison-items {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.compare-label {
  font-size: 13px;
  font-weight: 500;
  color: #495057;
}

.compare-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #e9ecef;
  border-radius: 16px;
  font-size: 13px;
  color: #212529;
}

.compare-chip button {
  background: none;
  border: none;
  font-size: 16px;
  color: #6c757d;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.compare-chip button:hover {
  color: #e74c3c;
}

.comparison-actions {
  display: flex;
  gap: 12px;
}

.clear-compare {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 13px;
  color: #6c757d;
  cursor: pointer;
}

.compare-btn {
  padding: 8px 20px;
  background: #387ed1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.compare-btn:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

/* Transitions */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
