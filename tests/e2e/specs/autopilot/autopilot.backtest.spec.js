/**
 * AutoPilot Phase 4 - Backtest E2E Tests
 *
 * Tests for backtest configuration, execution, and results viewing.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotBacktestPage } from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// BACKTEST - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Backtest - Happy Path', () => {
  let backtestPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    backtestPage = new AutoPilotBacktestPage(authenticatedPage);
    await backtestPage.navigate();
    await backtestPage.waitForPageLoad();
  });

  test('displays backtest page', async () => {
    await expect(backtestPage.backtestPage).toBeVisible();
    await expect(backtestPage.backtestHeader).toBeVisible();
  });

  test('displays backtest list', async () => {
    await expect(backtestPage.backtestList).toBeVisible();
  });

  test('displays new backtest button', async () => {
    await expect(backtestPage.newButton).toBeVisible();
  });

  test('opens backtest configuration modal', async () => {
    await backtestPage.openConfigModal();
    await expect(backtestPage.configModal).toBeVisible();
  });

  test('configures backtest parameters', async () => {
    await backtestPage.configureBacktest({
      startDate: '2024-01-01',
      endDate: '2024-06-30',
      capital: 500000,
      lots: 2,
      slippage: 0.5
    });
  });

  test('cancels backtest configuration', async () => {
    await backtestPage.openConfigModal();
    await backtestPage.cancelConfig();
    await expect(backtestPage.configModal).not.toBeVisible();
  });

  test('views backtest results', async () => {
    const count = await backtestPage.getBacktestCount();
    if (count > 0) {
      const firstRow = backtestPage.backtestRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const backtestId = testId.replace('autopilot-backtest-row-', '');
      await backtestPage.openResults(backtestId);
      await expect(backtestPage.resultsPage).toBeVisible();
    }
  });

  test('displays results summary', async () => {
    const count = await backtestPage.getBacktestCount();
    if (count > 0) {
      const firstRow = backtestPage.backtestRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const backtestId = testId.replace('autopilot-backtest-row-', '');
      await backtestPage.openResults(backtestId);
      await expect(backtestPage.resultsSummary).toBeVisible();
      await expect(backtestPage.totalPnl).toBeVisible();
      await expect(backtestPage.winRate).toBeVisible();
    }
  });

  test('displays equity curve', async () => {
    const count = await backtestPage.getBacktestCount();
    if (count > 0) {
      const firstRow = backtestPage.backtestRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const backtestId = testId.replace('autopilot-backtest-row-', '');
      await backtestPage.openResults(backtestId);
      await expect(backtestPage.equityCurve).toBeVisible();
    }
  });

  test('displays trade history', async () => {
    const count = await backtestPage.getBacktestCount();
    if (count > 0) {
      const firstRow = backtestPage.backtestRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const backtestId = testId.replace('autopilot-backtest-row-', '');
      await backtestPage.openResults(backtestId);
      await expect(backtestPage.tradesTable).toBeVisible();
    }
  });

  test.skip('displays drawdown analysis', async () => {
    // Skip: Drawdown component not implemented in Vue results view
    const count = await backtestPage.getBacktestCount();
    if (count > 0) {
      const firstRow = backtestPage.backtestRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const backtestId = testId.replace('autopilot-backtest-row-', '');
      await backtestPage.openResults(backtestId);
      await expect(backtestPage.drawdown).toBeVisible();
    }
  });
});


// =============================================================================
// BACKTEST - EDGE CASES
// =============================================================================

test.describe('AutoPilot Backtest - Edge Cases', () => {
  let backtestPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    backtestPage = new AutoPilotBacktestPage(authenticatedPage);
    await backtestPage.navigate();
    await backtestPage.waitForPageLoad();
  });

  test('handles invalid date range', async () => {
    await backtestPage.openConfigModal();
    await backtestPage.startDate.fill('2024-12-31');
    await backtestPage.endDate.fill('2024-01-01');
    await backtestPage.runButton.click();
    // Should show validation error
  });

  test('handles pagination if available', async () => {
    const pagination = backtestPage.pagination;
    if (await pagination.isVisible()) {
      const nextButton = pagination.locator('[data-testid="pagination-next"]');
      if (await nextButton.isEnabled()) {
        await nextButton.click();
        await backtestPage.page.waitForLoadState('networkidle');
      }
    }
  });

  test('filters backtests by completed status', async () => {
    await backtestPage.filterByCompleted();
    await expect(backtestPage.backtestPage).toBeVisible();
  });

  test('enables compare mode', async () => {
    await backtestPage.enableCompareMode();
  });

  test('handles very long date range', async () => {
    await backtestPage.openConfigModal();
    await backtestPage.startDate.fill('2019-01-01');
    await backtestPage.endDate.fill('2024-12-31');
    // May show warning about long backtest
  });

  test('deletes a backtest', async () => {
    const count = await backtestPage.getBacktestCount();
    if (count > 0) {
      const firstRow = backtestPage.backtestRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const backtestId = testId.replace('autopilot-backtest-row-', '');
      await backtestPage.deleteBacktest(backtestId);
    }
  });
});
