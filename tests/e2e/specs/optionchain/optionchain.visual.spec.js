import { test, expect } from '../../fixtures/auth.fixture.js';
import OptionChainPage from '../../pages/OptionChainPage.js';
import { prepareForVisualTest, VIEWPORTS } from '../../helpers/visual.helper.js';

/**
 * Option Chain Screen - Visual Regression Tests
 * Tests layout and visual appearance across viewports
 */
test.describe('Option Chain - Visual Regression @visual', () => {
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
  });

  test('should match desktop layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('optionchain-desktop.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="optionchain-spot-price"]'),
        page.locator('[data-testid="optionchain-dte-value"]'),
        page.locator('[data-testid^="optionchain-strike-row-"]')
      ]
    });
  });

  test('should match laptop layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.laptop);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('optionchain-laptop.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="optionchain-spot-price"]'),
        page.locator('[data-testid="optionchain-dte-value"]'),
        page.locator('[data-testid^="optionchain-strike-row-"]')
      ]
    });
  });

  test('should match tablet layout', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    await prepareForVisualTest(page);
    await expect(page).toHaveScreenshot('optionchain-tablet.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="optionchain-spot-price"]'),
        page.locator('[data-testid="optionchain-dte-value"]'),
        page.locator('[data-testid^="optionchain-strike-row-"]')
      ]
    });
  });

  test('should match summary bar appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    await prepareForVisualTest(page);
    await expect(optionChainPage.summaryBar).toHaveScreenshot('optionchain-summary-bar.png', {
      mask: [
        page.locator('[data-testid="optionchain-pcr"]'),
        page.locator('[data-testid="optionchain-max-pain"]'),
        page.locator('[data-testid="optionchain-ce-oi"]'),
        page.locator('[data-testid="optionchain-pe-oi"]')
      ]
    });
  });

  test('should match header appearance', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
    await prepareForVisualTest(page);
    await expect(optionChainPage.header).toHaveScreenshot('optionchain-header.png', {
      mask: [
        page.locator('[data-testid="optionchain-spot-price"]'),
        page.locator('[data-testid="optionchain-dte-value"]')
      ]
    });
  });
});
