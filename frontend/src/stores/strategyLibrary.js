import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'

export const useStrategyLibraryStore = defineStore('strategyLibrary', () => {
  // State
  const templates = ref([])
  const categories = ref([])
  const selectedTemplate = ref(null)
  const wizardInputs = ref({
    market_outlook: null,
    volatility_view: null,
    risk_tolerance: null,
    capital_size: null,
    experience_level: null,
    underlying: 'NIFTY'
  })
  const recommendations = ref([])
  const comparisonList = ref([])
  const deployedStrategy = ref(null)

  // UI state
  const isLoading = ref(false)
  const error = ref(null)
  const activeFilters = ref({
    category: null,
    riskLevel: null,
    difficulty: null,
    thetaPositive: null,
    search: ''
  })

  // Modal state
  const showWizardModal = ref(false)
  const showDetailsModal = ref(false)
  const showDeployModal = ref(false)
  const showCompareModal = ref(false)
  const wizardStep = ref(1)

  // Category display names and colors
  const categoryConfig = {
    bullish: { name: 'Bullish', color: '#00b386', icon: '📈' },
    bearish: { name: 'Bearish', color: '#e74c3c', icon: '📉' },
    neutral: { name: 'Neutral', color: '#6c757d', icon: '⚖️' },
    volatile: { name: 'Volatile', color: '#9b59b6', icon: '🌊' },
    income: { name: 'Income', color: '#f39c12', icon: '💰' },
    advanced: { name: 'Advanced', color: '#3498db', icon: '🎯' }
  }

  // Getters
  const filteredTemplates = computed(() => {
    let result = templates.value

    if (activeFilters.value.category) {
      result = result.filter(t => t.category === activeFilters.value.category)
    }
    if (activeFilters.value.riskLevel) {
      result = result.filter(t => t.risk_level === activeFilters.value.riskLevel)
    }
    if (activeFilters.value.difficulty) {
      result = result.filter(t => t.difficulty_level === activeFilters.value.difficulty)
    }
    if (activeFilters.value.thetaPositive !== null) {
      result = result.filter(t => t.theta_positive === activeFilters.value.thetaPositive)
    }
    if (activeFilters.value.search) {
      const search = activeFilters.value.search.toLowerCase()
      result = result.filter(t =>
        t.display_name.toLowerCase().includes(search) ||
        t.description.toLowerCase().includes(search)
      )
    }

    return result
  })

  const wizardComplete = computed(() => {
    return wizardInputs.value.market_outlook &&
           wizardInputs.value.volatility_view &&
           wizardInputs.value.risk_tolerance
  })

  const hasRecommendations = computed(() => recommendations.value.length > 0)

  const comparisonCount = computed(() => comparisonList.value.length)

  const canCompare = computed(() => comparisonList.value.length >= 2 && comparisonList.value.length <= 4)

  // Actions
  async function fetchTemplates(filters = {}) {
    isLoading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (filters.category) params.append('category', filters.category)
      if (filters.risk_level) params.append('risk_level', filters.risk_level)
      if (filters.difficulty) params.append('difficulty', filters.difficulty)
      if (filters.theta_positive !== undefined) params.append('theta_positive', filters.theta_positive)
      if (filters.search) params.append('search', filters.search)

      const response = await api.get(`/api/strategy-library/templates?${params.toString()}`)
      templates.value = response.data
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch templates'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchCategories() {
    try {
      const response = await api.get('/api/strategy-library/templates/categories')
      categories.value = response.data.categories
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch categories'
      return { success: false, error: error.value }
    }
  }

  async function fetchTemplateDetails(name) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.get(`/api/strategy-library/templates/${name}`)
      selectedTemplate.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch template details'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function runWizard() {
    if (!wizardComplete.value) {
      return { success: false, error: 'Please complete all wizard steps' }
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/strategy-library/wizard', wizardInputs.value)
      recommendations.value = response.data.recommendations
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Wizard failed'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function deployStrategy(templateName, options = {}) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/strategy-library/deploy', {
        template_name: templateName,
        underlying: options.underlying || 'NIFTY',
        expiry: options.expiry || null,
        lots: options.lots || 1,
        atm_strike: options.atm_strike || null
      })
      deployedStrategy.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to deploy strategy'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function compareStrategies() {
    if (!canCompare.value) {
      return { success: false, error: 'Select 2-4 strategies to compare' }
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/strategy-library/compare', {
        template_names: comparisonList.value.map(t => t.name)
      })
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to compare strategies'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPopular(limit = 10) {
    try {
      const response = await api.get(`/api/strategy-library/popular?limit=${limit}`)
      return { success: true, data: response.data.strategies }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch popular strategies'
      return { success: false, error: error.value }
    }
  }

  // Filter actions
  function setFilter(key, value) {
    activeFilters.value[key] = value
  }

  function clearFilters() {
    activeFilters.value = {
      category: null,
      riskLevel: null,
      difficulty: null,
      thetaPositive: null,
      search: ''
    }
  }

  // Comparison actions
  function addToComparison(template) {
    if (comparisonList.value.length >= 4) {
      return { success: false, error: 'Maximum 4 strategies for comparison' }
    }
    if (comparisonList.value.find(t => t.name === template.name)) {
      return { success: false, error: 'Already in comparison' }
    }
    comparisonList.value.push(template)
    return { success: true }
  }

  function removeFromComparison(template) {
    comparisonList.value = comparisonList.value.filter(t => t.name !== template.name)
  }

  function clearComparison() {
    comparisonList.value = []
  }

  function isInComparison(template) {
    return comparisonList.value.some(t => t.name === template.name)
  }

  // Wizard actions
  function setWizardInput(key, value) {
    wizardInputs.value[key] = value
  }

  function resetWizard() {
    wizardInputs.value = {
      market_outlook: null,
      volatility_view: null,
      risk_tolerance: null,
      capital_size: null,
      experience_level: null,
      underlying: 'NIFTY'
    }
    wizardStep.value = 1
    recommendations.value = []
  }

  function nextWizardStep() {
    if (wizardStep.value < 3) {
      wizardStep.value++
    }
  }

  function prevWizardStep() {
    if (wizardStep.value > 1) {
      wizardStep.value--
    }
  }

  // Modal actions
  function openWizard() {
    resetWizard()
    showWizardModal.value = true
  }

  function closeWizard() {
    showWizardModal.value = false
  }

  function openDetails(template) {
    selectedTemplate.value = template
    showDetailsModal.value = true
    // Fetch full details
    fetchTemplateDetails(template.name)
  }

  function closeDetails() {
    showDetailsModal.value = false
  }

  function openDeploy(template) {
    selectedTemplate.value = template
    showDeployModal.value = true
  }

  function closeDeploy() {
    showDeployModal.value = false
    deployedStrategy.value = null
  }

  function openCompare() {
    if (canCompare.value) {
      showCompareModal.value = true
    }
  }

  function closeCompare() {
    showCompareModal.value = false
  }

  // Reset
  function reset() {
    templates.value = []
    categories.value = []
    selectedTemplate.value = null
    recommendations.value = []
    comparisonList.value = []
    deployedStrategy.value = null
    isLoading.value = false
    error.value = null
    clearFilters()
    resetWizard()
    showWizardModal.value = false
    showDetailsModal.value = false
    showDeployModal.value = false
    showCompareModal.value = false
  }

  return {
    // State
    templates,
    categories,
    selectedTemplate,
    wizardInputs,
    recommendations,
    comparisonList,
    deployedStrategy,
    isLoading,
    error,
    activeFilters,

    // Modal state
    showWizardModal,
    showDetailsModal,
    showDeployModal,
    showCompareModal,
    wizardStep,

    // Config
    categoryConfig,

    // Getters
    filteredTemplates,
    wizardComplete,
    hasRecommendations,
    comparisonCount,
    canCompare,

    // Actions
    fetchTemplates,
    fetchCategories,
    fetchTemplateDetails,
    runWizard,
    deployStrategy,
    compareStrategies,
    fetchPopular,

    // Filter actions
    setFilter,
    clearFilters,

    // Comparison actions
    addToComparison,
    removeFromComparison,
    clearComparison,
    isInComparison,

    // Wizard actions
    setWizardInput,
    resetWizard,
    nextWizardStep,
    prevWizardStep,

    // Modal actions
    openWizard,
    closeWizard,
    openDetails,
    closeDetails,
    openDeploy,
    closeDeploy,
    openCompare,
    closeCompare,

    // Reset
    reset
  }
})
