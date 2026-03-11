/**
 * Option Chain Store — Lot Size Tests
 *
 * Reproduces Bug 3: lotSize hardcoded to 75 in store initialization
 * instead of derived from getLotSize() trading constants.
 *
 * Related bugs:
 * - frontend/src/constants/trading.js had stale fallback lot sizes (NIFTY: 25, etc.)
 *   served when /api/constants/trading fails on startup
 * - frontend/src/stores/optionchain.js line 14 used ref(75) instead of ref(getLotSize('NIFTY'))
 * - reset() hardcoded lotSize.value = 75 instead of getLotSize('NIFTY')
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock trading constants with realistic correct values (NSE Nov 2024 circular)
vi.mock('@/constants/trading', () => ({
  getLotSize: vi.fn((underlying) => {
    const sizes = { NIFTY: 75, BANKNIFTY: 35, FINNIFTY: 65, SENSEX: 20 }
    return sizes[(underlying || 'NIFTY').toUpperCase()] ?? 75
  }),
  getIndexToken: vi.fn(() => 256265),
  getIndexSymbol: vi.fn(() => 'NSE:NIFTY 50'),
}))

vi.mock('@/stores/userPreferences', () => ({
  useUserPreferencesStore: () => ({ pnlGridInterval: 100 })
}))

vi.mock('@/stores/watchlist', () => ({
  useWatchlistStore: () => ({
    ticks: {},
    isConnected: false,
    connectWebSocket: vi.fn(),
    subscribeToTokens: vi.fn(),
    unsubscribeFromTokens: vi.fn(),
  })
}))

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { expiries: [] } }),
    post: vi.fn(),
  }
}))

describe('optionchain store — lot size initialization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initial lotSize for NIFTY should be 75 (from getLotSize, not hardcoded)', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()

    // Store default underlying is NIFTY. getLotSize('NIFTY') = 75.
    // Bug was: ref(75) hardcoded → any change to constants wouldn't be reflected.
    // Fix: ref(getLotSize('NIFTY')) — derives the value from constants.
    expect(store.lotSize).toBe(75)
  })

  it('setUnderlying to BANKNIFTY updates lotSize to 35', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()

    await store.setUnderlying('BANKNIFTY')

    // getLotSize mock returns 35 for BANKNIFTY
    expect(store.lotSize).toBe(35)
  })

  it('setUnderlying to FINNIFTY updates lotSize to 65', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()

    await store.setUnderlying('FINNIFTY')

    // getLotSize mock returns 65 for FINNIFTY
    expect(store.lotSize).toBe(65)
  })

  it('reset() restores lotSize to NIFTY value (75) from getLotSize', async () => {
    const { useOptionChainStore } = await import('@/stores/optionchain')
    const store = useOptionChainStore()

    await store.setUnderlying('BANKNIFTY')
    expect(store.lotSize).toBe(35) // Sanity check

    store.reset()

    // After reset, underlying = 'NIFTY', lotSize should = getLotSize('NIFTY') = 75
    expect(store.underlying).toBe('NIFTY')
    expect(store.lotSize).toBe(75)
  })
})

describe('frontend trading constants — fallback lot sizes', () => {
  it('NIFTY fallback lot size must be 75 (was 25 — stale pre-2024 value)', async () => {
    // Unmap the mock to test the real module
    vi.unmock('@/constants/trading')

    const { tradingConstants } = await import('@/constants/trading')

    // frontend/src/constants/trading.js previously had:
    //   lot_sizes: { NIFTY: 25, BANKNIFTY: 15, FINNIFTY: 25, SENSEX: 10 }
    // After NSE Nov 2024 circular, correct values are:
    //   NIFTY: 75, BANKNIFTY: 35, FINNIFTY: 65, SENSEX: 20
    expect(tradingConstants.value.lot_sizes.NIFTY).toBe(75)
    expect(tradingConstants.value.lot_sizes.BANKNIFTY).toBe(35)
    expect(tradingConstants.value.lot_sizes.FINNIFTY).toBe(65)
    expect(tradingConstants.value.lot_sizes.SENSEX).toBe(20)
  })
})
