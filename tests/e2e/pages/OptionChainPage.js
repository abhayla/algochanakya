import { BasePage } from './BasePage.js';

/**
 * Page Object for Option Chain screen
 * Path: /optionchain
 */
export class OptionChainPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/optionchain';
  }

  // ============ Selectors ============

  // Page container
  get pageContainer() { return this.getByTestId('optionchain-page'); }
  get header() { return this.getByTestId('optionchain-header'); }

  // Underlying tabs
  get underlyingTabs() { return this.getByTestId('optionchain-underlying-tabs'); }
  get niftyTab() { return this.getByTestId('optionchain-underlying-nifty'); }
  get bankniftyTab() { return this.getByTestId('optionchain-underlying-banknifty'); }
  get finniftyTab() { return this.getByTestId('optionchain-underlying-finnifty'); }

  // Expiry and controls
  get expirySelect() { return this.getByTestId('optionchain-expiry-select'); }
  get spotBox() { return this.getByTestId('optionchain-spot-box'); }
  get spotPrice() { return this.getByTestId('optionchain-spot-price'); }
  get dteBox() { return this.getByTestId('optionchain-dte-box'); }
  get dteValue() { return this.getByTestId('optionchain-dte-value'); }
  get greeksToggle() { return this.getByTestId('optionchain-greeks-toggle'); }
  get liveToggle() { return this.getByTestId('optionchain-live-toggle'); }
  get refreshButton() { return this.getByTestId('optionchain-refresh-button'); }

  // Summary bar
  get summaryBar() { return this.getByTestId('optionchain-summary-bar'); }
  get pcrValue() { return this.getByTestId('optionchain-pcr'); }
  get maxPain() { return this.getByTestId('optionchain-max-pain'); }
  get ceOI() { return this.getByTestId('optionchain-ce-oi'); }
  get peOI() { return this.getByTestId('optionchain-pe-oi'); }
  get lotSize() { return this.getByTestId('optionchain-lot-size'); }
  get strikesRange() { return this.getByTestId('optionchain-strikes-range'); }

  // States
  get errorAlert() { return this.getByTestId('optionchain-error'); }
  get loadingState() { return this.getByTestId('optionchain-loading'); }
  get emptyState() { return this.getByTestId('optionchain-empty-state'); }

  // Table
  get tableContainer() { return this.getByTestId('optionchain-table-container'); }
  get table() { return this.getByTestId('optionchain-table'); }

  // Selected bar
  get selectedBar() { return this.getByTestId('optionchain-selected-bar'); }
  get clearSelectionButton() { return this.getByTestId('optionchain-clear-selection'); }
  get addToStrategyButton() { return this.getByTestId('optionchain-add-to-strategy'); }

  // Strike Finder
  get strikeFinderBtn() { return this.getByTestId('optionchain-strike-finder-btn'); }
  get strikeFinderMode() { return this.getByTestId('optionchain-strike-finder-mode'); }
  get strikeFinderType() { return this.getByTestId('optionchain-strike-finder-type'); }
  get strikeFinderDeltaInput() { return this.getByTestId('optionchain-strike-finder-delta-input'); }
  get strikeFinderPremiumInput() { return this.getByTestId('optionchain-strike-finder-premium-input'); }
  get strikeFinderSearchBtn() { return this.getByTestId('optionchain-strike-finder-search-btn'); }
  get strikeFinderResult() { return this.getByTestId('optionchain-strike-finder-result'); }
  get strikeFinderError() { return this.getByTestId('optionchain-strike-finder-error'); }
  get strikeFinderClose() { return this.getByTestId('optionchain-strike-finder-close'); }

  // ATM row and badge
  get atmRow() { return this.page.locator('[data-atm-row]'); }
  get atmBadge() { return this.getByTestId('optionchain-atm-badge'); }

  // LTP cells (legacy static selector — prefer per-strike getters below)
  get ltpCells() { return this.page.locator('[data-testid^="optionchain-ce-ltp-"], [data-testid^="optionchain-pe-ltp-"]'); }

  // ============ Dynamic Selectors ============

  getStrikeRow(strike) {
    return this.getByTestId(`optionchain-strike-row-${strike}`);
  }

  getCEAddButton(strike) {
    return this.getByTestId(`optionchain-ce-add-${strike}`);
  }

  getPEAddButton(strike) {
    return this.getByTestId(`optionchain-pe-add-${strike}`);
  }

  getSelectedChip(strike, type) {
    return this.getByTestId(`optionchain-selected-chip-${strike}-${type}`);
  }

  // Per-strike data selectors
  getCELTP(strike) { return this.getByTestId(`optionchain-ce-ltp-${strike}`); }
  getPELTP(strike) { return this.getByTestId(`optionchain-pe-ltp-${strike}`); }
  getCEOI(strike) { return this.getByTestId(`optionchain-ce-oi-${strike}`); }
  getPEOI(strike) { return this.getByTestId(`optionchain-pe-oi-${strike}`); }
  getCEIV(strike) { return this.getByTestId(`optionchain-ce-iv-${strike}`); }
  getPEIV(strike) { return this.getByTestId(`optionchain-pe-iv-${strike}`); }
  getCEVolume(strike) { return this.getByTestId(`optionchain-ce-volume-${strike}`); }
  getPEVolume(strike) { return this.getByTestId(`optionchain-pe-volume-${strike}`); }
  getStrikeCell(strike) { return this.getByTestId(`optionchain-strike-${strike}`); }

  // ============ Data Extraction ============

  /**
   * Parse a numeric string, stripping commas, K/L suffixes, and whitespace.
   * Returns NaN if the text is '-' or empty.
   */
  static parseNumericText(text) {
    if (!text || text.trim() === '-' || text.trim() === '') return NaN;
    let cleaned = text.replace(/,/g, '').trim();
    if (cleaned.endsWith('L')) return parseFloat(cleaned) * 100000;
    if (cleaned.endsWith('K')) return parseFloat(cleaned) * 1000;
    return parseFloat(cleaned);
  }

  /** Get all visible strike values from the table. */
  async getVisibleStrikes() {
    const rows = this.page.locator('[data-testid^="optionchain-strike-row-"]');
    const count = await rows.count();
    const strikes = [];
    for (let i = 0; i < count; i++) {
      const testid = await rows.nth(i).getAttribute('data-testid');
      const strike = parseFloat(testid.replace('optionchain-strike-row-', ''));
      if (!isNaN(strike)) strikes.push(strike);
    }
    return strikes;
  }

  /** Get CE LTP value for a strike as a float. */
  async getCELTPValue(strike) {
    const text = await this.getCELTP(strike).textContent();
    return OptionChainPage.parseNumericText(text);
  }

  /** Get PE LTP value for a strike as a float. */
  async getPELTPValue(strike) {
    const text = await this.getPELTP(strike).textContent();
    return OptionChainPage.parseNumericText(text);
  }

  /** Get CE OI value for a strike as a float. */
  async getCEOIValue(strike) {
    const text = await this.getCEOI(strike).locator('span').textContent();
    return OptionChainPage.parseNumericText(text);
  }

  /** Get PE OI value for a strike as a float. */
  async getPEOIValue(strike) {
    const text = await this.getPEOI(strike).locator('span').textContent();
    return OptionChainPage.parseNumericText(text);
  }

  /** Get all available expiry option values from the dropdown. */
  async getExpiryOptions() {
    const options = this.expirySelect.locator('option');
    const count = await options.count();
    const values = [];
    for (let i = 0; i < count; i++) {
      const val = await options.nth(i).getAttribute('value');
      if (val) values.push(val);
    }
    return values;
  }

  // ============ Actions ============

  async navigate() {
    await super.navigate();
    await this.waitForPageLoad();
    // Wait for initial API response (table, empty state, or error)
    // This prevents race conditions where tests run before data loads
    await this.waitForInitialLoad();
  }

  async waitForPageLoad() {
    await this.waitForTestId('optionchain-page', { timeout: 30000 });
  }

  /**
   * Wait for initial page load - ensures option chain data has loaded
   * SmartAPI instruments are pre-warmed in global-setup, so this should be fast
   */
  async waitForInitialLoad() {
    // Wait for option chain table OR empty state to appear
    // This indicates the API call has completed and Vue has rendered
    try {
      await Promise.race([
        this.page.locator('[data-testid="optionchain-table"] tbody tr').first().waitFor({ state: 'visible', timeout: 30000 }),
        this.page.locator('[data-testid="optionchain-empty-state"]').waitFor({ state: 'visible', timeout: 30000 })
      ]);
    } catch {
      // If neither appears within timeout, continue anyway
      // Individual test assertions will catch any issues
    }
  }

  async waitForChainLoad() {
    // Wait for table, empty state, or error — returns which state appeared
    const result = await Promise.race([
      this.waitForTestId('optionchain-table', { timeout: 30000 }).then(() => 'table'),
      this.waitForTestId('optionchain-empty-state', { timeout: 30000 }).then(() => 'empty'),
      this.waitForTestId('optionchain-error', { timeout: 30000 }).then(() => 'error'),
    ]);
    return result;
  }

  async assertChainLoaded() {
    // Asserts chain loaded successfully (table or empty state, not error)
    const state = await this.waitForChainLoad();
    if (state === 'error') {
      throw new Error('Option chain failed to load (optionchain-error shown)');
    }
    return state;
  }

  async selectUnderlying(underlying) {
    const tab = this.getByTestId(`optionchain-underlying-${underlying.toLowerCase()}`);
    await tab.click();
    await this.waitForChainLoad();
  }

  async selectExpiry(expiryValue) {
    await this.expirySelect.selectOption(expiryValue);
    await this.waitForChainLoad();
  }

  async toggleGreeks() {
    await this.greeksToggle.click();
  }

  async toggleLiveUpdates() {
    await this.liveToggle.locator('input').click();
  }

  async isLiveEnabled() {
    const checkbox = this.liveToggle.locator('input');
    return await checkbox.isChecked();
  }

  async isLiveDotVisible() {
    const dot = this.liveToggle.locator('.live-dot');
    return await dot.isVisible().catch(() => false);
  }

  async refresh() {
    await this.refreshButton.click();
    await this.waitForChainLoad();
  }

  async setStrikesRange(value) {
    await this.strikesRange.selectOption({ value: String(value) });
  }

  async selectCE(strike) {
    await this.getCEAddButton(strike).click();
  }

  async selectPE(strike) {
    await this.getPEAddButton(strike).click();
  }

  async clearSelection() {
    await this.clearSelectionButton.click();
  }

  async addToStrategy() {
    await this.addToStrategyButton.click();
    // Wait for navigation to strategy page
    await this.page.waitForURL('**/strategy**');
  }

  async getSpotPrice() {
    const text = await this.spotPrice.textContent();
    return parseFloat(text.replace(/,/g, ''));
  }

  async getDTE() {
    const text = await this.dteValue.textContent();
    return parseInt(text);
  }

  async getPCR() {
    const pcrElement = await this.pcrValue.locator('.value');
    const text = await pcrElement.textContent();
    return parseFloat(text);
  }

  async getMaxPain() {
    const maxPainElement = await this.maxPain.locator('.value');
    const text = await maxPainElement.textContent();
    return parseFloat(text.replace(/,/g, ''));
  }

  async getSelectedCount() {
    const chips = await this.selectedBar.locator('[data-testid^="optionchain-selected-chip-"]').all();
    return chips.length;
  }

  async isStrikeSelected(strike, type) {
    const chip = this.getSelectedChip(strike, type);
    return await chip.isVisible().catch(() => false);
  }

  // Strike Finder methods
  async openStrikeFinder() {
    await this.strikeFinderBtn.click();
    await this.page.waitForSelector('[data-testid="optionchain-strike-finder-mode"]', { timeout: 10000 });
  }

  async closeStrikeFinder() {
    await this.strikeFinderClose.click();
  }

  async isStrikeFinderVisible() {
    const finder = this.page.locator('.strike-finder');
    return await finder.isVisible().catch(() => false);
  }

  async setStrikeFinderMode(mode) {
    await this.strikeFinderMode.selectOption(mode);
  }

  async setStrikeFinderType(type) {
    await this.strikeFinderType.selectOption(type);
  }

  async enterTargetDelta(delta) {
    await this.strikeFinderDeltaInput.fill(String(delta));
  }

  async enterTargetPremium(premium) {
    await this.strikeFinderPremiumInput.fill(String(premium));
  }

  async searchStrike() {
    await this.strikeFinderSearchBtn.click();
  }

  async findStrikeByDelta(delta, optionType = 'CE') {
    await this.openStrikeFinder();
    await this.setStrikeFinderMode('delta');
    await this.setStrikeFinderType(optionType);
    await this.enterTargetDelta(delta);
    await this.searchStrike();
  }

  async findStrikeByPremium(premium, optionType = 'CE') {
    await this.openStrikeFinder();
    await this.setStrikeFinderMode('premium');
    await this.setStrikeFinderType(optionType);
    await this.enterTargetPremium(premium);
    await this.searchStrike();
  }

  async hasStrikeFinderError() {
    return await this.strikeFinderError.isVisible().catch(() => false);
  }

  async getStrikeFinderErrorText() {
    if (await this.hasStrikeFinderError()) {
      return await this.strikeFinderError.textContent();
    }
    return null;
  }

  async hasStrikeFinderResult() {
    return await this.strikeFinderResult.isVisible().catch(() => false);
  }

  async getStrikeFinderResultStrike() {
    const strikeValue = this.strikeFinderResult.locator('.strike-value');
    return await strikeValue.textContent();
  }

  // ============ Assertions ============

  async assertPageVisible() {
    await this.assertVisible('optionchain-page');
  }

  async assertTableVisible() {
    await this.assertVisible('optionchain-table');
  }

  async assertEmptyState() {
    await this.assertVisible('optionchain-empty-state');
  }

  async assertLoading() {
    await this.assertVisible('optionchain-loading');
  }

  async assertError() {
    await this.assertVisible('optionchain-error');
  }

  async assertSelectedBarVisible() {
    await this.assertVisible('optionchain-selected-bar');
  }

  async assertSelectedBarHidden() {
    await this.assertHidden('optionchain-selected-bar');
  }

  async assertSummaryBarVisible() {
    await this.assertVisible('optionchain-summary-bar');
  }

  async assertLiveToggleVisible() {
    await this.assertVisible('optionchain-live-toggle');
  }
}
