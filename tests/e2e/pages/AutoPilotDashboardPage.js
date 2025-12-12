/**
 * AutoPilot Dashboard Page Object
 *
 * Page object for AutoPilot Dashboard view.
 * URL: /autopilot
 */

import { BasePage } from './BasePage.js';

export class AutoPilotDashboardPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot';
  }

  // ===========================================================================
  // LOCATORS - Summary Cards
  // ===========================================================================

  get summarySection() {
    return this.getByTestId('autopilot-summary-section');
  }

  get activeStrategiesCard() {
    return this.getByTestId('autopilot-active-strategies-card');
  }

  get activeStrategiesCount() {
    return this.getByTestId('autopilot-active-count');
  }

  get waitingStrategiesCount() {
    return this.getByTestId('autopilot-waiting-count');
  }

  get todayPnlCard() {
    return this.getByTestId('autopilot-today-pnl-card');
  }

  get todayPnlValue() {
    return this.getByTestId('autopilot-today-pnl-value');
  }

  get capitalUsedCard() {
    return this.getByTestId('autopilot-capital-used-card');
  }

  get capitalUsedValue() {
    return this.getByTestId('autopilot-capital-used-value');
  }

  get riskStatusCard() {
    return this.getByTestId('autopilot-risk-status-card');
  }

  get riskStatusBadge() {
    return this.getByTestId('autopilot-risk-status-badge');
  }

  // ===========================================================================
  // LOCATORS - Strategy List
  // ===========================================================================

  get strategyListSection() {
    return this.getByTestId('autopilot-strategy-list');
  }

  get strategyCards() {
    return this.page.locator('[data-testid^="autopilot-strategy-card-"]');
  }

  getStrategyCard(id) {
    return this.getByTestId(`autopilot-strategy-card-${id}`);
  }

  getStrategyStatus(id) {
    return this.getByTestId(`autopilot-strategy-status-${id}`);
  }

  getStrategyPnl(id) {
    return this.getByTestId(`autopilot-strategy-pnl-${id}`);
  }

  getStrategyActions(id) {
    return this.getByTestId(`autopilot-strategy-actions-${id}`);
  }

  // ===========================================================================
  // LOCATORS - Action Buttons
  // ===========================================================================

  get createStrategyButton() {
    return this.getByTestId('autopilot-create-strategy-btn');
  }

  get killSwitchButton() {
    return this.getByTestId('autopilot-kill-switch-btn');
  }

  get refreshButton() {
    return this.getByTestId('autopilot-refresh-btn');
  }

  get settingsButton() {
    return this.getByTestId('autopilot-settings-btn');
  }

  // ===========================================================================
  // LOCATORS - Filters
  // ===========================================================================

  get statusFilter() {
    return this.getByTestId('autopilot-status-filter');
  }

  get underlyingFilter() {
    return this.getByTestId('autopilot-underlying-filter');
  }

  get clearFiltersButton() {
    return this.getByTestId('autopilot-clear-filters-btn');
  }

  // ===========================================================================
  // LOCATORS - Activity Feed
  // ===========================================================================

  get activityFeed() {
    return this.getByTestId('autopilot-activity-feed');
  }

  get activityItems() {
    return this.page.locator('[data-testid^="autopilot-activity-item-"]');
  }

  // ===========================================================================
  // LOCATORS - Modals
  // ===========================================================================

  get killSwitchModal() {
    return this.getByTestId('autopilot-kill-switch-modal');
  }

  get killSwitchConfirmButton() {
    return this.getByTestId('autopilot-kill-switch-confirm');
  }

  get killSwitchCancelButton() {
    return this.getByTestId('autopilot-kill-switch-cancel');
  }

  get activateStrategyModal() {
    return this.getByTestId('autopilot-activate-modal');
  }

  get activateConfirmButton() {
    return this.getByTestId('autopilot-activate-confirm');
  }

  get paperTradingCheckbox() {
    return this.getByTestId('autopilot-paper-trading-checkbox');
  }

  // ===========================================================================
  // LOCATORS - Empty State
  // ===========================================================================

  get emptyState() {
    return this.getByTestId('autopilot-empty-state');
  }

  get emptyStateCreateButton() {
    return this.getByTestId('autopilot-empty-create-btn');
  }

  // ===========================================================================
  // LOCATORS - Connection Status
  // ===========================================================================

  get connectionStatus() {
    return this.getByTestId('autopilot-connection-status');
  }

  get brokerStatus() {
    return this.getByTestId('autopilot-broker-status');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForDashboardLoad() {
    // First wait for the dashboard container to appear
    await this.page.waitForSelector('[data-testid="autopilot-dashboard"]', {
      timeout: 10000
    });
    // Then wait for either the summary section (loaded state) or an error state
    // Using Promise.race to handle both success and error scenarios
    await Promise.race([
      this.page.waitForSelector('[data-testid="autopilot-summary-section"]', {
        timeout: 15000
      }),
      this.page.waitForSelector('[data-testid="autopilot-error"]', {
        timeout: 15000
      })
    ]);
    await this.page.waitForLoadState('networkidle');
  }

  async createNewStrategy() {
    await this.createStrategyButton.click();
    await this.page.waitForURL('**/autopilot/strategies/new');
  }

  async openSettings() {
    await this.settingsButton.click();
    await this.page.waitForURL('**/autopilot/settings');
  }

  async activateKillSwitch() {
    await this.killSwitchButton.click();
    await this.killSwitchModal.waitFor({ state: 'visible' });
  }

  async confirmKillSwitch() {
    await this.killSwitchConfirmButton.click();
    await this.killSwitchModal.waitFor({ state: 'hidden' });
  }

  async cancelKillSwitch() {
    await this.killSwitchCancelButton.click();
    await this.killSwitchModal.waitFor({ state: 'hidden' });
  }

  async filterByStatus(status) {
    await this.statusFilter.selectOption(status);
    // Wait briefly for the filter to apply (API call is triggered on change)
    await this.page.waitForTimeout(500);
  }

  async filterByUnderlying(underlying) {
    await this.underlyingFilter.selectOption(underlying);
    // Wait briefly for the filter to apply (API call is triggered on change)
    await this.page.waitForTimeout(500);
  }

  async clearAllFilters() {
    await this.clearFiltersButton.click();
    // Wait briefly for the filters to clear (API call is triggered)
    await this.page.waitForTimeout(500);
  }

  async clickStrategy(id) {
    await this.getStrategyCard(id).click();
    await this.page.waitForURL(`**/autopilot/strategies/${id}`);
  }

  async openStrategyActions(id) {
    await this.getStrategyActions(id).click();
  }

  async pauseStrategy(id) {
    await this.openStrategyActions(id);
    await this.getByTestId(`autopilot-pause-strategy-${id}`).click();
  }

  async resumeStrategy(id) {
    await this.openStrategyActions(id);
    await this.getByTestId(`autopilot-resume-strategy-${id}`).click();
  }

  async exitStrategy(id) {
    await this.openStrategyActions(id);
    await this.getByTestId(`autopilot-exit-strategy-${id}`).click();
  }

  async refreshDashboard() {
    await this.refreshButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getActiveCount() {
    const text = await this.activeStrategiesCount.textContent();
    return parseInt(text, 10);
  }

  async getWaitingCount() {
    const text = await this.waitingStrategiesCount.textContent();
    return parseInt(text, 10);
  }

  async getTodayPnl() {
    const text = await this.todayPnlValue.textContent();
    return parseFloat(text.replace(/[^\d.-]/g, ''));
  }

  async getStrategyCount() {
    return await this.strategyCards.count();
  }

  async getRiskStatus() {
    return await this.riskStatusBadge.textContent();
  }

  async isConnected() {
    const status = await this.connectionStatus.getAttribute('data-status');
    return status === 'connected';
  }

  async isBrokerConnected() {
    const status = await this.brokerStatus.getAttribute('data-connected');
    return status === 'true';
  }
}


/**
 * AutoPilot Strategy Builder Page Object
 *
 * Page object for AutoPilot Strategy Builder view.
 * URL: /autopilot/strategies/new or /autopilot/strategies/:id/edit
 */
export class AutoPilotStrategyBuilderPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/strategies/new';
  }

  // ===========================================================================
  // LOCATORS - Strategy Info
  // ===========================================================================

  get nameInput() {
    return this.getByTestId('autopilot-builder-name');
  }

  get descriptionInput() {
    return this.getByTestId('autopilot-builder-description');
  }

  get underlyingSelect() {
    return this.getByTestId('autopilot-builder-underlying');
  }

  get strategyTypeSelect() {
    return this.getByTestId('autopilot-builder-strategy-type');
  }

  get expiryTypeSelect() {
    return this.getByTestId('autopilot-builder-expiry-type');
  }

  get lotsInput() {
    return this.getByTestId('autopilot-builder-lots');
  }

  get positionTypeSelect() {
    return this.getByTestId('autopilot-builder-position-type');
  }

  // ===========================================================================
  // LOCATORS - Replace Legs Modal
  // ===========================================================================

  get replaceLegsModal() {
    return this.getByTestId('autopilot-replace-legs-modal');
  }

  get replaceLegsConfirmButton() {
    return this.getByTestId('autopilot-replace-legs-confirm');
  }

  get replaceLegsCancelButton() {
    return this.getByTestId('autopilot-replace-legs-cancel');
  }

  // ===========================================================================
  // LOCATORS - Legs (Enhanced Table)
  // ===========================================================================

  get legsSection() {
    return this.getByTestId('autopilot-legs-section');
  }

  get legsTable() {
    return this.getByTestId('autopilot-legs-table');
  }

  get addLegButton() {
    return this.getByTestId('autopilot-legs-add-row-button');
  }

  get deleteSelectedButton() {
    return this.getByTestId('autopilot-legs-delete-selected-button');
  }

  get selectAllCheckbox() {
    return this.getByTestId('autopilot-legs-select-all');
  }

  get legsActionBar() {
    return this.getByTestId('autopilot-legs-action-bar');
  }

  get legsEmptyState() {
    return this.getByTestId('autopilot-legs-empty-state');
  }

  get legsTotalRow() {
    return this.getByTestId('autopilot-legs-total-row');
  }

  get legRows() {
    return this.page.locator('[data-testid^="autopilot-leg-row-"]');
  }

  getLegRow(index) {
    return this.getByTestId(`autopilot-leg-row-${index}`);
  }

  getLegCheckbox(index) {
    return this.getByTestId(`autopilot-leg-checkbox-${index}`);
  }

  getLegAction(index) {
    return this.getByTestId(`autopilot-leg-action-${index}`);
  }

  getLegExpiry(index) {
    return this.getByTestId(`autopilot-leg-expiry-${index}`);
  }

  getLegStrike(index) {
    return this.getByTestId(`autopilot-leg-strike-${index}`);
  }

  getLegType(index) {
    return this.getByTestId(`autopilot-leg-type-${index}`);
  }

  getLegLots(index) {
    return this.getByTestId(`autopilot-leg-lots-${index}`);
  }

  getLegEntry(index) {
    return this.getByTestId(`autopilot-leg-entry-${index}`);
  }

  getLegCmp(index) {
    return this.getByTestId(`autopilot-leg-cmp-${index}`);
  }

  getLegExitPnl(index) {
    return this.getByTestId(`autopilot-leg-exit-pnl-${index}`);
  }

  getLegTargetPrice(index) {
    return this.getByTestId(`autopilot-leg-target-price-${index}`);
  }

  getLegStopLossPrice(index) {
    return this.getByTestId(`autopilot-leg-stop-loss-price-${index}`);
  }

  getLegTrailingSl(index) {
    return this.getByTestId(`autopilot-leg-trailing-sl-${index}`);
  }

  getLegTargetPct(index) {
    return this.getByTestId(`autopilot-leg-target-pct-${index}`);
  }

  getLegStopLossPct(index) {
    return this.getByTestId(`autopilot-leg-stop-loss-pct-${index}`);
  }

  getLegMaxLoss(index) {
    return this.getByTestId(`autopilot-leg-max-loss-${index}`);
  }

  getLegDeleteButton(index) {
    return this.getByTestId(`autopilot-leg-delete-${index}`);
  }

  // ===========================================================================
  // LOCATORS - Entry Conditions
  // ===========================================================================

  get conditionsSection() {
    return this.getByTestId('autopilot-builder-conditions');
  }

  get addConditionButton() {
    return this.getByTestId('autopilot-builder-add-condition');
  }

  get conditionLogicToggle() {
    return this.getByTestId('autopilot-condition-logic');
  }

  get conditionRows() {
    return this.page.locator('[data-testid^="autopilot-condition-row-"]');
  }

  getConditionRow(index) {
    return this.getByTestId(`autopilot-condition-row-${index}`);
  }

  // ===========================================================================
  // LOCATORS - Risk Settings
  // ===========================================================================

  get riskSection() {
    return this.getByTestId('autopilot-builder-risk');
  }

  get maxLossInput() {
    return this.getByTestId('autopilot-builder-max-loss');
  }

  get maxProfitInput() {
    return this.getByTestId('autopilot-builder-max-profit');
  }

  get trailingStopToggle() {
    return this.getByTestId('autopilot-builder-trailing-stop');
  }

  get trailingStopValue() {
    return this.getByTestId('autopilot-builder-trailing-stop-value');
  }

  // ===========================================================================
  // LOCATORS - Schedule
  // ===========================================================================

  get scheduleSection() {
    return this.getByTestId('autopilot-builder-schedule');
  }

  get activationModeSelect() {
    return this.getByTestId('autopilot-builder-activation-mode');
  }

  get startTimeInput() {
    return this.getByTestId('autopilot-builder-start-time');
  }

  get endTimeInput() {
    return this.getByTestId('autopilot-builder-end-time');
  }

  // ===========================================================================
  // LOCATORS - Step Navigation
  // ===========================================================================

  get stepIndicator() {
    return this.getByTestId('autopilot-builder-step');
  }

  get nextButton() {
    return this.getByTestId('autopilot-builder-next');
  }

  get previousButton() {
    return this.getByTestId('autopilot-builder-previous');
  }

  get saveButton() {
    return this.getByTestId('autopilot-builder-save');
  }

  get activateButton() {
    return this.getByTestId('autopilot-builder-activate');
  }

  get cancelButton() {
    return this.getByTestId('autopilot-builder-cancel');
  }

  // ===========================================================================
  // LOCATORS - Validation
  // ===========================================================================

  get validationErrors() {
    return this.page.locator('[data-testid^="autopilot-validation-error-"]');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async fillStrategyInfo({ name, description, underlying, lots }) {
    if (name) await this.nameInput.fill(name);
    if (description) await this.descriptionInput.fill(description);
    if (underlying) await this.underlyingSelect.selectOption(underlying);
    if (lots !== undefined) await this.lotsInput.fill(lots.toString());
  }

  async selectStrategyType(strategyType) {
    await this.strategyTypeSelect.selectOption(strategyType);
  }

  async confirmReplaceLegs() {
    await this.replaceLegsModal.waitFor({ state: 'visible' });
    await this.replaceLegsConfirmButton.click();
    await this.replaceLegsModal.waitFor({ state: 'hidden' });
  }

  async cancelReplaceLegs() {
    await this.replaceLegsModal.waitFor({ state: 'visible' });
    await this.replaceLegsCancelButton.click();
    await this.replaceLegsModal.waitFor({ state: 'hidden' });
  }

  async addLeg({ action, expiry, strike, type, lots, entryPrice, targetPrice, stopLossPrice, trailingSl, targetPct, stopLossPct, maxLoss } = {}) {
    await this.addLegButton.click();
    const legCount = await this.legRows.count();
    const lastLegIndex = legCount - 1;

    if (action) {
      await this.getLegAction(lastLegIndex).selectOption(action);
    }
    if (expiry) {
      await this.getLegExpiry(lastLegIndex).selectOption(expiry);
    }
    if (strike) {
      await this.getLegStrike(lastLegIndex).selectOption(strike.toString());
    }
    if (type) {
      await this.getLegType(lastLegIndex).selectOption(type);
    }
    if (lots) {
      await this.getLegLots(lastLegIndex).fill(lots.toString());
    }
    if (entryPrice) {
      await this.getLegEntry(lastLegIndex).fill(entryPrice.toString());
    }
    if (targetPrice) {
      await this.getLegTargetPrice(lastLegIndex).fill(targetPrice.toString());
    }
    if (stopLossPrice) {
      await this.getLegStopLossPrice(lastLegIndex).fill(stopLossPrice.toString());
    }
    if (trailingSl !== undefined) {
      const checkbox = this.getLegTrailingSl(lastLegIndex);
      const isChecked = await checkbox.isChecked();
      if (trailingSl !== isChecked) {
        await checkbox.click();
      }
    }
    if (targetPct) {
      await this.getLegTargetPct(lastLegIndex).fill(targetPct.toString());
    }
    if (stopLossPct) {
      await this.getLegStopLossPct(lastLegIndex).fill(stopLossPct.toString());
    }
    if (maxLoss) {
      await this.getLegMaxLoss(lastLegIndex).fill(maxLoss.toString());
    }

    return lastLegIndex;
  }

  async selectLeg(index) {
    await this.getLegCheckbox(index).check();
  }

  async deselectLeg(index) {
    await this.getLegCheckbox(index).uncheck();
  }

  async selectAllLegs() {
    await this.selectAllCheckbox.check();
  }

  async deselectAllLegs() {
    await this.selectAllCheckbox.uncheck();
  }

  async deleteSelectedLegs() {
    await this.deleteSelectedButton.click();
  }

  async removeLeg(index) {
    await this.getLegDeleteButton(index).click();
  }

  async addCondition({ variable, operator, value }) {
    await this.addConditionButton.click();
    const condCount = await this.conditionRows.count();
    const lastCondIndex = condCount - 1;

    if (variable) {
      await this.getByTestId(`autopilot-condition-variable-${lastCondIndex}`).selectOption(variable);
    }
    if (operator) {
      await this.getByTestId(`autopilot-condition-operator-${lastCondIndex}`).selectOption(operator);
    }
    if (value) {
      await this.getByTestId(`autopilot-condition-value-${lastCondIndex}`).fill(value);
    }
  }

  async setConditionLogic(logic) {
    // Vue uses a <select> element, not separate buttons
    await this.conditionLogicToggle.selectOption(logic.toUpperCase());
  }

  async setRiskSettings({ maxLoss, maxProfit, trailingStop }) {
    if (maxLoss) await this.maxLossInput.fill(maxLoss.toString());
    if (maxProfit) await this.maxProfitInput.fill(maxProfit.toString());
    if (trailingStop) {
      await this.trailingStopToggle.click();
      await this.trailingStopValue.fill(trailingStop.toString());
    }
  }

  async setSchedule({ activationMode, startTime, endTime }) {
    if (activationMode) {
      await this.activationModeSelect.selectOption(activationMode);
      // Wait for time inputs to appear if switching to 'scheduled' mode
      if (activationMode === 'scheduled') {
        await this.startTimeInput.waitFor({ state: 'visible' });
      }
    }
    if (startTime) await this.startTimeInput.fill(startTime);
    if (endTime) await this.endTimeInput.fill(endTime);
  }

  async goToNextStep() {
    await this.nextButton.click();
  }

  async goToPreviousStep() {
    await this.previousButton.click();
  }

  async saveStrategy() {
    await this.saveButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async activateStrategy() {
    await this.activateButton.click();
  }

  async cancelBuilder() {
    await this.cancelButton.click();
    await this.page.waitForURL('**/autopilot');
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getCurrentStep() {
    const text = await this.stepIndicator.textContent();
    return parseInt(text.match(/\d+/)[0], 10);
  }

  async getLegCount() {
    return await this.legRows.count();
  }

  /**
   * Get CMP value for a leg as a number
   * @param {number} index - Leg index
   * @returns {number|null} - CMP value or null if not available
   */
  async getLegCmpValue(index) {
    const cmpCell = this.getLegCmp(index);
    const text = await cmpCell.textContent();
    const cleanText = text.replace(/[^\d.-]/g, '');
    const value = parseFloat(cleanText);
    return isNaN(value) ? null : value;
  }

  /**
   * Check if CMP is showing a valid live price (not "-", "0", or empty)
   * @param {number} index - Leg index
   * @returns {boolean} - True if CMP shows valid price
   */
  async isLegCmpValid(index) {
    const value = await this.getLegCmpValue(index);
    return value !== null && value > 0;
  }

  /**
   * Validate that all legs have valid CMP values (live data is flowing)
   * Throws an error if any leg has invalid CMP
   */
  async validateAllLegsCmp() {
    const legCount = await this.getLegCount();
    const invalidLegs = [];

    for (let i = 0; i < legCount; i++) {
      const isValid = await this.isLegCmpValid(i);
      if (!isValid) {
        const cmpText = await this.getLegCmp(i).textContent();
        invalidLegs.push({ index: i, value: cmpText });
      }
    }

    if (invalidLegs.length > 0) {
      const details = invalidLegs.map(l => `Leg ${l.index}: "${l.value}"`).join(', ');
      throw new Error(
        `Kite live data not available. Invalid CMP values found: ${details}. ` +
        `Ensure Kite broker token is valid and market is open.`
      );
    }

    return true;
  }

  async getConditionCount() {
    return await this.conditionRows.count();
  }

  async getValidationErrorCount() {
    return await this.validationErrors.count();
  }

  async hasValidationError() {
    return (await this.getValidationErrorCount()) > 0;
  }
}


/**
 * AutoPilot Strategy Detail Page Object
 *
 * Page object for AutoPilot Strategy Detail view.
 * URL: /autopilot/strategies/:id
 */
export class AutoPilotStrategyDetailPage extends BasePage {
  constructor(page, strategyId = null) {
    super(page);
    this.strategyId = strategyId;
    this.url = strategyId ? `/autopilot/strategies/${strategyId}` : '/autopilot/strategies';
  }

  // ===========================================================================
  // LOCATORS - Header
  // ===========================================================================

  get strategyName() {
    return this.getByTestId('autopilot-detail-name');
  }

  get strategyStatus() {
    return this.getByTestId('autopilot-detail-status');
  }

  get editButton() {
    return this.getByTestId('autopilot-detail-edit');
  }

  get deleteButton() {
    return this.getByTestId('autopilot-detail-delete');
  }

  get backButton() {
    return this.getByTestId('autopilot-detail-back');
  }

  // ===========================================================================
  // LOCATORS - Control Actions
  // ===========================================================================

  get activateButton() {
    return this.getByTestId('autopilot-detail-activate');
  }

  get pauseButton() {
    return this.getByTestId('autopilot-detail-pause');
  }

  get resumeButton() {
    return this.getByTestId('autopilot-detail-resume');
  }

  get exitButton() {
    return this.getByTestId('autopilot-detail-exit');
  }

  // ===========================================================================
  // LOCATORS - Condition Progress
  // ===========================================================================

  get conditionProgress() {
    return this.getByTestId('autopilot-detail-condition-progress');
  }

  get conditionItems() {
    return this.page.locator('[data-testid^="autopilot-condition-item-"]');
  }

  // ===========================================================================
  // LOCATORS - P&L Section
  // ===========================================================================

  get pnlSection() {
    return this.getByTestId('autopilot-strategy-pnl');
  }

  // Alias for backwards compatibility
  get realizedPnl() {
    return this.pnlSection;
  }

  get unrealizedPnl() {
    return this.pnlSection;
  }

  get totalPnl() {
    return this.pnlSection;
  }

  // ===========================================================================
  // LOCATORS - Strategy Page Sections
  // Note: Vue shows configuration, legs, conditions - not separate orders/logs
  // ===========================================================================

  get strategyDetail() {
    return this.getByTestId('autopilot-strategy-detail');
  }

  // Alias for backwards compatibility - Vue doesn't have separate orders section
  get ordersSection() {
    return this.strategyDetail;
  }

  get orderRows() {
    return this.page.locator('[data-testid^="autopilot-order-row-"]');
  }

  // Alias for backwards compatibility - Vue doesn't have separate logs section
  get logsSection() {
    return this.strategyDetail;
  }

  get logItems() {
    return this.page.locator('[data-testid^="autopilot-log-item-"]');
  }

  // ===========================================================================
  // LOCATORS - Modals
  // ===========================================================================

  get deleteModal() {
    return this.getByTestId('autopilot-delete-modal');
  }

  get deleteConfirmButton() {
    return this.getByTestId('autopilot-delete-confirm');
  }

  get exitModal() {
    return this.getByTestId('autopilot-exit-modal');
  }

  get exitConfirmButton() {
    return this.getByTestId('autopilot-exit-confirm');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async navigateToStrategy(id) {
    await this.page.goto(`/autopilot/strategies/${id}`);
    await this.page.waitForLoadState('networkidle');
  }

  async waitForStrategyLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-detail-name"]', {
      timeout: 10000
    });
  }

  async activateStrategy() {
    await this.activateButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async pauseStrategy() {
    await this.pauseButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async resumeStrategy() {
    await this.resumeButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async exitStrategy() {
    await this.exitButton.click();
    await this.exitModal.waitFor({ state: 'visible' });
    await this.exitConfirmButton.click();
    await this.exitModal.waitFor({ state: 'hidden' });
  }

  async editStrategy() {
    await this.editButton.click();
    await this.page.waitForURL(`**/autopilot/strategies/${this.strategyId}/edit`);
  }

  async deleteStrategy() {
    await this.deleteButton.click();
    await this.deleteModal.waitFor({ state: 'visible' });
    await this.deleteConfirmButton.click();
    await this.deleteModal.waitFor({ state: 'hidden' });
  }

  async goBack() {
    await this.backButton.click();
    await this.page.waitForURL('**/autopilot');
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getStatus() {
    return await this.strategyStatus.textContent();
  }

  async getTotalPnlValue() {
    const text = await this.totalPnl.textContent();
    return parseFloat(text.replace(/[^\d.-]/g, ''));
  }

  async getOrderCount() {
    return await this.orderRows.count();
  }

  async getLogCount() {
    return await this.logItems.count();
  }
}


/**
 * AutoPilot Settings Page Object
 *
 * Page object for AutoPilot Settings view.
 * URL: /autopilot/settings
 *
 * Vue testids from SettingsView.vue:
 * - autopilot-settings (page container)
 * - autopilot-settings-back, autopilot-settings-reset, autopilot-settings-save
 * - autopilot-settings-risk (risk limits section)
 * - autopilot-settings-max-daily-loss, autopilot-settings-strategy-loss
 * - autopilot-settings-max-capital, autopilot-settings-max-active
 * - autopilot-settings-time (time restrictions section)
 * - autopilot-settings-cooldown (cooldown section)
 * - autopilot-settings-features (features section)
 * - autopilot-settings-paper-trading
 * - autopilot-settings-error
 */
export class AutoPilotSettingsPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/settings';
  }

  // ===========================================================================
  // LOCATORS - Page Structure
  // ===========================================================================

  get settingsPage() {
    return this.getByTestId('autopilot-settings');
  }

  // ===========================================================================
  // LOCATORS - Risk Limits
  // ===========================================================================

  get riskSection() {
    return this.getByTestId('autopilot-settings-risk');
  }

  get maxDailyLossInput() {
    return this.getByTestId('autopilot-settings-max-daily-loss');
  }

  get perStrategyLossInput() {
    return this.getByTestId('autopilot-settings-strategy-loss');
  }

  get maxActiveStrategiesInput() {
    return this.getByTestId('autopilot-settings-max-active');
  }

  get maxCapitalInput() {
    return this.getByTestId('autopilot-settings-max-capital');
  }

  // Alias for backwards compatibility
  get maxCapitalPerStrategyInput() {
    return this.maxCapitalInput;
  }

  // ===========================================================================
  // LOCATORS - Time Restrictions
  // ===========================================================================

  get timeSection() {
    return this.getByTestId('autopilot-settings-time');
  }

  // ===========================================================================
  // LOCATORS - Cooldown Settings
  // ===========================================================================

  get cooldownSection() {
    return this.getByTestId('autopilot-settings-cooldown');
  }

  // ===========================================================================
  // LOCATORS - Features
  // ===========================================================================

  get featuresSection() {
    return this.getByTestId('autopilot-settings-features');
  }

  get paperTradingToggle() {
    return this.getByTestId('autopilot-settings-paper-trading');
  }

  // Aliases for backwards compatibility (Vue doesn't have separate notification toggles)
  get notificationsSection() {
    return this.featuresSection;
  }

  get emailNotificationsToggle() {
    return this.paperTradingToggle; // Fallback - Vue doesn't have email toggle
  }

  get pushNotificationsToggle() {
    return this.paperTradingToggle; // Fallback - Vue doesn't have push toggle
  }

  // ===========================================================================
  // LOCATORS - Actions
  // ===========================================================================

  get saveButton() {
    return this.getByTestId('autopilot-settings-save');
  }

  get resetButton() {
    return this.getByTestId('autopilot-settings-reset');
  }

  get backButton() {
    return this.getByTestId('autopilot-settings-back');
  }

  // ===========================================================================
  // LOCATORS - Feedback
  // ===========================================================================

  get successMessage() {
    // Vue shows success via button state change, not separate element
    return this.saveButton;
  }

  get errorMessage() {
    return this.getByTestId('autopilot-settings-error');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-settings"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async setMaxDailyLoss(value) {
    await this.maxDailyLossInput.fill(value.toString());
  }

  async setMaxActiveStrategies(value) {
    await this.maxActiveStrategiesInput.fill(value.toString());
  }

  async setMaxCapital(value) {
    await this.maxCapitalInput.fill(value.toString());
  }

  async togglePaperTrading() {
    await this.paperTradingToggle.click();
  }

  // Aliases for backwards compatibility
  async toggleEmailNotifications() {
    // Vue doesn't have email toggle - use paper trading as substitute
    await this.paperTradingToggle.click();
  }

  async togglePushNotifications() {
    // Vue doesn't have push toggle - use paper trading as substitute
    await this.paperTradingToggle.click();
  }

  async saveSettings() {
    await this.saveButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async resetSettings() {
    await this.resetButton.click();
  }

  async goBack() {
    await this.backButton.click();
    await this.page.waitForURL('**/autopilot');
  }
}


/**
 * AutoPilot Templates Page Object
 *
 * Page object for AutoPilot Template Library view.
 * URL: /autopilot/templates
 */
export class AutoPilotTemplatesPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/templates';
  }

  // ===========================================================================
  // LOCATORS - Page Structure
  // ===========================================================================

  get templatesPage() {
    return this.getByTestId('autopilot-templates-page');
  }

  get templatesHeader() {
    return this.getByTestId('autopilot-templates-header');
  }

  get categoriesSection() {
    return this.getByTestId('autopilot-templates-categories');
  }

  get categoryCards() {
    return this.page.locator('[data-testid^="autopilot-templates-category-"]');
  }

  getCategoryCard(category) {
    return this.getByTestId(`autopilot-templates-category-${category}`);
  }

  // ===========================================================================
  // LOCATORS - Template Cards
  // ===========================================================================

  get templateCards() {
    return this.page.locator('[data-testid^="autopilot-template-card-"]');
  }

  getTemplateCard(id) {
    return this.getByTestId(`autopilot-template-card-${id}`);
  }

  getTemplateRating(id) {
    return this.getByTestId(`autopilot-template-rating-${id}`);
  }

  getTemplateDeployButton(id) {
    return this.getByTestId(`autopilot-template-deploy-${id}`);
  }

  // ===========================================================================
  // LOCATORS - Search & Filters
  // ===========================================================================

  get searchInput() {
    return this.getByTestId('autopilot-templates-search');
  }

  get searchClearButton() {
    return this.getByTestId('autopilot-templates-search-clear');
  }

  get categoryFilter() {
    return this.getByTestId('autopilot-templates-category-filter');
  }

  get riskFilter() {
    return this.getByTestId('autopilot-templates-risk-filter');
  }

  // ===========================================================================
  // LOCATORS - Details Modal
  // ===========================================================================

  get detailsModal() {
    return this.getByTestId('autopilot-template-details-modal');
  }

  get detailsModalClose() {
    return this.getByTestId('autopilot-template-details-close');
  }

  get detailsModalDeploy() {
    return this.getByTestId('autopilot-template-details-deploy');
  }

  // ===========================================================================
  // LOCATORS - Deploy Modal
  // ===========================================================================

  get deployModal() {
    return this.getByTestId('autopilot-template-deploy-modal');
  }

  get deployNameInput() {
    return this.getByTestId('autopilot-template-deploy-name');
  }

  get deployLotsInput() {
    return this.getByTestId('autopilot-template-deploy-lots');
  }

  get deployActivateCheckbox() {
    return this.getByTestId('autopilot-template-deploy-activate');
  }

  get deployConfirmButton() {
    return this.getByTestId('autopilot-template-deploy-confirm');
  }

  get detailsModalRate() {
    return this.getByTestId('autopilot-template-details-rate');
  }

  // ===========================================================================
  // LOCATORS - Rating
  // ===========================================================================

  get ratingModal() {
    return this.getByTestId('autopilot-template-rating-modal');
  }

  get ratingStars() {
    return this.page.locator('[data-testid^="autopilot-template-rating-star-"]');
  }

  getRatingStar(star) {
    return this.getByTestId(`autopilot-template-rating-star-${star}`);
  }

  get ratingSubmit() {
    return this.getByTestId('autopilot-template-rating-submit');
  }

  // ===========================================================================
  // LOCATORS - Pagination & Empty State
  // ===========================================================================

  get pagination() {
    return this.getByTestId('autopilot-templates-pagination');
  }

  get emptyState() {
    return this.getByTestId('autopilot-templates-empty');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-templates-page"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async searchTemplates(query) {
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(500);
    await this.page.waitForLoadState('networkidle');
  }

  async clearSearch() {
    await this.searchClearButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByCategory(category) {
    await this.categoryFilter.selectOption(category);
    await this.page.waitForLoadState('networkidle');
  }

  async filterByRisk(risk) {
    await this.riskFilter.selectOption(risk);
    await this.page.waitForLoadState('networkidle');
  }

  async clickTemplate(id) {
    await this.getTemplateCard(id).click();
    await this.detailsModal.waitFor({ state: 'visible' });
  }

  async closeDetailsModal() {
    await this.detailsModalClose.click();
    await this.detailsModal.waitFor({ state: 'hidden' });
  }

  async deployTemplate(id) {
    // Click deploy button to open modal
    await this.getTemplateDeployButton(id).click();
    // Wait for deploy modal to appear
    await this.deployModal.waitFor({ state: 'visible' });
    // Click confirm button in modal
    await this.deployConfirmButton.click();
    // Wait for navigation to strategy detail page
    await this.page.waitForURL('**/autopilot/strategies/**', { timeout: 10000 });
  }

  async rateTemplate(stars) {
    await this.detailsModalRate.click();
    await this.ratingModal.waitFor({ state: 'visible' });
    await this.getRatingStar(stars).click();
    await this.ratingSubmit.click();
    await this.ratingModal.waitFor({ state: 'hidden' });
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getTemplateCount() {
    return await this.templateCards.count();
  }

  async getCategoryCount() {
    return await this.categoryCards.count();
  }
}


/**
 * AutoPilot Journal Page Object
 *
 * Page object for AutoPilot Trade Journal view.
 * URL: /autopilot/journal
 */
export class AutoPilotJournalPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/journal';
  }

  // ===========================================================================
  // LOCATORS - Page Structure
  // ===========================================================================

  get journalPage() {
    return this.getByTestId('autopilot-journal-page');
  }

  get journalHeader() {
    return this.getByTestId('autopilot-journal-header');
  }

  get statsSection() {
    return this.getByTestId('autopilot-journal-stats');
  }

  get totalTradesCard() {
    return this.getByTestId('autopilot-journal-total-trades');
  }

  get winRateCard() {
    return this.getByTestId('autopilot-journal-win-rate');
  }

  // ===========================================================================
  // LOCATORS - Trades Table
  // ===========================================================================

  get tradesTable() {
    return this.getByTestId('autopilot-journal-trades-table');
  }

  get tradeRows() {
    return this.page.locator('[data-testid^="autopilot-journal-trade-row-"]');
  }

  getTradeRow(id) {
    return this.getByTestId(`autopilot-journal-trade-row-${id}`);
  }

  // ===========================================================================
  // LOCATORS - Filters
  // ===========================================================================

  get dateFilter() {
    return this.getByTestId('autopilot-journal-date-filter');
  }

  get date7Days() {
    return this.getByTestId('autopilot-journal-date-7d');
  }

  get date30Days() {
    return this.getByTestId('autopilot-journal-date-30d');
  }

  get dateCustom() {
    return this.getByTestId('autopilot-journal-date-custom');
  }

  get dateStart() {
    return this.getByTestId('autopilot-journal-start-date');
  }

  get dateEnd() {
    return this.getByTestId('autopilot-journal-end-date');
  }

  get dateApply() {
    return this.getByTestId('autopilot-journal-date-apply');
  }

  get underlyingFilter() {
    return this.getByTestId('autopilot-journal-underlying-filter');
  }

  // Alias for backwards compatibility
  get strategyFilter() {
    return this.underlyingFilter;
  }

  get outcomeFilter() {
    return this.getByTestId('autopilot-journal-outcome-filter');
  }

  // Exit reason filter aliases
  get outcomeProfit() {
    return this.outcomeFilter;
  }

  get outcomeLoss() {
    return this.outcomeFilter;
  }

  get clearFiltersButton() {
    return this.getByTestId('autopilot-journal-clear-filters');
  }

  get filtersSection() {
    return this.getByTestId('autopilot-journal-filters');
  }

  // ===========================================================================
  // LOCATORS - Trade Details
  // ===========================================================================

  get tradeDetails() {
    return this.getByTestId('autopilot-journal-trade-details');
  }

  get tradePnlChart() {
    return this.getByTestId('autopilot-journal-trade-pnl-chart');
  }

  get tradeEntryPrice() {
    return this.getByTestId('autopilot-journal-trade-entry-price');
  }

  get tradeExitPrice() {
    return this.getByTestId('autopilot-journal-trade-exit-price');
  }

  get tradeNotes() {
    return this.getByTestId('autopilot-journal-trade-notes');
  }

  get tradeSaveNotes() {
    return this.getByTestId('autopilot-journal-trade-save-notes');
  }

  // ===========================================================================
  // LOCATORS - Export & Charts
  // ===========================================================================

  get exportButton() {
    return this.getByTestId('autopilot-journal-export-btn');
  }

  get exportModal() {
    return this.getByTestId('autopilot-journal-export-modal');
  }

  get exportCsv() {
    // Export format is selected via radio button, return the confirm button
    return this.getByTestId('autopilot-journal-export-confirm');
  }

  get cumulativeChart() {
    return this.getByTestId('autopilot-journal-cumulative-chart');
  }

  // ===========================================================================
  // LOCATORS - Pagination & Empty State
  // ===========================================================================

  get pagination() {
    return this.getByTestId('autopilot-journal-pagination');
  }

  get emptyState() {
    return this.getByTestId('autopilot-journal-empty-state');
  }

  // Alias for backwards compatibility
  get journalEmpty() {
    return this.emptyState;
  }

  get sortDate() {
    return this.getByTestId('autopilot-journal-sort-date');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-journal-page"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async filterByLast7Days() {
    // Date filter uses direct date inputs
    const today = new Date();
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    await this.dateStart.fill(sevenDaysAgo.toISOString().split('T')[0]);
    await this.dateEnd.fill(today.toISOString().split('T')[0]);
    await this.page.waitForLoadState('networkidle');
  }

  async filterByLast30Days() {
    // Date filter uses direct date inputs
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    await this.dateStart.fill(thirtyDaysAgo.toISOString().split('T')[0]);
    await this.dateEnd.fill(today.toISOString().split('T')[0]);
    await this.page.waitForLoadState('networkidle');
  }

  async filterByCustomDates(startDate, endDate) {
    await this.dateStart.fill(startDate);
    await this.dateEnd.fill(endDate);
    await this.page.waitForLoadState('networkidle');
  }

  async filterByStrategy(strategy) {
    await this.strategyFilter.click();
    await this.getByTestId(`autopilot-journal-strategy-option-${strategy}`).click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByOutcome(outcome) {
    // The outcome filter is a select dropdown for exit reasons
    // Map outcome to actual exit reason values
    const exitReasonMap = {
      'profit': 'target_hit',
      'loss': 'stop_loss',
      'target_hit': 'target_hit',
      'stop_loss': 'stop_loss',
      'trailing_stop': 'trailing_stop',
      'expiry': 'expiry',
      'manual': 'manual',
      'kill_switch': 'kill_switch'
    };
    const value = exitReasonMap[outcome] || outcome;
    await this.outcomeFilter.selectOption(value);
    await this.page.waitForLoadState('networkidle');
  }

  async clearAllFilters() {
    await this.clearFiltersButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async openTradeDetails(id) {
    await this.getTradeRow(id).click();
    await this.tradeDetails.waitFor({ state: 'visible' });
  }

  async addTradeNotes(notes) {
    await this.tradeNotes.fill(notes);
    await this.tradeSaveNotes.click();
    await this.page.waitForLoadState('networkidle');
  }

  async exportToCsv() {
    await this.exportButton.click();
    await this.exportModal.waitFor({ state: 'visible' });
    await this.exportCsv.click();
  }

  async sortByDate() {
    await this.sortDate.click();
    await this.page.waitForLoadState('networkidle');
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getTradeCount() {
    return await this.tradeRows.count();
  }
}


/**
 * AutoPilot Analytics Page Object
 *
 * Page object for AutoPilot Analytics Dashboard view.
 * URL: /autopilot/analytics
 */
export class AutoPilotAnalyticsPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/analytics';
  }

  // ===========================================================================
  // LOCATORS - Page Structure
  // ===========================================================================

  get analyticsPage() {
    return this.getByTestId('autopilot-analytics-page');
  }

  get analyticsHeader() {
    return this.getByTestId('autopilot-analytics-header');
  }

  get summarySection() {
    return this.getByTestId('autopilot-analytics-summary');
  }

  get totalPnl() {
    return this.getByTestId('autopilot-analytics-total-pnl');
  }

  get winRate() {
    return this.getByTestId('autopilot-analytics-win-rate');
  }

  get avgProfit() {
    return this.getByTestId('autopilot-analytics-avg-profit');
  }

  // ===========================================================================
  // LOCATORS - Charts
  // ===========================================================================

  get dailyPnlChart() {
    return this.getByTestId('autopilot-analytics-daily-pnl-chart');
  }

  get cumulativeChart() {
    return this.getByTestId('autopilot-analytics-cumulative-chart');
  }

  get weekdayChart() {
    return this.getByTestId('autopilot-analytics-weekday-chart');
  }

  get distributionChart() {
    return this.getByTestId('autopilot-analytics-distribution-chart');
  }

  // ===========================================================================
  // LOCATORS - Breakdown & Metrics
  // ===========================================================================

  get strategyBreakdown() {
    return this.getByTestId('autopilot-analytics-strategy-breakdown');
  }

  get strategyRows() {
    return this.page.locator('[data-testid^="autopilot-analytics-strategy-row-"]');
  }

  getStrategyRow(id) {
    return this.getByTestId(`autopilot-analytics-strategy-row-${id}`);
  }

  get strategyDetails() {
    return this.getByTestId('autopilot-analytics-strategy-details');
  }

  get drawdownSection() {
    return this.getByTestId('autopilot-analytics-drawdown');
  }

  get maxDrawdown() {
    return this.getByTestId('autopilot-analytics-max-drawdown');
  }

  get riskMetrics() {
    return this.getByTestId('autopilot-analytics-risk-metrics');
  }

  get sharpeRatio() {
    return this.getByTestId('autopilot-analytics-sharpe-ratio');
  }

  // ===========================================================================
  // LOCATORS - Filters
  // ===========================================================================

  get dateRange() {
    return this.getByTestId('autopilot-analytics-date-range');
  }

  get range7Days() {
    return this.getByTestId('autopilot-analytics-range-7d');
  }

  get range30Days() {
    return this.getByTestId('autopilot-analytics-range-30d');
  }

  get range90Days() {
    return this.getByTestId('autopilot-analytics-range-90d');
  }

  get rangeCustom() {
    return this.getByTestId('autopilot-analytics-range-custom');
  }

  get startDate() {
    return this.getByTestId('autopilot-analytics-start-date');
  }

  get endDate() {
    return this.getByTestId('autopilot-analytics-end-date');
  }

  get applyDates() {
    return this.getByTestId('autopilot-analytics-apply-dates');
  }

  get strategyFilter() {
    return this.getByTestId('autopilot-analytics-strategy-filter');
  }

  // ===========================================================================
  // LOCATORS - Time Toggle & Actions
  // ===========================================================================

  get timeToggle() {
    return this.getByTestId('autopilot-analytics-time-toggle');
  }

  get timeDaily() {
    return this.getByTestId('autopilot-analytics-time-daily');
  }

  get timeWeekly() {
    return this.getByTestId('autopilot-analytics-time-weekly');
  }

  get timeMonthly() {
    return this.getByTestId('autopilot-analytics-time-monthly');
  }

  get refreshButton() {
    return this.getByTestId('autopilot-analytics-refresh-btn');
  }

  get exportButton() {
    return this.getByTestId('autopilot-analytics-export-btn');
  }

  get exportModal() {
    return this.getByTestId('autopilot-analytics-export-modal');
  }

  get noDataState() {
    return this.getByTestId('autopilot-analytics-no-data');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-analytics-page"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async filterByLast7Days() {
    // Vue uses preset buttons directly, not a dropdown
    await this.range7Days.click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByLast30Days() {
    // Vue uses preset buttons directly, not a dropdown
    await this.range30Days.click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByLast90Days() {
    // Vue uses preset buttons directly, not a dropdown
    await this.range90Days.click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByCustomDates(start, end) {
    // Click custom preset first
    await this.rangeCustom.click();
    await this.page.waitForTimeout(300); // Wait for custom inputs to appear
    await this.startDate.fill(start);
    await this.endDate.fill(end);
    // No apply button needed - Vue watches date changes
    await this.page.waitForLoadState('networkidle');
  }

  async filterByStrategy(strategy) {
    await this.strategyFilter.click();
    await this.getByTestId(`autopilot-analytics-strategy-option-${strategy}`).click();
    await this.page.waitForLoadState('networkidle');
  }

  async setTimeDaily() {
    await this.timeToggle.click();
    await this.timeDaily.click();
    await this.page.waitForLoadState('networkidle');
  }

  async setTimeWeekly() {
    await this.timeToggle.click();
    await this.timeWeekly.click();
    await this.page.waitForLoadState('networkidle');
  }

  async setTimeMonthly() {
    await this.timeToggle.click();
    await this.timeMonthly.click();
    await this.page.waitForLoadState('networkidle');
  }

  async openStrategyDetails(id) {
    await this.getStrategyRow(id).click();
    await this.strategyDetails.waitFor({ state: 'visible' });
  }

  async refreshData() {
    await this.refreshButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async openExportModal() {
    await this.exportButton.click();
    await this.exportModal.waitFor({ state: 'visible' });
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getStrategyCount() {
    return await this.strategyRows.count();
  }
}


/**
 * AutoPilot Reports Page Object
 *
 * Page object for AutoPilot Reports view.
 * URL: /autopilot/reports
 */
export class AutoPilotReportsPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/reports';
  }

  // ===========================================================================
  // LOCATORS - Page Structure
  // ===========================================================================

  get reportsPage() {
    return this.getByTestId('autopilot-reports-page');
  }

  get reportsHeader() {
    return this.getByTestId('autopilot-reports-header');
  }

  get reportsList() {
    return this.getByTestId('autopilot-reports-list');
  }

  get reportRows() {
    return this.page.locator('[data-testid^="autopilot-report-row-"]');
  }

  getReportRow(id) {
    return this.getByTestId(`autopilot-report-row-${id}`);
  }

  getReportDelete(id) {
    return this.getByTestId(`autopilot-report-delete-${id}`);
  }

  // ===========================================================================
  // LOCATORS - Generate Report
  // ===========================================================================

  get generateButton() {
    return this.getByTestId('autopilot-reports-generate-btn');
  }

  get generateModal() {
    return this.getByTestId('autopilot-reports-generate-modal');
  }

  get nameInput() {
    return this.getByTestId('autopilot-reports-name-input');
  }

  get typeSelect() {
    return this.getByTestId('autopilot-reports-type-select');
  }

  get typePerformance() {
    return this.getByTestId('autopilot-reports-type-performance');
  }

  get startDate() {
    return this.getByTestId('autopilot-reports-start-date');
  }

  get endDate() {
    return this.getByTestId('autopilot-reports-end-date');
  }

  get submitButton() {
    return this.getByTestId('autopilot-reports-submit-btn');
  }

  get cancelButton() {
    return this.getByTestId('autopilot-reports-cancel-btn');
  }

  get validationError() {
    return this.getByTestId('autopilot-reports-validation-error');
  }

  // ===========================================================================
  // LOCATORS - Report Details
  // ===========================================================================

  get reportDetailsPage() {
    return this.getByTestId('autopilot-report-details-page');
  }

  get summarySection() {
    return this.getByTestId('autopilot-report-summary-section');
  }

  get downloadPdf() {
    return this.getByTestId('autopilot-report-download-pdf');
  }

  get downloadExcel() {
    return this.getByTestId('autopilot-report-download-excel');
  }

  // ===========================================================================
  // LOCATORS - Delete Modal
  // ===========================================================================

  get deleteConfirm() {
    return this.getByTestId('autopilot-report-delete-confirm');
  }

  // ===========================================================================
  // LOCATORS - Tax Summary
  // ===========================================================================

  get taxTab() {
    return this.getByTestId('autopilot-reports-tax-tab');
  }

  get taxSummary() {
    return this.getByTestId('autopilot-reports-tax-summary');
  }

  get generateTaxButton() {
    return this.getByTestId('autopilot-reports-generate-tax');
  }

  get fySelect() {
    return this.getByTestId('autopilot-reports-fy-select');
  }

  get taxSubmit() {
    return this.getByTestId('autopilot-reports-generate-tax');
  }

  // ===========================================================================
  // LOCATORS - Filters & Pagination
  // ===========================================================================

  get typeFilter() {
    return this.getByTestId('autopilot-reports-type-filter');
  }

  get filterPerformance() {
    return this.getByTestId('autopilot-reports-filter-performance');
  }

  get sortDate() {
    return this.getByTestId('autopilot-reports-sort-date');
  }

  get pagination() {
    return this.getByTestId('autopilot-reports-pagination');
  }

  get emptyState() {
    return this.getByTestId('autopilot-reports-empty');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-reports-page"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async openGenerateModal() {
    await this.generateButton.click();
    await this.generateModal.waitFor({ state: 'visible' });
  }

  async generateReport({ name, type, startDate, endDate }) {
    await this.openGenerateModal();
    if (name) await this.nameInput.fill(name);
    if (type) {
      // Type select is a dropdown, use selectOption
      await this.typeSelect.selectOption(type);
    }
    if (startDate) await this.startDate.fill(startDate);
    if (endDate) await this.endDate.fill(endDate);
    await this.submitButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async cancelGenerate() {
    await this.cancelButton.click();
    await this.generateModal.waitFor({ state: 'hidden' });
  }

  async openReport(id) {
    await this.getReportRow(id).click();
    await this.reportDetailsPage.waitFor({ state: 'visible' });
  }

  async deleteReport(id) {
    await this.getReportDelete(id).click();
    await this.deleteConfirm.click();
    await this.page.waitForLoadState('networkidle');
  }

  async downloadAsPdf() {
    await this.downloadPdf.click();
  }

  async downloadAsExcel() {
    await this.downloadExcel.click();
  }

  async openTaxSummary() {
    await this.taxTab.click();
    await this.page.waitForLoadState('networkidle');
  }

  async generateTaxReport(financialYear) {
    await this.generateTaxButton.click();
    await this.fySelect.selectOption(financialYear);
    await this.taxSubmit.click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByType(type) {
    // Vue uses a <select> dropdown for type filtering
    // Map test types to Vue report types
    const typeMap = {
      'performance': 'strategy',
      'strategy': 'strategy',
      'pnl': 'pnl',
      'monthly': 'monthly',
      'tax': 'tax'
    };
    const vueType = typeMap[type] || type;
    await this.typeFilter.selectOption(vueType);
    await this.page.waitForLoadState('networkidle');
  }

  async sortByDate() {
    await this.sortDate.click();
    await this.page.waitForLoadState('networkidle');
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getReportCount() {
    return await this.reportRows.count();
  }
}


/**
 * AutoPilot Backtest Page Object
 *
 * Page object for AutoPilot Backtest view.
 * URL: /autopilot/backtest
 */
export class AutoPilotBacktestPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/backtests';
  }

  // ===========================================================================
  // LOCATORS - Page Structure
  // ===========================================================================

  get backtestPage() {
    return this.getByTestId('autopilot-backtest-page');
  }

  get backtestHeader() {
    return this.getByTestId('autopilot-backtest-header');
  }

  get backtestList() {
    return this.getByTestId('autopilot-backtest-list');
  }

  get backtestRows() {
    return this.page.locator('[data-testid^="autopilot-backtest-row-"]');
  }

  getBacktestRow(id) {
    return this.getByTestId(`autopilot-backtest-row-${id}`);
  }

  getBacktestDelete(id) {
    return this.getByTestId(`autopilot-backtest-delete-${id}`);
  }

  // ===========================================================================
  // LOCATORS - New Backtest
  // ===========================================================================

  get newButton() {
    return this.getByTestId('autopilot-backtest-new-btn');
  }

  get configModal() {
    return this.getByTestId('autopilot-backtest-config-modal');
  }

  get strategySelect() {
    return this.getByTestId('autopilot-backtest-strategy-select');
  }

  get startDate() {
    return this.getByTestId('autopilot-backtest-start-date');
  }

  get endDate() {
    return this.getByTestId('autopilot-backtest-end-date');
  }

  get capitalInput() {
    return this.getByTestId('autopilot-backtest-capital');
  }

  get lotsInput() {
    return this.getByTestId('backtest-lots');
  }

  get slippageInput() {
    return this.getByTestId('autopilot-backtest-slippage');
  }

  get nameInput() {
    return this.getByTestId('autopilot-backtest-name-input');
  }

  get runButton() {
    return this.getByTestId('autopilot-backtest-run-btn');
  }

  get cancelButton() {
    return this.getByTestId('autopilot-backtest-cancel-btn');
  }

  get validationError() {
    return this.getByTestId('autopilot-backtest-validation-error');
  }

  // ===========================================================================
  // LOCATORS - Results
  // ===========================================================================

  get resultsPage() {
    return this.getByTestId('autopilot-backtest-results-page');
  }

  get resultsSummary() {
    return this.getByTestId('autopilot-backtest-results-summary');
  }

  get totalPnl() {
    return this.getByTestId('autopilot-backtest-total-pnl');
  }

  get winRate() {
    return this.getByTestId('autopilot-backtest-win-rate');
  }

  get equityCurve() {
    return this.getByTestId('autopilot-backtest-equity-curve');
  }

  get tradesTable() {
    return this.getByTestId('autopilot-backtest-trades-table');
  }

  get drawdown() {
    return this.getByTestId('autopilot-backtest-drawdown');
  }

  // ===========================================================================
  // LOCATORS - Filters & Actions
  // ===========================================================================

  get filterStrategy() {
    return this.getByTestId('autopilot-backtest-filter-strategy');
  }

  get filterStatus() {
    return this.getByTestId('autopilot-backtest-filter-status');
  }

  get filterCompleted() {
    return this.getByTestId('autopilot-backtest-filter-completed');
  }

  get compareToggle() {
    return this.getByTestId('autopilot-backtest-compare-toggle');
  }

  get deleteConfirm() {
    return this.getByTestId('autopilot-backtest-delete-confirm');
  }

  get pagination() {
    return this.getByTestId('autopilot-backtest-pagination');
  }

  get emptyState() {
    return this.getByTestId('autopilot-backtest-empty');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-backtest-page"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async openConfigModal() {
    await this.newButton.click();
    await this.configModal.waitFor({ state: 'visible' });
  }

  async configureBacktest({ name, strategy, startDate, endDate, capital, lots, slippage }) {
    await this.openConfigModal();
    // Wait for modal to be fully visible
    await this.page.waitForTimeout(300);

    if (name && await this.nameInput.isVisible()) {
      await this.nameInput.fill(name);
    }
    if (strategy && await this.strategySelect.isVisible()) {
      await this.strategySelect.click();
      await this.getByTestId(`autopilot-backtest-strategy-option-${strategy}`).click();
    }
    if (startDate && await this.startDate.isVisible()) {
      await this.startDate.fill(startDate);
    }
    if (endDate && await this.endDate.isVisible()) {
      await this.endDate.fill(endDate);
    }
    if (capital && await this.capitalInput.isVisible()) {
      await this.capitalInput.fill(capital.toString());
    }
    if (lots && await this.lotsInput.isVisible()) {
      await this.lotsInput.fill(lots.toString());
    }
    if (slippage !== undefined && await this.slippageInput.isVisible()) {
      await this.slippageInput.fill(slippage.toString());
    }
  }

  async runBacktest() {
    await this.runButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async cancelConfig() {
    await this.cancelButton.click();
    await this.configModal.waitFor({ state: 'hidden' });
  }

  async openResults(id) {
    await this.getBacktestRow(id).click();
    await this.resultsPage.waitFor({ state: 'visible' });
  }

  async deleteBacktest(id) {
    await this.getBacktestDelete(id).click();
    await this.deleteConfirm.click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByStrategy(strategy) {
    await this.filterStrategy.click();
    await this.getByTestId(`autopilot-backtest-filter-option-${strategy}`).click();
    await this.page.waitForLoadState('networkidle');
  }

  async filterByCompleted() {
    // The filter is a select dropdown, select the "completed" option
    await this.filterCompleted.selectOption('completed');
    await this.page.waitForLoadState('networkidle');
  }

  async enableCompareMode() {
    const toggle = this.compareToggle;
    if (await toggle.isVisible()) {
      await toggle.click();
    }
    // If compare toggle doesn't exist, just pass silently
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getBacktestCount() {
    return await this.backtestRows.count();
  }
}


/**
 * AutoPilot Sharing Page Object
 *
 * Page object for AutoPilot Strategy Sharing functionality.
 * URL: /autopilot/shared
 */
export class AutoPilotSharingPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/autopilot/shared';
  }

  // ===========================================================================
  // LOCATORS - Share Modal
  // ===========================================================================

  get shareModal() {
    return this.getByTestId('autopilot-share-modal');
  }

  get publicToggle() {
    return this.getByTestId('autopilot-share-public-toggle');
  }

  get descriptionInput() {
    return this.getByTestId('autopilot-share-description-input');
  }

  get generateButton() {
    return this.getByTestId('autopilot-share-generate-btn');
  }

  get shareLink() {
    return this.getByTestId('autopilot-share-link');
  }

  get copyButton() {
    return this.getByTestId('autopilot-share-copy-btn');
  }

  get copiedToast() {
    return this.getByTestId('autopilot-share-copied-toast');
  }

  get expirationSelect() {
    return this.getByTestId('autopilot-share-expiration');
  }

  get cancelButton() {
    return this.getByTestId('autopilot-share-cancel-btn');
  }

  // ===========================================================================
  // LOCATORS - Shared Strategies List
  // ===========================================================================

  get sharedStrategiesList() {
    return this.getByTestId('autopilot-shared-strategies-list');
  }

  get sharedStrategies() {
    return this.page.locator('[data-testid^="autopilot-shared-strategy-"]');
  }

  getSharedStrategy(id) {
    return this.getByTestId(`autopilot-shared-strategy-${id}`);
  }

  // ===========================================================================
  // LOCATORS - Shared Strategy Details
  // ===========================================================================

  get sharedStrategyPage() {
    return this.getByTestId('autopilot-shared-strategy-page');
  }

  get sharedStrategyDetails() {
    return this.getByTestId('autopilot-shared-strategy-details');
  }

  get readonlyBadge() {
    return this.getByTestId('autopilot-shared-readonly-badge');
  }

  get notFound() {
    return this.getByTestId('autopilot-shared-not-found');
  }

  // ===========================================================================
  // LOCATORS - Clone
  // ===========================================================================

  get cloneButton() {
    return this.getByTestId('autopilot-clone-btn');
  }

  get cloneModal() {
    return this.getByTestId('autopilot-clone-modal');
  }

  get cloneNameInput() {
    return this.getByTestId('autopilot-clone-name-input');
  }

  get cloneSubmitButton() {
    return this.getByTestId('autopilot-clone-submit-btn');
  }

  get cloneSuccessToast() {
    return this.getByTestId('autopilot-clone-success-toast');
  }

  // ===========================================================================
  // LOCATORS - Unshare
  // ===========================================================================

  get unshareConfirmButton() {
    return this.getByTestId('autopilot-unshare-confirm-btn');
  }

  // ===========================================================================
  // ACTIONS
  // ===========================================================================

  async waitForPageLoad() {
    await this.page.waitForSelector('[data-testid="autopilot-shared-strategies-list"]', {
      timeout: 10000
    });
    await this.page.waitForLoadState('networkidle');
  }

  async enablePublicSharing() {
    await this.publicToggle.click();
  }

  async setShareDescription(description) {
    await this.descriptionInput.fill(description);
  }

  async generateShareLink() {
    await this.generateButton.click();
    await this.shareLink.waitFor({ state: 'visible' });
  }

  async copyShareLink() {
    await this.copyButton.click();
  }

  async setExpiration(days) {
    await this.expirationSelect.selectOption(days.toString());
  }

  async cancelShare() {
    await this.cancelButton.click();
    await this.shareModal.waitFor({ state: 'hidden' });
  }

  async openSharedStrategy(id) {
    await this.getSharedStrategy(id).click();
    await this.sharedStrategyDetails.waitFor({ state: 'visible' });
  }

  async cloneStrategy(newName) {
    await this.cloneButton.click();
    await this.cloneModal.waitFor({ state: 'visible' });
    await this.cloneNameInput.fill(newName);
    await this.cloneSubmitButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async confirmUnshare() {
    await this.unshareConfirmButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  // ===========================================================================
  // ASSERTIONS HELPERS
  // ===========================================================================

  async getSharedCount() {
    return await this.sharedStrategies.count();
  }
}
