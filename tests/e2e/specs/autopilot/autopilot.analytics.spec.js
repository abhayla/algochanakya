/**
 * AutoPilot Phase 4 - Analytics Dashboard E2E Tests
 *
 * Tests for analytics charts, metrics, and performance data visualization.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotAnalyticsPage } from '../../pages/AutoPilotDashboardPage.js';


// =============================================================================
// ANALYTICS DASHBOARD - HAPPY PATH
// =============================================================================

test.describe('AutoPilot Analytics Dashboard - Happy Path', () => {
  let analyticsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    analyticsPage = new AutoPilotAnalyticsPage(authenticatedPage);
    await analyticsPage.navigate();
    await analyticsPage.waitForPageLoad();
  });

  test('displays analytics dashboard page', async () => {
    await expect(analyticsPage.analyticsPage).toBeVisible();
    await expect(analyticsPage.analyticsHeader).toBeVisible();
  });

  test('displays performance summary cards', async () => {
    await expect(analyticsPage.summarySection).toBeVisible();
    await expect(analyticsPage.totalPnl).toBeVisible();
    await expect(analyticsPage.winRate).toBeVisible();
    await expect(analyticsPage.avgProfit).toBeVisible();
  });

  test('displays daily P&L chart', async () => {
    await expect(analyticsPage.dailyPnlChart).toBeVisible();
  });

  // Note: Cumulative chart is part of drawdown section as "Equity Curve"
  test('displays drawdown section with equity curve', async () => {
    await expect(analyticsPage.drawdownSection).toBeVisible();
  });

  test('displays strategy breakdown', async () => {
    await expect(analyticsPage.strategyBreakdown).toBeVisible();
  });

  test('displays weekday analysis chart', async () => {
    await expect(analyticsPage.weekdayChart).toBeVisible();
  });

  test('displays drawdown metrics', async () => {
    await expect(analyticsPage.drawdownSection).toBeVisible();
    await expect(analyticsPage.maxDrawdown).toBeVisible();
  });

  test('filters analytics by last 30 days', async () => {
    await analyticsPage.filterByLast30Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });

  test('filters analytics by last 90 days', async () => {
    await analyticsPage.filterByLast90Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });

  test('displays risk metrics section with insights', async () => {
    // Risk metrics are shown in the insights section
    await expect(analyticsPage.riskMetrics).toBeVisible();
  });

  test('switches to 7-day date range', async () => {
    // Vue uses date presets - click 7d button
    await analyticsPage.filterByLast7Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });

  test('switches to 90-day date range', async () => {
    // Vue uses date presets - click 90d button
    await analyticsPage.filterByLast90Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });

  test('displays trade distribution chart', async () => {
    // Trade distribution chart showing P&L histogram by buckets
    await expect(analyticsPage.distributionChart).toBeVisible();
  });

  test('shows detailed strategy performance', async () => {
    // Click strategy row to open detailed strategy performance modal
    const count = await analyticsPage.getStrategyCount();
    if (count > 0) {
      const firstRow = analyticsPage.strategyRows.first();
      const testId = await firstRow.getAttribute('data-testid');
      const strategyId = testId.replace('autopilot-analytics-strategy-row-', '');
      await analyticsPage.openStrategyDetails(strategyId);
      await expect(analyticsPage.strategyDetails).toBeVisible();
    }
  });

  test('opens export modal', async () => {
    // Click export button to open export options modal
    await analyticsPage.openExportModal();
    await expect(analyticsPage.exportModal).toBeVisible();
  });

  test('refreshes analytics data', async () => {
    await analyticsPage.refreshData();
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });
});


// =============================================================================
// ANALYTICS DASHBOARD - EDGE CASES
// =============================================================================

test.describe('AutoPilot Analytics Dashboard - Edge Cases', () => {
  let analyticsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    analyticsPage = new AutoPilotAnalyticsPage(authenticatedPage);
    await analyticsPage.navigate();
    await analyticsPage.waitForPageLoad();
  });

  test('handles no data state with future date filter', async () => {
    // Uses custom date preset - Vue watches date changes automatically
    await analyticsPage.filterByCustomDates('2030-01-01', '2030-12-31');
    // Check for empty/no-data state or page visibility
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });

  test('handles chart interactions', async () => {
    // Hover over chart bars to show tooltips with P&L details
    const chart = analyticsPage.dailyPnlChart;
    if (await chart.isVisible()) {
      // Hover over a bar in the chart - tooltip appears with date and P&L
      const bars = chart.locator('.chart-bar');
      if (await bars.count() > 0) {
        await bars.first().hover();
        // Tooltip should appear (teleported to body)
        await analyticsPage.page.waitForLoadState('domcontentloaded');
      }
    }
  });

  test('handles mobile responsive view', async () => {
    await analyticsPage.page.setViewportSize({ width: 375, height: 667 });
    await analyticsPage.page.waitForLoadState('networkidle');
    await expect(analyticsPage.analyticsPage).toBeVisible();
    // Reset viewport
    await analyticsPage.page.setViewportSize({ width: 1280, height: 720 });
  });

  test('switches between date range presets', async () => {
    // Vue uses date presets - test switching between different presets
    await analyticsPage.filterByLast7Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
    await analyticsPage.filterByLast30Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
    await analyticsPage.filterByLast90Days();
    await expect(analyticsPage.analyticsPage).toBeVisible();
  });
});
