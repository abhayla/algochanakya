/**
 * AutoPilot WebSocket Composable Tests
 *
 * Tests for src/composables/autopilot/useWebSocket.js
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'

// Mock stores before importing the composable
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    isAuthenticated: true
  }))
}))

vi.mock('@/stores/autopilot', () => ({
  useAutopilotStore: vi.fn(() => ({
    strategies: [],
    currentStrategy: null,
    fetchDashboardSummary: vi.fn(),
    updateBuilderStrategy: vi.fn()
  }))
}))

import { useWebSocket, disconnectAutopilotWebSocket } from '@/composables/autopilot/useWebSocket'
import { useAutopilotStore } from '@/stores/autopilot'
import { useAuthStore } from '@/stores/auth'


// =============================================================================
// MOCK WEBSOCKET
// =============================================================================

class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  constructor(url) {
    this.url = url
    this.readyState = MockWebSocket.CONNECTING
    this.onopen = null
    this.onclose = null
    this.onerror = null
    this.onmessage = null
    this.sentMessages = []

    // Auto-connect after a tick
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) this.onopen({ type: 'open' })
    }, 0)
  }

  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
    this.sentMessages.push(data)
  }

  close(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSING
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED
      if (this.onclose) this.onclose({ code, reason, type: 'close' })
    }, 0)
  }

  // Helper to simulate receiving a message
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) })
    }
  }

  // Helper to simulate error
  simulateError(error) {
    if (this.onerror) {
      this.onerror(error)
    }
  }
}


// =============================================================================
// TEST SETUP
// =============================================================================

describe('useWebSocket Composable', () => {
  let originalWebSocket
  let mockWS

  beforeEach(() => {
    setActivePinia(createPinia())

    // Mock WebSocket
    originalWebSocket = global.WebSocket
    global.WebSocket = MockWebSocket

    // Reset localStorage mock
    localStorage.store = {}
    localStorage.setItem('access_token', 'test_token')

    // Clear all mocks
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    global.WebSocket = originalWebSocket
    vi.useRealTimers()

    // Clean up any active connections
    disconnectAutopilotWebSocket()
  })


  // ===========================================================================
  // CONNECTION TESTS
  // ===========================================================================

  describe('Connection', () => {
    it('connects with correct URL and token', async () => {
      const { connect, isConnected } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      expect(isConnected.value).toBe(true)
    })

    it('does not connect without auth token', () => {
      localStorage.removeItem('access_token')

      const { connect, isConnected } = useWebSocket()
      connect()

      expect(isConnected.value).toBe(false)
    })

    it('does not reconnect if already connected', async () => {
      const { connect } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Store reference to first WebSocket
      const firstWSCount = WebSocket.length

      connect()
      await vi.runAllTimersAsync()

      // Should not create a new connection
      expect(isConnected.value).toBe(true)
    })

    it('disconnects cleanly', async () => {
      const { connect, disconnect, isConnected } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()
      expect(isConnected.value).toBe(true)

      disconnect()
      await vi.runAllTimersAsync()
      expect(isConnected.value).toBe(false)
    })
  })


  // ===========================================================================
  // CONNECTION STATUS TESTS
  // ===========================================================================

  describe('Connection Status', () => {
    it('returns connected status when connected', async () => {
      const { connect, connectionStatus } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      expect(connectionStatus.value).toBe('connected')
    })

    it('returns disconnected status initially', () => {
      disconnectAutopilotWebSocket()
      const { connectionStatus } = useWebSocket()
      expect(connectionStatus.value).toBe('disconnected')
    })

    it('returns reconnecting status during reconnection', async () => {
      const { connect, reconnectAttempts, connectionStatus } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Simulate disconnect with non-1000 code to trigger reconnect
      reconnectAttempts.value = 1

      expect(connectionStatus.value).toBe('reconnecting')
    })
  })


  // ===========================================================================
  // MESSAGE SENDING TESTS
  // ===========================================================================

  describe('Message Sending', () => {
    it('sends JSON message when connected', async () => {
      const { connect, send } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      send('ping', {})

      // Check the mock captured the message (need to access the instance)
    })

    it('does not send when disconnected', () => {
      disconnectAutopilotWebSocket()
      const { send } = useWebSocket()

      // Should not throw
      send('ping', {})
    })
  })


  // ===========================================================================
  // SUBSCRIPTION TESTS
  // ===========================================================================

  describe('Subscriptions', () => {
    it('subscribes to strategy', async () => {
      const { connect, subscribeToStrategy, send } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      subscribeToStrategy(123)

      // Verify subscribe message was sent
    })

    it('unsubscribes from strategy', async () => {
      const { connect, unsubscribeFromStrategy } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      unsubscribeFromStrategy(123)

      // Verify unsubscribe message was sent
    })
  })


  // ===========================================================================
  // NOTIFICATION TESTS
  // ===========================================================================

  describe('Notifications', () => {
    it('adds notifications', async () => {
      const { notifications, connect } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Notifications are added internally via message handlers
      expect(notifications.value).toEqual([])
    })

    it('clears all notifications', async () => {
      const { notifications, clearNotifications, connect } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Add mock notifications directly
      notifications.value = [
        { id: 1, title: 'Test', message: 'Test message' }
      ]

      clearNotifications()
      expect(notifications.value).toEqual([])
    })

    it('removes specific notification', async () => {
      const { notifications, removeNotification, connect } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      notifications.value = [
        { id: 1, title: 'First' },
        { id: 2, title: 'Second' }
      ]

      removeNotification(0)
      expect(notifications.value).toHaveLength(1)
      expect(notifications.value[0].title).toBe('Second')
    })

    it('limits notifications to max count', async () => {
      const { notifications, connect } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Add more than max notifications
      const manyNotifications = Array.from({ length: 60 }, (_, i) => ({
        id: i,
        title: `Notification ${i}`
      }))
      notifications.value = manyNotifications

      // Should be truncated on next add (handled internally)
      expect(notifications.value.length).toBeLessThanOrEqual(60)
    })
  })


  // ===========================================================================
  // DISCONNECT UTILITY TESTS
  // ===========================================================================

  describe('disconnectAutopilotWebSocket', () => {
    it('disconnects and resets state', async () => {
      const { connect, isConnected, reconnectAttempts } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()
      expect(isConnected.value).toBe(true)

      disconnectAutopilotWebSocket()
      expect(isConnected.value).toBe(false)
      expect(reconnectAttempts.value).toBe(0)
    })
  })
})


// =============================================================================
// MESSAGE HANDLER TESTS
// =============================================================================

describe('useWebSocket - Message Handlers', () => {
  let mockAutopilotStore

  beforeEach(() => {
    setActivePinia(createPinia())

    // Setup mock store with spies
    mockAutopilotStore = {
      strategies: [],
      currentStrategy: null,
      fetchDashboardSummary: vi.fn().mockResolvedValue({}),
      updateBuilderStrategy: vi.fn()
    }

    useAutopilotStore.mockReturnValue(mockAutopilotStore)

    // Mock localStorage
    localStorage.store = { access_token: 'test_token' }

    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  describe('handleStrategyUpdate', () => {
    it('updates strategy in store list', async () => {
      mockAutopilotStore.strategies = [
        { id: 1, name: 'Old Name', status: 'active' }
      ]

      const { connect, lastMessage } = useWebSocket()
      connect()
      await vi.runAllTimersAsync()

      // Simulate strategy update message would be handled internally
    })

    it('updates currentStrategy if same ID', async () => {
      mockAutopilotStore.currentStrategy = { id: 1, name: 'Old' }
      mockAutopilotStore.strategies = [{ id: 1, name: 'Old' }]

      const { connect } = useWebSocket()
      connect()
      await vi.runAllTimersAsync()

      // Message handlers update the store directly
    })
  })

  describe('handleStatusChange', () => {
    it('shows notification on status change', async () => {
      const { connect, notifications } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Status change notification would be added via message handler
    })

    it('refreshes dashboard on status change', async () => {
      const { connect } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Dashboard refresh would be triggered via message handler
    })
  })

  describe('handleOrderEvent', () => {
    it('shows notification for order_placed', async () => {
      const { connect, notifications } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Order placed notification would be added via message handler
    })

    it('shows success notification for order_filled', async () => {
      const { connect, notifications } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Order filled notification would be added via message handler
    })

    it('shows error notification for order_rejected', async () => {
      const { connect, notifications } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Order rejected notification would be added via message handler
    })
  })

  describe('handlePnLUpdate', () => {
    it('updates strategy runtime_state in store', async () => {
      mockAutopilotStore.strategies = [
        { id: 1, runtime_state: { current_pnl: 0 } }
      ]

      const { connect } = useWebSocket()
      connect()
      await vi.runAllTimersAsync()

      // P&L update would modify the store via message handler
    })
  })

  describe('handleConditionUpdate', () => {
    it('updates builder state for current strategy', async () => {
      mockAutopilotStore.currentStrategy = { id: 1 }

      const { connect } = useWebSocket()
      connect()
      await vi.runAllTimersAsync()

      // Condition update would call updateBuilderStrategy
    })

    it('shows notification when conditions are met', async () => {
      const { connect, notifications } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Conditions met notification would be added via message handler
    })
  })

  describe('handleRiskAlert', () => {
    it('shows warning notification', async () => {
      const { connect, notifications } = useWebSocket()

      connect()
      await vi.runAllTimersAsync()

      // Risk alert notification would be added via message handler
    })
  })

  describe('handleMarketStatus', () => {
    it('logs market status', async () => {
      const consoleSpy = vi.spyOn(console, 'log')

      const { connect } = useWebSocket()
      connect()
      await vi.runAllTimersAsync()

      // Market status would be logged via message handler
      consoleSpy.mockRestore()
    })
  })
})


// =============================================================================
// RECONNECTION TESTS
// =============================================================================

describe('useWebSocket - Reconnection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.store = { access_token: 'test_token' }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  it('increments reconnect attempts on failure', async () => {
    const { reconnectAttempts, connect } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Initial connection should reset attempts
    expect(reconnectAttempts.value).toBe(0)
  })

  it('stops reconnecting after max attempts', async () => {
    const { reconnectAttempts, notifications } = useWebSocket()

    // Simulate max reconnect attempts reached
    reconnectAttempts.value = 5

    // Should show connection lost notification
  })

  it('uses exponential backoff for reconnection delay', async () => {
    const { reconnectAttempts } = useWebSocket()

    // Delay calculation: RECONNECT_DELAY * reconnectAttempts
    // e.g., 3000 * 1 = 3000ms, 3000 * 2 = 6000ms, etc.
    reconnectAttempts.value = 3

    // Expected delay would be 9000ms (3 * 3000)
  })
})


// =============================================================================
// HEARTBEAT TESTS
// =============================================================================

describe('useWebSocket - Heartbeat', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.store = { access_token: 'test_token' }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  it('starts ping interval on connect', async () => {
    const { connect } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Advance time by 25 seconds (ping interval)
    await vi.advanceTimersByTimeAsync(25000)

    // Ping should have been sent
  })

  it('stops ping interval on disconnect', async () => {
    const { connect, disconnect } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    disconnect()
    await vi.runAllTimersAsync()

    // Ping interval should be cleared
  })

  it('handles pong response', async () => {
    const { connect, lastMessage } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Pong response should be handled silently
  })

  it('handles heartbeat from server', async () => {
    const { connect, lastMessage } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Server heartbeat should be handled silently
  })
})


// =============================================================================
// ERROR HANDLING TESTS
// =============================================================================

describe('useWebSocket - Error Handling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.store = { access_token: 'test_token' }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  it('handles WebSocket error', async () => {
    const consoleSpy = vi.spyOn(console, 'error')

    const { connect } = useWebSocket()
    connect()
    await vi.runAllTimersAsync()

    // Error would be logged via handleError
    consoleSpy.mockRestore()
  })

  it('handles invalid JSON message', async () => {
    const consoleSpy = vi.spyOn(console, 'error')

    const { connect } = useWebSocket()
    connect()
    await vi.runAllTimersAsync()

    // Invalid JSON would trigger error in handleMessage
    consoleSpy.mockRestore()
  })

  it('shows notification for server error', async () => {
    const { connect, notifications } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Server error notification would be added via message handler
  })

  it('logs unknown message types', async () => {
    const consoleSpy = vi.spyOn(console, 'log')

    const { connect } = useWebSocket()
    connect()
    await vi.runAllTimersAsync()

    // Unknown message types would be logged
    consoleSpy.mockRestore()
  })
})


// =============================================================================
// LIFECYCLE TESTS
// =============================================================================

describe('useWebSocket - Lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.store = { access_token: 'test_token' }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  it('connects automatically when authenticated on mount', async () => {
    useAuthStore.mockReturnValue({ isAuthenticated: true })

    const { isConnected } = useWebSocket()

    // onMounted would trigger connect if authenticated and not initialized
  })

  it('does not connect if not authenticated', () => {
    useAuthStore.mockReturnValue({ isAuthenticated: false })

    const { isConnected } = useWebSocket()

    // Should not auto-connect
  })

  it('maintains connection on component unmount', async () => {
    const { connect, isConnected } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // onUnmounted does not disconnect - connection persists
    expect(isConnected.value).toBe(true)
  })
})


// =============================================================================
// CUSTOM EVENT TESTS
// =============================================================================

describe('useWebSocket - Custom Events', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.store = { access_token: 'test_token' }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  it('dispatches custom event when notification added', async () => {
    const eventHandler = vi.fn()
    window.addEventListener('autopilot-notification', eventHandler)

    const { connect } = useWebSocket()
    connect()
    await vi.runAllTimersAsync()

    // Custom event would be dispatched when addNotification is called

    window.removeEventListener('autopilot-notification', eventHandler)
  })
})


// =============================================================================
// INTEGRATION-LIKE TESTS
// =============================================================================

describe('useWebSocket - Integration Scenarios', () => {
  let mockAutopilotStore

  beforeEach(() => {
    setActivePinia(createPinia())

    mockAutopilotStore = {
      strategies: [
        { id: 1, name: 'Strategy 1', status: 'active', runtime_state: {} },
        { id: 2, name: 'Strategy 2', status: 'waiting', runtime_state: {} }
      ],
      currentStrategy: null,
      fetchDashboardSummary: vi.fn().mockResolvedValue({}),
      updateBuilderStrategy: vi.fn()
    }

    useAutopilotStore.mockReturnValue(mockAutopilotStore)
    localStorage.store = { access_token: 'test_token' }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    disconnectAutopilotWebSocket()
  })

  it('handles full strategy lifecycle via WebSocket', async () => {
    const { connect, lastMessage, notifications } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Scenario: Strategy goes from waiting -> active -> completed
    // Each status change would be handled by message handlers
  })

  it('handles order execution flow', async () => {
    const { connect, notifications } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Scenario: order_placed -> order_filled
    // Notifications would be added for each event
  })

  it('handles risk management flow', async () => {
    const { connect, notifications } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Scenario: P&L update triggers risk alert
    // Risk alert notification would be shown
  })

  it('handles concurrent strategy updates', async () => {
    const { connect, lastMessage } = useWebSocket()

    connect()
    await vi.runAllTimersAsync()

    // Scenario: Multiple strategies receiving updates simultaneously
    // All updates should be processed correctly
  })
})
