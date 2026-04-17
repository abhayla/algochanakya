import { BasePage } from './BasePage.js';

/**
 * Page Object for Strategy Builder screen
 * Path: /strategy
 */
export class StrategyBuilderPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/strategy';
  }

  // ============ Selectors ============

  // Page container
  get pageContainer() { return this.getByTestId('strategy-page'); }

  // Toolbar
  get toolbar() { return this.getByTestId('strategy-toolbar'); }
  get underlyingTabs() { return this.getByTestId('strategy-underlying-tabs'); }
  get niftyTab() { return this.getByTestId('strategy-underlying-nifty'); }
  get bankniftyTab() { return this.getByTestId('strategy-underlying-banknifty'); }
  get finniftyTab() { return this.getByTestId('strategy-underlying-finnifty'); }
  get pnlModeExpiry() { return this.getByTestId('strategy-pnl-mode-expiry'); }
  get pnlModeCurrent() { return this.getByTestId('strategy-pnl-mode-current'); }
  get loadingIndicator() { return this.getByTestId('strategy-loading'); }

  // Selector bar
  get selectorBar() { return this.getByTestId('strategy-selector-bar'); }
  get strategySelect() { return this.getByTestId('strategy-selector-saved-select'); }
  get strategyNameInput() { return this.getByTestId('strategy-name-input'); }
  get saveButton() { return this.getByTestId('strategy-save-button'); }
  get deleteButton() { return this.getByTestId('strategy-delete-button'); }

  // Error
  get errorAlert() { return this.getByTestId('strategy-error'); }

  // Table
  get tableWrapper() { return this.getByTestId('strategy-table-wrapper'); }
  get table() { return this.getByTestId('strategy-table'); }
  get emptyState() { return this.getByTestId('strategy-empty-state'); }
  get totalRow() { return this.getByTestId('strategy-total-row'); }

  // Action bar
  get actionBar() { return this.getByTestId('strategy-action-bar'); }
  get deleteLegsButton() { return this.getByTestId('strategy-delete-legs-button'); }
  get addRowButton() { return this.getByTestId('strategy-add-row-button'); }
  get recalculateButton() { return this.getByTestId('strategy-recalculate-button'); }
  get importPositionsButton() { return this.getByTestId('strategy-import-positions-button'); }
  get updatePositionsButton() { return this.getByTestId('strategy-update-positions-button'); }
  get saveButtonBottom() { return this.getByTestId('strategy-save-button-bottom'); }
  get shareButton() { return this.getByTestId('strategy-share-button'); }
  get basketOrderButton() { return this.getByTestId('strategy-basket-order-button'); }

  // Payoff section
  get payoffSection() { return this.getByTestId('strategy-payoff-section'); }

  // Summary cards
  get summaryGrid() { return this.getByTestId('strategy-summary-grid'); }
  get maxProfitCard() { return this.getByTestId('strategy-max-profit-card'); }
  get maxLossCard() { return this.getByTestId('strategy-max-loss-card'); }
  get breakevenCard() { return this.getByTestId('strategy-breakeven-card'); }
  get riskRewardCard() { return this.getByTestId('strategy-risk-reward-card'); }
  get spotCard() { return this.getByTestId('strategy-spot-card'); }

  // Modals
  get validationModal() { return this.getByTestId('strategy-validation-modal'); }
  get validationOkButton() { return this.getByTestId('strategy-validation-ok'); }
  get underlyingConfirmModal() { return this.getByTestId('strategy-underlying-confirm-modal'); }
  get underlyingCancelButton() { return this.getByTestId('strategy-underlying-cancel'); }
  get underlyingConfirmButton() { return this.getByTestId('strategy-underlying-confirm'); }

  // ============ Actions ============

  async navigate() {
    await super.navigate();
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.waitForTestId('strategy-page');
    // Wait for underlying tabs to be visible (indicates toolbar loaded)
    await this.underlyingTabs.waitFor({ state: 'visible', timeout: 10000 });
    // Wait for API calls to complete (expiries and spot price)
    await this.page.waitForLoadState('networkidle').catch(() => {});
  }

  async selectUnderlying(underlying) {
    const tab = this.getByTestId(`strategy-underlying-${underlying.toLowerCase()}`);
    await tab.click();
  }

  async setPnLMode(mode) {
    if (mode === 'expiry') {
      await this.pnlModeExpiry.click();
    } else {
      await this.pnlModeCurrent.click();
    }
  }

  async selectStrategy(strategyId) {
    await this.strategySelect.selectOption(strategyId);
  }

  async enterStrategyName(name) {
    await this.strategyNameInput.fill(name);
  }

  async addRow() {
    // Wait for button to be enabled (expiries must be loaded first)
    await this.addRowButton.waitFor({ state: 'visible' });
    await this.page.waitForFunction(
      (selector) => {
        const btn = document.querySelector(selector);
        return btn && !btn.disabled;
      },
      '[data-testid="strategy-add-row-button"]',
      { timeout: 10000 }
    );
    await this.addRowButton.click();
  }

  async waitForLegCount(expectedCount, timeout = 20000) {
    // Wait for the leg count to reach the expected value
    // Increased timeout from 10s to 20s due to async API calls in addLeg()
    await this.page.waitForFunction(
      ({ selector, count }) => {
        const rows = document.querySelectorAll(selector);
        return rows.length >= count;
      },
      { selector: '[data-testid="strategy-table"] tbody tr.leg-row', count: expectedCount },
      { timeout }
    );
  }

  async waitForAddRowEnabled() {
    await this.page.waitForFunction(
      (selector) => {
        const btn = document.querySelector(selector);
        return btn && !btn.disabled;
      },
      '[data-testid="strategy-add-row-button"]',
      { timeout: 15000 }
    );
  }

  /**
   * Wait for spot price to be loaded and displayed
   * @param {number} timeout - Timeout in milliseconds
   */
  async waitForSpotPrice(timeout = 15000) {
    await this.page.waitForFunction(
      () => {
        const spotCard = document.querySelector('[data-testid="strategy-spot-card"] .value');
        if (!spotCard) return false;
        const text = spotCard.textContent.trim();
        // Spot is loaded when it shows a positive number (not '-' or '0')
        const value = parseFloat(text.replace(/,/g, ''));
        return value > 0;
      },
      { timeout }
    );
  }

  /**
   * Wait for strike to be populated in a leg row
   * @param {number} rowIndex - Zero-based row index
   * @param {number} timeout - Timeout in milliseconds
   */
  async waitForStrikePopulated(rowIndex = 0, timeout = 20000) {
    await this.page.waitForFunction(
      ({ selector, index }) => {
        const rows = document.querySelectorAll(selector);
        if (rows.length <= index) return false;
        const row = rows[index];
        const strikeSelect = row.querySelectorAll('select')[3]; // 4th select is strike
        return strikeSelect && strikeSelect.value && strikeSelect.value !== '' && parseFloat(strikeSelect.value) > 0;
      },
      { selector: '[data-testid="strategy-table"] tbody tr.leg-row', index: rowIndex },
      { timeout }
    );
  }

  /**
   * Wait for CMP to be populated in a leg row
   * @param {number} rowIndex - Zero-based row index
   * @param {number} timeout - Timeout in milliseconds
   */
  async waitForCMPPopulated(rowIndex = 0, timeout = 20000) {
    await this.page.waitForFunction(
      ({ selector, index }) => {
        const rows = document.querySelectorAll(selector);
        if (rows.length <= index) return false;
        const row = rows[index];
        const cmpCell = row.querySelectorAll('td')[8]; // 9th td is CMP
        if (!cmpCell) return false;
        const text = cmpCell.textContent.trim();
        return text && text !== '-' && parseFloat(text.replace(/,/g, '')) > 0;
      },
      { selector: '[data-testid="strategy-table"] tbody tr.leg-row', index: rowIndex },
      { timeout }
    );
  }

  async isAddRowEnabled() {
    return await this.addRowButton.isEnabled();
  }

  async deleteSelectedLegs() {
    await this.deleteLegsButton.click();
  }

  async recalculate() {
    await this.recalculateButton.click();
    // Wait for calculation to complete
    await this.page.waitForSelector('[data-testid="strategy-loading"]', { state: 'hidden', timeout: 10000 }).catch(() => {});
  }

  async save() {
    await this.saveButton.click();
  }

  async deleteStrategy() {
    await this.deleteButton.click();
  }

  async share() {
    await this.shareButton.click();
  }

  async placeBasketOrder() {
    await this.basketOrderButton.click();
  }

  async importPositions() {
    await this.importPositionsButton.click();
  }

  async updatePositions() {
    await this.updatePositionsButton.click();
  }

  async getMaxProfit() {
    const valueElement = await this.maxProfitCard.locator('.value');
    const text = await valueElement.textContent();
    return text === '-' ? null : parseFloat(text.replace(/,/g, ''));
  }

  async getMaxLoss() {
    const valueElement = await this.maxLossCard.locator('.value');
    const text = await valueElement.textContent();
    return text === '-' ? null : parseFloat(text.replace(/,/g, ''));
  }

  async getBreakeven() {
    const valueElement = await this.breakevenCard.locator('.value');
    const text = await valueElement.textContent();
    return text;
  }

  async getRiskReward() {
    const valueElement = await this.riskRewardCard.locator('.value');
    const text = await valueElement.textContent();
    return text;
  }

  async getSpot() {
    const valueElement = await this.spotCard.locator('.value');
    const text = await valueElement.textContent();
    return text === '-' ? null : parseFloat(text.replace(/,/g, ''));
  }

  async getLegCount() {
    const rows = await this.table.locator('tbody tr.leg-row').all();
    return rows.length;
  }

  async isEmptyState() {
    return await this.emptyState.isVisible().catch(() => false);
  }

  async hasPayoffChart() {
    return await this.payoffSection.isVisible().catch(() => false);
  }

  async hasSummaryCards() {
    return await this.summaryGrid.isVisible().catch(() => false);
  }

  /**
   * Get the count of P/L spot price columns in the table header
   * These are the columns with data-testid="strategy-spot-column" that show P/L at different spot prices
   * @returns {Promise<number>} Count of P/L columns
   */
  async getPnLColumnCount() {
    const columns = await this.table.locator('[data-testid="strategy-spot-column"]').count();
    return columns;
  }

  /**
   * Check if P/L grid is rendered (has spot price columns)
   * @returns {Promise<boolean>} True if P/L columns exist
   */
  async hasPnLGrid() {
    const count = await this.getPnLColumnCount();
    return count > 0;
  }

  async getLegStrikeValue(rowIndex = 0) {
    // Get the strike select value from a leg row
    const rows = await this.table.locator('tbody tr.leg-row').all();
    if (rows.length <= rowIndex) return null;
    const row = rows[rowIndex];
    // Strike is the 4th select (after expiry, contract type, transaction type)
    const strikeSelect = row.locator('select').nth(3);
    return await strikeSelect.inputValue();
  }

  async getLegStrikeDisplay(rowIndex = 0) {
    // Get the currently selected strike option text
    const rows = await this.table.locator('tbody tr.leg-row').all();
    if (rows.length <= rowIndex) return null;
    const row = rows[rowIndex];
    // Strike is the 4th select (after expiry, contract type, transaction type)
    const strikeSelect = row.locator('select').nth(3);
    const value = await strikeSelect.inputValue();
    if (!value) return null;
    return parseFloat(value);
  }

  /**
   * Get leg row by index
   * @param {number} index - Zero-based row index
   * @returns {Locator} Row locator
   */
  getLegRow(index) {
    return this.table.locator('tbody tr.leg-row').nth(index);
  }

  /**
   * Wait for legs to be fully loaded with all data
   * @param {number} expectedCount - Expected number of legs
   */
  async waitForLegsLoaded(expectedCount) {
    // Wait for legs to appear
    await this.waitForLegCount(expectedCount);

    // Wait for network idle to ensure all data is loaded
    await this.page.waitForLoadState('networkidle').catch(() => {});

    // Additional wait for Vue reactivity
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Get all field values for a specific leg
   * @param {number} index - Zero-based row index
   * @returns {Object} Object containing all leg field values
   */
  async getLegDetails(index) {
    const row = this.getLegRow(index);

    // Wait for row to be visible
    await row.waitFor({ state: 'visible', timeout: 5000 });

    // Get all select and input elements
    const expirySelect = row.locator('select').nth(0);
    const typeSelect = row.locator('select').nth(1);
    const buySellSelect = row.locator('select').nth(2);
    const strikeSelect = row.locator('select').nth(3);
    const lotsInput = row.locator('input[type="number"]').first();
    const entryInput = row.locator('input[type="number"]').nth(1);

    return {
      expiry: await expirySelect.inputValue().catch(() => ''),
      type: await typeSelect.inputValue().catch(() => ''),
      buySell: await buySellSelect.inputValue().catch(() => ''),
      strike: await strikeSelect.inputValue().catch(() => ''),
      lots: await lotsInput.inputValue().catch(() => ''),
      entry: await entryInput.inputValue().catch(() => ''),
      qty: await row.locator('td').nth(7).textContent().catch(() => ''),
      cmp: await row.locator('td').nth(8).textContent().catch(() => ''),
      exitPL: await row.locator('td').nth(9).textContent().catch(() => '')
    };
  }

  /**
   * Get details for all legs in the strategy
   * @returns {Array<Object>} Array of leg detail objects
   */
  async getAllLegsDetails() {
    const count = await this.getLegCount();
    const legs = [];
    for (let i = 0; i < count; i++) {
      legs.push(await this.getLegDetails(i));
    }
    return legs;
  }

  /**
   * Get summary card values
   * @returns {Object} Object containing summary values
   */
  async getSummaryValues() {
    return {
      maxProfit: await this.maxProfitCard.locator('.value').textContent().catch(() => '-'),
      maxLoss: await this.maxLossCard.locator('.value').textContent().catch(() => '-'),
      breakeven: await this.breakevenCard.locator('.value').textContent().catch(() => '-'),
      riskReward: await this.riskRewardCard.locator('.value').textContent().catch(() => '-'),
      spot: await this.spotCard.locator('.value').textContent().catch(() => '-')
    };
  }

  /**
   * Wait for P/L calculation to complete
   */
  async waitForPnLCalculation() {
    // Wait for loading indicator to disappear
    await this.page.waitForSelector('[data-testid="strategy-loading"]', {
      state: 'hidden',
      timeout: 15000
    }).catch(() => {});
    // Additional buffer for Vue reactivity
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Check if the underlying tab is active
   * @param {string} underlying - NIFTY, BANKNIFTY, or FINNIFTY
   * @returns {boolean} True if tab is active
   */
  async isUnderlyingActive(underlying) {
    const tab = this.getByTestId(`strategy-underlying-${underlying.toLowerCase()}`);
    const classList = await tab.getAttribute('class');
    return classList.includes('active') || classList.includes('bg-blue') || classList.includes('selected');
  }

  /**
   * Verify all legs match expected template configuration
   * @param {Array} expectedLegs - Array of expected leg configurations
   * @param {number} lotSize - Lot size for the underlying
   * @param {number} lots - Number of lots configured
   * @returns {Object} Verification result with pass/fail and details
   */
  async verifyDeployedLegs(expectedLegs, lotSize, lots = 1) {
    const actualLegs = await this.getAllLegsDetails();
    const results = {
      passed: true,
      legCount: {
        expected: expectedLegs.length,
        actual: actualLegs.length,
        passed: actualLegs.length === expectedLegs.length
      },
      legs: []
    };

    if (!results.legCount.passed) {
      results.passed = false;
    }

    for (let i = 0; i < Math.min(expectedLegs.length, actualLegs.length); i++) {
      const expected = expectedLegs[i];
      const actual = actualLegs[i];

      const legResult = {
        index: i,
        type: {
          expected: expected.type,
          actual: actual.type,
          passed: actual.type === expected.type
        },
        position: {
          expected: expected.position,
          actual: actual.buySell,
          passed: actual.buySell === expected.position
        },
        lots: {
          expected: lots,
          actual: parseInt(actual.lots) || 0,
          passed: (parseInt(actual.lots) || 0) === lots
        },
        qty: {
          expected: lots * lotSize,
          actual: parseInt(actual.qty) || 0,
          passed: (parseInt(actual.qty) || 0) === lots * lotSize
        },
        strikePopulated: {
          passed: actual.strike !== '' && parseFloat(actual.strike) > 0
        },
        entryPopulated: {
          passed: actual.entry !== '' && parseFloat(actual.entry) > 0
        }
      };

      // Check if any field failed
      if (!legResult.type.passed || !legResult.position.passed ||
          !legResult.lots.passed || !legResult.qty.passed ||
          !legResult.strikePopulated.passed || !legResult.entryPopulated.passed) {
        results.passed = false;
      }

      results.legs.push(legResult);
    }

    return results;
  }

  // ============ Assertions ============

  async assertPageVisible() {
    await this.assertVisible('strategy-page');
  }

  async assertTableVisible() {
    await this.assertVisible('strategy-table');
  }

  async assertEmptyState() {
    await this.assertVisible('strategy-empty-state');
  }

  async assertTotalRowVisible() {
    await this.assertVisible('strategy-total-row');
  }

  async assertPayoffVisible() {
    await this.assertVisible('strategy-payoff-section');
  }

  async assertSummaryVisible() {
    await this.assertVisible('strategy-summary-grid');
  }

  async assertActionBarVisible() {
    await this.assertVisible('strategy-action-bar');
  }

  async assertError() {
    await this.assertVisible('strategy-error');
  }

  async assertLoading() {
    await this.assertVisible('strategy-loading');
  }

  // Modal interactions
  async isValidationModalVisible() {
    return await this.validationModal.isVisible();
  }

  async getValidationErrors() {
    await this.validationModal.waitFor({ state: 'visible' });
    const errorList = this.validationModal.locator('ul.error-list li');
    return await errorList.allTextContents();
  }

  async closeValidationModal() {
    await this.validationOkButton.click();
    await this.validationModal.waitFor({ state: 'hidden' });
  }

  async isUnderlyingConfirmModalVisible() {
    return await this.underlyingConfirmModal.isVisible();
  }

  async confirmUnderlyingChange() {
    await this.underlyingConfirmButton.click();
    await this.underlyingConfirmModal.waitFor({ state: 'hidden' });
  }

  async cancelUnderlyingChange() {
    await this.underlyingCancelButton.click();
    await this.underlyingConfirmModal.waitFor({ state: 'hidden' });
  }

  async waitForPnLUpdate() {
    // Wait for P/L calculation to complete by checking for P/L columns
    // The P/L grid columns (strategy-spot-column) appear after calculation
    await this.page.waitForLoadState('domcontentloaded'); // Brief delay for calculation to trigger

    // Wait for P/L grid columns to appear (max 10 seconds)
    try {
      await this.table.locator('[data-testid="strategy-spot-column"]').first().waitFor({
        state: 'visible',
        timeout: 10000
      });
    } catch (e) {
      // If columns don't appear, wait additional time and continue
      // (calculation might have failed, which is a valid test failure)
      await this.page.waitForLoadState('domcontentloaded');
    }
  }

  // ============ Enhanced Verification Methods ============

  /**
   * Get CMP value for a specific leg
   * @param {number} index - Zero-based row index
   * @returns {number|null} CMP value or null if not available
   */
  async getLegCMP(index) {
    const row = this.getLegRow(index);
    const cmpText = await row.locator('td').nth(8).textContent().catch(() => '-');
    if (!cmpText || cmpText.trim() === '-' || cmpText.trim() === '') {
      return null;
    }
    return parseFloat(cmpText.replace(/,/g, ''));
  }

  /**
   * Check if error banner is visible on the page
   * @returns {boolean} True if any error banner is visible
   */
  async hasErrorBanner() {
    // Check for specific error banner patterns used in Strategy Builder
    const errorSelectors = [
      '[data-testid="strategy-error"]',  // Primary error element (StrategyBuilderView.vue)
    ];

    for (const selector of errorSelectors) {
      const element = this.page.locator(selector);
      if (await element.isVisible().catch(() => false)) {
        // Extra check: ensure it's not just a negative number display
        const text = await element.textContent().catch(() => '');
        // Error banners typically have actual error messages, not just numbers
        if (text && text.length > 10 && !/^[-\d,.\s]+$/.test(text.trim())) {
          return true;
        }
      }
    }
    return false;
  }

  /**
   * Get error banner text if visible
   * @returns {string|null} Error text or null if no error
   */
  async getErrorBannerText() {
    const errorSelectors = [
      '[data-testid="strategy-error"]',  // Primary error element (StrategyBuilderView.vue)
    ];

    for (const selector of errorSelectors) {
      const element = this.page.locator(selector);
      if (await element.isVisible().catch(() => false)) {
        const text = await element.textContent().catch(() => '');
        // Only return text if it looks like an error message (not just a number)
        if (text && text.length > 10 && !/^[-\d,.\s]+$/.test(text.trim())) {
          return text;
        }
      }
    }
    return null;
  }

  /**
   * Check if payoff chart has rendered content (not blank)
   * Uses Chart.js with canvas element
   * @returns {boolean} True if chart has rendered content
   */
  async isPayoffChartRendered() {
    // The PayoffChart component uses Chart.js which renders to canvas
    // Check for canvas element in the payoff section
    const canvasSelectors = [
      '.payoff-chart canvas',
      '[data-testid="strategy-payoff-section"] canvas',
      '.payoff-section canvas'
    ];

    for (const selector of canvasSelectors) {
      const canvas = this.page.locator(selector);
      if (await canvas.isVisible().catch(() => false)) {
        // Canvas exists and is visible - check if it has actual content
        // We can check if the canvas has been drawn to by checking its data URL length
        const hasContent = await this.page.evaluate((sel) => {
          const canvasEl = document.querySelector(sel);
          if (!canvasEl) return false;
          // Check if canvas context has been used (data URL will be longer than blank canvas)
          try {
            const dataUrl = canvasEl.toDataURL();
            // A blank canvas has ~1.5KB data URL, rendered chart has much more
            return dataUrl.length > 5000;
          } catch (e) {
            // If we can't access the canvas, assume it's rendered if visible
            return true;
          }
        }, selector).catch(() => false);

        if (hasContent) {
          return true;
        }
      }
    }

    // Fallback: Check for SVG-based charts (some chart libraries use SVG)
    const svgPaths = this.page.locator('.payoff-chart svg path, [data-testid="strategy-payoff-section"] svg path');
    const pathCount = await svgPaths.count().catch(() => 0);
    if (pathCount > 0) {
      return true;
    }

    // Check for recharts-based charts
    const chartContainer = this.page.locator('.recharts-wrapper, .payoff-chart .recharts-wrapper');
    if (await chartContainer.isVisible().catch(() => false)) {
      const lineElements = chartContainer.locator('.recharts-line, .recharts-area');
      return await lineElements.count() > 0;
    }

    return false;
  }

  /**
   * Get the count of rendered chart elements (canvas or SVG)
   * @returns {number} Count of chart elements (1 for canvas, or SVG path count)
   */
  async getPayoffChartPathCount() {
    // Check for canvas first (Chart.js)
    const canvasSelectors = [
      '.payoff-chart canvas',
      '[data-testid="strategy-payoff-section"] canvas'
    ];

    for (const selector of canvasSelectors) {
      const canvas = this.page.locator(selector);
      if (await canvas.isVisible().catch(() => false)) {
        // Canvas found - return 1 to indicate chart exists
        return 1;
      }
    }

    // Fallback to SVG path counting
    const svgSelectors = [
      '[data-testid="strategy-payoff-section"] svg path',
      '.payoff-chart svg path',
      '#payoffChart path',
      '.recharts-line path',
      '.recharts-area path'
    ];

    let totalCount = 0;
    for (const selector of svgSelectors) {
      totalCount += await this.page.locator(selector).count().catch(() => 0);
    }
    return totalCount;
  }

  /**
   * Assert no errors are present on the page
   * Throws if error banner is visible
   */
  async assertNoErrors() {
    const hasError = await this.hasErrorBanner();
    if (hasError) {
      const errorText = await this.getErrorBannerText();
      throw new Error(`Error banner visible: ${errorText}`);
    }
  }

  /**
   * Assert payoff chart is rendered (not blank)
   * Throws if chart is empty
   */
  async assertPayoffChartRendered() {
    const isRendered = await this.isPayoffChartRendered();
    if (!isRendered) {
      throw new Error('Payoff chart is blank - no chart elements rendered');
    }
  }

  /**
   * Assert CMP changed after an action
   * @param {number} cmpBefore - CMP value before action
   * @param {number} cmpAfter - CMP value after action
   * @param {string} actionDescription - Description for error message
   */
  assertCMPChanged(cmpBefore, cmpAfter, actionDescription = 'action') {
    if (cmpBefore === cmpAfter) {
      throw new Error(`CMP did not change after ${actionDescription}: before=${cmpBefore}, after=${cmpAfter}`);
    }
  }

  /**
   * Build trading symbol from leg details
   * @param {Object} legDetails - Leg details object
   * @param {string} underlying - NIFTY, BANKNIFTY, etc.
   * @returns {string|null} Trading symbol or null if incomplete
   */
  buildTradingSymbol(legDetails, underlying = 'NIFTY') {
    if (!legDetails.expiry || !legDetails.strike || !legDetails.type) {
      return null;
    }

    // Parse expiry date (format varies: "27 Jan 20", "2026-01-27", etc.)
    const expiry = legDetails.expiry.trim();
    const strike = legDetails.strike.trim();
    const type = legDetails.type.trim();

    // Try to parse and format expiry
    // Expected output format: NIFTY27JAN26500CE
    try {
      // Common formats: "27 Jan 20" or "2026-01-27"
      let formattedExpiry;
      if (expiry.includes('-')) {
        // ISO format: 2026-01-27
        const date = new Date(expiry);
        const day = date.getDate().toString().padStart(2, '0');
        const month = date.toLocaleString('en-US', { month: 'short' }).toUpperCase();
        const year = date.getFullYear().toString().slice(-2);
        formattedExpiry = `${day}${month}${year}`;
      } else {
        // Format: "27 Jan 20" or "27 Jan 2026"
        const parts = expiry.split(' ');
        if (parts.length >= 3) {
          const day = parts[0].padStart(2, '0');
          const month = parts[1].toUpperCase().slice(0, 3);
          const year = parts[2].slice(-2);
          formattedExpiry = `${day}${month}${year}`;
        } else {
          return null;
        }
      }

      return `${underlying}${formattedExpiry}${strike}${type}`;
    } catch (e) {
      return null;
    }
  }
}
