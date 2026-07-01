/**
 * Dashboard Happy Path Tests
 *
 * Tests for normal user flows and expected behavior.
 * Note: These tests require authentication - use auth fixture.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { DashboardPage } from '../../pages/DashboardPage.js';

test.describe('Dashboard - Happy Path @happy', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new DashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForPageLoad();
  });

  test('page loads successfully', async ({ authenticatedPage }) => {
    await expect(dashboardPage.container).toBeVisible();
  });

  test('has correct URL', async ({ authenticatedPage }) => {
    expect(authenticatedPage.url()).toContain('/dashboard');
  });

  test('displays welcome message', async () => {
    await expect(dashboardPage.title).toBeVisible();
    // Title shows a time-based greeting with user name, e.g. "Good morning, Abhay"
    const titleText = await dashboardPage.title.textContent();
    expect(titleText).toMatch(/Good (morning|afternoon|evening)/i);
  });

  test('visible navigation cards (default flags hide OFO + AutoPilot)', async () => {
    await expect(dashboardPage.optionchainCard).toBeVisible();
    await expect(dashboardPage.strategyCard).toBeVisible();
    await expect(dashboardPage.positionsCard).toBeVisible();
    await expect(dashboardPage.strategiesCard).toBeVisible();
    // OFO + AutoPilot hidden by default feature flags — confirm they are NOT visible.
    await expect(dashboardPage.ofoCard).toHaveCount(0);
    await expect(dashboardPage.page.getByTestId('dashboard-autopilot-card')).toHaveCount(0);
  });

  test('option chain card navigates to /optionchain', async ({ authenticatedPage }) => {
    await dashboardPage.goToOptionChain();
    await authenticatedPage.waitForURL('**/optionchain**');
    expect(authenticatedPage.url()).toContain('/optionchain');
  });

  // ofo card test removed — OFO module is hidden by default feature flag. Re-add
  // only if VITE_ENABLE_OFO=true in a future variant suite.

  test('strategy card navigates to /strategy', async ({ authenticatedPage }) => {
    await dashboardPage.goToStrategy();
    await authenticatedPage.waitForURL('**/strategy**');
    expect(authenticatedPage.url()).toContain('/strategy');
  });

  test('positions card navigates to /positions', async ({ authenticatedPage }) => {
    await dashboardPage.goToPositions();
    await authenticatedPage.waitForURL('**/positions**');
    expect(authenticatedPage.url()).toContain('/positions');
  });

  test('strategies card navigates to /strategies', async ({ authenticatedPage }) => {
    await dashboardPage.goToStrategies();
    await authenticatedPage.waitForURL('**/strategies**');
    expect(authenticatedPage.url()).toContain('/strategies');
  });

  test('header shows nifty50 price (not dashes)', async ({ authenticatedPage }) => {
    const niftyPrice = authenticatedPage.getByTestId('kite-header-index-value-nifty50');
    // Prices should appear within 5s (2s WebSocket delay + 2s API fallback + margin)
    await expect(niftyPrice).not.toHaveText('--', { timeout: 5000 });

    const text = await niftyPrice.textContent();
    const numericValue = parseFloat(text.replace(/,/g, ''));
    expect(numericValue).toBeGreaterThan(0);
  });

  test('header shows both index prices', async ({ authenticatedPage }) => {
    // Header shows NIFTY 50 and SENSEX (the two primary indices)
    const indices = ['nifty50', 'sensex'];
    for (const index of indices) {
      const priceEl = authenticatedPage.getByTestId(`kite-header-index-value-${index}`);
      await expect(priceEl).not.toHaveText('--', { timeout: 5000 });
    }
  });
});
