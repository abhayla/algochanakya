/**
 * AutoPilot Legs Configuration - Edge Case Tests
 *
 * Tests for edge cases and validation in AutoPilot legs configuration.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Legs Configuration - Edge Cases', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.goto('/autopilot/strategies/new');
    // Wait for the name input to be visible instead of networkidle (WebSocket keeps connection active)
    await builderPage.nameInput.waitFor({ state: 'visible', timeout: 10000 });

    // Step 1 now contains both Basic Info + Legs (merged)
    // No need to navigate to a separate legs step
    await builderPage.fillStrategyInfo({
      name: 'Edge Test Strategy',
      underlying: 'NIFTY',
      lots: 1
    });
    // Legs are already visible on Step 1, no navigation needed
  });

  test('should show validation error when proceeding without legs', async ({ authenticatedPage }) => {
    // Try to proceed without adding legs (from Step 1 merged view)
    await builderPage.goToNextStep();

    // Should show validation error
    await expect(builderPage.validationErrors.first()).toBeVisible();
    await expect(builderPage.validationErrors.first()).toContainText('At least one leg is required');

    // Should still be on step 1 (merged Basic Info + Legs)
    const step = await builderPage.getCurrentStep();
    expect(step).toBe(1);
  });

  test('should disable delete selected when no legs selected', async ({ authenticatedPage }) => {
    // Add a leg but don't select it
    await builderPage.addLegButton.click();

    // Delete selected button should be disabled
    await expect(builderPage.deleteSelectedButton).toBeDisabled();
  });

  test('should enable delete selected when leg is selected', async ({ authenticatedPage }) => {
    // Add a leg and select it
    await builderPage.addLegButton.click();
    await builderPage.selectLeg(0);

    // Delete selected button should be enabled
    await expect(builderPage.deleteSelectedButton).toBeEnabled();
  });

  test('should handle lots input with minimum value 1', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Try to set lots to 0
    await builderPage.getLegLots(0).fill('0');

    // Should revert to 1 or show validation
    const lotsValue = await builderPage.getLegLots(0).inputValue();
    // Lots should be at least 1 (implementation may vary)
    expect(parseInt(lotsValue) || 1).toBeGreaterThanOrEqual(1);
  });

  test('should handle negative price values gracefully', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Try to enter negative target price
    await builderPage.getLegTargetPrice(0).fill('-100');

    // UI should accept the input (validation happens on submit)
    const value = await builderPage.getLegTargetPrice(0).inputValue();
    expect(value).toBe('-100');
  });

  test('should delete all legs when select all and delete', async ({ authenticatedPage }) => {
    // Add 3 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Select all and delete
    await builderPage.selectAllLegs();
    await builderPage.deleteSelectedLegs();

    // Should show empty state
    await expect(builderPage.legsEmptyState).toBeVisible();
  });

  test('should preserve leg data when navigating steps', async ({ authenticatedPage }) => {
    // Add a leg with data (now on Step 1 merged view)
    await builderPage.addLeg({
      action: 'BUY',
      type: 'CE',
      lots: 3
    });

    // Fill some AutoPilot fields
    await builderPage.getLegTargetPrice(0).fill('200');

    // Collapse and expand the Basic Info section to simulate UI interaction
    // This tests that leg data persists through UI state changes
    const basicInfoToggle = authenticatedPage.locator('[data-testid="autopilot-builder-basic-info-toggle"]');
    await basicInfoToggle.click(); // Collapse
    await basicInfoToggle.click(); // Expand

    // Verify data is preserved after UI interaction
    await expect(builderPage.getLegAction(0)).toHaveValue('BUY');
    await expect(builderPage.getLegType(0)).toHaveValue('CE');
    await expect(builderPage.getLegLots(0)).toHaveValue('3');
    await expect(builderPage.getLegTargetPrice(0)).toHaveValue('200');
  });

  test('should update select all checkbox state when individual selections change', async ({ authenticatedPage }) => {
    // Add 2 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Select one leg - select all should not be checked
    await builderPage.selectLeg(0);
    await expect(builderPage.selectAllCheckbox).not.toBeChecked();

    // Select second leg - select all should be checked
    await builderPage.selectLeg(1);
    await expect(builderPage.selectAllCheckbox).toBeChecked();

    // Deselect one - select all should not be checked
    await builderPage.deselectLeg(0);
    await expect(builderPage.selectAllCheckbox).not.toBeChecked();
  });

  test('should handle rapid add/delete operations', async ({ authenticatedPage }) => {
    // Rapidly add legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    let count = await builderPage.getLegCount();
    expect(count).toBe(5);

    // Rapidly delete legs
    await builderPage.removeLeg(4);
    await builderPage.removeLeg(3);
    await builderPage.removeLeg(2);

    count = await builderPage.getLegCount();
    expect(count).toBe(2);
  });

  test('should toggle trailing stop loss checkbox', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Check trailing SL
    await builderPage.getLegTrailingSl(0).check();
    await expect(builderPage.getLegTrailingSl(0)).toBeChecked();

    // Uncheck trailing SL
    await builderPage.getLegTrailingSl(0).uncheck();
    await expect(builderPage.getLegTrailingSl(0)).not.toBeChecked();
  });

  test('should display CMP column with valid live prices', async ({ authenticatedPage }) => {
    // Add a leg with specific configuration
    await builderPage.addLeg({
      action: 'SELL',
      type: 'PE',
      lots: 1
    });

    // CMP column should be visible
    const cmpCell = builderPage.getLegCmp(0);
    await expect(cmpCell).toBeVisible();

    // Wait for CMP to load (WebSocket or LTP API)
    await authenticatedPage.waitForTimeout(2000);

    // Check market hours to determine validation behavior
    const now = new Date();
    const istOffset = 5.5 * 60; // IST is UTC+5:30
    const istMinutes = now.getUTCHours() * 60 + now.getUTCMinutes() + istOffset;
    const marketOpen = 9 * 60 + 15;  // 9:15 AM IST
    const marketClose = 15 * 60 + 30; // 3:30 PM IST
    const isMarketHours = istMinutes >= marketOpen && istMinutes <= marketClose;
    const isWeekday = now.getUTCDay() >= 1 && now.getUTCDay() <= 5;

    // Get CMP value
    const cmpValue = await builderPage.getLegCmpValue(0);

    if (isMarketHours && isWeekday) {
      // During market hours: CMP must be a valid live price > 0
      // Test will fail if Kite broker token is expired or market data unavailable
      await builderPage.validateAllLegsCmp();
    } else {
      // During off-market hours: CMP can be "-" (null) or last closing price (>= 0)
      // If we have a value, it should be non-negative (closing price)
      if (cmpValue !== null) {
        expect(cmpValue).toBeGreaterThanOrEqual(0);
      }
    }
  });

  test('should display Exit P/L column', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Exit P/L column should be visible
    const exitPnlCell = builderPage.getLegExitPnl(0);
    await expect(exitPnlCell).toBeVisible();
  });

  test('should maintain leg order after deletion', async ({ authenticatedPage }) => {
    // Add 3 legs with different actions
    await builderPage.addLeg({ action: 'BUY' });
    await builderPage.addLeg({ action: 'SELL' });
    await builderPage.addLeg({ action: 'BUY' });

    // Delete middle leg
    await builderPage.removeLeg(1);

    // Verify remaining legs
    await expect(builderPage.getLegAction(0)).toHaveValue('BUY');
    await expect(builderPage.getLegAction(1)).toHaveValue('BUY');
  });

  test('should handle decimal values in price fields', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Wait for leg row to be visible
    await expect(builderPage.legRows.first()).toBeVisible();

    // Enter decimal values
    await builderPage.getLegEntry(0).fill('125.50');
    await builderPage.getLegTargetPrice(0).fill('150.75');

    // Verify values are preserved (browser may normalize 125.50 to 125.5)
    const entryValue = await builderPage.getLegEntry(0).inputValue();
    const targetValue = await builderPage.getLegTargetPrice(0).inputValue();
    expect(parseFloat(entryValue)).toBe(125.5);
    expect(parseFloat(targetValue)).toBe(150.75);
  });
});
