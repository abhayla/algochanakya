import { test, expect } from '../../fixtures/auth.fixture.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';
import { assertDataOrEmptyState } from '../../helpers/market-status.helper.js';

/**
 * Watchlist Screen - Happy Path Tests
 * Tests core functionality under normal conditions
 */
test.describe('Watchlist - Happy Path @happy', () => {
  let watchlistPage;

  test.beforeEach(async ({ page }) => {
    watchlistPage = new WatchlistPage(page);
    await watchlistPage.navigate();
  });

  test('should display watchlist page', async () => {
    await watchlistPage.assertPageVisible();
  });

  test('should display search input', async () => {
    await expect(watchlistPage.searchInput).toBeVisible();
  });

  test('should display watchlist tabs', async () => {
    await expect(watchlistPage.tabsContainer).toBeVisible();
  });

  test('should display watchlist header with count', async () => {
    await expect(watchlistPage.header).toBeVisible();
    await expect(watchlistPage.watchlistCount).toBeVisible();
  });

  test('should search for instruments', async ({ page }) => {
    await watchlistPage.search('NIFTY');
    // Wait for search results
    await page.waitForLoadState('domcontentloaded');
    // Either dropdown appears or no results — assert one is visible
    await assertDataOrEmptyState(page, 'watchlist-search-dropdown', 'watchlist-no-results', expect);
  });

  test('should open create watchlist modal', async () => {
    await watchlistPage.openCreateModal();
    await watchlistPage.assertCreateModalVisible();
    await expect(watchlistPage.createInput).toBeVisible();
  });

  test('should close create modal on cancel', async () => {
    await watchlistPage.openCreateModal();
    await watchlistPage.cancelCreateModal();
    await watchlistPage.assertCreateModalHidden();
  });

  test('should display instruments list or empty state', async ({ page }) => {
    await watchlistPage.waitForInstruments();
    await assertDataOrEmptyState(page, 'watchlist-instruments-container', 'watchlist-empty-state', expect);
  });

  test('should show new group button', async () => {
    await expect(watchlistPage.newGroupButton).toBeVisible();
  });

  test('should have no horizontal overflow', async () => {
    const hasOverflow = await watchlistPage.hasHorizontalOverflow();
    expect(hasOverflow).toBe(false);
  });
});
