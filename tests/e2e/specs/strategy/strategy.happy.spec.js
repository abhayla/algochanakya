import { test, expect } from '../../fixtures/auth.fixture.js';
import StrategyBuilderPage from '../../pages/StrategyBuilderPage.js';

/**
 * Strategy Builder Screen - Happy Path Tests
 * Tests core functionality under normal conditions
 */
test.describe('Strategy Builder - Happy Path @happy', () => {
  let strategyPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    strategyPage = new StrategyBuilderPage(authenticatedPage);
    await strategyPage.navigate();
  });

  test('should display strategy builder page', async () => {
    await strategyPage.assertPageVisible();
  });

  test('should display underlying tabs', async () => {
    await expect(strategyPage.underlyingTabs).toBeVisible();
    await expect(strategyPage.niftyTab).toBeVisible();
    await expect(strategyPage.bankniftyTab).toBeVisible();
    await expect(strategyPage.finniftyTab).toBeVisible();
  });

  test('should display P/L mode toggle', async () => {
    await expect(strategyPage.pnlModeExpiry).toBeVisible();
    await expect(strategyPage.pnlModeCurrent).toBeVisible();
  });

  test('should display strategy selector bar', async () => {
    await expect(strategyPage.selectorBar).toBeVisible();
    await expect(strategyPage.strategySelect).toBeVisible();
    await expect(strategyPage.strategyNameInput).toBeVisible();
  });

  test('should display strategy table', async () => {
    await strategyPage.assertTableVisible();
  });

  test('should display action bar', async () => {
    await strategyPage.assertActionBarVisible();
    await expect(strategyPage.addRowButton).toBeVisible();
    await expect(strategyPage.recalculateButton).toBeVisible();
  });

  test('should show empty state when no legs', async () => {
    const isEmpty = await strategyPage.isEmptyState();
    const legCount = await strategyPage.getLegCount();
    if (legCount === 0) {
      expect(isEmpty).toBe(true);
    }
  });

  test('should add a new leg row', async () => {
    const initialCount = await strategyPage.getLegCount();
    await strategyPage.addRow();
    const newCount = await strategyPage.getLegCount();
    expect(newCount).toBe(initialCount + 1);
  });

  test('should switch underlying tabs', async () => {
    await strategyPage.selectUnderlying('BANKNIFTY');
    await expect(strategyPage.bankniftyTab).toHaveClass(/active/);
  });

  test('should switch P/L mode', async () => {
    await strategyPage.setPnLMode('current');
    await expect(strategyPage.pnlModeCurrent).toHaveClass(/active/);

    await strategyPage.setPnLMode('expiry');
    await expect(strategyPage.pnlModeExpiry).toHaveClass(/active/);
  });

  test('should have no horizontal overflow', async () => {
    const hasOverflow = await strategyPage.hasHorizontalOverflow();
    expect(hasOverflow).toBe(false);
  });
});
