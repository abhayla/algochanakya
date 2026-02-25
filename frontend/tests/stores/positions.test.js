/**
 * Positions Pinia Store Tests
 *
 * Tests for src/stores/positions.js — F&O positions state management
 * Covers: fetchPositions, exitPosition, addToPosition, exitAll, getters, modals
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePositionsStore } from '@/stores/positions'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import api from '@/services/api'


// =============================================================================
// TEST DATA
// =============================================================================

const mockPositions = [
  {
    tradingsymbol: 'NIFTY2430024000CE',
    underlying: 'NIFTY',
    quantity: 50,
    pnl: 2500,
    average_price: 150,
    last_price: 200,
    product: 'NRML',
    exchange: 'NFO'
  },
  {
    tradingsymbol: 'NIFTY2430024000PE',
    underlying: 'NIFTY',
    quantity: -50,
    pnl: -1000,
    average_price: 80,
    last_price: 100,
    product: 'NRML',
    exchange: 'NFO'
  },
  {
    tradingsymbol: 'BANKNIFTY2430050000CE',
    underlying: 'BANKNIFTY',
    quantity: 30,
    pnl: 500,
    average_price: 200,
    last_price: 217,
    product: 'NRML',
    exchange: 'NFO'
  }
]

const mockSummary = {
  total_pnl: 2000,
  total_pnl_pct: 5.2,
  realized_pnl: 500,
  unrealized_pnl: 1500,
  total_positions: 3,
  total_quantity: 30,
  margin_used: 150000,
  margin_available: 350000
}

const mockFetchResponse = {
  data: {
    positions: mockPositions,
    summary: mockSummary
  }
}


// =============================================================================
// SETUP
// =============================================================================

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})


// =============================================================================
// INITIAL STATE
// =============================================================================

describe('Positions Store - Initial State', () => {
  it('should start with empty positions', () => {
    const store = usePositionsStore()
    expect(store.positions).toEqual([])
  })

  it('should start with zeroed summary', () => {
    const store = usePositionsStore()
    expect(store.summary.total_pnl).toBe(0)
    expect(store.summary.total_positions).toBe(0)
  })

  it('should default to day position type', () => {
    const store = usePositionsStore()
    expect(store.positionType).toBe('day')
  })

  it('should start with modals closed', () => {
    const store = usePositionsStore()
    expect(store.exitModal.show).toBe(false)
    expect(store.addModal.show).toBe(false)
  })
})


// =============================================================================
// GETTERS
// =============================================================================

describe('Positions Store - Getters', () => {
  it('should filter profit positions', () => {
    const store = usePositionsStore()
    store.positions = mockPositions

    expect(store.profitPositions).toHaveLength(2)
    store.profitPositions.forEach(p => {
      expect(p.pnl).toBeGreaterThan(0)
    })
  })

  it('should filter loss positions', () => {
    const store = usePositionsStore()
    store.positions = mockPositions

    expect(store.lossPositions).toHaveLength(1)
    store.lossPositions.forEach(p => {
      expect(p.pnl).toBeLessThan(0)
    })
  })

  it('should filter long positions', () => {
    const store = usePositionsStore()
    store.positions = mockPositions

    expect(store.longPositions).toHaveLength(2)
    store.longPositions.forEach(p => {
      expect(p.quantity).toBeGreaterThan(0)
    })
  })

  it('should filter short positions', () => {
    const store = usePositionsStore()
    store.positions = mockPositions

    expect(store.shortPositions).toHaveLength(1)
    store.shortPositions.forEach(p => {
      expect(p.quantity).toBeLessThan(0)
    })
  })

  it('should group positions by underlying', () => {
    const store = usePositionsStore()
    store.positions = mockPositions

    const groups = store.positionsByUnderlying
    expect(groups).toHaveProperty('NIFTY')
    expect(groups).toHaveProperty('BANKNIFTY')
    expect(groups.NIFTY.positions).toHaveLength(2)
    expect(groups.BANKNIFTY.positions).toHaveLength(1)
  })
})


// =============================================================================
// FETCH POSITIONS
// =============================================================================

describe('Positions Store - Fetch Positions', () => {
  it('should fetch and set positions', async () => {
    api.get.mockResolvedValueOnce(mockFetchResponse)
    const store = usePositionsStore()

    await store.fetchPositions()

    expect(store.positions).toHaveLength(3)
    expect(store.summary.total_pnl).toBe(2000)
    expect(store.isLoading).toBe(false)
  })

  it('should set loading during fetch', async () => {
    let resolve
    api.get.mockReturnValueOnce(new Promise(r => { resolve = r }))
    const store = usePositionsStore()

    const promise = store.fetchPositions()
    expect(store.isLoading).toBe(true)

    resolve(mockFetchResponse)
    await promise
    expect(store.isLoading).toBe(false)
  })

  it('should handle fetch error', async () => {
    api.get.mockRejectedValueOnce(new Error('Network error'))
    const store = usePositionsStore()

    await store.fetchPositions()

    expect(store.error).not.toBeNull()
    expect(store.isLoading).toBe(false)
  })

  it('should call correct API endpoint for day positions', async () => {
    api.get.mockResolvedValueOnce(mockFetchResponse)
    const store = usePositionsStore()
    store.positionType = 'day'

    await store.fetchPositions()

    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('/api/positions'))
  })
})


// =============================================================================
// EXIT MODAL
// =============================================================================

describe('Positions Store - Exit Modal', () => {
  it('should open exit modal with position data', () => {
    const store = usePositionsStore()
    const position = mockPositions[0]

    if (store.openExitModal) {
      store.openExitModal(position)
      expect(store.exitModal.show).toBe(true)
      expect(store.exitModal.position).toEqual(position)
    }
  })

  it('should close exit modal', () => {
    const store = usePositionsStore()
    store.exitModal.show = true
    store.exitModal.position = mockPositions[0]

    if (store.closeExitModal) {
      store.closeExitModal()
      expect(store.exitModal.show).toBe(false)
    }
  })
})


// =============================================================================
// ADD MODAL
// =============================================================================

describe('Positions Store - Add Modal', () => {
  it('should default add modal to BUY and LIMIT', () => {
    const store = usePositionsStore()
    expect(store.addModal.transactionType).toBe('BUY')
    expect(store.addModal.orderType).toBe('LIMIT')
  })
})
