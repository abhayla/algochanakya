<template>
  <KiteLayout>
  <div class="templates-page" data-testid="autopilot-templates-page">
    <!-- Header -->
    <div class="templates-header" data-testid="autopilot-templates-header">
      <div>
        <h1 class="templates-title">Strategy Templates</h1>
        <p class="templates-subtitle">Pre-built strategy configurations ready to deploy</p>
      </div>
      <router-link
        to="/autopilot"
        class="back-link"
        data-testid="autopilot-templates-back-btn"
      >
        <svg class="icon-svg-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Dashboard
      </router-link>
    </div>

    <!-- Filters -->
    <div class="filters-card" data-testid="autopilot-templates-filters">
      <div class="filters-grid">
        <!-- Search -->
        <div class="filter-field">
          <label class="filter-label">Search</label>
          <input
            v-model="filters.search"
            type="text"
            placeholder="Search templates..."
            class="filter-input"
            data-testid="autopilot-templates-search"
            @input="debouncedFetch"
          />
        </div>

        <!-- Category -->
        <div class="filter-field">
          <label class="filter-label">Category</label>
          <select
            v-model="filters.category"
            class="filter-select"
            data-testid="autopilot-templates-category-filter"
            @change="fetchTemplates"
          >
            <option :value="null">All Categories</option>
            <option value="income">Income</option>
            <option value="directional">Directional</option>
            <option value="volatility">Volatility</option>
            <option value="hedging">Hedging</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <!-- Underlying -->
        <div class="filter-field">
          <label class="filter-label">Underlying</label>
          <select
            v-model="filters.underlying"
            class="filter-select"
            data-testid="autopilot-templates-underlying-filter"
            @change="fetchTemplates"
          >
            <option :value="null">All Underlyings</option>
            <option value="NIFTY">NIFTY</option>
            <option value="BANKNIFTY">BANKNIFTY</option>
            <option value="FINNIFTY">FINNIFTY</option>
            <option value="SENSEX">SENSEX</option>
          </select>
        </div>

        <!-- Risk Level -->
        <div class="filter-field">
          <label class="filter-label">Risk Level</label>
          <select
            v-model="filters.riskLevel"
            class="filter-select"
            data-testid="autopilot-templates-risk-filter"
            @change="fetchTemplates"
          >
            <option :value="null">All Levels</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading templates...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="fetchTemplates" class="link-btn">Try again</button>
    </div>

    <!-- Templates Grid -->
    <div v-else-if="templates.length > 0" class="templates-grid" data-testid="autopilot-templates-grid">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        :data-testid="`autopilot-template-card-${template.id}`"
        @click="selectTemplate(template)"
      >
        <div class="template-card-content">
          <!-- Header -->
          <div class="template-card-header">
            <div>
              <h3 class="template-name">{{ template.name }}</h3>
              <div class="template-badges">
                <span v-if="template.is_system" class="badge badge-system">
                  System
                </span>
                <span
                  v-if="template.category"
                  class="badge badge-category"
                >
                  {{ template.category }}
                </span>
              </div>
            </div>
            <span :class="['risk-badge', getRiskClass(template.risk_level)]">
              {{ template.risk_level || 'Medium' }}
            </span>
          </div>

          <!-- Description -->
          <p class="template-description">
            {{ template.description || 'No description available' }}
          </p>

          <!-- Stats -->
          <div class="template-stats">
            <div class="stat-box">
              <div class="stat-value">{{ template.underlying || 'NIFTY' }}</div>
              <div class="stat-label">Underlying</div>
            </div>
            <div class="stat-box">
              <div class="stat-value">{{ template.expected_return_pct || '--' }}%</div>
              <div class="stat-label">Exp. Return</div>
            </div>
            <div class="stat-box">
              <div class="stat-value">{{ template.max_risk_pct || '--' }}%</div>
              <div class="stat-label">Max Risk</div>
            </div>
          </div>

          <!-- Rating -->
          <div class="template-footer">
            <div class="rating">
              <svg class="star-icon" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              <span>{{ template.avg_rating?.toFixed(1) || '0.0' }} ({{ template.rating_count || 0 }})</span>
            </div>
            <div class="deployments">
              {{ template.usage_count || 0 }} deployments
            </div>
          </div>

          <!-- Deploy Button -->
          <button
            class="deploy-btn"
            :data-testid="`autopilot-template-deploy-${template.id}`"
            @click.stop="showDeployModal(template)"
          >
            Deploy Strategy
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <h3 class="empty-title">No templates found</h3>
      <p class="empty-text">Try adjusting your filters</p>
    </div>

    <!-- Pagination -->
    <div v-if="pagination.totalPages > 1" class="pagination">
      <button
        :disabled="pagination.page <= 1"
        class="pagination-btn"
        @click="changePage(pagination.page - 1)"
      >
        Previous
      </button>
      <span class="pagination-text">
        Page {{ pagination.page }} of {{ pagination.totalPages }}
      </span>
      <button
        :disabled="pagination.page >= pagination.totalPages"
        class="pagination-btn"
        @click="changePage(pagination.page + 1)"
      >
        Next
      </button>
    </div>

    <!-- Deploy Modal -->
    <div v-if="showDeployModalFlag" class="modal-overlay" data-testid="autopilot-template-deploy-modal">
      <div class="modal-content modal-sm">
        <h3 class="modal-title">Deploy Template</h3>

        <div class="form-fields">
          <div class="form-field">
            <label class="filter-label">Strategy Name</label>
            <input
              v-model="deployOptions.name"
              type="text"
              class="filter-input"
              :placeholder="selectedTemplate?.name"
              data-testid="autopilot-template-deploy-name"
            />
          </div>

          <div class="form-field">
            <label class="filter-label">Lots</label>
            <input
              v-model.number="deployOptions.lots"
              type="number"
              min="1"
              max="50"
              class="filter-input"
              data-testid="autopilot-template-deploy-lots"
            />
          </div>

          <div class="form-field">
            <label class="checkbox-label">
              <input
                v-model="deployOptions.activateImmediately"
                type="checkbox"
                class="checkbox-input"
                data-testid="autopilot-template-deploy-activate"
              />
              <span>Activate immediately after deployment</span>
            </label>
          </div>
        </div>

        <div class="modal-actions">
          <button
            class="btn-secondary"
            @click="closeDeployModal"
          >
            Cancel
          </button>
          <button
            class="btn-primary"
            :disabled="deploying"
            data-testid="autopilot-template-deploy-confirm"
            @click="deployTemplate"
          >
            {{ deploying ? 'Deploying...' : 'Deploy' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Template Detail Modal -->
    <div v-if="selectedTemplate && !showDeployModalFlag" class="modal-overlay" data-testid="autopilot-template-details-modal">
      <div class="modal-content modal-xl">
        <!-- Header with Navigation -->
        <div class="modal-header-nav">
          <button
            class="nav-btn"
            :disabled="!hasPrev"
            @click="navigateToPrev"
            data-testid="autopilot-template-details-prev"
          >
            <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div class="modal-header-content">
            <h3 class="modal-title">{{ selectedTemplate.name }}</h3>
            <div class="template-badges">
              <span v-if="selectedTemplate.is_system" class="badge badge-system">System</span>
              <span v-if="selectedTemplate.category" class="badge badge-category">{{ selectedTemplate.category }}</span>
              <span :class="['risk-badge', getRiskClass(selectedTemplate.risk_level)]">
                {{ selectedTemplate.risk_level || 'Medium' }}
              </span>
            </div>
            <!-- Tags -->
            <div v-if="selectedTemplate.tags?.length" class="template-tags">
              <span v-for="tag in selectedTemplate.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>

          <button
            class="nav-btn"
            :disabled="!hasNext"
            @click="navigateToNext"
            data-testid="autopilot-template-details-next"
          >
            <svg class="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <button @click="selectedTemplate = null" class="close-btn" data-testid="autopilot-template-details-close">
            <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Description -->
        <p class="detail-description">{{ selectedTemplate.description }}</p>

        <!-- Two Column Layout -->
        <div class="detail-grid">
          <!-- Left: Payoff Chart -->
          <div class="detail-chart" data-testid="autopilot-template-details-chart">
            <div v-if="payoffLoading" class="chart-loading">
              <div class="loading-spinner"></div>
            </div>
            <PayoffChart
              v-else-if="payoffData.spotPrices.length"
              :spotPrices="payoffData.spotPrices"
              :totalPnl="payoffData.totalPnl"
            />
            <div v-else class="chart-placeholder">
              Payoff diagram not available
            </div>
          </div>

          <!-- Right: Stats -->
          <div class="detail-stats-vertical">
            <div class="detail-stat-row">
              <span class="stat-label">Underlying</span>
              <span class="stat-value">{{ selectedTemplate.underlying || 'NIFTY' }}</span>
            </div>
            <div class="detail-stat-row">
              <span class="stat-label">Expected Return</span>
              <span class="stat-value">{{ selectedTemplate.expected_return_pct || '--' }}%</span>
            </div>
            <div class="detail-stat-row">
              <span class="stat-label">Max Risk</span>
              <span class="stat-value">{{ selectedTemplate.max_risk_pct || '--' }}%</span>
            </div>
            <div class="detail-stat-row">
              <span class="stat-label">Risk Level</span>
              <span :class="['stat-value', 'risk-' + (selectedTemplate.risk_level || 'medium').toLowerCase()]">
                {{ selectedTemplate.risk_level || 'Medium' }}
              </span>
            </div>
            <div class="detail-stat-row">
              <span class="stat-label">Deployments</span>
              <span class="stat-value">{{ selectedTemplate.usage_count || 0 }}</span>
            </div>
            <div class="detail-stat-row">
              <span class="stat-label">Rating</span>
              <span class="stat-value">
                <svg class="star-icon-sm" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                {{ selectedTemplate.avg_rating?.toFixed(1) || '0.0' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Legs Configuration Table -->
        <div v-if="selectedTemplate.strategy_config?.legs_config?.length" class="legs-section" data-testid="autopilot-template-details-legs">
          <h4 class="section-heading">Strategy Legs</h4>
          <table class="legs-table">
            <thead>
              <tr>
                <th>Leg</th>
                <th>Type</th>
                <th>Action</th>
                <th>Strike Selection</th>
                <th>Qty Multiplier</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(leg, idx) in sortedLegsConfig" :key="leg.id || idx">
                <td>leg_{{ leg.sortedIndex }}</td>
                <td>
                  <span :class="['leg-type', leg.contract_type === 'CE' ? 'leg-ce' : 'leg-pe']">
                    {{ leg.contract_type }}
                  </span>
                </td>
                <td>
                  <span :class="['leg-action', leg.transaction_type === 'BUY' ? 'leg-buy' : 'leg-sell']">
                    {{ leg.transaction_type }}
                  </span>
                </td>
                <td>
                  {{ formatStrikeSelection(leg.strike_selection) }}
                </td>
                <td>{{ leg.quantity_multiplier || 1 }}x</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Educational Content -->
        <div v-if="selectedTemplate.educational_content" class="educational-content">
          <div v-if="selectedTemplate.educational_content.when_to_use" class="edu-section">
            <h4 class="edu-heading">When to Use</h4>
            <p class="edu-text">{{ selectedTemplate.educational_content.when_to_use }}</p>
          </div>

          <div class="edu-columns">
            <div v-if="selectedTemplate.educational_content.pros?.length" class="edu-section">
              <h4 class="edu-heading edu-pros">Pros</h4>
              <ul class="edu-list">
                <li v-for="(pro, idx) in selectedTemplate.educational_content.pros" :key="idx">{{ pro }}</li>
              </ul>
            </div>

            <div v-if="selectedTemplate.educational_content.cons?.length" class="edu-section">
              <h4 class="edu-heading edu-cons">Cons</h4>
              <ul class="edu-list">
                <li v-for="(con, idx) in selectedTemplate.educational_content.cons" :key="idx">{{ con }}</li>
              </ul>
            </div>
          </div>

          <div v-if="selectedTemplate.educational_content.exit_rules?.length" class="edu-section">
            <h4 class="edu-heading">Exit Rules</h4>
            <ul class="edu-list">
              <li v-for="(rule, idx) in selectedTemplate.educational_content.exit_rules" :key="idx">{{ rule }}</li>
            </ul>
          </div>

          <div v-if="selectedTemplate.educational_content.common_mistakes?.length" class="edu-section">
            <h4 class="edu-heading edu-warning">Common Mistakes</h4>
            <ul class="edu-list">
              <li v-for="(mistake, idx) in selectedTemplate.educational_content.common_mistakes" :key="idx">{{ mistake }}</li>
            </ul>
          </div>
        </div>

        <!-- Footer -->
        <div class="modal-footer">
          <button class="btn-secondary" @click="selectedTemplate = null">Close</button>
          <button class="btn-rate" @click="openRatingModal" data-testid="autopilot-template-rate-btn">
            Rate Template
          </button>
          <button
            class="btn-secondary btn-use-template"
            @click="useTemplate(selectedTemplate)"
            data-testid="autopilot-template-use-btn"
          >
            Use Template
          </button>
          <button class="btn-primary" @click="showDeployModal(selectedTemplate)">
            Deploy This Template
          </button>
        </div>
      </div>
    </div>

    <!-- Rating Modal -->
    <div
      v-if="showRatingModal"
      class="modal-overlay"
      data-testid="autopilot-template-rating-modal"
      @click.self="closeRatingModal"
    >
      <div class="modal-content modal-sm">
        <div class="modal-header">
          <h3 class="modal-title">Rate Template</h3>
          <button @click="closeRatingModal" class="close-btn">
            <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="rating-content">
          <p class="rating-prompt">How would you rate {{ selectedTemplate?.name }}?</p>

          <div class="rating-stars">
            <button
              v-for="star in 5"
              :key="star"
              class="star-btn"
              :class="{ 'star-filled': (ratingHover || ratingValue) >= star }"
              :data-testid="`autopilot-template-rating-star-${star}`"
              @click="setRating(star)"
              @mouseenter="setRatingHover(star)"
              @mouseleave="setRatingHover(0)"
            >
              <svg class="star-icon-lg" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            </button>
          </div>

          <p class="rating-text">{{ ratingValue > 0 ? `${ratingValue} star${ratingValue > 1 ? 's' : ''}` : 'Select a rating' }}</p>
        </div>

        <div class="modal-actions">
          <button
            class="btn-secondary"
            @click="closeRatingModal"
          >
            Cancel
          </button>
          <button
            class="btn-primary"
            :disabled="ratingValue === 0 || submittingRating"
            data-testid="autopilot-template-rating-submit"
            @click="submitRating"
          >
            {{ submittingRating ? 'Submitting...' : 'Submit Rating' }}
          </button>
        </div>
      </div>
    </div>
  </div>
  </KiteLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import { useRouter } from 'vue-router'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import PayoffChart from '@/components/strategy/PayoffChart.vue'
import '@/assets/css/strategy-table.css'

const store = useAutopilotStore()
const router = useRouter()

const templates = ref([])
const loading = ref(false)
const error = ref(null)
const selectedTemplate = ref(null)
const selectedTemplateIndex = ref(-1)
const showDeployModalFlag = ref(false)
const deploying = ref(false)

// Payoff chart state
const payoffData = ref({ spotPrices: [], totalPnl: [] })
const payoffLoading = ref(false)

// Rating modal state
const showRatingModal = ref(false)
const ratingValue = ref(0)
const ratingHover = ref(0)
const submittingRating = ref(false)

const filters = reactive({
  search: '',
  category: null,
  underlying: null,
  riskLevel: null
})

const pagination = reactive({
  page: 1,
  pageSize: 12,
  total: 0,
  totalPages: 0
})

const deployOptions = reactive({
  name: '',
  lots: 1,
  activateImmediately: false
})

let debounceTimeout = null

const debouncedFetch = () => {
  if (debounceTimeout) clearTimeout(debounceTimeout)
  debounceTimeout = setTimeout(() => {
    fetchTemplates()
  }, 300)
}

const fetchTemplates = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await store.fetchTemplates({
      page: pagination.page,
      pageSize: pagination.pageSize,
      search: filters.search || undefined,
      category: filters.category || undefined,
      underlying: filters.underlying || undefined,
      riskLevel: filters.riskLevel || undefined
    })

    templates.value = response.data || []
    pagination.total = response.total || 0
    pagination.totalPages = response.total_pages || 0
  } catch (err) {
    error.value = err.message || 'Failed to load templates'
  } finally {
    loading.value = false
  }
}

const changePage = (page) => {
  pagination.page = page
  fetchTemplates()
}

const selectTemplate = async (template) => {
  loading.value = true
  try {
    // Fetch full template data with strategy_config and educational_content
    const fullTemplate = await store.fetchTemplate(template.id)
    selectedTemplate.value = fullTemplate
    selectedTemplateIndex.value = templates.value.findIndex(t => t.id === template.id)

    // Fetch payoff data
    await fetchPayoffData(fullTemplate)
  } catch (err) {
    error.value = 'Failed to load template details'
    console.error('Error fetching template:', err)
  } finally {
    loading.value = false
  }
}

// Navigation methods
const navigateToPrev = async () => {
  if (selectedTemplateIndex.value > 0) {
    await selectTemplate(templates.value[selectedTemplateIndex.value - 1])
  }
}

const navigateToNext = async () => {
  if (selectedTemplateIndex.value < templates.value.length - 1) {
    await selectTemplate(templates.value[selectedTemplateIndex.value + 1])
  }
}

const hasPrev = computed(() => selectedTemplateIndex.value > 0)
const hasNext = computed(() => selectedTemplateIndex.value < templates.value.length - 1)

// Sorted legs configuration for display
const sortedLegsConfig = computed(() => {
  if (!selectedTemplate.value?.strategy_config?.legs_config) return []
  return [...selectedTemplate.value.strategy_config.legs_config]
    .sort((a, b) => {
      const offsetA = a.strike_selection?.offset || 0
      const offsetB = b.strike_selection?.offset || 0
      return offsetA - offsetB // Lower strikes first
    })
    .map((leg, idx) => ({
      ...leg,
      sortedIndex: idx + 1 // Renumber legs 1, 2, 3, 4
    }))
})

// Fetch payoff data for template
const fetchPayoffData = async (template) => {
  if (!template.strategy_config?.legs_config || template.strategy_config.legs_config.length === 0) {
    payoffData.value = { spotPrices: [], totalPnl: [] }
    return
  }

  payoffLoading.value = true
  try {
    // Calculate actual P/L based on template legs configuration
    // Uses intrinsic value at expiry for each leg

    // Generate sample payoff data based on template legs
    const spotBase = 26000 // NIFTY approximate
    const spotPrices = []
    const totalPnl = []

    // Lot size mapping for different underlyings
    const lotSizes = { NIFTY: 25, BANKNIFTY: 15, FINNIFTY: 25, SENSEX: 10 }
    const underlying = template.strategy_config?.underlying || 'NIFTY'
    const lotSize = lotSizes[underlying] || 25

    // Generate spot price range
    for (let i = -20; i <= 20; i++) {
      spotPrices.push(spotBase + (i * 100))
    }

    // Calculate actual P/L for each spot price based on legs
    const legs = template.strategy_config.legs_config

    // Estimate credit received (for preview purposes)
    // For Iron Condor, credit is typically 20-30% of spread width
    const spreadWidth = 200 // Distance between sold and bought strikes
    const estimatedCreditPerLot = spreadWidth * 0.25 // ~25% of spread width
    const numSpreads = legs.filter(l => l.transaction_type === 'SELL').length
    const totalCredit = estimatedCreditPerLot * numSpreads * lotSize

    for (let spot of spotPrices) {
      let intrinsicPayout = 0

      for (const leg of legs) {
        // Get strike from ATM offset
        const offset = leg.strike_selection?.offset || 0
        const strike = spotBase + offset

        // Calculate intrinsic value at expiry
        let intrinsic = 0
        if (leg.contract_type === 'CE') {
          intrinsic = Math.max(0, spot - strike)
        } else { // PE
          intrinsic = Math.max(0, strike - spot)
        }

        // SELL: we pay out intrinsic, BUY: we receive intrinsic
        if (leg.transaction_type === 'SELL') {
          intrinsicPayout += intrinsic * lotSize
        } else { // BUY
          intrinsicPayout -= intrinsic * lotSize
        }
      }

      // Net P/L = Credit - Payout
      // Positive = profit, Negative = loss
      const pnl = totalCredit - intrinsicPayout
      totalPnl.push(pnl)
    }

    payoffData.value = { spotPrices, totalPnl }
  } catch (err) {
    console.error('Error fetching payoff data:', err)
    payoffData.value = { spotPrices: [], totalPnl: [] }
  } finally {
    payoffLoading.value = false
  }
}

// Format strike selection for display
const formatStrikeSelection = (selection) => {
  if (!selection) return 'ATM'
  if (selection.mode === 'atm_offset') {
    const offset = selection.offset || 0
    if (offset === 0) return 'ATM'
    return offset > 0 ? `ATM +${offset}` : `ATM ${offset}`
  }
  if (selection.mode === 'delta_based') {
    return `Delta ${selection.target_delta}`
  }
  if (selection.mode === 'fixed') {
    return `Fixed ${selection.strike}`
  }
  return selection.mode
}

const showDeployModal = (template) => {
  selectedTemplate.value = template
  deployOptions.name = template.name
  deployOptions.lots = 1
  deployOptions.activateImmediately = false
  showDeployModalFlag.value = true
}

const closeDeployModal = () => {
  showDeployModalFlag.value = false
}

const deployTemplate = async () => {
  if (!selectedTemplate.value) return

  deploying.value = true

  try {
    const strategy = await store.deployTemplate(selectedTemplate.value.id, {
      name: deployOptions.name || selectedTemplate.value.name,
      lots: deployOptions.lots,
      activate_immediately: deployOptions.activateImmediately
    })

    closeDeployModal()
    selectedTemplate.value = null

    // Navigate to the new strategy
    router.push(`/autopilot/strategies/${strategy.id}`)
  } catch (err) {
    error.value = err.message || 'Failed to deploy template'
  } finally {
    deploying.value = false
  }
}

const getRiskClass = (level) => {
  switch (level?.toLowerCase()) {
    case 'low':
      return 'risk-low'
    case 'high':
      return 'risk-high'
    default:
      return 'risk-medium'
  }
}

// Rating modal functions
const openRatingModal = () => {
  ratingValue.value = 0
  ratingHover.value = 0
  showRatingModal.value = true
}

const closeRatingModal = () => {
  showRatingModal.value = false
  ratingValue.value = 0
  ratingHover.value = 0
}

const setRating = (value) => {
  ratingValue.value = value
}

const setRatingHover = (value) => {
  ratingHover.value = value
}

const submitRating = async () => {
  if (!selectedTemplate.value || ratingValue.value === 0) return

  submittingRating.value = true

  try {
    await store.rateTemplate(selectedTemplate.value.id, ratingValue.value)
    // Refresh the template data
    await fetchTemplates()
    closeRatingModal()
  } catch (err) {
    error.value = err.message || 'Failed to submit rating'
  } finally {
    submittingRating.value = false
  }
}

// Use Template - navigate to Strategy Builder
const useTemplate = (template) => {
  if (!template) return
  router.push({
    path: '/autopilot/strategies/new',
    query: { templateId: template.id }
  })
}

onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped>
/* ===== Page Container ===== */
.templates-page {
  padding: 24px;
}

/* ===== Header ===== */
.templates-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.templates-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.templates-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.back-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--kite-blue);
  text-decoration: none;
  font-weight: 500;
}

