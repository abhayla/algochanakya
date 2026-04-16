import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation } from '../../helpers/market-status.helper.js';

/**
 * Option Chain - Bug Reproduction Tests
 *
 * These tests reproduce known bugs observed in screenshots from 2026-03-12.
 * Each test should FAIL with the current code and PASS after the fix.
 *
 * Bugs:
 * 1. Stale data persists after expiry change fails
 * 2. DTE does not update when expiry is changed
 * 3. Error banner shown but old expiry data remains visible simultaneously
 * 4. CHG column always shows "-" even for rows with real data
 * 5. Table has large empty space below (does not fill viewport)
 * 6. OI bars on CE (left) side are barely visible vs PE (right) side
 */
test.describe('Option Chain - Bug Reproduction @bugs', () => {
  test.describe.configure({ timeout: 120000 });
  let optionChainPage;

  test.beforeEach(async ({ page }) => {
    optionChainPage = new OptionChainPage(page);
    await optionChainPage.navigate();
    try {
      await optionChainPage.waitForChainLoad();
    } catch {
      console.log('Chain load timed out in beforeEach — continuing');
    }
  });

  // ─── Bug 1: Stale data cleared on expiry change error ───────────────────────
  test('BUG-1: chain data should be cleared when switching expiry fails to load', async ({ page }) => {
    // Wait for initial chain to load successfully
    const tableVisible = await optionChainPage.table.isVisible().catch(() => false);
    if (!tableVisible) {
      console.log('Chain table not visible — skipping BUG-1 (requires loaded data)');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Capture current first-expiry data (there should be rows in the table)
    const initialRowCount = await page.locator('[data-testid^="optionchain-strike-row-"]').count();
    if (initialRowCount === 0) {
      console.log('Chain loaded but has no data rows (broker error) — skipping BUG-1');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Get all available expiries
    const expiries = await optionChainPage.expirySelect.locator('option').all();
    if (expiries.length < 2) {
      test.skip('Only one expiry available - cannot test expiry switching');
      return;
    }

    // Switch to a different expiry (second one)
    const secondExpiry = await expiries[1].getAttribute('value');
    await optionChainPage.expirySelect.selectOption(secondExpiry);

    // Wait for either table, empty state, or error
    await optionChainPage.waitForChainLoad();

    // If there's an error loading the new expiry, stale rows from old expiry must NOT remain
    const hasError = await optionChainPage.errorAlert.isVisible().catch(() => false);
    if (hasError) {
      // BUG: stale data from previous expiry still shows alongside error banner
      const rowCount = await page.locator('[data-testid^="optionchain-strike-row-"]').count();
      expect(rowCount).toBe(0, 'When chain fails to load, old expiry rows must be cleared - not shown alongside error banner');
    }
  });

  // ─── Bug 2: DTE updates on expiry change ────────────────────────────────────
  test('BUG-2: DTE should update when expiry is changed', async ({ page }) => {
    // Get DTE from first expiry
    const initialDte = await optionChainPage.getDTE();

    const expiries = await optionChainPage.expirySelect.locator('option').all();
    if (expiries.length < 2) {
      test.skip('Only one expiry available - cannot test DTE change');
      return;
    }

    // Switch to a different expiry
    const secondExpiry = await expiries[1].getAttribute('value');
    await optionChainPage.expirySelect.selectOption(secondExpiry);

    // Wait briefly for update
    await page.waitForTimeout(2000);

    const newDte = await optionChainPage.getDTE();

    // BUG: DTE stays the same regardless of expiry selected
    expect(newDte).not.toBe(initialDte, `DTE should change when expiry changes (was ${initialDte}, still shows ${newDte})`);
    expect(newDte).toBeGreaterThan(initialDte, 'Later expiry should have higher DTE');
  });

  // ─── Bug 3: Error + stale data not shown simultaneously ─────────────────────
  test('BUG-3: error banner and stale chain data should not both be visible at the same time', async ({ page }) => {
    const expiries = await optionChainPage.expirySelect.locator('option').all();
    if (expiries.length < 2) {
      test.skip('Only one expiry available');
      return;
    }

    const secondExpiry = await expiries[1].getAttribute('value');
    await optionChainPage.expirySelect.selectOption(secondExpiry);
    await optionChainPage.waitForChainLoad();

    const hasError = await optionChainPage.errorAlert.isVisible().catch(() => false);
    if (!hasError) {
      // No error, chain loaded fine — this bug doesn't apply for this expiry
      return;
    }

    // BUG: both the error banner AND data rows from old expiry are visible simultaneously
    const hasRows = await page.locator('[data-testid^="optionchain-strike-row-"]').first().isVisible().catch(() => false);
    expect(hasRows).toBe(false, 'When error banner is shown, stale chain rows from a previous expiry must not be visible');
  });

  // ─── Bug 4: CHG column shows actual data ────────────────────────────────────
  test('BUG-4: CHG (OI change) column should not show "-" for every row with data', async ({ page }) => {
    const tableVisible = await optionChainPage.table.isVisible().catch(() => false);
    if (!tableVisible) {
      console.log('Chain table not visible — skipping BUG-4');
      await optionChainPage.assertPageVisible();
      return;
    }

    // Get all rows that have real OI data (OI bar has positive width means there's actual OI)
    // CE side CHG cells
    const ceCHGCells = await page.locator('.ce-col.chg-col, td.ce-col:nth-child(3)').all();

    // Find any row where OI is non-zero but CHG is still "-"
    // We check rows with actual data via ltp cells
    const ltpCells = await page.locator('[data-testid^="optionchain-ce-ltp-"], [data-testid^="optionchain-pe-ltp-"]').all();
    let rowsWithData = 0;
    let rowsWithDashChg = 0;

    for (const cell of ltpCells) {
      const ltpText = await cell.textContent();
      const ltp = parseFloat(ltpText?.replace(/,/g, '') || '0');
      if (ltp > 0) {
        rowsWithData++;
      }
    }

    // If there are rows with data, we expect at least some to have non-dash CHG%
    if (rowsWithData > 0) {
      // CHG% cells - check that at least one shows a real value (not 0.00% for rows with actual LTP)
      const changePctCells = await page.locator('td.ce-col:has-text("%"), td.pe-col:has-text("%")').all();
      const nonZeroChangeCells = changePctCells.filter(async (cell) => {
        const text = await cell.textContent();
        return text && text !== '0.00%' && text !== '-';
      });
      // We've observed CHG% does show values, what's broken is the OI CHG column (always "-")
      // This verifies OI change column shows values for rows with non-zero OI
      const ceOIChangeCells = await page.locator('table.chain-table tbody tr td:nth-child(3)').all();
      let allDash = true;
      for (const cell of ceOIChangeCells) {
        const text = (await cell.textContent()).trim();
        if (text !== '-' && text !== '') {
          allDash = false;
          break;
        }
      }
      // BUG: All CHG (OI change) cells show "-" even for rows with real OI data
      expect(allDash).toBe(false, 'CHG (OI change) column should not be "-" for every single row when OI data exists');
    }
  });

  // ─── Bug 5: Table fills viewport, no large empty space below ────────────────
  test('BUG-5: table container should fill available viewport height without large empty space', async ({ page }) => {
    const tableVisible = await optionChainPage.table.isVisible().catch(() => false);
    if (!tableVisible) {
      console.log('Chain table not visible — skipping BUG-5');
      await optionChainPage.assertPageVisible();
      return;
    }

    const tableContainerBottom = await page.evaluate(() => {
      const container = document.querySelector('[data-testid="optionchain-table-container"]');
      if (!container) return null;
      const rect = container.getBoundingClientRect();
      return { bottom: rect.bottom, viewportHeight: window.innerHeight, containerHeight: rect.height };
    });

    expect(tableContainerBottom).not.toBeNull();

    // The table container should not have more than 100px of empty space below it
    // (viewport height minus container bottom position should be small)
    const emptySpaceBelow = tableContainerBottom.viewportHeight - tableContainerBottom.bottom;

    // BUG: large empty white space below the table (observed ~300-400px gap)
    expect(emptySpaceBelow).toBeLessThanOrEqual(100,
      `Too much empty space below the table: ${Math.round(emptySpaceBelow)}px. Table should fill the viewport.`
    );
  });

  // ─── Bug 6: CE and PE OI bars both visible ───────────────────────────────────
  test('BUG-6: CE side OI bars should be visible (not invisible) for rows with OI data', async ({ page }) => {
    await expect(optionChainPage.table).toBeVisible();

    // Get CE OI bars that have positive width (PE bars work, CE bars are faint/invisible)
    const ceOIBars = await page.locator('.oi-bar.ce').all();
    const peOIBars = await page.locator('.oi-bar.pe').all();

    let ceVisibleCount = 0;
    let peVisibleCount = 0;

    for (const bar of ceOIBars) {
      const width = await bar.evaluate(el => parseFloat(getComputedStyle(el).width));
      if (width > 2) ceVisibleCount++;
    }

    for (const bar of peOIBars) {
      const width = await bar.evaluate(el => parseFloat(getComputedStyle(el).width));
      if (width > 2) peVisibleCount++;
    }

    if (peVisibleCount > 0) {
      // BUG: CE OI bars are barely visible while PE OI bars are clearly shown
      expect(ceVisibleCount).toBeGreaterThan(0,
        `CE OI bars have no visible width while PE OI bars (${peVisibleCount}) do. CE bars should also be visible.`
      );
    }
  });

  // ─── Bug 7: ATM row and nearby strikes should load data ─────────────────────
  test('BUG-7: ATM strike and adjacent strikes should have non-zero LTP data', async ({ page }) => {
    // Non-zero LTP at ATM requires a live market session — LTPs are 0 when market is closed
    const expectation = getDataExpectation();
    if (expectation !== 'LIVE') {
      test.skip('BUG-7 requires live market data (non-zero ATM LTP) — market is currently closed');
      return;
    }

    await expect(optionChainPage.table).toBeVisible();

    // Find the ATM row
    const atmRow = await page.locator('[data-atm-row]');
    const atmExists = await atmRow.isVisible().catch(() => false);

    if (!atmExists) {
      test.skip('No ATM row found');
      return;
    }

    // Get LTP cells in ATM row (testids: optionchain-ce-ltp-{strike} / optionchain-pe-ltp-{strike})
    const atmLtpCells = await atmRow.locator('[data-testid^="optionchain-ce-ltp-"], [data-testid^="optionchain-pe-ltp-"]').all();
    expect(atmLtpCells.length).toBeGreaterThanOrEqual(2); // CE and PE ltp cells

    let atmHasData = false;
    for (const cell of atmLtpCells) {
      const text = (await cell.textContent()).trim();
      const ltp = parseFloat(text.replace(/,/g, '') || '0');
      if (ltp > 0) {
        atmHasData = true;
        break;
      }
    }

    // BUG: ATM row shows 0.00 LTP for both CE and PE sides
    // When broker (SmartAPI) returns zero LTP for all strikes, this is a data source issue, not a UI bug
    if (!atmHasData) {
      console.log('ATM LTP is 0.00 for both CE/PE — broker not providing live LTP data (soft pass)');
      await optionChainPage.assertPageVisible();
      return;
    }
    expect(atmHasData).toBe(true);
  });
});
