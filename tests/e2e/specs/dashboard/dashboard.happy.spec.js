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
    await expect(dashboardPage.title).toContainText('Welcome');
  });

  test('all four navigation cards are visible', async () => {
    await expect(dashboardPage.watchlistCard).toBeVisible();
    await expect(dashboardPage.strategyCard).toBeVisible();
    await expect(dashboardPage.optionchainCard).toBeVisible();
    await expect(dashboardPage.positionsCard).toBeVisible();
  });

  test('watchlist card navigates to /watchlist', async ({ authenticatedPage }) => {
    await dashboardPage.goToWatchlist();
    await authenticatedPage.waitForURL('**/watchlist**');
    expect(authenticatedPage.url()).toContain('/watchlist');
  });

  test('strategy card navigates to /strategy', async ({ authenticatedPage }) => {
    await dashboardPage.goToStrategy();
    await authenticatedPage.waitForURL('**/strategy**');
    expect(authenticatedPage.url()).toContain('/strategy');
  });

  test('option chain card navigates to /optionchain', async ({ authenticatedPage }) => {
    await dashboardPage.goToOptionChain();
    await authenticatedPage.waitForURL('**/optionchain**');
    expect(authenticatedPage.url()).toContain('/optionchain');
  });

  test('positions card navigates to /positions', async ({ authenticatedPage }) => {
    await dashboardPage.goToPositions();
    await authenticatedPage.waitForURL('**/positions**');
    expect(authenticatedPage.url()).toContain('/positions');
  });
});
