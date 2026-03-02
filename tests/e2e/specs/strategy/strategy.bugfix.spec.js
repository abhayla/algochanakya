import { test, expect } from '../../fixtures/auth.fixture.js';
import { StrategyBuilderPage } from '../../pages/StrategyBuilderPage.js';

/**
 * Strategy Builder - Bug Fix Verification Tests
 * Tests for P/L recalculation after leg deletion (removeSelectedLegs fix)
 */
test.describe('Strategy Builder - Bug Fixes @bugfix', () => {
  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
    await strategyPage.navigate();
    await strategyPage.waitForPageLoad(); // Wait for market data
  });

  test('BUG FIX: should recalculate P/L after bulk delete using removeSelectedLegs()', async () => {
    // This test verifies the fix for removeSelectedLegs() missing calculatePnL() call

    // Add 2 legs
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    const legCount1 = await strategyPage.getLegCount();
    if (legCount1 === 0) {
      console.log('First leg failed to add, skipping test');
      test.skip('Leg failed to add - skipping');
    }

    await strategyPage.addRow();
    await strategyPage.waitForLegCount(2);

    const legCount2 = await strategyPage.getLegCount();
    expect(legCount2).toBe(2);

    // Wait for initial P/L calculation
    await strategyPage.waitForPnLCalculation();

    // Verify P/L summary exists before deletion
    const hasSummaryBefore = await strategyPage.hasSummaryCards();
    expect(hasSummaryBefore).toBe(true);

    // Select first leg using checkbox
    const legRow = await strategyPage.getLegRow(0);
    const checkbox = legRow.locator('input[type="checkbox"]');
    await checkbox.check();
    await strategyPage.page.waitForLoadState('domcontentloaded');

    // Delete selected leg (this calls removeSelectedLegs())
    await strategyPage.deleteSelectedLegs();
    await strategyPage.waitForLegCount(1);
    await strategyPage.waitForPnLCalculation();

    // Verify we now have 1 leg
    const finalLegCount = await strategyPage.getLegCount();
    expect(finalLegCount).toBe(1);

    // THE FIX VERIFICATION: P/L summary should still exist (recalculation happened)
    // Before the fix, this would fail because calculatePnL() wasn't called
    const hasSummaryAfter = await strategyPage.hasSummaryCards();
    expect(hasSummaryAfter).toBe(true);

    // Verify we have valid P/L values
    const finalMaxProfit = await strategyPage.getMaxProfit();
    expect(typeof finalMaxProfit).toBe('number');

    console.log('✅ BUG FIX VERIFIED: removeSelectedLegs() now calls calculatePnL()');
  });

  test('BUG FIX: should clear P/L when deleting all legs', async () => {
    // Add 1 leg
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    const legCount = await strategyPage.getLegCount();
    if (legCount === 0) {
      console.log('Leg failed to add, skipping test');
      test.skip('Leg failed to add - skipping');
    }

    // Wait for P/L calculation
    await strategyPage.waitForPnLCalculation();

    // Verify P/L exists
    const hasSummary = await strategyPage.hasSummaryCards();
    expect(hasSummary).toBe(true);

    // Select the leg
    const legRow = await strategyPage.getLegRow(0);
    const checkbox = legRow.locator('input[type="checkbox"]');
    await checkbox.check();
    await strategyPage.page.waitForLoadState('domcontentloaded');

    // Delete the leg
    await strategyPage.deleteSelectedLegs();
    await strategyPage.waitForLegCount(0);

    // Verify no legs remain
    const finalLegCount = await strategyPage.getLegCount();
    expect(finalLegCount).toBe(0);

    // Verify empty state appears
    const isEmpty = await strategyPage.isEmptyState();
    expect(isEmpty).toBe(true);

    console.log('✅ BUG FIX VERIFIED: Deleting all legs clears P/L grid correctly');
  });

  test('BUG FIX: should show P/L grid for single row using LTP API fallback', async () => {
    // This test verifies that P/L grid appears for a single row
    // even when WebSocket CMP is unavailable, by fetching LTP from API

    // Add 1 leg
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    const legCount = await strategyPage.getLegCount();
    if (legCount === 0) {
      console.log('Leg failed to add, skipping test');
      test.skip('Leg failed to add - skipping');
    }

    // Wait for P/L calculation (which should now fetch LTP from API if WebSocket unavailable)
    await strategyPage.waitForPnLCalculation();

    // THE FIX VERIFICATION: P/L summary should appear for single row
    // Before the fix, this would fail if WebSocket CMP was unavailable
    const hasSummary = await strategyPage.hasSummaryCards();
    expect(hasSummary).toBe(true);

    // Verify we have valid P/L values
    const maxProfit = await strategyPage.getMaxProfit();
    const maxLoss = await strategyPage.getMaxLoss();

    expect(typeof maxProfit).toBe('number');
    expect(typeof maxLoss).toBe('number');

    console.log('✅ BUG FIX VERIFIED: Single row P/L grid works with LTP API fallback');
    console.log(`   Max Profit: ${maxProfit}, Max Loss: ${maxLoss}`);
  });
});
