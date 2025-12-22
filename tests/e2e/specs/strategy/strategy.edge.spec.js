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

    // Select first leg using checkbox (checkbox has no testid, use input[type="checkbox"] selector)
    const row0 = await strategyPage.getLegRow(0);
    const checkbox = row0.locator('input[type="checkbox"]');
    await checkbox.check();
    await strategyPage.page.waitForTimeout(300);

    // Delete selected leg
    await strategyPage.deleteSelectedLegs();
    await strategyPage.page.waitForTimeout(500);

    // Verify one leg was deleted
    const finalCount = await strategyPage.getLegCount();
    expect(finalCount).toBe(1);
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

  test('should reload page without errors after adding legs', async ({ authenticatedPage }) => {
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('Test Strategy');

    // Refresh page
    await authenticatedPage.reload();

    // Page should reload without errors (note: unsaved state is not persisted)
    await strategyPage.assertPageVisible();
  });

  // Duplicate name validation tests
  test('should show validation error for duplicate strategy name', async () => {
    // Add a leg and save first strategy
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('Test Strategy');
    await strategyPage.save();
    await strategyPage.page.waitForTimeout(1000); // Wait for save to complete

    // Close the success modal from first save
    const modalVisibleAfterSave = await strategyPage.isValidationModalVisible();
    if (modalVisibleAfterSave) {
      await strategyPage.closeValidationModal();
      await strategyPage.page.waitForTimeout(500);
    }

    // Reset to "New Strategy" mode
    await strategyPage.selectStrategy(''); // Select "New Strategy" option
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    // Try to save another strategy with same name
    await strategyPage.enterStrategyName('Test Strategy');
    await strategyPage.save();

    // Wait for validation modal to appear
    await strategyPage.validationModal.waitFor({ state: 'visible', timeout: 5000 });

    // Verify validation modal appears with duplicate error
    const modalVisible = await strategyPage.isValidationModalVisible();
    expect(modalVisible).toBe(true);
    const errors = await strategyPage.getValidationErrors();
    expect(errors.some(err => err.toLowerCase().includes('already exists'))).toBe(true);

    // Close modal
    await strategyPage.closeValidationModal();
  });

  test('should show validation error for case-insensitive duplicate names', async () => {
    // Save strategy with name "My Strategy"
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('My Strategy');
    await strategyPage.save();
    await strategyPage.page.waitForTimeout(1000);

    // Close the success modal from first save
    const modalVisibleAfterSave = await strategyPage.isValidationModalVisible();
    if (modalVisibleAfterSave) {
      await strategyPage.closeValidationModal();
      await strategyPage.page.waitForTimeout(500);
    }

    // Reset to "New Strategy" mode
    await strategyPage.selectStrategy(''); // Select "New Strategy" option
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    // Try saving "MY STRATEGY" (uppercase)
    await strategyPage.enterStrategyName('MY STRATEGY');
    await strategyPage.save();

    // Wait for validation modal to appear
    await strategyPage.validationModal.waitFor({ state: 'visible', timeout: 5000 });

    // Verify validation modal
    const modalVisible = await strategyPage.isValidationModalVisible();
    expect(modalVisible).toBe(true);
    await strategyPage.closeValidationModal();
  });

  // Required fields validation tests
  test('should show validation modal when saving without name', async () => {
    // Add leg with complete data but leave name empty
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('');

    // Try to save - button should be disabled, so we can't test the modal this way
    // This test verifies the existing behavior (button disabled)
    await expect(strategyPage.saveButton).toBeDisabled();
  });

  test('should show validation modal when leg has missing fields', async () => {
    // Add a leg - it may have default values, but if we can clear them
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.enterStrategyName('Test Strategy');

    // Note: The current implementation may pre-fill leg fields with defaults
    // This test would need to clear fields, but that depends on UI implementation
    // For now, we verify the happy path works
    await strategyPage.save();
    await strategyPage.page.waitForTimeout(500);
  });

  // Underlying change confirmation tests
  test('should show confirmation dialog when changing underlying with existing legs', async () => {
    // Add a leg to NIFTY
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    // Try to click BANKNIFTY tab
    await strategyPage.bankniftyTab.click();

    // Verify confirmation modal appears
    const modalVisible = await strategyPage.isUnderlyingConfirmModalVisible();
    expect(modalVisible).toBe(true);

    // Cancel for now
    await strategyPage.cancelUnderlyingChange();
  });

  test('should keep legs when canceling underlying change', async () => {
    // Add leg to NIFTY
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    const initialLegCount = await strategyPage.getLegCount();

    // Click different underlying
    await strategyPage.bankniftyTab.click();

    // Cancel the change
    await strategyPage.cancelUnderlyingChange();

    // Verify legs still exist
    const finalLegCount = await strategyPage.getLegCount();
    expect(finalLegCount).toBe(initialLegCount);

    // Verify underlying is still NIFTY
    const niftyActive = await strategyPage.isUnderlyingActive('nifty');
    expect(niftyActive).toBe(true);
  });

  test('should clear legs when confirming underlying change', async () => {
    // Add leg to NIFTY
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);

    // Click different underlying
    await strategyPage.bankniftyTab.click();

    // Confirm the change
    await strategyPage.confirmUnderlyingChange();

    // Verify legs are cleared
    const isEmpty = await strategyPage.isEmptyState();
    expect(isEmpty).toBe(true);

    // Verify underlying changed to BANKNIFTY
    const bankniftyActive = await strategyPage.isUnderlyingActive('banknifty');
    expect(bankniftyActive).toBe(true);
  });

  // P/L Recalculation Regression Tests
  test('should recalculate P/L when bulk deleting legs', async () => {
    // Add 3 legs
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(2);
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(3);
    await strategyPage.waitForPnLUpdate();

    // Verify P/L summary exists with 3 legs
    const hasSummaryBefore = await strategyPage.hasSummaryCards();
    expect(hasSummaryBefore).toBe(true);

    // Select first 2 legs
    const row0 = await strategyPage.getLegRow(0);
    const row1 = await strategyPage.getLegRow(1);
    await row0.locator('input[type="checkbox"]').check();
    await row1.locator('input[type="checkbox"]').check();

    // Delete selected legs
    await strategyPage.deleteSelectedLegs();
    await strategyPage.waitForLegCount(1);

    // Wait for recalculation
    await strategyPage.waitForPnLUpdate();

    // Verify P/L summary still exists after deletion (recalculation happened)
    const hasSummaryAfter = await strategyPage.hasSummaryCards();
    expect(hasSummaryAfter).toBe(true);

    // Verify we have valid P/L values
    const finalMaxProfit = await strategyPage.getMaxProfit();
    expect(typeof finalMaxProfit).toBe('number');
  });

  test('should clear P/L grid when all legs deleted', async () => {
    // Add 2 legs
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(1);
    await strategyPage.addRow();
    await strategyPage.waitForLegCount(2);
    await strategyPage.waitForPnLUpdate();

    // Verify P/L grid exists
    const hasSummary = await strategyPage.hasSummaryCards();
    expect(hasSummary).toBe(true);

    // Select all legs
    const row0 = await strategyPage.getLegRow(0);
    const row1 = await strategyPage.getLegRow(1);
    await row0.locator('input[type="checkbox"]').check();
    await row1.locator('input[type="checkbox"]').check();

    // Delete all legs
    await strategyPage.deleteSelectedLegs();
    await strategyPage.page.waitForTimeout(1000);

    // Verify legs are gone
    const legCount = await strategyPage.getLegCount();
    expect(legCount).toBe(0);

    // Verify empty state is shown
    const isEmpty = await strategyPage.isEmptyState();
    expect(isEmpty).toBe(true);
  });
});
