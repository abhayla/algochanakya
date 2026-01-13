/**
 * Header Index Prices Tests
 *
 * Tests for the NIFTY 50 and NIFTY BANK index price display in the header.
 * Verifies that SmartAPI/WebSocket integration is working correctly.
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
    // Check the label text
    await expect(headerPage.nifty50Item).toContainText('NIFTY 50');
  });

  test('NIFTY 50 shows a valid price', async ({ authenticatedPage }) => {
    // Wait for prices to load (WebSocket or API fallback)
    await headerPage.waitForIndexPrices();

    const price = await headerPage.getNifty50Price();
    expect(price).toBeGreaterThan(0);
    // NIFTY 50 is typically between 15,000 and 30,000
    expect(price).toBeGreaterThan(10000);
    expect(price).toBeLessThan(50000);

    // Take screenshot for visual verification
    await authenticatedPage.screenshot({
      path: 'test-results/screenshots/nifty50-price.png',
      clip: { x: 0, y: 0, width: 600, height: 60 }
    });
  });

  test('NIFTY BANK item is displayed', async () => {
    await expect(headerPage.niftyBankItem).toBeVisible();
    // Check the label text
    await expect(headerPage.niftyBankItem).toContainText('NIFTY BANK');
  });

  test('NIFTY BANK shows a valid price', async ({ authenticatedPage }) => {
    // Wait for prices to load (WebSocket or API fallback)
    await headerPage.waitForIndexPrices();

    const price = await headerPage.getNiftyBankPrice();
    expect(price).toBeGreaterThan(0);
    // NIFTY BANK is typically between 35,000 and 60,000
    expect(price).toBeGreaterThan(30000);
    expect(price).toBeLessThan(70000);

    // Take screenshot for visual verification
    await authenticatedPage.screenshot({
      path: 'test-results/screenshots/niftybank-price.png',
      clip: { x: 0, y: 0, width: 600, height: 60 }
    });
  });

  test('prices use Indian number format with commas', async () => {
    await headerPage.waitForIndexPrices();

    // Get raw text to verify formatting
    const niftyText = await headerPage.nifty50Value.textContent();
    const bankText = await headerPage.niftyBankValue.textContent();

    // Indian format uses commas (e.g., 20,500.50 or 45,200.25)
    expect(niftyText).toMatch(/[\d,]+(\.\d+)?/);
    expect(bankText).toMatch(/[\d,]+(\.\d+)?/);

    // Verify comma is present for large numbers
    expect(niftyText).toContain(',');
    expect(bankText).toContain(',');
  });

  test('index prices remain visible after page navigation', async ({ authenticatedPage }) => {
    await headerPage.waitForIndexPrices();

    // Get initial prices
    const initialNiftyPrice = await headerPage.getNifty50Price();

    // Navigate to another page (option chain - authenticated page)
    await authenticatedPage.goto('/optionchain');
    await authenticatedPage.waitForLoadState('networkidle');

    // Wait a moment for the page to stabilize
    await authenticatedPage.waitForTimeout(1000);

    // Verify index prices are still visible
    await expect(headerPage.indexPricesContainer).toBeVisible();
    await expect(headerPage.nifty50Item).toBeVisible();
    await expect(headerPage.niftyBankItem).toBeVisible();

    // Wait for prices to load on new page
    await headerPage.waitForIndexPrices();

    // Prices should still be valid
    const newNiftyPrice = await headerPage.getNifty50Price();
    expect(newNiftyPrice).toBeGreaterThan(0);
  });

  test('takes full header screenshot for visual verification', async ({ authenticatedPage }) => {
    await headerPage.waitForIndexPrices();

    // Capture the entire header for visual verification
    const header = authenticatedPage.locator('[data-testid="kite-header"]');
    await header.screenshot({
      path: 'test-results/screenshots/header-index-prices.png'
    });

    // Log the prices for debugging
    const niftyPrice = await headerPage.getNifty50Price();
    const bankPrice = await headerPage.getNiftyBankPrice();
    console.log(`[Index Prices] NIFTY 50: ${niftyPrice}, NIFTY BANK: ${bankPrice}`);
  });
});
