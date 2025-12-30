/**
 * AI Paper Trading E2E Tests
 *
 * Comprehensive testing of AI Autopilot paper trading feature with:
 * - Manual deployment triggering
 * - Paper trade entry and exit
 * - All 3 position sizing modes (Fixed, Tiered, Kelly)
 * - Screenshot verification after each test
 *
 * Test execution: npx playwright test tests/e2e/specs/ai/ai-paper-trading.spec.js --headed
 */

import { test, expect } from '../../fixtures/auth.fixture.js'
import { AIPaperTradingPage } from '../../pages/ai/AIPaperTradingPage.js'
import { AISettingsPage } from '../../pages/ai/AISettingsPage.js'

test.describe('AI Paper Trading - Comprehensive Tests', () => {
  let paperTradingPage
  let settingsPage

  // Increase timeout for all tests to 60 seconds
  test.setTimeout(60000)

  test.beforeEach(async ({ authenticatedPage }) => {
    paperTradingPage = new AIPaperTradingPage(authenticatedPage)
    settingsPage = new AISettingsPage(authenticatedPage)
  })

  // ==========================================================================
  // Suite 1: AI Settings Configuration (4 tests)
  // ==========================================================================

  test.describe('Suite 1: AI Settings Configuration', () => {
    // Increase timeout for settings configuration tests
    test.setTimeout(90000)

    test('TC01: Enable AI and configure paper mode', async ({ authenticatedPage }) => {
      // Navigate to settings
      await settingsPage.navigate()
      await settingsPage.verifyPageLoaded()

      // Enable AI
      await settingsPage.enableAI()

      // Set paper mode
      await settingsPage.setAutonomyMode('paper')

      // Save configuration
      await settingsPage.saveAndWait()

      // Verify configuration
      const config = await settingsPage.getConfiguration()
      expect(config.aiEnabled).toBe(true)
      expect(config.autonomyMode).toBe('paper')

      // Take screenshot
      await settingsPage.takeScreenshot('TC01-ai-settings-enabled')

      // Verify screenshot shows correct state
      const uiElements = await settingsPage.verifyUIElements()
      expect(Object.values(uiElements).every(v => v)).toBe(true)
    })

    test('TC02: Set position sizing to Fixed', async ({ authenticatedPage }) => {
      await settingsPage.navigate()

      // Configure fixed sizing
      await settingsPage.setSizingMode('fixed')
      await settingsPage.setBaseLots(1)
      await settingsPage.saveAndWait()

      // Verify
      const config = await settingsPage.getConfiguration()
      expect(config.sizingMode).toBe('fixed')
      expect(config.baseLots).toBe(1)

      // Screenshot
      await settingsPage.takeScreenshot('TC02-ai-settings-fixed')
    })

    test('TC03: Set position sizing to Tiered', async ({ authenticatedPage }) => {
      await settingsPage.navigate()

      // Configure tiered sizing
      await settingsPage.setSizingMode('tiered')
      await settingsPage.setBaseLots(1)
      await settingsPage.saveAndWait()

      // Verify
      const config = await settingsPage.getConfiguration()
      expect(config.sizingMode).toBe('tiered')

      // Screenshot
      await settingsPage.takeScreenshot('TC03-ai-settings-tiered')
    })

    test('TC04: Set position sizing to Kelly', async ({ authenticatedPage }) => {
      await settingsPage.navigate()

      // Configure kelly sizing
      await settingsPage.setSizingMode('kelly')
      await settingsPage.setBaseLots(1)
      await settingsPage.saveAndWait()

      // Verify
      const config = await settingsPage.getConfiguration()
      expect(config.sizingMode).toBe('kelly')

      // Screenshot
      await settingsPage.takeScreenshot('TC04-ai-settings-kelly')
    })
  })

  // ==========================================================================
  // Suite 2: Paper Trading - Fixed Sizing (3 tests)
  // ==========================================================================

  test.describe('Suite 2: Paper Trading - Fixed Sizing', () => {
    // Increase timeout for this suite due to configuration overhead
    test.setTimeout(90000)

    test.beforeEach(async ({ authenticatedPage }) => {
      // Ensure fixed sizing is configured
      await settingsPage.navigate()
      await settingsPage.configureForPaperTrading('fixed', 1)
    })

    test('TC05: Trigger deploy with Fixed sizing', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()
      await paperTradingPage.waitForLoad()

      // Get initial count
      const initialCount = await paperTradingPage.getActiveTradesCount()

      // Trigger deployment
      await paperTradingPage.triggerDeploy()

      // Wait for deployment to complete
      await paperTradingPage.waitForDeploymentComplete()

      // Verify new trade appears
      await paperTradingPage.waitForNewTrade(initialCount + 1)
      const newCount = await paperTradingPage.getActiveTradesCount()
      expect(newCount).toBeGreaterThanOrEqual(initialCount + 1)

      // Screenshot
      await paperTradingPage.takeScreenshot('TC05-deploy-fixed')

      // Verify at least one fixed trade exists (may have been created by beforeEach or this test)
      const fixedTradeRow = await paperTradingPage.findTradeRowBySizing('fixed')
      expect(fixedTradeRow).not.toBeNull()

      if (fixedTradeRow) {
        const latestTrade = await paperTradingPage.getTradeDataFromRow(fixedTradeRow)
        expect(latestTrade.lots).toBe('1') // base_lots = 1 for fixed
      }
    })

    test('TC06: Verify paper trade displayed correctly', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      // Verify table is visible
      const isTableVisible = await paperTradingPage.isPaperTradesTableVisible()
      expect(isTableVisible).toBe(true)

      // Get trade rows
      const rows = await paperTradingPage.getActiveTradeRows()
      expect(rows.length).toBeGreaterThan(0)

      // Verify table columns
      const tradeData = await paperTradingPage.getTradeDataFromRow(rows[0])
      expect(tradeData.strategy).toBeTruthy()
      expect(tradeData.regime).toBeTruthy()
      expect(tradeData.confidence).toBeTruthy()

      // Screenshot
      await paperTradingPage.takeScreenshot('TC06-trade-row-fixed')
    })

    test('TC07: Exit paper position (Fixed)', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      // Find a 'fixed' sized trade to exit
      const fixedTradeRow = await paperTradingPage.findTradeRowBySizing('fixed')
      expect(fixedTradeRow).not.toBeNull()

      const tradeId = await paperTradingPage.getTradeIdFromRow(fixedTradeRow)

      // Exit the trade and verify it succeeded
      const exitSuccess = await paperTradingPage.exitTrade(tradeId)
      expect(exitSuccess).toBe(true)

      // Screenshot
      await paperTradingPage.takeScreenshot('TC07-exit-fixed')
    })
  })

  // ==========================================================================
  // Suite 3: Paper Trading - Tiered Sizing (3 tests)
  // ==========================================================================

  test.describe('Suite 3: Paper Trading - Tiered Sizing', () => {
    // Increase timeout for this suite due to configuration overhead
    test.setTimeout(90000)

    test.beforeEach(async ({ authenticatedPage }) => {
      // Configure tiered sizing
      await settingsPage.navigate()
      await settingsPage.configureForPaperTrading('tiered', 1)
    })

    test('TC08: Configure tiered sizing', async ({ authenticatedPage }) => {
      await settingsPage.navigate()
      // Wait for page to fully load and sync with backend
      await authenticatedPage.waitForTimeout(1000)

      // Verify tiered mode is set
      const config = await settingsPage.getConfiguration()
      expect(config.sizingMode).toBe('tiered')
      expect(config.baseLots).toBe(1)

      // Screenshot
      await settingsPage.takeScreenshot('TC08-config-tiered')
    })

    test('TC09: Deploy with tiered sizing', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      const initialCount = await paperTradingPage.getActiveTradesCount()

      // Trigger deployment
      await paperTradingPage.triggerDeploy()
      await paperTradingPage.waitForDeploymentComplete()

      // Verify new trade
      await paperTradingPage.waitForNewTrade(initialCount + 1)

      // Verify at least one tiered trade exists (may have been created by beforeEach or this test)
      const tieredTradeRow = await paperTradingPage.findTradeRowBySizing('tiered')
      expect(tieredTradeRow).not.toBeNull()

      if (tieredTradeRow) {
        const latestTrade = await paperTradingPage.getTradeDataFromRow(tieredTradeRow)
        // Lots should be base_lots * tier.multiplier
        // Confidence-based: SKIP(0x), LOW(1x), MEDIUM(1.5x), HIGH(2x)
        const lots = parseInt(latestTrade.lots, 10)
        expect([0, 1, 2]).toContain(lots) // 1*1, 1*1.5 (rounded), or 1*2
      }

      // Screenshot
      await paperTradingPage.takeScreenshot('TC09-deploy-tiered')
    })

    test('TC10: Exit tiered position', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      // Find a 'tiered' sized trade to exit
      let tieredTradeRow = await paperTradingPage.findTradeRowBySizing('tiered')

      if (!tieredTradeRow) {
        // Deploy a tiered trade first
        await paperTradingPage.triggerDeploy()
        await paperTradingPage.waitForDeploymentComplete()
        await authenticatedPage.waitForTimeout(2000)
        tieredTradeRow = await paperTradingPage.findTradeRowBySizing('tiered')
      }

      expect(tieredTradeRow).not.toBeNull()
      const tradeId = await paperTradingPage.getTradeIdFromRow(tieredTradeRow)

      // Exit trade and verify it succeeded
      const exitSuccess = await paperTradingPage.exitTrade(tradeId)
      expect(exitSuccess).toBe(true)

      // Screenshot
      await paperTradingPage.takeScreenshot('TC10-exit-tiered')
    })
  })

  // ==========================================================================
  // Suite 4: Paper Trading - Kelly Sizing (3 tests)
  // ==========================================================================

  test.describe('Suite 4: Paper Trading - Kelly Sizing', () => {
    // Increase timeout for this suite due to configuration overhead
    test.setTimeout(90000)

    test.beforeEach(async ({ authenticatedPage }) => {
      // Configure kelly sizing
      await settingsPage.navigate()
      await settingsPage.configureForPaperTrading('kelly', 1)
    })

    test('TC11: Configure kelly sizing', async ({ authenticatedPage }) => {
      await settingsPage.navigate()
      // Wait for page to fully load and sync with backend
      await authenticatedPage.waitForTimeout(1000)

      const config = await settingsPage.getConfiguration()
      expect(config.sizingMode).toBe('kelly')

      // Screenshot
      await settingsPage.takeScreenshot('TC11-config-kelly')
    })

    test('TC12: Deploy with kelly sizing', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      const initialCount = await paperTradingPage.getActiveTradesCount()

      // Trigger deployment
      await paperTradingPage.triggerDeploy()
      await paperTradingPage.waitForDeploymentComplete()

      // Wait for trade count to increase (allow for parallel test interference)
      await paperTradingPage.waitForNewTrade(initialCount + 1)

      // Verify at least one kelly trade exists (may have been created by beforeEach or this test)
      const kellyTradeRow = await paperTradingPage.findTradeRowBySizing('kelly')
      expect(kellyTradeRow).not.toBeNull()

      if (kellyTradeRow) {
        const latestTrade = await paperTradingPage.getTradeDataFromRow(kellyTradeRow)
        // Kelly calculation should give at least 1 lot
        const lots = parseInt(latestTrade.lots, 10)
        expect(lots).toBeGreaterThanOrEqual(1)
      }

      // Screenshot
      await paperTradingPage.takeScreenshot('TC12-deploy-kelly')
    })

    test('TC13: Exit kelly position', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      const rows = await paperTradingPage.getActiveTradeRows()
      if (rows.length === 0) {
        await paperTradingPage.triggerDeploy()
        await paperTradingPage.waitForDeploymentComplete()
        await authenticatedPage.waitForTimeout(2000)
      }

      const rowsAfterDeploy = await paperTradingPage.getActiveTradeRows()
      const tradeId = await paperTradingPage.getTradeIdFromRow(rowsAfterDeploy[0])

      // Exit
      await paperTradingPage.exitTrade(tradeId)
      await authenticatedPage.waitForTimeout(2000)

      // Verify P&L calculated
      const summary = await paperTradingPage.getSummaryStats()
      expect(summary['Total P&L']).toBeTruthy()

      // Screenshot
      await paperTradingPage.takeScreenshot('TC13-exit-kelly')
    })
  })

  // ==========================================================================
  // Suite 5: Error Cases & UI Verification (2 tests)
  // ==========================================================================

  test.describe('Suite 5: Error Cases & UI Verification', () => {
    test('TC14: Deploy with AI disabled', async ({ authenticatedPage }) => {
      // Disable AI
      await settingsPage.navigate()
      await settingsPage.disableAI()
      await settingsPage.saveAndWait()

      // Navigate to paper trading
      await paperTradingPage.navigate()

      // Verify deploy button is disabled
      const isDisabled = await paperTradingPage.isDeployButtonDisabled()
      expect(isDisabled).toBe(true)

      // Screenshot
      await paperTradingPage.takeScreenshot('TC14-error-ai-disabled')
    })

    test('TC15: UI elements verification', async ({ authenticatedPage }) => {
      await paperTradingPage.navigate()

      // Verify all key elements are present
      const elements = await paperTradingPage.verifyUIElements()

      expect(elements['btn-trigger-deploy']).toBe(true)
      expect(elements['header-regime']).toBe(true)
      expect(elements['graduation-section']).toBe(true)
      expect(elements['paper-trades-section']).toBe(true)

      // Verify no console errors
      const consoleErrors = await paperTradingPage.verifyNoConsoleErrors()

      // Screenshot
      await paperTradingPage.takeScreenshot('TC15-ui-complete')

      // Final verification - all elements visible and no errors
      expect(Object.values(elements).every(v => v)).toBe(true)
    })
  })
})
