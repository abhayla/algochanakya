/**
 * Vitest Setup File
 *
 * Global setup for Vue/Pinia testing.
 */
import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => {
    localStorageMock.store[key] = value
  }),
  removeItem: vi.fn((key) => {
    delete localStorageMock.store[key]
  }),
  clear: vi.fn(() => {
    localStorageMock.store = {}
  })
}
global.localStorage = localStorageMock

// Mock WebSocket global (happy-dom may not expose WebSocket.OPEN static constant)
if (typeof WebSocket === 'undefined') {
  global.WebSocket = class MockWebSocket {
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
    }
    send() {}
    close() { this.readyState = MockWebSocket.CLOSED }
  }
} else if (!WebSocket.OPEN) {
  WebSocket.CONNECTING = 0
  WebSocket.OPEN = 1
  WebSocket.CLOSING = 2
  WebSocket.CLOSED = 3
}

// Mock import.meta.env
vi.stubGlobal('import.meta.env', {
  VITE_API_BASE_URL: 'http://localhost:8000',
  VITE_WS_URL: 'ws://localhost:8000'
})

// Reset localStorage before each test
beforeEach(() => {
  localStorageMock.store = {}
  localStorageMock.getItem.mockClear()
  localStorageMock.setItem.mockClear()
  localStorageMock.removeItem.mockClear()
  localStorageMock.clear.mockClear()
})

// Global test utilities
config.global.mocks = {
  $t: (msg) => msg
}
