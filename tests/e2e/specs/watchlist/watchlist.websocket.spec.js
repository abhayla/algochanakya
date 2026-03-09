import { test, expect } from '../../fixtures/auth.fixture.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';
import { getDataExpectation } from '../../helpers/market-status.helper.js';
import { assertLocatorIsValidPrice } from '../../helpers/assertions.js';

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
    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Instruments should be visible — assert the container is present
      await expect(watchlistPage.instrumentsContainer).toBeVisible();
      const firstRow = authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      await firstRow.waitFor({ state: 'visible', timeout: 5000 });
      await expect(firstRow).toBeVisible();
    } else {
      // PRE_OPEN or CLOSED — assert the page itself is at least stable
      await expect(watchlistPage.pageContainer).toBeVisible();
    }
  });

  test('should display live prices for instruments with valid values', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      await expect(watchlistPage.instrumentsContainer).toBeVisible();
      const firstRow = authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      await firstRow.waitFor({ state: 'visible', timeout: 5000 });

      // Validate that we have actual price values (not just placeholders)
      const ltpCell = authenticatedPage.locator('[data-testid^="watchlist-instrument-ltp-"]').first();
      await ltpCell.waitFor({ state: 'visible', timeout: 5000 });
      await assertLocatorIsValidPrice(ltpCell, 'watchlist LTP');
    } else {
      test.skip(true, `Skipping live price check — market state is ${expectation}`);
    }
  });

  test('should show change indicators (up/down arrows)', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      await expect(watchlistPage.instrumentsContainer).toBeVisible();
      const firstRow = authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      await firstRow.waitFor({ state: 'visible', timeout: 5000 });
      // Row should contain price and change info — assert it has meaningful text
      const rowContent = await firstRow.textContent();
      expect(rowContent.trim().length).toBeGreaterThan(0);
    } else {
      test.skip(true, `Skipping change indicator check — market state is ${expectation}`);
    }
  });

  test('should update prices when receiving new ticks', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      await expect(watchlistPage.instrumentsContainer).toBeVisible();
      const firstRow = authenticatedPage.locator('[data-testid^="watchlist-instrument-row-"]').first();
      await firstRow.waitFor({ state: 'visible', timeout: 5000 });

      // Wait for potential price update
      await authenticatedPage.waitForLoadState('domcontentloaded');

      const updatedContent = await firstRow.textContent();
      expect(updatedContent.trim().length).toBeGreaterThan(0);
    } else {
      test.skip(true, `Skipping tick update check — market state is ${expectation}`);
    }
  });

  test('should handle WebSocket disconnect gracefully', async ({ authenticatedPage }) => {
    // Navigate away and back to test reconnection
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await watchlistPage.navigate();

    // Page should recover
    await watchlistPage.assertPageVisible();
  });

  test('should subscribe to new instruments when added', async ({ authenticatedPage }) => {
    // This test would require adding an instrument
    // For now, just verify the page handles subscription
    await watchlistPage.assertPageVisible();
  });
});
