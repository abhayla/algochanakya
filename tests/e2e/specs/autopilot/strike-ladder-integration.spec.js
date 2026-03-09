/**
 * E2E Test: StrikeLadder Integration (Phase 1.5)
 *
 * Tests the integration of StrikeLadder modal in AutoPilot strategy builder.
 * Verifies spot price fetching, modal behavior, and strike selection flow.
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('StrikeLadder Integration', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new')
    await authenticatedPage.waitForLoadState('networkidle')
  })

  test('should open StrikeLadder modal when grid button clicked', async ({ authenticatedPage }) => {
    // Fill basic info
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test StrikeLadder')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.fill('[data-testid="autopilot-builder-lots"]', '1')

    // Add a leg
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Select leg details
    await authenticatedPage.selectOption('[data-testid="autopilot-leg-action-0"]', 'SELL')
    await authenticatedPage.selectOption('[data-testid="autopilot-leg-type-0"]', 'CE')

    // Select expiry (first available option)
    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Click grid button to open StrikeLadder
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')

    // Wait for modal to appear
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible',
      timeout: 3000
    })

    // Verify modal is visible
    const modal = authenticatedPage.locator('[data-testid="autopilot-strike-ladder-modal"]')
    await expect(modal).toBeVisible()

    // Verify modal content
    const modalTitle = authenticatedPage.locator('[data-testid="autopilot-ladder-modal-title"]')
    await expect(modalTitle).toContainText('Strike Ladder - NIFTY')

    // Verify close button exists
    const closeButton = authenticatedPage.locator('[data-testid="autopilot-strike-ladder-close"]')
    await expect(closeButton).toBeVisible()
  })

  test('should fetch real spot price from API', async ({ authenticatedPage }) => {
    // Setup network monitoring
    const spotPriceRequests = []
    authenticatedPage.on('request', request => {
      if (request.url().includes('/api/v1/autopilot/spot-price/')) {
        spotPriceRequests.push(request)
      }
    })

    const spotPriceResponses = []
    authenticatedPage.on('response', response => {
      if (response.url().includes('/api/v1/autopilot/spot-price/')) {
        spotPriceResponses.push(response)
      }
    })

    // Fill basic info
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Spot Price')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')

    // Add a leg
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Select expiry
    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Clear previous requests
    spotPriceRequests.length = 0
    spotPriceResponses.length = 0

    // Click grid button
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')

    // Wait for spot price API call
    await authenticatedPage.waitForLoadState('domcontentloaded')

    // Verify API call was made
    expect(spotPriceRequests.length).toBeGreaterThan(0)
    expect(spotPriceResponses.length).toBeGreaterThan(0)

    // Verify response
    const response = spotPriceResponses[0]
    expect(response.status()).toBe(200)

    const responseBody = await response.json()
    expect(responseBody).toHaveProperty('data')
    expect(responseBody.data).toHaveProperty('ltp')
    expect(responseBody.data).toHaveProperty('symbol')
    expect(responseBody.data.symbol).toBe('NIFTY')

    // Verify LTP is a finite positive number
    const ltp = responseBody.data.ltp
    expect(Number.isFinite(ltp)).toBe(true)
    expect(ltp).toBeGreaterThan(0)
    expect(ltp).toBeLessThan(100000) // Sanity check
  })

  test('should close modal when close button clicked', async ({ authenticatedPage }) => {
    // Setup and open modal
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Close')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Select expiry
    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'visible' })

    // Click close button
    await authenticatedPage.click('[data-testid="autopilot-strike-ladder-close"]')

    // Verify modal is hidden
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'hidden' })
    const modal = authenticatedPage.locator('[data-testid="autopilot-strike-ladder-modal"]')
    await expect(modal).not.toBeVisible()
  })

  test('should close modal when clicking outside', async ({ authenticatedPage }) => {
    // Setup and open modal
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Outside Click')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'visible' })

    // Click on overlay (outside modal content)
    await authenticatedPage.click('[data-testid="autopilot-strike-ladder-modal"]', { position: { x: 10, y: 10 } })

    // Verify modal is hidden
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'hidden' })
  })

  test('should work with different underlyings', async ({ authenticatedPage }) => {
    const underlyings = ['NIFTY', 'BANKNIFTY']

    for (const underlying of underlyings) {
      // Fill basic info
      await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', `Test ${underlying}`)
      await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', underlying)

      // Add a leg
      await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
      await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

      const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
      const expiryOptions = await expirySelect.locator('option').allTextContents()
      if (expiryOptions.length > 1) {
        await expirySelect.selectOption({ index: 1 })
      }

      // Setup response monitoring
      let spotPriceResponse = null
      authenticatedPage.on('response', response => {
        if (response.url().includes(`/api/v1/autopilot/spot-price/${underlying}`)) {
          spotPriceResponse = response
        }
      })

      // Open modal
      await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
      await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'visible' })

      // Wait for API response
      await authenticatedPage.waitForLoadState('domcontentloaded')

      // Verify correct underlying in modal title
      const modalTitle = authenticatedPage.locator('[data-testid="autopilot-ladder-modal-title"]')
      await expect(modalTitle).toContainText(`Strike Ladder - ${underlying}`)

      // Close modal
      await authenticatedPage.click('[data-testid="autopilot-strike-ladder-close"]')
      await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'hidden' })

      // Remove leg for next iteration
      await authenticatedPage.click('[data-testid="autopilot-leg-delete-0"]')
    }
  })

  test('should handle API failure gracefully with fallback', async ({ authenticatedPage }) => {
    // Check console for error message - set up listener BEFORE the error occurs
    const consoleMessages = []
    authenticatedPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleMessages.push(msg.text())
      }
    })

    // Intercept and fail the spot price API call
    await authenticatedPage.route('**/api/v1/autopilot/spot-price/**', route => {
      route.abort('failed')
    })

    // Setup
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Fallback')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Open modal - should still work with fallback
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')

    // Modal should still open despite API failure
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible',
      timeout: 3000
    })

    const modal = authenticatedPage.locator('[data-testid="autopilot-strike-ladder-modal"]')
    await expect(modal).toBeVisible()

    // Should have logged the error
    await authenticatedPage.waitForLoadState('domcontentloaded')
    expect(consoleMessages.some(msg => msg.includes('Error fetching spot price'))).toBe(true)
  })

  test('should work with multiple legs independently', async ({ authenticatedPage }) => {
    // Setup
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Multiple Legs')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')

    // Add first leg
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Add second leg
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-1"]')

    // Set expiry for both legs
    for (let i = 0; i < 2; i++) {
      const expirySelect = authenticatedPage.locator(`[data-testid="autopilot-leg-expiry-${i}"]`)
      const expiryOptions = await expirySelect.locator('option').allTextContents()
      if (expiryOptions.length > 1) {
        await expirySelect.selectOption({ index: 1 })
      }
    }

    // Open modal for first leg
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'visible' })

    // Close modal
    await authenticatedPage.click('[data-testid="autopilot-strike-ladder-close"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'hidden' })

    // Open modal for second leg
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-1"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'visible' })

    // Verify modal opened
    const modal = authenticatedPage.locator('[data-testid="autopilot-strike-ladder-modal"]')
    await expect(modal).toBeVisible()
  })

  test('should not have console errors', async ({ authenticatedPage }) => {
    const consoleErrors = []
    authenticatedPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // Full flow
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Console Errors')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', { state: 'visible' })
    await authenticatedPage.waitForLoadState('domcontentloaded') // Wait for any async operations

    // Filter out known/acceptable errors
    const criticalErrors = consoleErrors.filter(error =>
      !error.includes('DevTools') && // Ignore DevTools messages
      !error.includes('Extension') && // Ignore extension errors
      !error.includes('favicon') // Ignore favicon errors
    )

    expect(criticalErrors.length).toBe(0)
  })
})
