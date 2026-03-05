/**
 * WebSocket Composable for AutoPilot
 *
 * Manages WebSocket connection for real-time updates.
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAutopilotStore } from '@/stores/autopilot'
import { startPollingFallback, stopPollingFallback } from '@/services/priceService'
import api from '@/services/api'

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001'

// Shared state across all component instances
const socket = ref(null)
const isConnected = ref(false)
const reconnectAttempts = ref(0)
const lastMessage = ref(null)
const notifications = ref([])

const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_DELAY = 3000
const MAX_NOTIFICATIONS = 50

let reconnectTimer = null
let pingInterval = null
let isInitialized = false

export function useWebSocket() {
  const authStore = useAuthStore()
  const autopilotStore = useAutopilotStore()

  const connectionStatus = computed(() => {
    if (isConnected.value) return 'connected'
    if (reconnectAttempts.value > 0) return 'reconnecting'
    return 'disconnected'
  })

  /**
   * Connect to WebSocket server
   */
  function connect() {
    if (socket.value?.readyState === WebSocket.OPEN) {
      return
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      console.warn('[AutoPilot WS] No auth token, cannot connect')
      return
    }

    const wsUrl = `${WS_BASE_URL}/ws/autopilot?token=${token}`

    try {
      socket.value = new WebSocket(wsUrl)

      socket.value.onopen = handleOpen
      socket.value.onclose = handleClose
      socket.value.onerror = handleError
      socket.value.onmessage = handleMessage

    } catch (error) {
      console.error('[AutoPilot WS] Connection error:', error)
      scheduleReconnect()
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }

    // Stop polling fallback
    stopPollingFallback()

    if (socket.value) {
      socket.value.close(1000, 'User disconnected')
      socket.value = null
    }

    isConnected.value = false
    reconnectAttempts.value = 0
  }

  /**
   * Send message to server
   */
  function send(type, data = {}) {
    if (socket.value?.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify({ type, data }))
    } else {
      console.warn('[AutoPilot WS] Cannot send - not connected')
    }
  }

  /**
   * Subscribe to strategy updates
   */
  function subscribeToStrategy(strategyId) {
    send('subscribe', { strategy_id: strategyId })
  }

  /**
   * Unsubscribe from strategy updates
   */
  function unsubscribeFromStrategy(strategyId) {
    send('unsubscribe', { strategy_id: strategyId })
  }

  /**
   * Clear notifications
   */
  function clearNotifications() {
    notifications.value = []
  }

  /**
   * Remove a specific notification
   */
  function removeNotification(index) {
    notifications.value.splice(index, 1)
  }

  // ========================================================================
  // Event Handlers
  // ========================================================================

  function handleOpen() {
    console.log('[AutoPilot WS] Connected')
    isConnected.value = true
    reconnectAttempts.value = 0

    // Stop polling fallback since WebSocket is now connected
    stopPollingFallback()

    // Start ping interval
    pingInterval = setInterval(() => {
      send('ping')
    }, 25000)
  }

  function handleClose(event) {
    console.log('[AutoPilot WS] Closed:', event.code, event.reason)
    isConnected.value = false

    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }

    // Reconnect if not intentional close
    if (event.code !== 1000) {
      scheduleReconnect()
    }
  }

  function handleError(error) {
    console.error('[AutoPilot WS] Error:', error)
  }

  function handleMessage(event) {
    try {
      const message = JSON.parse(event.data)
      const { type, data, timestamp } = message

      lastMessage.value = { type, data, timestamp }

      switch (type) {
        case 'connected':
          console.log('[AutoPilot WS] Server confirmed connection:', data.message)
          break

        case 'pong':
          // Heartbeat response - no action needed
          break

        case 'heartbeat':
          // Server heartbeat - no action needed
          break

        case 'strategy_update':
          handleStrategyUpdate(data)
          break

        case 'strategy_status_changed':
          handleStatusChange(data)
          break

        case 'order_placed':
        case 'order_filled':
        case 'order_rejected':
          handleOrderEvent(type, data)
          break

        case 'pnl_update':
          handlePnLUpdate(data)
          break

        case 'condition_evaluated':
        case 'conditions_met':
          handleConditionUpdate(data)
          break

        case 'risk_alert':
          handleRiskAlert(data)
          break

        case 'market_status':
          handleMarketStatus(data)
          break

        case 'error':
          console.error('[AutoPilot WS] Server error:', data.message)
          addNotification('Error', data.message, 'error')
          break

        default:
          console.log('[AutoPilot WS] Unknown message type:', type, data)
      }

    } catch (error) {
      console.error('[AutoPilot WS] Error parsing message:', error)
    }
  }

  // ========================================================================
  // Message Handlers
  // ========================================================================

  function handleStrategyUpdate(data) {
    const { strategy_id, ...updates } = data

    // Update strategy in store
    const currentStrategies = autopilotStore.strategies
    const index = currentStrategies.findIndex(s => s.id === strategy_id)
    if (index !== -1) {
      autopilotStore.strategies[index] = {
        ...currentStrategies[index],
        ...updates
      }
    }

    // Update current strategy if viewing
    if (autopilotStore.currentStrategy?.id === strategy_id) {
      autopilotStore.currentStrategy = {
        ...autopilotStore.currentStrategy,
        ...updates
      }
    }
  }

  function handleStatusChange(data) {
    const { strategy_id, old_status, new_status, reason } = data

    // Update strategy status in store
    handleStrategyUpdate({ strategy_id, status: new_status })

    // Show notification
    const title = 'Strategy Status Changed'
    const message = `${old_status} → ${new_status}${reason ? `: ${reason}` : ''}`
    const type = new_status === 'error' ? 'error' :
                 new_status === 'active' ? 'success' :
                 new_status === 'completed' ? 'info' : 'info'

    addNotification(title, message, type)

    // Refresh dashboard summary
    autopilotStore.fetchDashboardSummary().catch(console.error)
  }

  function handleOrderEvent(eventType, data) {
    const { strategy_id, order_id, ...orderData } = data

    let title, message, type

    switch (eventType) {
      case 'order_placed':
        title = 'Order Placed'
        message = `${orderData.transaction_type || ''} ${orderData.quantity || ''} ${orderData.tradingsymbol || ''}`
        type = 'info'
        break

      case 'order_filled':
        title = 'Order Filled'
        message = `${orderData.tradingsymbol || ''} @ ${orderData.executed_price || ''}`
        type = 'success'
        break

      case 'order_rejected':
        title = 'Order Rejected'
        message = orderData.rejection_reason || orderData.message || 'Unknown reason'
        type = 'error'
        break

      default:
        return
    }

    addNotification(title, message, type)
  }

  function handlePnLUpdate(data) {
    const { strategy_id, realized_pnl, unrealized_pnl, total_pnl } = data

    // Update strategy in list
    const currentStrategies = autopilotStore.strategies
    const index = currentStrategies.findIndex(s => s.id === strategy_id)
    if (index !== -1) {
      autopilotStore.strategies[index] = {
        ...currentStrategies[index],
        runtime_state: {
          ...currentStrategies[index].runtime_state,
          realized_pnl,
          unrealized_pnl,
          current_pnl: total_pnl
        }
      }
    }

    // Update current strategy if viewing
    if (autopilotStore.currentStrategy?.id === strategy_id) {
      autopilotStore.currentStrategy = {
        ...autopilotStore.currentStrategy,
        runtime_state: {
          ...autopilotStore.currentStrategy?.runtime_state,
          realized_pnl,
          unrealized_pnl,
          current_pnl: total_pnl
        }
      }
    }
  }

  function handleConditionUpdate(data) {
    const { strategy_id, conditions_met, condition_states } = data

    // Update builder state if viewing this strategy
    if (autopilotStore.currentStrategy?.id === strategy_id) {
      autopilotStore.updateBuilderStrategy({
        _conditionStates: condition_states,
        _conditionsMet: conditions_met
      })
    }

    // Show notification when conditions are met
    if (conditions_met) {
      addNotification(
        'Conditions Met!',
        'Strategy conditions satisfied, executing entry...',
        'success'
      )
    }
  }

  function handleRiskAlert(data) {
    const { alert_type, message } = data
    addNotification('Risk Alert', message, 'warning')
  }

  function handleMarketStatus(data) {
    const { is_open, message } = data
    // Could emit event or update a market status store
    console.log('[AutoPilot WS] Market status:', is_open ? 'Open' : 'Closed', message)
  }

  // ========================================================================
  // Helpers
  // ========================================================================

  /**
   * Poll AutoPilot data via API as fallback when WebSocket is unavailable
   */
  async function pollAutopilotData() {
    try {
      const response = await api.get('/api/v1/autopilot/strategies', {
        params: { status: 'active,waiting' }
      })
      if (response.data?.data) {
        response.data.data.forEach(strategy => {
          handleStrategyUpdate({ strategy_id: strategy.id, ...strategy })
        })
      }
    } catch (error) {
      console.error('[AutoPilot WS] Polling error:', error)
    }
  }

  function scheduleReconnect() {
    if (reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS) {
      console.log('[AutoPilot WS] Max reconnect attempts reached')
      addNotification(
        'Connection Lost',
        'Unable to reconnect to AutoPilot server. Please refresh the page.',
        'error'
      )
      // Start polling fallback when WebSocket reconnect fails
      startPollingFallback(pollAutopilotData, 10000)
      return
    }

    reconnectAttempts.value++
    const delay = RECONNECT_DELAY * reconnectAttempts.value

    console.log(`[AutoPilot WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value})`)

    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  function addNotification(title, message, type = 'info') {
    const notification = {
      id: Date.now(),
      title,
      message,
      type,
      timestamp: new Date().toISOString(),
      read: false
    }

    notifications.value.unshift(notification)

    // Keep only last N notifications
    if (notifications.value.length > MAX_NOTIFICATIONS) {
      notifications.value = notifications.value.slice(0, MAX_NOTIFICATIONS)
    }

    // Emit custom event for notification component
    window.dispatchEvent(new CustomEvent('autopilot-notification', {
      detail: notification
    }))
  }

  // ========================================================================
  // Lifecycle
  // ========================================================================

  onMounted(() => {
    // Only connect once across all component instances
    if (!isInitialized && authStore.isAuthenticated) {
      isInitialized = true
      connect()
    }
  })

  onUnmounted(() => {
    // Don't disconnect on component unmount - keep connection alive
    // Only disconnect on explicit logout
  })

  return {
    // State
    isConnected,
    connectionStatus,
    reconnectAttempts,
    lastMessage,
    notifications,

    // Methods
    connect,
    disconnect,
    send,
    subscribeToStrategy,
    unsubscribeFromStrategy,
    clearNotifications,
    removeNotification
  }
}

/**
 * Force disconnect WebSocket (call on logout)
 */
export function disconnectAutopilotWebSocket() {
  if (socket.value) {
    socket.value.close(1000, 'User logged out')
    socket.value = null
  }
  isConnected.value = false
  reconnectAttempts.value = 0
  isInitialized = false

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (pingInterval) {
    clearInterval(pingInterval)
    pingInterval = null
  }

  // Stop polling fallback
  stopPollingFallback()
}
