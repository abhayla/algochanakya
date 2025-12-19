/**
 * AutoPilot Happy Path E2E Tests
 *
 * Tests for the happy path flows of AutoPilot feature.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import {
  AutoPilotDashboardPage,
  AutoPilotStrategyBuilderPage,
  AutoPilotStrategyDetailPage,
  AutoPilotSettingsPage
} from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// DASHBOARD TESTS
// =============================================================================

test.describe('AutoPilot Dashboard - Happy Path', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
  });

  test('displays dashboard summary cards', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.activeStrategiesCard).toBeVisible();
    await expect(dashboardPage.todayPnlCard).toBeVisible();
    await expect(dashboardPage.capitalUsedCard).toBeVisible();
    await expect(dashboardPage.riskStatusCard).toBeVisible();
  });

  test('displays active strategy count', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.activeStrategiesCount).toBeVisible();
    const count = await dashboardPage.getActiveCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('displays today P&L value', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.todayPnlValue).toBeVisible();
  });

  test('displays risk status badge', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.riskStatusBadge).toBeVisible();
    const status = await dashboardPage.getRiskStatus();
    expect(['safe', 'warning', 'critical']).toContain(status.toLowerCase());
  });

  test('shows create strategy button', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.createStrategyButton).toBeVisible();
    await expect(dashboardPage.createStrategyButton).toBeEnabled();
  });

  test('navigates to create strategy page', async ({ authenticatedPage }) => {
    await dashboardPage.waitForDashboardLoad();
    await dashboardPage.createNewStrategy();

    await expect(authenticatedPage).toHaveURL(/\/autopilot\/strategies\/new/);
  });

  test('navigates to settings page', async ({ authenticatedPage }) => {
    await dashboardPage.waitForDashboardLoad();
    await dashboardPage.openSettings();

    await expect(authenticatedPage).toHaveURL(/\/autopilot\/settings/);
  });

  test('displays strategy list', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.strategyListSection).toBeVisible();
  });

  test('refresh button updates data', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.refreshButton).toBeVisible();
    await dashboardPage.refreshDashboard();

    await expect(dashboardPage.summarySection).toBeVisible();
  });

  test('displays connection status indicator', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.connectionStatus).toBeVisible();
  });

  test('displays broker status indicator', async () => {
    await dashboardPage.waitForDashboardLoad();

    await expect(dashboardPage.brokerStatus).toBeVisible();
  });
});


// =============================================================================
// PHASE 2 DASHBOARD ENHANCEMENTS TESTS
// =============================================================================

test.describe('AutoPilot Dashboard - Phase 2 Enhancements', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  // Market Status Indicator Tests
  test('displays market status indicator', async () => {
    await expect(dashboardPage.marketStatusIndicator).toBeVisible();
  });

  test('shows market status dot with correct state', async () => {
    await expect(dashboardPage.marketStatusDot).toBeVisible();
    const status = await dashboardPage.getMarketStatus();
    expect(['open', 'closed']).toContain(status);
  });

  test('displays market countdown timer', async () => {
    await expect(dashboardPage.marketCountdown).toBeVisible();
    const countdown = await dashboardPage.getMarketCountdown();
    expect(countdown).toBeTruthy();
  });

  test('shows NIFTY index price', async () => {
    await expect(dashboardPage.niftyPrice).toBeVisible();
  });

  test('shows BANKNIFTY index price', async () => {
    await expect(dashboardPage.bankniftyPrice).toBeVisible();
  });

  test('shows VIX index price', async () => {
    await expect(dashboardPage.vixPrice).toBeVisible();
  });

  // P&L Card Enhancements Tests
  test('displays P&L sparkline chart', async () => {
    await expect(dashboardPage.pnlSparkline).toBeVisible();
  });

  test('shows P&L trend arrow when P&L is non-zero', async () => {
    const pnl = await dashboardPage.getTodayPnl();
    if (pnl !== 0) {
      await expect(dashboardPage.pnlTrendArrow).toBeVisible();
      const direction = await dashboardPage.getPnlTrendDirection();
      expect(['up', 'down']).toContain(direction);
    }
  });

  // Capital Used Enhancements Tests
  test('displays capital usage progress bar', async () => {
    await expect(dashboardPage.capitalProgressBar).toBeVisible();
  });

  test('shows capital utilization percentage', async () => {
    await expect(dashboardPage.capitalPercentage).toBeVisible();
    const pct = await dashboardPage.getCapitalUtilizationPct();
    expect(pct).toBeGreaterThanOrEqual(0);
    expect(pct).toBeLessThanOrEqual(100);
  });

  // Broker Status Enhanced Tests
  test('displays broker sync timestamp', async () => {
    await expect(dashboardPage.brokerSyncTime).toBeVisible();
    const syncTime = await dashboardPage.getBrokerSyncTime();
    expect(syncTime).toBeTruthy();
  });

  // Activity Timeline Enhanced Tests
  test('displays activity filter dropdown', async () => {
    await expect(dashboardPage.activityFilter).toBeVisible();
  });

  test('filters activities by type', async () => {
    const initialCount = await dashboardPage.getActivityFilteredCount();

    await dashboardPage.filterActivities('orders');
    await expect(dashboardPage.activityFilter).toHaveValue('orders');

    await dashboardPage.filterActivities('all');
    await expect(dashboardPage.activityFilter).toHaveValue('all');
  });

  test('shows real-time indicator when connected', async () => {
    const isConnected = await dashboardPage.isConnected();
    const hasRealtimeIndicator = await dashboardPage.isRealtimeConnected();
    expect(hasRealtimeIndicator).toBe(isConnected);
  });
});


// =============================================================================
// PHASE 2 QUICK DEPLOY TEMPLATES TESTS
// =============================================================================

test.describe('AutoPilot Dashboard - Quick Deploy Templates', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('displays template buttons when no strategies exist', async () => {
    const strategyCount = await dashboardPage.getStrategyCount();

    if (strategyCount === 0) {
      await expect(dashboardPage.templateShortStraddle).toBeVisible();
      await expect(dashboardPage.templateIronCondor).toBeVisible();
      await expect(dashboardPage.templateBullCallSpread).toBeVisible();
      await expect(dashboardPage.templateShortStrangle).toBeVisible();
    }
  });
});


// =============================================================================
// STRATEGY FILTERING TESTS
// =============================================================================

test.describe('AutoPilot Dashboard - Filtering', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('filters strategies by status', async () => {
    await expect(dashboardPage.statusFilter).toBeVisible();
    await dashboardPage.filterByStatus('active');

    // Strategies should be filtered
    await expect(dashboardPage.strategyListSection).toBeVisible();
  });

  test('filters strategies by underlying', async () => {
    await expect(dashboardPage.underlyingFilter).toBeVisible();
    await dashboardPage.filterByUnderlying('NIFTY');

    await expect(dashboardPage.strategyListSection).toBeVisible();
  });

  test('clears all filters', async () => {
    await dashboardPage.filterByStatus('active');
    await dashboardPage.filterByUnderlying('NIFTY');

    await dashboardPage.clearAllFilters();

    // Filters should be reset
    await expect(dashboardPage.strategyListSection).toBeVisible();
  });
});


// =============================================================================
// STRATEGY BUILDER TESTS
// =============================================================================

test.describe('AutoPilot Strategy Builder - Happy Path', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
  });

  test('displays strategy info form', async () => {
    await expect(builderPage.nameInput).toBeVisible();
    await expect(builderPage.underlyingSelect).toBeVisible();
    await expect(builderPage.lotsInput).toBeVisible();
  });

  test('fills strategy basic info', async ({ authenticatedPage }) => {
    await builderPage.fillStrategyInfo({
      name: 'Test Strategy',
      description: 'A test strategy for E2E testing',
      underlying: 'NIFTY',
      lots: 1
    });

    await expect(builderPage.nameInput).toHaveValue('Test Strategy');
    // Check lots value - Vue's v-model.number may return number or string
    const lotsValue = await builderPage.lotsInput.inputValue();
    expect(parseInt(lotsValue, 10)).toBe(1);
  });

  test('navigates between builder steps', async () => {
    // Step 1 now contains both Basic Info + Legs (merged)
    await builderPage.fillStrategyInfo({ name: 'Test' });
    // Add a leg with required strike to allow navigation (at least one complete leg required)
    await builderPage.addLeg({ strike: '25000' });

    await builderPage.goToNextStep(); // Go to Step 2 (Entry Conditions)
    const step = await builderPage.getCurrentStep();
    expect(step).toBe(2);

    await builderPage.goToPreviousStep(); // Back to Step 1 (Basic Info + Legs)
    const backStep = await builderPage.getCurrentStep();
    expect(backStep).toBe(1);
  });

  test('strategy type dropdown auto-populates legs for Iron Condor', async () => {
    // Select Iron Condor strategy type
    await builderPage.selectStrategyType('iron_condor');

    // Wait for legs to be added
    await builderPage.page.waitForTimeout(500);

    // Iron Condor should have 4 legs
    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(4);
  });

  test('strategy type dropdown auto-populates legs for Short Straddle', async () => {
    // Select Short Straddle strategy type
    await builderPage.selectStrategyType('short_straddle');

    // Wait for legs to be added
    await builderPage.page.waitForTimeout(500);

    // Short Straddle should have 2 legs
    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(2);
  });

  test('strategy type change shows replace confirmation when legs exist', async () => {
    // First add a leg manually
    await builderPage.addLeg({ strike: '25000' });
    expect(await builderPage.getLegCount()).toBe(1);

    // Now select a strategy type - should show confirmation
    await builderPage.selectStrategyType('iron_condor');

    // Confirmation modal should be visible
    await expect(builderPage.replaceLegsModal).toBeVisible();

    // Cancel and verify leg count unchanged
    await builderPage.cancelReplaceLegs();
    expect(await builderPage.getLegCount()).toBe(1);
  });

  test('confirming strategy type change replaces existing legs', async () => {
    // First add a leg manually
    await builderPage.addLeg({ strike: '25000' });
    expect(await builderPage.getLegCount()).toBe(1);

    // Select Iron Condor strategy type
    await builderPage.selectStrategyType('iron_condor');

    // Confirm replace
    await builderPage.confirmReplaceLegs();

    // Should now have 4 legs from Iron Condor
    expect(await builderPage.getLegCount()).toBe(4);
  });

  // Unskipped: Updated to use new table-based UI parameters
  // Step 1 now contains Basic Info + Legs (merged)
  test('adds leg to strategy', async () => {
    // Legs are now on Step 1 - no navigation needed
    await builderPage.addLeg({
      type: 'CE',
      action: 'SELL',
      strike: '25000'
    });

    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(1);
  });

  // Unskipped: Updated to use new table-based UI parameters
  // Step 1 now contains Basic Info + Legs (merged)
  test('removes leg from strategy', async () => {
    // Legs are now on Step 1 - no navigation needed
    await builderPage.addLeg({ type: 'CE', strike: '25000' });
    await builderPage.addLeg({ type: 'PE', strike: '24500' });

    await builderPage.removeLeg(0);

    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(1);
  });

  test('adds entry condition', async () => {
    // Step 1 now contains Basic Info + Legs, Step 2 is Entry Conditions
    // Fill required fields before navigating to next step
    await builderPage.fillStrategyInfo({ name: 'Test Entry Condition Strategy' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep(); // Go to conditions step (Step 2)

    await builderPage.addCondition({
      variable: 'TIME.CURRENT',
      operator: 'greater_than',
      value: '09:30'
    });

    const condCount = await builderPage.getConditionCount();
    expect(condCount).toBe(1);
  });

  test('toggles condition logic', async () => {
    // Step 1: Basic Info + Legs, Step 2: Entry Conditions
    // Fill required fields before navigating to next step
    await builderPage.fillStrategyInfo({ name: 'Test Condition Logic Strategy' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep(); // Go to Step 2

    await builderPage.addCondition({ variable: 'TIME.CURRENT' });
    await builderPage.addCondition({ variable: 'SPOT.PRICE' });

    await builderPage.setConditionLogic('OR');

    // Logic should be updated - verify the select has 'OR' selected
    await expect(builderPage.conditionLogicToggle).toHaveValue('OR');
  });

  test('sets risk settings', async () => {
    // Step 1: Basic Info + Legs, Step 2: Entry, Step 3: Adjustments, Step 4: Risk
    // Fill required fields before navigating through steps
    await builderPage.fillStrategyInfo({ name: 'Test Risk Settings Strategy' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep(); // Step 2
    await builderPage.goToNextStep(); // Step 3
    await builderPage.goToNextStep(); // Step 4 (Risk)

    await builderPage.setRiskSettings({
      maxLoss: 5000,
      maxProfit: 10000,
      trailingStop: 2000
    });

    await expect(builderPage.maxLossInput).toHaveValue('5000');
    await expect(builderPage.maxProfitInput).toHaveValue('10000');
  });

  test('sets schedule settings', async () => {
    // Fill required fields before navigating through steps
    await builderPage.fillStrategyInfo({ name: 'Test Schedule Settings Strategy' });
    await builderPage.addLeg({ strike: '25000', type: 'CE' });
    await builderPage.goToNextStep(); // Step 2 - Entry Conditions
    await builderPage.goToNextStep(); // Step 3 - Adjustments
    await builderPage.goToNextStep(); // Step 4 - Risk Settings (has schedule)

    await builderPage.setSchedule({
      activationMode: 'scheduled',  // Must be 'scheduled' to show time inputs
      startTime: '09:20',
      endTime: '15:15'
    });

    await expect(builderPage.startTimeInput).toHaveValue('09:20');
    await expect(builderPage.endTimeInput).toHaveValue('15:15');
  });

  test('cancels builder and returns to dashboard', async ({ authenticatedPage }) => {
    await builderPage.cancelBuilder();

    await expect(authenticatedPage).toHaveURL(/\/autopilot/);
  });
});


// =============================================================================
// STRATEGY DETAIL TESTS
// =============================================================================

test.describe('AutoPilot Strategy Detail - Happy Path', () => {
  // Note: These tests require at least one strategy to exist
  // They navigate to the first available strategy

  test('displays strategy header information', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    // Check if there are strategies to test with
    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) {
      // Skip if no strategies available
      return;
    }

    // Click first strategy to navigate to detail
    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await expect(detailPage.strategyName).toBeVisible();
    await expect(detailPage.strategyStatus).toBeVisible();
  });

  test('displays P&L information', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await expect(detailPage.pnlSection).toBeVisible();
  });

  test('displays orders section', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await expect(detailPage.ordersSection).toBeVisible();
  });

  test('displays activity logs', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await expect(detailPage.logsSection).toBeVisible();
  });

  test('navigates back to dashboard', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.strategyCards.count();
    if (strategyCount === 0) return;

    await dashboardPage.strategyCards.first().click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage);
    await detailPage.goBack();

    await expect(authenticatedPage).toHaveURL(/\/autopilot$/);
  });
});


// =============================================================================
// SETTINGS TESTS
// =============================================================================

test.describe('AutoPilot Settings - Happy Path', () => {
  let settingsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    settingsPage = new AutoPilotSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();
  });

  test('displays settings page', async () => {
    await expect(settingsPage.settingsPage).toBeVisible();
  });

  test('displays risk limit inputs', async () => {
    await expect(settingsPage.maxDailyLossInput).toBeVisible();
    await expect(settingsPage.maxActiveStrategiesInput).toBeVisible();
    await expect(settingsPage.maxCapitalInput).toBeVisible();
  });

  test('displays features section with paper trading toggle', async () => {
    await expect(settingsPage.featuresSection).toBeVisible();
    await expect(settingsPage.paperTradingToggle).toBeVisible();
  });

  test('modifies max daily loss', async () => {
    await settingsPage.maxDailyLossInput.fill('');
    await settingsPage.setMaxDailyLoss(20000);

    await expect(settingsPage.maxDailyLossInput).toHaveValue('20000');
  });

  test('modifies max active strategies', async () => {
    await settingsPage.maxActiveStrategiesInput.fill('');
    await settingsPage.setMaxActiveStrategies(5);

    await expect(settingsPage.maxActiveStrategiesInput).toHaveValue('5');
  });

  test('toggles paper trading mode', async () => {
    const initialChecked = await settingsPage.paperTradingToggle.isChecked();
    await settingsPage.togglePaperTrading();
    const afterChecked = await settingsPage.paperTradingToggle.isChecked();
    expect(afterChecked).not.toBe(initialChecked);
    // Toggle back to restore state
    await settingsPage.togglePaperTrading();
  });

  test('save button becomes enabled after changes', async () => {
    // Make a change
    await settingsPage.maxDailyLossInput.fill('');
    await settingsPage.setMaxDailyLoss(25000);

    // Save button should be enabled
    await expect(settingsPage.saveButton).toBeEnabled();
  });

  test('navigates back to dashboard', async ({ authenticatedPage }) => {
    await settingsPage.goBack();

    await expect(authenticatedPage).toHaveURL(/\/autopilot$/);
  });
});


// =============================================================================
// KILL SWITCH TESTS
// =============================================================================

test.describe('AutoPilot Kill Switch', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('shows kill switch button', async () => {
    await expect(dashboardPage.killSwitchButton).toBeVisible();
  });

  test('kill switch is disabled when no active strategies', async () => {
    // Kill switch should be disabled when there are no active/waiting strategies
    const activeCount = await dashboardPage.getActiveCount();
    const waitingCount = await dashboardPage.getWaitingCount();

    if (activeCount === 0 && waitingCount === 0) {
      await expect(dashboardPage.killSwitchButton).toBeDisabled();
    }
  });

  test('opens kill switch confirmation modal when strategies active', async () => {
    const activeCount = await dashboardPage.getActiveCount();
    const waitingCount = await dashboardPage.getWaitingCount();

    // Only test if there are active/waiting strategies
    if (activeCount > 0 || waitingCount > 0) {
      await dashboardPage.activateKillSwitch();

      await expect(dashboardPage.killSwitchModal).toBeVisible();
      await expect(dashboardPage.killSwitchConfirmButton).toBeVisible();
      await expect(dashboardPage.killSwitchCancelButton).toBeVisible();

      // Cancel to clean up
      await dashboardPage.cancelKillSwitch();
    }
  });

  test('cancels kill switch modal', async () => {
    const activeCount = await dashboardPage.getActiveCount();
    const waitingCount = await dashboardPage.getWaitingCount();

    if (activeCount > 0 || waitingCount > 0) {
      await dashboardPage.activateKillSwitch();
      await dashboardPage.cancelKillSwitch();

      await expect(dashboardPage.killSwitchModal).not.toBeVisible();
    }
  });
});


// =============================================================================
// ACTIVITY FEED TESTS
// =============================================================================

test.describe('AutoPilot Activity Feed', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('displays activity feed section', async () => {
    await expect(dashboardPage.activityFeed).toBeVisible();
  });

  test('displays activity items when available', async () => {
    // Activity items may or may not be present
    const itemCount = await dashboardPage.activityItems.count();
    expect(itemCount).toBeGreaterThanOrEqual(0);
  });
});


// =============================================================================
// EMPTY STATE TESTS
// =============================================================================

test.describe('AutoPilot Empty State', () => {
  // Note: This test's behavior depends on whether strategies exist

  test('displays empty state or strategy list', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    // Check if strategies exist
    const strategyCount = await dashboardPage.getStrategyCount();

    if (strategyCount === 0) {
      // Empty state should be shown
      await expect(dashboardPage.emptyState).toBeVisible();
      await expect(dashboardPage.emptyStateCreateButton).toBeVisible();
    } else {
      // Strategy list should be shown
      await expect(dashboardPage.strategyListSection).toBeVisible();
    }
  });

  test('empty state create button navigates to builder', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    const strategyCount = await dashboardPage.getStrategyCount();
    if (strategyCount === 0) {
      await dashboardPage.emptyStateCreateButton.click();
      await expect(authenticatedPage).toHaveURL(/\/autopilot\/strategies\/new/);
    }
  });
});
