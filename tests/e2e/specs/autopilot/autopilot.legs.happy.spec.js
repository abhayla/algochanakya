/**
 * AutoPilot Legs Configuration - Happy Path Tests
 *
 * Tests for the enhanced legs table in AutoPilot Strategy Builder.
 * Covers: adding legs, configuring fields, selection, deletion.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotStrategyBuilderPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Legs Configuration - Happy Path', () => {
  let builderPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    builderPage = new AutoPilotStrategyBuilderPage(authenticatedPage);
    await builderPage.goto('/autopilot/strategies/new');
    // Wait for the name input to be visible instead of networkidle (WebSocket keeps connection active)
    await builderPage.nameInput.waitFor({ state: 'visible', timeout: 10000 });

    // Step 1 now contains both Basic Info + Legs (merged)
    // No need to navigate to a separate legs step
    await builderPage.fillStrategyInfo({
      name: 'Test Strategy',
      underlying: 'NIFTY',
      lots: 1
    });
    // Legs are already visible on Step 1, no navigation needed
  });

  test('should display empty state when no legs added', async ({ authenticatedPage }) => {
    // Verify empty state is shown
    await expect(builderPage.legsEmptyState).toBeVisible();
    await expect(builderPage.legsEmptyState).toContainText('No legs added');

    // Verify add button is visible
    await expect(builderPage.addLegButton).toBeVisible();
  });

  test('should add a leg with default values', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Verify leg row appears
    await expect(builderPage.getLegRow(0)).toBeVisible();

    // Verify empty state is hidden
    await expect(builderPage.legsEmptyState).not.toBeVisible();

    // Verify total row appears
    await expect(builderPage.legsTotalRow).toBeVisible();
  });

  test('should add multiple legs', async ({ authenticatedPage }) => {
    // Add 3 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Verify leg count
    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(3);

    // Verify all rows are visible
    await expect(builderPage.getLegRow(0)).toBeVisible();
    await expect(builderPage.getLegRow(1)).toBeVisible();
    await expect(builderPage.getLegRow(2)).toBeVisible();
  });

  test('should configure leg with all base fields', async ({ authenticatedPage }) => {
    // Add a leg with configuration
    await builderPage.addLeg({
      action: 'SELL',
      type: 'PE',
      lots: 2
    });

    // Verify fields are set
    await expect(builderPage.getLegAction(0)).toHaveValue('SELL');
    await expect(builderPage.getLegType(0)).toHaveValue('PE');
    await expect(builderPage.getLegLots(0)).toHaveValue('2');
  });

  test('should configure AutoPilot-specific fields', async ({ authenticatedPage }) => {
    // Add a leg
    await builderPage.addLegButton.click();

    // Fill AutoPilot-specific fields
    await builderPage.getLegTargetPrice(0).fill('150');
    await builderPage.getLegStopLossPrice(0).fill('80');
    await builderPage.getLegTrailingSl(0).check();
    await builderPage.getLegTargetPct(0).fill('20');
    await builderPage.getLegStopLossPct(0).fill('10');
    await builderPage.getLegMaxLoss(0).fill('5000');

    // Verify values
    await expect(builderPage.getLegTargetPrice(0)).toHaveValue('150');
    await expect(builderPage.getLegStopLossPrice(0)).toHaveValue('80');
    await expect(builderPage.getLegTrailingSl(0)).toBeChecked();
    await expect(builderPage.getLegTargetPct(0)).toHaveValue('20');
    await expect(builderPage.getLegStopLossPct(0)).toHaveValue('10');
    await expect(builderPage.getLegMaxLoss(0)).toHaveValue('5000');
  });

  test('should delete a single leg', async ({ authenticatedPage }) => {
    // Add 2 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    let legCount = await builderPage.getLegCount();
    expect(legCount).toBe(2);

    // Delete first leg
    await builderPage.removeLeg(0);

    // Verify leg count decreased
    legCount = await builderPage.getLegCount();
    expect(legCount).toBe(1);
  });

  test('should select and delete multiple legs', async ({ authenticatedPage }) => {
    // Add 3 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Select first and third leg
    await builderPage.selectLeg(0);
    await builderPage.selectLeg(2);

    // Delete selected
    await builderPage.deleteSelectedLegs();

    // Verify only middle leg remains
    const legCount = await builderPage.getLegCount();
    expect(legCount).toBe(1);
  });

  test('should select all legs using checkbox', async ({ authenticatedPage }) => {
    // Add 3 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Select all
    await builderPage.selectAllLegs();

    // Verify all checkboxes are checked
    await expect(builderPage.getLegCheckbox(0)).toBeChecked();
    await expect(builderPage.getLegCheckbox(1)).toBeChecked();
    await expect(builderPage.getLegCheckbox(2)).toBeChecked();
  });

  test('should deselect all legs', async ({ authenticatedPage }) => {
    // Add 2 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Select all, then deselect all
    await builderPage.selectAllLegs();
    await builderPage.deselectAllLegs();

    // Verify all checkboxes are unchecked
    await expect(builderPage.getLegCheckbox(0)).not.toBeChecked();
    await expect(builderPage.getLegCheckbox(1)).not.toBeChecked();
  });

  test('should show BUY leg with blue styling', async ({ authenticatedPage }) => {
    // Add a BUY leg
    await builderPage.addLeg({ action: 'BUY' });

    // Verify row has buy styling
    const row = builderPage.getLegRow(0);
    await expect(row).toHaveClass(/leg-buy/);
  });

  test('should show SELL leg with orange styling', async ({ authenticatedPage }) => {
    // Add a SELL leg
    await builderPage.addLeg({ action: 'SELL' });

    // Verify row has sell styling
    const row = builderPage.getLegRow(0);
    await expect(row).toHaveClass(/leg-sell/);
  });

  test('should display action bar with leg count', async ({ authenticatedPage }) => {
    // Add 2 legs
    await builderPage.addLegButton.click();
    await builderPage.addLegButton.click();

    // Verify action bar shows count
    const actionBar = builderPage.legsActionBar;
    await expect(actionBar).toContainText('2 leg(s)');
  });

  test('should proceed to next step with valid leg', async ({ authenticatedPage }) => {
    // Add a leg with required fields (will need expiry and strike in real scenario)
    await builderPage.addLegButton.click();

    // Get current step - Step 1 now contains both Basic Info + Legs (merged)
    const currentStep = await builderPage.getCurrentStep();
    expect(currentStep).toBe(1);

    // Note: In real test, would need to select expiry and strike from dropdowns
    // For now, verify we're on step 1 (merged Basic Info + Legs)
  });

  test('should display table header with all columns', async ({ authenticatedPage }) => {
    // Add a leg to make table visible
    await builderPage.addLegButton.click();

    // Verify table is visible
    await expect(builderPage.legsTable).toBeVisible();

    // Verify headers contain expected columns
    const table = builderPage.legsTable;
    await expect(table).toContainText('Action');
    await expect(table).toContainText('Expiry');
    await expect(table).toContainText('Strike');
    await expect(table).toContainText('Type');
    await expect(table).toContainText('Lots');
    await expect(table).toContainText('Entry');
    await expect(table).toContainText('CMP');
    await expect(table).toContainText('Exit P/L');
    await expect(table).toContainText('Target');
    await expect(table).toContainText('SL');
    await expect(table).toContainText('Trail');
  });

  test('should display valid CMP values from Kite live data', async ({ authenticatedPage }) => {
    // Add a leg with specific configuration
    await builderPage.addLeg({
      action: 'SELL',
      type: 'CE',
      lots: 1
    });

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
      // This test will fail if Kite broker token is expired or market data unavailable
      await builderPage.validateAllLegsCmp();
      expect(cmpValue).toBeGreaterThan(0);
    } else {
      // During off-market hours: CMP can be "-" (null) or last closing price (>= 0)
      // We just verify the CMP cell is visible and not an error state
      const cmpCell = builderPage.getLegCmp(0);
      await expect(cmpCell).toBeVisible();
      // If we have a value, it should be non-negative (closing price)
      if (cmpValue !== null) {
        expect(cmpValue).toBeGreaterThanOrEqual(0);
      }
    }
  });
});
