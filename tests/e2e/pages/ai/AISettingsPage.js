/**
 * AI Settings Page Object
 *
 * Page object for the AI Settings page (/ai/settings)
 * Provides methods for configuring AI trading settings
 */

import { BasePage } from '../BasePage.js'

export class AISettingsPage extends BasePage {
  constructor(page) {
    super(page)
    this.url = '/ai/settings'
  }

  // ============================================================================
  // Selectors
  // ============================================================================

  get aiEnabledToggle() {
    return this.getByTestId('ai-enabled-toggle')
  }

  get sizingModeSelect() {
    return this.getByTestId('sizing-mode-select')
  }

  get baseLotsInput() {
    return this.getByTestId('base-lots-input')
  }

  get saveButton() {
    return this.getByTestId('save-button')
  }

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Enable AI trading
   */
  async enableAI() {
    const toggle = this.aiEnabledToggle
    const isChecked = await toggle.isChecked()

    if (!isChecked) {
      // Click the parent label which contains the visible toggle
      await toggle.locator('..').click()
    }
  }

  /**
   * Disable AI trading
   */
  async disableAI() {
    const toggle = this.aiEnabledToggle
    const isChecked = await toggle.isChecked()

    if (isChecked) {
      // Click the parent label which contains the visible toggle
      await toggle.locator('..').click()
    }
  }

  /**
   * Check if AI is enabled
   */
  async isAIEnabled() {
    return await this.aiEnabledToggle.isChecked()
  }

  /**
   * Set autonomy mode
   * @param {string} mode - 'paper' or 'live'
   */
  async setAutonomyMode(mode) {
    const radio = this.getByTestId(`mode-${mode}`)
    await radio.click()
    // Wait for auto-save
    await this.page.waitForTimeout(500)
  }

  /**
   * Get current autonomy mode
   */
  async getAutonomyMode() {
    const isPaperChecked = await this.getByTestId('mode-paper').isChecked()
    return isPaperChecked ? 'paper' : 'live'
  }

  /**
   * Set sizing mode
   * @param {string} mode - 'fixed', 'tiered', or 'kelly'
   */
  async setSizingMode(mode) {
    await this.sizingModeSelect.selectOption(mode)
    // Wait for auto-save
    await this.page.waitForTimeout(500)
  }

  /**
   * Get current sizing mode
   */
  async getSizingMode() {
    return await this.sizingModeSelect.inputValue()
  }

  /**
   * Set base lots
   * @param {number} lots - Number of base lots
   */
  async setBaseLots(lots) {
    await this.baseLotsInput.fill(lots.toString())
  }

  /**
   * Get base lots value
   */
  async getBaseLots() {
    const value = await this.baseLotsInput.inputValue()
    return parseInt(value, 10)
  }

  /**
   * Save settings
   */
  async save() {
    await this.saveButton.click()
    // Wait for API response (any status)
    try {
      await this.page.waitForResponse(
        (resp) => resp.url().includes('/api/v1/ai/config') && resp.request().method() === 'PUT',
        { timeout: 10000 }
      )
    } catch (error) {
      console.log('Save API call did not complete within timeout')
    }
  }

  /**
   * Save settings and wait for completion
   */
  async saveAndWait() {
    await this.saveButton.click()
    // Wait briefly for save to complete
    await this.page.waitForTimeout(500)
  }

  /**
   * Reset settings to defaults
   */
  async reset() {
    // Handle confirmation dialog
    this.page.on('dialog', async (dialog) => {
      await dialog.accept()
    })

    await this.resetButton.click()
    await this.page.waitForTimeout(1000)
  }

  /**
   * Configure AI for paper trading with specific sizing mode
   * @param {string} sizingMode - 'fixed', 'tiered', or 'kelly'
   * @param {number} baseLots - Number of base lots (default: 1)
   */
  async configureForPaperTrading(sizingMode, baseLots = 1) {
    await this.enableAI()
    await this.setAutonomyMode('paper')
    await this.setSizingMode(sizingMode)
    await this.setBaseLots(baseLots)
    await this.saveAndWait()
  }

  /**
   * Get complete configuration
   */
  async getConfiguration() {
    return {
      aiEnabled: await this.isAIEnabled(),
      autonomyMode: await this.getAutonomyMode(),
      sizingMode: await this.getSizingMode(),
      baseLots: await this.getBaseLots()
    }
  }

  /**
   * Verify settings page loaded correctly
   */
  async verifyPageLoaded() {
    // Check for toggle presence (it's hidden by CSS but should be attached)
    await this.aiEnabledToggle.waitFor({ state: 'attached' })
    await this.assertVisible('sizing-mode-select')
    await this.assertVisible('save-button')
  }

  /**
   * Check if save button is enabled
   */
  async isSaveButtonEnabled() {
    return await this.saveButton.isEnabled()
  }

  /**
   * Check if save button is disabled
   */
  async isSaveButtonDisabled() {
    return await this.saveButton.isDisabled()
  }

  /**
   * Take screenshot with automatic naming
   * @param {string} testName - Name of the test
   */
  async takeScreenshot(testName) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    await this.screenshot(`ai-settings-${testName}-${timestamp}`)
  }

  /**
   * Verify all UI elements are present
   */
  async verifyUIElements() {
    const elements = [
      'ai-enabled-toggle',
      'mode-paper',  // Radio button for paper trading
      'sizing-mode-select',
      'base-lots-input',
      'save-button'
    ]

    const results = {}
    for (const testId of elements) {
      try {
        // For hidden elements like checkboxes, check if attached instead of visible
        if (testId === 'ai-enabled-toggle') {
          const elem = this.getByTestId(testId)
          await elem.waitFor({ state: 'attached', timeout: 1000 })
          results[testId] = true
        } else {
          results[testId] = await this.isTestIdVisible(testId)
        }
      } catch (error) {
        results[testId] = false
      }
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

  /**
   * Wait for settings to be saved (check for success indicator)
   */
  async waitForSaveComplete() {
    // Wait for toast or some success indicator
    await this.page.waitForTimeout(1500)
  }
}
