import { BasePage } from './BasePage.js';

/**
 * Page Object for OFO (Options For Options) screen
 * Path: /ofo
 */
export default class OFOPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/ofo';
  }

  // ============ Selectors ============

  // Page container
  get pageContainer() { return this.getByTestId('ofo-page'); }
  get header() { return this.getByTestId('ofo-header'); }
  get headerTitle() { return this.getByTestId('ofo-header-title'); }

  // Underlying tabs
  get underlyingTabs() { return this.getByTestId('ofo-underlying-tabs'); }
  get niftyTab() { return this.getByTestId('ofo-underlying-nifty'); }
  get bankniftyTab() { return this.getByTestId('ofo-underlying-banknifty'); }
  get finniftyTab() { return this.getByTestId('ofo-underlying-finnifty'); }

  // Spot price
  get spotPrice() { return this.getByTestId('ofo-spot-price'); }

  // Calculation time indicator
  get calcTime() { return this.getByTestId('ofo-calc-time'); }

  // Controls
  get expirySelect() { return this.getByTestId('ofo-expiry-select'); }
  get strategySelect() { return this.getByTestId('ofo-strategy-select'); }
  get strategyTrigger() { return this.getByTestId('ofo-strategy-trigger'); }
  get strategyDropdown() { return this.getByTestId('ofo-strategy-dropdown'); }
  get strikeRangeSelect() { return this.getByTestId('ofo-strike-range'); }
  get lotsInput() { return this.getByTestId('ofo-lots-input'); }
  get calculateButton() { return this.getByTestId('ofo-calculate-btn'); }

  // Auto-refresh
  get autoRefreshToggle() { return this.getByTestId('ofo-auto-refresh'); }
  get autoRefreshInterval() { return this.getByTestId('ofo-refresh-interval'); }

  // Last calculated indicator
  get lastCalculated() { return this.getByTestId('ofo-last-calculated'); }

  // States
  get errorAlert() { return this.getByTestId('ofo-error'); }
  get loadingState() { return this.getByTestId('ofo-loading'); }
  get emptyState() { return this.getByTestId('ofo-empty'); }

  // Results section
  get resultsSection() { return this.getByTestId('ofo-results'); }

  // ============ Dynamic Selectors ============

  // Strategy group
  getStrategyGroup(strategyType) {
    return this.getByTestId(`ofo-group-${strategyType}`);
  }

  // Strategy group header
  getStrategyGroupHeader(strategyType) {
    return this.getByTestId(`ofo-group-header-${strategyType}`);
  }

  // Strategy group cards row
  getStrategyGroupCards(strategyType) {
    return this.getByTestId(`ofo-group-cards-${strategyType}`);
  }

  // Result card by strategy type and rank
  getResultCard(strategyType, rank) {
    return this.getByTestId(`ofo-card-${strategyType}-${rank}`);
  }

  // Card elements
  getCardRank(rank) {
    return this.getByTestId(`ofo-card-rank-${rank}`);
  }

  getCardName(rank) {
    return this.getByTestId(`ofo-card-name-${rank}`);
  }

  getCardProfit(rank) {
    return this.getByTestId(`ofo-card-profit-${rank}`);
  }

  getCardLegs(rank) {
    return this.getByTestId(`ofo-card-legs-${rank}`);
  }

  getCardBuilderButton(rank) {
    return this.getByTestId(`ofo-card-builder-${rank}`);
  }

  getCardOrderButton(rank) {
    return this.getByTestId(`ofo-card-order-${rank}`);
  }

  // Strategy option in dropdown
  getStrategyOption(strategyKey) {
    return this.getByTestId(`ofo-strategy-option-${strategyKey}`);
  }

  // Strategy select all / clear all
  get selectAllStrategiesBtn() { return this.getByTestId('ofo-strategy-select-all'); }
  get clearAllStrategiesBtn() { return this.getByTestId('ofo-strategy-clear-all'); }

  // ============ Actions ============

  async navigate() {
    await super.navigate();
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.waitForTestId('ofo-page');
  }

  async waitForResultsLoad() {
    // Wait for loading to complete and results to appear
    try {
      await this.page.waitForSelector('[data-testid="ofo-loading"]', { state: 'hidden', timeout: 30000 });
    } catch {
      // Loading might already be hidden
    }
    // Wait for results section or empty state
    await Promise.race([
      this.waitForTestId('ofo-results'),
      this.waitForTestId('ofo-empty')
    ]);
  }

  async selectUnderlying(underlying) {
    const tab = this.getByTestId(`ofo-underlying-${underlying.toLowerCase()}`);
    await tab.click();
  }

  async selectExpiry(expiryValue) {
    await this.expirySelect.selectOption(expiryValue);
  }

  async openStrategyDropdown() {
    await this.strategyTrigger.click();
    await this.page.waitForSelector('[data-testid="ofo-strategy-dropdown"]', { timeout: 5000 });
  }

  async closeStrategyDropdown() {
    // Click outside to close
    await this.page.locator('.dropdown-backdrop').click();
  }

  async toggleStrategy(strategyKey) {
    const isDropdownOpen = await this.strategyDropdown.isVisible().catch(() => false);
    if (!isDropdownOpen) {
      await this.openStrategyDropdown();
    }
    await this.getStrategyOption(strategyKey).click();
  }

  async selectAllStrategies() {
    const isDropdownOpen = await this.strategyDropdown.isVisible().catch(() => false);
    if (!isDropdownOpen) {
      await this.openStrategyDropdown();
    }
    await this.selectAllStrategiesBtn.click();
  }

  async clearAllStrategies() {
    const isDropdownOpen = await this.strategyDropdown.isVisible().catch(() => false);
    if (!isDropdownOpen) {
      await this.openStrategyDropdown();
    }
    await this.clearAllStrategiesBtn.click();
  }

  async setStrikeRange(value) {
    await this.strikeRangeSelect.selectOption(String(value));
  }

  async setLots(lots) {
    await this.lotsInput.fill(String(lots));
  }

  async calculate() {
    await this.calculateButton.click();
    await this.waitForResultsLoad();
  }

  async toggleAutoRefresh() {
    await this.autoRefreshToggle.locator('input').click();
  }

  async setAutoRefreshInterval(interval) {
    await this.autoRefreshInterval.selectOption(String(interval));
  }

  async openInBuilder(strategyType, rank) {
    const button = this.getByTestId(`ofo-card-builder-${rank}`);
    await button.click();
    await this.page.waitForURL('**/strategy**');
  }

  async placeOrder(strategyType, rank) {
    const button = this.getByTestId(`ofo-card-order-${rank}`);
    await button.click();
  }

  async getSpotPrice() {
    const text = await this.spotPrice.textContent();
    return parseFloat(text.replace(/,/g, '').replace('₹', ''));
  }

  async getCalculationTime() {
    const text = await this.calcTime.textContent();
    return text;
  }

  async getSelectedStrategiesCount() {
    const text = await this.strategyTrigger.textContent();
    const match = text.match(/(\d+) selected/);
    return match ? parseInt(match[1]) : 0;
  }

  async getResultCardCount(strategyType) {
    const cardsContainer = this.getStrategyGroupCards(strategyType);
    const cards = await cardsContainer.locator('[data-testid^="ofo-card-"]').all();
    return cards.length;
  }

  async hasResults() {
    return await this.resultsSection.isVisible().catch(() => false);
  }

  async hasEmptyState() {
    return await this.emptyState.isVisible().catch(() => false);
  }

  async hasError() {
    return await this.errorAlert.isVisible().catch(() => false);
  }

  async isLoading() {
    return await this.loadingState.isVisible().catch(() => false);
  }

  // ============ Assertions ============

  async assertPageVisible() {
    await this.assertVisible('ofo-page');
  }

  async assertHeaderVisible() {
    await this.assertVisible('ofo-header');
  }

  async assertUnderlyingTabsVisible() {
    await this.assertVisible('ofo-underlying-tabs');
  }

  async assertControlsVisible() {
    await this.assertVisible('ofo-expiry-select');
    await this.assertVisible('ofo-strategy-select');
    await this.assertVisible('ofo-strike-range');
    await this.assertVisible('ofo-lots-input');
    await this.assertVisible('ofo-calculate-btn');
  }

  async assertResultsVisible() {
    await this.assertVisible('ofo-results');
  }

  async assertEmptyState() {
    await this.assertVisible('ofo-empty');
  }

  async assertLoading() {
    await this.assertVisible('ofo-loading');
  }

  async assertError() {
    await this.assertVisible('ofo-error');
  }

  async assertStrategyGroupVisible(strategyType) {
    await this.assertVisible(`ofo-group-${strategyType}`);
  }

  async assertResultCardVisible(strategyType, rank) {
    await this.assertVisible(`ofo-card-${strategyType}-${rank}`);
  }
}
