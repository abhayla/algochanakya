# Vitest Test Patterns - Complete Examples

Comprehensive test examples for Pinia stores, Vue components, and composables.

---

## Table of Contents

1. [Pinia Store Tests](#pinia-store-tests)
2. [Vue Component Tests](#vue-component-tests)
3. [Composable Tests](#composable-tests)
4. [API Mocking Patterns](#api-mocking-patterns)
5. [Testing Async Operations](#testing-async-operations)

---

## Pinia Store Tests

### Complete Store Test Example

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePositionsStore } from '@/stores/positions'
import * as api from '@/services/api'

// Mock API module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  }
}))

describe('Positions Store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = usePositionsStore()
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      expect(store.positions).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBe(null)
      expect(store.positionType).toBe('day')
      expect(store.autoRefresh).toBe(false)
    })
  })

  describe('Getters', () => {
    it('should calculate totalPnl correctly', () => {
      store.positions = [
        { pnl: 1000, unrealised: 500 },
        { pnl: -200, unrealised: 100 }
      ]

      expect(store.totalPnl).toBe(1400) // 1000 + 500 + (-200) + 100
    })

    it('should return zero when no positions', () => {
      expect(store.totalPnl).toBe(0)
    })

    it('should filter open positions', () => {
      store.positions = [
        { tradingsymbol: 'NIFTY24JAN25000CE', quantity: 25 },
        { tradingsymbol: 'NIFTY24JAN24900PE', quantity: 0 },
        { tradingsymbol: 'BANKNIFTY24JAN52000CE', quantity: -15 }
      ]

      expect(store.openPositions).toHaveLength(2)
      expect(store.openPositions[0].tradingsymbol).toBe('NIFTY24JAN25000CE')
      expect(store.openPositions[1].tradingsymbol).toBe('BANKNIFTY24JAN52000CE')
    })
  })

  describe('Actions', () => {
    describe('fetchPositions', () => {
      it('should fetch positions successfully', async () => {
        const mockPositions = [
          { tradingsymbol: 'NIFTY24JAN25000CE', quantity: 25, pnl: 1000 }
        ]

        api.default.get.mockResolvedValueOnce({
          data: {
            positions: mockPositions,
            summary: { total_pnl: 1000 }
          }
        })

        await store.fetchPositions()

        expect(api.default.get).toHaveBeenCalledWith('/api/positions/', {
          params: { type: 'day' }
        })
        expect(store.positions).toEqual(mockPositions)
        expect(store.summary.total_pnl).toBe(1000)
        expect(store.loading).toBe(false)
      })

      it('should handle fetch error', async () => {
        api.default.get.mockRejectedValueOnce(new Error('Network error'))

        await store.fetchPositions()

        expect(store.error).toBe('Failed to fetch positions')
        expect(store.positions).toEqual([])
        expect(store.loading).toBe(false)
      })
    })

    describe('exitPosition', () => {
      it('should exit position with market order', async () => {
        const mockResponse = { data: { order_id: 'ORDER123', status: 'COMPLETE' } }
        api.default.post.mockResolvedValueOnce(mockResponse)

        const result = await store.exitPosition('NIFTY24JAN25000CE', {
          order_type: 'MARKET'
        })

        expect(api.default.post).toHaveBeenCalledWith('/api/positions/exit', {
          tradingsymbol: 'NIFTY24JAN25000CE',
          order_type: 'MARKET'
        })
        expect(result).toEqual(mockResponse.data)
      })

      it('should exit position with limit order', async () => {
        const mockResponse = { data: { order_id: 'ORDER124', status: 'COMPLETE' } }
        api.default.post.mockResolvedValueOnce(mockResponse)

        await store.exitPosition('NIFTY24JAN24900PE', {
          order_type: 'LIMIT',
          price: 150.5
        })

        expect(api.default.post).toHaveBeenCalledWith('/api/positions/exit', {
          tradingsymbol: 'NIFTY24JAN24900PE',
          order_type: 'LIMIT',
          price: 150.5
        })
      })

      it('should throw error on failed exit', async () => {
        api.default.post.mockRejectedValueOnce(new Error('Order failed'))

        await expect(
          store.exitPosition('NIFTY24JAN25000CE', { order_type: 'MARKET' })
        ).rejects.toThrow('Failed to exit position')
      })
    })

    describe('togglePositionType', () => {
      it('should toggle from day to net', () => {
        expect(store.positionType).toBe('day')

        store.togglePositionType()

        expect(store.positionType).toBe('net')
      })

      it('should toggle from net to day', () => {
        store.positionType = 'net'

        store.togglePositionType()

        expect(store.positionType).toBe('day')
      })

      it('should refetch positions after toggle', async () => {
        const fetchSpy = vi.spyOn(store, 'fetchPositions')
        api.default.get.mockResolvedValueOnce({ data: { positions: [] } })

        await store.togglePositionType()

        expect(fetchSpy).toHaveBeenCalled()
      })
    })
  })
})
```

---

## Vue Component Tests

### Complete Component Test Example

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ExitModal from '@/components/positions/ExitModal.vue'

describe('ExitModal', () => {
  let wrapper
  let pinia

  const defaultProps = {
    show: true,
    position: {
      tradingsymbol: 'NIFTY24JAN25000CE',
      quantity: 25,
      average_price: 150.0,
      ltp: 175.0
    }
  }

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  afterEach(() => {
    wrapper?.unmount()
  })

  const createWrapper = (props = {}) => {
    return mount(ExitModal, {
      props: {
        ...defaultProps,
        ...props
      },
      global: {
        plugins: [pinia]
      }
    })
  }

  describe('Rendering', () => {
    it('should render modal when show is true', () => {
      wrapper = createWrapper()

      expect(wrapper.find('[data-testid="positions-exit-modal"]').exists()).toBe(true)
    })

    it('should not render modal when show is false', () => {
      wrapper = createWrapper({ show: false })

      expect(wrapper.find('[data-testid="positions-exit-modal"]').exists()).toBe(false)
    })

    it('should display position details', () => {
      wrapper = createWrapper()

      const modal = wrapper.find('[data-testid="positions-exit-modal"]')
      expect(modal.text()).toContain('NIFTY24JAN25000CE')
      expect(modal.text()).toContain('25')
      expect(modal.text()).toContain('150.0')
    })
  })

  describe('Props', () => {
    it('should accept show prop', () => {
      wrapper = createWrapper({ show: false })
      expect(wrapper.props('show')).toBe(false)
    })

    it('should accept position prop', () => {
      const customPosition = {
        tradingsymbol: 'BANKNIFTY24JAN52000PE',
        quantity: -15,
        average_price: 200.0,
        ltp: 180.0
      }

      wrapper = createWrapper({ position: customPosition })

      expect(wrapper.props('position')).toEqual(customPosition)
    })

    it('should validate required props', () => {
      // Vitest will warn if required props are missing
      wrapper = createWrapper({ position: undefined })
      expect(wrapper.vm.position).toBeUndefined()
    })
  })

  describe('User Interactions', () => {
    it('should emit close event when backdrop is clicked', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-backdrop"]').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('should emit close event when close button is clicked', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-close-button"]').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('should update order type when dropdown changes', async () => {
      wrapper = createWrapper()

      const dropdown = wrapper.find('[data-testid="positions-exit-modal-type-dropdown"]')
      await dropdown.setValue('LIMIT')

      expect(wrapper.vm.orderType).toBe('LIMIT')
    })

    it('should show price input when LIMIT order type is selected', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-type-dropdown"]').setValue('LIMIT')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[data-testid="positions-exit-modal-price-input"]').exists()).toBe(true)
    })

    it('should not show price input when MARKET order type is selected', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-type-dropdown"]').setValue('MARKET')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[data-testid="positions-exit-modal-price-input"]').exists()).toBe(false)
    })
  })

  describe('Form Submission', () => {
    it('should emit submit event with market order', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-submit-button"]').trigger('click')

      expect(wrapper.emitted('submit')).toBeTruthy()
      expect(wrapper.emitted('submit')[0][0]).toEqual({
        order_type: 'MARKET',
        tradingsymbol: 'NIFTY24JAN25000CE'
      })
    })

    it('should emit submit event with limit order and price', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-type-dropdown"]').setValue('LIMIT')
      await wrapper.find('[data-testid="positions-exit-modal-price-input"]').setValue('180.5')
      await wrapper.find('[data-testid="positions-exit-modal-submit-button"]').trigger('click')

      expect(wrapper.emitted('submit')[0][0]).toEqual({
        order_type: 'LIMIT',
        price: 180.5,
        tradingsymbol: 'NIFTY24JAN25000CE'
      })
    })

    it('should disable submit button when loading', async () => {
      wrapper = createWrapper()
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()

      const submitButton = wrapper.find('[data-testid="positions-exit-modal-submit-button"]')
      expect(submitButton.attributes('disabled')).toBeDefined()
    })

    it('should validate price for limit orders', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-type-dropdown"]').setValue('LIMIT')
      await wrapper.find('[data-testid="positions-exit-modal-price-input"]').setValue('')
      await wrapper.find('[data-testid="positions-exit-modal-submit-button"]').trigger('click')

      // Should not emit if price is invalid
      expect(wrapper.emitted('submit')).toBeFalsy()
    })
  })

  describe('Computed Properties', () => {
    it('should calculate estimated P&L for market order', () => {
      wrapper = createWrapper()

      // Position: qty=25, avg_price=150, ltp=175
      // P&L = (175 - 150) * 25 = 625
      expect(wrapper.vm.estimatedPnl).toBe(625)
    })

    it('should calculate estimated P&L for limit order', async () => {
      wrapper = createWrapper()

      await wrapper.find('[data-testid="positions-exit-modal-type-dropdown"]').setValue('LIMIT')
      await wrapper.find('[data-testid="positions-exit-modal-price-input"]').setValue('180')
      await wrapper.vm.$nextTick()

      // P&L = (180 - 150) * 25 = 750
      expect(wrapper.vm.estimatedPnl).toBe(750)
    })

    it('should show pnl in green for profit', () => {
      wrapper = createWrapper()

      expect(wrapper.vm.pnlColor).toBe('text-green-600')
    })

    it('should show pnl in red for loss', () => {
      wrapper = createWrapper({
        position: {
          tradingsymbol: 'NIFTY24JAN25000CE',
          quantity: 25,
          average_price: 200.0,
          ltp: 175.0
        }
      })

      expect(wrapper.vm.pnlColor).toBe('text-red-600')
    })
  })
})
```

