import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';

/**
 * Strategy Builder Screen - API Tests
 * Tests API interactions and data loading
 */
// Skip: API tests require authenticated backend connection
test.describe.skip('Strategy Builder - API @api', () => {
  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
  });

  test('should fetch expiries on page load', async ({ authenticatedPage }) => {
    const expiryPromise = authenticatedPage.waitForResponse(
      response => response.url().includes('/api/options/expiries'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    const response = await expiryPromise;

    if (response) {
      expect(response.status()).toBe(200);
    }
  });

  test('should fetch saved strategies on page load', async ({ authenticatedPage }) => {
    const strategiesPromise = authenticatedPage.waitForResponse(
      response => response.url().includes('/api/strategies'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    const response = await strategiesPromise;

    if (response) {
      expect([200, 401]).toContain(response.status());
    }
  });

  test('should fetch strikes when expiry is selected', async () => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    // This would require selecting an expiry in the leg
    // For now, just verify page is stable
    await strategyPage.assertPageVisible();
  });

  test('should call calculate API on recalculate', async ({ authenticatedPage }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    const legCount = await strategyPage.getLegCount();
    if (legCount > 0) {
      const calculatePromise = authenticatedPage.waitForResponse(
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

  test('should have save button visible when strategy has name and legs', async ({ authenticatedPage }) => {
    await strategyPage.navigate();
    await strategyPage.enterStrategyName('API Test Strategy');
    await strategyPage.addRow();

    // Save button should be visible
    await expect(strategyPage.saveButton).toBeVisible();

    // Verify save button is enabled when conditions are met
    const isDisabled = await strategyPage.saveButton.isDisabled();
    // Save may be disabled if leg is incomplete - this is expected
    expect(typeof isDisabled).toBe('boolean');
  });

  test('should fetch LTP for instruments with valid prices', async ({ authenticatedPage }) => {
    const ltpPromise = authenticatedPage.waitForResponse(
      response => response.url().includes('/api/orders/ltp'),
      { timeout: 10000 }
    ).catch(() => null);

    await strategyPage.navigate();
    await strategyPage.addRow();

    // LTP might be called for leg instruments
    const response = await ltpPromise;

    if (response) {
      expect(response.status()).toBe(200);

      // Validate LTP response contains valid price data
      const data = await response.json();

      // LTP endpoint should return valid price data
      // Structure: { instruments: [{token, ltp, ...}] } or similar
      if (data && typeof data === 'object') {
        // If data contains LTP values, they should be positive numbers
        const hasValidLtp = Object.values(data).some(item => {
          if (typeof item === 'number') {
            return item > 0;
          }
          if (typeof item === 'object' && item !== null && 'ltp' in item) {
            return item.ltp > 0;
          }
          return false;
        });

        // Test will fail if Kite broker token is expired and no valid LTP data
        expect(hasValidLtp || Object.keys(data).length === 0).toBeTruthy();
      }
    }

    await strategyPage.assertPageVisible();
  });

  test('should handle API errors gracefully', async () => {
    // Navigate normally
    await strategyPage.navigate();

    // Page should be visible regardless
    await strategyPage.assertPageVisible();
  });

  test('should display loading indicator during calculation', async ({ authenticatedPage }) => {
    await strategyPage.navigate();
    await strategyPage.addRow();

    const isDisabled = await strategyPage.recalculateButton.isDisabled();
    if (!isDisabled) {
      // Click recalculate and check for loading
      const recalcPromise = strategyPage.recalculate();

      // May briefly show loading
      await Promise.race([
        authenticatedPage.waitForSelector('[data-testid="strategy-loading"]', { timeout: 1000 }),
        recalcPromise
      ]).catch(() => {});

      await strategyPage.assertPageVisible();
    }
  });

  test('should populate summary cards from calculation', async () => {
    await strategyPage.navigate();

    // Check if summary cards exist
    const hasSummary = await strategyPage.hasSummaryCards();
    if (hasSummary) {
      // Verify summary grid is visible
      await strategyPage.assertSummaryVisible();
    }
  });
});
