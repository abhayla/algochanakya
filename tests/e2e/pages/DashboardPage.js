/**
 * Dashboard Page Object
 *
 * Usage:
 *   import { DashboardPage } from '../pages/DashboardPage.js';
 *   const dashboardPage = new DashboardPage(page);
 *   await dashboardPage.navigate();
 */

import { BasePage } from './BasePage.js';

export class DashboardPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/dashboard';
  }

  // Selectors
  get container() {
    return this.getByTestId('dashboard-page');
  }

  get title() {
    return this.getByTestId('dashboard-title');
  }

  get cardsContainer() {
    return this.getByTestId('dashboard-cards');
  }

  get watchlistCard() {
    return this.getByTestId('dashboard-watchlist-card');
  }

  get strategyCard() {
    return this.getByTestId('dashboard-strategy-card');
  }

  get optionchainCard() {
    return this.getByTestId('dashboard-optionchain-card');
  }

  get positionsCard() {
    return this.getByTestId('dashboard-positions-card');
  }

  // Actions
  async waitForPageLoad() {
    await this.waitForTestId('dashboard-page');
    await this.waitForLoad();
  }

  async goToWatchlist() {
    await this.watchlistCard.click();
  }

  async goToStrategy() {
    await this.strategyCard.click();
  }

  async goToOptionChain() {
    await this.optionchainCard.click();
  }

  async goToPositions() {
    await this.positionsCard.click();
  }

  // Assertions
  async isPageVisible() {
    return await this.isTestIdVisible('dashboard-page');
  }

  async areCardsVisible() {
    const watchlist = await this.isTestIdVisible('dashboard-watchlist-card');
    const strategy = await this.isTestIdVisible('dashboard-strategy-card');
    const optionchain = await this.isTestIdVisible('dashboard-optionchain-card');
    const positions = await this.isTestIdVisible('dashboard-positions-card');
    return watchlist && strategy && optionchain && positions;
  }
}
