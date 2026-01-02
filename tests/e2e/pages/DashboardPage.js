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

  get optionchainCard() {
    return this.getByTestId('dashboard-optionchain-card');
  }

  get ofoCard() {
    return this.getByTestId('dashboard-ofo-card');
  }

  get strategyCard() {
    return this.getByTestId('dashboard-strategy-card');
  }

  get positionsCard() {
    return this.getByTestId('dashboard-positions-card');
  }

  get strategiesCard() {
    return this.getByTestId('dashboard-strategies-card');
  }

  // Actions
  async waitForPageLoad() {
    await this.waitForTestId('dashboard-page');
    await this.waitForLoad();
  }

  async goToOptionChain() {
    await this.optionchainCard.click();
  }

  async goToOFO() {
    await this.ofoCard.click();
  }

  async goToStrategy() {
    await this.strategyCard.click();
  }

  async goToPositions() {
    await this.positionsCard.click();
  }

  async goToStrategies() {
    await this.strategiesCard.click();
  }

  // Assertions
  async isPageVisible() {
    return await this.isTestIdVisible('dashboard-page');
  }

  async areCardsVisible() {
    const optionchain = await this.isTestIdVisible('dashboard-optionchain-card');
    const ofo = await this.isTestIdVisible('dashboard-ofo-card');
    const strategy = await this.isTestIdVisible('dashboard-strategy-card');
    const positions = await this.isTestIdVisible('dashboard-positions-card');
    const strategies = await this.isTestIdVisible('dashboard-strategies-card');
    return optionchain && ofo && strategy && positions && strategies;
  }
}
