/**
 * usePositionLegs Composable - Phase 5D
 *
 * Manages position legs for AutoPilot strategies.
 * Handles leg actions (exit, shift, roll, break) and Greeks updates.
 */
import { ref, computed } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import api from '@/services/api'

export function usePositionLegs(strategyId) {
  const autopilotStore = useAutopilotStore()

  // State
  const legs = ref([])
  const loading = ref(false)
  const error = ref(null)
  const selectedLeg = ref(null)

  // Action modals state
  const exitModal = ref({
    visible: false,
    legId: null,
    executionMode: 'market',
    limitPrice: null,
    loading: false
  })

  const shiftModal = ref({
    visible: false,
    legId: null,
    targetStrike: null,
    targetDelta: null,
    shiftDirection: null,
    shiftAmount: null,
    executionMode: 'market',
    loading: false
  })

  const rollModal = ref({
    visible: false,
    legId: null,
    targetExpiry: null,
    targetStrike: null,
    executionMode: 'market',
    loading: false
  })

  const breakTradeModal = ref({
    visible: false,
    legId: null,
    executionMode: 'market',
    newPositions: 'auto',
    premiumSplit: 'equal',
    preferRoundStrikes: true,
    maxDelta: 0.30,
    simulation: null,
    loading: false
  })

  /**
   * Fetch all legs for strategy
   */
  const fetchLegs = async (statusFilter = null) => {
    if (!strategyId) {
      return
    }

    try {
      loading.value = true
      error.value = null

      const params = statusFilter ? { status_filter: statusFilter } : {}

      const response = await api.get(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs`,
        { params }
      )

      if (response.data.success && response.data.data) {
        legs.value = response.data.data
      }
    } catch (err) {
      console.error('Error fetching position legs:', err)
      error.value = err.response?.data?.message || 'Failed to fetch position legs'
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch single leg details
   */
  const fetchLeg = async (legId) => {
    if (!strategyId || !legId) {
      return null
    }

    try {
      const response = await api.get(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/${legId}`
      )

      if (response.data.success && response.data.data) {
        return response.data.data
      }
    } catch (err) {
      console.error('Error fetching leg:', err)
      error.value = err.response?.data?.message || 'Failed to fetch leg'
    }

    return null
  }

  /**
   * Exit a position leg
   */
  const exitLeg = async (legId, executionMode = 'market', limitPrice = null) => {
    if (!strategyId || !legId) {
      return { success: false, error: 'Invalid parameters' }
    }

    try {
      exitModal.value.loading = true

      const response = await api.post(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/${legId}/exit`,
        {
          execution_mode: executionMode,
          limit_price: limitPrice
        }
      )

      if (response.data.success) {
        // Refresh legs
        await fetchLegs()

        // Close modal
        exitModal.value.visible = false

        return { success: true, data: response.data.data }
      }
    } catch (err) {
      console.error('Error exiting leg:', err)
      return {
        success: false,
        error: err.response?.data?.message || 'Failed to exit leg'
      }
    } finally {
      exitModal.value.loading = false
    }

    return { success: false }
  }

  /**
   * Shift a position leg
   */
  const shiftLeg = async (params) => {
    if (!strategyId || !params.legId) {
      return { success: false, error: 'Invalid parameters' }
    }

    try {
      shiftModal.value.loading = true

      const response = await api.post(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/${params.legId}/shift`,
        {
          target_strike: params.targetStrike,
          target_delta: params.targetDelta,
          shift_direction: params.shiftDirection,
          shift_amount: params.shiftAmount,
          execution_mode: params.executionMode || 'market',
          limit_offset: params.limitOffset || 1.0
        }
      )

      if (response.data.success) {
        await fetchLegs()
        shiftModal.value.visible = false
        return { success: true, data: response.data.data }
      }
    } catch (err) {
      console.error('Error shifting leg:', err)
      return {
        success: false,
        error: err.response?.data?.message || 'Failed to shift leg'
      }
    } finally {
      shiftModal.value.loading = false
    }

    return { success: false }
  }

  /**
   * Roll a position leg
   */
  const rollLeg = async (params) => {
    if (!strategyId || !params.legId || !params.targetExpiry) {
      return { success: false, error: 'Invalid parameters' }
    }

    try {
      rollModal.value.loading = true

      const response = await api.post(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/${params.legId}/roll`,
        {
          target_expiry: params.targetExpiry,
          target_strike: params.targetStrike,
          execution_mode: params.executionMode || 'market'
        }
      )

      if (response.data.success) {
        await fetchLegs()
        rollModal.value.visible = false
        return { success: true, data: response.data.data }
      }
    } catch (err) {
      console.error('Error rolling leg:', err)
      return {
        success: false,
        error: err.response?.data?.message || 'Failed to roll leg'
      }
    } finally {
      rollModal.value.loading = false
    }

    return { success: false }
  }

  /**
   * Execute break trade
   */
  const breakTrade = async (params) => {
    if (!strategyId || !params.legId) {
      return { success: false, error: 'Invalid parameters' }
    }

    try {
      breakTradeModal.value.loading = true

      const response = await api.post(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/${params.legId}/break`,
        {
          execution_mode: params.executionMode || 'market',
          new_positions: params.newPositions || 'auto',
          new_put_strike: params.newPutStrike,
          new_call_strike: params.newCallStrike,
          premium_split: params.premiumSplit || 'equal',
          prefer_round_strikes: params.preferRoundStrikes !== false,
          max_delta: params.maxDelta || 0.30
        }
      )

      if (response.data.success) {
        await fetchLegs()
        breakTradeModal.value.visible = false
        return { success: true, data: response.data.data }
      }
    } catch (err) {
      console.error('Error executing break trade:', err)
      return {
        success: false,
        error: err.response?.data?.message || 'Failed to execute break trade'
      }
    } finally {
      breakTradeModal.value.loading = false
    }

    return { success: false }
  }

  /**
   * Simulate break trade
   */
  const simulateBreakTrade = async (legId, premiumSplit = 'equal', preferRoundStrikes = true, maxDelta = 0.30) => {
    if (!strategyId || !legId) {
      return null
    }

    try {
      const response = await api.post(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/${legId}/break/simulate`,
        null,
        {
          params: {
            premium_split: premiumSplit,
            prefer_round_strikes: preferRoundStrikes,
            max_delta: maxDelta
          }
        }
      )

      if (response.data.success && response.data.data) {
        return response.data.data
      }
    } catch (err) {
      console.error('Error simulating break trade:', err)
      error.value = err.response?.data?.message || 'Failed to simulate break trade'
    }

    return null
  }

  /**
   * Update Greeks for all legs
   */
  const updateAllGreeks = async () => {
    if (!strategyId) {
      return { success: false, error: 'Invalid strategy ID' }
    }

    try {
      const response = await api.post(
        `/api/v1/autopilot/legs/strategies/${strategyId}/legs/update-greeks`
      )

      if (response.data.success) {
        await fetchLegs()
        return { success: true, data: response.data.data }
      }
    } catch (err) {
      console.error('Error updating Greeks:', err)
      return {
        success: false,
        error: err.response?.data?.message || 'Failed to update Greeks'
      }
    }

    return { success: false }
  }

  /**
   * Open exit modal for leg
   */
  const openExitModal = (legId) => {
    exitModal.value = {
      visible: true,
      legId,
      executionMode: 'market',
      limitPrice: null,
      loading: false
    }
  }

  /**
   * Open shift modal for leg
   */
  const openShiftModal = (legId) => {
    shiftModal.value = {
      visible: true,
      legId,
      targetStrike: null,
      targetDelta: null,
      shiftDirection: null,
      shiftAmount: null,
      executionMode: 'market',
      loading: false
    }
  }

  /**
   * Open roll modal for leg
   */
  const openRollModal = (legId) => {
    rollModal.value = {
      visible: true,
      legId,
      targetExpiry: null,
      targetStrike: null,
      executionMode: 'market',
      loading: false
    }
  }

  /**
   * Open break trade modal for leg
   */
  const openBreakTradeModal = async (legId) => {
    breakTradeModal.value = {
      visible: true,
      legId,
      executionMode: 'market',
      newPositions: 'auto',
      premiumSplit: 'equal',
      preferRoundStrikes: true,
      maxDelta: 0.30,
      simulation: null,
      loading: false
    }

    // Auto-load simulation
    const simulation = await simulateBreakTrade(legId)
    if (simulation) {
      breakTradeModal.value.simulation = simulation
    }
  }

  /**
   * Close all modals
   */
  const closeModals = () => {
    exitModal.value.visible = false
    shiftModal.value.visible = false
    rollModal.value.visible = false
    breakTradeModal.value.visible = false
  }

  // Computed properties
  const openLegs = computed(() => {
    return legs.value.filter(leg => leg.status === 'open')
  })

  const closedLegs = computed(() => {
    return legs.value.filter(leg => leg.status === 'closed')
  })

  const totalUnrealizedPnL = computed(() => {
    return openLegs.value.reduce((sum, leg) => sum + (leg.unrealized_pnl || 0), 0)
  })

  const totalRealizedPnL = computed(() => {
    return closedLegs.value.reduce((sum, leg) => sum + (leg.realized_pnl || 0), 0)
  })

  const netDelta = computed(() => {
    return openLegs.value.reduce((sum, leg) => sum + (leg.delta || 0), 0)
  })

  const netTheta = computed(() => {
    return openLegs.value.reduce((sum, leg) => sum + (leg.theta || 0), 0)
  })

  const netGamma = computed(() => {
    return openLegs.value.reduce((sum, leg) => sum + (leg.gamma || 0), 0)
  })

  const netVega = computed(() => {
    return openLegs.value.reduce((sum, leg) => sum + (leg.vega || 0), 0)
  })

  return {
    // State
    legs,
    loading,
    error,
    selectedLeg,
    exitModal,
    shiftModal,
    rollModal,
    breakTradeModal,

    // Computed
    openLegs,
    closedLegs,
    totalUnrealizedPnL,
    totalRealizedPnL,
    netDelta,
    netTheta,
    netGamma,
    netVega,

    // Methods
    fetchLegs,
    fetchLeg,
    exitLeg,
    shiftLeg,
    rollLeg,
    breakTrade,
    simulateBreakTrade,
    updateAllGreeks,
    openExitModal,
    openShiftModal,
    openRollModal,
    openBreakTradeModal,
    closeModals
  }
}
