/**
 * Navigation Menu - Visual Regression E2E Tests
 *
 * Screenshot tests for AutoPilot navigation menu item.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

// Helper to prepare page for visual testing
async function prepareForVisualTest(page) {
  // Wait for any animations to complete
  await page.waitForLoadState('domcontentloaded');

  // Hide dynamic content that changes between runs
  await page.evaluate(() => {
    // Hide index prices as they change
    const indexPrices = document.querySelector('[data-testid="kite-header-index-prices"]');
    if (indexPrices) {
      indexPrices.style.visibility = 'hidden';
    }

    // Hide connection status dot
    const statusDot = document.querySelector('[data-testid="kite-header-connection-status"]');
    if (statusDot) {
      statusDot.style.visibility = 'hidden';
    }
  });
}

test.describe('Navigation Menu - AutoPilot Visual Tests', () => {

  test('navigation bar with AutoPilot matches baseline @visual', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
    await prepareForVisualTest(authenticatedPage);

    const nav = authenticatedPage.locator('[data-testid="kite-header-nav"]');
    await expect(nav).toHaveScreenshot('navigation-with-autopilot.png', {
      maxDiffPixels: 100,
    });
  });

  test('AutoPilot nav item default state @visual', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
    await prepareForVisualTest(authenticatedPage);

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await expect(autopilotNav).toHaveScreenshot('autopilot-nav-default.png', {
      maxDiffPixels: 50,
    });
  });

  test('AutoPilot nav item hover state @visual', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
    await prepareForVisualTest(authenticatedPage);

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await autopilotNav.hover();
    await authenticatedPage.waitForLoadState('domcontentloaded'); // Wait for hover transition

    await expect(autopilotNav).toHaveScreenshot('autopilot-nav-hover.png', {
      maxDiffPixels: 50,
    });
  });

  test('AutoPilot nav item active state @visual', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/autopilot');
    await authenticatedPage.waitForLoadState('networkidle');
    await prepareForVisualTest(authenticatedPage);

    const autopilotNav = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"]');
    await expect(autopilotNav).toHaveScreenshot('autopilot-nav-active.png', {
      maxDiffPixels: 50,
    });
  });

  test('robot icon renders correctly @visual', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
    await prepareForVisualTest(authenticatedPage);

    const icon = authenticatedPage.locator('[data-testid="kite-header-nav-autopilot"] svg');
    await expect(icon).toHaveScreenshot('autopilot-robot-icon.png', {
      maxDiffPixels: 20,
    });
  });

  test('full header with AutoPilot matches baseline @visual', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
    await prepareForVisualTest(authenticatedPage);

    const header = authenticatedPage.locator('[data-testid="kite-header"]');
    await expect(header).toHaveScreenshot('full-header-with-autopilot.png', {
      maxDiffPixels: 200,
    });
  });
});
