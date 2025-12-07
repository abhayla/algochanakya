/**
 * Visual Helper - Screenshot masking and visual regression utilities
 *
 * Usage:
 *   import { maskDynamicContent, prepareForVisualTest } from '../helpers/visual.helper.js';
 *   await maskDynamicContent(page);
 *   await expect(page).toHaveScreenshot('my-screen.png');
 */

/**
 * Mask all dynamic content (prices, timestamps, etc.) before screenshot
 * This ensures visual tests don't fail due to changing data
 */
export async function maskDynamicContent(page) {
  await page.evaluate(() => {
    // Mask LTP/price values
    document.querySelectorAll('[data-testid*="ltp"], [data-testid*="price"], .ltp, .price').forEach(el => {
      el.textContent = '00,000.00';
    });

    // Mask P/L values
    document.querySelectorAll('[data-testid*="pnl"], .pnl, .profit, .loss').forEach(el => {
      el.textContent = '+0,000';
    });

    // Mask timestamps
    document.querySelectorAll('[data-testid*="time"], [data-testid*="timestamp"], .timestamp, .time').forEach(el => {
      el.textContent = '00:00:00';
    });

    // Mask OI values
    document.querySelectorAll('[data-testid*="oi"]').forEach(el => {
      el.textContent = '0.00L';
    });

    // Mask IV values
    document.querySelectorAll('[data-testid*="iv"]').forEach(el => {
      el.textContent = '00.00';
    });

    // Mask spot prices
    document.querySelectorAll('[data-testid*="spot"]').forEach(el => {
      el.textContent = '00,000';
    });

    // Mask change percentages
    document.querySelectorAll('[data-testid*="change"], .change-percent').forEach(el => {
      el.textContent = '+0.00%';
    });

    // Mask quantities
    document.querySelectorAll('[data-testid*="qty"], [data-testid*="quantity"]').forEach(el => {
      el.textContent = '0';
    });

    // Mask index values in header
    document.querySelectorAll('[data-testid*="index-value"]').forEach(el => {
      el.textContent = '00,000.00';
    });
  });
}

/**
 * Prepare page for visual test - masks content and waits for stability
 */
export async function prepareForVisualTest(page) {
  // Wait for page to be fully loaded
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000); // Allow Vue animations to complete

  // Disable animations for consistent screenshots
  await page.evaluate(() => {
    const style = document.createElement('style');
    style.textContent = `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `;
    document.head.appendChild(style);
  });

  // Mask dynamic content
  await maskDynamicContent(page);
}

/**
 * Get visual comparison options for toHaveScreenshot
 */
export function getVisualCompareOptions(options = {}) {
  return {
    maxDiffPixelRatio: 0.01,
    threshold: 0.2,
    animations: 'disabled',
    ...options
  };
}

/**
 * Standard viewports for responsive testing
 */
export const VIEWPORTS = {
  desktop: { width: 1920, height: 1080 },
  laptop: { width: 1440, height: 900 },
  tablet: { width: 1024, height: 768 },
  mobile: { width: 375, height: 667 }
};

/**
 * Set viewport and prepare for visual test
 */
export async function setViewportAndPrepare(page, viewportName) {
  const viewport = VIEWPORTS[viewportName] || VIEWPORTS.desktop;
  await page.setViewportSize(viewport);
  await page.waitForTimeout(500); // Allow responsive adjustments
  await prepareForVisualTest(page);
}

/**
 * Ensure consistent viewport for visual regression tests
 * Call before screenshots when using maximized browser window
 */
export async function ensureConsistentViewport(page, viewportName = 'desktop') {
  const viewport = VIEWPORTS[viewportName] || VIEWPORTS.desktop;
  await page.setViewportSize(viewport);
  await page.waitForTimeout(200); // Allow responsive adjustments
}

/**
 * Combined preparation: set viewport + prepare for visual test
 * Use this for all visual regression tests to ensure consistency
 */
export async function prepareVisualTestWithViewport(page, viewportName = 'desktop') {
  await ensureConsistentViewport(page, viewportName);
  await prepareForVisualTest(page);
}
