import { BasePage } from './BasePage.js';

/**
 * Page Object for Strategy Builder screen
 * Path: /strategy
 */
export default class StrategyBuilderPage extends BasePage {
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
  get strategySelect() { return this.getByTestId('strategy-select'); }
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

  // ============ Actions ============

  async navigate() {
    await super.navigate();
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.waitForTestId('strategy-page');
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

  async waitForLegCount(expectedCount, timeout = 10000) {
    // Wait for the leg count to reach the expected value
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
      { timeout: 10000 }
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
    await this.page.waitForTimeout(1000);
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
    await this.page.waitForTimeout(500);
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
}
