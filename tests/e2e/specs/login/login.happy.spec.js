/**
 * Login Happy Path Tests
 *
 * Tests for normal user flows and expected behavior.
 */

import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Login - Happy Path @happy', () => {
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

  test('Zerodha login button is visible and default', async () => {
    await expect(loginPage.zerodhaButton).toBeVisible();
    await expect(loginPage.zerodhaButton).toContainText('Zerodha');
  });

  test('Angel One login button is visible', async () => {
    await expect(loginPage.angelOneButton).toBeVisible();
    await expect(loginPage.angelOneButton).toContainText('Angel One');
  });

  test('displays platform features', async ({ page }) => {
    // Check for feature descriptions
    await expect(page.getByText('Advanced Strategy Builder')).toBeVisible();
    await expect(page.getByText('Live Market Data')).toBeVisible();
    await expect(page.getByText('Secure Broker Integration')).toBeVisible();
  });

  test('safety toggle shows info when clicked', async () => {
    await expect(loginPage.safetyToggle).toBeVisible();
    await loginPage.toggleSafetyInfo();

    // Check safety info content is shown
    const safetyInfo = loginPage.page.getByText("Yes, it's completely safe!");
    await expect(safetyInfo).toBeVisible();
  });
});
