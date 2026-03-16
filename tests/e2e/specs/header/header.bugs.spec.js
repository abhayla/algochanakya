/**
 * Header Bug Reproduction Tests
 *
 * Bugs:
 * HEADER-BUG-1: User ID is truncated in the header (MAAW1001 shows as MAAW)
 * HEADER-BUG-2: NIFTY BANK and FIN NIFTY should be removed from header
 *               (they consume space and cause user ID to be clipped)
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { KiteHeaderPage } from '../../pages/KiteHeaderPage.js';

test.describe('Header Bugs @bugs', () => {
  test.describe.configure({ mode: 'serial' });

  let headerPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    headerPage = new KiteHeaderPage(authenticatedPage);
    await headerPage.navigate();
    await headerPage.waitForLoad();
  });

  // ─── HEADER-BUG-1: User ID fully visible ────────────────────────────────────
  test('HEADER-BUG-1: user ID should be fully visible without truncation', async ({ authenticatedPage }) => {
    const userMenu = authenticatedPage.locator('[data-testid="kite-header-user-menu"]');
    await expect(userMenu).toBeVisible();

    const userId = userMenu.locator('.user-id');
    await expect(userId).toBeVisible();

    // Get the rendered text and bounding box
    const text = await userId.textContent();
    const box = await userId.boundingBox();
    const headerBox = await authenticatedPage.locator('[data-testid="kite-header"]').boundingBox();

    expect(text.trim().length).toBeGreaterThan(0);

    // BUG: user ID is clipped by header overflow — right edge of text must be within header
    expect(box.x + box.width).toBeLessThanOrEqual(headerBox.x + headerBox.width + 1);

    // The user-id element must not overflow its container (no clipping)
    const isClipped = await userId.evaluate(el => {
      return el.scrollWidth > el.clientWidth;
    });
    expect(isClipped).toBe(false, `User ID "${text.trim()}" is being clipped/truncated`);
  });

  // ─── HEADER-BUG-2: NIFTY BANK removed from header ───────────────────────────
  test('HEADER-BUG-2: NIFTY BANK index should not be shown in header', async ({ authenticatedPage }) => {
    const niftyBank = authenticatedPage.locator('[data-testid="kite-header-index-niftybank"]');
    // BUG: NIFTY BANK is shown, consuming space that causes user ID truncation
    await expect(niftyBank).not.toBeVisible();
  });

  // ─── HEADER-BUG-2: FIN NIFTY removed from header ────────────────────────────
  test('HEADER-BUG-2: FIN NIFTY index should not be shown in header', async ({ authenticatedPage }) => {
    const finNifty = authenticatedPage.locator('[data-testid="kite-header-index-finnifty"]');
    // BUG: FIN NIFTY is shown, consuming space that causes user ID truncation
    await expect(finNifty).not.toBeVisible();
  });

  // ─── NIFTY 50 and SENSEX must still be present ──────────────────────────────
  test('NIFTY 50 and SENSEX should still be visible in header', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('[data-testid="kite-header-index-nifty50"]')).toBeVisible();
    await expect(authenticatedPage.locator('[data-testid="kite-header-index-sensex"]')).toBeVisible();
  });
});
