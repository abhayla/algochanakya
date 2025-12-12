/**
 * Centralized Strategy Types Configuration
 *
 * This is the SINGLE SOURCE OF TRUTH for strategy types in the frontend.
 * Data is fetched from backend API and cached for use across components.
 *
 * Used by:
 * - Strategy Builder (regular)
 * - AutoPilot Strategy Builder
 * - Strategy Library
 */

import { ref, computed } from 'vue'
import api from '@/services/api'

// ============================================================================
// STATE - Reactive references for strategy types data
// ============================================================================

/** @type {import('vue').Ref<Object>} All strategy types keyed by name */
export const strategyTypes = ref({})

/** @type {import('vue').Ref<Object>} Category definitions with display properties */
export const categories = ref({})

/** @type {import('vue').Ref<boolean>} Loading state */
export const isLoading = ref(false)

/** @type {import('vue').Ref<string|null>} Error message if fetch fails */
export const error = ref(null)

/** @type {import('vue').Ref<boolean>} Whether data has been loaded */
export const isLoaded = ref(false)


// ============================================================================
// COMPUTED - Derived data from strategy types
// ============================================================================

/**
 * Strategy types grouped by category
 * @returns {Object} Object with category keys containing arrays of strategies
 */
export const strategiesByCategory = computed(() => {
  const grouped = {}
  for (const [key, strategy] of Object.entries(strategyTypes.value)) {
    const category = strategy.category || 'other'
    if (!grouped[category]) {
      grouped[category] = []
    }
    grouped[category].push({ key, ...strategy })
  }
  return grouped
})

/**
 * Flat list of all strategies with their keys
 * @returns {Array} Array of strategy objects with key property
 */
export const strategyList = computed(() => {
  return Object.entries(strategyTypes.value).map(([key, strategy]) => ({
    key,
    ...strategy
  }))
})

/**
 * Category list with counts
 * @returns {Array} Array of category objects with strategy count
 */
export const categoryList = computed(() => {
  return Object.entries(categories.value).map(([key, category]) => ({
    key,
    ...category,
    count: strategiesByCategory.value[key]?.length || 0
  }))
})


// ============================================================================
// FUNCTIONS - Load and access strategy types
// ============================================================================

/**
 * Load strategy types from backend API
 * Only fetches if not already loaded (or force=true)
 *
 * @param {boolean} force - Force reload even if already loaded
 * @returns {Promise<void>}
 */
export async function loadStrategyTypes(force = false) {
  // Skip if already loaded unless forced
  if (isLoaded.value && !force) {
    return
  }

  isLoading.value = true
  error.value = null

  try {
    const response = await api.get('/api/constants/strategy-types')
    strategyTypes.value = response.data.strategy_types || {}
    categories.value = response.data.categories || {}
    isLoaded.value = true
  } catch (err) {
    console.error('Failed to load strategy types:', err)
    error.value = err.message || 'Failed to load strategy types'
    // Use fallback data if API fails
    useFallbackData()
  } finally {
    isLoading.value = false
  }
}

/**
 * Get a strategy by its key name
 *
 * @param {string} name - Strategy key (e.g., 'iron_condor')
 * @returns {Object|null} Strategy object or null if not found
 */
export function getStrategyByName(name) {
  const strategy = strategyTypes.value[name]
  if (strategy) {
    return { key: name, ...strategy }
  }
  return null
}

/**
 * Get strategies in a specific category
 *
 * @param {string} category - Category key (e.g., 'bullish')
 * @returns {Array} Array of strategies in the category
 */
export function getStrategiesByCategory(category) {
  return strategiesByCategory.value[category] || []
}

/**
 * Get legs configuration for a strategy
 *
 * @param {string} name - Strategy key
 * @returns {Array} Array of leg configurations
 */
export function getStrategyLegs(name) {
  const strategy = strategyTypes.value[name]
  return strategy?.legs || []
}

/**
 * Check if a strategy type exists
 *
 * @param {string} name - Strategy key
 * @returns {boolean}
 */
export function hasStrategy(name) {
  return !!strategyTypes.value[name]
}


// ============================================================================
// FALLBACK DATA - Used if API is unavailable
// ============================================================================

/**
 * Use fallback data when API fails
 * This ensures the app remains functional offline
 */
function useFallbackData() {
  categories.value = {
    bullish: { name: 'Bullish', color: '#00b386', icon: 'trending-up' },
    bearish: { name: 'Bearish', color: '#e74c3c', icon: 'trending-down' },
    neutral: { name: 'Neutral', color: '#6c757d', icon: 'minus' },
    volatile: { name: 'Volatile', color: '#9b59b6', icon: 'activity' },
    income: { name: 'Income', color: '#f39c12', icon: 'dollar-sign' },
    advanced: { name: 'Advanced', color: '#3498db', icon: 'target' }
  }

  // Minimal fallback - just key strategies
  strategyTypes.value = {
    iron_condor: {
      display_name: 'Iron Condor',
      category: 'neutral',
      legs: [
        { type: 'PE', action: 'BUY', strike_offset: -200 },
        { type: 'PE', action: 'SELL', strike_offset: -100 },
        { type: 'CE', action: 'SELL', strike_offset: 100 },
        { type: 'CE', action: 'BUY', strike_offset: 200 }
      ]
    },
    short_straddle: {
      display_name: 'Short Straddle',
      category: 'neutral',
      legs: [
        { type: 'CE', action: 'SELL', strike_offset: 0 },
        { type: 'PE', action: 'SELL', strike_offset: 0 }
      ]
    },
    short_strangle: {
      display_name: 'Short Strangle',
      category: 'neutral',
      legs: [
        { type: 'CE', action: 'SELL', strike_offset: 100 },
        { type: 'PE', action: 'SELL', strike_offset: -100 }
      ]
    },
    bull_call_spread: {
      display_name: 'Bull Call Spread',
      category: 'bullish',
      legs: [
        { type: 'CE', action: 'BUY', strike_offset: 0 },
        { type: 'CE', action: 'SELL', strike_offset: 100 }
      ]
    },
    bear_put_spread: {
      display_name: 'Bear Put Spread',
      category: 'bearish',
      legs: [
        { type: 'PE', action: 'BUY', strike_offset: 0 },
        { type: 'PE', action: 'SELL', strike_offset: -100 }
      ]
    },
    long_straddle: {
      display_name: 'Long Straddle',
      category: 'volatile',
      legs: [
        { type: 'CE', action: 'BUY', strike_offset: 0 },
        { type: 'PE', action: 'BUY', strike_offset: 0 }
      ]
    },
    custom: {
      display_name: 'Custom Strategy',
      category: 'advanced',
      legs: []
    }
  }

  isLoaded.value = true
}


// ============================================================================
// DEFAULT EXPORT - Composable function
// ============================================================================

/**
 * Composable for using strategy types in components
 *
 * @returns {Object} Reactive refs and functions for strategy types
 *
 * @example
 * import { useStrategyTypes } from '@/constants/strategyTypes'
 *
 * const { strategyTypes, categories, loadStrategyTypes, getStrategyLegs } = useStrategyTypes()
 *
 * onMounted(() => {
 *   loadStrategyTypes()
 * })
 */
export function useStrategyTypes() {
  return {
    // State
    strategyTypes,
    categories,
    isLoading,
    error,
    isLoaded,

    // Computed
    strategiesByCategory,
    strategyList,
    categoryList,

    // Functions
    loadStrategyTypes,
    getStrategyByName,
    getStrategiesByCategory,
    getStrategyLegs,
    hasStrategy
  }
}

export default useStrategyTypes
