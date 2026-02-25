/**
 * Auth Pinia Store Tests
 *
 * Tests for src/stores/auth.js — authentication state management
 * Covers: login, logout, fetchUser, setToken, checkAuth, broker-specific logins
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

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

const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  name: 'Test User'
}

const mockBrokerConnections = [
  {
    broker: 'zerodha',
    broker_user_id: 'AB1234',
    is_active: true
  },
  {
    broker: 'angelone',
    broker_user_id: 'ANG5678',
    is_active: false
  }
]

const mockLoginResponse = {
  data: {
    user: mockUser,
    access_token: 'mock-jwt-token-123'
  }
}

const mockFetchUserResponse = {
  data: {
    user: mockUser,
    broker_connections: mockBrokerConnections
  }
}


// =============================================================================
// SETUP
// =============================================================================

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => { localStorageMock.store[key] = value }),
  removeItem: vi.fn((key) => { delete localStorageMock.store[key] }),
  clear: vi.fn(() => { localStorageMock.store = {} })
}

// Mock window.location
const originalLocation = window.location
delete window.location
window.location = { href: '', assign: vi.fn() }


beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorageMock.store = {}
  Object.defineProperty(window, 'localStorage', { value: localStorageMock })
  window.location.href = ''
})

afterEach(() => {
  vi.restoreAllMocks()
})


// =============================================================================
// INITIAL STATE
// =============================================================================

describe('Auth Store - Initial State', () => {
  it('should start with null user', () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()
  })

  it('should start unauthenticated', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
  })

  it('should start with loading false', () => {
    const store = useAuthStore()
    expect(store.loading).toBe(false)
  })

  it('should have all broker loading states as false', () => {
    const store = useAuthStore()
    expect(store.zerodhaLoading).toBe(false)
    expect(store.angelOneLoading).toBe(false)
    expect(store.upstoxLoading).toBe(false)
    expect(store.fyersLoading).toBe(false)
    expect(store.dhanLoading).toBe(false)
    expect(store.paytmLoading).toBe(false)
  })
})


// =============================================================================
// LOGIN
// =============================================================================

describe('Auth Store - Login', () => {
  it('should login successfully and store token', async () => {
    api.post.mockResolvedValueOnce(mockLoginResponse)
    const store = useAuthStore()

    const result = await store.login({ username: 'test', password: 'pass' })

    expect(result.success).toBe(true)
    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toEqual(mockUser)
    expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'mock-jwt-token-123')
  })

  it('should handle login failure', async () => {
    api.post.mockRejectedValueOnce({
      response: { data: { detail: 'Invalid credentials' } }
    })
    const store = useAuthStore()

    const result = await store.login({ username: 'test', password: 'wrong' })

    expect(result.success).toBe(false)
    expect(result.error).toBe('Invalid credentials')
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('should set loading during login', async () => {
    let resolveLogin
    api.post.mockReturnValueOnce(new Promise(resolve => { resolveLogin = resolve }))
    const store = useAuthStore()

    const loginPromise = store.login({ username: 'test', password: 'pass' })
    expect(store.loading).toBe(true)

    resolveLogin(mockLoginResponse)
    await loginPromise
    expect(store.loading).toBe(false)
  })

  it('should reset loading on failure', async () => {
    api.post.mockRejectedValueOnce(new Error('Network error'))
    const store = useAuthStore()

    await store.login({ username: 'test', password: 'pass' })
    expect(store.loading).toBe(false)
  })
})


// =============================================================================
// FETCH USER
// =============================================================================

describe('Auth Store - Fetch User', () => {
  it('should fetch and set user with broker connections', async () => {
    api.get.mockResolvedValueOnce(mockFetchUserResponse)
    const store = useAuthStore()

    const result = await store.fetchUser()

    expect(result.success).toBe(true)
    expect(store.isAuthenticated).toBe(true)
    expect(store.user).not.toBeNull()
    expect(store.user.email).toBe('test@example.com')
    expect(store.user.broker).toBe('zerodha')
    expect(store.user.broker_user_id).toBe('AB1234')
    expect(store.user.broker_connections).toHaveLength(2)
  })

  it('should clear state on fetch failure', async () => {
    api.get.mockRejectedValueOnce({
      response: { data: { detail: 'Token expired' } }
    })
    const store = useAuthStore()

    const result = await store.fetchUser()

    expect(result.success).toBe(false)
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
  })

  it('should handle empty broker connections', async () => {
    api.get.mockResolvedValueOnce({
      data: { user: mockUser, broker_connections: [] }
    })
    const store = useAuthStore()

    await store.fetchUser()

    expect(store.user.broker_user_id).toBeNull()
    expect(store.user.broker).toBeNull()
  })
})


// =============================================================================
// LOGOUT
// =============================================================================

describe('Auth Store - Logout', () => {
  it('should clear user state on logout', async () => {
    api.post.mockResolvedValueOnce({})
    const store = useAuthStore()

    // Set up authenticated state first
    store.user = mockUser
    store.isAuthenticated = true

    await store.logout()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
  })

  it('should clear state even if API call fails', async () => {
    api.post.mockRejectedValueOnce(new Error('Network error'))
    const store = useAuthStore()

    store.user = mockUser
    store.isAuthenticated = true

    await store.logout()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })
})


// =============================================================================
// SET TOKEN
// =============================================================================

describe('Auth Store - Set Token', () => {
  it('should store token and set authenticated', () => {
    const store = useAuthStore()

    store.setToken('new-token-456')

    expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'new-token-456')
    expect(store.isAuthenticated).toBe(true)
  })
})


// =============================================================================
// CHECK AUTH
// =============================================================================

describe('Auth Store - Check Auth', () => {
  it('should fetch user if token exists', async () => {
    localStorageMock.store['access_token'] = 'existing-token'
    api.get.mockResolvedValueOnce(mockFetchUserResponse)
    const store = useAuthStore()

    await store.checkAuth()

    expect(api.get).toHaveBeenCalledWith('/api/auth/me')
    expect(store.isAuthenticated).toBe(true)
  })

  it('should not fetch if no token', async () => {
    const store = useAuthStore()

    await store.checkAuth()

    expect(api.get).not.toHaveBeenCalled()
  })
})


// =============================================================================
// BROKER-SPECIFIC LOGINS
// =============================================================================

describe('Auth Store - Zerodha Login', () => {
  it('should redirect to Zerodha login URL', async () => {
    api.get.mockResolvedValueOnce({
      data: { login_url: 'https://kite.zerodha.com/connect/login?...' }
    })
    const store = useAuthStore()

    const result = await store.initiateZerodhaLogin()

    expect(result.success).toBe(true)
    expect(window.location.href).toBe('https://kite.zerodha.com/connect/login?...')
  })

  it('should set zerodhaLoading during login', async () => {
    let resolve
    api.get.mockReturnValueOnce(new Promise(r => { resolve = r }))
    const store = useAuthStore()

    const promise = store.initiateZerodhaLogin()
    expect(store.zerodhaLoading).toBe(true)

    resolve({ data: { login_url: 'https://kite.zerodha.com' } })
    await promise
    // Note: zerodhaLoading stays true on success (redirect happens)
  })

  it('should reset loading on failure', async () => {
    api.get.mockRejectedValueOnce(new Error('Failed'))
    const store = useAuthStore()

    await store.initiateZerodhaLogin()
    expect(store.zerodhaLoading).toBe(false)
  })
})


describe('Auth Store - AngelOne Login', () => {
  it('should login with AngelOne and store token', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        success: true,
        token: 'angel-token-789',
        redirect_url: '/dashboard'
      }
    })
    const store = useAuthStore()

    const result = await store.initiateAngelOneLogin()

    expect(result.success).toBe(true)
    expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'angel-token-789')
    expect(store.isAuthenticated).toBe(true)
  })

  it('should use 35s timeout for AngelOne', async () => {
    api.post.mockResolvedValueOnce({
      data: { success: true, token: 'token', redirect_url: '/dashboard' }
    })
    const store = useAuthStore()

    await store.initiateAngelOneLogin()

    expect(api.post).toHaveBeenCalledWith(
      '/api/auth/angelone/login',
      {},
      { timeout: 35000 }
    )
  })

  it('should handle AngelOne login failure', async () => {
    api.post.mockRejectedValueOnce({
      response: { data: { detail: 'TOTP failed' } }
    })
    const store = useAuthStore()

    const result = await store.initiateAngelOneLogin()

    expect(result.success).toBe(false)
    expect(store.angelOneLoading).toBe(false)
  })
})


describe('Auth Store - Dhan Login', () => {
  it('should login with client ID and access token', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        success: true,
        token: 'dhan-token',
        redirect_url: '/dashboard'
      }
    })
    const store = useAuthStore()

    const result = await store.initiateDhanLogin('DHAN123', 'dhan-access-token')

    expect(result.success).toBe(true)
    expect(api.post).toHaveBeenCalledWith('/api/auth/dhan/login', {
      client_id: 'DHAN123',
      access_token: 'dhan-access-token'
    })
  })
})


describe('Auth Store - Disconnect Broker', () => {
  it('should disconnect broker and refresh user', async () => {
    api.delete.mockResolvedValueOnce({})
    api.get.mockResolvedValueOnce(mockFetchUserResponse)
    const store = useAuthStore()

    const result = await store.disconnectBroker('angelone')

    expect(result.success).toBe(true)
    expect(api.delete).toHaveBeenCalledWith('/api/auth/angelone/disconnect')
    expect(api.get).toHaveBeenCalledWith('/api/auth/me')
  })

  it('should handle disconnect failure', async () => {
    api.delete.mockRejectedValueOnce({
      response: { data: { detail: 'Cannot disconnect active broker' } }
    })
    const store = useAuthStore()

    const result = await store.disconnectBroker('zerodha')

    expect(result.success).toBe(false)
    expect(result.error).toBe('Cannot disconnect active broker')
  })
})
