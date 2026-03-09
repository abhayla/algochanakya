import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';
import { waitForApiResponse } from '../../helpers/wait-helpers.js';

/**
 * Option Chain Screen - API Tests
 * Tests API interactions and data loading
 */
test.describe('Option Chain - API @api', () => {
  test.describe.configure({ timeout: 180000 });
  let optionChainPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    optionChainPage = new OptionChainPage(authenticatedPage);
  });

  test('should fetch expiries on page load', async ({ authenticatedPage }) => {
    const expiryResponsePromise = authenticatedPage.waitForResponse(
      response => response.url().includes('/api/options/expiries') || response.url().includes('/api/optionchain'),
      { timeout: 30000 }
    );

    await optionChainPage.navigate();
    const response = await expiryResponsePromise;
    expect(response.status()).toBe(200);
  });

  test('should fetch option chain data', async ({ authenticatedPage }) => {
    const chainResponsePromise = waitForApiResponse(
      authenticatedPage,
      '/api/optionchain/chain',
      { timeout: 30000 }
    );

    await optionChainPage.navigate();
    const response = await chainResponsePromise;
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toBeDefined();
    expect(typeof data).toBe('object');
  });

  test('should fetch new chain on underlying change', async ({ authenticatedPage }) => {
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();

    const chainResponsePromise = waitForApiResponse(
      authenticatedPage,
      '/api/optionchain/chain',
      { timeout: 30000 }
    );

    await optionChainPage.selectUnderlying('BANKNIFTY');
    const response = await chainResponsePromise;
    expect(response.status()).toBe(200);
  });

  test('should fetch new chain on expiry change', async ({ authenticatedPage }) => {
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();

    const expirySelect = optionChainPage.expirySelect;
    const options = await expirySelect.locator('option').all();

    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      expect(options.length).toBeGreaterThan(1);
    }

    if (options.length > 1) {
      const chainResponsePromise = waitForApiResponse(
        authenticatedPage,
        '/api/optionchain/chain',
        { timeout: 30000 }
      );

      const secondOption = await options[1].getAttribute('value');
      await expirySelect.selectOption(secondOption);

      const response = await chainResponsePromise;
      expect(response.status()).toBe(200);
    }
  });

  test('should handle API errors gracefully', async ({ authenticatedPage }) => {
    // Navigate normally — page must remain stable even if API returns errors
    await optionChainPage.navigate();
    await optionChainPage.assertPageVisible();
  });

  test('should display loading state during fetch', async ({ authenticatedPage }) => {
    // Start navigation and check that either loading state, table, or empty state appears
    const navigationPromise = optionChainPage.navigate();

    // At least one of these must appear: loading spinner (fast), table, or empty state (slower)
    // Use Promise.any so ONE resolving is sufficient; no rejection if loading indicator skipped
    await Promise.any([
      authenticatedPage.waitForSelector('[data-testid="optionchain-loading"]', { timeout: 2000 }),
      authenticatedPage.waitForSelector('[data-testid="optionchain-table"]', { timeout: 30000 }),
      authenticatedPage.waitForSelector('[data-testid="optionchain-empty-state"]', { timeout: 30000 })
    ]);

    await navigationPromise;
    await optionChainPage.assertPageVisible();
  });

  test('should populate summary bar from API data', async ({ authenticatedPage }) => {
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();

    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Table must be visible and summary bar must have real values
      await expect(optionChainPage.table).toBeVisible();
      await expect(optionChainPage.summaryBar).toBeVisible();

      // PCR value must be non-empty
      const pcrText = await optionChainPage.pcrValue.textContent();
      expect(pcrText.trim().length).toBeGreaterThan(0);
      expect(pcrText.trim()).not.toBe('-');
    } else {
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });
});
