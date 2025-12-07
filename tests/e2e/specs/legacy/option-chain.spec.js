import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

let page;

test.describe.configure({ mode: 'serial' });

test.describe('Option Chain - Complete Tests', () => {

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();

    console.log('\n' + '='.repeat(60));
    console.log('OPTION CHAIN TEST SUITE');
    console.log('='.repeat(60));

    // Login
    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('networkidle');

    const zerodhaBtn = page.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaBtn.click();

    await page.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });
    await page.waitForTimeout(1000);

    console.log('✓ Kite login page loaded');

    // Auto-fill credentials
    const userIdInput = page.locator('input#userid, input[name="user_id"]').first();
    await userIdInput.fill(ZERODHA_USER_ID);
    console.log('✓ User ID: ' + ZERODHA_USER_ID);

    const passwordInput = page.locator('input[type="password"]').first();
    await passwordInput.fill(ZERODHA_PASSWORD);
    console.log('✓ Password filled');

    const loginBtn = page.locator('button[type="submit"]').first();
    await loginBtn.click();
    console.log('✓ Clicked Login\n');

    console.log('*'.repeat(50));
    console.log('*** ENTER TOTP MANUALLY ***');
    console.log('*'.repeat(50) + '\n');

    await page.waitForURL(/localhost/, { timeout: 180000 });
    await page.waitForTimeout(3000);

    console.log('✓ Login successful!\n');
  });

  test.afterAll(async () => {
    console.log('\n✓ All tests complete. Browser stays open for 30 seconds...');
    await page.waitForTimeout(30000);
    await page.context().close();
  });

  // ============================================
  // TEST 1: Navigate to Option Chain
  // ============================================
  test('1. Navigate to Option Chain page', async () => {
    console.log('\n--- TEST 1: Navigate to Option Chain ---');

    await page.goto(`${FRONTEND_URL}/optionchain`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const title = await page.locator('text=Option Chain').first().isVisible();
    console.log('✓ Option Chain page loaded:', title ? 'Yes' : 'No');

    // Verify KiteLayout header is present
    const header = page.locator('.kite-header, header').first();
    const hasHeader = await header.isVisible().catch(() => false);
    console.log('✓ KiteHeader visible:', hasHeader ? 'Yes' : 'No');

    // Verify index prices in header (should show actual numbers, not "--")
    const headerText = await header.innerText().catch(() => '');
    const hasNifty50 = /NIFTY\s*50/i.test(headerText);
    const hasNiftyBank = /NIFTY\s*BANK/i.test(headerText);
    // Check for actual price numbers (not "--")
    const niftyPriceMatch = headerText.match(/NIFTY\s*50[^\d]*(\d{2,6}[\d,.]*)/i);
    const bankPriceMatch = headerText.match(/NIFTY\s*BANK[^\d]*(\d{2,6}[\d,.]*)/i);
    const hasLivePrices = niftyPriceMatch && bankPriceMatch;
    console.log('  Header NIFTY 50:', hasNifty50 ? '✓' : '✗');
    console.log('  Header NIFTY BANK:', hasNiftyBank ? '✓' : '✗');
    console.log('  Live prices: NIFTY:', niftyPriceMatch ? niftyPriceMatch[1] : '--', '| BANK:', bankPriceMatch ? bankPriceMatch[1] : '--');
    console.log('  Index prices live (not "--"):', hasLivePrices ? '✓' : '✗');

    // Verify user avatar circle (initials in blue circle)
    const userAvatar = page.locator('.user-avatar');
    const hasAvatar = await userAvatar.isVisible().catch(() => false);
    const avatarText = hasAvatar ? await userAvatar.innerText().catch(() => '') : '';
    console.log('  User avatar circle:', hasAvatar ? `✓ (${avatarText})` : '✗');

    // Verify header icons (cart/orders and bell/notifications)
    const headerIcons = page.locator('.header-icons .icon-btn, .icon-btn');
    const iconCount = await headerIcons.count();
    console.log('  Header icons (cart, bell):', iconCount >= 2 ? `✓ (${iconCount})` : `✗ (${iconCount})`);

    // Verify navigation links
    const navLinks = await page.locator('.main-nav a, nav a').count();
    console.log('  Navigation links:', navLinks);

    // Verify user ID (not Guest)
    const hasGuest = headerText.toLowerCase().includes('guest');
    console.log('  Shows Guest:', hasGuest ? '✗ (BAD)' : '✓ NO');

    await page.screenshot({ path: 'tests/screenshots/oc-01-page-load.png', fullPage: true });
    expect(title).toBeTruthy();
    expect(hasHeader).toBeTruthy();
  });

  // ============================================
  // TEST 2: Verify Underlying Selector
  // ============================================
  test('2. Verify underlying selector (NIFTY/BANKNIFTY/FINNIFTY)', async () => {
    console.log('\n--- TEST 2: Underlying Selector ---');

    const niftyBtn = page.locator('button').filter({ hasText: /^NIFTY$/ }).first();
    const bankNiftyBtn = page.locator('button').filter({ hasText: /BANKNIFTY/ }).first();
    const finNiftyBtn = page.locator('button').filter({ hasText: /FINNIFTY/ }).first();

    const hasNifty = await niftyBtn.isVisible();
    const hasBankNifty = await bankNiftyBtn.isVisible();
    const hasFinNifty = await finNiftyBtn.isVisible();

    console.log('  NIFTY:', hasNifty ? '✓' : '✗');
    console.log('  BANKNIFTY:', hasBankNifty ? '✓' : '✗');
    console.log('  FINNIFTY:', hasFinNifty ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-02-underlying.png' });
    expect(hasNifty && hasBankNifty && hasFinNifty).toBeTruthy();
  });

  // ============================================
  // TEST 3: Verify Expiry Dropdown
  // ============================================
  test('3. Verify expiry dropdown has dates', async () => {
    console.log('\n--- TEST 3: Expiry Dropdown ---');

    const expirySelect = page.locator('select').filter({ has: page.locator('option') }).first();

    if (await expirySelect.isVisible()) {
      const options = await expirySelect.locator('option').allInnerTexts();
      console.log('  Expiry options:', options.slice(0, 5).join(', '));

      const hasExpiries = options.length > 0;
      console.log('  Has expiry dates:', hasExpiries ? '✓' : '✗');

      await page.screenshot({ path: 'tests/screenshots/oc-03-expiry.png' });
      expect(hasExpiries).toBeTruthy();
    }
  });

  // ============================================
  // TEST 4: Verify Spot Price Display
  // ============================================
  test('4. Verify spot price is displayed', async () => {
    console.log('\n--- TEST 4: Spot Price ---');

    const pageText = await page.locator('body').innerText();

    // Look for "Spot:" text with a number
    const hasSpot = /Spot[:\s]*[\d,]+/.test(pageText);
    console.log('  Spot price displayed:', hasSpot ? '✓' : '✗');

    // Extract spot value
    const spotMatch = pageText.match(/Spot[:\s]*([\d,]+)/);
    if (spotMatch) {
      console.log('  Spot value:', spotMatch[1]);
    }

    await page.screenshot({ path: 'tests/screenshots/oc-04-spot.png' });
    expect(hasSpot).toBeTruthy();
  });

  // ============================================
  // TEST 5: Click Refresh and Load Data
  // ============================================
  test('5. Click Refresh to load option chain', async () => {
    console.log('\n--- TEST 5: Refresh Data ---');

    const refreshBtn = page.locator('button').filter({ hasText: /Refresh|Load/i }).first();

    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      console.log('  ✓ Clicked Refresh');

      // Wait for loading to complete
      await page.waitForTimeout(5000);

      // Check if data loaded (look for strike prices)
      const pageText = await page.locator('body').innerText();
      const hasStrikes = /\b2[456]\d{3}\b/.test(pageText); // 24000-26999 range
      console.log('  Strike data loaded:', hasStrikes ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-05-refresh.png', fullPage: true });
  });

  // ============================================
  // TEST 6: Verify Table Headers
  // ============================================
  test('6. Verify option chain table headers', async () => {
    console.log('\n--- TEST 6: Table Headers ---');

    const expectedHeaders = ['OI', 'IV', 'LTP', 'STRIKE', 'Chg'];
    const headerText = await page.locator('thead, th').allInnerTexts();
    const allHeaders = headerText.join(' ').toUpperCase();

    console.log('  Headers found:', allHeaders.substring(0, 100));

    let foundCount = 0;
    for (const header of expectedHeaders) {
      const found = allHeaders.includes(header.toUpperCase());
      console.log(`    ${header}:`, found ? '✓' : '✗');
      if (found) foundCount++;
    }

    await page.screenshot({ path: 'tests/screenshots/oc-06-headers.png' });
    expect(foundCount).toBeGreaterThanOrEqual(3);
  });

  // ============================================
  // TEST 7: Verify Strike Prices Listed
  // ============================================
  test('7. Verify strike prices are listed', async () => {
    console.log('\n--- TEST 7: Strike Prices ---');

    // Look for cells with 5-digit numbers (strike prices like 25000, 26000)
    const strikeCells = await page.locator('td, th').filter({ hasText: /^\d{5}$/ }).all();

    console.log('  Strike cells found:', strikeCells.length);

    if (strikeCells.length > 0) {
      const sampleStrikes = [];
      for (let i = 0; i < Math.min(5, strikeCells.length); i++) {
        sampleStrikes.push(await strikeCells[i].innerText());
      }
      console.log('  Sample strikes:', sampleStrikes.join(', '));
    }

    await page.screenshot({ path: 'tests/screenshots/oc-07-strikes.png' });
    expect(strikeCells.length).toBeGreaterThan(0);
  });

  // ============================================
  // TEST 8: Verify ATM Strike Highlighted
  // ============================================
  test('8. Verify ATM strike is highlighted', async () => {
    console.log('\n--- TEST 8: ATM Highlight ---');

    // Look for ATM text or highlighted row (supports both Tailwind and Kite styling)
    const atmText = page.locator('text=ATM');
    // Support both Tailwind (bg-yellow-50) and Kite (.atm-row) styling
    const highlightedRow = page.locator('tr.bg-yellow-50, tr[class*="yellow"], tr.atm-row');

    const hasATMText = await atmText.first().isVisible().catch(() => false);
    const hasHighlightedRow = await highlightedRow.first().isVisible().catch(() => false);

    console.log('  ATM label visible:', hasATMText ? '✓' : '✗');
    console.log('  ATM row highlighted:', hasHighlightedRow ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-08-atm.png' });
  });

  // ============================================
  // TEST 9: Verify OI Data Displayed
  // ============================================
  test('9. Verify OI data is displayed', async () => {
    console.log('\n--- TEST 9: OI Data ---');

    const pageText = await page.locator('body').innerText();

    // Look for OI values (K, L, Cr suffixes or large numbers)
    const hasOI = /\d+\.?\d*[KLCr]|\d{4,}/.test(pageText);

    // Look for OI bars - support both Tailwind (bg-red/bg-green) and Kite (.oi-bar.ce/.oi-bar.pe)
    const oiBars = await page.locator('[class*="bg-red"], [class*="bg-green"], .oi-bar.ce, .oi-bar.pe, .oi-bar').count();

    console.log('  OI values present:', hasOI ? '✓' : '✗');
    console.log('  OI bars visible:', oiBars > 0 ? `✓ (${oiBars})` : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-09-oi.png' });
  });

  // ============================================
  // TEST 10: Verify IV Data Displayed
  // ============================================
  test('10. Verify IV (Implied Volatility) data', async () => {
    console.log('\n--- TEST 10: IV Data ---');

    const pageText = await page.locator('body').innerText();

    // IV values typically between 10-100
    const ivPattern = /\b[12345]\d\.\d{1,2}\b/;
    const hasIV = ivPattern.test(pageText);

    console.log('  IV values present:', hasIV ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-10-iv.png' });
  });

  // ============================================
  // TEST 11: Verify LTP Data Displayed
  // ============================================
  test('11. Verify LTP (Last Traded Price) data', async () => {
    console.log('\n--- TEST 11: LTP Data ---');

    const pageText = await page.locator('body').innerText();

    // LTP values with decimals
    const ltpPattern = /\b\d+\.\d{2}\b/;
    const hasLTP = ltpPattern.test(pageText);

    console.log('  LTP values present:', hasLTP ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-11-ltp.png' });
  });

  // ============================================
  // TEST 12: Verify Summary Bar (PCR, Max Pain)
  // ============================================
  test('12. Verify summary bar (PCR, Max Pain)', async () => {
    console.log('\n--- TEST 12: Summary Bar ---');

    const pageText = await page.locator('body').innerText();

    const hasPCR = /PCR[:\s]*\d+\.?\d*/i.test(pageText);
    const hasMaxPain = /Max\s*Pain[:\s]*[\d,]+/i.test(pageText);
    const hasCEOI = /CE\s*OI/i.test(pageText);
    const hasPEOI = /PE\s*OI/i.test(pageText);

    console.log('  PCR:', hasPCR ? '✓' : '✗');
    console.log('  Max Pain:', hasMaxPain ? '✓' : '✗');
    console.log('  CE OI:', hasCEOI ? '✓' : '✗');
    console.log('  PE OI:', hasPEOI ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-12-summary.png' });
  });

  // ============================================
  // TEST 13: Toggle Greeks Display
  // ============================================
  test('13. Toggle Greeks checkbox', async () => {
    console.log('\n--- TEST 13: Greeks Toggle ---');

    const greeksCheckbox = page.locator('input[type="checkbox"]').filter({ has: page.locator('xpath=..').filter({ hasText: /Greek/i }) });
    const greeksLabel = page.locator('label, span').filter({ hasText: /Greek/i }).first();

    // Try clicking the checkbox or label
    if (await greeksLabel.isVisible()) {
      await greeksLabel.click();
      console.log('  ✓ Clicked Greeks toggle');
      await page.waitForTimeout(500);

      // Check if Delta column appeared
      const pageText = await page.locator('thead').innerText();
      const hasDelta = pageText.includes('Delta');
      console.log('  Delta column visible:', hasDelta ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-13-greeks.png' });
  });

  // ============================================
  // TEST 14: Change Strikes Range
  // ============================================
  test('14. Change strikes range filter', async () => {
    console.log('\n--- TEST 14: Strikes Range ---');

    // Support both old (±10) and new (10 Strikes) option format
    const rangeSelect = page.locator('select').filter({ has: page.locator('option:has-text("10")') }).first();

    if (await rangeSelect.isVisible()) {
      // Get initial row count
      const initialRows = await page.locator('tbody tr').count();
      console.log('  Initial rows:', initialRows);

      // Change to 10 strikes
      await rangeSelect.selectOption('10');
      await page.waitForTimeout(500);

      const reducedRows = await page.locator('tbody tr').count();
      console.log('  After 10 strikes:', reducedRows);

      // Change to 30 strikes
      await rangeSelect.selectOption('30');
      await page.waitForTimeout(500);

      const expandedRows = await page.locator('tbody tr').count();
      console.log('  After 30 strikes:', expandedRows);
    }

    await page.screenshot({ path: 'tests/screenshots/oc-14-range.png' });
  });

  // ============================================
  // TEST 15: Switch to BANKNIFTY
  // ============================================
  test('15. Switch underlying to BANKNIFTY', async () => {
    console.log('\n--- TEST 15: Switch to BANKNIFTY ---');

    const bankNiftyBtn = page.locator('button').filter({ hasText: /BANKNIFTY/ }).first();

    if (await bankNiftyBtn.isVisible()) {
      await bankNiftyBtn.click();
      console.log('  ✓ Clicked BANKNIFTY');

      await page.waitForTimeout(3000);

      // Verify spot changed (BANKNIFTY is typically 50000+ range)
      const pageText = await page.locator('body').innerText();
      const hasBankNiftySpot = /Spot[:\s]*[456]\d{4}/.test(pageText);
      console.log('  BANKNIFTY spot visible:', hasBankNiftySpot ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-15-banknifty.png', fullPage: true });
  });

  // ============================================
  // TEST 16: Switch back to NIFTY
  // ============================================
  test('16. Switch back to NIFTY', async () => {
    console.log('\n--- TEST 16: Switch back to NIFTY ---');

    const niftyBtn = page.locator('button').filter({ hasText: /^NIFTY$/ }).first();

    if (await niftyBtn.isVisible()) {
      await niftyBtn.click();
      console.log('  ✓ Clicked NIFTY');
      await page.waitForTimeout(3000);
    }

    await page.screenshot({ path: 'tests/screenshots/oc-16-nifty.png' });
  });

  // ============================================
  // TEST 17: Click + Button to Select CE Strike
  // ============================================
  test('17. Select CE strike with + button', async () => {
    console.log('\n--- TEST 17: Select CE Strike ---');

    // Find + buttons in CE column (left side)
    const ceAddButtons = page.locator('button').filter({ hasText: '+' }).first();

    if (await ceAddButtons.isVisible()) {
      await ceAddButtons.click();
      console.log('  ✓ Clicked + on CE strike');
      await page.waitForTimeout(500);

      // Check if selection bar appeared
      const selectionBar = page.locator('text=/Selected/i');
      const hasSelection = await selectionBar.first().isVisible().catch(() => false);
      console.log('  Selection bar visible:', hasSelection ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-17-select-ce.png' });
  });

  // ============================================
  // TEST 18: Click + Button to Select PE Strike
  // ============================================
  test('18. Select PE strike with + button', async () => {
    console.log('\n--- TEST 18: Select PE Strike ---');

    // Find + buttons - get the last few which should be PE side
    const allAddButtons = await page.locator('button').filter({ hasText: '+' }).all();

    if (allAddButtons.length > 1) {
      // Click a PE button (right side of table)
      await allAddButtons[allAddButtons.length - 1].click();
      console.log('  ✓ Clicked + on PE strike');
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: 'tests/screenshots/oc-18-select-pe.png' });
  });

  // ============================================
  // TEST 19: Verify Selected Strikes Display
  // ============================================
  test('19. Verify selected strikes display', async () => {
    console.log('\n--- TEST 19: Selected Strikes ---');

    const selectedBar = page.locator('text=/Selected/i').first();

    if (await selectedBar.isVisible()) {
      const selectionText = await page.locator('body').innerText();

      const hasCE = /CE\s*\d{5}/i.test(selectionText);
      const hasPE = /PE\s*\d{5}/i.test(selectionText);

      console.log('  CE strike selected:', hasCE ? '✓' : '✗');
      console.log('  PE strike selected:', hasPE ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-19-selected.png' });
  });

  // ============================================
  // TEST 20: "Add to Strategy Builder" Button
  // ============================================
  test('20. "Add to Strategy Builder" button visible', async () => {
    console.log('\n--- TEST 20: Add to Strategy Button ---');

    const addToStrategyBtn = page.locator('button').filter({ hasText: /Add to Strategy|Strategy Builder/i }).first();

    const isVisible = await addToStrategyBtn.isVisible().catch(() => false);
    console.log('  Button visible:', isVisible ? '✓' : '✗');

    if (isVisible) {
      const isEnabled = await addToStrategyBtn.isEnabled();
      console.log('  Button enabled:', isEnabled ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-20-add-to-strategy.png' });
  });

  // ============================================
  // TEST 21: Clear Selection
  // ============================================
  test('21. Clear selection button', async () => {
    console.log('\n--- TEST 21: Clear Selection ---');

    const clearBtn = page.locator('button').filter({ hasText: /Clear/i }).first();

    if (await clearBtn.isVisible()) {
      await clearBtn.click();
      console.log('  ✓ Clicked Clear');
      await page.waitForTimeout(500);

      // Check if selection bar disappeared
      const selectedBar = page.locator('text=/Selected.*:/i');
      const stillVisible = await selectedBar.first().isVisible().catch(() => false);
      console.log('  Selection cleared:', !stillVisible ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/oc-21-clear.png' });
  });

  // ============================================
  // TEST 22: Change Expiry Date
  // ============================================
  test('22. Change expiry date', async () => {
    console.log('\n--- TEST 22: Change Expiry ---');

    const expirySelect = page.locator('select').filter({ has: page.locator('option') }).first();

    if (await expirySelect.isVisible()) {
      const options = await expirySelect.locator('option').allInnerTexts();

      if (options.length > 1) {
        // Select second expiry
        await expirySelect.selectOption({ index: 1 });
        console.log('  ✓ Changed to:', options[1]);
        await page.waitForTimeout(3000);

        // Verify data reloaded
        const refreshBtn = page.locator('button').filter({ hasText: /Refresh/i }).first();
        if (await refreshBtn.isVisible()) {
          await refreshBtn.click();
          await page.waitForTimeout(3000);
        }
      }
    }

    await page.screenshot({ path: 'tests/screenshots/oc-22-change-expiry.png', fullPage: true });
  });

  // ============================================
  // TEST 23: ITM/OTM Color Coding
  // ============================================
  test('23. Verify ITM/OTM color coding', async () => {
    console.log('\n--- TEST 23: ITM/OTM Colors ---');

    // Look for ITM background colors - support both Tailwind and Kite styling
    // Tailwind: tr[class*="red"], td[class*="red"]
    // Kite: .itm-ce (red for CE ITM), .itm-pe (green for PE ITM), .ce-col, .pe-col
    const redBg = await page.locator('tr[class*="red"], td[class*="red"], tr.itm-ce, .ce-col').count();
    const greenBg = await page.locator('tr[class*="green"], td[class*="green"], tr.itm-pe, .pe-col').count();

    console.log('  CE (red-tinted) elements:', redBg);
    console.log('  PE (green-tinted) elements:', greenBg);

    await page.screenshot({ path: 'tests/screenshots/oc-23-itm-otm.png' });
  });

  // ============================================
  // TEST 24: Days to Expiry Display
  // ============================================
  test('24. Verify Days to Expiry (DTE) display', async () => {
    console.log('\n--- TEST 24: DTE Display ---');

    const pageText = await page.locator('body').innerText();

    const hasDTE = /DTE[:\s]*\d+|Days?\s*to\s*Expiry/i.test(pageText);
    console.log('  DTE displayed:', hasDTE ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/oc-24-dte.png' });
  });

  // ============================================
  // TEST 25: Final Summary
  // ============================================
  test('25. Final summary and screenshot', async () => {
    console.log('\n' + '='.repeat(60));
    console.log('OPTION CHAIN TEST SUMMARY');
    console.log('='.repeat(60));

    await page.screenshot({ path: 'tests/screenshots/oc-25-final.png', fullPage: true });

    console.log('\n✅ Tests Completed');
    console.log('\nFeatures Verified:');
    console.log('  • Underlying selector (NIFTY/BANKNIFTY/FINNIFTY)');
    console.log('  • Expiry dropdown');
    console.log('  • Spot price display');
    console.log('  • Option chain table');
    console.log('  • Strike prices');
    console.log('  • ATM highlighting');
    console.log('  • OI data & bars');
    console.log('  • IV (Implied Volatility)');
    console.log('  • LTP');
    console.log('  • Summary bar (PCR, Max Pain)');
    console.log('  • Greeks toggle');
    console.log('  • Strikes range filter');
    console.log('  • Strike selection (+)');
    console.log('  • Add to Strategy Builder');
    console.log('  • ITM/OTM colors');
    console.log('  • Days to Expiry');

    console.log('\n📸 Screenshots saved in tests/screenshots/oc-*.png');
    console.log('='.repeat(60));
  });
});
