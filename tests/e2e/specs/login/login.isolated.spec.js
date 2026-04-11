/**
 * Login Isolated Tests
 *
 * Tests for login page that need fresh browser context (no auth state).
 * These tests run in the "isolated" project with a fresh browser session.
 * Tag: @isolated
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { LoginPage } from '../../pages/LoginPage.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Login - Isolated Tests @isolated', () => {
  let loginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();
  });

  test('page loads successfully', async ({ page }) => {
    await expect(loginPage.container).toBeVisible();
  });

  test('has correct URL', async ({ page }) => {
    expect(page.url()).toContain('/login');
  });

  test('Zerodha is available in broker dropdown', async () => {
    await expect(loginPage.brokerSelect).toBeVisible();
    const options = await loginPage.brokerSelect.locator('option').allTextContents();
    expect(options.some(o => o.includes('Zerodha'))).toBeTruthy();
  });

  test('Angel One is available in broker dropdown', async () => {
    await expect(loginPage.brokerSelect).toBeVisible();
    const options = await loginPage.brokerSelect.locator('option').allTextContents();
    expect(options.some(o => o.includes('Angel One'))).toBeTruthy();
  });

  test('displays login help sections', async ({ page }) => {
    // Check for help sections present in the current UI
    await expect(page.getByText('Which broker should I select?')).toBeVisible();
    await expect(page.getByText('Is it safe to connect?')).toBeVisible();
    await expect(page.getByText('Having trouble logging in?')).toBeVisible();
  });

  test('safety toggle shows info when clicked', async () => {
    await expect(loginPage.safetyToggle).toBeVisible();
    await loginPage.toggleSafetyInfo();

    // Check safety info content is shown
    const safetyInfo = loginPage.page.getByText("Yes, it's completely safe!");
    await expect(safetyInfo).toBeVisible();
  });
});
