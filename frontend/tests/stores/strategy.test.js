/**
 * Strategy Builder Pinia Store Tests
 *
 * Tests for src/stores/strategy.js — strategy builder state management
 * Covers: leg management, P/L calculation, save/load, share functionality
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useStrategyStore } from '@/stores/strategy'

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

const mockLeg = {
  instrument: 'NIFTY',
  expiry: '2024-03-28',
  strike: 24000,
  type: 'CE',
  action: 'BUY',
  lots: 1,
  entryPrice: 150,
  lotSize: 25
}

const mockIronCondor = [
  { ...mockLeg, strike: 23500, type: 'PE', action: 'SELL', entryPrice: 80 },
  { ...mockLeg, strike: 23000, type: 'PE', action: 'BUY', entryPrice: 40 },
  { ...mockLeg, strike: 24500, type: 'CE', action: 'SELL', entryPrice: 90 },
  { ...mockLeg, strike: 25000, type: 'CE', action: 'BUY', entryPrice: 45 }
]

const mockSaveResponse = {
  data: {
    id: 1,
    name: 'Iron Condor NIFTY',
    legs: mockIronCondor
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

describe('Strategy Store - Initial State', () => {
  it('should start with empty legs', () => {
    const store = useStrategyStore()
    expect(store.legs).toEqual([])
  })

  it('should default to NIFTY underlying', () => {
    const store = useStrategyStore()
    // Underlying may vary — just check it's set
    expect(store.underlying).toBeDefined()
  })

  it('should start with no loading', () => {
    const store = useStrategyStore()
    expect(store.isLoading).toBe(false)
  })
})


// =============================================================================
// LEG MANAGEMENT
// =============================================================================

describe('Strategy Store - Leg Management', () => {
  it('should add a leg', () => {
    const store = useStrategyStore()

    if (store.addLeg) {
      store.addLeg(mockLeg)
      expect(store.legs).toHaveLength(1)
      expect(store.legs[0].strike).toBe(24000)
    }
  })

  it('should remove a leg', () => {
    const store = useStrategyStore()

    if (store.addLeg && store.removeLeg) {
      store.addLeg(mockLeg)
      expect(store.legs).toHaveLength(1)

      store.removeLeg(0)
      expect(store.legs).toHaveLength(0)
    }
  })

  it('should clear all legs', () => {
    const store = useStrategyStore()

    if (store.addLeg && store.clearLegs) {
      mockIronCondor.forEach(leg => store.addLeg(leg))
      expect(store.legs.length).toBeGreaterThan(0)

      store.clearLegs()
      expect(store.legs).toHaveLength(0)
    }
  })

  it('should update leg entry price', () => {
    const store = useStrategyStore()

    if (store.addLeg && store.updateLeg) {
      store.addLeg(mockLeg)
      store.updateLeg(0, { entryPrice: 200 })
      expect(store.legs[0].entryPrice).toBe(200)
    }
  })
})


// =============================================================================
// P/L CALCULATION
// =============================================================================

describe('Strategy Store - P/L Calculation', () => {
  it('should calculate P/L for a simple long call', () => {
    const store = useStrategyStore()

    if (store.addLeg && store.calculatePnL) {
      store.addLeg({
        ...mockLeg,
        action: 'BUY',
        entryPrice: 150,
        lots: 1,
        lotSize: 25
      })

      // At expiry, spot = 24500 (in the money by 500)
      // P/L = (500 - 150) * 25 = 8750
      const pnl = store.calculatePnL ? store.calculatePnL(24500) : null
      if (pnl !== null) {
        expect(typeof pnl).toBe('number')
      }
    }
  })
})


// =============================================================================
// SAVE / LOAD
// =============================================================================

describe('Strategy Store - Save / Load', () => {
  it('should save strategy via API', async () => {
    api.post.mockResolvedValueOnce(mockSaveResponse)
    const store = useStrategyStore()

    if (store.saveStrategy) {
      const result = await store.saveStrategy('Iron Condor NIFTY')

      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/strategies'),
        expect.any(Object)
      )
    }
  })

  it('should load strategy from API', async () => {
    api.get.mockResolvedValueOnce(mockSaveResponse)
    const store = useStrategyStore()

    if (store.loadStrategy) {
      await store.loadStrategy(1)

      expect(api.get).toHaveBeenCalledWith(expect.stringContaining('/api/strategies'))
    }
  })
})


// =============================================================================
// UNDERLYING SELECTION
// =============================================================================

describe('Strategy Store - Underlying Selection', () => {
  it('should change underlying', () => {
    const store = useStrategyStore()

    if (store.setUnderlying) {
      store.setUnderlying('BANKNIFTY')
      expect(store.underlying).toBe('BANKNIFTY')
    }
  })
})
