/**
 * useOptionChain Composable - Phase 5D
 *
 * Manages option chain data fetching, strike finding, and filtering.
 * Provides reactive option chain state with Greeks and live prices.
 */
import { ref, computed, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import api from '@/services/api'

export function useOptionChain() {
  const autopilotStore = useAutopilotStore()

  // State
  const underlying = ref('NIFTY')
  const selectedExpiry = ref(null)
  const expiries = ref([])
  const optionChainData = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const useCache = ref(true)

  // Filters
  const filters = ref({
    showGreeks: true,
    strikeRange: 'all', // 'all', 'itm', 'atm', 'otm'
    numStrikes: 15, // Number of strikes to show around ATM
    sortBy: 'strike', // 'strike', 'oi', 'volume', 'iv'
    sortOrder: 'asc'
  })

  // Strike finder
  const strikeFinder = ref({
    mode: 'delta', // 'delta', 'premium', 'manual'
    optionType: 'PE',
    targetDelta: 0.15,
    targetPremium: 180,
    tolerance: 0.02,
    preferRoundStrikes: true,
    result: null,
    loading: false
  })

  /**
   * Fetch available expiries for underlying
   */
  const fetchExpiries = async () => {
    try {
      loading.value = true
      error.value = null

      const response = await api.get(`/api/v1/autopilot/option-chain/expiries/${underlying.value}`)

      if (response.data && response.data.expiries) {
        expiries.value = response.data.expiries

        // Auto-select first (nearest) expiry
        if (expiries.value.length > 0 && !selectedExpiry.value) {
          selectedExpiry.value = expiries.value[0]
        }
      }
    } catch (err) {
      console.error('Error fetching expiries:', err)
      error.value = err.response?.data?.message || 'Failed to fetch expiries'
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch option chain for selected underlying and expiry
   */
  const fetchOptionChain = async () => {
    if (!underlying.value || !selectedExpiry.value) {
      return
    }

    try {
      loading.value = true
      error.value = null

      const response = await api.get(
        `/api/v1/autopilot/option-chain/${underlying.value}/${selectedExpiry.value}`,
        { params: { use_cache: useCache.value } }
      )

      if (response.data) {
        optionChainData.value = response.data
      }
    } catch (err) {
      console.error('Error fetching option chain:', err)
      error.value = err.response?.data?.message || 'Failed to fetch option chain'
    } finally {
      loading.value = false
    }
  }

  /**
   * Find strike by delta
   * @param {Object} params - Optional parameters object (if not provided, uses internal state)
   */
  const findStrikeByDelta = async (params = null) => {
    const payload = params || {
      underlying: underlying.value,
      expiry: selectedExpiry.value,
      option_type: strikeFinder.value.optionType,
      target_delta: strikeFinder.value.targetDelta,
      tolerance: strikeFinder.value.tolerance,
      prefer_round_strike: strikeFinder.value.preferRoundStrikes
    }

    if (!payload.underlying || !payload.expiry) {
      return null
    }

    try {
      strikeFinder.value.loading = true
      strikeFinder.value.result = null

      const response = await api.post('/api/v1/autopilot/option-chain/find-by-delta', payload)

      if (response.data) {
        if (params) {
          // If called with params (from StrikeFinder component), return the data
          return response.data
        } else {
          // If called without params (internal use), update state
          strikeFinder.value.result = response.data
        }
      }
    } catch (err) {
      console.error('Error finding strike by delta:', err)
      error.value = err.response?.data?.message || 'Failed to find strike'
      throw err
    } finally {
      strikeFinder.value.loading = false
    }
  }

  /**
   * Find strike by premium
   * @param {Object} params - Optional parameters object (if not provided, uses internal state)
   */
  const findStrikeByPremium = async (params = null) => {
    const payload = params || {
      underlying: underlying.value,
      expiry: selectedExpiry.value,
      option_type: strikeFinder.value.optionType,
      target_premium: strikeFinder.value.targetPremium,
      tolerance: 10,
      prefer_round_strike: strikeFinder.value.preferRoundStrikes
    }

    if (!payload.underlying || !payload.expiry) {
      return null
    }

    try {
      strikeFinder.value.loading = true
      strikeFinder.value.result = null

      const response = await api.post('/api/v1/autopilot/option-chain/find-by-premium', payload)

      if (response.data) {
        if (params) {
          // If called with params (from StrikeFinder component), return the data
          return response.data
        } else {
          // If called without params (internal use), update state
          strikeFinder.value.result = response.data
        }
      }
    } catch (err) {
      console.error('Error finding strike by premium:', err)
      error.value = err.response?.data?.message || 'Failed to find strike'
      throw err
    } finally {
      strikeFinder.value.loading = false
    }
  }

  /**
   * Find ATM strike
   */
  const findATMStrike = async () => {
    if (!underlying.value || !selectedExpiry.value) {
      return null
    }

    try {
      const response = await api.get(
        `/api/v1/autopilot/option-chain/find-atm/${underlying.value}/${selectedExpiry.value}`
      )

      if (response.data && response.data.atm_strike) {
        return response.data.atm_strike
      }
    } catch (err) {
      console.error('Error finding ATM strike:', err)
    }

    return null
  }

  /**
   * Get strikes list
   */
  const fetchStrikesList = async () => {
    if (!underlying.value || !selectedExpiry.value) {
      return []
    }

    try {
      const response = await api.get(
        `/api/v1/autopilot/option-chain/${underlying.value}/${selectedExpiry.value}/strikes`
      )

      if (response.data && Array.isArray(response.data)) {
        return response.data
      }
    } catch (err) {
      console.error('Error fetching strikes:', err)
    }

    return []
  }

  /**
   * Filtered option chain data based on current filters
   */
  const filteredOptions = computed(() => {
    if (!optionChainData.value || !optionChainData.value.options) {
      return []
    }

    let options = [...optionChainData.value.options]

    // Filter by strike range
    if (filters.value.strikeRange !== 'all') {
      const spotPrice = optionChainData.value.spot_price
      const atmStrike = optionChainData.value.atm_strike || spotPrice

      if (filters.value.strikeRange === 'itm') {
        options = options.filter(opt => {
          const strike = opt.strike
          return (opt.option_type === 'CE' && strike < atmStrike) ||
                 (opt.option_type === 'PE' && strike > atmStrike)
        })
      } else if (filters.value.strikeRange === 'atm') {
        // Show strikes within ±5% of ATM
        const range = atmStrike * 0.05
        options = options.filter(opt =>
          Math.abs(opt.strike - atmStrike) <= range
        )
      } else if (filters.value.strikeRange === 'otm') {
        options = options.filter(opt => {
          const strike = opt.strike
          return (opt.option_type === 'CE' && strike > atmStrike) ||
                 (opt.option_type === 'PE' && strike < atmStrike)
        })
      }
    }

    // Limit number of strikes around ATM
    if (filters.value.numStrikes && filters.value.numStrikes > 0) {
      const atmStrike = optionChainData.value.atm_strike || optionChainData.value.spot_price

      // Sort by distance from ATM
      options.sort((a, b) => {
        return Math.abs(a.strike - atmStrike) - Math.abs(b.strike - atmStrike)
      })

      options = options.slice(0, filters.value.numStrikes)
    }

    // Sort by selected field
    if (filters.value.sortBy) {
      options.sort((a, b) => {
        const aVal = a[filters.value.sortBy] || 0
        const bVal = b[filters.value.sortBy] || 0

        if (filters.value.sortOrder === 'asc') {
          return aVal > bVal ? 1 : -1
        } else {
          return aVal < bVal ? 1 : -1
        }
      })
    }

    return options
  })

  /**
   * Grouped by strike for CE/PE mirrored display
   */
  const groupedByStrike = computed(() => {
    if (!filteredOptions.value || filteredOptions.value.length === 0) {
      return []
    }

    const strikes = new Map()

    filteredOptions.value.forEach(option => {
      if (!strikes.has(option.strike)) {
        strikes.set(option.strike, { strike: option.strike, CE: null, PE: null })
      }

      const row = strikes.get(option.strike)
      if (option.option_type === 'CE') {
        row.CE = option
      } else {
        row.PE = option
      }
    })

    return Array.from(strikes.values()).sort((a, b) => a.strike - b.strike)
  })

  /**
   * ATM strike from current data
   */
  const atmStrike = computed(() => {
    return optionChainData.value?.atm_strike || optionChainData.value?.spot_price || null
  })

  /**
   * Current spot price
   */
  const spotPrice = computed(() => {
    return optionChainData.value?.spot_price || null
  })

  /**
   * Is data cached
   */
  const isCached = computed(() => {
    return optionChainData.value?.cached || false
  })

  /**
   * Cached timestamp
   */
  const cachedAt = computed(() => {
    return optionChainData.value?.cached_at || null
  })

  /**
   * Refresh option chain (bypass cache)
   */
  const refreshOptionChain = async () => {
    const originalUseCache = useCache.value
    useCache.value = false
    await fetchOptionChain()
    useCache.value = originalUseCache
  }

  /**
   * Set underlying and fetch data
   */
  const setUnderlying = async (newUnderlying) => {
    underlying.value = newUnderlying
    selectedExpiry.value = null
    optionChainData.value = null
    await fetchExpiries()
  }

  /**
   * Set expiry and fetch option chain
   */
  const setExpiry = async (newExpiry) => {
    selectedExpiry.value = newExpiry
    await fetchOptionChain()
  }

  /**
   * Update filters
   */
  const updateFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  /**
   * Execute strike finder based on mode
   */
  const executeStrikeFinder = async () => {
    if (strikeFinder.value.mode === 'delta') {
      await findStrikeByDelta()
    } else if (strikeFinder.value.mode === 'premium') {
      await findStrikeByPremium()
    }
  }

  /**
   * Clear strike finder result
   */
  const clearStrikeFinderResult = () => {
    strikeFinder.value.result = null
  }

  // Watch for underlying/expiry changes
  watch(underlying, () => {
    fetchExpiries()
  })

  watch(selectedExpiry, () => {
    if (selectedExpiry.value) {
      fetchOptionChain()
    }
  })

  return {
    // State
    underlying,
    selectedExpiry,
    expiries,
    optionChainData,
    loading,
    error,
    useCache,
    filters,
    strikeFinder,

    // Computed
    filteredOptions,
    groupedByStrike,
    atmStrike,
    spotPrice,
    isCached,
    cachedAt,

    // Methods
    fetchExpiries,
    fetchOptionChain,
    refreshOptionChain,
    setUnderlying,
    setExpiry,
    updateFilters,
    findStrikeByDelta,
    findStrikeByPremium,
    findATMStrike,
    fetchStrikesList,
    executeStrikeFinder,
    clearStrikeFinderResult
  }
}
