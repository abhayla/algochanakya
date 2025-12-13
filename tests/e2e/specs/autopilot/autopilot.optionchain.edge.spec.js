/**
 * AutoPilot Option Chain - Edge Case Tests
 *
 * Tests for error handling, loading states, and edge cases.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Option Chain - Edge Cases', () => {
  let page;

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new AutoPilotDashboardPage(authenticatedPage);
    await page.navigate();
    await page.waitForDashboardLoad();

    // Navigate to option chain view
    await page.page.click('[data-testid="autopilot-nav-optionchain"]');
  });

  test('should handle empty option chain gracefully', async ({ authenticatedPage }) => {
    // Mock API to return empty data
    await page.page.route('**/api/v1/autopilot/option-chain/**', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ underlying: 'NIFTY', spot_price: 25250, strikes: [] })
      });
    });

    // Select underlying
    await page.page.selectOption('[data-testid="autopilot-optionchain-underlying-select"]', 'NIFTY');

    // Wait for empty state
    const emptyState = page.page.locator('[data-testid="autopilot-optionchain-empty-state"]');
    await expect(emptyState).toBeVisible();
    await expect(emptyState).toContainText(/no data/i);
  });

  test('should handle API error', async ({ authenticatedPage }) => {
    // Mock API to return error
    await page.page.route('**/api/v1/autopilot/option-chain/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    // Select underlying
    await page.page.selectOption('[data-testid="autopilot-optionchain-underlying-select"]', 'NIFTY');

    // Wait for error message
    const errorMessage = page.page.locator('[data-testid="autopilot-optionchain-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/error|failed/i);
  });

  test('should reject invalid delta search', async ({ authenticatedPage }) => {
    // Open strike finder
    await page.page.click('[data-testid="autopilot-optionchain-strike-finder-btn"]');

    // Select delta mode
    await page.page.selectOption('[data-testid="autopilot-strike-finder-mode"]', 'delta');

    // Enter invalid delta (> 1.0)
    await page.page.fill('[data-testid="autopilot-strike-finder-delta-input"]', '1.5');

    // Click find button
    await page.page.click('[data-testid="autopilot-strike-finder-search-btn"]');

    // Verify validation error
    const errorMessage = page.page.locator('[data-testid="autopilot-strike-finder-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText(/invalid|range/i);
  });

  test('should reject invalid premium search', async ({ authenticatedPage }) => {
    // Open strike finder
    await page.page.click('[data-testid="autopilot-optionchain-strike-finder-btn"]');

    // Select premium mode
    await page.page.selectOption('[data-testid="autopilot-strike-finder-mode"]', 'premium');

    // Enter invalid premium (negative)
    await page.page.fill('[data-testid="autopilot-strike-finder-premium-input"]', '-100');

    // Click find button
    await page.page.click('[data-testid="autopilot-strike-finder-search-btn"]');

    // Verify validation error
    const errorMessage = page.page.locator('[data-testid="autopilot-strike-finder-error"]');
    await expect(errorMessage).toBeVisible();
  });

  test('should handle expiry not found', async ({ authenticatedPage }) => {
    // Mock API to return empty expiries
    await page.page.route('**/api/v1/autopilot/option-chain/expiries/**', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify([])
      });
    });

    // Select underlying
    await page.page.selectOption('[data-testid="autopilot-optionchain-underlying-select"]', 'NIFTY');

    // Wait for no expiries message
    const noExpiries = page.page.locator('[data-testid="autopilot-optionchain-no-expiries"]');
    await expect(noExpiries).toBeVisible();
  });

  test('should show loading states', async ({ authenticatedPage }) => {
    // Delay API response
    await page.page.route('**/api/v1/autopilot/option-chain/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.continue();
    });

    // Select underlying
    await page.page.selectOption('[data-testid="autopilot-optionchain-underlying-select"]', 'NIFTY');

    // Verify loading indicator appears
    const loadingIndicator = page.page.locator('[data-testid="autopilot-optionchain-loading"]');
    await expect(loadingIndicator).toBeVisible();

    // Wait for loading to finish
    await page.page.waitForSelector('[data-testid="autopilot-optionchain-table"]', { timeout: 3000 });

    // Verify loading indicator is gone
    await expect(loadingIndicator).not.toBeVisible();
  });
});
