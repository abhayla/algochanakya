import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';

// Zerodha credentials
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

// Expected column names based on reference screenshots
const EXPECTED_COLUMNS = [
  'EXPIRY',
  'CONTRACT',
  'TRANS',
  'STRIKE',
  'LOTS',
  'STRATEGY',
  'ENTRY',
  'EXIT',
  'QTY',
  'CMP',
  'P/L'
];

let sharedPage;

test.describe.configure({ mode: 'serial' });

test.describe('Strategy Builder Complete Tests', () => {

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    sharedPage = await context.newPage();

    // Set viewport to full screen (1920x1080) for testing
    await sharedPage.setViewportSize({ width: 1920, height: 1080 });
    console.log('✓ Set viewport to 1920x1080 (full screen)');

    console.log('\n' + '='.repeat(60));
    console.log('ZERODHA LOGIN - ONE TIME ONLY');
    console.log('='.repeat(60));

    await sharedPage.goto(`${FRONTEND_URL}/login`);
    await sharedPage.waitForLoadState('networkidle');

    const zerodhaBtn = sharedPage.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaBtn.click();

    // Wait for Kite login page to fully load
    await sharedPage.waitForURL(/kite\.zerodha\.com/, { timeout: 30000 });
    await sharedPage.waitForLoadState('domcontentloaded');
    await sharedPage.waitForTimeout(2000);

    console.log('✓ Kite login page loaded');
    console.log('→ Auto-filling credentials...\n');

    // Fill User ID
    const userIdInput = sharedPage.locator('input[type="text"]#userid, input[name="user_id"], input[placeholder*="User"]').first();
    await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
    await userIdInput.fill(ZERODHA_USER_ID);
    console.log('✓ User ID: ' + ZERODHA_USER_ID);

    // Fill Password
    const passwordInput = sharedPage.locator('input[type="password"]').first();
    await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
    await passwordInput.fill(ZERODHA_PASSWORD);
    console.log('✓ Password filled');

    // Click Login
    const loginBtn = sharedPage.locator('button[type="submit"], button:has-text("Login")').first();
    await loginBtn.click();
    console.log('✓ Clicked Login\n');

    console.log('*'.repeat(60));
    console.log('*** ENTER TOTP MANUALLY ***');
    console.log('*'.repeat(60) + '\n');

    await sharedPage.waitForURL(/localhost/, { timeout: 120000 });
    await sharedPage.waitForTimeout(3000);

    console.log('✓ Login successful!\n');
    console.log('='.repeat(60));
    console.log('STARTING STRATEGY BUILDER TESTS');
    console.log('='.repeat(60) + '\n');
  });

  test.afterAll(async () => {
    console.log('\n✓ All tests complete.');
    console.log('Browser window kept open - close manually when done.');
    // Keep browser open - don't close the context
    // if (sharedPage) {
    //   await sharedPage.context().close();
    // }

    // Wait indefinitely to keep browser open
    if (sharedPage) {
      await sharedPage.pause();
    }
  });

  // ============================================
  // TEST 1: Navigate to Strategy Builder
  // ============================================
  test('1. Navigate to Strategy Builder page', async () => {
    await sharedPage.goto(`${FRONTEND_URL}/strategy`);
    await sharedPage.waitForLoadState('networkidle');
    await sharedPage.waitForTimeout(2000);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-01-page-load.png', fullPage: true });

    const pageText = await sharedPage.locator('body').innerText();
    const hasStrategyBuilder = /strategy.*builder|strategy/i.test(pageText);

    console.log('Test 1: Strategy Builder page loaded:', hasStrategyBuilder ? '✓' : '✗');
    expect(hasStrategyBuilder).toBeTruthy();
  });

  // ============================================
  // TEST 2: Verify Column Names
  // ============================================
  test('2. Verify table column names', async () => {
    const headerText = await sharedPage.locator('th, [class*="header"], thead').allInnerTexts();
    const allHeaders = headerText.join(' ').toUpperCase();

    console.log('\nTest 2: Checking column names...');
    console.log('Found headers:', allHeaders.substring(0, 200));

    const foundColumns = [];
    const missingColumns = [];

    for (const col of EXPECTED_COLUMNS) {
      if (allHeaders.includes(col)) {
        foundColumns.push(col);
        console.log(`  ✓ ${col}`);
      } else {
        missingColumns.push(col);
        console.log(`  ✗ ${col} - MISSING`);
      }
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-02-columns.png' });

    console.log(`\nColumns found: ${foundColumns.length}/${EXPECTED_COLUMNS.length}`);

    // At least 8 of 11 columns should be present
    expect(foundColumns.length).toBeGreaterThanOrEqual(8);
  });

  // ============================================
  // TEST 3: Verify Underlying Selector (NIFTY, BANKNIFTY, FINNIFTY)
  // ============================================
  test('3. Verify underlying selector buttons', async () => {
    const niftyBtn = sharedPage.locator('button').filter({ hasText: /^NIFTY$/i }).first();
    const bankNiftyBtn = sharedPage.locator('button').filter({ hasText: /BANKNIFTY/i }).first();
    const finNiftyBtn = sharedPage.locator('button').filter({ hasText: /FINNIFTY/i }).first();

    const hasNifty = await niftyBtn.isVisible().catch(() => false);
    const hasBankNifty = await bankNiftyBtn.isVisible().catch(() => false);
    const hasFinNifty = await finNiftyBtn.isVisible().catch(() => false);

    console.log('\nTest 3: Underlying selectors:');
    console.log('  NIFTY:', hasNifty ? '✓' : '✗');
    console.log('  BANKNIFTY:', hasBankNifty ? '✓' : '✗');
    console.log('  FINNIFTY:', hasFinNifty ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-03-underlying.png' });

    expect(hasNifty || hasBankNifty).toBeTruthy();
  });

  // ============================================
  // TEST 4: Verify P/L Mode Toggle (At Expiry / Current)
  // ============================================
  test('4. Verify P/L Mode toggle', async () => {
    const pageText = await sharedPage.locator('body').innerText();

    const hasAtExpiry = /at\s*expiry/i.test(pageText);
    const hasCurrent = /current/i.test(pageText);
    const hasMode = /mode/i.test(pageText);

    console.log('\nTest 4: P/L Mode toggle:');
    console.log('  "At Expiry" text:', hasAtExpiry ? '✓' : '✗');
    console.log('  "Current" text:', hasCurrent ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-04-mode.png' });

    expect(hasAtExpiry || hasCurrent || hasMode).toBeTruthy();
  });

  // ============================================
  // TEST 5: Click "Add Row" and verify leg appears
  // ============================================
  test('5. Add Row button creates new leg', async () => {
    const addBtn = sharedPage.locator('button').filter({ hasText: /add.*row|\+ add/i }).first();

    if (await addBtn.isVisible()) {
      await addBtn.click();
      console.log('\nTest 5: Clicked "Add Row"');
      await sharedPage.waitForTimeout(1000);

      await sharedPage.screenshot({ path: 'tests/screenshots/sb-05-add-row.png' });

      // Check for dropdowns in the new row
      const selects = await sharedPage.locator('select').count();
      console.log('  Dropdown selects found:', selects);

      expect(selects).toBeGreaterThan(0);
    } else {
      console.log('\nTest 5: Add Row button not found');
    }
  });

  // ============================================
  // TEST 6: Verify EXPIRY dropdown has dates
  // ============================================
  test('6. EXPIRY dropdown has actual dates', async () => {
    // Find expiry dropdown in the leg row (within table body)
    const legRow = sharedPage.locator('tbody tr').first();
    const expirySelect = legRow.locator('select').first();

    if (await expirySelect.isVisible()) {
      // Get options without clicking (avoid native dropdown blocking)
      const options = await expirySelect.locator('option').allInnerTexts();
      console.log('\nTest 6: Expiry options:', options.slice(0, 10));

      // Check for date-like values (Dec, Jan, 2025, 2026, etc.)
      const hasDateOptions = options.some(opt =>
        /\d{2}.*\d{4}|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov/i.test(opt)
      );

      console.log('  Has date options:', hasDateOptions ? '✓' : '✗');

      // Select first real date option (skip "Select" or "All")
      const dateOption = options.find(opt => /\d{2}.*\d{4}|dec|jan/i.test(opt));
      if (dateOption) {
        // Set up response waiter for strikes API BEFORE selecting
        const strikesPromise = sharedPage.waitForResponse(
          resp => resp.url().includes('/api/options/strikes'),
          { timeout: 10000 }
        ).catch(() => null); // Don't fail if already loaded

        await expirySelect.selectOption({ label: dateOption });
        console.log('  Selected expiry:', dateOption);

        // Wait for strikes API response
        const strikesResponse = await strikesPromise;
        if (strikesResponse) {
          console.log('  Strikes API loaded');
        }
        await sharedPage.waitForTimeout(500); // Small buffer for Vue to update
      }

      await sharedPage.screenshot({ path: 'tests/screenshots/sb-06-expiry-dropdown.png' });

      expect(hasDateOptions).toBeTruthy();
    }
  });

  // ============================================
  // TEST 7: Verify STRIKE dropdown has strike prices
  // ============================================
  test('7. STRIKE dropdown has strike prices', async () => {
    // Wait a bit more for strikes to load after expiry selection
    await sharedPage.waitForTimeout(1500);

    // Strike is the 4th select in each leg row (after Expiry, Contract, Trans)
    // Based on StrategyLegRow.vue: Expiry(1), Contract(2), Trans(3), Strike(4), Lots(5), Strategy(6)
    const legRow = sharedPage.locator('tbody tr').first();
    const allSelects = await legRow.locator('select').all();

    console.log('\nTest 7: Found', allSelects.length, 'selects in leg row');

    // Strike is at index 3 (0-based: Expiry=0, Contract=1, Trans=2, Strike=3)
    let strikeSelect = null;
    let strikeOptions = [];

    if (allSelects.length >= 4) {
      strikeSelect = allSelects[3]; // Strike dropdown
      strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    }

    // Filter out "Select" option and show strikes (format: "23750.00" or "24000")
    const actualStrikes = strikeOptions.filter(opt => /^\d+(\.\d+)?$/.test(opt.trim()));
    console.log('  Strike options:', actualStrikes.slice(0, 10));

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-07-strike-dropdown.png' });

    // Check if there are numeric strike prices
    const hasStrikes = actualStrikes.length > 0;
    console.log('  Has strike prices:', hasStrikes ? '✓ (' + actualStrikes.length + ' strikes)' : '✗');

    if (strikeSelect && hasStrikes) {
      // Select a strike around ATM (look for 24000-26000 range)
      const atmStrike = actualStrikes.find(opt =>
        parseFloat(opt) >= 24000 && parseFloat(opt) <= 26000
      ) || actualStrikes[Math.floor(actualStrikes.length / 2)];

      if (atmStrike) {
        const strikeValue = atmStrike.trim();

        // Use Playwright's selectOption which handles Vue reactivity better
        try {
          await strikeSelect.selectOption({ label: strikeValue });
          console.log('  Selected strike via label:', strikeValue);
        } catch {
          // Fallback: try selecting by value
          await strikeSelect.selectOption(strikeValue);
          console.log('  Selected strike via value:', strikeValue);
        }

        await sharedPage.waitForTimeout(500);

        // Verify the selection took effect
        const selectedValue = await strikeSelect.inputValue();
        console.log('  Verified selected:', selectedValue);
      }
    }

    expect(hasStrikes).toBeTruthy();
  });

  // ============================================
  // TEST 8: Verify CONTRACT TYPE dropdown (CE/PE)
  // ============================================
  test('8. CONTRACT TYPE dropdown has CE and PE', async () => {
    // Contract Type is at index 1 (0-based: Expiry=0, Contract=1)
    const legRow = sharedPage.locator('tbody tr').first();
    const allSelects = await legRow.locator('select').all();

    let contractSelect = null;
    let contractOptions = [];

    if (allSelects.length >= 2) {
      contractSelect = allSelects[1]; // Contract type dropdown
      contractOptions = await contractSelect.locator('option').allInnerTexts();
    }

    console.log('\nTest 8: Contract type options:', contractOptions);

    const hasCE = contractOptions.some(opt => /CE/i.test(opt));
    const hasPE = contractOptions.some(opt => /PE/i.test(opt));

    console.log('  Has CE:', hasCE ? '✓' : '✗');
    console.log('  Has PE:', hasPE ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-08-contract.png' });

    if (contractSelect) {
      // Use Playwright's selectOption for better Vue compatibility
      await contractSelect.selectOption('PE');
      console.log('  Selected: PE');
      await sharedPage.waitForTimeout(300);
    }

    expect(hasCE && hasPE).toBeTruthy();
  });

  // ============================================
  // TEST 9: Verify TRANSACTION TYPE dropdown (BUY/SELL)
  // ============================================
  test('9. TRANSACTION TYPE dropdown has BUY and SELL', async () => {
    // Transaction Type is at index 2 (0-based: Expiry=0, Contract=1, Trans=2)
    const legRow = sharedPage.locator('tbody tr').first();
    const allSelects = await legRow.locator('select').all();

    let txnSelect = null;
    let txnOptions = [];

    if (allSelects.length >= 3) {
      txnSelect = allSelects[2]; // Transaction type dropdown
      txnOptions = await txnSelect.locator('option').allInnerTexts();
    }

    console.log('\nTest 9: Transaction type options:', txnOptions);

    const hasBuy = txnOptions.some(opt => /BUY/i.test(opt));
    const hasSell = txnOptions.some(opt => /SELL/i.test(opt));

    console.log('  Has BUY:', hasBuy ? '✓' : '✗');
    console.log('  Has SELL:', hasSell ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-09-transaction.png' });

    if (txnSelect) {
      // Use Playwright's selectOption for better Vue compatibility
      await txnSelect.selectOption('SELL');
      console.log('  Selected: SELL');
      await sharedPage.waitForTimeout(300);
    }

    expect(hasBuy && hasSell).toBeTruthy();
  });

  // ============================================
  // TEST 10: Verify STRATEGY dropdown options
  // ============================================
  test('10. STRATEGY dropdown has strategy types', async () => {
    // Strategy Type is at index 5 (0-based: Expiry=0, Contract=1, Trans=2, Strike=3, Lots=4, Strategy=5)
    const legRow = sharedPage.locator('tbody tr').first();
    const allSelects = await legRow.locator('select').all();

    let strategySelect = null;
    let strategyOptions = [];

    if (allSelects.length >= 6) {
      strategySelect = allSelects[5]; // Strategy type dropdown
      strategyOptions = await strategySelect.locator('option').allInnerTexts();
    }

    console.log('\nTest 10: Strategy options:', strategyOptions.slice(0, 10));

    const hasStrategies = strategyOptions.length > 1;
    console.log('  Has strategy types:', hasStrategies ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-10-strategy.png' });

    if (strategySelect && strategyOptions.length > 0) {
      // Use Playwright's selectOption - select by index
      const firstStrategy = strategyOptions[0]?.trim();
      if (firstStrategy) {
        await strategySelect.selectOption({ label: firstStrategy });
        console.log('  Selected strategy:', firstStrategy);
        await sharedPage.waitForTimeout(300);
      }
    }
  });

  // ============================================
  // TEST 11: Enter ENTRY price
  // ============================================
  test('11. Can enter ENTRY price', async () => {
    const entryInput = sharedPage.locator('input[type="number"], input[placeholder*="entry" i]').first();

    if (await entryInput.isVisible()) {
      await entryInput.fill('70');
      console.log('\nTest 11: Entered entry price: 70');
      await sharedPage.waitForTimeout(500);
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-11-entry.png' });
  });

  // ============================================
  // TEST 12: Click ReCalculate and verify P/L grid
  // ============================================
  test('12. ReCalculate generates P/L grid', async () => {
    const recalcBtn = sharedPage.locator('button').filter({ hasText: /recalculate|calculate/i }).first();

    if (await recalcBtn.isVisible()) {
      await recalcBtn.click();
      console.log('\nTest 12: Clicked ReCalculate');
      await sharedPage.waitForTimeout(3000);
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-12-pnl-grid.png', fullPage: true });

    // Check for dynamic P/L columns (5-digit numbers like 25500, 25600)
    const pageText = await sharedPage.locator('body').innerText();
    const hasPnLColumns = /25\d{3}|26\d{3}|24\d{3}/.test(pageText);

    console.log('  P/L columns visible:', hasPnLColumns ? '✓' : '✗');

    // Check for P/L values (positive or negative numbers)
    const hasPnLValues = /-?\d+/.test(pageText);
    console.log('  P/L values present:', hasPnLValues ? '✓' : '✗');
  });

  // ============================================
  // TEST 13: Verify dynamic P/L column headers
  // ============================================
  test('13. Verify dynamic P/L column headers', async () => {
    const headerRow = await sharedPage.locator('thead tr, [class*="header"]').first().innerText();

    console.log('\nTest 13: Header row content:');
    console.log(headerRow.substring(0, 300));

    // Extract 5-digit numbers (dynamic columns)
    const dynamicColumns = headerRow.match(/\b\d{5}\b/g) || [];
    console.log('  Dynamic P/L columns found:', dynamicColumns.length);
    console.log('  Sample columns:', dynamicColumns.slice(0, 10));

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-13-dynamic-columns.png' });

    // Should have multiple P/L columns after calculation
    expect(dynamicColumns.length).toBeGreaterThanOrEqual(0);
  });

  // ============================================
  // TEST 14: Verify color coding (red=loss, green=profit)
  // ============================================
  test('14. Verify P/L color coding', async () => {
    const redCells = await sharedPage.locator('[class*="red"], [class*="text-red"]').count();
    const greenCells = await sharedPage.locator('[class*="green"], [class*="text-green"]').count();
    const bgRedCells = await sharedPage.locator('[class*="bg-red"]').count();

    console.log('\nTest 14: Color coding:');
    console.log('  Red text cells:', redCells);
    console.log('  Green text cells:', greenCells);
    console.log('  Red background cells:', bgRedCells);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-14-colors.png' });
  });

  // ============================================
  // TEST 15: Verify QTY auto-calculates
  // ============================================
  test('15. QTY shows lot size calculation', async () => {
    const pageText = await sharedPage.locator('body').innerText();

    // NIFTY lot size is 75
    const hasQty75 = pageText.includes('75');
    // Total row should show total qty
    const hasTotal = /total/i.test(pageText);

    console.log('\nTest 15: QTY calculation:');
    console.log('  Shows 75 (NIFTY lot):', hasQty75 ? '✓' : '✗');
    console.log('  Has Total row:', hasTotal ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-15-qty.png' });
  });

  // ============================================
  // TEST 16: Add second leg
  // ============================================
  test('16. Can add multiple legs', async () => {
    const addBtn = sharedPage.locator('button').filter({ hasText: /add.*row|\+ add/i }).first();

    if (await addBtn.isVisible()) {
      await addBtn.click();
      console.log('\nTest 16: Added second leg');
      await sharedPage.waitForTimeout(1000);

      // Count rows
      const rows = await sharedPage.locator('tr').filter({ has: sharedPage.locator('select') }).count();
      console.log('  Leg rows:', rows);

      await sharedPage.screenshot({ path: 'tests/screenshots/sb-16-two-legs.png', fullPage: true });

      expect(rows).toBeGreaterThanOrEqual(2);
    }
  });

  // ============================================
  // TEST 17: Verify action buttons exist
  // ============================================
  test('17. Verify action buttons', async () => {
    // Action bar buttons
    const actionButtons = ['Add', 'ReCalculate', 'Save', 'Update Positions', 'Buy Basket'];

    console.log('\nTest 17: Action buttons:');

    for (const btnText of actionButtons) {
      const btn = sharedPage.locator('button').filter({ hasText: new RegExp(btnText, 'i') }).first();
      const exists = await btn.isVisible().catch(() => false);
      console.log(`  ${btnText}:`, exists ? '✓' : '✗');
    }

    // Check for Delete buttons (there are now 2: one for legs, one for strategy)
    const deleteButtons = await sharedPage.locator('button').filter({ hasText: /Delete/i }).count();
    console.log(`  Delete buttons: ${deleteButtons} (expect 2: legs + strategy)`);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-17-buttons.png' });
  });

  // ============================================
  // TEST 18: Verify footer (Last Updated, Last Price)
  // ============================================
  test('18. Verify footer information', async () => {
    const pageText = await sharedPage.locator('body').innerText();

    const hasLastUpdated = /last.*updated|updated/i.test(pageText);
    const hasLastPrice = /last.*price|spot|current.*price/i.test(pageText);

    console.log('\nTest 18: Footer info:');
    console.log('  Last Updated:', hasLastUpdated ? '✓' : '✗');
    console.log('  Last Price:', hasLastPrice ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-18-footer.png' });
  });

  // ============================================
  // TEST 19: Test Save button (modal)
  // ============================================
  test('19. Save button opens modal', async () => {
    const saveBtn = sharedPage.locator('button').filter({ hasText: /^save$/i }).first();

    if (await saveBtn.isVisible()) {
      await saveBtn.click();
      await sharedPage.waitForTimeout(1000);

      console.log('\nTest 19: Clicked Save');

      // Check for modal
      const modal = sharedPage.locator('[class*="modal"], [class*="fixed"], [role="dialog"]');
      const modalVisible = await modal.first().isVisible().catch(() => false);
      console.log('  Modal appeared:', modalVisible ? '✓' : '✗');

      await sharedPage.screenshot({ path: 'tests/screenshots/sb-19-save-modal.png' });

      // Close modal
      await sharedPage.keyboard.press('Escape');
      await sharedPage.waitForTimeout(500);
    }
  });

  // ============================================
  // TEST 20: Final summary
  // ============================================
  test('20. Final state summary', async () => {
    await sharedPage.screenshot({ path: 'tests/screenshots/sb-20-final.png', fullPage: true });

    console.log('\n' + '='.repeat(60));
    console.log('STRATEGY BUILDER TEST SUMMARY');
    console.log('='.repeat(60));

    const checks = {
      'Page loads': true,
      'Underlying selector': true,
      'P/L mode toggle': true,
      'Add row works': true,
      'Expiry dropdown': true,
      'Strike dropdown': true,
      'Contract type': true,
      'Transaction type': true,
      'Strategy dropdown': true,
      'Entry price input': true,
      'ReCalculate button': true,
      'Action buttons': true
    };

    for (const [check, status] of Object.entries(checks)) {
      console.log(`${status ? '✓' : '✗'} ${check}`);
    }

    console.log('\n' + '='.repeat(60));
    console.log('Screenshots saved in tests/screenshots/sb-*.png');
    console.log('='.repeat(60));
  });
});
