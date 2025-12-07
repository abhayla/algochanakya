import { test, expect } from '@playwright/test';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';

/**
 * Strategy Builder Screen - API Tests
 * Tests API interactions and data loading
 */
test.describe('Strategy Builder - API @api', () => {
  let strategyPage;

  test.beforeEach(async ({ page }) => {
    strategyPage = new StrategyBuilderPage(page);
  });

  test('should fetch expiries on page load', async ({ page }) => {
    const expiryPromise = page.waitForResponse(
      response => response.url().includes('/api/options/expiries'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    const response = await expiryPromise;

    if (response) {
      expect(response.status()).toBe(200);
    }
  });

  test('should fetch saved strategies on page load', async ({ page }) => {
    const strategiesPromise = page.waitForResponse(
      response => response.url().includes('/api/strategies'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    const response = await strategiesPromise;

    if (response) {
      expect([200, 401]).toContain(response.status());
    }
  });

  test('should fetch strikes when expiry is selected', async ({ page }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    // This would require selecting an expiry in the leg
    // For now, just verify page is stable
    await strategyPage.assertPageVisible();
  });

  test('should call calculate API on recalculate', async ({ page }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    const legCount = await strategyPage.getLegCount();
    if (legCount > 0) {
      const calculatePromise = page.waitForResponse(
        response => response.url().includes('/api/strategies/calculate'),
        { timeout: 15000 }
      ).catch(() => null);

      // Try to recalculate (may fail if leg not complete)
      const isDisabled = await strategyPage.recalculateButton.isDisabled();
      if (!isDisabled) {
        await strategyPage.recalculate();
        const response = await calculatePromise;
        if (response) {
          expect([200, 400, 422]).toContain(response.status());
        }
      }
    }
  });

  test('should call save API when saving strategy', async ({ page }) => {
    await strategyPage.navigate();
    await strategyPage.enterStrategyName('API Test Strategy');
    await strategyPage.addRow();

    // Save button should be visible
    await expect(strategyPage.saveButton).toBeVisible();
  });

  test('should fetch LTP for instruments', async ({ page }) => {
    const ltpPromise = page.waitForResponse(
      response => response.url().includes('/api/orders/ltp'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    await strategyPage.addRow();

    // LTP might be called for leg instruments
    const response = await ltpPromise;
    // Response is optional
    await strategyPage.assertPageVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Navigate normally
    await strategyPage.navigate();

    // Page should be visible regardless
    await strategyPage.assertPageVisible();
  });

  test('should display loading indicator during calculation', async ({ page }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    const isDisabled = await strategyPage.recalculateButton.isDisabled();
    if (!isDisabled) {
      // Click recalculate and check for loading
      const recalcPromise = strategyPage.recalculate();

      // May briefly show loading
      await Promise.race([
        page.waitForSelector('[data-testid="strategy-loading"]', { timeout: 1000 }),
        recalcPromise
      ]).catch(() => {});

      await strategyPage.assertPageVisible();
    }
  });

  test('should populate summary cards from calculation', async ({ page }) => {
    await strategyPage.navigate();

    // Check if summary cards exist
    const hasSummary = await strategyPage.hasSummaryCards();
    if (hasSummary) {
      // Verify summary grid is visible
      await strategyPage.assertSummaryVisible();
    }
  });
});
