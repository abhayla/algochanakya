/**
 * Navigation Menu - Happy Path E2E Tests
 *
 * Tests for the AutoPilot navigation menu item.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

test.describe('Navigation Menu - AutoPilot Happy Path', () => {

  test('AutoPilot menu item is visible in navigation', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await expect(autopilotNav).toBeVisible();
  });

  test('AutoPilot menu item displays correct label', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await expect(autopilotNav).toContainText('AutoPilot');
  });

  test('AutoPilot menu item navigates to /autopilot', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    await authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]').click();
    await expect(authenticatedPage).toHaveURL(/\/autopilot/);
  });

  test('AutoPilot menu item shows robot icon', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const icon = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"] svg');
    await expect(icon).toBeVisible();
  });

  test('AutoPilot is last item in navigation menu', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
    const lastItem = navItems.last();
    await expect(lastItem).toHaveAttribute('data-testid', 'kite-header-nav-autopilot');
  });

  test('AutoPilot menu item has correct href', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await expect(autopilotNav).toHaveAttribute('href', '/autopilot');
  });

  test('AutoPilot menu item shows active state when on AutoPilot page', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await expect(autopilotNav).toHaveClass(/active/);
  });

  test('navigation menu order is correct', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
    const count = await navItems.count();

    // AutoPilot should be the 7th item (index 6)
    expect(count).toBe(7);

    const expectedOrder = [
      'kite-header-nav-dashboard',
      'kite-header-nav-optionchain',
      'kite-header-nav-strategy',
      'kite-header-nav-positions',
      'kite-header-nav-strategies',
      'kite-header-nav-watchlist',
      'kite-header-nav-autopilot'
    ];

    for (let i = 0; i < expectedOrder.length; i++) {
      await expect(navItems.nth(i)).toHaveAttribute('data-testid', expectedOrder[i]);
    }
  });
});
