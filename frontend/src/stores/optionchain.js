import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'
import { getLotSize, getIndexToken as getIndexTokenFromConstants } from '@/constants/trading'
import { useUserPreferencesStore } from './userPreferences'

export const useOptionChainStore = defineStore('optionchain', () => {
  // State
  const underlying = ref('NIFTY')
  const expiry = ref('')
  const expiries = ref([])
  const spotPrice = ref(0)
  const daysToExpiry = computed(() => {
    if (!expiry.value) return 0
    try {
      const expiryDate = new Date(expiry.value)
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const diff = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24))
      return Math.max(0, diff)
    } catch {
      return 0
    }
  })
  const lotSize = ref(getLotSize('NIFTY'))
  const chain = ref([])
  const dataFreshness = ref('LIVE')  // 'LIVE' | 'LAST_KNOWN'
  const summary = ref({
    total_ce_oi: 0,
    total_pe_oi: 0,
    pcr: 0,
    max_pain: 0,
    atm_strike: 0
  })

  const isLoading = ref(false)
  const error = ref(null)

  // Live prices from WebSocket (token -> tick data)
  const livePrices = ref({})
  const isLiveUpdatesEnabled = ref(true)

  // Display settings
  const showGreeks = ref(true)  // Finding #6: Greeks ON by default for options traders
  const showVolume = ref(true)
  const strikesRange = ref(10) // Finding #5: Default to 10 strikes above/below ATM (20 total)
  const localGridInterval = ref(null) // null = use user preference from Settings

  // Selected for strategy
  const selectedStrikes = ref([])

  // Strike Finder state
  const strikeFinder = ref({
    visible: false,
    mode: 'delta', // 'delta' or 'premium'
    optionType: 'CE',
    targetDelta: null,
    targetPremium: null,
    result: null,
    loading: false,
    error: null
  })

  // Lot sizes
  // Lot sizes now from centralized constants

  // Getters

  // Effective grid interval (local override or user preference)
  const effectiveGridInterval = computed(() => {
    if (localGridInterval.value !== null) {
      return localGridInterval.value
    }
    const userPrefsStore = useUserPreferencesStore()
    return userPrefsStore.pnlGridInterval
  })

  // Check if underlying has 50-point strikes (to show/hide toggle)
  const has50PointStrikes = computed(() => {
    if (chain.value.length < 2) return false
    const nativeStep = Math.abs(chain.value[1].strike - chain.value[0].strike)
    return nativeStep <= 50
  })

  const filteredChain = computed(() => {
    if (!chain.value.length) return []

    // Find ATM row
    const atmRow = chain.value.find(row => row.is_atm)
    const atmIdx = chain.value.findIndex(row => row.is_atm)
    if (atmIdx === -1) return chain.value

    // Get effective grid interval (local override or user preference)
    const gridInterval = effectiveGridInterval.value // 50 or 100

    // Detect native step from actual data (backend returns all strikes from Zerodha)
    // NIFTY has 50-point strikes, BANKNIFTY has 100-point strikes in Zerodha's data
    let nativeStep = 50 // Default fallback
    if (chain.value.length >= 2) {
      nativeStep = Math.abs(chain.value[1].strike - chain.value[0].strike)
    }

    // Calculate skip factor: if user wants 100 interval but native is 50, skip every other strike
    const skipFactor = Math.max(1, Math.floor(gridInterval / nativeStep))

    // If range is 50 or more, show all (but still respect interval)
    if (strikesRange.value >= 50) {
      if (skipFactor > 1) {
        // Filter to show strikes at 100-point boundaries (divisible by gridInterval)
        // BUT always include the ATM strike even if it's not aligned
        return chain.value.filter(row => row.is_atm || row.strike % gridInterval === 0)
      }
      return chain.value
    }

    // Filter around ATM with interval consideration
    let strikes = []

    if (skipFactor > 1) {
      // Filter strikes that are at 100-point boundaries (divisible by gridInterval)
      // BUT always include the ATM strike even if it's not aligned
      const alignedStrikes = chain.value.filter(row => row.is_atm || row.strike % gridInterval === 0)

      // Find ATM index in filtered list
      const alignedAtmIdx = alignedStrikes.findIndex(row => row.is_atm)

      if (alignedAtmIdx === -1) {
        // Fallback: if no ATM found, use center of aligned strikes
        const centerIdx = Math.floor(alignedStrikes.length / 2)
        const start = Math.max(0, centerIdx - strikesRange.value)
        const end = Math.min(alignedStrikes.length, centerIdx + strikesRange.value + 1)
        strikes = alignedStrikes.slice(start, end)
      } else {
        // Get strikesRange strikes on each side of ATM
        const start = Math.max(0, alignedAtmIdx - strikesRange.value)
        const end = Math.min(alignedStrikes.length, alignedAtmIdx + strikesRange.value + 1)
        strikes = alignedStrikes.slice(start, end)
      }
    } else {
      // Show all strikes within range (no skip needed)
      const start = Math.max(0, atmIdx - strikesRange.value)
      const end = Math.min(chain.value.length, atmIdx + strikesRange.value + 1)
      strikes = chain.value.slice(start, end)
    }

    return strikes
  })

  const atmStrike = computed(() => {
    return summary.value.atm_strike || Math.round(spotPrice.value / 50) * 50
  })

  const maxCEOI = computed(() => {
    return Math.max(...chain.value.map(r => r.ce?.oi || 0), 1)
  })

  const maxPEOI = computed(() => {
    return Math.max(...chain.value.map(r => r.pe?.oi || 0), 1)
  })

  // Get live LTP for an option (token-based lookup)
  function getLiveLTP(token) {
    if (!token || !isLiveUpdatesEnabled.value) return null
    return livePrices.value[token]?.ltp || null
  }

  // Get live change for an option
  function getLiveChange(token) {
    if (!token || !isLiveUpdatesEnabled.value) return null
    return livePrices.value[token]?.change || null
  }

  // Get live change percent for an option
  function getLiveChangePercent(token) {
    if (!token || !isLiveUpdatesEnabled.value) return null
    return livePrices.value[token]?.change_percent || null
  }

  // Get current index token for underlying
  function getIndexToken() {
    return getIndexTokenFromConstants(underlying.value) || getIndexTokenFromConstants('NIFTY')
  }

  // Get all option tokens from the chain for WebSocket subscription
  function getAllOptionTokens() {
    const tokens = []
    for (const row of chain.value) {
      if (row.ce?.instrument_token) tokens.push(row.ce.instrument_token)
      if (row.pe?.instrument_token) tokens.push(row.pe.instrument_token)
    }
    return tokens
  }

  // Actions
  async function setUnderlying(ul) {
    underlying.value = ul.toUpperCase()
    lotSize.value = getLotSize(underlying.value)
    expiry.value = '' // Reset expiry when underlying changes
    error.value = null // Clear previous error when switching underlying
    chain.value = []
    summary.value = {
      total_ce_oi: 0,
      total_pe_oi: 0,
      pcr: 0,
      max_pain: 0,
      atm_strike: 0
    }
    await fetchExpiries()
  }

  async function fetchExpiries() {
    try {
      const response = await api.get('/api/options/expiries', {
        params: { underlying: underlying.value }
      })
      expiries.value = response.data.expiries || []

      // Auto-select first expiry if available
      if (expiries.value.length > 0 && !expiry.value) {
        expiry.value = expiries.value[0]
      }

      return { success: true }
    } catch (err) {
      console.error('Error fetching expiries:', err)
      error.value = err.response?.data?.detail || 'Failed to fetch expiries'
      return { success: false, error: error.value }
    }
  }

  async function fetchOptionChain() {
    if (!expiry.value) {
      return { success: false, error: 'No expiry selected' }
    }

    isLoading.value = true
    error.value = null
    chain.value = []
    summary.value = { total_ce_oi: 0, total_pe_oi: 0, pcr: 0, max_pain: 0, atm_strike: 0 }

    try {
      const response = await api.get('/api/optionchain/chain', {
        params: {
          underlying: underlying.value,
          expiry: expiry.value
        },
        timeout: 30000  // Chain can be slow on cold start; override global 10s default
      })

      spotPrice.value = response.data.spot_price
      lotSize.value = response.data.lot_size
      chain.value = response.data.chain
      summary.value = response.data.summary
      dataFreshness.value = response.data.data_freshness || 'LIVE'

      return { success: true }
    } catch (err) {
      console.error('Error fetching option chain:', err)
      error.value = err.response?.data?.detail || 'Failed to load option chain'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  function toggleStrikeSelection(strike, type) {
    const key = `${strike}-${type}`
    const index = selectedStrikes.value.findIndex(s => s.key === key)

    if (index > -1) {
      selectedStrikes.value.splice(index, 1)
    } else {
      const row = chain.value.find(r => r.strike === strike)
      const data = type === 'CE' ? row.ce : row.pe

      if (data) {
        selectedStrikes.value.push({
          key,
          strike,
          type,
          ltp: data.ltp || 0,
          iv: data.iv || 0,
          instrument_token: data.instrument_token,
          tradingsymbol: data.tradingsymbol
        })
      }
    }
  }

  function isStrikeSelected(strike, type) {
    const key = `${strike}-${type}`
    return selectedStrikes.value.some(s => s.key === key)
  }

  function clearSelection() {
    selectedStrikes.value = []
  }

  function getAddToStrategyPayload() {
    return selectedStrikes.value.map(s => ({
      expiry_date: expiry.value,
      contract_type: s.type,
      strike_price: s.strike,
      entry_price: s.ltp,
      instrument_token: s.instrument_token,
      tradingsymbol: s.tradingsymbol
    }))
  }

  // OI bar width calculation (0-50px based on max OI)
  function getOIBarWidth(oi, type) {
    if (!oi) return 0
    const maxOI = type === 'ce' ? maxCEOI.value : maxPEOI.value
    return Math.round((oi / maxOI) * 50)
  }

  // Update live prices from WebSocket ticks
  function updateLivePrices(ticks) {
    if (!isLiveUpdatesEnabled.value) return

    // Update live prices map
    for (const tick of ticks) {
      livePrices.value[tick.token] = {
        ltp: tick.ltp,
        change: tick.change,
        change_percent: tick.change_percent
      }
    }

    // Update chain with live prices
    updateChainWithLivePrices()

    // Update spot price if index token is in ticks
    const indexToken = getIndexToken()
    const indexTick = ticks.find(t => t.token === indexToken)
    if (indexTick) {
      spotPrice.value = indexTick.ltp
    }
  }

  // Update chain array with live prices from livePrices map
  function updateChainWithLivePrices() {
    for (const row of chain.value) {
      // Update CE live price
      if (row.ce?.instrument_token) {
        const liveData = livePrices.value[row.ce.instrument_token]
        if (liveData) {
          row.ce.ltp = liveData.ltp
          row.ce.change = liveData.change
          row.ce.change_pct = liveData.change_percent
        }
      }
      // Update PE live price
      if (row.pe?.instrument_token) {
        const liveData = livePrices.value[row.pe.instrument_token]
        if (liveData) {
          row.pe.ltp = liveData.ltp
          row.pe.change = liveData.change
          row.pe.change_pct = liveData.change_percent
        }
      }
    }
  }

  // Toggle live updates on/off
  function toggleLiveUpdates() {
    isLiveUpdatesEnabled.value = !isLiveUpdatesEnabled.value
  }

  // Strike Finder methods
  function toggleStrikeFinder() {
    strikeFinder.value.visible = !strikeFinder.value.visible
    if (!strikeFinder.value.visible) {
      // Clear result when closing
      strikeFinder.value.result = null
      strikeFinder.value.error = null
    }
  }

  async function findStrikeByDelta(params) {
    strikeFinder.value.loading = true
    strikeFinder.value.error = null
    strikeFinder.value.result = null

    try {
      const response = await api.post('/api/optionchain/find-by-delta', {
        underlying: params.underlying,
        expiry: params.expiry,
        option_type: params.option_type,
        target_delta: params.target_delta,
        tolerance: params.tolerance || 0.02,
        prefer_round_strike: params.prefer_round_strike !== false
      })

      strikeFinder.value.result = response.data
      return response.data
    } catch (err) {
      console.error('Error finding strike by delta:', err)
      strikeFinder.value.error = err.response?.data?.detail || 'Failed to find strike'
      throw err
    } finally {
      strikeFinder.value.loading = false
    }
  }

  async function findStrikeByPremium(params) {
    strikeFinder.value.loading = true
    strikeFinder.value.error = null
    strikeFinder.value.result = null

    try {
      const response = await api.post('/api/optionchain/find-by-premium', {
        underlying: params.underlying,
        expiry: params.expiry,
        option_type: params.option_type,
        target_premium: params.target_premium,
        tolerance: params.tolerance || 10,
        prefer_round_strike: params.prefer_round_strike !== false
      })

      strikeFinder.value.result = response.data
      return response.data
    } catch (err) {
      console.error('Error finding strike by premium:', err)
      strikeFinder.value.error = err.response?.data?.detail || 'Failed to find strike'
      throw err
    } finally {
      strikeFinder.value.loading = false
    }
  }

  function clearStrikeFinderResult() {
    strikeFinder.value.result = null
    strikeFinder.value.error = null
  }

  function reset() {
    underlying.value = 'NIFTY'
    expiry.value = ''
    expiries.value = []
    spotPrice.value = 0
    lotSize.value = getLotSize('NIFTY')
    chain.value = []
    summary.value = {
      total_ce_oi: 0,
      total_pe_oi: 0,
      pcr: 0,
      max_pain: 0,
      atm_strike: 0
    }
    isLoading.value = false
    error.value = null
    selectedStrikes.value = []
    livePrices.value = {}
    isLiveUpdatesEnabled.value = true
  }

  // Set local grid interval (doesn't affect saved user preferences)
  function setLocalGridInterval(value) {
    localGridInterval.value = value
  }

  return {
    // State
    underlying,
    expiry,
    expiries,
    spotPrice,
    daysToExpiry,
    lotSize,
    chain,
    dataFreshness,
    summary,
    isLoading,
    error,
    showGreeks,
    showVolume,
    strikesRange,
    localGridInterval,
    selectedStrikes,
    getLotSize,
    livePrices,
    isLiveUpdatesEnabled,
    strikeFinder,

    // Getters
    filteredChain,
    atmStrike,
    maxCEOI,
    maxPEOI,
    effectiveGridInterval,
    has50PointStrikes,

    // Actions
    setUnderlying,
    fetchExpiries,
    fetchOptionChain,
    toggleStrikeSelection,
    isStrikeSelected,
    clearSelection,
    getAddToStrategyPayload,
    getOIBarWidth,
    reset,

    // Live price methods
    getLiveLTP,
    getLiveChange,
    getLiveChangePercent,
    getIndexToken,
    getAllOptionTokens,
    updateLivePrices,
    updateChainWithLivePrices,
    toggleLiveUpdates,

    // Strike Finder methods
    toggleStrikeFinder,
    findStrikeByDelta,
    findStrikeByPremium,
    clearStrikeFinderResult,

    // Grid interval methods
    setLocalGridInterval
  }
})