---

## Composable Tests

### WebSocket Composable Test Example

```javascript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useWebSocket } from '@/composables/autopilot/useWebSocket'

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = WebSocket.CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onerror = null
    this.onclose = null

    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      if (this.onopen) this.onopen(new Event('open'))
    }, 10)
  }

  send(data) {
    this.sentMessages = this.sentMessages || []
    this.sentMessages.push(data)
  }

  close() {
    this.readyState = WebSocket.CLOSED
    if (this.onclose) this.onclose(new CloseEvent('close'))
  }

  // Helper to simulate receiving messages
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }))
    }
  }
}

global.WebSocket = MockWebSocket

describe('useWebSocket', () => {
  let composable
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.useFakeTimers()
  })

  afterEach(() => {
    composable?.disconnect()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('Connection', () => {
    it('should connect to WebSocket', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      expect(composable.isConnected.value).toBe(true)
    })

    it('should set connecting state during connection', () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()

      expect(composable.isConnecting.value).toBe(true)
    })

    it('should include token in WebSocket URL', () => {
      const token = 'test-jwt-token'
      localStorage.setItem('access_token', token)

      composable = useWebSocket('ws://localhost:8000/ws/autopilot')
      composable.connect()

      expect(composable.ws.url).toContain(`token=${token}`)
    })

    it('should handle connection without token', () => {
      localStorage.removeItem('access_token')

      composable = useWebSocket('ws://localhost:8000/ws/autopilot')
      composable.connect()

      expect(composable.ws.url).not.toContain('token=')
    })
  })

  describe('Disconnection', () => {
    it('should disconnect from WebSocket', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      composable.disconnect()

      expect(composable.isConnected.value).toBe(false)
      expect(composable.ws).toBe(null)
    })

    it('should stop heartbeat on disconnect', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      const heartbeatInterval = composable.heartbeatInterval
      composable.disconnect()

      expect(composable.heartbeatInterval).toBe(null)
    })
  })

  describe('Message Handling', () => {
    it('should receive and parse messages', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      const testMessage = { type: 'STRATEGY_UPDATE', data: { id: 1, status: 'active' } }
      composable.ws.simulateMessage(testMessage)

      expect(composable.lastMessage.value).toEqual(testMessage)
    })

    it('should call message handlers', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')
      const handler = vi.fn()

      composable.onMessage('STRATEGY_UPDATE', handler)
      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      const testMessage = { type: 'STRATEGY_UPDATE', data: { id: 1 } }
      composable.ws.simulateMessage(testMessage)

      expect(handler).toHaveBeenCalledWith(testMessage.data)
    })

    it('should support multiple handlers for same type', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')
      const handler1 = vi.fn()
      const handler2 = vi.fn()

      composable.onMessage('PNL_UPDATE', handler1)
      composable.onMessage('PNL_UPDATE', handler2)
      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      const testMessage = { type: 'PNL_UPDATE', data: { pnl: 1000 } }
      composable.ws.simulateMessage(testMessage)

      expect(handler1).toHaveBeenCalledWith(testMessage.data)
      expect(handler2).toHaveBeenCalledWith(testMessage.data)
    })

    it('should not call handlers for different message types', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')
      const handler = vi.fn()

      composable.onMessage('STRATEGY_UPDATE', handler)
      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      composable.ws.simulateMessage({ type: 'PNL_UPDATE', data: {} })

      expect(handler).not.toHaveBeenCalled()
    })
  })

  describe('Sending Messages', () => {
    it('should send messages when connected', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      composable.send({ action: 'subscribe', strategy_id: 1 })

      expect(composable.ws.sentMessages).toHaveLength(1)
      expect(JSON.parse(composable.ws.sentMessages[0])).toEqual({
        action: 'subscribe',
        strategy_id: 1
      })
    })

    it('should queue messages when not connected', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.send({ action: 'subscribe', strategy_id: 1 })

      // Message should be queued, not sent
      expect(composable.ws).toBe(null)
      expect(composable.messageQueue).toHaveLength(1)

      // Connect and verify message is sent
      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      expect(composable.ws.sentMessages).toHaveLength(1)
      expect(composable.messageQueue).toHaveLength(0)
    })
  })

  describe('Heartbeat', () => {
    it('should send ping messages at intervals', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      // Clear initial messages
      composable.ws.sentMessages = []

      // Advance by heartbeat interval (30 seconds)
      await vi.advanceTimersByTimeAsync(30000)

      expect(composable.ws.sentMessages).toHaveLength(1)
      expect(JSON.parse(composable.ws.sentMessages[0])).toEqual({ type: 'ping' })
    })

    it('should handle pong responses', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      composable.ws.simulateMessage({ type: 'pong' })

      // Pong should update last pong time
      expect(composable.lastPongTime.value).toBeTruthy()
    })
  })

  describe('Reconnection', () => {
    it('should attempt to reconnect on disconnect', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      // Simulate disconnection
      composable.ws.close()

      // Should attempt reconnect after delay
      await vi.advanceTimersByTimeAsync(5000)

      expect(composable.isConnecting.value).toBe(true)
    })

    it('should not reconnect if manually disconnected', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      composable.disconnect()

      await vi.advanceTimersByTimeAsync(10000)

      expect(composable.isConnecting.value).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('should handle WebSocket errors', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      const errorEvent = new Event('error')
      composable.ws.onerror(errorEvent)

      expect(composable.error.value).toBeTruthy()
    })

    it('should handle malformed messages', async () => {
      composable = useWebSocket('ws://localhost:8000/ws/autopilot')

      composable.connect()
      await vi.advanceTimersByTimeAsync(100)

      // Simulate malformed JSON
      composable.ws.onmessage(new MessageEvent('message', { data: 'invalid json' }))

      expect(composable.error.value).toBeTruthy()
    })
  })
})
```

