/**
 * Option Chain Store — Comprehensive Unit Tests
 *
 * Covers: initial state, computed properties, actions (fetch, selection,
 * live prices, strike finder), reset, and error handling.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/constants/trading', () => ({
  getLotSize: vi.fn((ul) => {
    const sizes = { NIFTY: 75, BANKNIFTY: 35, FINNIFTY: 65, SENSEX: 20 }
    return sizes[(ul || 'NIFTY').toUpperCase()] ?? 75
  }),
  getIndexToken: vi.fn((ul) => {
    const tokens = { NIFTY: 256265, BANKNIFTY: 260105, FINNIFTY: 257801 }
    return tokens[(ul || 'NIFTY').toUpperCase()] || 256265
  }),
}))

vi.mock('@/stores/userPreferences', () => ({
  useUserPreferencesStore: () => ({ pnlGridInterval: 100 })
}))

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  }
}))

import api from '@/services/api'

// Test data
const MOCK_CHAIN = [
  { strike: 23900, is_atm: false, ce: { ltp: 250, oi: 50000, iv: 0.15, instrument_token: 1001, tradingsymbol: 'NIFTY23900CE' }, pe: { ltp: 10, oi: 30000, iv: 0.12, instrument_token: 2001 } },
  { strike: 23950, is_atm: false, ce: { ltp: 210, oi: 60000, iv: 0.14, instrument_token: 1002 }, pe: { ltp: 15, oi: 35000, iv: 0.13, instrument_token: 2002 } },
  { strike: 24000, is_atm: true,  ce: { ltp: 180, oi: 80000, iv: 0.13, instrument_token: 1003, tradingsymbol: 'NIFTY24000CE' }, pe: { ltp: 30, oi: 70000, iv: 0.14, instrument_token: 2003 } },
  { strike: 24050, is_atm: false, ce: { ltp: 140, oi: 40000, iv: 0.12, instrument_token: 1004 }, pe: { ltp: 50, oi: 45000, iv: 0.15, instrument_token: 2004 } },
  { strike: 24100, is_atm: false, ce: { ltp: 100, oi: 30000, iv: 0.11, instrument_token: 1005 }, pe: { ltp: 80, oi: 55000, iv: 0.16, instrument_token: 2005 } },
]

const MOCK_CHAIN_RESPONSE = {
  data: {
    spot_price: 24010,
    lot_size: 75,
    chain: MOCK_CHAIN,
    summary: { total_ce_oi: 260000, total_pe_oi: 235000, pcr: 0.9, max_pain: 24000, atm_strike: 24000 },
  }
}


describe('optionchain store — initial state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with NIFTY as default underlying', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()
    expect(store.underlying).toBe('NIFTY')
  })

  it('initializes with empty chain and summary', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()
    expect(store.chain).toEqual([])
    expect(store.summary.pcr).toBe(0)
    expect(store.summary.max_pain).toBe(0)
  })

  it('initializes with live updates enabled', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()
    expect(store.isLiveUpdatesEnabled).toBe(true)
  })

  it('initializes with Greeks shown by default', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()
    expect(store.showGreeks).toBe(true)
  })

  it('initializes with 10 strikes range', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()
    expect(store.strikesRange).toBe(10)
  })
})


describe('optionchain store — computed properties', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
  })

  it('daysToExpiry returns 0 when no expiry set', () => {
    expect(store.daysToExpiry).toBe(0)
  })

  it('daysToExpiry calculates correctly for future date', () => {
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + 5)
    store.expiry = futureDate.toISOString().split('T')[0]
    // Math.ceil rounds up partial days; result is 5 or 6 depending on time of day
    expect(store.daysToExpiry).toBeGreaterThanOrEqual(5)
    expect(store.daysToExpiry).toBeLessThanOrEqual(6)
  })

  it('daysToExpiry returns 0 for past date', () => {
    const pastDate = new Date()
    pastDate.setDate(pastDate.getDate() - 3)
    store.expiry = pastDate.toISOString().split('T')[0]
    expect(store.daysToExpiry).toBe(0)
  })

  it('atmStrike uses summary atm_strike when available', () => {
    store.summary = { ...store.summary, atm_strike: 24000 }
    expect(store.atmStrike).toBe(24000)
  })

  it('atmStrike falls back to rounded spot price', () => {
    store.spotPrice = 24035
    store.summary = { ...store.summary, atm_strike: 0 }
    expect(store.atmStrike).toBe(24050) // rounds to nearest 50
  })

  it('maxCEOI returns max CE open interest', () => {
    store.chain = MOCK_CHAIN
    expect(store.maxCEOI).toBe(80000)
  })

  it('maxPEOI returns max PE open interest', () => {
    store.chain = MOCK_CHAIN
    expect(store.maxPEOI).toBe(70000)
  })

  it('filteredChain returns empty for empty chain', () => {
    expect(store.filteredChain).toEqual([])
  })

  it('filteredChain limits to strikesRange around ATM', () => {
    store.chain = MOCK_CHAIN
    store.strikesRange = 2
    const filtered = store.filteredChain
    expect(filtered.length).toBeLessThanOrEqual(5) // 2 above + ATM + 2 below
    expect(filtered.some(r => r.is_atm)).toBe(true)
  })

  it('getIndexToken returns correct token for NIFTY', () => {
    expect(store.getIndexToken()).toBe(256265)
  })
})


describe('optionchain store — fetchExpiries', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
  })

  it('fetches expiries and auto-selects first', async () => {
    api.get.mockResolvedValue({ data: { expiries: ['2026-03-27', '2026-04-03'] } })

    const result = await store.fetchExpiries()

    expect(result.success).toBe(true)
    expect(api.get).toHaveBeenCalledWith('/api/options/expiries', {
      params: { underlying: 'NIFTY' }
    })
    expect(store.expiries).toEqual(['2026-03-27', '2026-04-03'])
    expect(store.expiry).toBe('2026-03-27')
  })

  it('handles empty expiries', async () => {
    api.get.mockResolvedValue({ data: { expiries: [] } })

    await store.fetchExpiries()

    expect(store.expiries).toEqual([])
    expect(store.expiry).toBe('')
  })

  it('sets error on API failure', async () => {
    api.get.mockRejectedValue({ response: { data: { detail: 'Service unavailable' } } })

    const result = await store.fetchExpiries()

    expect(result.success).toBe(false)
    expect(store.error).toBe('Service unavailable')
  })
})


describe('optionchain store — fetchOptionChain', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
  })

  it('returns error when no expiry selected', async () => {
    const result = await store.fetchOptionChain()
    expect(result.success).toBe(false)
    expect(result.error).toBe('No expiry selected')
  })

  it('fetches chain and populates state', async () => {
    store.expiry = '2026-03-27'
    api.get.mockResolvedValue(MOCK_CHAIN_RESPONSE)

    const result = await store.fetchOptionChain()

    expect(result.success).toBe(true)
    expect(store.spotPrice).toBe(24010)
    expect(store.lotSize).toBe(75)
    expect(store.chain).toHaveLength(5)
    expect(store.summary.pcr).toBe(0.9)
    expect(store.summary.max_pain).toBe(24000)
  })

  it('sets loading state during fetch', async () => {
    store.expiry = '2026-03-27'
    let loadingDuringFetch = false
    api.get.mockImplementation(() => {
      loadingDuringFetch = store.isLoading
      return Promise.resolve(MOCK_CHAIN_RESPONSE)
    })

    await store.fetchOptionChain()

    expect(loadingDuringFetch).toBe(true)
    expect(store.isLoading).toBe(false) // cleared after
  })

  it('handles API error', async () => {
    store.expiry = '2026-03-27'
    api.get.mockRejectedValue({ response: { data: { detail: 'No instruments found' } } })

    const result = await store.fetchOptionChain()

    expect(result.success).toBe(false)
    expect(store.error).toBe('No instruments found')
    expect(store.isLoading).toBe(false)
  })
})


describe('optionchain store — strike selection', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
    store.chain = MOCK_CHAIN
  })

  it('selects a strike', () => {
    store.toggleStrikeSelection(24000, 'CE')

    expect(store.selectedStrikes).toHaveLength(1)
    expect(store.selectedStrikes[0].strike).toBe(24000)
    expect(store.selectedStrikes[0].type).toBe('CE')
    expect(store.selectedStrikes[0].ltp).toBe(180)
  })

  it('deselects a previously selected strike', () => {
    store.toggleStrikeSelection(24000, 'CE')
    expect(store.selectedStrikes).toHaveLength(1)

    store.toggleStrikeSelection(24000, 'CE')
    expect(store.selectedStrikes).toHaveLength(0)
  })

  it('selects multiple strikes', () => {
    store.toggleStrikeSelection(24000, 'CE')
    store.toggleStrikeSelection(24100, 'PE')

    expect(store.selectedStrikes).toHaveLength(2)
  })

  it('isStrikeSelected returns correct state', () => {
    store.toggleStrikeSelection(24000, 'CE')

    expect(store.isStrikeSelected(24000, 'CE')).toBe(true)
    expect(store.isStrikeSelected(24000, 'PE')).toBe(false)
    expect(store.isStrikeSelected(24100, 'CE')).toBe(false)
  })

  it('clearSelection removes all', () => {
    store.toggleStrikeSelection(24000, 'CE')
    store.toggleStrikeSelection(24100, 'PE')
    store.clearSelection()

    expect(store.selectedStrikes).toHaveLength(0)
  })

  it('getAddToStrategyPayload returns correct format', () => {
    store.expiry = '2026-03-27'
    store.toggleStrikeSelection(24000, 'CE')

    const payload = store.getAddToStrategyPayload()

    expect(payload).toHaveLength(1)
    expect(payload[0]).toEqual({
      expiry_date: '2026-03-27',
      contract_type: 'CE',
      strike_price: 24000,
      entry_price: 180,
      instrument_token: 1003,
      tradingsymbol: 'NIFTY24000CE',
    })
  })
})


describe('optionchain store — live prices', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
    store.chain = JSON.parse(JSON.stringify(MOCK_CHAIN))
  })

  it('updateLivePrices stores tick data', () => {
    store.updateLivePrices([
      { token: 1003, ltp: 185, change: 5, change_percent: 2.8 }
    ])

    expect(store.livePrices[1003]).toEqual({ ltp: 185, change: 5, change_percent: 2.8 })
  })

  it('updateLivePrices updates chain CE/PE ltps', () => {
    store.updateLivePrices([
      { token: 1003, ltp: 190, change: 10, change_percent: 5.5 }
    ])

    const atmRow = store.chain.find(r => r.is_atm)
    expect(atmRow.ce.ltp).toBe(190)
  })

  it('updateLivePrices updates spot price from index tick', () => {
    store.underlying = 'NIFTY'
    store.updateLivePrices([
      { token: 256265, ltp: 24050, change: 40, change_percent: 0.17 }
    ])

    expect(store.spotPrice).toBe(24050)
  })

  it('updateLivePrices is no-op when live updates disabled', () => {
    store.isLiveUpdatesEnabled = false
    store.updateLivePrices([
      { token: 1003, ltp: 999, change: 0, change_percent: 0 }
    ])

    expect(store.livePrices).toEqual({})
  })

  it('getLiveLTP returns null when live updates disabled', () => {
    store.isLiveUpdatesEnabled = false
    store.livePrices = { 1003: { ltp: 185 } }

    expect(store.getLiveLTP(1003)).toBeNull()
  })

  it('getLiveLTP returns ltp when available', () => {
    store.livePrices = { 1003: { ltp: 185, change: 5, change_percent: 2.8 } }

    expect(store.getLiveLTP(1003)).toBe(185)
  })

  it('toggleLiveUpdates flips the flag', () => {
    expect(store.isLiveUpdatesEnabled).toBe(true)
    store.toggleLiveUpdates()
    expect(store.isLiveUpdatesEnabled).toBe(false)
    store.toggleLiveUpdates()
    expect(store.isLiveUpdatesEnabled).toBe(true)
  })

  it('getAllOptionTokens returns all CE and PE tokens', () => {
    const tokens = store.getAllOptionTokens()
    expect(tokens).toContain(1001) // CE token
    expect(tokens).toContain(2001) // PE token
    expect(tokens).toHaveLength(10) // 5 CE + 5 PE
  })
})


describe('optionchain store — OI bar width', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
    store.chain = MOCK_CHAIN
  })

  it('returns 0 for zero OI', () => {
    expect(store.getOIBarWidth(0, 'ce')).toBe(0)
  })

  it('returns 50 for max OI', () => {
    expect(store.getOIBarWidth(80000, 'ce')).toBe(50)
  })

  it('returns proportional width', () => {
    expect(store.getOIBarWidth(40000, 'ce')).toBe(25) // 40000/80000 * 50
  })
})


describe('optionchain store — strike finder', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
  })

  it('toggleStrikeFinder opens and closes', () => {
    expect(store.strikeFinder.visible).toBe(false)
    store.toggleStrikeFinder()
    expect(store.strikeFinder.visible).toBe(true)
    store.toggleStrikeFinder()
    expect(store.strikeFinder.visible).toBe(false)
  })

  it('closing strike finder clears result', () => {
    store.strikeFinder.visible = true
    store.strikeFinder.result = { strike: 24000 }
    store.toggleStrikeFinder() // close
    expect(store.strikeFinder.result).toBeNull()
  })

  it('findStrikeByDelta calls API and stores result', async () => {
    const mockResult = { strike: 24100, delta: 0.3, ltp: 80 }
    api.post.mockResolvedValue({ data: mockResult })

    const result = await store.findStrikeByDelta({
      underlying: 'NIFTY', expiry: '2026-03-27', option_type: 'CE', target_delta: 0.3
    })

    expect(api.post).toHaveBeenCalledWith('/api/optionchain/find-by-delta', expect.objectContaining({
      target_delta: 0.3,
      option_type: 'CE',
    }))
    expect(store.strikeFinder.result).toEqual(mockResult)
    expect(store.strikeFinder.loading).toBe(false)
  })

  it('findStrikeByDelta handles error', async () => {
    api.post.mockRejectedValue({ response: { data: { detail: 'No match found' } } })

    await expect(store.findStrikeByDelta({
      underlying: 'NIFTY', expiry: '2026-03-27', option_type: 'CE', target_delta: 0.99
    })).rejects.toBeDefined()

    expect(store.strikeFinder.error).toBe('No match found')
    expect(store.strikeFinder.loading).toBe(false)
  })

  it('findStrikeByPremium calls correct API', async () => {
    api.post.mockResolvedValue({ data: { strike: 24200, premium: 50 } })

    await store.findStrikeByPremium({
      underlying: 'NIFTY', expiry: '2026-03-27', option_type: 'PE', target_premium: 50
    })

    expect(api.post).toHaveBeenCalledWith('/api/optionchain/find-by-premium', expect.objectContaining({
      target_premium: 50,
      option_type: 'PE',
    }))
  })

  it('clearStrikeFinderResult clears result and error', () => {
    store.strikeFinder.result = { strike: 24000 }
    store.strikeFinder.error = 'some error'
    store.clearStrikeFinderResult()
    expect(store.strikeFinder.result).toBeNull()
    expect(store.strikeFinder.error).toBeNull()
  })
})


describe('optionchain store — setUnderlying', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: { expiries: [] } })
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
  })

  it('uppercases underlying name', async () => {
    await store.setUnderlying('banknifty')
    expect(store.underlying).toBe('BANKNIFTY')
  })

  it('updates lot size for new underlying', async () => {
    await store.setUnderlying('BANKNIFTY')
    expect(store.lotSize).toBe(35)
  })

  it('resets expiry and chain when switching', async () => {
    store.expiry = '2026-03-27'
    store.chain = MOCK_CHAIN
    await store.setUnderlying('BANKNIFTY')
    expect(store.expiry).toBe('')
    expect(store.chain).toEqual([])
  })

  it('clears error when switching underlying', async () => {
    store.error = 'Previous error'
    await store.setUnderlying('BANKNIFTY')
    expect(store.error).toBeNull()
  })

  it('fetches expiries for new underlying', async () => {
    await store.setUnderlying('FINNIFTY')
    expect(api.get).toHaveBeenCalledWith('/api/options/expiries', {
      params: { underlying: 'FINNIFTY' }
    })
  })
})


describe('optionchain store — reset', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useOptionChainStore } = await import('@/stores/optionchain')
    store = useOptionChainStore()
  })

  it('resets all state to defaults', () => {
    store.underlying = 'BANKNIFTY'
    store.expiry = '2026-03-27'
    store.chain = MOCK_CHAIN
    store.spotPrice = 24000
    store.isLoading = true
    store.error = 'some error'
    store.isLiveUpdatesEnabled = false
    store.selectedStrikes = [{ key: '24000-CE' }]
    store.livePrices = { 1003: { ltp: 185 } }

    store.reset()

    expect(store.underlying).toBe('NIFTY')
    expect(store.expiry).toBe('')
    expect(store.expiries).toEqual([])
    expect(store.chain).toEqual([])
    expect(store.spotPrice).toBe(0)
    expect(store.lotSize).toBe(75)
    expect(store.isLoading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.isLiveUpdatesEnabled).toBe(true)
    expect(store.selectedStrikes).toEqual([])
    expect(store.livePrices).toEqual({})
  })
})
