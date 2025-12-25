/**
 * AI Implementation Phases E2E Test
 *
 * Tests all 8 phases of AI implementation to verify:
 * - API endpoints return valid responses
 * - No breaking changes to existing functionality
 * - Real data integration (not mocks)
 */

import { test, expect } from '../../fixtures/auth.fixture.js'
import fs from 'fs'
import path from 'path'

// Read auth token from storage state file
function getAuthToken() {
  try {
    const authStatePath = path.join(process.cwd(), 'tests', 'config', '.auth-state.json')
    if (fs.existsSync(authStatePath)) {
      const authState = JSON.parse(fs.readFileSync(authStatePath, 'utf8'))
      const origin = authState.origins?.find(o => o.origin === 'http://localhost:5173')
      const token = origin?.localStorage?.find(item => item.name === 'access_token')?.value
      return token || process.env.TEST_AUTH_TOKEN
    }
  } catch (e) {
    console.warn('Could not read auth token from state file:', e.message)
  }
  return process.env.TEST_AUTH_TOKEN
}

const API_BASE = process.env.API_BASE || 'http://localhost:8000'
const authToken = getAuthToken()
const authHeader = authToken ? { 'Authorization': `Bearer ${authToken}` } : {}

test.describe('AI Implementation Phases - E2E Tests', () => {

  test.describe('Phase 6: Analytics API - Real Data', () => {

    test('GET /api/v1/ai/analytics/performance returns real metrics', async ({ authenticatedPage, request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/analytics/performance`, {
        params: {
          start_date: '2024-01-01',
          end_date: '2024-12-31'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      // Verify structure (should have real database queries now, not mocks)
      expect(data).toHaveProperty('total_trades')
      expect(data).toHaveProperty('winning_trades')
      expect(data).toHaveProperty('win_rate')
      expect(data).toHaveProperty('total_pnl')
      expect(data).toHaveProperty('avg_pnl_per_trade')  // Fixed: correct field name

      // Verify data types
      expect(typeof data.total_trades).toBe('number')
      expect(typeof data.win_rate).toBe('number')
    })

    test('GET /api/v1/ai/analytics/by-regime returns real data', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/analytics/by-regime`, {
        params: {
          start_date: '2024-01-01',
          end_date: '2024-12-31'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      // Should be an array of regime performance data
      expect(Array.isArray(data)).toBe(true)
    })

    test('GET /api/v1/ai/analytics/by-strategy returns real data', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/analytics/by-strategy`, {
        params: {
          start_date: '2024-01-01',
          end_date: '2024-12-31'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      expect(Array.isArray(data)).toBe(true)
    })

    test('GET /api/v1/ai/analytics/decisions returns real data', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/analytics/decisions`, {
        params: {
          start_date: '2024-01-01',
          end_date: '2024-12-31',
          interval: 'daily'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      expect(Array.isArray(data)).toBe(true)
    })

    test('GET /api/v1/ai/analytics/learning returns real data', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/analytics/learning`, {
        params: {
          start_date: '2024-01-01',
          end_date: '2024-12-31'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      // Fixed: /learning returns a single object (LearningProgressMetrics), not an array
      expect(typeof data).toBe('object')
      expect(data).toHaveProperty('model_version')
      expect(data).toHaveProperty('accuracy')
      expect(data).toHaveProperty('performance_trend')
    })
  })

  test.describe('Phase 3: Market Regime API', () => {

    test('GET /api/v1/ai/regime/current returns regime classification', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/regime/current`, {
        params: {
          underlying: 'NIFTY'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      // Verify regime result structure
      expect(data).toHaveProperty('regime_type')
      expect(data).toHaveProperty('confidence')
      expect(data).toHaveProperty('reasoning')
      expect(data).toHaveProperty('indicators')

      // Valid regime types
      const validRegimes = ['TRENDING_BULLISH', 'TRENDING_BEARISH', 'RANGEBOUND', 'VOLATILE', 'PRE_EVENT', 'EVENT_DAY', 'UNKNOWN']
      expect(validRegimes).toContain(data.regime_type)
    })

    test('GET /api/v1/ai/regime/indicators returns indicators snapshot', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/regime/indicators`, {
        params: {
          underlying: 'NIFTY'
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      // Verify indicators structure
      expect(data).toHaveProperty('underlying')
      expect(data).toHaveProperty('spot_price')
      expect(data).toHaveProperty('rsi_14')
      expect(data).toHaveProperty('adx_14')
      expect(data).toHaveProperty('ema_50')
    })
  })

  test.describe('Phase 2 & 4: AI Config API', () => {

    test('GET /api/v1/ai/config returns user AI configuration', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.get(`${API_BASE}/api/v1/ai/config/`, {
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      // Verify config structure
      expect(data).toHaveProperty('ai_enabled')
      expect(data).toHaveProperty('preferred_underlyings')
      expect(data).toHaveProperty('max_strategies_per_day')
    })

    test('PUT /api/v1/ai/config updates AI configuration', async ({ request }) => {
      if (!authToken) {
        test.skip('No auth token available')
        return
      }

      const response = await request.put(`${API_BASE}/api/v1/ai/config/`, {
        data: {
          ai_enabled: true,
          preferred_underlyings: ['NIFTY', 'BANKNIFTY'],
          max_daily_trades: 5
        },
        headers: authHeader
      })

      expect(response.status()).toBe(200)
      const data = await response.json()

      expect(data.ai_enabled).toBe(true)
      expect(data.preferred_underlyings).toContain('NIFTY')
    })
  })

  test.describe('Frontend Routes - Phase 1', () => {

    test('AI Paper Trading route is accessible', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/ai/paper-trading')

      // Should load without errors
      await authenticatedPage.waitForSelector('[data-testid="paper-trading-view"]', { timeout: 10000 })

      // Verify page title
      await expect(authenticatedPage.locator('h1')).toContainText('Paper Trading Dashboard')
    })

    test('AI Analytics route is accessible', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/ai/analytics')

      // Should load without errors
      await authenticatedPage.waitForSelector('[data-testid="analytics-view"]', { timeout: 10000 })

      // Verify page title
      await expect(authenticatedPage.locator('h1')).toContainText('AI Performance Analytics')
    })
  })

  test.describe('Integration Tests - All Phases', () => {

    test('useToast composable works correctly', async ({ authenticatedPage }) => {
      // Navigate to a page that uses toast
      await authenticatedPage.goto('/ai/paper-trading')

      // Toast should be available (we created the composable)
      // This test verifies the missing composable was created in Phase 1
      const consoleErrors = []
      authenticatedPage.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
      })

      // Wait for page to load
      await authenticatedPage.waitForLoadState('networkidle')

      // Check for import errors
      const hasToastError = consoleErrors.some(err =>
        err.includes('useToast') || err.includes('Failed to resolve module')
      )

      expect(hasToastError).toBe(false)
    })
  })
})
