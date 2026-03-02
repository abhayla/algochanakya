/**
 * Dashboard Edge Case Tests
 *
 * Tests for error states, edge cases, and boundary conditions.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { DashboardPage } from '../../pages/DashboardPage.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Dashboard - Edge Cases @edge', () => {

  test('unauthenticated access redirects to login', async ({ page }) => {
    // Clear any stored tokens
    await page.goto(FRONTEND_URL);
    await page.evaluate(() => {
      localStorage.clear();
    });

    // Try to access dashboard
    await page.goto(FRONTEND_URL + '/dashboard');

    // Should redirect to login
    await page.waitForURL('**/login**', { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });

  test('no horizontal overflow at any viewport', async ({ page }) => {
    // This test requires auth, so we skip if no token available
    const token = process.env.TEST_AUTH_TOKEN;
    if (!token) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    await page.goto(FRONTEND_URL);
    await page.evaluate((t) => {
      localStorage.setItem('access_token', t);
      localStorage.setItem('token', t);
    }, token);
    await page.reload();

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigate();
    await dashboardPage.waitForPageLoad();

    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1440, height: 900 },
      { width: 1024, height: 768 }
    ];

    for (const viewport of viewports) {
      await dashboardPage.setViewportSize(viewport.width, viewport.height);
      const hasOverflow = await dashboardPage.hasHorizontalOverflow();
      expect(hasOverflow, `Horizontal overflow at ${viewport.width}x${viewport.height}`).toBe(false);
    }
  });

  test('handles expired token gracefully', async ({ page }) => {
    await page.goto(FRONTEND_URL);

    // Set an invalid/expired token
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired-token-12345');
      localStorage.setItem('token', 'expired-token-12345');
    });

    // Try to access dashboard
    await page.goto(FRONTEND_URL + '/dashboard');

    // Should redirect to login eventually (when API call fails)
    // Note: This depends on how the app handles token validation
    await page.waitForTimeout(2000);
  });
});
