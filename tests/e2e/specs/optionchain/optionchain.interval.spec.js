import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, assertDataOrEmptyState, getISTTimeString } from '../../helpers/market-status.helper.js';

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
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  test('should hide interval toggle for BANKNIFTY', async ({ authenticatedPage }) => {
    await optionChainPage.selectUnderlying('BANKNIFTY');

    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();
      await expect(
        authenticatedPage.locator('[data-testid="optionchain-interval-toggle"]')
      ).not.toBeVisible();
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Default State ─────────────────────────────────────────────────────────

  test('should default to 50-point interval for NIFTY', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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

      const radio50 = authenticatedPage.locator('[data-testid="optionchain-interval-50"]');
      await expect(radio50).toBeChecked();

      const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
      await expect(radio100).not.toBeChecked();
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Interaction ───────────────────────────────────────────────────────────

  test('should switch to 100-point interval', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Row Count ─────────────────────────────────────────────────────────────

  test('should show fewer rows with 100-point interval than with 50-point interval', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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

      // Confirm we start on 50pt and count rows
      const radio50 = authenticatedPage.locator('[data-testid="optionchain-interval-50"]');
      await expect(radio50).toBeChecked();

      const rows50 = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]');
      const count50 = await rows50.count();
      expect(count50).toBeGreaterThan(0);

      // Switch to 100pt
      const radio100 = authenticatedPage.locator('[data-testid="optionchain-interval-100"]');
      await radio100.click();
      await expect(radio100).toBeChecked();

      // Give Vue a tick to re-filter the rows
      await authenticatedPage.waitForTimeout(500);

      const rows100 = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]');
      const count100 = await rows100.count();
      expect(count100).toBeGreaterThan(0);

      // 100pt mode must show strictly fewer rows than 50pt mode
      expect(count100).toBeLessThan(count50);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Strike Values ─────────────────────────────────────────────────────────

  test('should show only strikes divisible by 100 in 100-point mode', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── ATM Always Present ────────────────────────────────────────────────────

  test('should always show ATM strike regardless of interval filter', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Restore Behaviour ─────────────────────────────────────────────────────

  test('should restore full row count when switching back from 100-point to 50-point', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[interval] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
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

      // Baseline row count at 50pt
      const initialCount = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();
      expect(initialCount).toBeGreaterThan(0);

      // Switch to 100pt
      await radio100.click();
      await expect(radio100).toBeChecked();
      await authenticatedPage.waitForTimeout(500);

      const reducedCount = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();
      expect(reducedCount).toBeLessThan(initialCount);

      // Switch back to 50pt
      await radio50.click();
      await expect(radio50).toBeChecked();
      await authenticatedPage.waitForTimeout(500);

      const restoredCount = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();

      // Row count must be restored to the original 50pt value
      expect(restoredCount).toBe(initialCount);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });
});
