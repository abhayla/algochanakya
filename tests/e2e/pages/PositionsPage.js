/**
 * Positions Page Object
 *
 * Usage:
 *   import { PositionsPage } from '../pages/PositionsPage.js';
 *   const positionsPage = new PositionsPage(page);
 *   await positionsPage.navigate();
 */

import { BasePage } from './BasePage.js';

export class PositionsPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/positions';
  }

  // Selectors
  get container() {
    return this.getByTestId('positions-page');
  }

  get dayButton() {
    return this.getByTestId('positions-day-button');
  }

  get netButton() {
    return this.getByTestId('positions-net-button');
  }

  get pnlBox() {
    return this.getByTestId('positions-pnl-box');
  }

  get summaryBar() {
    return this.getByTestId('positions-summary-bar');
  }

  get table() {
    return this.getByTestId('positions-table');
  }

  get tableContainer() {
    return this.getByTestId('positions-table-container');
  }

  get emptyState() {
    return this.getByTestId('positions-empty-state');
  }

  get exitModal() {
    return this.getByTestId('positions-exit-modal');
  }

  get addModal() {
    return this.getByTestId('positions-add-modal');
  }

  // Actions
  async waitForPageLoad() {
    await this.waitForTestId('positions-page');
    await this.waitForLoad();
    // Wait for loading to complete - either table or empty state should be visible
    await this.waitForLoadingComplete();
  }

  /**
   * Wait for the positions loading to complete
   * Once loading is done, either positions-table or positions-empty-state will be visible
   */
  async waitForLoadingComplete() {
    // Wait for loading spinner/text to disappear and content to appear
    // We check for either table or empty state to be visible
    await this.page.waitForFunction(
      () => {
        const table = document.querySelector('[data-testid="positions-table"]');
        const empty = document.querySelector('[data-testid="positions-empty-state"]');
        return table !== null || empty !== null;
      },
      { timeout: 15000 }
    );
  }

  async selectDayPositions() {
    await this.dayButton.click();
  }

  async selectNetPositions() {
    await this.netButton.click();
  }

  async clickExitButton(symbol) {
    await this.page.locator(`[data-testid="positions-exit-button-${symbol}"]`).click();
  }

  async clickAddButton(symbol) {
    await this.page.locator(`[data-testid="positions-add-button-${symbol}"]`).click();
  }

  async getPositionRow(symbol) {
    return this.page.locator(`[data-testid="positions-row-${symbol}"]`);
  }

  // Assertions
  async isPageVisible() {
    return await this.isTestIdVisible('positions-page');
  }

  async hasPositions() {
    return await this.isTestIdVisible('positions-table');
  }

  async isEmpty() {
    return await this.isTestIdVisible('positions-empty-state');
  }

  async isExitModalOpen() {
    return await this.isTestIdVisible('positions-exit-modal');
  }

  async isAddModalOpen() {
    return await this.isTestIdVisible('positions-add-modal');
  }

  async getPnlText() {
    return await this.pnlBox.textContent();
  }

  async isDaySelected() {
    const btn = await this.dayButton;
    return await btn.evaluate(el => el.classList.contains('active'));
  }

  async isNetSelected() {
    const btn = await this.netButton;
    return await btn.evaluate(el => el.classList.contains('active'));
  }
}
