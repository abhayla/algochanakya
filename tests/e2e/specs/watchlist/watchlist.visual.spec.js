import { test, expect } from '../../fixtures/auth.fixture.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';
import { prepareForVisualTest, VIEWPORTS } from '../../helpers/visual.helper.js';

/**
 * Watchlist Screen - Visual Regression Tests
 * Tests layout and visual appearance across viewports
 */
test.describe('Watchlist - Visual Regression @visual', () => {
  let watchlistPage;

  test.beforeEach(async ({ page }) => {
    watchlistPage = new WatchlistPage(page);
  });

  test('should match desktop layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await watchlistPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('watchlist-desktop.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid^="watchlist-instrument-row-"]'),
        page.locator('[data-testid="watchlist-count"]')
      ]
    });
  });

  test('should match laptop layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.laptop);
    await watchlistPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('watchlist-laptop.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid^="watchlist-instrument-row-"]'),
        page.locator('[data-testid="watchlist-count"]')
      ]
    });
  });

  test('should match tablet layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet);
    await watchlistPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('watchlist-tablet.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid^="watchlist-instrument-row-"]'),
        page.locator('[data-testid="watchlist-count"]')
      ]
    });
  });

  test('should match mobile layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await watchlistPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('watchlist-mobile.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid^="watchlist-instrument-row-"]'),
        page.locator('[data-testid="watchlist-count"]')
      ]
    });
  });

  test('should match create modal appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await watchlistPage.navigate();
    await watchlistPage.openCreateModal();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('watchlist-create-modal.png');
  });

  test('should match empty state appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await watchlistPage.navigate();
    const hasEmptyState = await watchlistPage.emptyState.isVisible();
    if (hasEmptyState) {
      await prepareForVisualTest(page);
      await expect(watchlistPage.emptyState).toHaveScreenshot('watchlist-empty-state.png');
    } else {
      // Instruments are loaded — assert the instruments container is visible
      await expect(watchlistPage.instrumentsContainer).toBeVisible();
    }
  });
});
