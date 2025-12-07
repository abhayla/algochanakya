import { BasePage } from './BasePage.js';

/**
 * Page Object for Strategy Library screen
 * Path: /strategies
 *
 * Features tested:
 * - Category filtering
 * - Strategy search
 * - Strategy cards display
 * - Strategy Wizard modal
 * - Strategy Details modal
 * - Deploy modal
 * - Strategy comparison
 */
export default class StrategyLibraryPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/strategies';
  }

  // ============ Page Selectors ============

  get pageContainer() { return this.getByTestId('strategy-library-page'); }
  get pageTitle() { return this.getByTestId('strategy-library-title'); }
  get loadingSpinner() { return this.getByTestId('strategy-library-loading'); }
  get errorMessage() { return this.getByTestId('strategy-library-error'); }

  // ============ Category Selectors ============

  get categoryContainer() { return this.getByTestId('strategy-library-categories'); }
  get categoryAll() { return this.getByTestId('strategy-library-category-all'); }
  get categoryBullish() { return this.getByTestId('strategy-library-category-bullish'); }
  get categoryBearish() { return this.getByTestId('strategy-library-category-bearish'); }
  get categoryNeutral() { return this.getByTestId('strategy-library-category-neutral'); }
  get categoryVolatile() { return this.getByTestId('strategy-library-category-volatile'); }
  get categoryIncome() { return this.getByTestId('strategy-library-category-income'); }
  get categoryAdvanced() { return this.getByTestId('strategy-library-category-advanced'); }

  getCategoryPill(category) {
    return this.getByTestId(`strategy-library-category-${category.toLowerCase()}`);
  }

  // ============ Search Selectors ============

  get searchContainer() { return this.getByTestId('strategy-library-search-container'); }
  get searchInput() { return this.getByTestId('strategy-library-search-input'); }
  get searchClearButton() { return this.getByTestId('strategy-library-search-clear'); }

  // ============ Wizard Button ============

  get wizardButton() { return this.getByTestId('strategy-library-wizard-button'); }

  // ============ Strategy Cards Grid ============

  get cardsGrid() { return this.getByTestId('strategy-library-cards-grid'); }
  get emptyState() { return this.getByTestId('strategy-library-empty-state'); }

  getStrategyCard(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}`);
  }

  getCardName(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-name`);
  }

  getCardCategory(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-category`);
  }

  getCardMaxProfit(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-max-profit`);
  }

  getCardMaxLoss(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-max-loss`);
  }

  getCardWinProbability(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-win-probability`);
  }

  getCardRiskLevel(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-risk-level`);
  }

  getCardThetaBadge(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-theta`);
  }

  getCardVegaBadge(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-vega`);
  }

  getCardDeltaBadge(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-delta`);
  }

  getCardViewDetailsButton(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-view-details`);
  }

  getCardDeployButton(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-deploy`);
  }

  getCardCompareCheckbox(strategyName) {
    return this.getByTestId(`strategy-card-${strategyName}-compare`);
  }

  // ============ Strategy Wizard Modal ============

  get wizardModal() { return this.getByTestId('strategy-wizard-modal'); }
  get wizardModalTitle() { return this.getByTestId('strategy-wizard-modal-title'); }
  get wizardModalClose() { return this.getByTestId('strategy-wizard-modal-close'); }

  // Wizard Step 1: Market Outlook
  get wizardStep1() { return this.getByTestId('strategy-wizard-step-1'); }
  get wizardOutlookBullish() { return this.getByTestId('strategy-wizard-outlook-bullish'); }
  get wizardOutlookBearish() { return this.getByTestId('strategy-wizard-outlook-bearish'); }
  get wizardOutlookNeutral() { return this.getByTestId('strategy-wizard-outlook-neutral'); }
  get wizardOutlookVolatile() { return this.getByTestId('strategy-wizard-outlook-volatile'); }

  // Wizard Step 2: Volatility View
  get wizardStep2() { return this.getByTestId('strategy-wizard-step-2'); }
  get wizardVolatilityHigh() { return this.getByTestId('strategy-wizard-volatility-high'); }
  get wizardVolatilityLow() { return this.getByTestId('strategy-wizard-volatility-low'); }
  get wizardVolatilityAny() { return this.getByTestId('strategy-wizard-volatility-any'); }

  // Wizard Step 3: Risk Tolerance
  get wizardStep3() { return this.getByTestId('strategy-wizard-step-3'); }
  get wizardRiskLow() { return this.getByTestId('strategy-wizard-risk-low'); }
  get wizardRiskMedium() { return this.getByTestId('strategy-wizard-risk-medium'); }
  get wizardRiskHigh() { return this.getByTestId('strategy-wizard-risk-high'); }

  // Wizard Navigation
  get wizardBackButton() { return this.getByTestId('strategy-wizard-back-button'); }
  get wizardNextButton() { return this.getByTestId('strategy-wizard-next-button'); }
  get wizardGetRecommendationsButton() { return this.getByTestId('strategy-wizard-get-recommendations'); }

  // Wizard Recommendations
  get wizardRecommendations() { return this.getByTestId('strategy-wizard-recommendations'); }

  getWizardRecommendation(index) {
    return this.getByTestId(`strategy-wizard-recommendation-${index}`);
  }

  getWizardRecommendationScore(index) {
    return this.getByTestId(`strategy-wizard-recommendation-${index}-score`);
  }

  getWizardRecommendationReasons(index) {
    return this.getByTestId(`strategy-wizard-recommendation-${index}-reasons`);
  }

  // ============ Strategy Details Modal ============

  get detailsModal() { return this.getByTestId('strategy-details-modal'); }
  get detailsModalTitle() { return this.getByTestId('strategy-details-modal-title'); }
  get detailsModalClose() { return this.getByTestId('strategy-details-modal-close'); }
  get detailsDescription() { return this.getByTestId('strategy-details-description'); }
  get detailsWhenToUse() { return this.getByTestId('strategy-details-when-to-use'); }
  get detailsPros() { return this.getByTestId('strategy-details-pros'); }
  get detailsCons() { return this.getByTestId('strategy-details-cons'); }
  get detailsCommonMistakes() { return this.getByTestId('strategy-details-common-mistakes'); }
  get detailsExitRules() { return this.getByTestId('strategy-details-exit-rules'); }
  get detailsDeployButton() { return this.getByTestId('strategy-details-deploy-button'); }

  // ============ Deploy Modal ============

  get deployModal() { return this.getByTestId('strategy-deploy-modal'); }
  get deployModalTitle() { return this.getByTestId('strategy-deploy-modal-title'); }
  get deployModalClose() { return this.getByTestId('strategy-deploy-modal-close'); }
  get deployUnderlyingSelect() { return this.getByTestId('strategy-deploy-underlying'); }
  get deployExpirySelect() { return this.getByTestId('strategy-deploy-expiry'); }
  get deployLotsInput() { return this.getByTestId('strategy-deploy-lots'); }
  get deployLegsPreview() { return this.getByTestId('strategy-deploy-legs-preview'); }
  get deployNetPremium() { return this.getByTestId('strategy-deploy-net-premium'); }
  get deployButton() { return this.getByTestId('strategy-deploy-confirm-button'); }
  get deployCancelButton() { return this.getByTestId('strategy-deploy-cancel-button'); }

  // ============ Comparison Bar ============

  get comparisonBar() { return this.getByTestId('strategy-comparison-bar'); }
  get comparisonCount() { return this.getByTestId('strategy-comparison-count'); }
  get comparisonClearButton() { return this.getByTestId('strategy-comparison-clear'); }
  get comparisonCompareButton() { return this.getByTestId('strategy-comparison-compare-button'); }

  // ============ Comparison Modal ============

  get compareModal() { return this.getByTestId('strategy-compare-modal'); }
  get compareModalTitle() { return this.getByTestId('strategy-compare-modal-title'); }
  get compareModalClose() { return this.getByTestId('strategy-compare-modal-close'); }
  get compareTable() { return this.getByTestId('strategy-compare-table'); }

  // ============ Actions ============

  async navigate() {
    await this.page.goto(this.url);
    await this.waitForLoad();
  }

  async waitForPageLoad() {
    await this.waitForTestId('strategy-library-page');
  }

  async selectCategory(category) {
    await this.getCategoryPill(category).click();
    await this.page.waitForTimeout(300); // Wait for filter to apply
  }

  async clearCategoryFilter() {
    await this.categoryAll.click();
    await this.page.waitForTimeout(300);
  }

  async search(query) {
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(500); // Wait for debounce
  }

  async clearSearch() {
    await this.searchClearButton.click();
    await this.page.waitForTimeout(300);
  }

  async openWizard() {
    await this.wizardButton.click();
    await this.waitForTestId('strategy-wizard-modal');
  }

  async closeWizard() {
    await this.wizardModalClose.click();
    await this.page.waitForSelector('[data-testid="strategy-wizard-modal"]', { state: 'hidden' });
  }

  async selectWizardOutlook(outlook) {
    const option = this.getByTestId(`strategy-wizard-outlook-${outlook.toLowerCase()}`);
    await option.click();
  }

  async selectWizardVolatility(volatility) {
    const option = this.getByTestId(`strategy-wizard-volatility-${volatility.toLowerCase()}`);
    await option.click();
  }

  async selectWizardRisk(risk) {
    const option = this.getByTestId(`strategy-wizard-risk-${risk.toLowerCase()}`);
    await option.click();
  }

  async wizardNext() {
    await this.wizardNextButton.click();
    await this.page.waitForTimeout(300);
  }

  async wizardBack() {
    await this.wizardBackButton.click();
    await this.page.waitForTimeout(300);
  }

  async getRecommendations() {
    await this.wizardGetRecommendationsButton.click();
    await this.waitForTestId('strategy-wizard-recommendations');
  }

  async openStrategyDetails(strategyName) {
    await this.getCardViewDetailsButton(strategyName).click();
    await this.waitForTestId('strategy-details-modal');
  }

  async closeDetails() {
    await this.detailsModalClose.click();
    await this.page.waitForSelector('[data-testid="strategy-details-modal"]', { state: 'hidden' });
  }

  async openDeploy(strategyName) {
    await this.getCardDeployButton(strategyName).click();
    await this.waitForTestId('strategy-deploy-modal');
  }

  async openDeployFromDetails() {
    await this.detailsDeployButton.click();
    await this.waitForTestId('strategy-deploy-modal');
  }

  async closeDeploy() {
    await this.deployCancelButton.click();
    await this.page.waitForSelector('[data-testid="strategy-deploy-modal"]', { state: 'hidden' });
  }

  async selectDeployUnderlying(underlying) {
    await this.deployUnderlyingSelect.selectOption(underlying);
  }

  async selectDeployExpiry(expiry) {
    await this.deployExpirySelect.selectOption(expiry);
  }

  async setDeployLots(lots) {
    await this.deployLotsInput.fill(String(lots));
  }

  async confirmDeploy() {
    await this.deployButton.click();
  }

  async addToComparison(strategyName) {
    await this.getCardCompareCheckbox(strategyName).click();
    await this.page.waitForTimeout(200);
  }

  async removeFromComparison(strategyName) {
    await this.getCardCompareCheckbox(strategyName).click();
    await this.page.waitForTimeout(200);
  }

  async clearComparison() {
    await this.comparisonClearButton.click();
    await this.page.waitForTimeout(200);
  }

  async openCompareModal() {
    await this.comparisonCompareButton.click();
    await this.waitForTestId('strategy-compare-modal');
  }

  async closeCompareModal() {
    await this.compareModalClose.click();
    await this.page.waitForSelector('[data-testid="strategy-compare-modal"]', { state: 'hidden' });
  }

  // ============ Getters ============

  async getStrategyCards() {
    const cards = await this.cardsGrid.locator('[data-testid^="strategy-card-"]').all();
    return cards;
  }

  async getStrategyCardCount() {
    const cards = await this.getStrategyCards();
    return cards.length;
  }

  async getCategoryCount(category) {
    const pill = this.getCategoryPill(category);
    const countBadge = pill.locator('.count, .badge');
    const text = await countBadge.textContent();
    return parseInt(text) || 0;
  }

  async getComparisonCount() {
    const text = await this.comparisonCount.textContent();
    return parseInt(text) || 0;
  }

  async getRecommendationCount() {
    const items = await this.wizardRecommendations.locator('[data-testid^="strategy-wizard-recommendation-"]').all();
    return items.length;
  }

  async getDeployLegsCount() {
    const legs = await this.deployLegsPreview.locator('tr, .leg-row').all();
    return legs.length;
  }

  // ============ Assertions ============

  async assertPageVisible() {
    const visible = await this.pageContainer.isVisible();
    if (!visible) throw new Error('Strategy Library page not visible');
  }

  async assertCategoriesVisible() {
    const visible = await this.categoryContainer.isVisible();
    if (!visible) throw new Error('Categories container not visible');
  }

  async assertWizardButtonVisible() {
    const visible = await this.wizardButton.isVisible();
    if (!visible) throw new Error('Wizard button not visible');
  }

  async assertCardsGridVisible() {
    const visible = await this.cardsGrid.isVisible();
    if (!visible) throw new Error('Cards grid not visible');
  }

  async assertEmptyStateVisible() {
    const visible = await this.emptyState.isVisible();
    if (!visible) throw new Error('Empty state not visible');
  }

  async assertWizardModalVisible() {
    const visible = await this.wizardModal.isVisible();
    if (!visible) throw new Error('Wizard modal not visible');
  }

  async assertDetailsModalVisible() {
    const visible = await this.detailsModal.isVisible();
    if (!visible) throw new Error('Details modal not visible');
  }

  async assertDeployModalVisible() {
    const visible = await this.deployModal.isVisible();
    if (!visible) throw new Error('Deploy modal not visible');
  }

  async assertComparisonBarVisible() {
    const visible = await this.comparisonBar.isVisible();
    if (!visible) throw new Error('Comparison bar not visible');
  }

  async assertCompareModalVisible() {
    const visible = await this.compareModal.isVisible();
    if (!visible) throw new Error('Compare modal not visible');
  }

  async assertNoHorizontalOverflow() {
    const hasOverflow = await this.hasHorizontalOverflow();
    if (hasOverflow) throw new Error('Page has horizontal overflow');
  }
}
