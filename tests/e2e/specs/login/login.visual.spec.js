/**
 * Login Visual Regression Tests
 *
 * Screenshot comparisons for UI consistency.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { LoginPage } from '../../pages/LoginPage.js';
import { prepareForVisualTest, getVisualCompareOptions, VIEWPORTS } from '../../helpers/visual.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('Login - Visual Regression @visual', () => {
  let loginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await page.goto(FRONTEND_URL + '/login');
    await loginPage.waitForPageLoad();
  });

  test('desktop layout matches baseline', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot(
      'login-desktop.png',
      getVisualCompareOptions()
    );
  });

  test('laptop layout matches baseline', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.laptop);
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot(
      'login-laptop.png',
      getVisualCompareOptions()
    );
  });

  test('tablet layout matches baseline', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet);
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot(
      'login-tablet.png',
      getVisualCompareOptions()
    );
  });

  test('safety info expanded state matches baseline', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await loginPage.toggleSafetyInfo();
    await page.waitForLoadState('domcontentloaded'); // Wait for expand animation
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot(
      'login-safety-info.png',
      getVisualCompareOptions()
    );
  });

  test('error state matches baseline', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await loginPage.clickAngelOneLogin(); // Triggers error message
    await page.waitForLoadState('domcontentloaded');
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot(
      'login-error.png',
      getVisualCompareOptions()
    );
  });
});
