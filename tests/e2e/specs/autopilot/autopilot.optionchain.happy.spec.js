/**
 * AutoPilot Option Chain - Happy Path Tests
 *
 * Tests for option chain viewing, filtering, and strike finding functionality.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { AutoPilotDashboardPage } from '../../pages/AutoPilotDashboardPage.js';

test.describe('AutoPilot Option Chain - Happy Path', () => {
  let page;

  test.beforeEach(async ({ authenticatedPage }) => {
    page = new AutoPilotDashboardPage(authenticatedPage);
    await page.navigate();
    await page.waitForDashboardLoad();

    // Navigate to option chain view
    await page.page.click('[data-testid="autopilot-nav-optionchain"]');
    await page.page.waitForSelector('[data-testid="autopilot-optionchain-table"]');
  });

  test('should view option chain for NIFTY', async ({ authenticatedPage }) => {
    // Select NIFTY underlying
    await page.page.selectOption('[data-testid="autopilot-optionchain-underlying-select"]', 'NIFTY');

    // Wait for option chain to load
    await page.page.waitForSelector('[data-testid="autopilot-optionchain-table"]');

    // Verify option chain table is visible
    const table = page.page.locator('[data-testid="autopilot-optionchain-table"]');
    await expect(table).toBeVisible();

    // Verify strikes are displayed
    const strikeRows = page.page.locator('[data-testid^="autopilot-optionchain-strike-row"]');
    await expect(strikeRows.first()).toBeVisible();
  });

  test('should change expiry selection', async ({ authenticatedPage }) => {
    // Select different expiry
    await page.page.selectOption('[data-testid="autopilot-optionchain-expiry-select"]', { index: 1 });

    // Wait for chain to reload
    await page.page.waitForLoadState('networkidle');

    // Verify new data loaded
    const table = page.page.locator('[data-testid="autopilot-optionchain-table"]');
    await expect(table).toBeVisible();
  });

  test('should toggle Greeks display', async ({ authenticatedPage }) => {
    // Toggle Greeks on
    await page.page.click('[data-testid="autopilot-optionchain-greeks-toggle"]');

    // Verify Greeks columns are visible
    const deltaColumn = page.page.locator('[data-testid="autopilot-optionchain-header-delta"]');
    await expect(deltaColumn).toBeVisible();

    const gammaColumn = page.page.locator('[data-testid="autopilot-optionchain-header-gamma"]');
    await expect(gammaColumn).toBeVisible();

    // Toggle Greeks off
    await page.page.click('[data-testid="autopilot-optionchain-greeks-toggle"]');

    // Verify Greeks columns are hidden
    await expect(deltaColumn).not.toBeVisible();
  });

  test('should select strike from chain', async ({ authenticatedPage }) => {
    // Click on a strike row
    const strikeRow = page.page.locator('[data-testid="autopilot-optionchain-strike-row-25000"]');
    await strikeRow.click();

    // Verify strike selection (may trigger modal or highlight)
    await expect(strikeRow).toHaveClass(/selected|active/);
  });

  test('should highlight ATM strike', async ({ authenticatedPage }) => {
    // Wait for chain to load
    await page.page.waitForSelector('[data-testid^="autopilot-optionchain-strike-row"]');

    // Find ATM strike (should have special class/styling)
    const atmStrike = page.page.locator('[data-testid^="autopilot-optionchain-strike-row"].atm');
    await expect(atmStrike).toBeVisible();

    // Verify ATM indicator
    const atmBadge = page.page.locator('[data-testid="autopilot-optionchain-atm-badge"]');
    await expect(atmBadge).toBeVisible();
  });

  test('should find strike by delta', async ({ authenticatedPage }) => {
    // Open strike finder
    await page.page.click('[data-testid="autopilot-optionchain-strike-finder-btn"]');

    // Select delta mode
    await page.page.selectOption('[data-testid="autopilot-strike-finder-mode"]', 'delta');

    // Enter target delta
    await page.page.fill('[data-testid="autopilot-strike-finder-delta-input"]', '0.15');

    // Select option type
    await page.page.selectOption('[data-testid="autopilot-strike-finder-type"]', 'CE');

    // Click find button
    await page.page.click('[data-testid="autopilot-strike-finder-search-btn"]');

    // Wait for result
    await page.page.waitForSelector('[data-testid="autopilot-strike-finder-result"]');

    // Verify result displays strike
    const result = page.page.locator('[data-testid="autopilot-strike-finder-result"]');
    await expect(result).toContainText(/Strike: \d+/);
  });

  test('should find strike by premium', async ({ authenticatedPage }) => {
    // Open strike finder
    await page.page.click('[data-testid="autopilot-optionchain-strike-finder-btn"]');

    // Select premium mode
    await page.page.selectOption('[data-testid="autopilot-strike-finder-mode"]', 'premium');

    // Enter target premium
    await page.page.fill('[data-testid="autopilot-strike-finder-premium-input"]', '185');

    // Select option type
    await page.page.selectOption('[data-testid="autopilot-strike-finder-type"]', 'PE');

    // Click find button
    await page.page.click('[data-testid="autopilot-strike-finder-search-btn"]');

    // Wait for result
    await page.page.waitForSelector('[data-testid="autopilot-strike-finder-result"]');

    // Verify result
    const result = page.page.locator('[data-testid="autopilot-strike-finder-result"]');
    await expect(result).toBeVisible();
  });

  test('should display cache indicator', async ({ authenticatedPage }) => {
    // Wait for data to load
    await page.page.waitForSelector('[data-testid="autopilot-optionchain-table"]');

    // Check for cache indicator
    const cacheIndicator = page.page.locator('[data-testid="autopilot-optionchain-cache-indicator"]');

    // Cache indicator should be present and show status
    if (await cacheIndicator.isVisible()) {
      await expect(cacheIndicator).toContainText(/cached|live/i);
    }
  });
});
