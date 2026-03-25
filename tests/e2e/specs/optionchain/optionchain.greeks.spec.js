import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, getISTTimeString } from '../../helpers/market-status.helper.js';

/**
 * Option Chain - Greeks Column Visibility Tests
 *
 * Tests the Greeks toggle (Delta, Gamma, Theta, Vega columns) on the option chain table.
 * Greeks default to ON (showGreeks: true in store). The toggle hides/shows all four
 * Greek columns on both CE and PE sides simultaneously.
 *
 * Data sensitivity: Greek cell values are only populated when the broker returns valid
 * option data. Tests that inspect cell content gate on getDataExpectation() to avoid
 * false failures during market close or when instrument data is unavailable.
 */
test.describe('Option Chain - Greeks Visibility @edge', () => {
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

  // ─── Test 1: Toggle element is present ──────────────────────────────────────

  test('should display Greeks toggle', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
  });

  // ─── Test 2: Greeks columns visible by default ───────────────────────────────

  test('should show Greeks columns by default', async ({ authenticatedPage }) => {
    const chainState = await optionChainPage.waitForChainLoad();

    if (chainState === 'error') {
      test.skip('Option chain returned an error — cannot assert Greek column visibility');
      return;
    }

    const expectation = getDataExpectation();
    if (expectation === 'CLOSED') {
      // Under CLOSED state the chain may show empty state — still assert toggle visible
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      console.log(`[Greeks] Market CLOSED (${getISTTimeString()}) — asserting toggle only`);
      return;
    }

    // Table must be present for column assertions
    await expect(optionChainPage.table).toBeVisible();

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Resolve a strike from the first rendered row
    const firstRow = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').first();
    await firstRow.waitFor({ state: 'visible', timeout: 15000 });
    const testId = await firstRow.getAttribute('data-testid');
    const strike = testId.replace('optionchain-strike-row-', '');

    // All four CE Greek cells must be visible (showGreeks defaults to true)
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-delta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-gamma-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-theta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-vega-${strike}"]`)).toBeVisible();

    // All four PE Greek cells must be visible
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-delta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-gamma-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-theta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-vega-${strike}"]`)).toBeVisible();
  });

  // ─── Test 3: Toggle OFF hides Greek columns ───────────────────────────────────

  test('should hide Greeks columns when toggled off', async ({ authenticatedPage }) => {
    const chainState = await optionChainPage.waitForChainLoad();

    if (chainState === 'error') {
      test.skip('Option chain returned an error — cannot assert Greek column visibility');
      return;
    }

    const expectation = getDataExpectation();
    if (expectation === 'CLOSED') {
      console.log(`[Greeks] Market CLOSED (${getISTTimeString()}) — skipping cell-level assertion`);
      // Still verify toggle interaction does not crash the page
      await optionChainPage.toggleGreeks();
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }

    const firstRow = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').first();
    await firstRow.waitFor({ state: 'visible', timeout: 15000 });
    const testId = await firstRow.getAttribute('data-testid');
    const strike = testId.replace('optionchain-strike-row-', '');

    // Greeks are on by default — clicking once turns them off
    await optionChainPage.toggleGreeks();

    // CE Greek cells must not be visible after toggle off
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-delta-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-gamma-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-theta-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-vega-${strike}"]`)).not.toBeVisible();

    // PE Greek cells must not be visible after toggle off
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-delta-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-gamma-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-theta-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-vega-${strike}"]`)).not.toBeVisible();

    // Table itself must still be visible — toggling Greeks must not destroy the table
    await expect(optionChainPage.table).toBeVisible();
  });

  // ─── Test 4: Toggle ON restores Greek columns ─────────────────────────────────

  test('should show Greeks columns when toggled back on', async ({ authenticatedPage }) => {
    const chainState = await optionChainPage.waitForChainLoad();

    if (chainState === 'error') {
      test.skip('Option chain returned an error — cannot assert Greek column visibility');
      return;
    }

    const expectation = getDataExpectation();
    if (expectation === 'CLOSED') {
      console.log(`[Greeks] Market CLOSED (${getISTTimeString()}) — skipping cell-level assertion`);
      await optionChainPage.toggleGreeks();
      await optionChainPage.toggleGreeks();
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }

    const firstRow = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').first();
    await firstRow.waitFor({ state: 'visible', timeout: 15000 });
    const testId = await firstRow.getAttribute('data-testid');
    const strike = testId.replace('optionchain-strike-row-', '');

    // Toggle OFF then back ON
    await optionChainPage.toggleGreeks();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-delta-${strike}"]`)).not.toBeVisible();

    await optionChainPage.toggleGreeks();

    // All four CE Greek cells must be visible again
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-delta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-gamma-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-theta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-vega-${strike}"]`)).toBeVisible();

    // All four PE Greek cells must be visible again
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-delta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-gamma-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-theta-${strike}"]`)).toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-vega-${strike}"]`)).toBeVisible();
  });

  // ─── Test 5: Delta values are numeric within [-1, 1] ─────────────────────────

  test('should display valid delta values', async ({ authenticatedPage }) => {
    const chainState = await optionChainPage.waitForChainLoad();

    if (chainState === 'error') {
      test.skip('Option chain returned an error — cannot assert delta values');
      return;
    }

    const expectation = getDataExpectation();

    // Delta values are only meaningful with live or last-known market data
    if (expectation !== 'LIVE' && expectation !== 'LAST_KNOWN') {
      console.log(`[Greeks] Market ${expectation} (${getISTTimeString()}) — skipping delta value assertions`);
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping delta assertions');
      await optionChainPage.assertPageVisible();
      return;
    }

    const firstRow = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').first();
    await firstRow.waitFor({ state: 'visible', timeout: 15000 });
    const testId = await firstRow.getAttribute('data-testid');
    const strike = testId.replace('optionchain-strike-row-', '');

    const ceDeltaCell = authenticatedPage.locator(`[data-testid="optionchain-ce-delta-${strike}"]`);
    const peDeltaCell = authenticatedPage.locator(`[data-testid="optionchain-pe-delta-${strike}"]`);

    const isCeDeltaVisible = await ceDeltaCell.isVisible({ timeout: 5000 }).catch(() => false);
    if (!isCeDeltaVisible) {
      // Greeks may be unavailable for this strike (e.g., no IV data from broker)
      console.log(`[Greeks] CE delta cell not visible for strike ${strike} — broker may not have returned Greeks`);
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    const ceDeltaText = await ceDeltaCell.textContent();
    const peDeltaText = await peDeltaCell.textContent();

    const ceDelta = parseFloat(ceDeltaText);
    const peDelta = parseFloat(peDeltaText);

    // A non-numeric cell means the broker returned no Greek data — treat as acceptable
    if (!isNaN(ceDelta)) {
      // CE delta: 0 to +1
      expect(ceDelta).toBeGreaterThanOrEqual(0);
      expect(ceDelta).toBeLessThanOrEqual(1);
    } else {
      console.log(`[Greeks] CE delta for strike ${strike} is non-numeric ("${ceDeltaText}") — broker data unavailable`);
    }

    if (!isNaN(peDelta)) {
      // PE delta: -1 to 0
      expect(peDelta).toBeGreaterThanOrEqual(-1);
      expect(peDelta).toBeLessThanOrEqual(0);
    } else {
      console.log(`[Greeks] PE delta for strike ${strike} is non-numeric ("${peDeltaText}") — broker data unavailable`);
    }

    // At least one delta value must be numeric when data is available
    expect(!isNaN(ceDelta) || !isNaN(peDelta)).toBe(true);
  });

  // ─── Test 6: Greeks state persists after underlying switch ────────────────────

  test('should maintain Greeks state after underlying switch', async ({ authenticatedPage }) => {
    const chainState = await optionChainPage.waitForChainLoad();

    if (chainState === 'error') {
      test.skip('Option chain returned an error — cannot test state persistence');
      return;
    }

    const expectation = getDataExpectation();

    // Turn Greeks off before switching underlying
    await optionChainPage.toggleGreeks();

    // Switch to BANKNIFTY and wait for chain to reload
    await optionChainPage.selectUnderlying('BANKNIFTY');
    const bnfState = await optionChainPage.waitForChainLoad();

    if (bnfState === 'error') {
      // BANKNIFTY chain failed to load — still verify page is stable
      await optionChainPage.assertPageVisible();
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    if (expectation === 'CLOSED') {
      console.log(`[Greeks] Market CLOSED (${getISTTimeString()}) — asserting toggle visible after switch`);
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Resolve a strike from the BANKNIFTY chain
    const firstRow = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').first();
    await firstRow.waitFor({ state: 'visible', timeout: 15000 });
    const testId = await firstRow.getAttribute('data-testid');
    const strike = testId.replace('optionchain-strike-row-', '');

    // Greeks were toggled off before the switch — they must remain hidden after the switch
    await expect(authenticatedPage.locator(`[data-testid="optionchain-ce-delta-${strike}"]`)).not.toBeVisible();
    await expect(authenticatedPage.locator(`[data-testid="optionchain-pe-delta-${strike}"]`)).not.toBeVisible();
  });

  // ─── Test 7: All four Greek types present for a single strike ────────────────

  test('should display all four Greek types', async ({ authenticatedPage }) => {
    const chainState = await optionChainPage.waitForChainLoad();

    if (chainState === 'error') {
      test.skip('Option chain returned an error — cannot assert all Greek types');
      return;
    }

    const expectation = getDataExpectation();
    if (expectation === 'CLOSED') {
      console.log(`[Greeks] Market CLOSED (${getISTTimeString()}) — asserting toggle only`);
      await expect(authenticatedPage.locator('[data-testid="optionchain-greeks-toggle"]')).toBeVisible();
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    if (!(await hasChainData(authenticatedPage))) {
      console.log('Chain loaded but has no data rows (broker error) — skipping data assertions');
      await optionChainPage.assertPageVisible();
      return;
    }

    const firstRow = authenticatedPage.locator('[data-testid^="optionchain-strike-row-"]').first();
    await firstRow.waitFor({ state: 'visible', timeout: 15000 });
    const testId = await firstRow.getAttribute('data-testid');
    const strike = testId.replace('optionchain-strike-row-', '');

    const greekTypes = ['delta', 'gamma', 'theta', 'vega'];

    for (const greek of greekTypes) {
      await expect(
        authenticatedPage.locator(`[data-testid="optionchain-ce-${greek}-${strike}"]`),
        `CE ${greek} cell must be visible for strike ${strike}`
      ).toBeVisible();

      await expect(
        authenticatedPage.locator(`[data-testid="optionchain-pe-${greek}-${strike}"]`),
        `PE ${greek} cell must be visible for strike ${strike}`
      ).toBeVisible();
    }
  });
});
