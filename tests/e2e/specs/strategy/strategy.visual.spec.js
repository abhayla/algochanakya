import { test, expect } from '@playwright/test';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';
import { prepareForVisualTest, VIEWPORTS } from '../../helpers/visual.helper.js';

/**
 * Strategy Builder Screen - Visual Regression Tests
 * Tests layout and visual appearance across viewports
 */
test.describe('Strategy Builder - Visual Regression @visual', () => {
  let strategyPage;

  test.beforeEach(async ({ page }) => {
    strategyPage = new StrategyBuilderPage(page);
  });

  test('should match desktop layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('strategy-desktop.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="strategy-spot-card"]'),
        page.locator('[data-testid="strategy-max-profit-card"]'),
        page.locator('[data-testid="strategy-max-loss-card"]'),
        page.locator('[data-testid="strategy-breakeven-card"]'),
        page.locator('tbody tr.leg-row')
      ]
    });
  });

  test('should match laptop layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.laptop);
    await strategyPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('strategy-laptop.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="strategy-spot-card"]'),
        page.locator('[data-testid="strategy-max-profit-card"]'),
        page.locator('[data-testid="strategy-max-loss-card"]'),
        page.locator('[data-testid="strategy-breakeven-card"]'),
        page.locator('tbody tr.leg-row')
      ]
    });
  });

  test('should match tablet layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet);
    await strategyPage.navigate();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('strategy-tablet.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="strategy-spot-card"]'),
        page.locator('[data-testid="strategy-max-profit-card"]'),
        page.locator('[data-testid="strategy-max-loss-card"]'),
        page.locator('[data-testid="strategy-breakeven-card"]'),
        page.locator('tbody tr.leg-row')
      ]
    });
  });

  test('should match toolbar appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(page);
    await expect(strategyPage.toolbar).toHaveScreenshot('strategy-toolbar.png');
  });

  test('should match selector bar appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(page);
    await expect(strategyPage.selectorBar).toHaveScreenshot('strategy-selector-bar.png');
  });

  test('should match action bar appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(page);
    await expect(strategyPage.actionBar).toHaveScreenshot('strategy-action-bar.png');
  });

  test('should match empty state appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    const isEmpty = await strategyPage.isEmptyState();
    if (isEmpty) {
      await prepareForVisualTest(page);
      await expect(strategyPage.emptyState).toHaveScreenshot('strategy-empty-state.png');
    }
  });

  test('should match summary cards appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    const hasSummary = await strategyPage.hasSummaryCards();
    if (hasSummary) {
      await prepareForVisualTest(page);
      await expect(strategyPage.summaryGrid).toHaveScreenshot('strategy-summary-cards.png', {
        mask: [
          page.locator('[data-testid="strategy-spot-card"]'),
          page.locator('[data-testid="strategy-max-profit-card"]'),
          page.locator('[data-testid="strategy-max-loss-card"]'),
          page.locator('[data-testid="strategy-breakeven-card"]')
        ]
      });
    }
  });
});
