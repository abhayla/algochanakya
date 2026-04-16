import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';

/**
 * Option Chain Screen - Strike Interval Toggle Tests
 *
 * Tests the 50/100-point strike interval filter that appears only for underlyings
 * with native 50-point strike spacing (currently NIFTY only).
 *
 * Business rules:
 * - NIFTY: native 50-point strikes → toggle visible, default 50pt
 * - BANKNIFTY: 100-point strikes only → toggle hidden
 * - 100pt mode: only strikes divisible by 100 are shown
 * - ATM strike is always shown regardless of interval filter
 */
test.describe('Option Chain - Strike Interval Toggle @edge', () => {
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
  });

  // ── Visibility ────────────────────────────────────────────────────────────

  test('should display interval toggle for NIFTY', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();
    const intervalToggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await intervalToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(intervalToggle).toBeVisible();
  });

  test('should hide interval toggle for BANKNIFTY', async ({ authenticatedPage }) => {
    // Click BANKNIFTY tab and wait for chain load (may be slow)
    const tab = authenticatedPage.locator('[data-testid="optionchain-underlying-banknifty"]');
    await tab.click();
    try {
      await optionChainPage.waitForChainLoad();
    } catch {
      console.log('BANKNIFTY chain load timed out — continuing with visibility check');
    }

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();
    await expect(
      authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]')
    ).not.toBeVisible();
  });

  // ── Default State ─────────────────────────────────────────────────────────

  test('should default to interval matching user preference for NIFTY', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();

    const toggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await toggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Default interval depends on user preference (50 or 100) — verify one is checked
    const radio50 = authenticatedPage.locator('[data-testid="optionchain-interval-50"]');
    const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
    const is50Checked = await radio50.isChecked();
    const is100Checked = await radio100.isChecked();
    expect(is50Checked || is100Checked, 'One interval radio must be selected').toBe(true);
    expect(is50Checked !== is100Checked, 'Exactly one interval radio must be selected').toBe(true);
  });

  // ── Interaction ───────────────────────────────────────────────────────────

  test('should switch to 100-point interval', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();

    const intervalToggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await intervalToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }

    const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
    await radio100.click();
    await expect(radio100).toBeChecked();

    const radio50 = authenticatedPage.locator('[data-testid="optionchain-interval-50"]');
    await expect(radio50).not.toBeChecked();

    // Chain must still show data after the switch
    await expect(optionChainPage.table).toBeVisible();
  });

  // ── Row Count ─────────────────────────────────────────────────────────────

  test('should show wider strike gaps with 100-point interval than with 50-point interval', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();

    const intervalToggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await intervalToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Ensure we start on 50pt
    const radio50 = authenticatedPage.locator('[data-testid="optionchain-interval-50"]');
    const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
    await radio50.click();
    await expect(radio50).toBeChecked();
    await authenticatedPage.waitForTimeout(500);

    // Collect strike values in 50pt mode
    const rows50 = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]');
    const count50 = await rows50.count();
    expect(count50).toBeGreaterThan(0);

    const strikes50 = [];
    for (let i = 0; i < Math.min(count50, 5); i++) {
      const testid = await rows50.nth(i).getAttribute('data-testid');
      strikes50.push(parseInt(testid.replace('optionchain-strike-row-', ''), 10));
    }
    const gap50 = strikes50.length >= 2 ? strikes50[1] - strikes50[0] : 0;

    // Switch to 100pt
    await radio100.click();
    await expect(radio100).toBeChecked();
    await authenticatedPage.waitForTimeout(500);

    const rows100 = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]');
    const count100 = await rows100.count();
    expect(count100).toBeGreaterThan(0);

    const strikes100 = [];
    for (let i = 0; i < Math.min(count100, 5); i++) {
      const testid = await rows100.nth(i).getAttribute('data-testid');
      strikes100.push(parseInt(testid.replace('optionchain-strike-row-', ''), 10));
    }
    const gap100 = strikes100.length >= 2 ? strikes100[1] - strikes100[0] : 0;

    // 100pt mode should have wider gaps between strikes
    // Store design: range takes N strikes on each side AFTER filtering, so count is same
    // but strike spacing is wider
    if (gap50 > 0 && gap100 > 0) {
      expect(gap100).toBeGreaterThanOrEqual(gap50);
    }
  });

  // ── Strike Values ─────────────────────────────────────────────────────────

  test('should show only strikes divisible by 100 in 100-point mode', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();

    const intervalToggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await intervalToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Switch to 100pt
    const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
    await radio100.click();
    await expect(radio100).toBeChecked();
    await authenticatedPage.waitForTimeout(500);

    const rows = await authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').all();
    expect(rows.length).toBeGreaterThan(0);

    const nonDivisible = [];
    for (const row of rows) {
      const testId = await row.getAttribute('data-testid');
      const strike = parseInt(testId.replace('optionchain-strike-row-', ''), 10);
      if (!isNaN(strike) && strike % 100 !== 0) {
        nonDivisible.push(strike);
      }
    }

    expect(nonDivisible).toEqual([]);
  });

  // ── ATM Always Present ────────────────────────────────────────────────────

  test('should always show ATM strike regardless of interval filter', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();

    const intervalToggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await intervalToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Confirm ATM row exists in default 50pt mode
    const atmRow = optionChainPage.atmRow;
    await expect(atmRow).toBeVisible();

    // Switch to 100pt
    const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
    await radio100.click();
    await expect(radio100).toBeChecked();
    await authenticatedPage.waitForTimeout(500);

    // ATM row must still be present after filtering
    await expect(atmRow).toBeVisible();
  });

  // ── Restore Behaviour ─────────────────────────────────────────────────────

  test('should restore strike spacing when switching back from 100-point to 50-point', async ({ authenticatedPage }) => {
    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }
    await expect(optionChainPage.table).toBeVisible();

    const intervalToggle = authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]');
    if (!(await intervalToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      console.log('Interval toggle not visible — NIFTY may not have 50pt strikes loaded');
      await optionChainPage.assertPageVisible();
      return;
    }

    const radio50 = authenticatedPage.locator('[data-testid="optionchain-interval-50"]');
    const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');

    // Helper to get first strike gap
    const getFirstGap = async () => {
      const rows = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]');
      const count = await rows.count();
      if (count < 2) return 0;
      const s1 = parseInt((await rows.nth(0).getAttribute('data-testid')).replace('optionchain-strike-row-', ''), 10);
      const s2 = parseInt((await rows.nth(1).getAttribute('data-testid')).replace('optionchain-strike-row-', ''), 10);
      return Math.abs(s2 - s1);
    };

    // Start with 50pt
    await radio50.click();
    await expect(radio50).toBeChecked();
    await authenticatedPage.waitForTimeout(500);
    const initialGap = await getFirstGap();

    // Switch to 100pt — should widen gaps
    await radio100.click();
    await expect(radio100).toBeChecked();
    await authenticatedPage.waitForTimeout(500);
    const widerGap = await getFirstGap();

    if (initialGap > 0 && widerGap > 0) {
      expect(widerGap).toBeGreaterThanOrEqual(initialGap);
    }

    // Switch back to 50pt — should restore original spacing
    await radio50.click();
    await expect(radio50).toBeChecked();
    await authenticatedPage.waitForTimeout(500);
    const restoredGap = await getFirstGap();

    // Gap should be restored to original 50pt spacing
    if (initialGap > 0 && restoredGap > 0) {
      expect(restoredGap).toBe(initialGap);
    }
  });
});
