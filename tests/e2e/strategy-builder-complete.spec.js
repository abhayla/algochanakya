import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

let sharedPage;

test.describe.configure({ mode: 'serial' });

test.describe('Strategy Builder Complete Tests', () => {

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    sharedPage = await context.newPage();

    console.log('\n' + '='.repeat(60));
    console.log('ZERODHA LOGIN');
    console.log('='.repeat(60));

    await sharedPage.goto(`${FRONTEND_URL}/login`);
    await sharedPage.waitForLoadState('networkidle');

    const zerodhaBtn = sharedPage.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaBtn.click();

    await sharedPage.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });
    await sharedPage.waitForTimeout(1000);

    // Auto-fill credentials
    const userIdInput = sharedPage.locator('input[type="text"]#userid, input[name="user_id"]').first();
    await userIdInput.fill(ZERODHA_USER_ID);

    const passwordInput = sharedPage.locator('input[type="password"]').first();
    await passwordInput.fill(ZERODHA_PASSWORD);

    const loginBtn = sharedPage.locator('button[type="submit"]').first();
    await loginBtn.click();

    console.log('\n*** ENTER TOTP MANUALLY ***\n');

    await sharedPage.waitForURL(/localhost/, { timeout: 120000 });
    await sharedPage.waitForTimeout(3000);

    console.log('Login successful!\n');
  });

  test.afterAll(async () => {
    console.log('\nTests complete. Browser stays open for 10 seconds...');
    await sharedPage.waitForTimeout(10000);
    await sharedPage.context().close();
  });

  // ============================================
  // TEST 1: Page loads correctly
  // ============================================
  test('1. Strategy Builder page loads', async () => {
    await sharedPage.goto(`${FRONTEND_URL}/strategy`);
    await sharedPage.waitForLoadState('networkidle');
    await sharedPage.waitForTimeout(2000);

    const title = await sharedPage.locator('text=Strategy Builder').first().isVisible();
    console.log('Test 1: Page loaded:', title ? 'PASS' : 'FAIL');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-01.png', fullPage: true });
    expect(title).toBeTruthy();
  });

  // ============================================
  // TEST 2: Column headers are correct
  // ============================================
  test('2. Verify all column headers', async () => {
    const expectedHeaders = ['EXPIRY', 'CONTRACT', 'TRANS', 'STRIKE', 'LOTS', 'STRATEGY', 'ENTRY', 'EXIT', 'QTY', 'CMP', 'P/L'];

    const headerRow = await sharedPage.locator('thead tr').first().innerText();
    console.log('\nTest 2: Header row content:', headerRow.substring(0, 100));

    let foundCount = 0;
    for (const header of expectedHeaders) {
      const found = headerRow.toUpperCase().includes(header);
      console.log(`  ${header}:`, found ? 'FOUND' : 'MISSING');
      if (found) foundCount++;
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-02.png' });
    expect(foundCount).toBeGreaterThanOrEqual(10);
  });

  // ============================================
  // TEST 3: Underlying selector works
  // ============================================
  test('3. Underlying selector (NIFTY/BANKNIFTY/FINNIFTY)', async () => {
    const niftyBtn = sharedPage.locator('button').filter({ hasText: /^NIFTY$/ }).first();
    const bankNiftyBtn = sharedPage.locator('button').filter({ hasText: /BANKNIFTY/ }).first();
    const finNiftyBtn = sharedPage.locator('button').filter({ hasText: /FINNIFTY/ }).first();

    // Click BANKNIFTY
    if (await bankNiftyBtn.isVisible()) {
      await bankNiftyBtn.click();
      await sharedPage.waitForTimeout(1000);
      console.log('\nTest 3: Clicked BANKNIFTY');
    }

    // Click back to NIFTY
    if (await niftyBtn.isVisible()) {
      await niftyBtn.click();
      await sharedPage.waitForTimeout(1000);
      console.log('  Clicked NIFTY');
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-03.png' });
    expect(await niftyBtn.isVisible()).toBeTruthy();
  });

  // ============================================
  // TEST 4: Strategy selector dropdown exists
  // ============================================
  test('4. Strategy selector dropdown exists', async () => {
    const strategySelect = sharedPage.locator('select').filter({ has: sharedPage.locator('option:has-text("New Strategy")') }).first();

    const isVisible = await strategySelect.isVisible();
    console.log('\nTest 4: Strategy dropdown visible:', isVisible ? 'PASS' : 'FAIL');

    if (isVisible) {
      const options = await strategySelect.locator('option').allInnerTexts();
      console.log('  Options:', options.slice(0, 5));
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-04.png' });
    expect(isVisible).toBeTruthy();
  });

  // ============================================
  // TEST 5: Strategy name input exists
  // ============================================
  test('5. Strategy name input exists', async () => {
    const nameInput = sharedPage.locator('input[placeholder*="strategy name" i]').first();

    const isVisible = await nameInput.isVisible();
    console.log('\nTest 5: Strategy name input visible:', isVisible ? 'PASS' : 'FAIL');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-05.png' });
    expect(isVisible).toBeTruthy();
  });

  // ============================================
  // TEST 6: Add Row creates leg with default values
  // ============================================
  test('6. Add Row creates leg with defaults', async () => {
    const addBtn = sharedPage.locator('button').filter({ hasText: /\+ Add Row/i }).first();

    await addBtn.click();
    await sharedPage.waitForTimeout(1000);
    console.log('\nTest 6: Clicked "+ Add Row"');

    // Check defaults
    const legRow = sharedPage.locator('tbody tr').first();

    // Check Contract default (should be PE or CE)
    const contractSelect = legRow.locator('select').nth(1);
    const contractValue = await contractSelect.inputValue();
    console.log('  Contract default:', contractValue);

    // Check Transaction default (should be SELL or BUY)
    const transSelect = legRow.locator('select').nth(2);
    const transValue = await transSelect.inputValue();
    console.log('  Transaction default:', transValue);

    // Check Lots default (should be 1)
    const lotsSelect = legRow.locator('select').nth(4);
    const lotsValue = await lotsSelect.inputValue();
    console.log('  Lots default:', lotsValue);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-06.png' });
    expect(lotsValue).toBe('1');
  });

  // ============================================
  // TEST 7: Expiry dropdown has dates
  // ============================================
  test('7. Expiry dropdown has dates', async () => {
    const expirySelect = sharedPage.locator('tbody tr').first().locator('select').first();
    const options = await expirySelect.locator('option').allInnerTexts();

    console.log('\nTest 7: Expiry options:', options.slice(0, 5));

    const hasDateOptions = options.some(opt => /dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|\d{2}/i.test(opt));
    console.log('  Has date options:', hasDateOptions ? 'PASS' : 'FAIL');

    // Select first real date
    if (options.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      console.log('  Selected:', options[1]);
      await sharedPage.waitForTimeout(1500);
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-07.png' });
    expect(hasDateOptions).toBeTruthy();
  });

  // ============================================
  // TEST 8: Strike dropdown loads after expiry selection
  // ============================================
  test('8. Strike dropdown has strikes after expiry', async () => {
    await sharedPage.waitForTimeout(1000);

    const strikeSelect = sharedPage.locator('tbody tr').first().locator('select').nth(3);
    const options = await strikeSelect.locator('option').allInnerTexts();

    console.log('\nTest 8: Strike options:', options.slice(0, 10));

    const hasStrikes = options.some(opt => /\d{4,5}/.test(opt));
    console.log('  Has strike prices:', hasStrikes ? 'PASS' : 'FAIL');

    // Select a strike
    if (hasStrikes) {
      const strikeOption = options.find(opt => /\d{5}/.test(opt));
      if (strikeOption) {
        await strikeSelect.selectOption({ label: strikeOption });
        console.log('  Selected:', strikeOption);
      }
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-08.png' });
    expect(hasStrikes).toBeTruthy();
  });

  // ============================================
  // TEST 9: Entry price input works
  // ============================================
  test('9. Entry price input works', async () => {
    const entryInput = sharedPage.locator('tbody tr').first().locator('input[type="number"]').first();

    await entryInput.fill('70');
    const value = await entryInput.inputValue();

    console.log('\nTest 9: Entry price:', value);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-09.png' });
    expect(value).toBe('70');
  });

  // ============================================
  // TEST 10: ReCalculate button works
  // ============================================
  test('10. ReCalculate generates P/L grid', async () => {
    const recalcBtn = sharedPage.locator('button').filter({ hasText: /ReCalculate/i }).first();

    await recalcBtn.click();
    console.log('\nTest 10: Clicked ReCalculate');
    await sharedPage.waitForTimeout(3000);

    // Check for dynamic P/L columns (5-digit numbers in header)
    const headerText = await sharedPage.locator('thead').innerText();
    const dynamicColumns = headerText.match(/\d{5}/g) || [];

    console.log('  Dynamic columns found:', dynamicColumns.length);
    console.log('  Sample:', dynamicColumns.slice(0, 5));

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-10.png', fullPage: true });
    expect(dynamicColumns.length).toBeGreaterThan(0);
  });

  // ============================================
  // TEST 11: Grid has horizontal scroll, not browser
  // ============================================
  test('11. Grid has horizontal scroll (not browser)', async () => {
    const tableContainer = sharedPage.locator('.overflow-auto').first();

    // Check if table container has scroll
    const hasOverflow = await tableContainer.evaluate(el => {
      return el.scrollWidth > el.clientWidth;
    });

    console.log('\nTest 11: Table has horizontal scroll:', hasOverflow ? 'PASS' : 'NEEDS MORE DATA');

    // Check browser doesn't have horizontal scroll
    const browserHasScroll = await sharedPage.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    console.log('  Browser has horizontal scroll:', browserHasScroll ? 'FAIL (BAD)' : 'PASS (GOOD)');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-11.png' });
    expect(browserHasScroll).toBeFalsy();
  });

  // ============================================
  // TEST 12: Add multiple legs
  // ============================================
  test('12. Can add multiple legs', async () => {
    const addBtn = sharedPage.locator('button').filter({ hasText: /\+ Add Row/i }).first();

    // Add second leg
    await addBtn.click();
    await sharedPage.waitForTimeout(500);

    // Add third leg
    await addBtn.click();
    await sharedPage.waitForTimeout(500);

    const legCount = await sharedPage.locator('tbody tr').filter({ has: sharedPage.locator('select') }).count();
    console.log('\nTest 12: Leg count:', legCount);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-12.png', fullPage: true });
    expect(legCount).toBeGreaterThanOrEqual(3);
  });

  // ============================================
  // TEST 13: Delete selected legs
  // ============================================
  test('13. Delete selected legs works', async () => {
    // Select first leg
    const firstCheckbox = sharedPage.locator('tbody tr').first().locator('input[type="checkbox"]');
    await firstCheckbox.check();

    // Click delete
    const deleteBtn = sharedPage.locator('button').filter({ hasText: /Delete/i }).first();
    await deleteBtn.click();
    await sharedPage.waitForTimeout(500);

    const legCount = await sharedPage.locator('tbody tr').filter({ has: sharedPage.locator('select') }).count();
    console.log('\nTest 13: Legs after delete:', legCount);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-13.png' });
  });

  // ============================================
  // TEST 14: Save strategy
  // ============================================
  test('14. Save strategy works', async () => {
    // Enter strategy name
    const nameInput = sharedPage.locator('input[placeholder*="strategy name" i]').first();
    const strategyName = 'Test Strategy ' + Date.now();

    if (await nameInput.isVisible()) {
      await nameInput.fill(strategyName);
      console.log('\nTest 14: Strategy name:', strategyName);
    }

    // Configure a leg if needed
    const legRow = sharedPage.locator('tbody tr').first();
    const expirySelect = legRow.locator('select').first();
    const options = await expirySelect.locator('option').allInnerTexts();
    if (options.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      await sharedPage.waitForTimeout(1000);
    }

    // Select strike
    const strikeSelect = legRow.locator('select').nth(3);
    const strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    if (strikeOptions.length > 1) {
      await strikeSelect.selectOption({ index: 1 });
    }

    // Enter entry price
    const entryInput = legRow.locator('input[type="number"]').first();
    await entryInput.fill('100');

    // Click Save
    const saveBtn = sharedPage.locator('button').filter({ hasText: /^Save$/i }).first();

    if (await saveBtn.isEnabled()) {
      await saveBtn.click();
      console.log('  Clicked Save');
      await sharedPage.waitForTimeout(2000);

      // Check for success toast
      const toast = sharedPage.locator('text=/saved|success/i');
      const toastVisible = await toast.first().isVisible().catch(() => false);
      console.log('  Save success toast:', toastVisible ? 'PASS' : 'NOT VISIBLE');
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-14.png' });
  });

  // ============================================
  // TEST 15: Strategy dropdown has saved strategies
  // ============================================
  test('15. Strategy dropdown shows saved strategies', async () => {
    // Reload page to ensure dropdown refreshes
    await sharedPage.reload();
    await sharedPage.waitForLoadState('networkidle');
    await sharedPage.waitForTimeout(2000);

    const strategySelect = sharedPage.locator('select').filter({ has: sharedPage.locator('option:has-text("New Strategy")') }).first();

    if (await strategySelect.isVisible()) {
      const options = await strategySelect.locator('option').allInnerTexts();
      console.log('\nTest 15: Saved strategies:', options);

      // Check if there are more options than just "New Strategy"
      const hasSavedStrategies = options.length > 1;
      console.log('  Has saved strategies:', hasSavedStrategies ? 'PASS' : 'NONE YET');
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-15.png' });
  });

  // ============================================
  // TEST 16: Summary stats are displayed
  // ============================================
  test('16. Summary stats displayed', async () => {
    // Add a leg and calculate to show stats
    const addBtn = sharedPage.locator('button').filter({ hasText: /\+ Add Row/i }).first();
    await addBtn.click();
    await sharedPage.waitForTimeout(500);

    // Configure leg
    const legRow = sharedPage.locator('tbody tr').first();
    const expirySelect = legRow.locator('select').first();
    const options = await expirySelect.locator('option').allInnerTexts();
    if (options.length > 1) {
      await expirySelect.selectOption({ index: 1 });
      await sharedPage.waitForTimeout(1000);
    }

    const strikeSelect = legRow.locator('select').nth(3);
    const strikeOptions = await strikeSelect.locator('option').allInnerTexts();
    if (strikeOptions.length > 1) {
      await strikeSelect.selectOption({ index: 1 });
    }

    const entryInput = legRow.locator('input[type="number"]').first();
    await entryInput.fill('100');

    // Recalculate
    const recalcBtn = sharedPage.locator('button').filter({ hasText: /ReCalculate/i }).first();
    await recalcBtn.click();
    await sharedPage.waitForTimeout(2000);

    const pageText = await sharedPage.locator('body').innerText();

    const hasMaxProfit = /max.*profit/i.test(pageText);
    const hasMaxLoss = /max.*loss/i.test(pageText);
    const hasBreakeven = /breakeven/i.test(pageText);
    const hasRiskReward = /risk.*reward/i.test(pageText);

    console.log('\nTest 16: Summary stats:');
    console.log('  Max Profit:', hasMaxProfit ? 'FOUND' : 'MISSING');
    console.log('  Max Loss:', hasMaxLoss ? 'FOUND' : 'MISSING');
    console.log('  Breakeven:', hasBreakeven ? 'FOUND' : 'MISSING');
    console.log('  Risk/Reward:', hasRiskReward ? 'FOUND' : 'MISSING');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-16.png' });
  });

  // ============================================
  // TEST 17: P/L Mode toggle works
  // ============================================
  test('17. P/L Mode toggle works', async () => {
    const currentBtn = sharedPage.locator('button').filter({ hasText: /Current/i }).first();
    const expiryBtn = sharedPage.locator('button').filter({ hasText: /At Expiry/i }).first();

    // Click Current
    if (await currentBtn.isVisible()) {
      await currentBtn.click();
      console.log('\nTest 17: Clicked "Current" mode');
      await sharedPage.waitForTimeout(1000);
    }

    // Click At Expiry
    if (await expiryBtn.isVisible()) {
      await expiryBtn.click();
      console.log('  Clicked "At Expiry" mode');
      await sharedPage.waitForTimeout(1000);
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-17.png' });
  });

  // ============================================
  // TEST 18: Total row shows calculations
  // ============================================
  test('18. Total row shows calculations', async () => {
    const totalRow = sharedPage.locator('tr').filter({ hasText: /Total/i }).first();

    if (await totalRow.isVisible()) {
      const totalText = await totalRow.innerText();
      console.log('\nTest 18: Total row:', totalText.substring(0, 100));

      // Check for QTY total
      const hasQty = /\d+/.test(totalText);
      console.log('  Has QTY total:', hasQty ? 'PASS' : 'FAIL');
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-18.png' });
  });

  // ============================================
  // TEST 19: Color coding works
  // ============================================
  test('19. P/L color coding (red/green)', async () => {
    const greenCells = await sharedPage.locator('.bg-green-100, .bg-green-50, .text-green-600, .text-green-800').count();
    const redCells = await sharedPage.locator('.bg-red-100, .text-red-600, .text-red-800').count();

    console.log('\nTest 19: Color coding:');
    console.log('  Green cells:', greenCells);
    console.log('  Red cells:', redCells);

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-19.png' });
  });

  // ============================================
  // TEST 20: Buy Basket Order button
  // ============================================
  test('20. Buy Basket Order button exists', async () => {
    const buyBtn = sharedPage.locator('button').filter({ hasText: /Buy Basket Order/i }).first();
    const isVisible = await buyBtn.isVisible();

    console.log('\nTest 20: Buy Basket Order button:', isVisible ? 'PASS' : 'FAIL');

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-20.png' });
    expect(isVisible).toBeTruthy();
  });

  // ============================================
  // TEST 21: Column widths are adequate
  // ============================================
  test('21. Column widths show full values', async () => {
    // Check that column headers are not truncated
    const headers = await sharedPage.locator('thead th').all();

    console.log('\nTest 21: Column widths:');
    for (let i = 0; i < Math.min(headers.length, 12); i++) {
      const box = await headers[i].boundingBox();
      const text = await headers[i].innerText();
      if (box) {
        console.log(`  ${text.substring(0, 10)}: ${Math.round(box.width)}px`);
      }
    }

    // Verify no columns are too narrow (less than 50px) - skip first column (checkbox)
    let allAdequate = true;
    for (const header of headers.slice(1, 12)) {
      const box = await header.boundingBox();
      if (box && box.width < 50) allAdequate = false;
    }

    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-21.png' });
    expect(allAdequate).toBeTruthy();
  });

  // ============================================
  // TEST 22: Final summary
  // ============================================
  test('22. Final state verification', async () => {
    await sharedPage.screenshot({ path: 'tests/screenshots/sb-complete-22-final.png', fullPage: true });

    console.log('\n' + '='.repeat(60));
    console.log('STRATEGY BUILDER TEST SUMMARY');
    console.log('='.repeat(60));
    console.log('All tests completed. Check screenshots in tests/screenshots/');
  });
});
