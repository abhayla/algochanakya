/**
 * Dashboard Visual Regression Tests
 *
 * Screenshot comparisons for UI consistency.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { DashboardPage } from '../../pages/DashboardPage.js';
import { prepareForVisualTest, getVisualCompareOptions, VIEWPORTS } from '../../helpers/visual.helper.js';

test.describe('Dashboard - Visual Regression @visual', () => {
  let dashboardPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    dashboardPage = new DashboardPage(authenticatedPage);
    await dashboardPage.navigate();
    await dashboardPage.waitForPageLoad();
  });

  test('desktop layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      'dashboard-desktop.png',
      getVisualCompareOptions()
    );
  });

  test('laptop layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.laptop);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      'dashboard-laptop.png',
      getVisualCompareOptions()
    );
  });
});