.back-link:hover {
  color: var(--kite-blue-dark, #1565c0);
}

/* ===== Icons ===== */
.icon-svg {
  width: 24px;
  height: 24px;
}

.icon-svg-sm {
  width: 20px;
  height: 20px;
}

/* ===== Filters ===== */
.filters-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  margin-bottom: 24px;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .filters-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.filter-field {
  display: flex;
  flex-direction: column;
}

.filter-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.filter-input,
.filter-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
  color: var(--kite-text-primary);
  background: white;
}

.filter-input:focus,
.filter-select:focus {
  outline: none;
  border-color: var(--kite-blue);
  box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
}

/* ===== Loading State ===== */
.loading-state {
  text-align: center;
  padding: 48px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
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

/* ===== Error State ===== */
.error-state {
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red);
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 24px;
}

.error-message {
  color: var(--kite-red);
}

.link-btn {
  margin-top: 8px;
  color: var(--kite-red);
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: underline;
}

/* ===== Templates Grid ===== */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 24px;
}

@media (min-width: 768px) {
  .templates-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .templates-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ===== Template Card ===== */
.template-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: box-shadow 0.2s ease;
}

.template-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.template-card-content {
  padding: 20px;
}

.template-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.template-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.template-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.badge {
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 4px;
}

.badge-system {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.badge-category {
  background: var(--kite-border-light, #f5f5f5);
  color: var(--kite-text-secondary);
  text-transform: capitalize;
}

.risk-badge {
  padding: 4px 8px;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 4px;
  text-transform: capitalize;
}

.risk-low {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.risk-medium {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.risk-high {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.template-description {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== Template Stats ===== */
.template-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.stat-box {
  background: var(--kite-body-bg, #f9fafb);
  border-radius: 4px;
  padding: 8px;
  text-align: center;
}

.stat-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--kite-text-muted, #9e9e9e);
}

/* ===== Template Footer ===== */
.template-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.rating {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--kite-text-secondary);
}

.star-icon {
  width: 16px;
  height: 16px;
  color: #ffc107;
}

.deployments {
  color: var(--kite-text-muted, #9e9e9e);
}

/* ===== Deploy Button ===== */
.deploy-btn {
  width: 100%;
  margin-top: 16px;
  padding: 10px;
  background: var(--kite-blue);
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.deploy-btn:hover {
  background: var(--kite-blue-dark, #1565c0);
}

/* ===== Empty State ===== */
.empty-state {
  text-align: center;
  padding: 48px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto;
  color: var(--kite-text-muted, #9e9e9e);
}

.empty-title {
  margin-top: 16px;
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.empty-text {
  margin-top: 8px;
  color: var(--kite-text-secondary);
}

/* ===== Pagination ===== */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  background: white;
  color: var(--kite-text-primary);
  cursor: pointer;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--kite-table-hover, #f5f5f5);
}

.pagination-text {
  color: var(--kite-text-secondary);
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
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  margin: 16px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-sm {
  width: 100%;
  max-width: 400px;
  padding: 24px;
}

.modal-lg {
  width: 100%;
  max-width: 640px;
  padding: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.close-btn {
  padding: 4px;
  color: var(--kite-text-muted, #9e9e9e);
  background: none;
  border: none;
  cursor: pointer;
}

.close-btn:hover {
  color: var(--kite-text-secondary);
}

/* ===== Form Fields ===== */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  cursor: pointer;
}

.checkbox-input {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}

/* ===== Modal Actions ===== */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border);
}

.btn-secondary {
  padding: 8px 16px;
  color: var(--kite-text-secondary);
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  color: var(--kite-text-primary);
}

.btn-primary {
  padding: 8px 16px;
  background: var(--kite-blue);
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--kite-blue-dark, #1565c0);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== Detail Modal ===== */
.detail-description {
  color: var(--kite-text-secondary);
  margin-bottom: 24px;
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 640px) {
  .detail-stats {
    grid-template-columns: repeat(4, 1fr);
  }
}

.detail-stat-box {
  background: var(--kite-body-bg, #f9fafb);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.detail-stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

/* ===== Educational Content ===== */
.educational-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.edu-section {
  margin-bottom: 8px;
}

.edu-heading {
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 4px;
}

.edu-pros {
  color: var(--kite-green);
}

.edu-cons {
  color: var(--kite-red);
}

.edu-text {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.edu-list {
  list-style: disc;
  list-style-position: inside;
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Rate Button ===== */
.btn-rate {
  padding: 8px 16px;
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange, #ff9800);
  border: 1px solid var(--kite-orange, #ff9800);
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-rate:hover {
  background: var(--kite-orange, #ff9800);
  color: white;
}

/* ===== Rating Modal ===== */
.rating-content {
  text-align: center;
  padding: 16px 0;
}

.rating-prompt {
  font-size: 1rem;
  color: var(--kite-text-primary);
  margin-bottom: 20px;
}

.rating-stars {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.star-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  transition: transform 0.15s ease;
  color: var(--kite-border, #e0e0e0);
}

.star-btn:hover {
  transform: scale(1.15);
}

.star-btn.star-filled {
  color: #ffc107;
}

.star-icon-lg {
  width: 40px;
  height: 40px;
}

.rating-text {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  font-weight: 500;
}

/* ===== Utilities ===== */
.capitalize {
  text-transform: capitalize;
}

/* ===== Enhanced Modal Styles ===== */

/* Modal XL size */
.modal-xl {
  width: 100%;
  max-width: 900px;
  padding: 24px;
}

/* Navigation Header */
.modal-header-nav {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.modal-header-content {
  flex: 1;
}

.nav-btn {
  padding: 8px;
  background: var(--kite-body-bg, #f9fafb);
  border: 1px solid var(--kite-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-btn:hover:not(:disabled) {
  background: var(--kite-table-hover, #f5f5f5);
  border-color: var(--kite-blue);
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.nav-icon {
  width: 20px;
  height: 20px;
}

/* Tags */
.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.tag {
  padding: 2px 8px;
  font-size: 0.75rem;
  background: var(--kite-body-bg, #f9fafb);
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-secondary);
}

/* Two Column Grid */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

@media (min-width: 640px) {
  .detail-grid {
    grid-template-columns: 1.5fr 1fr;
  }
}

.detail-chart {
  min-height: 200px;
  background: var(--kite-body-bg, #f9fafb);
  border-radius: 8px;
  padding: 16px;
}

.chart-loading, .chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--kite-text-muted);
}

/* Vertical Stats */
.detail-stats-vertical {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--kite-body-bg, #f9fafb);
  border-radius: 4px;
}

/* Legs Table */
.legs-section {
  margin-bottom: 24px;
}

.section-heading {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.legs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.legs-table th,
.legs-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--kite-border);
}

.legs-table th {
  background: var(--kite-body-bg, #f9fafb);
  font-weight: 500;
  color: var(--kite-text-secondary);
}

.leg-type {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.leg-ce {
  background: #e3f2fd;
  color: #1976d2;
}

.leg-pe {
  background: #fce4ec;
  color: #c2185b;
}

.leg-action {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.leg-buy {
  background: #e8f5e9;
  color: #388e3c;
}

.leg-sell {
  background: #ffebee;
  color: #d32f2f;
}

/* Educational Columns */
.edu-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.edu-warning {
  color: var(--kite-orange, #ff9800);
}

.star-icon-sm {
  width: 14px;
  height: 14px;
  color: #ffc107;
  vertical-align: middle;
  margin-right: 4px;
}

/* Use Template Button */
.btn-use-template {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue, #387ed1);
  border: 1px solid var(--kite-blue, #387ed1);
}

.btn-use-template:hover {
  background: var(--kite-blue, #387ed1);
  color: white;
}
</style>
