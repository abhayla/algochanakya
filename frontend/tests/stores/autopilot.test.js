/**
 * AutoPilot Pinia Store Tests
 *
 * Tests for src/stores/autopilot.js
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAutopilotStore } from '@/stores/autopilot'

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

const mockStrategy = {
  id: 1,
  name: 'Test Strategy',
  status: 'draft',
  underlying: 'NIFTY',
  legs_config: [],
  entry_conditions: { logic: 'AND', conditions: [] }
}

const mockActiveStrategy = {
  id: 2,
  name: 'Active Strategy',
  status: 'active',
  underlying: 'BANKNIFTY'
}

const mockWaitingStrategy = {
  id: 3,
  name: 'Waiting Strategy',
  status: 'waiting',
  underlying: 'NIFTY'
}

const mockCompletedStrategy = {
  id: 4,
  name: 'Completed Strategy',
  status: 'completed',
  underlying: 'FINNIFTY'
}

const mockDashboardSummary = {
  active_strategies: 2,
  waiting_strategies: 1,
  completed_strategies: 3,
  today_total_pnl: 5000,
  kite_connected: true,
  risk_metrics: {
    status: 'safe',
    daily_loss_used_pct: 20
  }
}

const mockSettings = {
  max_active_strategies: 5,
  max_daily_loss: 10000,
  notifications_enabled: true
}


// =============================================================================
// INITIAL STATE TESTS
// =============================================================================

describe('AutoPilot Store - Initial State', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initializes with default state', () => {
    const store = useAutopilotStore()

    expect(store.strategies).toEqual([])
    expect(store.currentStrategy).toBeNull()
    expect(store.dashboardSummary).toBeNull()
    expect(store.settings).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.saving).toBe(false)
    expect(store.error).toBeNull()
  })

  it('initializes pagination with defaults', () => {
    const store = useAutopilotStore()

    expect(store.pagination).toEqual({
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0
    })
  })

  it('initializes filters as null', () => {
    const store = useAutopilotStore()

    expect(store.filters).toEqual({
      status: null,
      underlying: null
    })
  })

  it('initializes builder with empty strategy', () => {
    const store = useAutopilotStore()

    expect(store.builder.step).toBe(1)
    expect(store.builder.strategy.name).toBe('')
    expect(store.builder.strategy.underlying).toBe('NIFTY')
    expect(store.builder.strategy.legs_config).toEqual([])
    expect(store.builder.validation).toEqual({})
  })
})


// =============================================================================
// GETTERS TESTS
// =============================================================================

describe('AutoPilot Store - Getters', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  describe('activeStrategies', () => {
    it('returns only active, waiting, and pending strategies', () => {
      store.strategies = [
        { id: 1, status: 'active' },
        { id: 2, status: 'waiting' },
        { id: 3, status: 'pending' },
        { id: 4, status: 'draft' },
        { id: 5, status: 'completed' }
      ]

      expect(store.activeStrategies).toHaveLength(3)
      expect(store.activeStrategies.map(s => s.id)).toEqual([1, 2, 3])
    })

    it('returns empty array when no active strategies', () => {
      store.strategies = [
        { id: 1, status: 'draft' },
        { id: 2, status: 'completed' }
      ]

      expect(store.activeStrategies).toHaveLength(0)
    })
  })

  describe('draftStrategies', () => {
    it('returns only draft strategies', () => {
      store.strategies = [
        { id: 1, status: 'draft' },
        { id: 2, status: 'active' },
        { id: 3, status: 'draft' }
      ]

      expect(store.draftStrategies).toHaveLength(2)
      expect(store.draftStrategies.map(s => s.id)).toEqual([1, 3])
    })
  })

  describe('completedStrategies', () => {
    it('returns completed, error, and expired strategies', () => {
      store.strategies = [
        { id: 1, status: 'completed' },
        { id: 2, status: 'error' },
        { id: 3, status: 'expired' },
        { id: 4, status: 'active' }
      ]

      expect(store.completedStrategies).toHaveLength(3)
      expect(store.completedStrategies.map(s => s.id)).toEqual([1, 2, 3])
    })
  })

  describe('hasActiveStrategies', () => {
    it('returns true when active strategies exist', () => {
      store.strategies = [{ id: 1, status: 'active' }]
      expect(store.hasActiveStrategies).toBe(true)
    })

    it('returns true when waiting strategies exist', () => {
      store.strategies = [{ id: 1, status: 'waiting' }]
      expect(store.hasActiveStrategies).toBe(true)
    })

    it('returns false when only drafts exist', () => {
      store.strategies = [{ id: 1, status: 'draft' }]
      expect(store.hasActiveStrategies).toBe(false)
    })

    it('returns false when strategies is empty', () => {
      store.strategies = []
      expect(store.hasActiveStrategies).toBe(false)
    })
  })

  describe('todayPnL', () => {
    it('returns PnL from dashboard summary', () => {
      store.dashboardSummary = { today_total_pnl: 5000 }
      expect(store.todayPnL).toBe(5000)
    })

    it('returns 0 when dashboard summary is null', () => {
      store.dashboardSummary = null
      expect(store.todayPnL).toBe(0)
    })

    it('returns 0 when PnL is not set', () => {
      store.dashboardSummary = {}
      expect(store.todayPnL).toBe(0)
    })
  })

  describe('riskStatus', () => {
    it('returns risk status from dashboard', () => {
      store.dashboardSummary = {
        risk_metrics: { status: 'warning' }
      }
      expect(store.riskStatus).toBe('warning')
    })

    it('returns safe when dashboard is null', () => {
      store.dashboardSummary = null
      expect(store.riskStatus).toBe('safe')
    })

    it('returns safe when risk_metrics is missing', () => {
      store.dashboardSummary = {}
      expect(store.riskStatus).toBe('safe')
    })
  })

  describe('isKiteConnected', () => {
    it('returns true when Kite is connected', () => {
      store.dashboardSummary = { kite_connected: true }
      expect(store.isKiteConnected).toBe(true)
    })

    it('returns false when Kite is not connected', () => {
      store.dashboardSummary = { kite_connected: false }
      expect(store.isKiteConnected).toBe(false)
    })

    it('returns false when dashboard is null', () => {
      store.dashboardSummary = null
      expect(store.isKiteConnected).toBe(false)
    })
  })

  describe('canCreateStrategy', () => {
    it('returns true when no settings or dashboard', () => {
      store.settings = null
      store.dashboardSummary = null
      expect(store.canCreateStrategy).toBe(true)
    })

    it('returns true when under limit', () => {
      store.settings = { max_active_strategies: 5 }
      store.dashboardSummary = {
        active_strategies: 2,
        waiting_strategies: 1
      }
      expect(store.canCreateStrategy).toBe(true)
    })

    it('returns false when at limit', () => {
      store.settings = { max_active_strategies: 3 }
      store.dashboardSummary = {
        active_strategies: 2,
        waiting_strategies: 1
      }
      expect(store.canCreateStrategy).toBe(false)
    })

    it('returns false when over limit', () => {
      store.settings = { max_active_strategies: 2 }
      store.dashboardSummary = {
        active_strategies: 2,
        waiting_strategies: 1
      }
      expect(store.canCreateStrategy).toBe(false)
    })
  })
})


// =============================================================================
// FETCH STRATEGIES TESTS
// =============================================================================

describe('AutoPilot Store - fetchStrategies', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  it('fetches strategies successfully', async () => {
    const mockResponse = {
      data: {
        data: [mockStrategy, mockActiveStrategy],
        page: 1,
        page_size: 20,
        total: 2,
        total_pages: 1
      }
    }
    api.get.mockResolvedValue(mockResponse)

    await store.fetchStrategies()

    expect(api.get).toHaveBeenCalledWith('/api/v1/autopilot/strategies', {
      params: { page: 1, page_size: 20 }
    })
    expect(store.strategies).toEqual([mockStrategy, mockActiveStrategy])
    expect(store.pagination.total).toBe(2)
    expect(store.loading).toBe(false)
  })

  it('sets loading during fetch', async () => {
    api.get.mockImplementation(() => new Promise(() => {})) // Never resolves

    store.fetchStrategies()
    expect(store.loading).toBe(true)
  })

  it('applies filters to request', async () => {
    api.get.mockResolvedValue({
      data: { data: [], page: 1, page_size: 20, total: 0, total_pages: 0 }
    })

    store.setFilters({ status: 'active', underlying: 'NIFTY' })
    await store.fetchStrategies()

    expect(api.get).toHaveBeenCalledWith('/api/v1/autopilot/strategies', {
      params: {
        page: 1,
        page_size: 20,
        status: 'active',
        underlying: 'NIFTY'
      }
    })
  })

  it('removes null filter values', async () => {
    api.get.mockResolvedValue({
      data: { data: [], page: 1, page_size: 20, total: 0, total_pages: 0 }
    })

    store.setFilters({ status: 'active', underlying: null })
    await store.fetchStrategies()

    const callParams = api.get.mock.calls[0][1].params
    expect(callParams.status).toBe('active')
    expect(callParams).not.toHaveProperty('underlying')
  })

  it('handles fetch error', async () => {
    const errorResponse = {
      response: { data: { detail: 'Server error' } }
    }
    api.get.mockRejectedValue(errorResponse)

    await expect(store.fetchStrategies()).rejects.toEqual(errorResponse)
    expect(store.error).toBe('Server error')
    expect(store.loading).toBe(false)
  })

  it('uses custom pagination options', async () => {
    api.get.mockResolvedValue({
      data: { data: [], page: 2, page_size: 50, total: 100, total_pages: 2 }
    })

    await store.fetchStrategies({ page: 2, pageSize: 50 })

    expect(api.get).toHaveBeenCalledWith('/api/v1/autopilot/strategies', {
      params: { page: 2, page_size: 50 }
    })
    expect(store.pagination.page).toBe(2)
    expect(store.pagination.pageSize).toBe(50)
  })
})


// =============================================================================
// FETCH SINGLE STRATEGY TESTS
// =============================================================================

describe('AutoPilot Store - fetchStrategy', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  it('fetches single strategy successfully', async () => {
    api.get.mockResolvedValue({
      data: { data: mockStrategy }
    })

    const result = await store.fetchStrategy(1)

    expect(api.get).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1')
    expect(store.currentStrategy).toEqual(mockStrategy)
    expect(result).toEqual(mockStrategy)
  })

  it('handles fetch error', async () => {
    api.get.mockRejectedValue({
      response: { data: { detail: 'Not found' } }
    })

    await expect(store.fetchStrategy(999)).rejects.toBeDefined()
    expect(store.error).toBe('Not found')
  })
})


// =============================================================================
// CREATE STRATEGY TESTS
// =============================================================================

describe('AutoPilot Store - createStrategy', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  it('creates strategy successfully', async () => {
    api.post.mockResolvedValue({
      data: { data: mockStrategy }
    })

    const result = await store.createStrategy({ name: 'Test' })

    expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies', { name: 'Test' })
    expect(store.strategies[0]).toEqual(mockStrategy)
    expect(result).toEqual(mockStrategy)
    expect(store.saving).toBe(false)
  })

  it('sets saving during create', async () => {
    api.post.mockImplementation(() => new Promise(() => {}))

    store.createStrategy({ name: 'Test' })
    expect(store.saving).toBe(true)
  })

  it('handles create error', async () => {
    api.post.mockRejectedValue({
      response: { data: { detail: 'Validation error' } }
    })

    await expect(store.createStrategy({})).rejects.toBeDefined()
    expect(store.error).toBe('Validation error')
  })
})


// =============================================================================
// UPDATE STRATEGY TESTS
// =============================================================================

describe('AutoPilot Store - updateStrategy', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    store.strategies = [{ ...mockStrategy }]
    vi.clearAllMocks()
  })

  it('updates strategy successfully', async () => {
    const updatedStrategy = { ...mockStrategy, name: 'Updated Name' }
    api.put.mockResolvedValue({
      data: { data: updatedStrategy }
    })

    const result = await store.updateStrategy(1, { name: 'Updated Name' })

    expect(api.put).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1', { name: 'Updated Name' })
    expect(store.strategies[0].name).toBe('Updated Name')
    expect(result.name).toBe('Updated Name')
  })

  it('updates currentStrategy if same ID', async () => {
    store.currentStrategy = { ...mockStrategy }
    const updatedStrategy = { ...mockStrategy, name: 'Updated' }
    api.put.mockResolvedValue({
      data: { data: updatedStrategy }
    })

    await store.updateStrategy(1, { name: 'Updated' })

    expect(store.currentStrategy.name).toBe('Updated')
  })

  it('does not update currentStrategy if different ID', async () => {
    store.currentStrategy = { id: 999, name: 'Different' }
    api.put.mockResolvedValue({
      data: { data: { ...mockStrategy, name: 'Updated' } }
    })

    await store.updateStrategy(1, { name: 'Updated' })

    expect(store.currentStrategy.name).toBe('Different')
  })
})


// =============================================================================
// DELETE STRATEGY TESTS
// =============================================================================

describe('AutoPilot Store - deleteStrategy', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    store.strategies = [{ ...mockStrategy }, { ...mockActiveStrategy }]
    vi.clearAllMocks()
  })

  it('deletes strategy successfully', async () => {
    api.delete.mockResolvedValue({})

    await store.deleteStrategy(1)

    expect(api.delete).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1')
    expect(store.strategies).toHaveLength(1)
    expect(store.strategies[0].id).toBe(2)
  })

  it('clears currentStrategy if same ID', async () => {
    store.currentStrategy = { ...mockStrategy }
    api.delete.mockResolvedValue({})

    await store.deleteStrategy(1)

    expect(store.currentStrategy).toBeNull()
  })

  it('does not clear currentStrategy if different ID', async () => {
    store.currentStrategy = { ...mockActiveStrategy }
    api.delete.mockResolvedValue({})

    await store.deleteStrategy(1)

    expect(store.currentStrategy).not.toBeNull()
    expect(store.currentStrategy.id).toBe(2)
  })
})


// =============================================================================
// LIFECYCLE ACTION TESTS
// =============================================================================

describe('AutoPilot Store - Lifecycle Actions', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    store.strategies = [{ ...mockStrategy }]
    vi.clearAllMocks()
  })

  describe('activateStrategy', () => {
    it('activates strategy successfully', async () => {
      const activatedStrategy = { ...mockStrategy, status: 'waiting' }
      api.post.mockResolvedValue({
        data: { data: activatedStrategy }
      })

      const result = await store.activateStrategy(1)

      expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1/activate', {
        confirm: true,
        paper_trading: false
      })
      expect(store.strategies[0].status).toBe('waiting')
      expect(result.status).toBe('waiting')
    })

    it('activates in paper trading mode', async () => {
      api.post.mockResolvedValue({
        data: { data: { ...mockStrategy, status: 'waiting' } }
      })

      await store.activateStrategy(1, { paperTrading: true })

      expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1/activate', {
        confirm: true,
        paper_trading: true
      })
    })
  })

  describe('pauseStrategy', () => {
    it('pauses strategy successfully', async () => {
      const pausedStrategy = { ...mockActiveStrategy, status: 'paused' }
      store.strategies = [{ ...mockActiveStrategy }]
      api.post.mockResolvedValue({
        data: { data: pausedStrategy }
      })

      const result = await store.pauseStrategy(2)

      expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies/2/pause')
      expect(store.strategies[0].status).toBe('paused')
      expect(result.status).toBe('paused')
    })
  })

  describe('resumeStrategy', () => {
    it('resumes strategy successfully', async () => {
      const pausedStrategy = { id: 2, status: 'paused' }
      store.strategies = [pausedStrategy]
      const resumedStrategy = { ...pausedStrategy, status: 'active' }
      api.post.mockResolvedValue({
        data: { data: resumedStrategy }
      })

      const result = await store.resumeStrategy(2)

      expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies/2/resume')
      expect(store.strategies[0].status).toBe('active')
      expect(result.status).toBe('active')
    })
  })

  describe('cloneStrategy', () => {
    it('clones strategy successfully', async () => {
      const clonedStrategy = { id: 10, name: 'Test Strategy (Copy)', status: 'draft' }
      api.post.mockResolvedValue({
        data: { data: clonedStrategy }
      })

      const result = await store.cloneStrategy(1)

      expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1/clone', {
        new_name: null,
        reset_schedule: true
      })
      expect(store.strategies[0]).toEqual(clonedStrategy)
      expect(result).toEqual(clonedStrategy)
    })

    it('clones with custom name', async () => {
      const clonedStrategy = { id: 10, name: 'Custom Name', status: 'draft' }
      api.post.mockResolvedValue({
        data: { data: clonedStrategy }
      })

      await store.cloneStrategy(1, 'Custom Name')

      expect(api.post).toHaveBeenCalledWith('/api/v1/autopilot/strategies/1/clone', {
        new_name: 'Custom Name',
        reset_schedule: true
      })
    })
  })
})


// =============================================================================
// DASHBOARD TESTS
// =============================================================================

describe('AutoPilot Store - Dashboard', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  it('fetches dashboard summary successfully', async () => {
    api.get.mockResolvedValue({
      data: { data: mockDashboardSummary }
    })

    const result = await store.fetchDashboardSummary()

    expect(api.get).toHaveBeenCalledWith('/api/v1/autopilot/dashboard/summary')
    expect(store.dashboardSummary).toEqual(mockDashboardSummary)
    expect(result).toEqual(mockDashboardSummary)
  })

  it('handles dashboard fetch error', async () => {
    api.get.mockRejectedValue({
      response: { data: { detail: 'Unauthorized' } }
    })

    await expect(store.fetchDashboardSummary()).rejects.toBeDefined()
    expect(store.error).toBe('Unauthorized')
  })
})


// =============================================================================
// SETTINGS TESTS
// =============================================================================

describe('AutoPilot Store - Settings', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  it('fetches settings successfully', async () => {
    api.get.mockResolvedValue({
      data: { data: mockSettings }
    })

    const result = await store.fetchSettings()

    expect(api.get).toHaveBeenCalledWith('/api/v1/autopilot/settings')
    expect(store.settings).toEqual(mockSettings)
    expect(result).toEqual(mockSettings)
  })

  it('updates settings successfully', async () => {
    const updatedSettings = { ...mockSettings, max_daily_loss: 20000 }
    api.put.mockResolvedValue({
      data: { data: updatedSettings }
    })

    const result = await store.updateSettings({ max_daily_loss: 20000 })

    expect(api.put).toHaveBeenCalledWith('/api/v1/autopilot/settings', { max_daily_loss: 20000 })
    expect(store.settings).toEqual(updatedSettings)
    expect(result.max_daily_loss).toBe(20000)
  })
})


// =============================================================================
// BUILDER TESTS
// =============================================================================

describe('AutoPilot Store - Builder', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  describe('initBuilder', () => {
    it('initializes with empty strategy', () => {
      store.builder.step = 3
      store.initBuilder()

      expect(store.builder.step).toBe(1)
      expect(store.builder.strategy.name).toBe('')
      expect(store.builder.strategy.underlying).toBe('NIFTY')
      expect(store.builder.validation).toEqual({})
    })

    it('initializes with provided strategy', () => {
      store.initBuilder({ ...mockStrategy, name: 'Test' })

      expect(store.builder.strategy.name).toBe('Test')
      expect(store.builder.strategy.id).toBe(1)
    })
  })

  describe('setBuilderStep', () => {
    it('sets builder step', () => {
      store.setBuilderStep(3)
      expect(store.builder.step).toBe(3)
    })
  })

  describe('updateBuilderStrategy', () => {
    it('updates builder strategy fields', () => {
      store.updateBuilderStrategy({
        name: 'Updated',
        underlying: 'BANKNIFTY'
      })

      expect(store.builder.strategy.name).toBe('Updated')
      expect(store.builder.strategy.underlying).toBe('BANKNIFTY')
    })

    it('preserves other fields', () => {
      store.builder.strategy.lots = 5
      store.updateBuilderStrategy({ name: 'New Name' })

      expect(store.builder.strategy.lots).toBe(5)
    })
  })

  describe('Leg Management', () => {
    it('adds leg with generated ID', () => {
      store.addLeg({
        option_type: 'CE',
        strike_method: 'atm_offset',
        transaction_type: 'BUY'
      })

      expect(store.builder.strategy.legs_config).toHaveLength(1)
      expect(store.builder.strategy.legs_config[0].option_type).toBe('CE')
      expect(store.builder.strategy.legs_config[0].id).toMatch(/^leg_\d+$/)
    })

    it('updates leg at index', () => {
      store.addLeg({ option_type: 'CE' })
      store.updateLeg(0, { option_type: 'PE' })

      expect(store.builder.strategy.legs_config[0].option_type).toBe('PE')
    })

    it('does not update leg at invalid index', () => {
      store.updateLeg(99, { option_type: 'PE' })
      expect(store.builder.strategy.legs_config).toHaveLength(0)
    })

    it('removes leg at index', () => {
      store.addLeg({ option_type: 'CE' })
      store.addLeg({ option_type: 'PE' })
      store.removeLeg(0)

      expect(store.builder.strategy.legs_config).toHaveLength(1)
      expect(store.builder.strategy.legs_config[0].option_type).toBe('PE')
    })
  })

  describe('Condition Management', () => {
    it('adds condition with generated ID and enabled flag', () => {
      store.addCondition({
        variable: 'TIME.CURRENT',
        operator: 'greater_than',
        value: '09:30'
      })

      const condition = store.builder.strategy.entry_conditions.conditions[0]
      expect(condition.id).toMatch(/^cond_\d+$/)
      expect(condition.enabled).toBe(true)
      expect(condition.variable).toBe('TIME.CURRENT')
    })

    it('updates condition at index', () => {
      store.addCondition({ variable: 'TIME.CURRENT' })
      store.updateCondition(0, { variable: 'SPOT' })

      expect(store.builder.strategy.entry_conditions.conditions[0].variable).toBe('SPOT')
    })

    it('does not update condition at invalid index', () => {
      store.updateCondition(99, { variable: 'SPOT' })
      expect(store.builder.strategy.entry_conditions.conditions).toHaveLength(0)
    })

    it('removes condition at index', () => {
      store.addCondition({ variable: 'TIME.CURRENT' })
      store.addCondition({ variable: 'SPOT' })
      store.removeCondition(0)

      expect(store.builder.strategy.entry_conditions.conditions).toHaveLength(1)
      expect(store.builder.strategy.entry_conditions.conditions[0].variable).toBe('SPOT')
    })
  })
})


// =============================================================================
// HELPER ACTIONS TESTS
// =============================================================================

describe('AutoPilot Store - Helper Actions', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  describe('updateStrategyInList', () => {
    it('updates strategy in list', () => {
      store.strategies = [{ id: 1, name: 'Old' }]
      store.updateStrategyInList(1, { id: 1, name: 'New' })

      expect(store.strategies[0].name).toBe('New')
    })

    it('updates currentStrategy if same ID', () => {
      store.strategies = [{ id: 1, name: 'Old' }]
      store.currentStrategy = { id: 1, name: 'Old' }
      store.updateStrategyInList(1, { id: 1, name: 'New' })

      expect(store.currentStrategy.name).toBe('New')
    })

    it('does not crash if strategy not found', () => {
      store.strategies = [{ id: 1, name: 'Test' }]
      store.updateStrategyInList(999, { id: 999, name: 'New' })

      expect(store.strategies[0].name).toBe('Test')
    })
  })

  describe('setFilters', () => {
    it('sets filter values', () => {
      store.setFilters({ status: 'active' })

      expect(store.filters.status).toBe('active')
      expect(store.filters.underlying).toBeNull()
    })

    it('merges with existing filters', () => {
      store.setFilters({ status: 'active' })
      store.setFilters({ underlying: 'NIFTY' })

      expect(store.filters.status).toBe('active')
      expect(store.filters.underlying).toBe('NIFTY')
    })
  })

  describe('clearFilters', () => {
    it('resets filters to null', () => {
      store.filters = { status: 'active', underlying: 'NIFTY' }
      store.clearFilters()

      expect(store.filters.status).toBeNull()
      expect(store.filters.underlying).toBeNull()
    })
  })

  describe('clearError', () => {
    it('clears error message', () => {
      store.error = 'Some error'
      store.clearError()

      expect(store.error).toBeNull()
    })
  })
})


// =============================================================================
// ERROR HANDLING TESTS
// =============================================================================

describe('AutoPilot Store - Error Handling', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
    vi.clearAllMocks()
  })

  it('extracts error from response.data.detail', async () => {
    api.get.mockRejectedValue({
      response: { data: { detail: 'Detailed error message' } }
    })

    await expect(store.fetchStrategies()).rejects.toBeDefined()
    expect(store.error).toBe('Detailed error message')
  })

  it('falls back to error.message', async () => {
    api.get.mockRejectedValue({
      message: 'Network error'
    })

    await expect(store.fetchStrategies()).rejects.toBeDefined()
    expect(store.error).toBe('Network error')
  })

  it('clears error before each action', async () => {
    store.error = 'Previous error'
    api.get.mockResolvedValue({
      data: { data: [], page: 1, page_size: 20, total: 0, total_pages: 0 }
    })

    await store.fetchStrategies()
    expect(store.error).toBeNull()
  })
})


// =============================================================================
// EMPTY STRATEGY HELPER TESTS
// =============================================================================

describe('AutoPilot Store - Empty Strategy Factory', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAutopilotStore()
  })

  it('creates strategy with correct defaults', () => {
    store.initBuilder()
    const strategy = store.builder.strategy

    // Basic fields
    expect(strategy.name).toBe('')
    expect(strategy.description).toBe('')
    expect(strategy.underlying).toBe('NIFTY')
    expect(strategy.expiry_type).toBe('current_week')
    expect(strategy.lots).toBe(1)
    expect(strategy.position_type).toBe('intraday')
    expect(strategy.priority).toBe(100)

    // Entry conditions
    expect(strategy.entry_conditions.logic).toBe('AND')
    expect(strategy.entry_conditions.conditions).toEqual([])

    // Order settings
    expect(strategy.order_settings.order_type).toBe('MARKET')
    expect(strategy.order_settings.execution_style).toBe('sequential')
    expect(strategy.order_settings.delay_between_legs).toBe(2)
    expect(strategy.order_settings.on_leg_failure).toBe('stop')

    // Slippage protection
    expect(strategy.order_settings.slippage_protection.enabled).toBe(true)
    expect(strategy.order_settings.slippage_protection.max_per_leg_pct).toBe(2.0)
    expect(strategy.order_settings.slippage_protection.max_total_pct).toBe(5.0)

    // Risk settings
    expect(strategy.risk_settings.max_loss).toBeNull()
    expect(strategy.risk_settings.trailing_stop.enabled).toBe(false)

    // Schedule config
    expect(strategy.schedule_config.activation_mode).toBe('always')
    expect(strategy.schedule_config.active_days).toEqual(['MON', 'TUE', 'WED', 'THU', 'FRI'])
    expect(strategy.schedule_config.start_time).toBe('09:15')
    expect(strategy.schedule_config.end_time).toBe('15:30')
  })
})
