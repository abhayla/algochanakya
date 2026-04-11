/**
 * Navigation Menu - Cross Screen E2E Tests
 *
 * Tests that AutoPilot navigation item appears consistently on all screens.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

test.describe('Navigation Menu - AutoPilot Across All Screens', () => {

  const screens = [
    { name: 'Dashboard', path: '/dashboard' },
    { name: 'Watchlist', path: '/watchlist' },
    { name: 'Positions', path: '/positions' },
    { name: 'Option Chain', path: '/optionchain' },
    { name: 'Strategy Builder', path: '/strategy' },
    { name: 'Strategy Library', path: '/strategies' },
    { name: 'AutoPilot', path: '/autopilot' },
  ];

  for (const screen of screens) {
    test(`AutoPilot nav item visible on ${screen.name} screen`, async ({ authenticatedPage }) => {
      await authenticatedPage.goto(screen.path);
      await authenticatedPage.waitForLoadState('networkidle');

      const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
      await expect(autopilotNav).toBeVisible();
    });

    test(`AutoPilot nav item has robot icon on ${screen.name} screen`, async ({ authenticatedPage }) => {
      await authenticatedPage.goto(screen.path);
      await authenticatedPage.waitForLoadState('networkidle');

      const icon = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"] svg');
      await expect(icon).toBeVisible();
    });

    test(`AutoPilot nav item clickable from ${screen.name} screen`, async ({ authenticatedPage }) => {
      await authenticatedPage.goto(screen.path);
      await authenticatedPage.waitForLoadState('networkidle');

      await authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]').click();
      await expect(authenticatedPage).toHaveURL(/\/autopilot/);
    });
  }

  test('navigation bar is consistent across all screens', async ({ authenticatedPage }) => {
    for (const screen of screens) {
      await authenticatedPage.goto(screen.path);
      await authenticatedPage.waitForLoadState('domcontentloaded');

      // Check that all 6 nav items exist (dashboard, optionchain, ofo, strategy, positions, autopilot)
      const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
      await expect(navItems.first()).toBeVisible(); // wait for Vue to mount
      const count = await navItems.count();
      expect(count).toBe(6);

      // Check AutoPilot is always last
      const lastItem = navItems.last();
      await expect(lastItem).toHaveAttribute('data-testid', 'kite-header-nav-autopilot');
    }
  });
});
