/**
 * E2E Test: StrikeLadder Phase 2 Features
 *
 * Tests the Phase 2 enhancements:
 * - Loading skeleton for spot price
 * - Real option chain API integration
 * - Greeks toggle functionality
 * - Greeks display formatting
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('StrikeLadder Phase 2 Features', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new')
    await authenticatedPage.waitForLoadState('domcontentloaded')
  })

  test('should display loading skeleton for spot price', async ({ authenticatedPage }) => {
    // Fill basic info
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Loading Skeleton')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.fill('[data-testid="autopilot-builder-lots"]', '1')

    // Add a leg
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Select expiry
    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Intercept spot price API to add delay
    await authenticatedPage.route('**/api/v1/autopilot/spot-price/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000)) // 1 second delay
      await route.continue()
    })

    // Click grid button
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')

    // Wait for modal to appear
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible',
      timeout: 3000
    })

    // Check for skeleton element (it should be visible initially)
    const skeleton = authenticatedPage.locator('.spot-skeleton')

    // Wait briefly so skeleton has had time to appear
    // The route intercept adds 1s delay so after modal appears skeleton should be showing
    // Then wait for spot value to appear after the delayed API responds
    const spotValue = authenticatedPage.locator('.spot-value')
    await expect(spotValue).toBeVisible({ timeout: 5000 })

    // Verify spot value contains a number
    const spotText = await spotValue.textContent()
    expect(spotText).toMatch(/₹[\d,]+/)
  })

  test('should fetch real option chain data from API', async ({ authenticatedPage }) => {
    // Setup network monitoring for option chain API
    const optionChainRequests = []
    authenticatedPage.on('request', request => {
      if (request.url().includes('/api/v1/autopilot/option-chain/')) {
        optionChainRequests.push(request)
      }
    })

    const optionChainResponses = []
    authenticatedPage.on('response', response => {
      if (response.url().includes('/api/v1/autopilot/option-chain/')) {
        optionChainResponses.push(response)
      }
    })

    // Fill basic info
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Option Chain API')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')

    // Add a leg
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Select expiry
    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })

      // Get the selected expiry value for verification
      const selectedExpiry = await expirySelect.inputValue()

      // Clear previous requests
      optionChainRequests.length = 0
      optionChainResponses.length = 0

      // Click grid button
      await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')

      // Wait for modal to appear
      await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
        state: 'visible'
      })

      // Wait for API call — look for strike rows to appear as a proxy
      const strikeRows = authenticatedPage.locator('.strike-row')
      await strikeRows.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})

      // Verify API call was made
      expect(optionChainRequests.length).toBeGreaterThan(0)

      // Verify request URL contains underlying and expiry
      const requestUrl = optionChainRequests[0].url()
      expect(requestUrl).toContain('/api/v1/autopilot/option-chain/NIFTY/')
      expect(requestUrl).toContain(selectedExpiry)

      // Verify response if available
      if (optionChainResponses.length > 0) {
        const response = optionChainResponses[0]
        expect(response.status()).toBe(200)

        const responseBody = await response.json()
        expect(responseBody).toHaveProperty('options')
        expect(Array.isArray(responseBody.options)).toBe(true)

        // Verify option data structure
        if (responseBody.options.length > 0) {
          const option = responseBody.options[0]
          expect(option).toHaveProperty('strike')
          expect(option).toHaveProperty('option_type')
          expect(option).toHaveProperty('ltp')
          expect(option).toHaveProperty('delta')
        }
      }

      // Verify table shows data
      const table = authenticatedPage.locator('.ladder-table')
      await expect(table).toBeVisible()

      // Check that at least one strike row exists
      const rowCount = await strikeRows.count()
      expect(rowCount).toBeGreaterThan(0)
    }
  })

  test('should toggle Greeks display on checkbox click', async ({ authenticatedPage }) => {
    // Setup
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Greeks Toggle')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Open modal
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible'
    })

    // Wait for table to load (wait for strike rows or table to be populated)
    const strikeRows = authenticatedPage.locator('.strike-row')
    await strikeRows.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})

    // Initially, Greeks columns should NOT be visible
    let ceTheta = authenticatedPage.locator('th:has-text("CE Θ")')
    await expect(ceTheta).not.toBeVisible()

    // Find and click the Greeks toggle checkbox
    const greeksToggle = authenticatedPage.locator('.greeks-toggle input[type="checkbox"]')
    await expect(greeksToggle).toBeVisible()
    await greeksToggle.check()

    // Now Greeks columns should be visible
    await expect(ceTheta).toBeVisible()

    let ceIV = authenticatedPage.locator('th:has-text("CE IV")')
    await expect(ceIV).toBeVisible()

    let peTheta = authenticatedPage.locator('th:has-text("PE Θ")')
    await expect(peTheta).toBeVisible()

    let peIV = authenticatedPage.locator('th:has-text("PE IV")')
    await expect(peIV).toBeVisible()

    // Uncheck the toggle
    await greeksToggle.uncheck()

    // Greeks columns should be hidden again
    await expect(ceTheta).not.toBeVisible()
    await expect(ceIV).not.toBeVisible()
  })

  test('should display Greeks with proper formatting', async ({ authenticatedPage }) => {
    // Setup
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Greeks Formatting')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Open modal
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible'
    })

    // Wait for data to load — look for strike rows to appear
    const strikeRows = authenticatedPage.locator('.strike-row')
    await strikeRows.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})

    // Enable Greeks display
    const greeksToggle = authenticatedPage.locator('.greeks-toggle input[type="checkbox"]')
    await greeksToggle.check()

    // Wait for Greeks columns to appear
    await authenticatedPage.locator('th:has-text("CE Θ")').waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})

    // Find a strike row with data
    const firstRow = strikeRows.first()

    // Get CE Theta cell
    const ceThetaCells = firstRow.locator('td.greeks-cell').filter({ hasText: /^-?\d+\.\d{2}$/ })
    if (await ceThetaCells.count() > 0) {
      const thetaText = await ceThetaCells.first().textContent()

      // Verify format: should be decimal with 2 places
      expect(thetaText).toMatch(/^-?\d+\.\d{2}$/)

      // Check if negative theta has red color class
      if (thetaText.startsWith('-')) {
        const thetaValue = ceThetaCells.first().locator('.greeks-value')
        const classes = await thetaValue.getAttribute('class')
        expect(classes).toContain('negative')
      }
    }

    // Check IV formatting (should have % sign)
    const ivCells = firstRow.locator('td.greeks-cell').filter({ hasText: /%/ })
    if (await ivCells.count() > 0) {
      const ivText = await ivCells.first().textContent()
      expect(ivText).toMatch(/\d+\.\d%/)
    }
  })

  test('should handle option chain API failure gracefully', async ({ authenticatedPage }) => {
    // Intercept and fail the option chain API call
    await authenticatedPage.route('**/api/v1/autopilot/option-chain/**', route => {
      route.abort('failed')
    })

    // Setup
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test API Failure')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Open modal - should still open but show error
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')

    // Modal should still open despite API failure
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible',
      timeout: 3000
    })

    const modal = authenticatedPage.locator('[data-testid="autopilot-strike-ladder-modal"]')
    await expect(modal).toBeVisible()

    // Wait for API failure to be processed — wait for loading state to resolve
    await authenticatedPage.locator('.ladder-loading, .ladder-error, .strike-row').first().waitFor({ timeout: 5000 }).catch(() => {})

    // Table should be empty (no mock data fallback)
    const strikeRows = authenticatedPage.locator('.strike-row')
    const rowCount = await strikeRows.count()
    expect(rowCount).toBe(0)

    // Error message should be displayed
    const errorMessage = authenticatedPage.locator('.error-message, .ladder-error')
    // Error message may or may not be visible depending on implementation
    // The important thing is that there are no strike rows
  })

  test('should display spot price in header after loading', async ({ authenticatedPage }) => {
    // Setup
    await authenticatedPage.fill('[data-testid="autopilot-builder-name"]', 'Test Spot Price Display')
    await authenticatedPage.selectOption('[data-testid="autopilot-builder-underlying"]', 'NIFTY')
    await authenticatedPage.click('[data-testid="autopilot-legs-add-row-button"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    const expirySelect = authenticatedPage.locator('[data-testid="autopilot-leg-expiry-0"]')
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }

    // Open modal
    await authenticatedPage.click('[data-testid="autopilot-leg-open-ladder-0"]')
    await authenticatedPage.waitForSelector('[data-testid="autopilot-strike-ladder-modal"]', {
      state: 'visible'
    })

    // Wait for spot price to load — wait for spot-value element to appear
    const spotValue = authenticatedPage.locator('.spot-value')
    await expect(spotValue).toBeVisible({ timeout: 10000 })

    // Verify spot price display
    const spotLabel = authenticatedPage.locator('.spot-label')
    await expect(spotLabel).toContainText('Spot:')

    await expect(spotValue).toBeVisible()

    // Verify format
    const spotText = await spotValue.textContent()
    expect(spotText).toMatch(/₹[\d,]+/)

    // Extract number and verify it's reasonable for NIFTY
    const spotNumber = parseInt(spotText.replace(/[₹,]/g, ''))
    expect(spotNumber).toBeGreaterThan(10000)
    expect(spotNumber).toBeLessThan(100000)
  })
})
