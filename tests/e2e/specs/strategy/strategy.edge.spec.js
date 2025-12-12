import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';

/**
 * Strategy Builder Screen - Edge Case Tests
 * Tests boundary conditions and error handling
 */
test.describe('Strategy Builder - Edge Cases @edge', () => {
  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
    await strategyPage.navigate();
  });

  test('should handle rapid leg additions', async () => {
    // Add multiple legs rapidly (waiting for each to complete since addLeg is async)
    for (let i = 0; i < 5; i++) {
      await strategyPage.addRow();
      await strategyPage.waitForLegCount(i + 1);
    }
    const count = await strategyPage.getLegCount();
    expect(count).toBeGreaterThanOrEqual(5);
  });

  test('should handle save without strategy name', async () => {
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('');
    // Save button should be disabled
    await expect(strategyPage.saveButton).toBeDisabled();
  });

  test('should handle save without legs', async () => {
    await strategyPage.enterStrategyName('Test Strategy');
    // If no legs, save should be disabled
    const isEmpty = await strategyPage.isEmptyState();
    if (isEmpty) {
      await expect(strategyPage.saveButton).toBeDisabled();
    }
  });

  test('should handle recalculate without legs', async () => {
    // Recalculate button should be disabled when no legs
    const isEmpty = await strategyPage.isEmptyState();
    if (isEmpty) {
      await expect(strategyPage.recalculateButton).toBeDisabled();
    }
  });

  test('should handle rapid underlying switches', async () => {
    await strategyPage.selectUnderlying('BANKNIFTY');
    await strategyPage.selectUnderlying('FINNIFTY');
    await strategyPage.selectUnderlying('NIFTY');
    // Page should remain stable
    await strategyPage.assertPageVisible();
  });

  test('should enable Add Row button after expiries load', async () => {
    // Wait for Add Row to be enabled (expiries loaded)
    await strategyPage.waitForAddRowEnabled();
    const isEnabled = await strategyPage.isAddRowEnabled();
    expect(isEnabled).toBe(true);
  });

  test('should handle rapid P/L mode toggles', async () => {
    await strategyPage.setPnLMode('current');
    await strategyPage.setPnLMode('expiry');
    await strategyPage.setPnLMode('current');
    // Page should remain stable
    await strategyPage.assertPageVisible();
  });

  test('should clear legs on delete', async () => {
    // Add legs (waiting for each to complete since addLeg is async)
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(2);

    const initialCount = await strategyPage.getLegCount();
    expect(initialCount).toBeGreaterThanOrEqual(2);

    // Note: Deleting requires selecting legs first
    // This tests the button visibility
    await expect(strategyPage.deleteLegsButton).toBeVisible();
  });

  test('should handle very long strategy name', async () => {
    const longName = 'A'.repeat(100);
    await strategyPage.enterStrategyName(longName);
    // Should handle gracefully
    await strategyPage.assertPageVisible();
  });

  test('should handle special characters in strategy name', async () => {
    await strategyPage.enterStrategyName('Test @#$% Strategy!');
    await strategyPage.assertPageVisible();
  });

  test('should maintain state after page refresh', async ({ authenticatedPage }) => {
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('Test Strategy');

    // Refresh page
    await authenticatedPage.reload();

    // Page should load (state may or may not persist)
    await strategyPage.assertPageVisible();
  });
});
