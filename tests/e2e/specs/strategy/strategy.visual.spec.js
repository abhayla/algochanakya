import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';
import { prepareForVisualTest, getVisualCompareOptions, VIEWPORTS } from '../../helpers/visual.helper.js';

/**
 * Strategy Builder Screen - Visual Regression Tests
 * Tests layout and visual appearance across viewports
 */
test.describe('Strategy Builder - Visual Regression @visual', () => {
  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
  });

  test('should match desktop layout', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot('strategy-desktop.png', {
      ...getVisualCompareOptions(),
      fullPage: true,
      mask: [
        authenticatedPage.locator('[data-testid="strategy-spot-card"]'),
        authenticatedPage.locator('[data-testid="strategy-max-profit-card"]'),
        authenticatedPage.locator('[data-testid="strategy-max-loss-card"]'),
        authenticatedPage.locator('[data-testid="strategy-breakeven-card"]'),
        authenticatedPage.locator('tbody tr.leg-row')
      ]
    });
  });

  test('should match laptop layout', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.laptop);
    await strategyPage.navigate();
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot('strategy-laptop.png', {
      ...getVisualCompareOptions(),
      fullPage: true,
      mask: [
        authenticatedPage.locator('[data-testid="strategy-spot-card"]'),
        authenticatedPage.locator('[data-testid="strategy-max-profit-card"]'),
        authenticatedPage.locator('[data-testid="strategy-max-loss-card"]'),
        authenticatedPage.locator('[data-testid="strategy-breakeven-card"]'),
        authenticatedPage.locator('tbody tr.leg-row')
      ]
    });
  });

  test('should match tablet layout', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.tablet);
    await strategyPage.navigate();
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot('strategy-tablet.png', {
      ...getVisualCompareOptions(),
      fullPage: true,
      mask: [
        authenticatedPage.locator('[data-testid="strategy-spot-card"]'),
        authenticatedPage.locator('[data-testid="strategy-max-profit-card"]'),
        authenticatedPage.locator('[data-testid="strategy-max-loss-card"]'),
        authenticatedPage.locator('[data-testid="strategy-breakeven-card"]'),
        authenticatedPage.locator('tbody tr.leg-row')
      ]
    });
  });

  test('should match toolbar appearance', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(authenticatedPage);
    await expect(strategyPage.toolbar).toHaveScreenshot('strategy-toolbar.png', getVisualCompareOptions());
  });

  test('should match selector bar appearance', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(authenticatedPage);
    await expect(strategyPage.selectorBar).toHaveScreenshot('strategy-selector-bar.png', getVisualCompareOptions());
  });

  test('should match action bar appearance', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    await prepareForVisualTest(authenticatedPage);
    await expect(strategyPage.actionBar).toHaveScreenshot('strategy-action-bar.png', getVisualCompareOptions());
  });

  test('should match empty state appearance', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    const isEmpty = await strategyPage.isEmptyState();
    if (isEmpty) {
      await prepareForVisualTest(authenticatedPage);
      await expect(strategyPage.emptyState).toHaveScreenshot('strategy-empty-state.png', getVisualCompareOptions());
    }
  });

  test('should match summary cards appearance', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await strategyPage.navigate();
    const hasSummary = await strategyPage.hasSummaryCards();
    if (hasSummary) {
      await prepareForVisualTest(authenticatedPage);
      await expect(strategyPage.summaryGrid).toHaveScreenshot('strategy-summary-cards.png', {
        ...getVisualCompareOptions(),
        mask: [
          authenticatedPage.locator('[data-testid="strategy-spot-card"]'),
          authenticatedPage.locator('[data-testid="strategy-max-profit-card"]'),
          authenticatedPage.locator('[data-testid="strategy-max-loss-card"]'),
          authenticatedPage.locator('[data-testid="strategy-breakeven-card"]')
        ]
      });
    }
  });
});
