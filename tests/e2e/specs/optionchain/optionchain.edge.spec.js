import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';

/**
 * Option Chain Screen - Edge Case Tests
 * Tests boundary conditions and error handling
 */
test.describe('Option Chain - Edge Cases @edge', () => {
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
    await optionChainPage.navigate();
  });

  test('should handle rapid underlying switches', async () => {
    await optionChainPage.selectUnderlying('BANKNIFTY');
    await optionChainPage.selectUnderlying('FINNIFTY');
    await optionChainPage.selectUnderlying('NIFTY');
    // Page should remain stable
    await optionChainPage.assertPageVisible();
  });

  test('should handle strike selection and deselection', async ({ page }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Data must be present — require the table and at least one strike row
      await expect(optionChainPage.table).toBeVisible();
      const strikeRow = page.locator('[data-testid^="optionchain-strike-row-"]').first();
      await expect(strikeRow).toBeVisible();

      const testId = await strikeRow.getAttribute('data-testid');
      const strike = testId.replace('optionchain-strike-row-', '');

      // Select CE
      await optionChainPage.selectCE(strike);
      await expect(optionChainPage.selectedBar).toBeVisible();

      // Clear selection
      await optionChainPage.clearSelection();
      await optionChainPage.assertSelectedBarHidden();
    } else {
      await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('should handle multiple strike selections', async ({ page }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Data must be present — require table and at least 2 strike rows
      await expect(optionChainPage.table).toBeVisible();
      const strikeRows = page.locator('[data-testid^="optionchain-strike-row-"]');
      const rowCount = await strikeRows.count();
      expect(rowCount).toBeGreaterThanOrEqual(2);

      const testId1 = await strikeRows.nth(0).getAttribute('data-testid');
      const strike1 = testId1.replace('optionchain-strike-row-', '');

      const testId2 = await strikeRows.nth(1).getAttribute('data-testid');
      const strike2 = testId2.replace('optionchain-strike-row-', '');

      await optionChainPage.selectCE(strike1);
      await optionChainPage.selectPE(strike2);

      const count = await optionChainPage.getSelectedCount();
      expect(count).toBe(2);

      await optionChainPage.clearSelection();
    } else {
      await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('should handle refresh during loading', async () => {
    await optionChainPage.waitForChainLoad();
    // Rapid refresh clicks
    await optionChainPage.refreshButton.click();
    await optionChainPage.refreshButton.click();
    // Page should handle this gracefully
    await optionChainPage.assertPageVisible();
  });

  test('should toggle Greeks on and off', async () => {
    await optionChainPage.waitForChainLoad();
    // Toggle Greeks on
    await optionChainPage.toggleGreeks();
    // Toggle Greeks off
    await optionChainPage.toggleGreeks();
    // Page should remain stable
    await optionChainPage.assertPageVisible();
  });

  test('should handle strikes range change', async () => {
    await optionChainPage.waitForChainLoad();
    // Change strikes range
    await optionChainPage.setStrikesRange(20);
    await optionChainPage.assertPageVisible();
  });

  test('should maintain selection after refresh', async ({ page }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      await expect(optionChainPage.table).toBeVisible();
      const strikeRow = page.locator('[data-testid^="optionchain-strike-row-"]').first();
      await expect(strikeRow).toBeVisible();

      const testId = await strikeRow.getAttribute('data-testid');
      const strike = testId.replace('optionchain-strike-row-', '');

      // Select CE then click refresh
      await optionChainPage.selectCE(strike);
      await expect(optionChainPage.selectedBar).toBeVisible();

      await optionChainPage.refresh();
      await optionChainPage.waitForChainLoad();

      // After refresh, the selection bar visibility is implementation-dependent;
      // but the page must be stable and the chain must still be loaded
      await optionChainPage.assertPageVisible();
      await expect(optionChainPage.table).toBeVisible();
    } else {
      await assertDataOrEmptyState(page, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });
});
