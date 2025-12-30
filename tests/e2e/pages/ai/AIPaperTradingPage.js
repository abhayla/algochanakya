/**
 * AI Paper Trading Page Object
 *
 * Page object for the AI Paper Trading dashboard (/ai/paper-trading)
 * Provides methods for interacting with paper trading features
 */

import { BasePage } from '../BasePage.js'

export class AIPaperTradingPage extends BasePage {
  constructor(page) {
    super(page)
    this.url = '/ai/paper-trading'
  }

  // ============================================================================
  // Selectors
  // ============================================================================

  get deployButton() {
    return this.getByTestId('btn-trigger-deploy')
  }

  get refreshTradesButton() {
    return this.getByTestId('btn-refresh-trades')
  }

  get paperTradesSection() {
    return this.getByTestId('paper-trades-section')
  }

  get paperTradesTable() {
    return this.getByTestId('paper-trades-table')
  }

  get closedTradesTable() {
    return this.getByTestId('closed-trades-table')
  }

  get tradesSummary() {
    return this.getByTestId('trades-summary')
  }

  get regimeIndicator() {
    return this.getByTestId('header-regime')
  }

  get graduationSection() {
    return this.getByTestId('graduation-section')
  }

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Trigger AI deployment
   */
  async triggerDeploy() {
    // Set up response listener BEFORE clicking to avoid race condition
    const responsePromise = this.page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/ai/deploy/trigger') && resp.status() === 200,
      { timeout: 30000 }
    )
    await this.deployButton.click()
    await responsePromise
  }

  /**
   * Exit a paper trade by ID
   * @param {string} tradeId - UUID of the paper trade
   * @returns {boolean} true if exit was successful
   */
  async exitTrade(tradeId) {
    const exitButton = this.getByTestId(`btn-exit-trade-${tradeId}`)

    // Set up one-time dialog handler BEFORE clicking
    this.page.once('dialog', async (dialog) => {
      await dialog.accept()
    })

    // Set up response listener BEFORE clicking to avoid race condition
    const responsePromise = this.page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/ai/deploy/paper-trade/exit') && resp.status() === 200,
      { timeout: 30000 }
    )
    await exitButton.click()
    const response = await responsePromise

    // Parse response body to verify success
    const body = await response.json()
    if (!body.success) {
      return false
    }

    // Wait for UI to update after exit (the list refreshes)
    await this.page.waitForTimeout(1000)

    // Verify trade is no longer in active list by refreshing
    await this.refreshTrades()

    return true
  }

  /**
   * Refresh paper trades list
   */
  async refreshTrades() {
    // Set up response listener BEFORE clicking to avoid race condition
    const responsePromise = this.page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/ai/deploy/paper-trade/list'),
      { timeout: 10000 }
    )
    await this.refreshTradesButton.click()
    await responsePromise
  }

  /**
   * Get all active trade rows
   */
  async getActiveTradeRows() {
    const table = this.paperTradesTable
    const rows = await table.locator('tbody tr').all()
    return rows
  }

  /**
   * Get all closed trade rows
   */
  async getClosedTradeRows() {
    const table = this.closedTradesTable
    const rows = await table.locator('tbody tr').all()
    return rows
  }

  /**
   * Get trade ID from a table row
   * @param {Locator} row - Table row locator
   */
  async getTradeIdFromRow(row) {
    const testId = await row.getAttribute('data-testid')
    // Extract ID from data-testid like "paper-trade-row-{id}"
    const match = testId.match(/paper-trade-row-(.+)/)
    return match ? match[1] : null
  }

  /**
   * Get trade data from a table row
   * @param {Locator} row - Table row locator
   */
  async getTradeDataFromRow(row) {
    const cells = await row.locator('td').allTextContents()
    return {
      strategy: cells[0],
      entryTime: cells[1],
      regime: cells[2],
      confidence: cells[3],
      lots: cells[4],
      sizing: cells[5],
      entryPremium: cells[6]
    }
  }

  /**
   * Find a trade row with a specific sizing mode
   * @param {string} sizingMode - 'fixed', 'tiered', or 'kelly'
   * @returns {Locator|null} The matching row or null if not found
   */
  async findTradeRowBySizing(sizingMode) {
    const rows = await this.getActiveTradeRows()
    for (const row of rows) {
      const data = await this.getTradeDataFromRow(row)
      if (data.sizing.toLowerCase().includes(sizingMode.toLowerCase())) {
        return row
      }
    }
    return null
  }

  /**
   * Get summary statistics
   */
  async getSummaryStats() {
    const summary = this.tradesSummary
    const cards = await summary.locator('.summary-card').all()

    const stats = {}
    for (const card of cards) {
      const label = await card.locator('.summary-label').textContent()
      const value = await card.locator('.summary-value').textContent()
      stats[label.trim()] = value.trim()
    }

    return stats
  }

  /**
   * Check if deploy button is disabled
   */
  async isDeployButtonDisabled() {
    return await this.deployButton.isDisabled()
  }

  /**
   * Check if deploy button is enabled
   */
  async isDeployButtonEnabled() {
    return await this.deployButton.isEnabled()
  }

  /**
   * Wait for deployment to complete
   */
  async waitForDeploymentComplete() {
    // Wait for button text to change from "Deploying..." back to "Trigger Deploy"
    await this.page.waitForFunction(
      () => {
        const btn = document.querySelector('[data-testid="btn-trigger-deploy"]')
        return btn && btn.textContent.includes('Trigger Deploy')
      },
      { timeout: 20000 }
    )
  }

  /**
   * Get current regime from header
   */
  async getCurrentRegime() {
    const regimeText = await this.regimeIndicator.textContent()
    return regimeText.trim()
  }

  /**
   * Check if paper trades table is visible
   */
  async isPaperTradesTableVisible() {
    return await this.paperTradesTable.isVisible()
  }

  /**
   * Check if empty state message is visible
   */
  async isEmptyStateVisible() {
    const emptyMessage = this.paperTradesSection.locator('.empty-message')
    return await emptyMessage.isVisible()
  }

  /**
   * Get active trades count from table
   */
  async getActiveTradesCount() {
    const rows = await this.getActiveTradeRows()
    return rows.length
  }

  /**
   * Get closed trades count from table
   */
  async getClosedTradesCount() {
    const rows = await this.getClosedTradeRows()
    return rows.length
  }

  /**
   * Wait for new trade to appear in table
   * @param {number} expectedCount - Expected number of active trades
   */
  async waitForNewTrade(expectedCount) {
    await this.page.waitForFunction(
      (count) => {
        const rows = document.querySelectorAll('[data-testid="paper-trades-table"] tbody tr')
        return rows.length >= count
      },
      expectedCount,
      { timeout: 30000 }
    )
  }

  /**
   * Verify no console errors
   */
  async verifyNoConsoleErrors() {
    const errors = []
    this.page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    return errors
  }

  /**
   * Take screenshot with automatic naming
   * @param {string} testName - Name of the test
   */
  async takeScreenshot(testName) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    await this.screenshot(`ai-paper-trading-${testName}-${timestamp}`)
  }

  /**
   * Verify all UI elements are present
   */
  async verifyUIElements() {
    const elements = [
      'btn-trigger-deploy',
      'header-regime',
      'graduation-section',
      'paper-trades-section'
    ]

    const results = {}
    for (const testId of elements) {
      results[testId] = await this.isTestIdVisible(testId)
    }

    return results
  }

  /**
   * Get toast message text
   */
  async getToastMessage() {
    const toast = this.page.locator('.toast-message').first()
    await toast.waitFor({ state: 'visible', timeout: 5000 })
    return await toast.textContent()
  }
}
