import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'

export const useStrategyStore = defineStore('strategy', () => {
  // State
  const strategies = ref([])
  const currentStrategy = ref(null)
  const legs = ref([])
  const underlying = ref('NIFTY')

  // Options data
  const expiries = ref([])
  const strikes = ref({}) // expiry -> strikes array
  const optionChain = ref({})

  // P/L calculation
  const pnlMode = ref('expiry') // 'expiry' or 'current'
  const targetDate = ref(null)
  const pnlGrid = ref(null)
  const spotPrices = ref([])
  const currentSpot = ref(0)

  // Live prices
  const livePrices = ref({}) // token -> { ltp, change, change_percent }

  // Lot sizes
  const lotSizes = {
    'NIFTY': 75,
    'BANKNIFTY': 15,
    'FINNIFTY': 25
  }

  // Strategy types
  const strategyTypes = [
    'Naked Put',
    'Naked Call',
    'Butterfly',
    'Calendar Spread',
    'Iron Condor',
    'Straddle',
    'Strangle',
    'Spread',
    'Ratio Spread',
    'Synthetic Future',
    'Custom'
  ]

  // UI state
  const isLoading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)
  const selectedLegIndices = ref([])

  // Getters
  const lotSize = computed(() => lotSizes[underlying.value] || 75)

  const totalQty = computed(() => {
    return legs.value.reduce((sum, leg) => {
      return sum + (leg.lots * lotSize.value)
    }, 0)
  })

  const selectedStrikes = computed(() => {
    const uniqueStrikes = [...new Set(
      legs.value
        .filter(leg => leg.strike_price)
        .map(leg => parseFloat(leg.strike_price))
    )]
    return uniqueStrikes.sort((a, b) => a - b)
  })

  const pnlColumns = computed(() => {
    if (!pnlGrid.value) return []
    return pnlGrid.value.spot_prices
  })

  const maxProfit = computed(() => pnlGrid.value?.max_profit || 0)
  const maxLoss = computed(() => pnlGrid.value?.max_loss || 0)
  const breakevens = computed(() => pnlGrid.value?.breakeven || [])

  // Helper function to generate temporary ID
  const generateTempId = () => `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  // Actions
  function setUnderlying(newUnderlying) {
    underlying.value = newUnderlying.toUpperCase()
    legs.value = []
    pnlGrid.value = null
    expiries.value = []
    strikes.value = {}
    fetchExpiries()
  }

  async function fetchExpiries() {
    try {
      const response = await api.get(`/api/options/expiries?underlying=${underlying.value}`)
      expiries.value = response.data.expiries
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch expiries'
      return { success: false, error: error.value }
    }
  }

  async function fetchStrikes(expiry) {
    try {
      const response = await api.get(`/api/options/strikes?underlying=${underlying.value}&expiry=${expiry}`)
      strikes.value[expiry] = response.data.strikes
      return { success: true, data: response.data.strikes }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch strikes'
      return { success: false, error: error.value }
    }
  }

  async function fetchInstrumentToken(expiry, strike, contractType) {
    try {
      const response = await api.get('/api/options/instrument', {
        params: {
          underlying: underlying.value,
          expiry,
          strike,
          contract_type: contractType
        }
      })
      return response.data.instrument_token
    } catch (err) {
      console.error('Failed to fetch instrument token:', err)
      return null
    }
  }

  function addLeg(legData = null) {
    const defaultExpiry = expiries.value[0] || ''
    const newLeg = legData || {
      temp_id: generateTempId(),
      expiry_date: defaultExpiry,
      contract_type: 'PE',
      transaction_type: 'SELL',
      strike_price: null,
      lots: 1,
      strategy_type: 'Naked Put',
      entry_price: null,
      exit_price: null,
      instrument_token: null,
    }
    legs.value.push(newLeg)

    // Fetch strikes for the expiry if not already fetched
    if (defaultExpiry && !strikes.value[defaultExpiry]) {
      fetchStrikes(defaultExpiry)
    }
  }

  function updateLeg(index, updates) {
    if (index >= 0 && index < legs.value.length) {
      legs.value[index] = { ...legs.value[index], ...updates }

      // If expiry changed, fetch strikes for new expiry
      if (updates.expiry_date && !strikes.value[updates.expiry_date]) {
        fetchStrikes(updates.expiry_date)
      }

      // If strike or contract type changed, update instrument token
      if (updates.strike_price !== undefined || updates.contract_type !== undefined) {
        const leg = legs.value[index]
        if (leg.expiry_date && leg.strike_price && leg.contract_type) {
          fetchInstrumentToken(leg.expiry_date, leg.strike_price, leg.contract_type)
            .then(token => {
              if (token) {
                legs.value[index].instrument_token = token
              }
            })
        }
      }
    }
  }

  function removeLeg(index) {
    if (index >= 0 && index < legs.value.length) {
      legs.value.splice(index, 1)
      // Update selected indices
      selectedLegIndices.value = selectedLegIndices.value
        .filter(i => i !== index)
        .map(i => i > index ? i - 1 : i)
    }
  }

  function removeSelectedLegs() {
    if (selectedLegIndices.value.length === 0) return

    // Sort in reverse order to remove from end first
    const indicesToRemove = [...selectedLegIndices.value].sort((a, b) => b - a)
    indicesToRemove.forEach(index => {
      legs.value.splice(index, 1)
    })
    selectedLegIndices.value = []
  }

  function toggleLegSelection(index) {
    const idx = selectedLegIndices.value.indexOf(index)
    if (idx === -1) {
      selectedLegIndices.value.push(index)
    } else {
      selectedLegIndices.value.splice(idx, 1)
    }
  }

  function selectAllLegs() {
    selectedLegIndices.value = legs.value.map((_, i) => i)
  }

  function deselectAllLegs() {
    selectedLegIndices.value = []
  }

  async function calculatePnL() {
    if (legs.value.length === 0) {
      pnlGrid.value = null
      return { success: false, error: 'No legs to calculate' }
    }

    // Validate legs have required data
    const validLegs = legs.value.filter(leg =>
      leg.strike_price && leg.entry_price && leg.expiry_date
    )

    if (validLegs.length === 0) {
      return { success: false, error: 'Legs must have strike price and entry price' }
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/strategies/calculate', {
        underlying: underlying.value,
        legs: validLegs.map(leg => ({
          strike: parseFloat(leg.strike_price),
          contract_type: leg.contract_type,
          transaction_type: leg.transaction_type,
          lots: leg.lots,
          lot_size: lotSize.value,
          entry_price: parseFloat(leg.entry_price),
          expiry_date: leg.expiry_date,
        })),
        mode: pnlMode.value,
        target_date: targetDate.value,
      })

      pnlGrid.value = response.data
      spotPrices.value = response.data.spot_prices
      currentSpot.value = response.data.current_spot
      lastUpdated.value = new Date()

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'P/L calculation failed'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  function togglePnLMode() {
    pnlMode.value = pnlMode.value === 'expiry' ? 'current' : 'expiry'
    if (legs.value.length > 0) {
      calculatePnL()
    }
  }

  function setTargetDate(date) {
    targetDate.value = date
    if (pnlMode.value === 'current' && legs.value.length > 0) {
      calculatePnL()
    }
  }

  // Strategy CRUD
  async function fetchStrategies(filters = {}) {
    isLoading.value = true
    try {
      const params = new URLSearchParams()
      if (filters.status) params.append('status', filters.status)
      if (filters.underlying) params.append('underlying', filters.underlying)

      const response = await api.get(`/api/strategies?${params.toString()}`)
      strategies.value = response.data
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch strategies'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function saveStrategy(name) {
    isLoading.value = true
    try {
      const response = await api.post('/api/strategies', {
        name,
        underlying: underlying.value,
        legs: legs.value.map(leg => ({
          expiry_date: leg.expiry_date,
          contract_type: leg.contract_type,
          transaction_type: leg.transaction_type,
          strike_price: leg.strike_price ? parseFloat(leg.strike_price) : null,
          lots: leg.lots,
          strategy_type: leg.strategy_type,
          entry_price: leg.entry_price ? parseFloat(leg.entry_price) : null,
          exit_price: leg.exit_price ? parseFloat(leg.exit_price) : null,
          instrument_token: leg.instrument_token,
        })),
      })
      currentStrategy.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to save strategy'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function loadStrategy(id) {
    isLoading.value = true
    try {
      const response = await api.get(`/api/strategies/${id}`)
      currentStrategy.value = response.data
      underlying.value = response.data.underlying
      legs.value = response.data.legs.map(leg => ({
        ...leg,
        temp_id: leg.id,
        strike_price: leg.strike_price ? parseFloat(leg.strike_price) : null,
        entry_price: leg.entry_price ? parseFloat(leg.entry_price) : null,
        exit_price: leg.exit_price ? parseFloat(leg.exit_price) : null,
      }))

      // Fetch expiries and calculate P/L
      await fetchExpiries()
      await calculatePnL()

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to load strategy'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function updateStrategy(id, data) {
    try {
      const response = await api.put(`/api/strategies/${id}`, data)
      currentStrategy.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update strategy'
      return { success: false, error: error.value }
    }
  }

  async function deleteStrategy(id) {
    try {
      await api.delete(`/api/strategies/${id}`)
      strategies.value = strategies.value.filter(s => s.id !== id)
      if (currentStrategy.value?.id === id) {
        currentStrategy.value = null
        legs.value = []
      }
      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete strategy'
      return { success: false, error: error.value }
    }
  }

  // Sharing
  async function shareStrategy(id) {
    try {
      const strategyId = id || currentStrategy.value?.id
      if (!strategyId) {
        return { success: false, error: 'No strategy to share' }
      }

      const response = await api.post(`/api/strategies/${strategyId}/share`)
      return {
        success: true,
        shareCode: response.data.share_code,
        shareUrl: response.data.share_url
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to share strategy'
      return { success: false, error: error.value }
    }
  }

  async function loadSharedStrategy(shareCode) {
    isLoading.value = true
    try {
      const response = await api.get(`/api/strategies/shared/${shareCode}`)
      currentStrategy.value = response.data
      underlying.value = response.data.underlying
      legs.value = response.data.legs.map(leg => ({
        ...leg,
        temp_id: leg.id,
        strike_price: leg.strike_price ? parseFloat(leg.strike_price) : null,
        entry_price: leg.entry_price ? parseFloat(leg.entry_price) : null,
        exit_price: leg.exit_price ? parseFloat(leg.exit_price) : null,
      }))

      await fetchExpiries()
      await calculatePnL()

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to load shared strategy'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  // Orders
  async function placeBasketOrder() {
    if (legs.value.length === 0) {
      return { success: false, error: 'No legs to order' }
    }

    // Validate all legs have instrument tokens
    const invalidLegs = legs.value.filter(leg => !leg.instrument_token)
    if (invalidLegs.length > 0) {
      return { success: false, error: 'Some legs are missing instrument tokens' }
    }

    isLoading.value = true
    try {
      const response = await api.post('/api/orders/basket', {
        strategy_id: currentStrategy.value?.id,
        legs: legs.value.map(leg => ({
          instrument_token: leg.instrument_token,
          transaction_type: leg.transaction_type,
          quantity: leg.lots * lotSize.value,
          price: leg.entry_price ? parseFloat(leg.entry_price) : null,
          order_type: leg.entry_price ? 'LIMIT' : 'MARKET',
        })),
      })

      return { success: response.data.success, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to place basket order'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function importPositions() {
    isLoading.value = true
    try {
      const response = await api.post(`/api/orders/import-positions?underlying=${underlying.value}`)

      // Add imported legs
      response.data.legs.forEach(leg => {
        legs.value.push({
          temp_id: generateTempId(),
          expiry_date: leg.expiry_date,
          contract_type: leg.contract_type,
          transaction_type: leg.transaction_type,
          strike_price: leg.strike_price ? parseFloat(leg.strike_price) : null,
          lots: leg.lots,
          entry_price: leg.entry_price ? parseFloat(leg.entry_price) : null,
          instrument_token: leg.instrument_token,
          strategy_type: 'Imported',
        })
      })

      await calculatePnL()

      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to import positions'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function updateFromPositions() {
    try {
      const response = await api.get(`/api/orders/positions?underlying=${underlying.value}`)
      // Update legs with current position data
      // This could update prices, quantities etc.
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update positions'
      return { success: false, error: error.value }
    }
  }

  // Live prices
  function updateLivePrices(prices) {
    prices.forEach(p => {
      livePrices.value[p.token] = {
        ltp: p.ltp,
        change: p.change,
        change_percent: p.change_percent,
      }
    })
  }

  function getLegCMP(leg) {
    if (!leg.instrument_token) return null
    return livePrices.value[leg.instrument_token]?.ltp || null
  }

  function getLegPnL(leg) {
    const cmp = getLegCMP(leg)
    if (cmp === null || !leg.entry_price) return null

    const qty = leg.lots * lotSize.value
    const multiplier = leg.transaction_type === 'BUY' ? 1 : -1
    return (cmp - parseFloat(leg.entry_price)) * qty * multiplier
  }

  // Clear / Reset
  function clearStrategy() {
    currentStrategy.value = null
    legs.value = []
    pnlGrid.value = null
    selectedLegIndices.value = []
    error.value = null
  }

  function reset() {
    strategies.value = []
    currentStrategy.value = null
    legs.value = []
    underlying.value = 'NIFTY'
    expiries.value = []
    strikes.value = {}
    pnlMode.value = 'expiry'
    targetDate.value = null
    pnlGrid.value = null
    spotPrices.value = []
    currentSpot.value = 0
    livePrices.value = {}
    isLoading.value = false
    error.value = null
    lastUpdated.value = null
    selectedLegIndices.value = []
  }

  return {
    // State
    strategies,
    currentStrategy,
    legs,
    underlying,
    expiries,
    strikes,
    optionChain,
    pnlMode,
    targetDate,
    pnlGrid,
    spotPrices,
    currentSpot,
    livePrices,
    lotSizes,
    strategyTypes,
    isLoading,
    error,
    lastUpdated,
    selectedLegIndices,

    // Getters
    lotSize,
    totalQty,
    selectedStrikes,
    pnlColumns,
    maxProfit,
    maxLoss,
    breakevens,

    // Actions
    setUnderlying,
    fetchExpiries,
    fetchStrikes,
    fetchInstrumentToken,
    addLeg,
    updateLeg,
    removeLeg,
    removeSelectedLegs,
    toggleLegSelection,
    selectAllLegs,
    deselectAllLegs,
    calculatePnL,
    togglePnLMode,
    setTargetDate,
    fetchStrategies,
    saveStrategy,
    loadStrategy,
    updateStrategy,
    deleteStrategy,
    shareStrategy,
    loadSharedStrategy,
    placeBasketOrder,
    importPositions,
    updateFromPositions,
    updateLivePrices,
    getLegCMP,
    getLegPnL,
    clearStrategy,
    reset,
  }
})
