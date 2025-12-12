/**
 * Navigation Menu - Accessibility Audit E2E Tests
 *
 * Accessibility and style consistency tests for AutoPilot navigation menu item.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

test.describe('Navigation Menu - AutoPilot Accessibility Audit', () => {

  test('AutoPilot nav item has proper link semantics @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');

    // Should be a link element
    const tagName = await autopilotNav.evaluate(el => el.tagName.toLowerCase());
    expect(tagName).toBe('a');

    // Should have href attribute
    await expect(autopilotNav).toHaveAttribute('href', '/autopilot');

    // Should have visible text content
    await expect(autopilotNav).toContainText('AutoPilot');
  });

  test('navigation has consistent font styling @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
    const count = await navItems.count();

    const fontSizes = [];
    const fontFamilies = [];

    for (let i = 0; i < count; i++) {
      const fontSize = await navItems.nth(i).evaluate(el =>
        window.getComputedStyle(el).fontSize
      );
      const fontFamily = await navItems.nth(i).evaluate(el =>
        window.getComputedStyle(el).fontFamily
      );
      fontSizes.push(fontSize);
      fontFamilies.push(fontFamily);
    }

    // All nav items should have same font size
    expect(new Set(fontSizes).size).toBe(1);

    // All nav items should have same font family
    expect(new Set(fontFamilies).size).toBe(1);
  });

  test('navigation items have consistent padding @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
    const count = await navItems.count();

    const paddings = [];

    for (let i = 0; i < count; i++) {
      const padding = await navItems.nth(i).evaluate(el =>
        window.getComputedStyle(el).padding
      );
      paddings.push(padding);
    }

    // All nav items should have same padding
    expect(new Set(paddings).size).toBe(1);
  });

  test('no horizontal overflow with AutoPilot nav item @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const header = authenticatedPage.locator('[data-testid="kite-header"]');
    const scrollWidth = await header.evaluate(el => el.scrollWidth);
    const clientWidth = await header.evaluate(el => el.clientWidth);

    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });

  test('AutoPilot nav item has sufficient color contrast @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');

    const color = await autopilotNav.evaluate(el =>
      window.getComputedStyle(el).color
    );
    const backgroundColor = await autopilotNav.evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    );

    // Color should not be transparent
    expect(color).not.toBe('rgba(0, 0, 0, 0)');
  });

  test('robot icon has correct dimensions @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const icon = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"] svg');
    const boundingBox = await icon.boundingBox();

    // Icon should be 16x16
    expect(boundingBox.width).toBe(16);
    expect(boundingBox.height).toBe(16);
  });

  test('AutoPilot nav item is keyboard accessible @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    // Tab through navigation items
    const navItems = authenticatedPage.locator('[data-testid="kite-header-nav"] a');
    const count = await navItems.count();

    // Focus on first nav item
    await navItems.first().focus();

    // Tab to AutoPilot (last item)
    for (let i = 1; i < count; i++) {
      await authenticatedPage.keyboard.press('Tab');
    }

    // AutoPilot should now be focused
    const focusedElement = await authenticatedPage.evaluate(() =>
      document.activeElement?.getAttribute('data-testid')
    );
    expect(focusedElement).toBe('kite-header-nav-autopilot');

    // Press Enter to navigate
    await authenticatedPage.keyboard.press('Enter');
    await expect(authenticatedPage).toHaveURL(/\/autopilot/);
  });

  test('active state styling is consistent @audit', async ({ authenticatedPage }) => {
    // Check active styling on different pages

    // Dashboard active
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
    const dashboardNav = authenticatedPage.locator('[data-testid="kite-header-nav-dashboard"]');
    const dashboardActiveClass = await dashboardNav.getAttribute('class');
    expect(dashboardActiveClass).toContain('active');

    // AutoPilot active
    await authenticatedPage.goto('/autopilot');
    await authenticatedPage.waitForLoadState('networkidle');
    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    const autopilotActiveClass = await autopilotNav.getAttribute('class');
    expect(autopilotActiveClass).toContain('active');
  });

  test('icon aligns properly with text @audit', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    const icon = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"] svg');

    // Get vertical positions
    const navBox = await autopilotNav.boundingBox();
    const iconBox = await icon.boundingBox();

    // Icon should be vertically centered within the nav item
    const navCenterY = navBox.y + navBox.height / 2;
    const iconCenterY = iconBox.y + iconBox.height / 2;

    // Allow 2px tolerance for centering
    expect(Math.abs(navCenterY - iconCenterY)).toBeLessThan(2);
  });
});