---

## API Mocking Patterns

### Mocking Axios API Module

```javascript
import { vi } from 'vitest'
import * as api from '@/services/api'

// Mock entire API module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

// In test
api.default.get.mockResolvedValueOnce({ data: { result: 'success' } })
api.default.post.mockRejectedValueOnce(new Error('Failed'))
```

### Mocking Specific API Endpoints

```javascript
beforeEach(() => {
  // Mock successful fetch
  api.default.get.mockImplementation((url) => {
    if (url === '/api/positions/') {
      return Promise.resolve({
        data: {
          positions: [{ tradingsymbol: 'NIFTY24JAN25000CE', quantity: 25 }],
          summary: { total_pnl: 1000 }
        }
      })
    }
    return Promise.reject(new Error('Unknown endpoint'))
  })
})
```

### Mocking with Different Responses

```javascript
it('should handle pagination', async () => {
  // First call returns page 1
  api.default.get.mockResolvedValueOnce({
    data: { items: [1, 2, 3], page: 1, has_more: true }
  })

  // Second call returns page 2
  api.default.get.mockResolvedValueOnce({
    data: { items: [4, 5, 6], page: 2, has_more: false }
  })

  await store.fetchPage(1)
  await store.fetchPage(2)

  expect(store.items).toHaveLength(6)
})
```

