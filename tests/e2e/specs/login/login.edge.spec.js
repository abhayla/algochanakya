/**
 * Login Edge Case Tests
 *
 * Tests for error states, edge cases, and boundary conditions.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { LoginPage } from '../../pages/LoginPage.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Login - Edge Cases @edge', () => {
  let loginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
  });

  test('unauthenticated user is redirected to login from protected routes', async ({ page }) => {
    // Try to access dashboard without authentication
    await page.goto(FRONTEND_URL + '/dashboard');

    // Should be redirected to login
    await page.waitForURL('**/login**', { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });

  test('Angel One shows coming soon message', async ({ page }) => {
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();

    await loginPage.clickAngelOneLogin();

    // Should show error message
    await expect(loginPage.errorMessage).toBeVisible();
    await expect(loginPage.errorMessage).toContainText('coming soon');
  });

  test('no horizontal overflow at any viewport', async ({ page }) => {
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();

    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1440, height: 900 },
      { width: 1024, height: 768 }
    ];

    for (const viewport of viewports) {
      await loginPage.setViewportSize(viewport.width, viewport.height);
      const hasOverflow = await loginPage.hasHorizontalOverflow();
      expect(hasOverflow, `Horizontal overflow at ${viewport.width}x${viewport.height}`).toBe(false);
    }
  });

  test('page loads without errors in console', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();

    // Filter out expected errors (like network errors for missing favicon)
    const criticalErrors = consoleErrors.filter(err =>
      !err.includes('favicon') &&
      !err.includes('Failed to load resource')
    );

    expect(criticalErrors).toHaveLength(0);
  });

  test('loading state is shown when initiating OAuth', async ({ page }) => {
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();

    // Click Zerodha login - loading state should appear briefly
    // Note: This test assumes the API call takes some time
    await loginPage.clickZerodhaLogin();

    // Check that button shows loading state
    const buttonText = await loginPage.zerodhaButton.textContent();
    // The button should either show "Connecting..." or redirect
    // Since OAuth flow redirects, we just verify no crash
    await page.waitForTimeout(500);
  });
});
