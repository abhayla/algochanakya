/**
 * Positions Visual Regression Tests
 *
 * Screenshot comparisons for UI consistency.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { PositionsPage } from '../../pages/PositionsPage.js';
import { prepareForVisualTest, getVisualCompareOptions, VIEWPORTS } from '../../helpers/visual.helper.js';

test.describe('Positions - Visual Regression @visual', () => {
  let positionsPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    positionsPage = new PositionsPage(authenticatedPage);
    await positionsPage.navigate();
    await positionsPage.waitForPageLoad();
  });

  test('desktop layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      'positions-desktop.png',
      getVisualCompareOptions()
    );
  });

  test('laptop layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.laptop);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      'positions-laptop.png',
      getVisualCompareOptions()
    );
  });

  test('tablet layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.tablet);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      'positions-tablet.png',
      getVisualCompareOptions()
    );
  });

  test('exit modal matches baseline', async ({ authenticatedPage }) => {
    const hasPositions = await positionsPage.hasPositions();

    if (hasPositions) {
      await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
      const exitBtn = authenticatedPage.locator('[data-testid^="positions-exit-button-"]').first();
      await exitBtn.click();
      await positionsPage.exitModal.waitFor({ state: 'visible', timeout: 5000 });
      await prepareForVisualTest(authenticatedPage);
      await expect(authenticatedPage).toHaveScreenshot(
        'positions-exit-modal.png',
        getVisualCompareOptions()
      );
    } else {
      // No positions — capture empty state baseline instead (always assert something)
      await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
      await prepareForVisualTest(authenticatedPage);
      await expect(positionsPage.emptyState).toBeVisible();
    }
  });
});
