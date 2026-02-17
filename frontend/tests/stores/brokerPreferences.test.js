/**
 * brokerPreferences Pinia Store Tests
 *
 * Tests for src/stores/brokerPreferences.js
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBrokerPreferencesStore } from '@/stores/brokerPreferences'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  }
}))

import api from '@/services/api'

const mockPreferences = {
  market_data_source: 'smartapi',
  order_broker: 'kite',
  pnl_grid_interval: 100,
}

describe('useBrokerPreferencesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  // ---------------------------------------------------------------------------
  // Initial state
  // ---------------------------------------------------------------------------

  it('has correct initial state', () => {
    const store = useBrokerPreferencesStore()
    expect(store.marketDataSource).toBeDefined()
    expect(store.orderBroker).toBeDefined()
    expect(store.loading).toBe(false)
    expect(store.saving).toBe(false)
    expect(store.error).toBeNull()
  })

  // ---------------------------------------------------------------------------
  // fetchPreferences
  // ---------------------------------------------------------------------------

  it('fetchPreferences sets marketDataSource from API', async () => {
    api.get.mockResolvedValueOnce({ data: mockPreferences })
    const store = useBrokerPreferencesStore()

    await store.fetchPreferences()

    expect(api.get).toHaveBeenCalledWith('/api/user/preferences/')
    expect(store.marketDataSource).toBe('smartapi')
  })

  it('fetchPreferences sets orderBroker from API', async () => {
    api.get.mockResolvedValueOnce({ data: mockPreferences })
    const store = useBrokerPreferencesStore()

    await store.fetchPreferences()

    expect(store.orderBroker).toBe('kite')
  })

  it('fetchPreferences sets loading correctly', async () => {
    const loadingStates = []
    api.get.mockImplementationOnce(async () => {
      loadingStates.push(true) // during fetch
      return { data: mockPreferences }
    })
    const store = useBrokerPreferencesStore()

    await store.fetchPreferences()

    expect(store.loading).toBe(false) // cleared after
  })

  it('fetchPreferences handles error', async () => {
    api.get.mockRejectedValueOnce({ response: { data: { detail: 'Unauthorized' } } })
    const store = useBrokerPreferencesStore()

    await expect(store.fetchPreferences()).rejects.toBeDefined()
    expect(store.error).toBe('Unauthorized')
    expect(store.loading).toBe(false)
  })

  // ---------------------------------------------------------------------------
  // updatePreferences
  // ---------------------------------------------------------------------------

  it('updatePreferences sends PUT with market_data_source', async () => {
    api.put.mockResolvedValueOnce({ data: { ...mockPreferences, market_data_source: 'dhan' } })
    const store = useBrokerPreferencesStore()

    await store.updatePreferences({ market_data_source: 'dhan' })

    expect(api.put).toHaveBeenCalledWith('/api/user/preferences/', { market_data_source: 'dhan' })
    expect(store.marketDataSource).toBe('dhan')
  })

  it('updatePreferences sends PUT with order_broker', async () => {
    api.put.mockResolvedValueOnce({ data: { ...mockPreferences, order_broker: 'upstox' } })
    const store = useBrokerPreferencesStore()

    await store.updatePreferences({ order_broker: 'upstox' })

    expect(api.put).toHaveBeenCalledWith('/api/user/preferences/', { order_broker: 'upstox' })
    expect(store.orderBroker).toBe('upstox')
  })

  it('updatePreferences handles error', async () => {
    api.put.mockRejectedValueOnce({ response: { data: { detail: 'Invalid broker' } } })
    const store = useBrokerPreferencesStore()

    await expect(store.updatePreferences({ market_data_source: 'bad' })).rejects.toBeDefined()
    expect(store.error).toBe('Invalid broker')
    expect(store.saving).toBe(false)
  })

  // ---------------------------------------------------------------------------
  // Getters / computed
  // ---------------------------------------------------------------------------

  it('isUsingPlatformDefault returns true when market_data_source is platform', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockPreferences, market_data_source: 'platform' } })
    const store = useBrokerPreferencesStore()
    await store.fetchPreferences()

    expect(store.isUsingPlatformDefault).toBe(true)
  })

  it('isUsingPlatformDefault returns false when user has own broker', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockPreferences, market_data_source: 'dhan' } })
    const store = useBrokerPreferencesStore()
    await store.fetchPreferences()

    expect(store.isUsingPlatformDefault).toBe(false)
  })

  it('activeSourceLabel returns correct label for smartapi', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockPreferences, market_data_source: 'smartapi' } })
    const store = useBrokerPreferencesStore()
    await store.fetchPreferences()

    expect(store.activeSourceLabel).toBe('SmartAPI')
  })

  it('activeSourceLabel returns correct label for platform', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockPreferences, market_data_source: 'platform' } })
    const store = useBrokerPreferencesStore()
    await store.fetchPreferences()

    expect(store.activeSourceLabel).toBe('Platform Default')
  })
})