---

## Testing Async Operations

### Using Fake Timers

```javascript
import { vi } from 'vitest'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

it('should auto-refresh every 5 seconds', async () => {
  const fetchSpy = vi.spyOn(store, 'fetchPositions')

  store.startAutoRefresh()

  // Advance time by 5 seconds
  await vi.advanceTimersByTimeAsync(5000)
  expect(fetchSpy).toHaveBeenCalledTimes(1)

  // Advance another 5 seconds
  await vi.advanceTimersByTimeAsync(5000)
  expect(fetchSpy).toHaveBeenCalledTimes(2)
})
```

### Testing Debounced Functions

```javascript
it('should debounce search input', async () => {
  const searchSpy = vi.spyOn(store, 'search')

  // Type multiple characters quickly
  wrapper.vm.handleSearchInput('a')
  wrapper.vm.handleSearchInput('ab')
  wrapper.vm.handleSearchInput('abc')

  // Should not have called search yet
  expect(searchSpy).not.toHaveBeenCalled()

  // Advance past debounce delay (300ms)
  await vi.advanceTimersByTimeAsync(300)

  // Should have called search once with final value
  expect(searchSpy).toHaveBeenCalledTimes(1)
  expect(searchSpy).toHaveBeenCalledWith('abc')
})
```

### Testing Promises

```javascript
it('should handle async errors', async () => {
  api.default.post.mockRejectedValueOnce(new Error('Network error'))

  await expect(store.exitPosition('NIFTY24JAN25000CE')).rejects.toThrow('Network error')
})

it('should wait for multiple promises', async () => {
  const promise1 = store.fetchPositions()
  const promise2 = store.fetchOrders()

  await Promise.all([promise1, promise2])

  expect(store.positions).toBeDefined()
  expect(store.orders).toBeDefined()
})
```

---

## Best Practices

1. **Always set active Pinia** before creating stores
2. **Clear mocks** in beforeEach to prevent test pollution
3. **Use vi.useFakeTimers()** for time-based tests
4. **Mock at module level** with vi.mock()
5. **Use mockResolvedValueOnce** for single-use mocks
6. **Use mockImplementation** for complex mock logic
7. **Test error paths** along with happy paths
8. **Unmount components** in afterEach
9. **Use data-testid** selectors for stability
10. **Test user interactions** with trigger() and setValue()
