import { test, expect } from '../../fixtures/auth.fixture.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';

/**
 * Watchlist Screen - Edge Case Tests
 * Tests boundary conditions and error handling
 */
test.describe('Watchlist - Edge Cases @edge', () => {
  let watchlistPage;

  test.beforeEach(async ({ page }) => {
    watchlistPage = new WatchlistPage(page);
    await watchlistPage.navigate();
  });

  test('should handle empty search query', async () => {
    await watchlistPage.search('');
    // Dropdown should not appear for empty query
    const isVisible = await watchlistPage.searchDropdown.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });

  test('should handle single character search', async () => {
    await watchlistPage.search('N');
    // Dropdown should not appear for single character
    const isVisible = await watchlistPage.searchDropdown.isVisible().catch(() => false);
    expect(isVisible).toBe(false);
  });

  test('should handle search with no results', async ({ page }) => {
    await watchlistPage.search('XYZNONEXISTENT123');
    await page.waitForTimeout(600);
    const noResults = await watchlistPage.noResultsMessage.isVisible().catch(() => false);
    // Either no results or empty dropdown
    expect(noResults || !(await watchlistPage.searchDropdown.isVisible().catch(() => false))).toBeTruthy();
  });

  test('should handle special characters in search', async ({ page }) => {
    await watchlistPage.search('@#$%');
    await page.waitForTimeout(600);
    // Should not crash, may show no results
    await expect(watchlistPage.searchInput).toBeVisible();
  });

  test('should handle rapid search input', async ({ page }) => {
    // Type rapidly
    await watchlistPage.searchInput.type('NIFTY', { delay: 50 });
    await page.waitForTimeout(600);
    // Page should remain stable
    await expect(watchlistPage.pageContainer).toBeVisible();
  });

  test('should handle create modal with empty name', async () => {
    await watchlistPage.openCreateModal();
    await watchlistPage.createInput.fill('');
    // Submit should ideally be disabled or show validation
    await expect(watchlistPage.createSubmitButton).toBeVisible();
  });

  test('should clear search input', async () => {
    await watchlistPage.search('NIFTY');
    await watchlistPage.clearSearch();
    await expect(watchlistPage.searchInput).toHaveValue('');
  });

  test('should handle click outside modal to close', async ({ page }) => {
    await watchlistPage.openCreateModal();
    // Click overlay (outside modal content)
    await page.click('[data-testid="watchlist-create-modal"]', { position: { x: 10, y: 10 } });
    // Modal should close
    await watchlistPage.assertCreateModalHidden();
  });

  test('should maintain state after failed search', async ({ page }) => {
    await watchlistPage.search('INVALIDTERM');
    await page.waitForTimeout(600);
    await watchlistPage.clearSearch();
    // Page should be in initial state
    await expect(watchlistPage.searchInput).toHaveValue('');
  });
});
