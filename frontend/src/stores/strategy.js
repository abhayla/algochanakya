import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'
import { fetchLegLTP as fetchLegLTPFromAPI } from '@/composables/usePriceFallback'
import { getLotSize, getIndexToken, getIndexSymbol } from '@/constants/trading'

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
  const lotSize = computed(() => getLotSize(underlying.value))

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

  // Can add row only if underlying is selected and expiries are loaded
  const canAddRow = computed(() => underlying.value && expiries.value.length > 0)

  // Helper function to generate temporary ID
  const generateTempId = () => `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  // Actions
  function setUnderlying(newUnderlying) {
    underlying.value = newUnderlying.toUpperCase()
    legs.value = []
    pnlGrid.value = null
    expiries.value = []
    strikes.value = {}
    currentSpot.value = 0
    fetchExpiries()
    fetchSpotPrice() // Fetch spot price for ATM calculation
  }

  async function fetchExpiries() {
    try {
      const response = await api.get(`/api/options/expiries?underlying=${underlying.value}`)
      expiries.value = response.data.expiries

      // Pre-fetch strikes for the first expiry so they're ready when user adds a row
      if (expiries.value.length > 0 && !strikes.value[expiries.value[0]]) {
        await fetchStrikes(expiries.value[0])
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch expiries'
      return { success: false, error: error.value }
    }
  }

  async function fetchStrikes(expiry) {
    try {
      const response = await api.get(`/api/options/strikes?underlying=${underlying.value}&expiry=${expiry}`)
      // Convert Decimal strings to numbers for consistent matching with leg.strike_price
      const normalizedStrikes = response.data.strikes.map(s => parseFloat(s))
      strikes.value[expiry] = normalizedStrikes
      return { success: true, data: normalizedStrikes }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch strikes'
      return { success: false, error: error.value }
    }
  }

  // Fetch spot price for the current underlying
  async function fetchSpotPrice() {
    try {
      const symbol = getIndexSymbol(underlying.value)
      if (!symbol) return { success: false }

      const response = await api.get('/api/orders/ltp', {
        params: { instruments: symbol }
      })

      if (response.data && response.data[symbol]) {
        currentSpot.value = response.data[symbol].last_price
        return { success: true, spot: currentSpot.value }
      }
      return { success: false }
    } catch (err) {
      console.error('Failed to fetch spot price:', err)
      return { success: false }
    }
  }

  // Find the nearest strike to the spot price
  function findNearestStrike(spot, strikesArray) {
    if (!spot || !strikesArray?.length) return null
    return strikesArray.reduce((prev, curr) =>
      Math.abs(curr - spot) < Math.abs(prev - spot) ? curr : prev
    )
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
      // Return full instrument data including tradingsymbol for LTP fetching
      return {
        instrument_token: response.data.instrument_token,
        tradingsymbol: response.data.tradingsymbol
      }
    } catch (err) {
      console.error('Failed to fetch instrument token:', err)
      return null
    }
  }

  async function addLeg(legData = null) {
    const defaultExpiry = expiries.value[0] || ''

    // Ensure strikes are loaded for the default expiry
    if (defaultExpiry && !strikes.value[defaultExpiry]) {
      await fetchStrikes(defaultExpiry)
    }

    // Calculate ATM strike if not provided
    let defaultStrike = null
    if (!legData?.strike_price && defaultExpiry && strikes.value[defaultExpiry]) {
      // If spot price is not yet loaded, try to fetch it
      if (currentSpot.value === 0) {
        await fetchSpotPrice()
      }

      if (currentSpot.value > 0) {
        defaultStrike = findNearestStrike(currentSpot.value, strikes.value[defaultExpiry])
      }
    }

    const newLeg = legData || {
      temp_id: generateTempId(),
      expiry_date: defaultExpiry,
      contract_type: 'PE',
      transaction_type: 'SELL',
      strike_price: defaultStrike,
      lots: 1,
      strategy_type: 'Naked Put',
      entry_price: null,
      exit_price: null,
      instrument_token: null,
      tradingsymbol: null,
    }
    legs.value.push(newLeg)

    // If we set a default strike, fetch instrument token
    if (defaultStrike && defaultExpiry) {
      const legIndex = legs.value.length - 1
      const data = await fetchInstrumentToken(defaultExpiry, defaultStrike, newLeg.contract_type)
      if (data) {
        legs.value[legIndex].instrument_token = data.instrument_token
        legs.value[legIndex].tradingsymbol = data.tradingsymbol
      }
    }

    // Auto-calculate P/L after adding leg
    calculatePnL()
  }

  function updateLeg(index, updates) {
    if (index >= 0 && index < legs.value.length) {
      // Auto-set position_status based on exit_price
      if ('exit_price' in updates) {
        updates.position_status = updates.exit_price ? 'closed' : 'open'
      }

      legs.value[index] = { ...legs.value[index], ...updates }

      // If expiry changed, fetch strikes for new expiry
      if (updates.expiry_date && !strikes.value[updates.expiry_date]) {
        fetchStrikes(updates.expiry_date)
      }

      // If strike, contract type, or expiry changed, update instrument token and tradingsymbol
      if (updates.strike_price !== undefined || updates.contract_type !== undefined || updates.expiry_date !== undefined) {
        const leg = legs.value[index]
        if (leg.expiry_date && leg.strike_price && leg.contract_type) {
          fetchInstrumentToken(leg.expiry_date, leg.strike_price, leg.contract_type)
            .then(data => {
              if (data) {
                legs.value[index].instrument_token = data.instrument_token
                legs.value[index].tradingsymbol = data.tradingsymbol
              }
              // Auto-calculate P/L after token update
              calculatePnL()
            })
        }
      } else {
        // Auto-calculate P/L for other field changes
        calculatePnL()
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

      // Auto-calculate P/L after removing leg
      calculatePnL()
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

    // Auto-calculate P/L after removing selected legs
    calculatePnL()
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

    // Validate legs have required data (entry_price no longer required - use CMP as fallback)
    const validLegs = legs.value.filter(leg =>
      leg.strike_price && leg.expiry_date && leg.instrument_token
    )

    if (validLegs.length === 0) {
      return { success: false, error: 'Legs must have strike price and instrument token' }
    }

    // Fetch LTP from API for legs without WebSocket CMP (as fallback)
    for (const leg of validLegs) {
      if (!getLegCMP(leg) && leg.tradingsymbol) {
        await fetchLegLTP(leg)  // Updates livePrices with LTP from API
      }
    }

    // Build legs with CMP/LTP fallback for missing entry prices
    const legsWithEntry = validLegs.map(leg => {
      const cmp = getLegCMP(leg)  // Now includes API-fetched LTP
      const effectiveEntry = leg.entry_price || cmp
      return {
        ...leg,
        effective_entry: effectiveEntry
      }
    }).filter(leg => leg.effective_entry != null)  // Still need SOME entry value

    if (legsWithEntry.length === 0) {
      return { success: false, error: 'No valid entry prices or CMP available for calculation' }
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/strategies/calculate', {
        underlying: underlying.value,
        legs: legsWithEntry.map(leg => ({
          strike: parseFloat(leg.strike_price),
          contract_type: leg.contract_type,
          transaction_type: leg.transaction_type,
          lots: leg.lots,
          lot_size: lotSize.value,
          entry_price: parseFloat(leg.effective_entry),
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

      // Fetch strikes for ALL unique expiry dates from loaded legs
      const uniqueExpiries = [...new Set(
        legs.value.map(leg => leg.expiry_date).filter(exp => exp != null)
      )]
      await Promise.all(
        uniqueExpiries.map(expiry =>
          !strikes.value[expiry] ? fetchStrikes(expiry) : Promise.resolve()
        )
      )

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

      // Fetch strikes for ALL unique expiry dates from loaded legs
      const uniqueExpiries = [...new Set(
        legs.value.map(leg => leg.expiry_date).filter(exp => exp != null)
      )]
      await Promise.all(
        uniqueExpiries.map(expiry =>
          !strikes.value[expiry] ? fetchStrikes(expiry) : Promise.resolve()
        )
      )

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

      // Fetch strikes for ALL unique expiry dates from imported legs
      const uniqueExpiries = [...new Set(
        response.data.legs.map(leg => leg.expiry_date).filter(exp => exp != null)
      )]
      await Promise.all(
        uniqueExpiries.map(expiry =>
          !strikes.value[expiry] ? fetchStrikes(expiry) : Promise.resolve()
        )
      )

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

  // Check if leg is using CMP as entry price (for UI indicator)
  function isLegUsingCMPEntry(leg) {
    return !leg.entry_price && getLegCMP(leg) != null
  }

  function getLegPnL(leg) {
    const cmp = getLegCMP(leg)
    if (cmp === null) return null

    // Use entry_price if available, otherwise use CMP as entry (Exit P/L = 0 when using CMP)
    const entryPrice = leg.entry_price || cmp
    const qty = leg.lots * lotSize.value
    const multiplier = leg.transaction_type === 'BUY' ? 1 : -1
    return (cmp - parseFloat(entryPrice)) * qty * multiplier
  }

  // Get leg tokens for WebSocket subscription
  function getLegTokens() {
    return legs.value
      .map(leg => leg.instrument_token)
      .filter(token => token != null)
  }

  // Calculate Exit P/L for a leg based on CMP
  function getLegExitPnL(leg) {
    const cmp = getLegCMP(leg)
    if (cmp === null) return null

    // Use entry_price if available, otherwise use CMP as entry (Exit P/L = 0 when using CMP)
    const entryPrice = leg.entry_price || cmp
    const qty = leg.lots * lotSize.value
    const multiplier = leg.transaction_type === 'BUY' ? 1 : -1
    return (cmp - parseFloat(entryPrice)) * qty * multiplier
  }

  // Fetch LTP from Kite API as fallback when WebSocket unavailable
  async function fetchLegLTP(leg) {
    if (!leg.instrument_token || !leg.tradingsymbol) return

    // Skip if we already have live price for this token
    if (livePrices.value[leg.instrument_token]?.ltp) return

    await fetchLegLTPFromAPI(leg, (token, tick) => {
      livePrices.value[token] = tick
    })
  }

  // Add leg from Option Chain
  function addLegFromOptionChain(leg) {
    const newLeg = {
      temp_id: generateTempId(),
      expiry_date: leg.expiry_date,
      contract_type: leg.contract_type,
      transaction_type: 'SELL', // Default to SELL
      strike_price: leg.strike_price,
      lots: 1,
      strategy_type: 'Custom',
      entry_price: leg.entry_price,
      exit_price: null,
      instrument_token: leg.instrument_token,
      tradingsymbol: leg.tradingsymbol || null
    }
    legs.value.push(newLeg)

    // Fetch strikes for the expiry if not already fetched
    if (leg.expiry_date && !strikes.value[leg.expiry_date]) {
      fetchStrikes(leg.expiry_date)
    }

    // Auto-calculate P/L after adding leg from Option Chain
    calculatePnL()
  }

  // Add leg from OFO (Options For Options)
  function addLegFromOFO(leg) {
    const newLeg = {
      temp_id: generateTempId(),
      expiry_date: leg.expiry_date,
      contract_type: leg.contract_type,
      transaction_type: leg.transaction_type,
      strike_price: leg.strike_price,
      lots: leg.lots || 1,
      strategy_type: 'Custom',
      entry_price: leg.entry_price,
      exit_price: null,
      instrument_token: leg.instrument_token,
      tradingsymbol: leg.tradingsymbol || null
    }
    legs.value.push(newLeg)

    // Fetch strikes for the expiry if not already fetched
    if (leg.expiry_date && !strikes.value[leg.expiry_date]) {
      fetchStrikes(leg.expiry_date)
    }
  }

  // Clear legs only (keep strategy settings)
  function clearLegs() {
    legs.value = []
    pnlGrid.value = null
    selectedLegIndices.value = []
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

  // Validation functions
  function validateStrategy() {
    const errors = []

    // Check name
    if (!currentStrategy.value?.name?.trim()) {
      errors.push('Strategy name is required')
    }

    // Check underlying
    if (!underlying.value) {
      errors.push('Underlying is required')
    }

    // Check legs
    if (legs.value.length === 0) {
      errors.push('At least one leg is required')
    }

    // Check each leg has all required fields
    legs.value.forEach((leg, index) => {
      const missingFields = []
      if (!leg.strike_price) missingFields.push('strike')
      if (!leg.expiry_date) missingFields.push('expiry')
      if (!leg.option_type && !leg.contract_type) missingFields.push('option type')
      if (!leg.transaction_type) missingFields.push('buy/sell')
      if (!leg.lots) missingFields.push('lots')

      if (missingFields.length > 0) {
        errors.push(`Leg ${index + 1} is missing: ${missingFields.join(', ')}`)
      }
    })

    return errors
  }

  async function checkDuplicateName(name, excludeStrategyId = null) {
    try {
      const params = { name }
      if (excludeStrategyId) {
        params.strategy_id = excludeStrategyId
      }
      const response = await api.get('/api/strategies/check-name', { params })
      return response.data.exists
    } catch (err) {
      console.error('Failed to check duplicate name:', err)
      return false
    }
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
    canAddRow,

    // Actions
    setUnderlying,
    fetchExpiries,
    fetchStrikes,
    fetchSpotPrice,
    findNearestStrike,
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
    getLegTokens,
    getLegExitPnL,
    isLegUsingCMPEntry,
    fetchLegLTP,
    addLegFromOptionChain,
    addLegFromOFO,
    clearLegs,
    clearStrategy,
    reset,
    validateStrategy,
    checkDuplicateName,
  }
})
