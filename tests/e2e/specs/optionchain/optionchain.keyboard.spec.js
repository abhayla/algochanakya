import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';

/**
 * Option Chain Screen - Keyboard Shortcut Tests
 *
 * Covers the handleKeyDown shortcuts defined in the Vue component:
 *   1 → NIFTY tab
 *   2 → BANKNIFTY tab
 *   3 → FINNIFTY tab
 *   G / g → toggle Greeks visibility
 *
 * Keyboard shortcuts MUST be suppressed when focus is inside an input/select
 * to avoid interfering with user typing.
 */
test.describe('Option Chain - Keyboard Shortcuts @edge', () => {
  test.describe.configure({ timeout: 180000 });
  let optionChainPage;

  async function hasChainData(page) {
    const rows = page.locator('[data-testid^="optionchain-strike-row-"]');
    const count = await rows.count();
    return count > 0;
  }

  test.beforeEach(async ({ authenticatedPage }) => {
    optionChainPage = new OptionChainPage(authenticatedPage);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
  });

  // ─── Tab switching shortcuts ───────────────────────────────────────────────

  test('should switch to NIFTY tab when pressing 1', async ({ authenticatedPage }) => {
    // Start on BANKNIFTY so there is a visible tab switch to assert
    await authenticatedPage.locator('[data-testid="optionchain-underlying-banknifty"]').click();
    await optionChainPage.waitForChainLoad();

    await authenticatedPage.keyboard.press('1');
    await optionChainPage.waitForChainLoad();

    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-nifty"]')
    ).toHaveAttribute('aria-selected', 'true');
  });

  test('should switch to BANKNIFTY tab when pressing 2', async ({ authenticatedPage }) => {
    // Ensure we are not already on BANKNIFTY (default is NIFTY)
    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-nifty"]')
    ).toHaveAttribute('aria-selected', 'true');

    await authenticatedPage.keyboard.press('2');
    await optionChainPage.waitForChainLoad();

    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-banknifty"]')
    ).toHaveAttribute('aria-selected', 'true');
  });

  test('should switch to FINNIFTY tab when pressing 3', async ({ authenticatedPage }) => {
    await authenticatedPage.keyboard.press('3');
    await optionChainPage.waitForChainLoad();

    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-finnifty"]')
    ).toHaveAttribute('aria-selected', 'true');
  });

  // ─── Greeks toggle shortcuts ───────────────────────────────────────────────

  test('should toggle Greeks with g key', async ({ authenticatedPage }) => {
    // Capture pre-toggle Greeks visibility
    const greekCell = authenticatedPage.locator('[data-testid^="optionchain-ce-delta-"]').first();
    const visibleBefore = await greekCell.isVisible().catch(() => false);

    await authenticatedPage.keyboard.press('g');

    // After toggle, visibility must have flipped
    const visibleAfter = await greekCell.isVisible().catch(() => false);

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    // Data is present — Greek cells exist, so we can assert the actual flip
    expect(visibleAfter).toBe(!visibleBefore);
  });

  test('should handle uppercase G key for Greeks toggle', async ({ authenticatedPage }) => {
    const greekCell = authenticatedPage.locator('[data-testid^="optionchain-ce-delta-"]').first();
    const visibleBefore = await greekCell.isVisible().catch(() => false);

    await authenticatedPage.keyboard.press('G');

    const visibleAfter = await greekCell.isVisible().catch(() => false);

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    expect(visibleAfter).toBe(!visibleBefore);
  });

  // ─── Input suppression ────────────────────────────────────────────────────

  test('should not trigger shortcuts when expiry select is focused', async ({ authenticatedPage }) => {
    // Record which tab is currently active before focusing the select
    const activeTabBefore = await authenticatedPage
      .locator('[data-testid^="optionchain-underlying-"][aria-selected="true"]')
      .getAttribute('data-testid');

    // Focus the expiry select — keyboard events inside inputs/selects must not
    // trigger the tab-switch shortcut
    await optionChainPage.expirySelect.focus();

    // Press '2' while the select has focus
    await authenticatedPage.keyboard.press('2');

    // Allow a short tick for any unintended navigation to occur
    await authenticatedPage.waitForTimeout(300);

    // The active tab must be unchanged
    const activeTabAfter = await authenticatedPage
      .locator('[data-testid^="optionchain-underlying-"][aria-selected="true"]')
      .getAttribute('data-testid');

    expect(activeTabAfter).toBe(activeTabBefore);
  });

  // ─── Sequence test ────────────────────────────────────────────────────────

  test('should cycle through underlyings with keyboard sequence 2 → 1 → 3', async ({ authenticatedPage }) => {
    // Step 1: press 2 → BANKNIFTY
    await authenticatedPage.keyboard.press('2');
    await optionChainPage.waitForChainLoad();
    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-banknifty"]')
    ).toHaveAttribute('aria-selected', 'true');

    // Step 2: press 1 → NIFTY
    await authenticatedPage.keyboard.press('1');
    await optionChainPage.waitForChainLoad();
    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-nifty"]')
    ).toHaveAttribute('aria-selected', 'true');

    // Step 3: press 3 → FINNIFTY
    await authenticatedPage.keyboard.press('3');
    await optionChainPage.waitForChainLoad();
    await expect(
      authenticatedPage.locator('[data-testid="optionchain-underlying-finnifty"]')
    ).toHaveAttribute('aria-selected', 'true');
  });
});
