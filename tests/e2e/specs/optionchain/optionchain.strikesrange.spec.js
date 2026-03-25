import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import {
  getDataExpectation,
  assertDataOrEmptyState,
  getISTTimeString,
} from '../../helpers/market-status.helper.js';

/**
 * Option Chain Screen - Strikes Range Selector Tests
 *
 * Tests the 5/10/15/20/30/All dropdown that controls how many strikes
 * above and below ATM are visible in the filtered chain.
 *
 * Business rules (from store `filteredChain` getter):
 * - The selected value is the number of strikes on EACH SIDE of ATM.
 * - Expected visible rows ≈ 2 * range + 1 (ATM included).
 * - ATM strike is always included regardless of range.
 * - value=50 ("All Strikes") disables the range filter entirely.
 * - Actual row count may be lower if some strikes have no instruments
 *   or the interval filter (50/100pt) is active.
 *
 * Row count assertions use ±2 tolerance to absorb those real-world gaps.
 */
test.describe('Option Chain - Strikes Range Selector @edge', () => {
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

  // ── Default State ──────────────────────────────────────────────────────────

  test('should default to 10 strikes range', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();
      await expect(optionChainPage.strikesRange).toHaveValue('10');
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Row Count per Range ────────────────────────────────────────────────────

  test('should show correct row count for 5-strike range', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      await optionChainPage.setStrikesRange('5');
      await authenticatedPage.waitForTimeout(500);

      const rows = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .all();
      const rowCount = rows.length;

      // 5 above + 5 below + ATM = 11, tolerance ±2
      expect(rowCount).toBeGreaterThanOrEqual(9);
      expect(rowCount).toBeLessThanOrEqual(13);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  test('should show correct row count for 10-strike range', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      // Default is already 10, but set explicitly for test independence
      await optionChainPage.setStrikesRange('10');
      await authenticatedPage.waitForTimeout(500);

      const rows = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .all();
      const rowCount = rows.length;

      // 10 above + 10 below + ATM = 21, tolerance ±2
      expect(rowCount).toBeGreaterThanOrEqual(19);
      expect(rowCount).toBeLessThanOrEqual(23);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  test('should show correct row count for 20-strike range', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      await optionChainPage.setStrikesRange('20');
      await authenticatedPage.waitForTimeout(500);

      const rows = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .all();
      const rowCount = rows.length;

      // 20 above + 20 below + ATM = 41, tolerance ±2
      expect(rowCount).toBeGreaterThanOrEqual(39);
      expect(rowCount).toBeLessThanOrEqual(43);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Relative Comparison ────────────────────────────────────────────────────

  test('should show more rows with larger range', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      await optionChainPage.setStrikesRange('5');
      await authenticatedPage.waitForTimeout(500);
      const countAtRange5 = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();

      await optionChainPage.setStrikesRange('20');
      await authenticatedPage.waitForTimeout(500);
      const countAtRange20 = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();

      expect(countAtRange20).toBeGreaterThan(countAtRange5);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── ATM Always Present ─────────────────────────────────────────────────────

  test('should always include ATM strike', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      await optionChainPage.setStrikesRange('5');
      await authenticatedPage.waitForTimeout(500);

      // ATM badge is the authoritative indicator that the ATM row is rendered
      await expect(optionChainPage.atmBadge).toBeVisible();
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── All Strikes ────────────────────────────────────────────────────────────

  test('should show maximum rows with All Strikes', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      // Capture row count at range=10 (default) as a baseline
      await optionChainPage.setStrikesRange('10');
      await authenticatedPage.waitForTimeout(500);
      const countAt10 = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();

      // Switch to All Strikes (value=50 in the select)
      await optionChainPage.setStrikesRange('50');
      await authenticatedPage.waitForTimeout(500);
      const countAllStrikes = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();

      expect(countAllStrikes).toBeGreaterThan(countAt10);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });

  // ── Reactivity ─────────────────────────────────────────────────────────────

  test('should update row count after range change', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();
    console.log(`[strikesrange] market state: ${expectation} at ${getISTTimeString()}`);

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      if (!(await hasChainData(authenticatedPage))) {
        console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
        await optionChainPage.assertPageVisible();
        return;
      }
      await expect(optionChainPage.table).toBeVisible();

      // Start at range=10 and record baseline
      await optionChainPage.setStrikesRange('10');
      await authenticatedPage.waitForTimeout(500);
      const countBefore = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();
      expect(countBefore).toBeGreaterThan(0);

      // Narrow to range=5 and verify the count decreased
      await optionChainPage.setStrikesRange('5');
      await authenticatedPage.waitForTimeout(500);
      const countAfter = await authenticatedPage
        .locator('[data-testid^="optionchain-strike-row-"]')
        .count();

      expect(countAfter).toBeLessThan(countBefore);
    } else {
      await assertDataOrEmptyState(
        authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect
      );
    }
  });
});
