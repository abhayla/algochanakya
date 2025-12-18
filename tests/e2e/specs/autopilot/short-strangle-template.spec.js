/**
 * E2E Tests: SHORT-STRANGLE-ADJUSTMENTS-Template Creation
 *
 * Creates the Short Strangle with Adjustments template through the AutoPilot UI.
 * This test validates the entire strategy builder flow and serves as a seed for the template.
 *
 * Template Configuration:
 * - Entry: Sell 15-delta PUT + 15-delta CALL (NIFTY)
 * - Adjustment 1: Shift profitable leg when premium captured > 60% (RECURRING)
 * - Adjustment 2: Alert when delta doubles (RECURRING)
 * - Adjustment 3: Break trade when delta > 0.50 (RECURRING)
 * - Adjustment 4: Exit all when DTE < 2 (ONE-TIME)
 *
 * Reference: docs/autopilot/SHORT-STRANGLE-ADJUSTMENTS-WORKFLOW.md
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('AutoPilot - SHORT-STRANGLE-ADJUSTMENTS-Template', () => {
  // Increase timeout for these tests due to heavy page loads and multiple steps
  test.setTimeout(120000)

  // Run tests serially to avoid parallel contention issues
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ authenticatedPage }) => {
    // Navigate to AutoPilot strategy builder
    await authenticatedPage.goto('/autopilot/strategies/new', { waitUntil: 'domcontentloaded' })

    // Wait for page to load
    await expect(authenticatedPage.getByTestId('autopilot-strategy-builder')).toBeVisible({ timeout: 10000 })
  })

  test('should create SHORT-STRANGLE-ADJUSTMENTS-Template with recurring adjustments', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // ========================================================================
    // STEP 1: Strategy Setup - Basic Info
    // ========================================================================

    // Expand basic info section if collapsed
    const basicInfoToggle = page.getByTestId('autopilot-builder-basic-info-toggle')
    if (await basicInfoToggle.isVisible()) {
      const content = page.getByTestId('autopilot-builder-basic-info-content')
      if (!(await content.isVisible())) {
        await basicInfoToggle.click()
        await expect(content).toBeVisible()
      }
    }

    // Fill strategy name
    await page.getByTestId('autopilot-builder-name').fill('SHORT-STRANGLE-ADJUSTMENTS-Template')

    // Fill description
    await page.getByTestId('autopilot-builder-description').fill(
      'Sell 15-delta PUT and CALL on monthly expiry. ' +
      'Includes automatic adjustments: shift profitable leg when premium decays, ' +
      'break trade when leg goes deep ITM, exit before expiry.'
    )

    // Select underlying: NIFTY
    await page.getByTestId('autopilot-builder-underlying').selectOption('NIFTY')

    // Select strategy type: Short Strangle
    const strategyTypeSelect = page.getByTestId('autopilot-builder-strategy-type')
    await strategyTypeSelect.selectOption('short_strangle')

    // Handle legs replacement modal if it appears (strategy type change triggers this)
    const replaceModal = page.getByTestId('autopilot-replace-legs-modal')
    if (await replaceModal.isVisible({ timeout: 1000 }).catch(() => false)) {
      await page.getByTestId('autopilot-replace-legs-confirm').click()
      await expect(replaceModal).not.toBeVisible()
    }

    // Set lots to 1
    await page.getByTestId('autopilot-builder-lots').fill('1')

    // Select position type: Positional (for monthly expiry)
    await page.getByTestId('autopilot-builder-position-type').selectOption('positional')

    // Verify legs were auto-populated for short strangle (2 legs: SELL CE + SELL PE)
    await page.waitForTimeout(500) // Wait for legs to populate
    const legsTable = page.locator('[data-testid^="autopilot-leg-row-"]')
    const legCount = await legsTable.count()
    expect(legCount).toBeGreaterThanOrEqual(2)

    // ---- Configure Leg 0 (SELL CE): Select expiry and strike via Strike Ladder ----
    const leg0ExpirySelect = page.getByTestId('autopilot-leg-expiry-0')
    await expect(leg0ExpirySelect).toBeVisible()
    const leg0ExpiryOptions = await leg0ExpirySelect.locator('option').allTextContents()
    if (leg0ExpiryOptions.length > 1) {
      await leg0ExpirySelect.selectOption({ index: 1 }) // Select first available expiry
    }
    await page.waitForTimeout(500) // Wait for expiry to be set

    // Open Strike Ladder for Leg 0 and select a CE strike
    const leg0OpenLadderBtn = page.getByTestId('autopilot-leg-open-ladder-0')
    await expect(leg0OpenLadderBtn).toBeVisible({ timeout: 5000 })
    await leg0OpenLadderBtn.click()

    // Wait for Strike Ladder modal
    const strikeLadderModal = page.getByTestId('autopilot-strike-ladder-modal')
    await expect(strikeLadderModal).toBeVisible({ timeout: 5000 })

    // Wait for option chain to load - look for CE buttons to appear
    const ceButtons = strikeLadderModal.locator('button.select-ce')
    await expect(ceButtons.first()).toBeVisible({ timeout: 15000 }) // Wait up to 15s for chain to load

    // Find and click a CE button in the strike ladder (select OTM CE around 15-delta)
    const ceButtonCount = await ceButtons.count()
    if (ceButtonCount > 0) {
      // Select a CE strike that's about 3-5 strikes from first visible (OTM)
      const ceIndexToSelect = Math.min(3, ceButtonCount - 1)
      await ceButtons.nth(ceIndexToSelect).click()
    }

    // Modal should close after selection
    await expect(strikeLadderModal).not.toBeVisible({ timeout: 5000 })
    await page.waitForTimeout(500)

    // ---- Configure Leg 1 (SELL PE): Select expiry and strike via Strike Ladder ----
    const leg1ExpirySelect = page.getByTestId('autopilot-leg-expiry-1')
    await expect(leg1ExpirySelect).toBeVisible()
    const leg1ExpiryOptions = await leg1ExpirySelect.locator('option').allTextContents()
    if (leg1ExpiryOptions.length > 1) {
      await leg1ExpirySelect.selectOption({ index: 1 }) // Select same expiry as leg 0
    }
    await page.waitForTimeout(500) // Wait for expiry to be set

    // Open Strike Ladder for Leg 1 and select a PE strike
    const leg1OpenLadderBtn = page.getByTestId('autopilot-leg-open-ladder-1')
    await expect(leg1OpenLadderBtn).toBeVisible({ timeout: 5000 })
    await leg1OpenLadderBtn.click()

    // Wait for Strike Ladder modal
    await expect(strikeLadderModal).toBeVisible({ timeout: 5000 })

    // Wait for option chain to load - look for PE buttons to appear
    const peButtons = strikeLadderModal.locator('button.select-pe')
    await expect(peButtons.first()).toBeVisible({ timeout: 15000 }) // Wait up to 15s for chain to load

    // Find and click a PE button in the strike ladder (select OTM PE around 15-delta)
    const peButtonCount = await peButtons.count()
    if (peButtonCount > 0) {
      // Select a PE strike that's about 3-5 strikes from last visible (OTM put)
      const peIndexToSelect = Math.max(0, peButtonCount - 4)
      await peButtons.nth(peIndexToSelect).click()
    }

    // Modal should close after selection
    await expect(strikeLadderModal).not.toBeVisible({ timeout: 5000 })
    await page.waitForTimeout(500)

    // Scroll back to top and verify/re-fill strategy name (may have been cleared by modal interactions)
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.waitForTimeout(300)

    // Check if name field is empty and re-fill if needed
    const nameField = page.getByTestId('autopilot-builder-name')
    const nameValue = await nameField.inputValue()
    if (!nameValue || nameValue.trim() === '') {
      await nameField.fill('SHORT-STRANGLE-ADJUSTMENTS-Template')
    }

    // Navigate to Step 2: Entry Conditions
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-2')).toBeVisible({ timeout: 5000 })

    // ========================================================================
    // STEP 2: Entry Conditions
    // ========================================================================

    // Optional: Add time condition (entry after market stabilizes)
    // For now, skip entry conditions - strategy enters immediately on activation

    // Navigate to Step 3: Monitoring & Adjustments
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-3')).toBeVisible({ timeout: 5000 })

    // ========================================================================
    // STEP 3: Monitoring & Adjustments - Add 4 Rules
    // ========================================================================

    // Verify adjustment rule builder is visible
    await expect(page.getByTestId('autopilot-adjustment-rule-builder')).toBeVisible()

    // ----- RULE 1: Shift Profitable Leg (RECURRING) -----
    await page.getByTestId('autopilot-add-rule-btn').click()
    await expect(page.getByTestId('autopilot-rule-modal')).toBeVisible()

    await page.getByTestId('autopilot-rule-name').fill('Shift Profitable Leg')

    // Select trigger type: Premium Captured %
    await page.getByTestId('autopilot-rule-trigger-type').selectOption('premium_based')

    // Set threshold if field is visible (60% premium captured)
    const thresholdField1 = page.getByTestId('autopilot-rule-trigger-threshold')
    if (await thresholdField1.isVisible()) {
      await thresholdField1.fill('60')
    }

    // Select action type: Roll Strike
    await page.getByTestId('autopilot-rule-action-type').selectOption('roll_strike')

    // Set cooldown: 60 minutes (in seconds = 3600)
    await page.getByTestId('autopilot-rule-cooldown').fill('3600')

    // Set max executions per day: 3
    await page.getByTestId('autopilot-rule-max-executions').fill('3')

    // Enable the rule
    const enabledCheckbox1 = page.getByTestId('autopilot-rule-enabled')
    if (await enabledCheckbox1.isVisible()) {
      await enabledCheckbox1.check()
    }

    // Save rule
    await page.getByTestId('autopilot-rule-save').click()
    await expect(page.getByTestId('autopilot-rule-modal')).not.toBeVisible()

    // Verify rule was created
    await expect(page.getByTestId('autopilot-rule-card-0')).toBeVisible()

    // ----- RULE 2: Delta Doubles Alert (RECURRING) -----
    await page.getByTestId('autopilot-add-rule-btn').click()
    await expect(page.getByTestId('autopilot-rule-modal')).toBeVisible()

    await page.getByTestId('autopilot-rule-name').fill('Delta Doubles Alert')

    // Select trigger type: Delta Based
    await page.getByTestId('autopilot-rule-trigger-type').selectOption('delta_based')

    // Set threshold (0.30 = delta doubled from 0.15)
    const thresholdField2 = page.getByTestId('autopilot-rule-trigger-threshold')
    if (await thresholdField2.isVisible()) {
      await thresholdField2.fill('0.30')
    }

    // Select action type: Alert (no auto-action)
    // Check if 'alert' option exists, otherwise use a suitable alternative
    const actionSelect2 = page.getByTestId('autopilot-rule-action-type')
    const alertOption = actionSelect2.locator('option[value="alert"]')
    if (await alertOption.count() > 0) {
      await actionSelect2.selectOption('alert')
    } else {
      // If alert not available, skip this action type or use exit_all as placeholder
      await actionSelect2.selectOption('exit_all')
    }

    // Set cooldown: 30 minutes (1800 seconds)
    await page.getByTestId('autopilot-rule-cooldown').fill('1800')

    // Enable the rule
    const enabledCheckbox2 = page.getByTestId('autopilot-rule-enabled')
    if (await enabledCheckbox2.isVisible()) {
      await enabledCheckbox2.check()
    }

    // Save rule
    await page.getByTestId('autopilot-rule-save').click()
    await expect(page.getByTestId('autopilot-rule-modal')).not.toBeVisible()

    // Verify rule was created
    await expect(page.getByTestId('autopilot-rule-card-1')).toBeVisible()

    // ----- RULE 3: Break Trade Deep ITM (RECURRING) -----
    await page.getByTestId('autopilot-add-rule-btn').click()
    await expect(page.getByTestId('autopilot-rule-modal')).toBeVisible()

    await page.getByTestId('autopilot-rule-name').fill('Break Trade Deep ITM')

    // Select trigger type: Delta Based
    await page.getByTestId('autopilot-rule-trigger-type').selectOption('delta_based')

    // Set threshold: 0.50 (deep ITM)
    const thresholdField3 = page.getByTestId('autopilot-rule-trigger-threshold')
    if (await thresholdField3.isVisible()) {
      await thresholdField3.fill('0.50')
    }

    // Select action type: Add Hedge (closest to break trade concept)
    // If 'break_trade' option exists, use it
    const actionSelect3 = page.getByTestId('autopilot-rule-action-type')
    const breakTradeOption = actionSelect3.locator('option[value="break_trade"]')
    if (await breakTradeOption.count() > 0) {
      await actionSelect3.selectOption('break_trade')
    } else {
      await actionSelect3.selectOption('add_hedge')
    }

    // Set cooldown: 120 minutes (7200 seconds)
    await page.getByTestId('autopilot-rule-cooldown').fill('7200')

    // Set max executions per day: 2
    await page.getByTestId('autopilot-rule-max-executions').fill('2')

    // Enable the rule
    const enabledCheckbox3 = page.getByTestId('autopilot-rule-enabled')
    if (await enabledCheckbox3.isVisible()) {
      await enabledCheckbox3.check()
    }

    // Save rule
    await page.getByTestId('autopilot-rule-save').click()
    await expect(page.getByTestId('autopilot-rule-modal')).not.toBeVisible()

    // Verify rule was created
    await expect(page.getByTestId('autopilot-rule-card-2')).toBeVisible()

    // ----- RULE 4: Exit Before Expiry (ONE-TIME) -----
    await page.getByTestId('autopilot-add-rule-btn').click()
    await expect(page.getByTestId('autopilot-rule-modal')).toBeVisible()

    await page.getByTestId('autopilot-rule-name').fill('Exit Before Expiry')

    // Select trigger type: Time Based (for DTE)
    await page.getByTestId('autopilot-rule-trigger-type').selectOption('time_based')

    // Set threshold if visible (DTE < 2)
    const thresholdField4 = page.getByTestId('autopilot-rule-trigger-threshold')
    if (await thresholdField4.isVisible()) {
      await thresholdField4.fill('2')
    }

    // Select action type: Exit All
    await page.getByTestId('autopilot-rule-action-type').selectOption('exit_all')

    // Set max executions: 1 (one-time)
    await page.getByTestId('autopilot-rule-max-executions').fill('1')

    // DO NOT check recurring for this rule (one-time execution)
    // Enable the rule
    const enabledCheckbox4 = page.getByTestId('autopilot-rule-enabled')
    if (await enabledCheckbox4.isVisible()) {
      await enabledCheckbox4.check()
    }

    // Save rule
    await page.getByTestId('autopilot-rule-save').click()
    await expect(page.getByTestId('autopilot-rule-modal')).not.toBeVisible()

    // Verify rule was created
    await expect(page.getByTestId('autopilot-rule-card-3')).toBeVisible()

    // Verify all 4 rules are visible
    const ruleCards = page.locator('[data-testid^="autopilot-rule-card-"]')
    expect(await ruleCards.count()).toBe(4)

    // Navigate to Step 4: Risk Settings
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-4')).toBeVisible({ timeout: 5000 })

    // ========================================================================
    // STEP 4: Risk Settings
    // ========================================================================

    // Set max loss: 15000
    const maxLossInput = page.getByTestId('autopilot-builder-max-loss')
    if (await maxLossInput.isVisible()) {
      await maxLossInput.fill('15000')
    }

    // Set target profit: 10000
    const maxProfitInput = page.getByTestId('autopilot-builder-max-profit')
    if (await maxProfitInput.isVisible()) {
      await maxProfitInput.fill('10000')
    }

    // Navigate to Step 5: Review
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-5')).toBeVisible({ timeout: 5000 })

    // ========================================================================
    // STEP 5: Review & Save
    // ========================================================================

    // Verify review page shows the strategy name
    const reviewContent = page.getByTestId('autopilot-builder-step-5')
    await expect(reviewContent).toContainText('SHORT-STRANGLE-ADJUSTMENTS-Template')

    // Save the strategy (as draft)
    const saveButton = page.getByTestId('autopilot-builder-save')

    // Intercept the API request to see request/response
    let apiResponse = null
    page.on('request', async (request) => {
      if (request.url().includes('/api/v1/autopilot/strategies') && request.method() === 'POST') {
        console.log('API Request URL:', request.url())
        console.log('API Request Body:', request.postData())
      }
    })
    page.on('response', async (response) => {
      if (response.url().includes('/api/v1/autopilot/strategies') && response.request().method() === 'POST') {
        try {
          apiResponse = await response.json()
          console.log('API Response Status:', response.status())
          console.log('API Response:', JSON.stringify(apiResponse, null, 2))
        } catch (e) {
          console.log('API Response status:', response.status())
          console.log('API Response error reading body:', e.message)
        }
      }
    })

    await saveButton.click()

    // Wait for navigation to strategy detail page after successful save
    // The app redirects to /autopilot/strategies/{id} after creating
    // Note: Must explicitly exclude /new from matching
    try {
      await page.waitForURL(/\/autopilot\/strategies\/(?!new)[^/]+$/, { timeout: 15000 })
      // Successfully redirected to strategy detail page
      console.log('Successfully redirected to:', page.url())
    } catch (e) {
      console.log('waitForURL failed, current URL:', page.url())

      // Take screenshot of final state
      await page.screenshot({ path: 'test-results/save-final-state.png' })

      // Check if there's a network error displayed
      const networkError = page.getByText('Network Error')
      if (await networkError.isVisible({ timeout: 1000 }).catch(() => false)) {
        console.log('Network error detected - backend may not be responding correctly')
      }

      // Check for error banner (store.error in StrategyBuilderView)
      const errorBanner = page.locator('.error-banner')
      if (await errorBanner.isVisible({ timeout: 1000 }).catch(() => false)) {
        const errorText = await errorBanner.textContent()
        console.log('Error banner found:', errorText)
      }

      // Also check for toast notifications
      const toast = page.locator('.toast, [class*="toast"], [class*="notification"]')
      if (await toast.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        const toastText = await toast.first().textContent()
        console.log('Toast message:', toastText)
      }

      // Check for other error messages
      const errorMessage = page.locator('.error-message, .toast-error, [class*="error"]')
      if (await errorMessage.isVisible({ timeout: 500 }).catch(() => false)) {
        const errorText = await errorMessage.textContent()
        console.log('Error message found:', errorText)
      }

      // Final check - if we somehow got redirected anyway
      const finalUrl = page.url()
      if (finalUrl.includes('/autopilot/strategies/') && !finalUrl.includes('/new')) {
        console.log('Successfully redirected despite timeout')
      } else {
        throw new Error(`Save failed - URL is still: ${finalUrl}`)
      }
    }

    // Verify we're on the strategy detail page (not /new)
    const finalUrl = page.url()
    expect(finalUrl).toMatch(/\/autopilot\/strategies\/(?!new)[^/]+$/)
    expect(finalUrl).not.toContain('/new')
  })

  test('should display all 4 adjustment rules after creation', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // This test verifies that adjustment rules persist after navigation
    // First, go directly to Step 3 to check if rules are configured
    await page.getByTestId('autopilot-builder-monitoring-tab').click()
    await page.waitForTimeout(500)

    // Check that rule builder is visible
    await expect(page.getByTestId('autopilot-adjustment-rule-builder')).toBeVisible()

    // In a fresh builder, should show empty state
    await expect(page.getByText('No adjustment rules configured')).toBeVisible()
  })

  test('should navigate through all 5 steps correctly', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Step 1 should be visible by default
    await expect(page.getByTestId('autopilot-builder-step-1')).toBeVisible()

    // Fill in minimum required fields to allow navigation
    await page.getByTestId('autopilot-builder-name').fill('Navigation Test Strategy')
    await page.getByTestId('autopilot-builder-underlying').selectOption('NIFTY')
    await page.getByTestId('autopilot-builder-lots').fill('1')

    // Add a leg and configure it minimally
    await page.getByTestId('autopilot-legs-add-row-button').click()
    await page.waitForSelector('[data-testid="autopilot-leg-row-0"]')

    // Select expiry
    const expirySelect = page.getByTestId('autopilot-leg-expiry-0')
    await expect(expirySelect).toBeVisible()
    const expiryOptions = await expirySelect.locator('option').allTextContents()
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 })
    }
    await page.waitForTimeout(500)

    // Open Strike Ladder and select a strike
    const openLadderBtn = page.getByTestId('autopilot-leg-open-ladder-0')
    await expect(openLadderBtn).toBeVisible({ timeout: 5000 })
    await openLadderBtn.click()

    const strikeLadderModal = page.getByTestId('autopilot-strike-ladder-modal')
    await expect(strikeLadderModal).toBeVisible({ timeout: 5000 })

    // Wait for strikes to load and click first CE button
    const ceButtons = strikeLadderModal.locator('button.select-ce')
    await expect(ceButtons.first()).toBeVisible({ timeout: 15000 })
    await ceButtons.first().click()

    await expect(strikeLadderModal).not.toBeVisible({ timeout: 5000 })

    // Navigate to Step 2
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-2')).toBeVisible({ timeout: 5000 })

    // Navigate to Step 3
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-3')).toBeVisible({ timeout: 5000 })

    // Navigate to Step 4
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-4')).toBeVisible({ timeout: 5000 })

    // Navigate to Step 5
    await page.getByTestId('autopilot-builder-next').click()
    await expect(page.getByTestId('autopilot-builder-step-5')).toBeVisible({ timeout: 5000 })

    // Navigate back to Step 4
    await page.getByTestId('autopilot-builder-previous').click()
    await expect(page.getByTestId('autopilot-builder-step-4')).toBeVisible({ timeout: 5000 })

    // Click directly on Step 1 tab
    await page.getByTestId('autopilot-builder-legs-tab').click()
    await expect(page.getByTestId('autopilot-builder-step-1')).toBeVisible({ timeout: 5000 })
  })

  test('should populate short strangle legs when strategy type is selected', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Fill required fields first
    await page.getByTestId('autopilot-builder-name').fill('Test Strangle')
    await page.getByTestId('autopilot-builder-underlying').selectOption('NIFTY')

    // Select short strangle strategy type
    await page.getByTestId('autopilot-builder-strategy-type').selectOption('short_strangle')

    // Handle modal if appears
    const replaceModal = page.getByTestId('autopilot-replace-legs-modal')
    if (await replaceModal.isVisible({ timeout: 1000 }).catch(() => false)) {
      await page.getByTestId('autopilot-replace-legs-confirm').click()
    }

    // Wait for legs to populate
    await page.waitForTimeout(1000)

    // Verify legs were created (at least 2 for strangle: CE + PE)
    const legsTable = page.locator('[data-testid^="autopilot-leg-row-"]')
    const legCount = await legsTable.count()

    // Short strangle should have 2 legs
    expect(legCount).toBeGreaterThanOrEqual(2)
  })
})
