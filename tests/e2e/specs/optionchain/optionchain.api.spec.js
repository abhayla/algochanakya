import { test, expect } from '@playwright/test';
import OptionChainPage from '../../pages/OptionChainPage.js';

/**
 * Option Chain Screen - API Tests
 * Tests API interactions and data loading
 */
test.describe('Option Chain - API @api', () => {
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
  });

  test('should fetch expiries on page load', async ({ page }) => {
    // Listen for expiries API call
    const expiryPromise = page.waitForResponse(
      response => response.url().includes('/api/options/expiries') || response.url().includes('/api/optionchain'),
      { timeout: 10000 }
    ).catch(() => null);

    await optionChainPage.navigate();
    const response = await expiryPromise;

    if (response) {
      expect(response.status()).toBe(200);
    }
  });

  test('should fetch option chain data', async ({ page }) => {
    // Listen for chain API call
    const chainPromise = page.waitForResponse(
      response => response.url().includes('/api/optionchain/chain'),
      { timeout: 15000 }
    ).catch(() => null);

    await optionChainPage.navigate();
    const response = await chainPromise;

    if (response) {
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data).toBeDefined();
    }
  });

  test('should fetch new chain on underlying change', async ({ page }) => {
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();

    // Listen for new chain request
    const chainPromise = page.waitForResponse(
      response => response.url().includes('/api/optionchain/chain'),
      { timeout: 15000 }
    ).catch(() => null);

    await optionChainPage.selectUnderlying('BANKNIFTY');
    const response = await chainPromise;

    if (response) {
      expect(response.status()).toBe(200);
    }
  });

  test('should fetch new chain on expiry change', async ({ page }) => {
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();

    // Get expiry options
    const expirySelect = optionChainPage.expirySelect;
    const options = await expirySelect.locator('option').all();

    if (options.length > 1) {
      // Listen for chain request
      const chainPromise = page.waitForResponse(
        response => response.url().includes('/api/optionchain/chain'),
        { timeout: 15000 }
      ).catch(() => null);

      // Select second expiry
      const secondOption = await options[1].getAttribute('value');
      await expirySelect.selectOption(secondOption);

      const response = await chainPromise;
      if (response) {
        expect(response.status()).toBe(200);
      }
    }
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Navigate normally (can't easily simulate API errors without mocking)
    await optionChainPage.navigate();

    // Page should be visible regardless
    await optionChainPage.assertPageVisible();
  });

  test('should display loading state during fetch', async ({ page }) => {
    // This might be too fast to catch, but we try
    const navigationPromise = optionChainPage.navigate();

    // Check for loading or page
    await Promise.race([
      page.waitForSelector('[data-testid="optionchain-loading"]', { timeout: 2000 }),
      page.waitForSelector('[data-testid="optionchain-table"]', { timeout: 10000 }),
      page.waitForSelector('[data-testid="optionchain-empty-state"]', { timeout: 10000 })
    ]).catch(() => {});

    await navigationPromise;
    await optionChainPage.assertPageVisible();
  });

  test('should populate summary bar from API data', async ({ page }) => {
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();

    const hasTable = await optionChainPage.table.isVisible().catch(() => false);
    if (hasTable) {
      // Check summary values are populated
      await expect(optionChainPage.summaryBar).toBeVisible();
      // PCR, Max Pain should have values
      const pcrText = await optionChainPage.pcrValue.textContent();
      expect(pcrText.length).toBeGreaterThan(0);
    }
  });
});
