/**
 * Broker Settings Page Object
 *
 * Covers the BrokerSettings section inside /settings and
 * the BrokerUpgradeBanner / DataSourceBadge components
 * that appear on Dashboard, Watchlist, OptionChain, and Positions.
 *
 * Usage:
 *   import { BrokerSettingsPage } from '../pages/BrokerSettingsPage.js';
 *   const page = new BrokerSettingsPage(authenticatedPage);
 *   await page.navigate();
 */

import { BasePage } from './BasePage.js';

export class BrokerSettingsPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/settings';
  }

  // -----------------------------------------------------------------------
  // Settings page containers
  // -----------------------------------------------------------------------

  get settingsPage() {
    return this.getByTestId('settings-page');
  }

  get brokerSection() {
    return this.getByTestId('settings-broker-section');
  }

  // -----------------------------------------------------------------------
  // Broker settings controls
  // -----------------------------------------------------------------------

  get marketDataSelect() {
    return this.getByTestId('settings-broker-market-data-select');
  }

  get orderBrokerSelect() {
    return this.getByTestId('settings-broker-order-select');
  }

  get saveBtn() {
    return this.getByTestId('settings-broker-save-btn');
  }

  get resetBtn() {
    return this.getByTestId('settings-broker-reset-btn');
  }

  get saveSuccess() {
    return this.getByTestId('settings-broker-save-success');
  }

  get saveError() {
    return this.getByTestId('settings-broker-save-error');
  }

  // -----------------------------------------------------------------------
  // Upgrade banner helpers (screen-namespaced)
  // -----------------------------------------------------------------------

  upgradeBanner(screen) {
    return this.getByTestId(`${screen}-upgrade-banner`);
  }

  upgradeBannerSettingsLink(screen) {
    return this.getByTestId(`${screen}-upgrade-banner-settings-link`);
  }

  upgradeBannerDismiss(screen) {
    return this.getByTestId(`${screen}-upgrade-banner-dismiss`);
  }

  dataSourceBadge(screen) {
    return this.getByTestId(`${screen}-data-source-badge`);
  }

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------

  async waitForPageLoad() {
    await this.waitForTestId('settings-page');
    await this.waitForLoad();
  }

  async selectMarketDataSource(value) {
    await this.marketDataSelect.selectOption(value);
  }

  async selectOrderBroker(value) {
    await this.orderBrokerSelect.selectOption(value);
  }

  async save() {
    await this.saveBtn.click();
  }

  async reset() {
    await this.resetBtn.click();
  }

  async dismissBanner(screen) {
    await this.upgradeBannerDismiss(screen).click();
  }

  async clickBannerSettingsLink(screen) {
    await this.upgradeBannerSettingsLink(screen).click();
  }
}
