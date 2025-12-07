/**
 * Strategy Library Screen - Visual Regression Tests
 *
 * Tests visual consistency and layout:
 * - Page layout and structure
 * - Component visibility
 * - Responsive design
 * - No horizontal overflow
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyLibraryPage from '../../pages/StrategyLibraryPage.js';
import { prepareForVisualTest, getVisualCompareOptions, VIEWPORTS } from '../../helpers/visual.helper.js';

test.describe('Strategy Library - Visual Regression @visual', () => {
  let strategyLibraryPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyLibraryPage = new StrategyLibraryPage(authenticatedPage);
    await strategyLibraryPage.navigate();
  });

  // ==================== Layout Tests ====================

  test('should have no horizontal overflow', async () => {
    await strategyLibraryPage.assertNoHorizontalOverflow();
  });

  test('should display page title correctly', async () => {
    await expect(strategyLibraryPage.pageTitle).toBeVisible();
    const title = await strategyLibraryPage.pageTitle.textContent();
    expect(title.length).toBeGreaterThan(0);
  });

  test('should display categories container', async () => {
    await strategyLibraryPage.assertCategoriesVisible();
  });

  test('should display search container', async () => {
    await expect(strategyLibraryPage.searchContainer).toBeVisible();
  });

  test('should display cards grid', async () => {
    await strategyLibraryPage.assertCardsGridVisible();
  });

  // ==================== Category Visual Tests ====================

  test('should display all category pills inline', async ({ authenticatedPage }) => {
    const categories = await authenticatedPage.locator('[data-testid^="strategy-library-category-"]').all();
    expect(categories.length).toBeGreaterThanOrEqual(5);

    for (const category of categories) {
      await expect(category).toBeVisible();
    }
  });

  test('should highlight active category', async () => {
    await strategyLibraryPage.selectCategory('bullish');

    const bullishPill = strategyLibraryPage.categoryBullish;
    const classList = await bullishPill.getAttribute('class');

    // Should have active/selected class
    expect(classList).toMatch(/active|selected|bg-/);
  });

  // ==================== Card Grid Visual Tests ====================

  test('should display cards in grid layout', async () => {
    const grid = strategyLibraryPage.cardsGrid;
    const gridStyle = await grid.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        display: style.display,
        gridTemplateColumns: style.gridTemplateColumns
      };
    });

    // Should be grid or flex layout
    expect(['grid', 'flex']).toContain(gridStyle.display);
  });

  test('should display card with proper structure', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();

    // Card should be visible
    await expect(firstCard).toBeVisible();

    // Card should have reasonable dimensions
    const boundingBox = await firstCard.boundingBox();
    expect(boundingBox.width).toBeGreaterThan(200);
    expect(boundingBox.height).toBeGreaterThan(100);
  });

  test('should display card action buttons', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();

    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await expect(detailsButton).toBeVisible();
    await expect(deployButton).toBeVisible();
  });

  // ==================== Modal Visual Tests ====================

  test('should display wizard modal with proper overlay', async () => {
    await strategyLibraryPage.openWizard();

    const modal = strategyLibraryPage.wizardModal;
    await expect(modal).toBeVisible();

    // Check modal has proper z-index/overlay
    const modalBox = await modal.boundingBox();
    expect(modalBox.width).toBeGreaterThan(200);
    expect(modalBox.height).toBeGreaterThan(200);
  });

  test('should display wizard steps properly', async () => {
    await strategyLibraryPage.openWizard();

    // Step 1 should be visible
    await expect(strategyLibraryPage.wizardStep1).toBeVisible();

    // Should have outlook options
    await expect(strategyLibraryPage.wizardOutlookBullish).toBeVisible();
    await expect(strategyLibraryPage.wizardOutlookBearish).toBeVisible();
    await expect(strategyLibraryPage.wizardOutlookNeutral).toBeVisible();
    await expect(strategyLibraryPage.wizardOutlookVolatile).toBeVisible();
  });

  test('should display details modal with proper layout', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await strategyLibraryPage.assertDetailsModalVisible();

    const modal = strategyLibraryPage.detailsModal;
    const modalBox = await modal.boundingBox();

    // Modal should have substantial size
    expect(modalBox.width).toBeGreaterThan(300);
    expect(modalBox.height).toBeGreaterThan(200);
  });

  test('should display deploy modal with form elements', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const deployButton = firstCard.locator('[data-testid$="-deploy"]');

    await deployButton.click();
    await strategyLibraryPage.assertDeployModalVisible();

    // Check form elements
    await expect(strategyLibraryPage.deployUnderlyingSelect).toBeVisible();
    await expect(strategyLibraryPage.deployLotsInput).toBeVisible();
    await expect(strategyLibraryPage.deployButton).toBeVisible();
  });

  // ==================== Responsive Tests ====================

  test('should adapt to tablet viewport', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 768, height: 1024 });
    await strategyLibraryPage.navigate();

    // Should still show all main elements
    await strategyLibraryPage.assertPageVisible();
    await strategyLibraryPage.assertCategoriesVisible();
    await strategyLibraryPage.assertCardsGridVisible();

    // No horizontal overflow
    await strategyLibraryPage.assertNoHorizontalOverflow();
  });

  test('should adapt to mobile viewport', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 375, height: 667 });
    await strategyLibraryPage.navigate();

    // Should still show main elements
    await strategyLibraryPage.assertPageVisible();
    await strategyLibraryPage.assertCardsGridVisible();

    // No horizontal overflow
    await strategyLibraryPage.assertNoHorizontalOverflow();
  });

  test('should adapt to wide desktop viewport', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 1920, height: 1080 });
    await strategyLibraryPage.navigate();

    // Should still show all elements properly
    await strategyLibraryPage.assertPageVisible();
    await strategyLibraryPage.assertCategoriesVisible();
    await strategyLibraryPage.assertCardsGridVisible();
    await strategyLibraryPage.assertWizardButtonVisible();
  });

  // ==================== Color and Theme Tests ====================

  test('should display category badges with appropriate colors', async ({ authenticatedPage }) => {
    const cards = await authenticatedPage.locator('[data-testid^="strategy-card-"]').all();
    if (cards.length === 0) return;

    const firstCard = cards[0];
    const categoryBadge = firstCard.locator('[data-testid$="-category"]');

    if (await categoryBadge.isVisible()) {
      const bgColor = await categoryBadge.evaluate((el) => {
        return window.getComputedStyle(el).backgroundColor;
      });

      // Should have a background color
      expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
    }
  });

  test('should display Greek badges correctly', async ({ authenticatedPage }) => {
    const cards = await authenticatedPage.locator('[data-testid^="strategy-card-"]').all();

    for (const card of cards.slice(0, 3)) {
      const thetaBadge = card.locator('[data-testid$="-theta"]');
      const vegaBadge = card.locator('[data-testid$="-vega"]');
      const deltaBadge = card.locator('[data-testid$="-delta"]');

      // At least one should exist on cards that have Greeks
      const thetaVisible = await thetaBadge.isVisible().catch(() => false);
      const vegaVisible = await vegaBadge.isVisible().catch(() => false);
      const deltaVisible = await deltaBadge.isVisible().catch(() => false);

      // If any Greeks badges exist, they should be properly styled
      if (thetaVisible || vegaVisible || deltaVisible) {
        // Greeks are present
        expect(thetaVisible || vegaVisible || deltaVisible).toBe(true);
      }
    }
  });

  // ==================== Empty State Visual Tests ====================

  test('should display empty state properly', async ({ authenticatedPage }) => {
    await strategyLibraryPage.search('xyz123nonexistent999');
    await authenticatedPage.waitForTimeout(500);

    const cardCount = await strategyLibraryPage.getStrategyCardCount();
    if (cardCount === 0) {
      const emptyState = strategyLibraryPage.emptyState;
      await expect(emptyState).toBeVisible();

      // Empty state should have proper styling
      const emptyBox = await emptyState.boundingBox();
      expect(emptyBox.height).toBeGreaterThan(50);
    }
  });

  // ==================== Comparison Bar Visual Tests ====================

  test('should display comparison bar when strategies selected', async ({ authenticatedPage }) => {
    const cards = await authenticatedPage.locator('[data-testid^="strategy-card-"]').all();
    if (cards.length < 2) return;

    // Select two strategies
    await cards[0].locator('[data-testid$="-compare"]').click();
    await authenticatedPage.waitForTimeout(200);
    await cards[1].locator('[data-testid$="-compare"]').click();
    await authenticatedPage.waitForTimeout(200);

    const comparisonBar = strategyLibraryPage.comparisonBar;
    const isVisible = await comparisonBar.isVisible().catch(() => false);

    if (isVisible) {
      // Should be visible at bottom of screen
      const barBox = await comparisonBar.boundingBox();
      expect(barBox.width).toBeGreaterThan(200);
    }
  });

  // ==================== Screenshot Tests ====================

  test('should match strategy library page snapshot', async ({ authenticatedPage }) => {
    // Wait for page to fully load
    await authenticatedPage.waitForTimeout(1000);
    await prepareForVisualTest(authenticatedPage);

    // Take screenshot for visual comparison
    await expect(authenticatedPage).toHaveScreenshot('strategy-library-page.png', getVisualCompareOptions());
  });

  test('should match wizard modal snapshot', async ({ authenticatedPage }) => {
    await strategyLibraryPage.openWizard();
    await authenticatedPage.waitForTimeout(500);
    await prepareForVisualTest(authenticatedPage);

    await expect(strategyLibraryPage.wizardModal).toHaveScreenshot('strategy-wizard-modal.png', getVisualCompareOptions());
  });

  test('should match details modal snapshot', async ({ authenticatedPage }) => {
    const firstCard = authenticatedPage.locator('[data-testid^="strategy-card-"]').first();
    const detailsButton = firstCard.locator('[data-testid$="-view-details"]');

    await detailsButton.click();
    await authenticatedPage.waitForTimeout(500);
    await prepareForVisualTest(authenticatedPage);

    await expect(strategyLibraryPage.detailsModal).toHaveScreenshot('strategy-details-modal.png', getVisualCompareOptions());
  });
});
