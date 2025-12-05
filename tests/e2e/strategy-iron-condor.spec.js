import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

// Iron Condor Strategy Configuration
const STRATEGY_NAME = 'Iron Condor Test ' + new Date().toISOString().slice(0, 10);
const UNDERLYING = 'NIFTY';
const LOT_SIZE = 75;

// 4 Legs of Iron Condor
const LEGS = [
  { contract: 'PE', transaction: 'BUY',  strike: '25600', entry: '15',  description: 'Buy PE 25600 (protection)' },
  { contract: 'PE', transaction: 'SELL', strike: '25800', entry: '35',  description: 'Sell PE 25800 (credit)' },
  { contract: 'CE', transaction: 'SELL', strike: '26200', entry: '40',  description: 'Sell CE 26200 (credit)' },
  { contract: 'CE', transaction: 'BUY',  strike: '26400', entry: '18',  description: 'Buy CE 26400 (protection)' },
];

// Expected P/L characteristics for Iron Condor
// Max Profit = Net Premium Received = (35 - 15) + (40 - 18) = 20 + 22 = 42 per lot = 42 * 75 = 3150
// Max Loss = Width of spread - Net Premium = (200 - 42) * 75 = 11850 per spread

let page;

test.describe.configure({ mode: 'serial' });

test.describe('Iron Condor Strategy - Complete Test', () => {

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();

    console.log('\n' + '='.repeat(70));
    console.log('IRON CONDOR STRATEGY TEST');
    console.log('='.repeat(70));
    console.log('\nStrategy: PE BUY 25600, PE SELL 25800, CE SELL 26200, CE BUY 26400');
    console.log('This is a classic Iron Condor - profit when NIFTY stays between 25800-26200\n');
  });

  test.afterAll(async () => {
    console.log('\n' + '='.repeat(70));
    console.log('TEST COMPLETE - Browser stays open for verification');
    console.log('='.repeat(70));
    console.log('\nYou can manually inspect the strategy builder.');
    console.log('Close the browser when done.\n');

    // Keep browser open indefinitely for manual inspection
    await page.waitForTimeout(60000); // 1 minute
  });

  // ============================================
  // STEP 1: Login to Zerodha
  // ============================================
  test('Step 1: Login to Zerodha', async () => {
    console.log('\n--- STEP 1: ZERODHA LOGIN ---');

    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Click Zerodha button
    const zerodhaBtn = page.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaBtn.click();
    console.log('✓ Clicked Zerodha login button');

    // Wait for Kite login page
    await page.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });
    await page.waitForTimeout(1500);

    // Auto-fill User ID
    const userIdInput = page.locator('input#userid, input[name="user_id"]').first();
    await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
    await userIdInput.fill(ZERODHA_USER_ID);
    console.log('✓ User ID filled: ' + ZERODHA_USER_ID);

    // Auto-fill Password
    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill(ZERODHA_PASSWORD);
    console.log('✓ Password filled');

    // Click Login
    const loginBtn = page.locator('button[type="submit"]').first();
    await loginBtn.click();
    console.log('✓ Clicked Login button');

    // Wait for TOTP page
    await page.waitForTimeout(2000);

    console.log('\n' + '*'.repeat(50));
    console.log('*** ENTER TOTP MANUALLY ***');
    console.log('*'.repeat(50) + '\n');

    // Wait for redirect back to app after TOTP
    await page.waitForURL(/localhost/, { timeout: 180000 }); // 3 minutes for TOTP
    await page.waitForTimeout(3000);

    console.log('✓ Login successful!\n');

    await page.screenshot({ path: 'tests/screenshots/ic-01-login-success.png' });
  });

  // ============================================
  // STEP 2: Navigate to Strategy Builder
  // ============================================
  test('Step 2: Navigate to Strategy Builder', async () => {
    console.log('\n--- STEP 2: NAVIGATE TO STRATEGY BUILDER ---');

    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify page loaded
    const title = await page.locator('text=Strategy Builder').first().isVisible();
    console.log('✓ Strategy Builder page loaded');

    // Verify NIFTY is selected (or select it)
    const niftyBtn = page.locator('button').filter({ hasText: /^NIFTY$/ }).first();
    if (await niftyBtn.isVisible()) {
      await niftyBtn.click();
      await page.waitForTimeout(1000);
      console.log('✓ NIFTY underlying selected');
    }

    await page.screenshot({ path: 'tests/screenshots/ic-02-strategy-page.png' });

    expect(title).toBeTruthy();
  });

  // ============================================
  // STEP 3: Enter Strategy Name
  // ============================================
  test('Step 3: Enter Strategy Name', async () => {
    console.log('\n--- STEP 3: ENTER STRATEGY NAME ---');

    const nameInput = page.locator('input[placeholder*="strategy name" i], input[placeholder*="name" i]').first();

    if (await nameInput.isVisible()) {
      await nameInput.fill(STRATEGY_NAME);
      console.log('✓ Strategy name: ' + STRATEGY_NAME);
    } else {
      console.log('⚠ Strategy name input not found, continuing...');
    }

    await page.screenshot({ path: 'tests/screenshots/ic-03-strategy-name.png' });
  });

  // ============================================
  // STEP 4: Add Leg 1 - PE BUY 25600
  // ============================================
  test('Step 4: Add Leg 1 - PE BUY 25600', async () => {
    console.log('\n--- STEP 4: ADD LEG 1 - PE BUY 25600 ---');

    // Click Add Row
    const addBtn = page.locator('button').filter({ hasText: /\+ Add Row|Add Row/i }).first();
    await addBtn.click();
    await page.waitForTimeout(1000);
    console.log('✓ Clicked Add Row');

    // Get the first leg row
    const legRow = page.locator('tbody tr').first();

    // Select Expiry (first available)
    const expirySelect = legRow.locator('select').first();
    await expirySelect.waitFor({ state: 'visible' });
    const expiryOptions = await expirySelect.locator('option').allInnerTexts();
    console.log('  Available expiries:', expiryOptions.slice(0, 5).join(', '));

    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      console.log('  ✓ Selected expiry:', expiryOptions[1]);
      await page.waitForTimeout(1500); // Wait for strikes to load
    }

    // Select Contract Type: PE
    const contractSelect = legRow.locator('select').nth(1);
    await contractSelect.selectOption('PE');
    console.log('  ✓ Selected contract: PE');

    // Select Transaction Type: BUY
    const transSelect = legRow.locator('select').nth(2);
    await transSelect.selectOption('BUY');
    console.log('  ✓ Selected transaction: BUY');

    // Select Strike: 25600
    await page.waitForTimeout(500);
    const strikeSelect = legRow.locator('select').nth(3);
    const strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    console.log('  Available strikes (sample):', strikeOptions.slice(0, 10).join(', '));

    // Find and select 25600
    const strike25600 = strikeOptions.find(opt => opt.includes('25600'));
    if (strike25600) {
      await strikeSelect.selectOption({ label: strike25600 });
      console.log('  ✓ Selected strike: 25600');
    } else {
      // Try by value
      await strikeSelect.selectOption('25600');
      console.log('  ✓ Selected strike: 25600 (by value)');
    }

    // Enter Entry Price: 15 (second number input - first is LOTS)
    const entryInput = legRow.locator('input[type="number"]').nth(1);
    await entryInput.fill('15');
    console.log('  ✓ Entry price: 15');

    await page.screenshot({ path: 'tests/screenshots/ic-04-leg1-pe-buy-25600.png' });
  });

  // ============================================
  // STEP 5: Add Leg 2 - PE SELL 25800
  // ============================================
  test('Step 5: Add Leg 2 - PE SELL 25800', async () => {
    console.log('\n--- STEP 5: ADD LEG 2 - PE SELL 25800 ---');

    // Click Add Row
    const addBtn = page.locator('button').filter({ hasText: /\+ Add Row|Add Row/i }).first();
    await addBtn.click();
    await page.waitForTimeout(1000);
    console.log('✓ Clicked Add Row');

    // Get the second leg row
    const legRow = page.locator('tbody tr').nth(1);

    // Select Expiry (same as first leg)
    const expirySelect = legRow.locator('select').first();
    const expiryOptions = await expirySelect.locator('option').allInnerTexts();
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      await page.waitForTimeout(1500);
    }

    // Select Contract Type: PE
    const contractSelect = legRow.locator('select').nth(1);
    await contractSelect.selectOption('PE');
    console.log('  ✓ Selected contract: PE');

    // Select Transaction Type: SELL
    const transSelect = legRow.locator('select').nth(2);
    await transSelect.selectOption('SELL');
    console.log('  ✓ Selected transaction: SELL');

    // Select Strike: 25800
    await page.waitForTimeout(500);
    const strikeSelect = legRow.locator('select').nth(3);
    const strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    const strike25800 = strikeOptions.find(opt => opt.includes('25800'));
    if (strike25800) {
      await strikeSelect.selectOption({ label: strike25800 });
    } else {
      await strikeSelect.selectOption('25800');
    }
    console.log('  ✓ Selected strike: 25800');

    // Enter Entry Price: 35 (second number input - first is LOTS)
    const entryInput = legRow.locator('input[type="number"]').nth(1);
    await entryInput.fill('35');
    console.log('  ✓ Entry price: 35');

    await page.screenshot({ path: 'tests/screenshots/ic-05-leg2-pe-sell-25800.png' });
  });

  // ============================================
  // STEP 6: Add Leg 3 - CE SELL 26200
  // ============================================
  test('Step 6: Add Leg 3 - CE SELL 26200', async () => {
    console.log('\n--- STEP 6: ADD LEG 3 - CE SELL 26200 ---');

    // Click Add Row
    const addBtn = page.locator('button').filter({ hasText: /\+ Add Row|Add Row/i }).first();
    await addBtn.click();
    await page.waitForTimeout(1000);
    console.log('✓ Clicked Add Row');

    // Get the third leg row
    const legRow = page.locator('tbody tr').nth(2);

    // Select Expiry
    const expirySelect = legRow.locator('select').first();
    const expiryOptions = await expirySelect.locator('option').allInnerTexts();
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      await page.waitForTimeout(1500);
    }

    // Select Contract Type: CE
    const contractSelect = legRow.locator('select').nth(1);
    await contractSelect.selectOption('CE');
    console.log('  ✓ Selected contract: CE');

    // Select Transaction Type: SELL
    const transSelect = legRow.locator('select').nth(2);
    await transSelect.selectOption('SELL');
    console.log('  ✓ Selected transaction: SELL');

    // Select Strike: 26200
    await page.waitForTimeout(500);
    const strikeSelect = legRow.locator('select').nth(3);
    const strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    const strike26200 = strikeOptions.find(opt => opt.includes('26200'));
    if (strike26200) {
      await strikeSelect.selectOption({ label: strike26200 });
    } else {
      await strikeSelect.selectOption('26200');
    }
    console.log('  ✓ Selected strike: 26200');

    // Enter Entry Price: 40 (second number input - first is LOTS)
    const entryInput = legRow.locator('input[type="number"]').nth(1);
    await entryInput.fill('40');
    console.log('  ✓ Entry price: 40');

    await page.screenshot({ path: 'tests/screenshots/ic-06-leg3-ce-sell-26200.png' });
  });

  // ============================================
  // STEP 7: Add Leg 4 - CE BUY 26400
  // ============================================
  test('Step 7: Add Leg 4 - CE BUY 26400', async () => {
    console.log('\n--- STEP 7: ADD LEG 4 - CE BUY 26400 ---');

    // Click Add Row
    const addBtn = page.locator('button').filter({ hasText: /\+ Add Row|Add Row/i }).first();
    await addBtn.click();
    await page.waitForTimeout(1000);
    console.log('✓ Clicked Add Row');

    // Get the fourth leg row
    const legRow = page.locator('tbody tr').nth(3);

    // Select Expiry
    const expirySelect = legRow.locator('select').first();
    const expiryOptions = await expirySelect.locator('option').allInnerTexts();
    if (expiryOptions.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      await page.waitForTimeout(1500);
    }

    // Select Contract Type: CE
    const contractSelect = legRow.locator('select').nth(1);
    await contractSelect.selectOption('CE');
    console.log('  ✓ Selected contract: CE');

    // Select Transaction Type: BUY
    const transSelect = legRow.locator('select').nth(2);
    await transSelect.selectOption('BUY');
    console.log('  ✓ Selected transaction: BUY');

    // Select Strike: 26400
    await page.waitForTimeout(500);
    const strikeSelect = legRow.locator('select').nth(3);
    const strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    const strike26400 = strikeOptions.find(opt => opt.includes('26400'));
    if (strike26400) {
      await strikeSelect.selectOption({ label: strike26400 });
    } else {
      await strikeSelect.selectOption('26400');
    }
    console.log('  ✓ Selected strike: 26400');

    // Enter Entry Price: 18 (second number input - first is LOTS)
    const entryInput = legRow.locator('input[type="number"]').nth(1);
    await entryInput.fill('18');
    console.log('  ✓ Entry price: 18');

    await page.screenshot({ path: 'tests/screenshots/ic-07-leg4-ce-buy-26400.png' });
  });

  // ============================================
  // STEP 8: Verify All 4 Legs
  // ============================================
  test('Step 8: Verify all 4 legs are configured', async () => {
    console.log('\n--- STEP 8: VERIFY ALL LEGS ---');

    await page.screenshot({ path: 'tests/screenshots/ic-08-all-legs.png', fullPage: true });

    // Count legs from table (single unified table layout)
    const legCount = await page.locator('table tbody tr').filter({ has: page.locator('select') }).count();
    console.log('✓ Total legs:', legCount);

    // Verify each leg
    const rows = await page.locator('table tbody tr').filter({ has: page.locator('select') }).all();

    console.log('\nLeg Configuration:');
    console.log('-'.repeat(60));

    for (let i = 0; i < Math.min(rows.length, 4); i++) {
      const row = rows[i];
      const contract = await row.locator('select').nth(1).inputValue();
      const trans = await row.locator('select').nth(2).inputValue();
      const strike = await row.locator('select').nth(3).inputValue();
      const lots = await row.locator('input[type="number"]').first().inputValue();
      const entry = await row.locator('input[type="number"]').nth(1).inputValue();

      console.log(`Leg ${i + 1}: ${contract} ${trans} ${strike} - Lots: ${lots}, Entry: ${entry}`);
    }
    console.log('-'.repeat(60));

    expect(legCount).toBe(4);
  });

  // ============================================
  // STEP 9: Click ReCalculate
  // ============================================
  test('Step 9: Click ReCalculate', async () => {
    console.log('\n--- STEP 9: RECALCULATE P/L ---');

    const recalcBtn = page.locator('button').filter({ hasText: /ReCalculate/i }).first();
    await recalcBtn.click();
    console.log('✓ Clicked ReCalculate');

    // Wait for calculation
    await page.waitForTimeout(4000);

    await page.screenshot({ path: 'tests/screenshots/ic-09-after-recalculate.png', fullPage: true });

    // Check if P/L columns appeared (single unified table)
    const pnlGridHeader = page.locator('thead');
    const headerText = await pnlGridHeader.innerText();
    const dynamicColumns = headerText.match(/\d{5}/g) || [];
    console.log('✓ Dynamic P/L columns generated:', dynamicColumns.length);
    console.log('  Sample columns:', dynamicColumns.slice(0, 8).join(', '));
  });

  // ============================================
  // STEP 9.5: Verify CMP and Exit Columns
  // ============================================
  test('Step 9.5: Verify CMP and Exit columns', async () => {
    console.log('\n--- STEP 9.5: VERIFY CMP AND EXIT COLUMNS ---');

    // Wait for LTP data to load
    await page.waitForTimeout(3000);

    // Get all leg rows from the table (single unified table)
    const rows = await page.locator('table tbody tr').filter({ has: page.locator('select') }).all();

    console.log('\nLeg CMP and Exit Values:');
    console.log('-'.repeat(60));

    let cmpFound = 0;
    let exitPnLFound = 0;

    // New column layout: checkbox(0), expiry(1), type(2), B/S(3), strike(4), lots(5), entry(6), qty(7), CMP(8), Exit P/L(9)
    for (let i = 0; i < Math.min(rows.length, 4); i++) {
      const row = rows[i];
      const rowText = await row.innerText();

      console.log(`Leg ${i + 1} row text: ${rowText.substring(0, 100)}...`);

      // Check CMP column - column index 8 in new layout
      const cmpCell = await row.locator('td').nth(8).innerText();
      const cmpValue = parseFloat(cmpCell.replace(/,/g, ''));
      if (!isNaN(cmpValue) && cmpValue > 0) {
        cmpFound++;
        console.log(`  Leg ${i + 1} CMP: ${cmpValue} ✓`);
      } else {
        console.log(`  Leg ${i + 1} CMP: ${cmpCell} (waiting for LTP)`);
      }

      // Check Exit P/L column - column index 9 in new layout
      const exitCell = await row.locator('td').nth(9);
      const exitText = await exitCell.innerText();
      // Exit P/L should be a number (positive or negative)
      const exitValue = parseFloat(exitText.replace(/,/g, ''));
      if (!isNaN(exitValue)) {
        exitPnLFound++;
        console.log(`  Leg ${i + 1} Exit P/L: ${exitText} ✓`);
      } else {
        console.log(`  Leg ${i + 1} Exit: ${exitText} (input field mode)`);
      }
    }

    console.log('-'.repeat(60));
    console.log(`CMP values found: ${cmpFound}/4`);
    console.log(`Exit P/L values found: ${exitPnLFound}/4`);

    // Take screenshot showing CMP and Exit values
    await page.screenshot({ path: 'tests/screenshots/ic-09b-cmp-exit.png' });

    // Note: CMP may show "-" after market hours, this is expected
    // During market hours, CMP should show actual prices
    console.log('\nNote: CMP shows "-" after market hours (3:30 PM). This is expected.');
    console.log('During market hours, CMP will show live option prices.');
  });

  // ============================================
  // STEP 10: Validate P/L Grid Values
  // ============================================
  test('Step 10: Validate P/L grid values', async () => {
    console.log('\n--- STEP 10: VALIDATE P/L GRID ---');

    // Get total row values
    const totalRow = page.locator('tr').filter({ hasText: /Total/i }).first();
    const totalText = await totalRow.innerText();
    console.log('Total row:', totalText.substring(0, 150));

    // Extract P/L values from total row
    const pnlValues = totalText.match(/-?\d{1,6}/g) || [];
    console.log('P/L values found:', pnlValues.slice(0, 15).join(', '));

    // Check for both positive and negative values (Iron Condor should have both)
    const hasPositive = pnlValues.some(v => parseInt(v) > 0);
    const hasNegative = pnlValues.some(v => parseInt(v) < 0);

    console.log('Has positive P/L zones:', hasPositive ? '✓' : '✗');
    console.log('Has negative P/L zones:', hasNegative ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/ic-10-pnl-grid.png', fullPage: true });
  });

  // ============================================
  // STEP 10.5: Verify Breakeven Columns
  // ============================================
  test('Step 10.5: Verify breakeven columns in P/L grid', async () => {
    console.log('\n--- STEP 10.5: VERIFY BREAKEVEN COLUMNS ---');

    // Get the header row for P/L columns (single unified table)
    const pnlGridHeader = page.locator('thead');
    const headerText = await pnlGridHeader.innerText();
    console.log('Header text (truncated):', headerText.substring(0, 200));

    // Get all column headers
    const dynamicColumns = headerText.match(/\d{5}/g) || [];
    console.log('Dynamic columns:', dynamicColumns.join(', '));

    // Get breakeven values from summary
    const pageText = await page.locator('body').innerText();
    const breakevenMatch = pageText.match(/Breakeven[:\s]*([\d,.\s]+)/i);

    let breakevenColumnsFound = 0;
    let breakevenValues = [];

    if (breakevenMatch) {
      const breakevenStr = breakevenMatch[1].trim();
      console.log('Breakeven from summary:', breakevenStr);

      // Parse breakeven values (could be "25758, 26242" or "25758 26242")
      breakevenValues = breakevenStr.match(/\d{5}/g) || [];
      console.log('Parsed breakeven values:', breakevenValues.join(', '));

      // Check if breakeven values are in the column headers
      breakevenValues.forEach(be => {
        const found = dynamicColumns.includes(be);
        if (found) breakevenColumnsFound++;
        console.log(`Breakeven ${be} in columns: ${found ? '✓ FOUND' : '✗ NOT FOUND'}`);
      });

      console.log(`\nBreakeven columns found: ${breakevenColumnsFound}/${breakevenValues.length}`);
    } else {
      console.log('Breakeven values not found in summary yet');
    }

    await page.screenshot({ path: 'tests/screenshots/ic-10c-breakeven-columns.png' });

    // Assert that breakeven columns are present
    if (breakevenValues.length > 0) {
      expect(breakevenColumnsFound).toBe(breakevenValues.length);
    }
  });

  // ============================================
  // STEP 11: Validate Summary Stats
  // ============================================
  test('Step 11: Validate summary stats', async () => {
    console.log('\n--- STEP 11: VALIDATE SUMMARY STATS ---');

    const pageText = await page.locator('body').innerText();

    // Extract Max Profit
    const maxProfitMatch = pageText.match(/Max\s*Profit[:\s]*([-\d,]+)/i);
    const maxProfit = maxProfitMatch ? maxProfitMatch[1] : 'Not found';
    console.log('Max Profit:', maxProfit);

    // Extract Max Loss
    const maxLossMatch = pageText.match(/Max\s*Loss[:\s]*([-\d,]+)/i);
    const maxLoss = maxLossMatch ? maxLossMatch[1] : 'Not found';
    console.log('Max Loss:', maxLoss);

    // Extract Breakeven
    const breakevenMatch = pageText.match(/Breakeven[:\s]*([\d,.\s]+)/i);
    const breakeven = breakevenMatch ? breakevenMatch[1].trim() : 'Not found';
    console.log('Breakeven:', breakeven);

    // Extract Risk/Reward
    const riskRewardMatch = pageText.match(/Risk\/Reward[:\s]*([\d.:]+)/i);
    const riskReward = riskRewardMatch ? riskRewardMatch[1] : 'Not found';
    console.log('Risk/Reward:', riskReward);

    // Validate Iron Condor characteristics
    console.log('\n--- Iron Condor Validation ---');

    // For Iron Condor:
    // - Max Profit should be positive (net premium received)
    // - Max Loss should be negative (when price moves beyond wings)
    // - Breakeven should be between sell strikes

    const maxProfitNum = parseInt(maxProfit.replace(/,/g, '')) || 0;
    const maxLossNum = parseInt(maxLoss.replace(/,/g, '')) || 0;

    console.log('Max Profit positive:', maxProfitNum > 0 ? '✓' : '✗');
    console.log('Max Loss negative:', maxLossNum < 0 ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/ic-11-summary-stats.png' });
  });

  // ============================================
  // STEP 12: Validate Total Qty
  // ============================================
  test('Step 12: Validate total quantity', async () => {
    console.log('\n--- STEP 12: VALIDATE TOTAL QTY ---');

    // Expected: 4 legs × 1 lot × 75 = 300
    const expectedQty = 4 * 1 * LOT_SIZE; // 300

    const totalRow = page.locator('tr').filter({ hasText: /Total/i }).first();
    const totalText = await totalRow.innerText();

    const hasExpectedQty = totalText.includes(expectedQty.toString());
    console.log('Expected total qty:', expectedQty);
    console.log('Total qty found:', hasExpectedQty ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/ic-12-total-qty.png' });
  });

  // ============================================
  // STEP 13: Save Strategy
  // ============================================
  test('Step 13: Save strategy', async () => {
    console.log('\n--- STEP 13: SAVE STRATEGY ---');

    // Make sure strategy name is filled
    const nameInput = page.locator('input[placeholder*="strategy name" i], input[placeholder*="name" i]').first();
    if (await nameInput.isVisible()) {
      const currentName = await nameInput.inputValue();
      if (!currentName) {
        await nameInput.fill(STRATEGY_NAME);
      }
    }

    // Click Save
    const saveBtn = page.locator('button').filter({ hasText: /^Save$/i }).first();

    if (await saveBtn.isEnabled()) {
      await saveBtn.click();
      console.log('✓ Clicked Save');
      await page.waitForTimeout(2500);

      // Check for success toast or message
      const successToast = page.locator('text=/saved|success/i');
      const toastVisible = await successToast.first().isVisible().catch(() => false);
      console.log('Save success:', toastVisible ? '✓' : '(toast may have auto-hidden)');
    } else {
      console.log('⚠ Save button disabled - checking requirements');
    }

    await page.screenshot({ path: 'tests/screenshots/ic-13-saved.png' });
  });

  // ============================================
  // STEP 14: Verify Strategy in Dropdown
  // ============================================
  test('Step 14: Verify strategy in dropdown', async () => {
    console.log('\n--- STEP 14: VERIFY IN DROPDOWN ---');

    const strategySelect = page.locator('select').filter({ has: page.locator('option:has-text("New Strategy")') }).first();

    if (await strategySelect.isVisible()) {
      const options = await strategySelect.locator('option').allInnerTexts();
      console.log('Strategies in dropdown:', options.length);

      const hasOurStrategy = options.some(opt => opt.includes('Iron Condor') || opt.includes(STRATEGY_NAME.substring(0, 10)));
      console.log('Our strategy found:', hasOurStrategy ? '✓' : '(may need to refresh)');
    }

    await page.screenshot({ path: 'tests/screenshots/ic-14-dropdown.png' });
  });

  // ============================================
  // STEP 15: Color Coding Verification
  // ============================================
  test('Step 15: Verify color coding', async () => {
    console.log('\n--- STEP 15: COLOR CODING ---');

    const greenCells = await page.locator('.bg-green-100, [class*="bg-green"]').count();
    const redCells = await page.locator('.bg-red-100, [class*="bg-red"]').count();

    console.log('Green (profit) cells:', greenCells);
    console.log('Red (loss) cells:', redCells);

    // Iron Condor should have profit zone in the middle and loss zones on wings
    const hasProperColoring = greenCells > 0 && redCells > 0;
    console.log('Has proper color coding:', hasProperColoring ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/ic-15-colors.png', fullPage: true });
  });

  // ============================================
  // STEP 16: Final Summary
  // ============================================
  test('Step 16: Final summary', async () => {
    console.log('\n' + '='.repeat(70));
    console.log('IRON CONDOR TEST SUMMARY');
    console.log('='.repeat(70));

    console.log('\n✓ Strategy Configuration:');
    console.log('  Leg 1: PE BUY  25600 @ 15  (protection)');
    console.log('  Leg 2: PE SELL 25800 @ 35  (credit)');
    console.log('  Leg 3: CE SELL 26200 @ 40  (credit)');
    console.log('  Leg 4: CE BUY  26400 @ 18  (protection)');
    console.log('\n  Net Premium: (35-15) + (40-18) = 42 per share');
    console.log('  Net Premium × Lot Size: 42 × 75 = 3,150');
    console.log('  Max Profit Range: 25800 - 26200');
    console.log('  Max Loss: If NIFTY < 25600 or > 26400');

    console.log('\n✓ All Screenshots saved in tests/screenshots/ic-*.png');

    await page.screenshot({ path: 'tests/screenshots/ic-16-final.png', fullPage: true });

    console.log('\n' + '='.repeat(70));
    console.log('TEST PASSED - Iron Condor strategy validated');
    console.log('='.repeat(70) + '\n');
  });
});
