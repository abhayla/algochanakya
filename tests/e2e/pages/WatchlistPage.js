import { BasePage } from './BasePage.js';

/**
 * Page Object for Watchlist screen
 * Path: /watchlist
 */
export class WatchlistPage extends BasePage {
  constructor(page) {
    super(page);
    this.path = '/watchlist';
  }

  // ============ Selectors ============

  // Page container
  get pageContainer() { return this.getByTestId('watchlist-page'); }

  // Search
  get searchInput() { return this.getByTestId('watchlist-search-input'); }
  get searchDropdown() { return this.getByTestId('watchlist-search-dropdown'); }
  get noResultsMessage() { return this.getByTestId('watchlist-no-results'); }

  // Header
  get header() { return this.getByTestId('watchlist-header'); }
  get watchlistCount() { return this.getByTestId('watchlist-count'); }
  get newGroupButton() { return this.getByTestId('watchlist-new-group-button'); }

  // Tabs
  get tabsContainer() { return this.getByTestId('watchlist-tabs'); }
  get addTabButton() { return this.getByTestId('watchlist-add-tab-button'); }

  // Loading and Empty states
  get loadingIndicator() { return this.getByTestId('watchlist-loading'); }
  get instrumentsList() { return this.getByTestId('watchlist-instruments-list'); }
  get emptyState() { return this.getByTestId('watchlist-empty-state'); }
  get instrumentsContainer() { return this.getByTestId('watchlist-instruments'); }

  // Create Modal
  get createModal() { return this.getByTestId('watchlist-create-modal'); }
  get createModalContent() { return this.getByTestId('watchlist-create-modal-content'); }
  get createInput() { return this.getByTestId('watchlist-create-input'); }
  get createCancelButton() { return this.getByTestId('watchlist-create-cancel'); }
  get createSubmitButton() { return this.getByTestId('watchlist-create-submit'); }

  // ============ Dynamic Selectors ============

  getTab(id) {
    return this.getByTestId(`watchlist-tab-${id}`);
  }

  getSearchResult(instrumentToken) {
    return this.getByTestId(`watchlist-search-result-${instrumentToken}`);
  }

  getInstrumentRow(token) {
    return this.getByTestId(`watchlist-instrument-row-${token}`);
  }

  getRemoveButton(token) {
    return this.getByTestId(`watchlist-remove-button-${token}`);
  }

  // ============ Actions ============

  async navigate() {
    await super.navigate(this.path);
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.waitForTestId('watchlist-page');
  }

  async search(query) {
    await this.searchInput.fill(query);
    // Wait for debounce and results
    await this.page.waitForTimeout(500);
  }

  async clearSearch() {
    await this.searchInput.clear();
  }

  async selectSearchResult(instrumentToken) {
    await this.getSearchResult(instrumentToken).click();
  }

  async selectTab(id) {
    await this.getTab(id).click();
  }

  async openCreateModal() {
    await this.newGroupButton.click();
    await this.waitForTestId('watchlist-create-modal');
  }

  async createWatchlist(name) {
    await this.openCreateModal();
    await this.createInput.fill(name);
    await this.createSubmitButton.click();
    // Wait for modal to close
    await this.page.waitForSelector('[data-testid="watchlist-create-modal"]', { state: 'hidden' });
  }

  async cancelCreateModal() {
    await this.createCancelButton.click();
  }

  async removeInstrument(token) {
    // Hover to show remove button
    await this.getInstrumentRow(token).hover();
    await this.getRemoveButton(token).click();
  }

  async getInstrumentCount() {
    const countText = await this.watchlistCount.textContent();
    const match = countText.match(/\((\d+)\/100\)/);
    return match ? parseInt(match[1]) : 0;
  }

  async getTabCount() {
    const tabs = await this.tabsContainer.locator('button[data-testid^="watchlist-tab-"]').all();
    return tabs.length;
  }

  async isInstrumentInList(token) {
    const row = this.getInstrumentRow(token);
    return await row.isVisible().catch(() => false);
  }

  async waitForInstruments() {
    // Wait for either instruments or empty state
    await Promise.race([
      this.waitForTestId('watchlist-instruments'),
      this.waitForTestId('watchlist-empty-state')
    ]);
  }

  // ============ Assertions ============

  async assertPageVisible() {
    await this.assertVisible('watchlist-page');
  }

  async assertSearchResultsVisible() {
    await this.assertVisible('watchlist-search-dropdown');
  }

  async assertNoResultsVisible() {
    await this.assertVisible('watchlist-no-results');
  }

  async assertEmptyState() {
    await this.assertVisible('watchlist-empty-state');
  }

  async assertInstrumentsVisible() {
    await this.assertVisible('watchlist-instruments');
  }

  async assertCreateModalVisible() {
    await this.assertVisible('watchlist-create-modal');
  }

  async assertCreateModalHidden() {
    await this.assertHidden('watchlist-create-modal');
  }
}
