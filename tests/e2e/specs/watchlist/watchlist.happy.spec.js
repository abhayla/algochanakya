import { test, expect } from '../../fixtures/auth.fixture.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';

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
    await page.waitForTimeout(600);
    // Either dropdown appears or no results
    const hasResults = await watchlistPage.searchDropdown.isVisible().catch(() => false);
    const hasNoResults = await watchlistPage.noResultsMessage.isVisible().catch(() => false);
    expect(hasResults || hasNoResults).toBeTruthy();
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

  test('should display instruments list or empty state', async () => {
    await watchlistPage.waitForInstruments();
    const hasInstruments = await watchlistPage.instrumentsContainer.isVisible().catch(() => false);
    const hasEmptyState = await watchlistPage.emptyState.isVisible().catch(() => false);
    expect(hasInstruments || hasEmptyState).toBeTruthy();
  });

  test('should show new group button', async () => {
    await expect(watchlistPage.newGroupButton).toBeVisible();
  });

  test('should have no horizontal overflow', async () => {
    const hasOverflow = await watchlistPage.hasHorizontalOverflow();
    expect(hasOverflow).toBe(false);
  });
});
