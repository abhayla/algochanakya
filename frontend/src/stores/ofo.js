import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'
import { getLotSize } from '@/constants/trading'
import { useStrategyStore } from './strategy'

/**
 * OFO (Options For Options) Store
 *
 * Manages state for finding and displaying the best option strategy combinations.
 */
export const useOFOStore = defineStore('ofo', () => {
  // =========================================================================
  // STATE
  // =========================================================================

  // Selection state
  const underlying = ref('NIFTY')
  const expiry = ref('')
  const expiries = ref([])

  // Strategy selection (multi-select)
  const selectedStrategies = ref([])

  // Configuration
  const strikeRange = ref(10) // ±strikes from ATM (5, 10, 15, 20)
  const lots = ref(1)

  // Results
  const results = ref({}) // strategy_type -> array of top 3 results
  const spotPrice = ref(0)
  const atmStrike = ref(0)
  const lotSize = ref(getLotSize('NIFTY'))
  const calculationTimeMs = ref(0)
  const totalCombinationsEvaluated = ref(0)
  const lastCalculated = ref(null)

  // Auto-refresh
  const autoRefreshEnabled = ref(false)
  const autoRefreshInterval = ref(5) // minutes
  let autoRefreshTimer = null

  // UI state
  const isLoading = ref(false)
  const error = ref(null)

  // Available strategies (loaded from API)
  const availableStrategies = ref([
    { key: 'iron_condor', name: 'Iron Condor', category: 'neutral', legs_count: 4 },
    { key: 'iron_butterfly', name: 'Iron Butterfly', category: 'neutral', legs_count: 4 },
    { key: 'short_straddle', name: 'Short Straddle', category: 'neutral', legs_count: 2 },
    { key: 'short_strangle', name: 'Short Strangle', category: 'neutral', legs_count: 2 },
    { key: 'long_straddle', name: 'Long Straddle', category: 'volatile', legs_count: 2 },
    { key: 'long_strangle', name: 'Long Strangle', category: 'volatile', legs_count: 2 },
    { key: 'bull_call_spread', name: 'Bull Call Spread', category: 'bullish', legs_count: 2 },
    { key: 'bear_put_spread', name: 'Bear Put Spread', category: 'bearish', legs_count: 2 },
    { key: 'butterfly_spread', name: 'Butterfly Spread', category: 'neutral', legs_count: 4 }
  ])

  // =========================================================================
  // GETTERS
  // =========================================================================

  const selectedCount = computed(() => selectedStrategies.value.length)

  const hasResults = computed(() => Object.keys(results.value).length > 0)

  const orderedResults = computed(() => {
    // Return results in the order of selectedStrategies
    const ordered = {}
    for (const strategyKey of selectedStrategies.value) {
      if (results.value[strategyKey]) {
        ordered[strategyKey] = results.value[strategyKey]
      }
    }
    return ordered
  })

  const lastCalculatedFormatted = computed(() => {
    if (!lastCalculated.value) return null
    const date = new Date(lastCalculated.value)
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  })

  // =========================================================================
  // ACTIONS
  // =========================================================================

  /**
   * Set underlying and fetch expiries
   */
  async function setUnderlying(ul) {
    underlying.value = ul.toUpperCase()
    lotSize.value = getLotSize(underlying.value)
    expiry.value = ''
    results.value = {}
    lastCalculated.value = null
    await fetchExpiries()
  }

  /**
   * Fetch available expiries for selected underlying
   */
  async function fetchExpiries() {
    try {
      const response = await api.get('/api/options/expiries', {
        params: { underlying: underlying.value }
      })
      expiries.value = response.data.expiries || []

      // Auto-select first expiry
      if (expiries.value.length > 0 && !expiry.value) {
        expiry.value = expiries.value[0]
      }
    } catch (err) {
      console.error('[OFO] Failed to fetch expiries:', err)
      error.value = 'Failed to load expiries'
    }
  }

  /**
   * Toggle strategy selection
   */
  function toggleStrategy(strategyKey) {
    const idx = selectedStrategies.value.indexOf(strategyKey)
    if (idx === -1) {
      selectedStrategies.value.push(strategyKey)
    } else {
      selectedStrategies.value.splice(idx, 1)
    }
  }

  /**
   * Check if strategy is selected
   */
  function isStrategySelected(strategyKey) {
    return selectedStrategies.value.includes(strategyKey)
  }

  /**
   * Select all strategies
   */
  function selectAllStrategies() {
    selectedStrategies.value = availableStrategies.value.map(s => s.key)
  }

  /**
   * Clear all strategy selections
   */
  function clearStrategies() {
    selectedStrategies.value = []
  }

  /**
   * Calculate best strategy combinations
   */
  async function calculate() {
    if (!underlying.value || !expiry.value) {
      error.value = 'Please select underlying and expiry'
      return
    }

    if (selectedStrategies.value.length === 0) {
      error.value = 'Please select at least one strategy'
      return
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/ofo/calculate', {
        underlying: underlying.value,
        expiry: expiry.value,
        strategy_types: selectedStrategies.value,
        strike_range: strikeRange.value,
        lots: lots.value
      })

      const data = response.data
      results.value = data.results || {}
      spotPrice.value = data.spot_price || 0
      atmStrike.value = data.atm_strike || 0
      lotSize.value = data.lot_size || getLotSize(underlying.value)
      calculationTimeMs.value = data.calculation_time_ms || 0
      totalCombinationsEvaluated.value = data.total_combinations_evaluated || 0
      lastCalculated.value = data.calculated_at || new Date().toISOString()

      console.log(`[OFO] Calculated ${totalCombinationsEvaluated.value} combinations in ${calculationTimeMs.value}ms`)
    } catch (err) {
      console.error('[OFO] Calculation failed:', err)
      error.value = err.response?.data?.detail || 'Failed to calculate strategies'
      results.value = {}
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Start auto-refresh timer
   */
  function startAutoRefresh() {
    stopAutoRefresh()
    autoRefreshEnabled.value = true
    autoRefreshTimer = setInterval(() => {
      if (selectedStrategies.value.length > 0 && expiry.value) {
        calculate()
      }
    }, autoRefreshInterval.value * 60 * 1000)
    console.log(`[OFO] Auto-refresh started: every ${autoRefreshInterval.value} minutes`)
  }

  /**
   * Stop auto-refresh timer
   */
  function stopAutoRefresh() {
    autoRefreshEnabled.value = false
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer)
      autoRefreshTimer = null
    }
    console.log('[OFO] Auto-refresh stopped')
  }

  /**
   * Toggle auto-refresh
   */
  function toggleAutoRefresh() {
    if (autoRefreshEnabled.value) {
      stopAutoRefresh()
    } else {
      startAutoRefresh()
    }
  }

  /**
   * Set auto-refresh interval and restart if enabled
   */
  function setAutoRefreshInterval(minutes) {
    autoRefreshInterval.value = minutes
    if (autoRefreshEnabled.value) {
      startAutoRefresh()
    }
  }

  /**
   * Open strategy in Strategy Builder
   */
  async function openInStrategyBuilder(result) {
    const strategyStore = useStrategyStore()

    // Set underlying and expiry
    await strategyStore.setUnderlying(underlying.value)

    // Clear existing legs
    strategyStore.clearLegs()

    // Add each leg from the result
    for (const leg of result.legs) {
      strategyStore.addLegFromOFO({
        expiry_date: leg.expiry,
        contract_type: leg.contract_type,
        transaction_type: leg.transaction_type,
        strike_price: leg.strike,
        lots: leg.lots,
        entry_price: leg.cmp,
        instrument_token: leg.instrument_token,
        tradingsymbol: leg.tradingsymbol
      })
    }

    // Return route path for navigation
    return '/strategy'
  }

  /**
   * Get strategy display name
   */
  function getStrategyName(strategyKey) {
    const strategy = availableStrategies.value.find(s => s.key === strategyKey)
    return strategy?.name || strategyKey
  }

  /**
   * Reset store state
   */
  function reset() {
    stopAutoRefresh()
    underlying.value = 'NIFTY'
    expiry.value = ''
    expiries.value = []
    selectedStrategies.value = []
    strikeRange.value = 10
    lots.value = 1
    results.value = {}
    spotPrice.value = 0
    atmStrike.value = 0
    lotSize.value = getLotSize('NIFTY')
    calculationTimeMs.value = 0
    totalCombinationsEvaluated.value = 0
    lastCalculated.value = null
    isLoading.value = false
    error.value = null
  }

  // =========================================================================
  // RETURN
  // =========================================================================

  return {
    // State
    underlying,
    expiry,
    expiries,
    selectedStrategies,
    strikeRange,
    lots,
    results,
    spotPrice,
    atmStrike,
    lotSize,
    calculationTimeMs,
    totalCombinationsEvaluated,
    lastCalculated,
    autoRefreshEnabled,
    autoRefreshInterval,
    isLoading,
    error,
    availableStrategies,

    // Getters
    selectedCount,
    hasResults,
    orderedResults,
    lastCalculatedFormatted,

    // Actions
    setUnderlying,
    fetchExpiries,
    toggleStrategy,
    isStrategySelected,
    selectAllStrategies,
    clearStrategies,
    calculate,
    startAutoRefresh,
    stopAutoRefresh,
    toggleAutoRefresh,
    setAutoRefreshInterval,
    openInStrategyBuilder,
    getStrategyName,
    reset
  }
})
