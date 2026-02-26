/**
 * Shared test setup helpers for Vitest store/composable tests.
 *
 * Eliminates the repeated beforeEach boilerplate across all store test files.
 *
 * Usage:
 *   import { setupStoreTest, mockApiSuccess, mockApiError } from '../helpers/test-setup.js'
 *
 *   describe('myStore', () => {
 *     setupStoreTest()   // sets up Pinia, clears mocks, clears localStorage
 *
 *     it('fetches data', async () => {
 *       mockApiSuccess(api, 'get', '/api/user', mockUser)
 *       ...
 *     })
 *   })
 */

import { beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { vi } from 'vitest'

/**
 * Standard store test setup.
 *
 * Call inside describe() — sets up Pinia, clears all mocks,
 * and resets localStorage before each test.
 */
export function setupStoreTest() {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    if (typeof localStorage !== 'undefined') {
      localStorage.clear()
    }
  })
}

/**
 * Mock a successful API response for a single call.
 *
 * @param {object} apiModule - The vi.mocked api module
 * @param {'get'|'post'|'put'|'delete'|'patch'} method - HTTP method
 * @param {any} data - Response data (wrapped in { data })
 *
 * Usage:
 *   mockApiSuccess(api, 'get', { id: 1, name: 'Test' })
 */
export function mockApiSuccess(apiModule, method, data) {
  apiModule[method].mockResolvedValueOnce({ data })
}

/**
 * Mock a failed API response for a single call.
 *
 * @param {object} apiModule - The vi.mocked api module
 * @param {'get'|'post'|'put'|'delete'|'patch'} method - HTTP method
 * @param {object} error - Error object (defaults to network error)
 *
 * Usage:
 *   mockApiError(api, 'post', { response: { status: 401 } })
 */
export function mockApiError(apiModule, method, error = new Error('Network Error')) {
  apiModule[method].mockRejectedValueOnce(error)
}

/**
 * Mock an API response with a 401 status code.
 * Triggers the axios interceptor → redirect to /login.
 *
 * @param {object} apiModule - The vi.mocked api module
 * @param {'get'|'post'|'put'|'delete'|'patch'} method - HTTP method
 */
export function mockApi401(apiModule, method) {
  mockApiError(apiModule, method, {
    response: { status: 401, data: { detail: 'Token expired' } },
  })
}
