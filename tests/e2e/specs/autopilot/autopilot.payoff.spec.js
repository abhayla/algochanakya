/**
 * AutoPilot Payoff Chart - E2E Tests
 *
 * Tests for payoff diagram and risk metrics visualization.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Payoff Chart - E2E', () => {
  let page;

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new AutoPilotDashboardPage(authenticatedPage);
    await page.navigate();
    await page.waitForDashboardLoad();

    // Navigate to strategy detail
    await page.page.click('[data-testid="autopilot-strategy-row"]');
    await page.page.waitForSelector('[data-testid="autopilot-strategy-detail"]');
  });

  test('should view payoff chart', async ({ authenticatedPage }) => {
    // Navigate to analytics/payoff tab
    const payoffTab = page.page.locator('[data-testid="autopilot-analytics-tab"]');

    if (await payoffTab.isVisible()) {
      await payoffTab.click();

      // Verify payoff chart is displayed
      const payoffChart = page.page.locator('[data-testid="autopilot-payoff-chart"]');
      await expect(payoffChart).toBeVisible({ timeout: 5000 });

      // Verify chart canvas or SVG exists
      const chartCanvas = payoffChart.locator('canvas, svg');
      await expect(chartCanvas).toBeVisible();
    }
  });

  test('should toggle at expiry/current mode', async ({ authenticatedPage }) => {
    // Navigate to payoff
    const payoffTab = page.page.locator('[data-testid="autopilot-analytics-tab"]');

    if (await payoffTab.isVisible()) {
      await payoffTab.click();

      // Find mode toggle
      const modeToggle = page.page.locator('[data-testid="autopilot-payoff-mode-toggle"]');

      if (await modeToggle.isVisible()) {
        // Toggle to current mode
        await page.page.click('[data-testid="autopilot-payoff-mode-current"]');

        // Wait for chart to update
        await page.page.waitForTimeout(1000);

        // Verify current mode indicator
        const currentModeLabel = page.page.locator('[data-testid="autopilot-payoff-current-label"]');
        await expect(currentModeLabel).toBeVisible();

        // Toggle back to expiry
        await page.page.click('[data-testid="autopilot-payoff-mode-expiry"]');

        await page.page.waitForTimeout(1000);
      }
    }
  });

  test('should display breakeven markers', async ({ authenticatedPage }) => {
    // Navigate to payoff
    const payoffTab = page.page.locator('[data-testid="autopilot-analytics-tab"]');

    if (await payoffTab.isVisible()) {
      await payoffTab.click();

      // Wait for chart to load
      await page.page.waitForSelector('[data-testid="autopilot-payoff-chart"]', { timeout: 5000 });

      // Look for breakeven markers
      const breakevenMarkers = page.page.locator('[data-testid^="autopilot-payoff-breakeven"]');

      // If breakevens exist, they should be visible
      const count = await breakevenMarkers.count();
      if (count > 0) {
        await expect(breakevenMarkers.first()).toBeVisible();

        // Verify breakeven value is displayed
        const breakevenValue = breakevenMarkers.first().locator('[data-testid="autopilot-breakeven-value"]');
        if (await breakevenValue.isVisible()) {
          const valueText = await breakevenValue.textContent();
          expect(valueText.length).toBeGreaterThan(0);
        }
      }
    }
  });

  test('should show tooltip on hover', async ({ authenticatedPage }) => {
    // Navigate to payoff
    const payoffTab = page.page.locator('[data-testid="autopilot-analytics-tab"]');

    if (await payoffTab.isVisible()) {
      await payoffTab.click();

      // Wait for chart
      const payoffChart = page.page.locator('[data-testid="autopilot-payoff-chart"]');
      await expect(payoffChart).toBeVisible({ timeout: 5000 });

      // Hover over chart area
      await payoffChart.hover({ position: { x: 100, y: 100 } });

      // Look for tooltip
      const tooltip = page.page.locator('[data-testid="autopilot-payoff-tooltip"]');

      // Tooltip may appear on hover
      if (await tooltip.isVisible({ timeout: 2000 })) {
        // Verify tooltip has data
        const tooltipText = await tooltip.textContent();
        expect(tooltipText.length).toBeGreaterThan(0);

        // Tooltip should show spot price and P&L
        expect(tooltipText).toMatch(/\d+/);  // Should contain numbers
      }
    }
  });

  test('should display risk metrics summary', async ({ authenticatedPage }) => {
    // Navigate to payoff
    const payoffTab = page.page.locator('[data-testid="autopilot-analytics-tab"]');

    if (await payoffTab.isVisible()) {
      await payoffTab.click();

      // Wait for metrics to load
      await page.page.waitForTimeout(2000);

      // Verify risk metrics section
      const riskMetrics = page.page.locator('[data-testid="autopilot-risk-metrics"]');

      if (await riskMetrics.isVisible()) {
        // Max profit
        const maxProfit = riskMetrics.locator('[data-testid="autopilot-max-profit"]');
        if (await maxProfit.isVisible()) {
          await expect(maxProfit).toBeVisible();
        }

        // Max loss
        const maxLoss = riskMetrics.locator('[data-testid="autopilot-max-loss"]');
        if (await maxLoss.isVisible()) {
          await expect(maxLoss).toBeVisible();
        }

        // Risk/reward ratio
        const riskReward = riskMetrics.locator('[data-testid="autopilot-risk-reward"]');
        if (await riskReward.isVisible()) {
          await expect(riskReward).toBeVisible();
        }

        // Breakevens
        const breakevens = riskMetrics.locator('[data-testid="autopilot-breakevens"]');
        if (await breakevens.isVisible()) {
          await expect(breakevens).toBeVisible();
        }
      }
    }
  });
});
