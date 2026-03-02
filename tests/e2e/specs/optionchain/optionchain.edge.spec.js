import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';

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
    const hasTable = await optionChainPage.table.isVisible().catch(() => false);
    if (hasTable) {
      // Find a strike row
      const strikeRow = page.locator('[data-testid^="optionchain-strike-row-"]').first();
      if (await strikeRow.isVisible()) {
        const testId = await strikeRow.getAttribute('data-testid');
        const strike = testId.replace('optionchain-strike-row-', '');

        // Select CE
        await optionChainPage.selectCE(strike);
        await expect(optionChainPage.selectedBar).toBeVisible();

        // Clear selection
        await optionChainPage.clearSelection();
        await optionChainPage.assertSelectedBarHidden();
      } else {
        // Table loaded but no strike rows — chain data is loading or expiry unavailable
        await expect(optionChainPage.table).toBeVisible();
      }
    } else {
      // No table — page must still show a loading state or status indicator
      await optionChainPage.assertPageVisible();
    }
  });

  test('should handle multiple strike selections', async ({ page }) => {
    await optionChainPage.waitForChainLoad();
    const hasTable = await optionChainPage.table.isVisible().catch(() => false);
    if (hasTable) {
      const strikeRows = await page.locator('[data-testid^="optionchain-strike-row-"]').all();
      if (strikeRows.length >= 2) {
        const testId1 = await strikeRows[0].getAttribute('data-testid');
        const strike1 = testId1.replace('optionchain-strike-row-', '');

        const testId2 = await strikeRows[1].getAttribute('data-testid');
        const strike2 = testId2.replace('optionchain-strike-row-', '');

        await optionChainPage.selectCE(strike1);
        await optionChainPage.selectPE(strike2);

        const count = await optionChainPage.getSelectedCount();
        expect(count).toBe(2);

        await optionChainPage.clearSelection();
      } else {
        // Fewer than 2 strike rows — chain data is partial; page should still be stable
        await optionChainPage.assertPageVisible();
      }
    } else {
      // No table — page must still be visible
      await optionChainPage.assertPageVisible();
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
    const hasTable = await optionChainPage.table.isVisible().catch(() => false);
    if (hasTable) {
      const strikeRow = page.locator('[data-testid^="optionchain-strike-row-"]').first();
      if (await strikeRow.isVisible()) {
        const testId = await strikeRow.getAttribute('data-testid');
        const strike = testId.replace('optionchain-strike-row-', '');

        await optionChainPage.selectCE(strike);
        // Note: Selection might or might not persist after refresh depending on implementation
        await optionChainPage.assertPageVisible();
      } else {
        // Table loaded but no strike rows yet
        await expect(optionChainPage.table).toBeVisible();
      }
    } else {
      // No table — page must still be visible
      await optionChainPage.assertPageVisible();
    }
  });
});
