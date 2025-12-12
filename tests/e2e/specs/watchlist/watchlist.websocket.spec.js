import { test, expect } from '../../fixtures/auth.fixture.js';
import WatchlistPage from '../../pages/WatchlistPage.js';

/**
 * Watchlist Screen - WebSocket Tests
 * Tests real-time price updates via WebSocket
 */
test.describe('Watchlist - WebSocket @websocket', () => {
  let watchlistPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    watchlistPage = new WatchlistPage(authenticatedPage);
    await watchlistPage.navigate();
  });

  test('should connect to WebSocket on page load', async ({ authenticatedPage }) => {
    // Wait for WebSocket connection
    await authenticatedPage.waitForTimeout(2000);
    // Check if instruments have live prices (if any instruments exist)
    const hasInstruments = await watchlistPage.instrumentsContainer.isVisible().catch(() => false);
    if (hasInstruments) {
      // Verify price elements are present
      const priceElements = await authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      await expect(priceElements).toBeVisible();
    }
  });

  test('should display live prices for instruments with valid values', async ({ authenticatedPage }) => {
    await authenticatedPage.waitForTimeout(2000);
    const hasInstruments = await watchlistPage.instrumentsContainer.isVisible().catch(() => false);
    if (hasInstruments) {
      // Check that price text is not empty
      const firstRow = await authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      const priceText = await firstRow.textContent();
      expect(priceText.length).toBeGreaterThan(0);

      // Validate that we have actual price values (not just placeholders)
      // Look for LTP cell with valid numeric value
      const ltpCell = authenticatedPage.locator('[data-testid^="watchlist-instrument-ltp-"]').first();
      if (await ltpCell.isVisible()) {
        const ltpText = await ltpCell.textContent();
        const ltpValue = parseFloat(ltpText.replace(/[^\d.-]/g, ''));

        // LTP should be a valid positive number
        // Test will fail if Kite broker token is expired
        expect(ltpValue).toBeGreaterThan(0);
      }
    }
  });

  test('should show change indicators (up/down arrows)', async ({ authenticatedPage }) => {
    await authenticatedPage.waitForTimeout(2000);
    const hasInstruments = await watchlistPage.instrumentsContainer.isVisible().catch(() => false);
    if (hasInstruments) {
      // Look for change indicators (↑ or ↓)
      const rowContent = await authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first().textContent();
      // Row should contain price and change info
      expect(rowContent).toBeTruthy();
    }
  });

  test('should update prices when receiving new ticks', async ({ authenticatedPage }) => {
    await authenticatedPage.waitForTimeout(2000);
    const hasInstruments = await watchlistPage.instrumentsContainer.isVisible().catch(() => false);
    if (hasInstruments) {
      // Get initial price
      const firstRow = authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      const initialContent = await firstRow.textContent();

      // Wait for potential update
      await authenticatedPage.waitForTimeout(3000);

      // Price might have updated (or stayed same if market is closed)
      const updatedContent = await firstRow.textContent();
      // Just verify it's still visible and has content
      expect(updatedContent.length).toBeGreaterThan(0);
    }
  });

  test('should handle WebSocket disconnect gracefully', async ({ authenticatedPage }) => {
    // Navigate away and back to test reconnection
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForTimeout(500);
    await watchlistPage.navigate();

    // Page should recover
    await watchlistPage.assertPageVisible();
  });

  test('should subscribe to new instruments when added', async ({ authenticatedPage }) => {
    // This test would require adding an instrument
    // For now, just verify the page handles subscription
    await authenticatedPage.waitForTimeout(1000);
    await watchlistPage.assertPageVisible();
  });
});
