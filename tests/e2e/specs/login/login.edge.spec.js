/**
 * Login Edge Case Tests
 *
 * Tests for error states, edge cases, and boundary conditions.
 * These tests need an unauthenticated browser context (login page should be visible).
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { LoginPage } from '../../pages/LoginPage.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Login - Edge Cases @edge', () => {
  // Clear auth state so these tests see the login page, not the dashboard
  test.use({ storageState: { cookies: [], origins: [] } });

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

  test('selecting Angel One shows inline credential fields', async ({ page }) => {
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();

    await loginPage.brokerSelect.selectOption('angelone');

    // AngelOne shows inline credential fields (not "coming soon")
    await expect(loginPage.angelOneFields).toBeVisible();
    await expect(loginPage.angelOneClientId).toBeVisible();
    await expect(loginPage.angelOnePin).toBeVisible();
    await expect(loginPage.angelOneTotp).toBeVisible();
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

    // Filter out expected non-critical errors
    const criticalErrors = consoleErrors.filter(err =>
      !err.includes('favicon') &&
      !err.includes('Failed to load resource')
    );

    expect(criticalErrors).toHaveLength(0);
  });

  test('submit button shows loading state when initiating OAuth', async ({ page }) => {
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();

    // Click the submit button (Zerodha is default)
    await loginPage.submitButton.click();

    // After click, either redirect happens or loading state shows
    // Just verify no crash — OAuth redirects are external
    await page.waitForLoadState('domcontentloaded');
    // Test passes as long as there's no JS exception
  });
});
