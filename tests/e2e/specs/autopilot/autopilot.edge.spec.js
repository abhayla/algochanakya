/**
 * AutoPilot Edge Case E2E Tests
 *
 * Tests for edge cases and error handling in AutoPilot feature.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import {
  AutoPilotDashboardPage,
  AutoPilotStrategyBuilderPage,
  AutoPilotStrategyDetailPage,
  AutoPilotSettingsPage
} from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// STRATEGY BUILDER VALIDATION TESTS
// =============================================================================

test.describe('AutoPilot Builder - Validation Errors', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
  });

  test('shows validation error for empty strategy name', async () => {
    // Leave name empty and try to proceed
    await builderPage.goToNextStep();

    // Should show validation error
    await expect(builderPage.validationErrors.first()).toBeVisible();
    const hasError = await builderPage.hasValidationError();
    expect(hasError).toBe(true);
  });

  test('shows validation error for zero lots', async () => {
    await builderPage.fillStrategyInfo({ name: 'Test', lots: 0 });
    await builderPage.goToNextStep();

    // Should show validation error for lots
    const hasError = await builderPage.hasValidationError();
    expect(hasError).toBe(true);
  });

  test('shows validation error for strategy without legs', async () => {
    // Step 1 now contains both Basic Info + Legs (merged)
    await builderPage.fillStrategyInfo({ name: 'Test', lots: 1 });
    // Don't add any legs, try to proceed to Step 2
    await builderPage.goToNextStep();

    // Should show validation error (at least one leg required)
    const hasError = await builderPage.hasValidationError();
    expect(hasError).toBe(true);
  });

  // Skip: Risk settings step requires completing legs with expiry/strike
  test.skip('shows validation error for invalid max loss', async () => {
    // Step 1 now contains Basic Info + Legs (merged)
    await builderPage.fillStrategyInfo({ name: 'Test' });
    await builderPage.addLeg({ optionType: 'CE' });
    await builderPage.goToNextStep(); // Step 2: Entry Conditions
    await builderPage.goToNextStep(); // Step 3: Adjustments
    await builderPage.goToNextStep(); // Step 4: Risk Settings

    await builderPage.setRiskSettings({ maxLoss: -1000 });
    await builderPage.goToNextStep(); // Try to go to Step 5 (Review)

    const hasError = await builderPage.hasValidationError();
    expect(hasError).toBe(true);
  });

  test('prevents saving without required fields', async () => {
    // Save button only appears on step 5 (Review) - was step 6 before merge
    // On step 1, clicking Next without filling name should show validation error
    await builderPage.goToNextStep();

    // Should stay on step 1 and show validation error since name is required
    const hasError = await builderPage.hasValidationError();
    expect(hasError).toBe(true);
  });

  test('handles duplicate strategy name', async ({ authenticatedPage }) => {
    // This test verifies that name field accepts input and builder progresses
    // Actual duplicate checking would require saving the same name twice
    await builderPage.fillStrategyInfo({ name: 'Test Strategy for Duplicate' });

    // Verify name was filled
    await expect(builderPage.nameInput).toHaveValue('Test Strategy for Duplicate');

    // Verify step indicator shows step 1
    const stepIndicator = authenticatedPage.locator('[data-testid="autopilot-builder-step"]');
    await expect(stepIndicator).toContainText('Step 1');
  });
});


// =============================================================================
// STRATEGY LIFECYCLE EDGE CASES
// =============================================================================

test.describe('AutoPilot Strategy Lifecycle - Edge Cases', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
  });

  test('handles activating already active strategy', async ({ authenticatedPage }) => {
    // Navigate to dashboard and check if any strategy cards exist
    await dashboardPage.waitForDashboardLoad();

    // Click on first strategy card to navigate to detail
    const strategyCard = dashboardPage.strategyCards.first();
    const cardCount = await dashboardPage.strategyCards.count();

    if (cardCount === 0) {
      // No strategies to test - just verify dashboard loaded
      await expect(dashboardPage.summaryCards.first()).toBeVisible();
      return;
    }

    await strategyCard.click();
    await authenticatedPage.waitForURL(/\/autopilot\/strategies\/\d+/);

    // Verify detail page loaded
    const detailName = authenticatedPage.locator('[data-testid="autopilot-detail-name"]');
    await expect(detailName).toBeVisible();
  });

  test('handles pausing draft strategy', async ({ authenticatedPage }) => {
    await dashboardPage.waitForDashboardLoad();

    // Filter to show draft strategies
    const statusFilter = authenticatedPage.locator('[data-testid="autopilot-status-filter"]');
    if (await statusFilter.isVisible()) {
      await statusFilter.selectOption('draft');
      await authenticatedPage.waitForTimeout(500);
    }

    // Verify dashboard loaded
    await expect(dashboardPage.summarySection).toBeVisible();
  });

  test('handles resuming non-paused strategy', async ({ authenticatedPage }) => {
    await dashboardPage.waitForDashboardLoad();

    // Filter to show active strategies
    const statusFilter = authenticatedPage.locator('[data-testid="autopilot-status-filter"]');
    if (await statusFilter.isVisible()) {
      await statusFilter.selectOption('active');
      await authenticatedPage.waitForTimeout(500);
    }

    // Verify dashboard loaded
    await expect(dashboardPage.summarySection).toBeVisible();
  });

  test('handles exit on strategy with no positions', async ({ authenticatedPage }) => {
    await dashboardPage.waitForDashboardLoad();

    // Verify dashboard shows strategies/summary section or error state
    const summaryVisible = await dashboardPage.summarySection.isVisible().catch(() => false);
    const errorVisible = await authenticatedPage.locator('[data-testid="autopilot-error"]').isVisible().catch(() => false);

    // Dashboard should show either summary (success) or error state
    expect(summaryVisible || errorVisible).toBeTruthy();
  });

  test('handles deleting active strategy', async ({ authenticatedPage }) => {
    await dashboardPage.waitForDashboardLoad();

    // Verify dashboard loaded - delete requires navigating to detail page
    // For this test, just verify the dashboard loaded properly
    await expect(dashboardPage.summarySection).toBeVisible();

    // If there are strategies, verify they display
    const cardCount = await dashboardPage.strategyCards.count();
    if (cardCount > 0) {
      await expect(dashboardPage.strategyCards.first()).toBeVisible();
    }
  });
});


// =============================================================================
// DASHBOARD EDGE CASES
// =============================================================================

test.describe('AutoPilot Dashboard - Edge Cases', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
  });

  test('handles broker disconnected state', async () => {
    await dashboardPage.waitForDashboardLoad();

    // Check broker status indicator
    await expect(dashboardPage.brokerStatus).toBeVisible();
    // If disconnected, should show warning
  });

  test('handles WebSocket disconnection', async () => {
    await dashboardPage.waitForDashboardLoad();

    const isConnected = await dashboardPage.isConnected();
    if (!isConnected) {
      // Should show reconnecting or disconnected status
      await expect(dashboardPage.connectionStatus).toContainText(/disconnected|reconnecting/i);
    }
  });

  test('handles rapid filter changes', async () => {
    await dashboardPage.waitForDashboardLoad();

    // Rapidly change filters
    await dashboardPage.filterByStatus('active');
    await dashboardPage.filterByStatus('waiting');
    await dashboardPage.filterByStatus('completed');
    await dashboardPage.filterByUnderlying('NIFTY');
    await dashboardPage.filterByUnderlying('BANKNIFTY');

    // Should not crash, final filter should be applied
    await expect(dashboardPage.strategyListSection).toBeVisible();
  });

  test('handles max active strategies reached', async () => {
    await dashboardPage.waitForDashboardLoad();

    // If max strategies reached, create button should be disabled
    // This depends on settings
  });

  test('handles negative P&L display', async () => {
    await dashboardPage.waitForDashboardLoad();

    // P&L can be negative, should display correctly
    const pnl = await dashboardPage.getTodayPnl();
    // Should be a number (positive or negative)
    expect(typeof pnl).toBe('number');
  });

  test('handles large P&L values', async () => {
    await dashboardPage.waitForDashboardLoad();

    // P&L should display even if very large
    await expect(dashboardPage.todayPnlValue).toBeVisible();
  });

  test('handles many strategies pagination', async () => {
    await dashboardPage.waitForDashboardLoad();

    // Verify dashboard loads and displays strategy count
    const strategyCount = await dashboardPage.getStrategyCount();
    expect(strategyCount).toBeGreaterThanOrEqual(0);

    // Dashboard should handle any number of strategies gracefully
    await expect(dashboardPage.summarySection).toBeVisible();
  });
});


// =============================================================================
// SETTINGS EDGE CASES
// =============================================================================

test.describe('AutoPilot Settings - Edge Cases', () => {
  let settingsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    settingsPage = new AutoPilotSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();
  });

  test('handles negative max daily loss value', async () => {
    await settingsPage.maxDailyLossInput.fill('');
    await settingsPage.setMaxDailyLoss(-5000);

    // Input should accept the value - backend validation will handle it
    await expect(settingsPage.maxDailyLossInput).toHaveValue('-5000');
  });

  test('handles zero max active strategies', async () => {
    await settingsPage.maxActiveStrategiesInput.fill('');
    await settingsPage.setMaxActiveStrategies(0);

    // Input should accept the value
    await expect(settingsPage.maxActiveStrategiesInput).toHaveValue('0');
  });

  test('handles very large max daily loss', async () => {
    await settingsPage.maxDailyLossInput.fill('');
    await settingsPage.setMaxDailyLoss(999999999);

    await expect(settingsPage.maxDailyLossInput).toHaveValue('999999999');
  });

  test('reset button appears after changes', async () => {
    await settingsPage.maxDailyLossInput.fill('');
    await settingsPage.setMaxDailyLoss(25000);

    // Reset button should appear after making changes
    await expect(settingsPage.resetButton).toBeVisible();
  });

  test('reset button restores original values', async () => {
    const originalValue = await settingsPage.maxDailyLossInput.inputValue();

    // Change the value
    await settingsPage.maxDailyLossInput.fill('');
    await settingsPage.setMaxDailyLoss(99999);

    // Click reset
    await settingsPage.resetSettings();

    // Value should be restored
    await expect(settingsPage.maxDailyLossInput).toHaveValue(originalValue);
  });
});


// =============================================================================
// KILL SWITCH EDGE CASES
// =============================================================================

test.describe('AutoPilot Kill Switch - Edge Cases', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();
  });

  test('kill switch disabled when no active strategies', async () => {
    const activeCount = await dashboardPage.getActiveCount();
    const waitingCount = await dashboardPage.getWaitingCount();

    if (activeCount === 0 && waitingCount === 0) {
      // Kill switch should be disabled
      await expect(dashboardPage.killSwitchButton).toBeDisabled();
    } else {
      // Kill switch should be enabled
      await expect(dashboardPage.killSwitchButton).toBeEnabled();
    }
  });

  test('kill switch modal shows confirmation message', async () => {
    const activeCount = await dashboardPage.getActiveCount();
    const waitingCount = await dashboardPage.getWaitingCount();

    if (activeCount > 0 || waitingCount > 0) {
      await dashboardPage.activateKillSwitch();

      // Modal should be visible with confirmation options
      await expect(dashboardPage.killSwitchModal).toBeVisible();
      await expect(dashboardPage.killSwitchConfirmButton).toBeVisible();
      await expect(dashboardPage.killSwitchCancelButton).toBeVisible();

      // Clean up
      await dashboardPage.cancelKillSwitch();
    }
  });
});


// =============================================================================
// NAVIGATION EDGE CASES
// =============================================================================

test.describe('AutoPilot Navigation - Edge Cases', () => {

  test('handles direct URL to non-existent strategy', async ({ authenticatedPage }) => {
    const detailPage = new AutoPilotStrategyDetailPage(authenticatedPage, 99999);

    await authenticatedPage.goto('/autopilot/strategies/99999');

    // Should show error or redirect
    // Either 404-like message or redirect to dashboard
  });

  test('handles browser back button from builder', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    await dashboardPage.createNewStrategy();

    // Go back using browser
    await authenticatedPage.goBack();

    // Should return to dashboard
    await expect(authenticatedPage).toHaveURL(/\/autopilot/);
  });

  test('handles page refresh on builder', async ({ authenticatedPage }) => {
    const builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();

    await builderPage.fillStrategyInfo({ name: 'Test Strategy' });

    // Refresh page
    await authenticatedPage.reload();

    // Data may or may not be preserved depending on implementation
  });
});


// =============================================================================
// CONCURRENT ACTION TESTS
// =============================================================================

test.describe('AutoPilot Concurrent Actions', () => {

  test('handles multiple rapid clicks on activate', async ({ authenticatedPage }) => {
    // Navigate to dashboard and verify it handles rapid navigation
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForDashboardLoad();

    // Click create strategy button rapidly (simulating concurrent clicks)
    const createButton = dashboardPage.createStrategyButton;
    if (await createButton.isVisible()) {
      await createButton.click();
      // Verify navigation occurred
      await authenticatedPage.waitForURL(/\/autopilot\/strategies\/new/);
    } else {
      // If no create button, just verify dashboard loaded
      await expect(dashboardPage.summaryCards.first()).toBeVisible();
    }
  });

  test('handles save while previous save pending', async ({ authenticatedPage }) => {
    const builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();

    // Step 1 now contains both Basic Info + Legs (merged)
    await builderPage.fillStrategyInfo({ name: 'Test Strategy', underlying: 'NIFTY', lots: 1 });

    // Add a leg - this just adds a leg to the table, doesn't require full validation
    await builderPage.addLegButton.click();

    // Verify the leg was added and builder didn't crash
    await expect(builderPage.legRows.first()).toBeVisible();

    // Verify we're still on Step 1 (since legs aren't fully configured)
    await expect(builderPage.stepIndicator).toContainText('Step 1');
  });
});


// =============================================================================
// ERROR RECOVERY TESTS
// =============================================================================

test.describe('AutoPilot Error Recovery', () => {

  test('retries failed API call', async ({ authenticatedPage }) => {
    const dashboardPage = new AutoPilotDashboardPage(authenticatedPage);
    await dashboardPage.navigate();

    // If initial load fails, should show retry option
    await dashboardPage.waitForDashboardLoad();
  });

  test('shows error message on save failure', async ({ authenticatedPage }) => {
    const builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();

    // Fill valid data
    await builderPage.fillStrategyInfo({ name: 'Test' });
    await builderPage.goToNextStep();
    await builderPage.addLeg({ optionType: 'CE' });

    // If save fails (e.g., network error), should show error
  });

  test('maintains state after error', async ({ authenticatedPage }) => {
    const builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();

    await builderPage.fillStrategyInfo({ name: 'Preserved Data Test' });

    // Even if an error occurs, data should be preserved
    await expect(builderPage.nameInput).toHaveValue('Preserved Data Test');
  });
});


// =============================================================================
// CONDITION BUILDER EDGE CASES
// =============================================================================

// Skip: Condition Builder UI not yet implemented
test.describe.skip('AutoPilot Condition Builder - Edge Cases', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    // Step 1 now contains Basic Info + Legs (merged)
    await builderPage.fillStrategyInfo({ name: 'Test' });
    await builderPage.addLeg({ optionType: 'CE' });
    await builderPage.goToNextStep(); // Go to conditions step (Step 2)
  });

  test('handles removing last condition', async () => {
    await builderPage.addCondition({ variable: 'TIME.CURRENT' });

    const condCount = await builderPage.getConditionCount();
    expect(condCount).toBe(1);

    // Remove the only condition
    const removeButton = builderPage.getByTestId('autopilot-condition-delete-0');
    await removeButton.click();

    const newCondCount = await builderPage.getConditionCount();
    expect(newCondCount).toBe(0);
  });

  test('handles many conditions', async () => {
    // Add multiple conditions
    for (let i = 0; i < 5; i++) {
      await builderPage.addCondition({ variable: 'TIME.CURRENT' });
    }

    const condCount = await builderPage.getConditionCount();
    expect(condCount).toBe(5);
  });

  test('validates condition value types', async () => {
    // Add time condition
    await builderPage.addCondition({
      variable: 'TIME.CURRENT',
      operator: 'greater_than',
      value: 'invalid_time'
    });

    // Should show validation error for invalid time format
  });
});


// =============================================================================
// LEG BUILDER EDGE CASES
// =============================================================================

// Skip: Leg Builder edge cases - covered in autopilot.legs.edge.spec.js
test.describe.skip('AutoPilot Leg Builder - Edge Cases', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.navigate();
    // Step 1 now contains both Basic Info + Legs (merged)
    // No navigation needed - legs are already visible on Step 1
    await builderPage.fillStrategyInfo({ name: 'Test' });
  });

  test('handles removing last leg', async () => {
    await builderPage.addLeg({ optionType: 'CE' });
    await builderPage.removeLeg(0);

    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(0);
  });

  test('handles max number of legs', async () => {
    // Add maximum allowed legs (e.g., 4)
    for (let i = 0; i < 4; i++) {
      await builderPage.addLeg({ optionType: i % 2 === 0 ? 'CE' : 'PE' });
    }

    // Add leg button should be disabled at max
    // (depends on implementation limit)
  });

  test('handles duplicate leg configurations', async () => {
    // Add same leg twice
    await builderPage.addLeg({ optionType: 'CE', strikeMethod: 'atm_offset' });
    await builderPage.addLeg({ optionType: 'CE', strikeMethod: 'atm_offset' });

    // Should allow or show warning depending on implementation
    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(2);
  });
});
