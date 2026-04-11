/**
 * Header Index Prices Tests
 *
 * Tests for the NIFTY 50 and SENSEX index price display in the header.
 * Verifies UI structure always; price range assertions only when live data
 * is available (market open with active WebSocket).
 *
 * Note: These tests require authentication - use auth fixture.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { KiteHeaderPage } from '../../pages/KiteHeaderPage.js';

test.describe('Header Index Prices @happy', () => {
  test.describe.configure({ mode: 'serial' });

  let headerPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    headerPage = new KiteHeaderPage(authenticatedPage);
    await headerPage.navigate();
    await headerPage.waitForLoad();
  });

  test('index prices container is visible', async () => {
    await expect(headerPage.indexPricesContainer).toBeVisible();
  });

  test('NIFTY 50 item is displayed', async () => {
    await expect(headerPage.nifty50Item).toBeVisible();
    await expect(headerPage.nifty50Item).toContainText('NIFTY 50');
  });

  test('NIFTY 50 shows a price or placeholder', async ({ authenticatedPage }) => {
    const hasLiveData = await headerPage.waitForIndexPrices();

    const niftyText = await headerPage.nifty50Value.textContent();

    if (hasLiveData) {
      // Live prices: validate range (NIFTY 50 typically 15,000–30,000)
      const price = parseFloat(niftyText.replace(/,/g, ''));
      expect(price).toBeGreaterThan(10000);
      expect(price).toBeLessThan(50000);

      await authenticatedPage.screenshot({
        path: 'test-results/screenshots/nifty50-price.png',
        clip: { x: 0, y: 0, width: 600, height: 60 }
      });
    } else {
      // Market closed: element must show placeholder '--' or a valid number
      expect(niftyText.trim()).toMatch(/^(--)|([\d,]+(\.\d+)?)$/);
    }
  });

  test('SENSEX item is displayed', async () => {
    await expect(headerPage.sensexItem).toBeVisible();
    await expect(headerPage.sensexItem).toContainText('SENSEX');
  });

  test('SENSEX shows a price or placeholder', async ({ authenticatedPage }) => {
    const hasLiveData = await headerPage.waitForIndexPrices();

    const sensexText = await headerPage.sensexValue.textContent();

    if (hasLiveData) {
      // Live prices: validate range (SENSEX typically 60,000–90,000)
      const price = parseFloat(sensexText.replace(/,/g, ''));
      expect(price).toBeGreaterThan(50000);
      expect(price).toBeLessThan(100000);

      await authenticatedPage.screenshot({
        path: 'test-results/screenshots/sensex-price.png',
        clip: { x: 0, y: 0, width: 600, height: 60 }
      });
    } else {
      // Market closed: element must show placeholder '--' or a valid number
      expect(sensexText.trim()).toMatch(/^(--)|([\d,]+(\.\d+)?)$/);
    }
  });

  test('prices use Indian number format or show placeholder', async () => {
    const hasLiveData = await headerPage.waitForIndexPrices();

    const niftyText = await headerPage.nifty50Value.textContent();
    const sensexText = await headerPage.sensexValue.textContent();

    if (hasLiveData) {
      // Live: expect Indian comma-formatted numbers
      expect(niftyText).toMatch(/[\d,]+(\.\d+)?/);
      expect(sensexText).toMatch(/[\d,]+(\.\d+)?/);
      expect(niftyText).toContain(',');
      expect(sensexText).toContain(',');
    } else {
      // Offline: expect '--' placeholder
      expect(niftyText.trim()).toBe('--');
      expect(sensexText.trim()).toBe('--');
    }
  });

  test('index prices remain visible after page navigation', async ({ authenticatedPage }) => {
    // Navigate to another page — verify header persists
    await authenticatedPage.goto('/optionchain');
    await authenticatedPage.waitForLoadState('domcontentloaded');

    await expect(headerPage.indexPricesContainer).toBeVisible();
    await expect(headerPage.nifty50Item).toBeVisible();
    await expect(headerPage.sensexItem).toBeVisible();
  });

  test('takes full header screenshot for visual verification', async ({ authenticatedPage }) => {
    // Capture header regardless of whether live data is present
    const header = authenticatedPage.locator('[data-testid="kite-header"]');
    await header.screenshot({
      path: 'test-results/screenshots/header-index-prices.png'
    });

    const niftyText = await headerPage.nifty50Value.textContent();
    const sensexText = await headerPage.sensexValue.textContent();
    console.log(`[Index Prices] NIFTY 50: ${niftyText.trim()}, SENSEX: ${sensexText.trim()}`);
  });
});
