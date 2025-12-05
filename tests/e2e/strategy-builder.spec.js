import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8000';

test.describe('Strategy Builder Tests', () => {
  let authToken = null;

  // Set faster timeout for individual tests (30 seconds)
  test.describe.configure({ timeout: 30000 });

  // Login once before all tests
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();

    console.log('\n' + '='.repeat(60));
    console.log('ZERODHA LOGIN');
    console.log('='.repeat(60));

    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('domcontentloaded');

    const zerodhaButton = page.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaButton.click();

    await page.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });

    console.log('\n*** MANUAL LOGIN REQUIRED ***');
    console.log('Complete Zerodha login in the browser...\n');

    await page.waitForURL(/localhost:5173/, { timeout: 120000 });
    await page.waitForTimeout(3000);

    authToken = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log('✓ Login successful, token obtained\n');

    await page.close();
  });

  test('1. Navigate to Strategy Builder page', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);

    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'tests/screenshots/sb-01-page-load.png', fullPage: true });

    // Verify page loaded
    const pageContent = await page.content();
    const hasStrategyContent = pageContent.toLowerCase().includes('strategy') ||
                               pageContent.toLowerCase().includes('nifty') ||
                               pageContent.toLowerCase().includes('underlying');

    console.log('Strategy Builder page loaded:', hasStrategyContent ? '✓' : '✗');
    expect(hasStrategyContent).toBeTruthy();
  });

  test('2. Verify underlying selector (NIFTY, BANKNIFTY, FINNIFTY)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Check for underlying buttons/tabs
    const niftyBtn = page.locator('button, [role="tab"]').filter({ hasText: /^NIFTY$/i }).first();
    const bankNiftyBtn = page.locator('button, [role="tab"]').filter({ hasText: /BANKNIFTY/i }).first();
    const finNiftyBtn = page.locator('button, [role="tab"]').filter({ hasText: /FINNIFTY/i }).first();

    const hasNifty = await niftyBtn.isVisible().catch(() => false);
    const hasBankNifty = await bankNiftyBtn.isVisible().catch(() => false);
    const hasFinNifty = await finNiftyBtn.isVisible().catch(() => false);

    console.log('NIFTY selector:', hasNifty ? '✓' : '✗');
    console.log('BANKNIFTY selector:', hasBankNifty ? '✓' : '✗');
    console.log('FINNIFTY selector:', hasFinNifty ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/sb-02-underlying-selector.png' });
  });

  test('3. Add first leg to strategy', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Click "Add row" button
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();

    if (await addButton.isVisible()) {
      await addButton.click();
      console.log('✓ Clicked Add row button');
      await page.waitForTimeout(1000);
    } else {
      console.log('Add button not found, checking if row already exists');
    }

    await page.screenshot({ path: 'tests/screenshots/sb-03-add-leg.png', fullPage: true });

    // Check if a leg row appeared
    const legRow = page.locator('tr, [class*="leg"], [class*="row"]').filter({
      has: page.locator('select, [class*="dropdown"]')
    });
    const legCount = await legRow.count();
    console.log('Leg rows found:', legCount);
  });

  test('4. Configure leg - Select Expiry', async ({ page }) => {
    // Set shorter timeout for this test
    test.setTimeout(60000);

    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');

    // Wait for expiries to load (API call happens on mount)
    await page.waitForTimeout(3000);

    // Add a leg first
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      console.log('✓ Clicked Add Row button');
    }

    // Wait for leg row to appear in tbody (not the empty state row)
    const legRow = page.locator('tbody tr').filter({ has: page.locator('td select') }).first();
    await legRow.waitFor({ state: 'visible', timeout: 5000 });
    console.log('✓ Leg row appeared');

    // Find expiry dropdown - it's the first select in the leg row
    const expiryDropdown = legRow.locator('select').first();
    await expiryDropdown.waitFor({ state: 'visible', timeout: 5000 });

    // Wait for options to be loaded (more than just "Select")
    await page.waitForFunction(
      (sel) => {
        const select = document.querySelector(sel);
        return select && select.options.length > 1;
      },
      'tbody tr td select',
      { timeout: 10000 }
    );

    // Get options
    const options = await expiryDropdown.locator('option').allInnerTexts();
    console.log('Expiry options:', options.slice(0, 5));

    // Select first real expiry (index 1, skipping "Select")
    if (options.length > 1) {
      await expiryDropdown.selectOption({ index: 1 });
      console.log('✓ Selected expiry:', options[1]);

      // Verify selection worked
      const selectedValue = await expiryDropdown.inputValue();
      console.log('Selected value:', selectedValue);
    } else {
      console.log('✗ No expiry options available');
    }

    await page.screenshot({ path: 'tests/screenshots/sb-04-select-expiry.png' });
    console.log('Test 4 completed');
  });

  test('5. Configure leg - Select Contract Type (CE/PE)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Add leg
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await page.waitForTimeout(1000);
    }

    // Find contract type dropdown in leg row (has CE/PE but NOT "All")
    const legRow = page.locator('tbody tr').filter({ has: page.locator('select') }).first();
    const contractDropdown = legRow.locator('select').filter({
      has: page.locator('option:has-text("PE")')
    }).filter({
      hasNot: page.locator('option:has-text("All")')
    }).first();

    if (await contractDropdown.isVisible()) {
      // Get options WITHOUT clicking (click opens native dropdown and gets stuck on Windows)
      const options = await contractDropdown.locator('option').allInnerTexts();
      console.log('Contract type options:', options);

      // Select PE - selectOption doesn't require prior click
      await contractDropdown.selectOption('PE');
      console.log('✓ Selected PE');
    }

    await page.screenshot({ path: 'tests/screenshots/sb-05-select-contract.png' });
  });

  test('6. Configure leg - Select Transaction Type (BUY/SELL)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Add leg
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await page.waitForTimeout(1000);
    }

    // Find transaction type dropdown in leg row (has BUY/SELL options)
    const legRow = page.locator('tbody tr').filter({ has: page.locator('select') }).first();
    const txnDropdown = legRow.locator('select').filter({
      has: page.locator('option:has-text("SELL")')
    }).filter({
      has: page.locator('option:has-text("BUY")')
    }).first();

    if (await txnDropdown.isVisible()) {
      const options = await txnDropdown.locator('option').allInnerTexts();
      console.log('Transaction type options:', options);

      await txnDropdown.selectOption('SELL');
      console.log('✓ Selected SELL');
    }

    await page.screenshot({ path: 'tests/screenshots/sb-06-select-txn.png' });
  });

  test('7. Configure leg - Select Strike Price', async ({ page }) => {
    test.setTimeout(60000);

    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);

    // Add leg
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      console.log('✓ Clicked Add Row button');
    }

    // Wait for leg row to appear
    const legRow = page.locator('tbody tr').filter({ has: page.locator('td select') }).first();
    await legRow.waitFor({ state: 'visible', timeout: 5000 });
    console.log('✓ Leg row appeared');

    // First select expiry (required to load strikes)
    const expiryDropdown = legRow.locator('select').first();
    await expiryDropdown.waitFor({ state: 'visible', timeout: 5000 });

    // Wait for expiry options to load
    await page.waitForFunction(
      (sel) => {
        const select = document.querySelector(sel);
        return select && select.options.length > 1;
      },
      'tbody tr td select',
      { timeout: 10000 }
    );

    const expiryOptions = await expiryDropdown.locator('option').allInnerTexts();
    console.log('Expiry options:', expiryOptions.slice(0, 5));

    if (expiryOptions.length > 1) {
      await expiryDropdown.selectOption({ index: 1 });
      console.log('✓ Selected expiry:', expiryOptions[1]);
    }

    // Wait for strikes API call to complete
    await page.waitForTimeout(3000);

    // Strike dropdown is the 4th select (index 3): expiry(0), contract(1), transaction(2), strike(3)
    const strikeDropdown = legRow.locator('select').nth(3);
    await strikeDropdown.waitFor({ state: 'visible', timeout: 5000 });

    // Wait for strike options to load
    await page.waitForFunction(
      () => {
        const selects = document.querySelectorAll('tbody tr td select');
        if (selects.length >= 4) {
          const strikeSelect = selects[3];
          return strikeSelect && strikeSelect.options.length > 1;
        }
        return false;
      },
      { timeout: 10000 }
    );

    const strikeOptions = await strikeDropdown.locator('option').allInnerTexts();
    console.log('Strike options (first 10):', strikeOptions.slice(0, 10));

    if (strikeOptions.length > 1) {
      // Find numeric strikes (5 digits like 24000, 24050)
      const validStrikes = strikeOptions.filter(o => /^\d{5}$/.test(o.trim()));
      console.log('Valid numeric strikes:', validStrikes.slice(0, 10));

      if (validStrikes.length > 0) {
        const midIndex = Math.floor(validStrikes.length / 2);
        await strikeDropdown.selectOption(validStrikes[midIndex]);
        console.log('✓ Selected strike:', validStrikes[midIndex]);

        const selectedValue = await strikeDropdown.inputValue();
        console.log('Selected strike value:', selectedValue);
      } else if (strikeOptions.length > 1) {
        await strikeDropdown.selectOption({ index: 1 });
        console.log('✓ Selected first strike option');
      }
    } else {
      console.log('✗ Strike options not loaded');
    }

    await page.screenshot({ path: 'tests/screenshots/sb-07-select-strike.png' });
  });

  test('8. Enter Entry Price', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Add leg
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      await page.waitForTimeout(1000);
    }

    // Find entry price input
    const entryInput = page.locator('input[type="number"], input[placeholder*="entry" i], input[placeholder*="price" i]').first();

    if (await entryInput.isVisible()) {
      await entryInput.fill('70.25');
      console.log('✓ Entered entry price: 70.25');
    }

    await page.screenshot({ path: 'tests/screenshots/sb-08-entry-price.png' });
  });

  test('9. Click ReCalculate and verify P/L grid', async ({ page }) => {
    test.setTimeout(90000);

    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);

    // Add and configure a complete leg
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      console.log('✓ Clicked Add Row button');
    }

    // Wait for leg row to appear
    const legRow = page.locator('tbody tr').filter({ has: page.locator('td select') }).first();
    await legRow.waitFor({ state: 'visible', timeout: 5000 });
    console.log('✓ Leg row appeared');

    // 1. Select expiry (first dropdown)
    const expiryDropdown = legRow.locator('select').first();
    await expiryDropdown.waitFor({ state: 'visible', timeout: 5000 });

    // Wait for expiry options to load
    await page.waitForFunction(
      (sel) => {
        const select = document.querySelector(sel);
        return select && select.options.length > 1;
      },
      'tbody tr td select',
      { timeout: 10000 }
    );

    const expiryOptions = await expiryDropdown.locator('option').allInnerTexts();
    console.log('Expiry options:', expiryOptions.slice(0, 3));

    await expiryDropdown.selectOption({ index: 1 });
    console.log('✓ Selected expiry:', expiryOptions[1]);

    // Wait for strikes API call to complete
    await page.waitForTimeout(3000);

    // 2. Select strike (4th dropdown, index 3)
    const strikeDropdown = legRow.locator('select').nth(3);
    await strikeDropdown.waitFor({ state: 'visible', timeout: 5000 });

    // Wait for strike options to load
    await page.waitForFunction(
      () => {
        const selects = document.querySelectorAll('tbody tr td select');
        if (selects.length >= 4) {
          const strikeSelect = selects[3];
          return strikeSelect && strikeSelect.options.length > 1;
        }
        return false;
      },
      { timeout: 10000 }
    );

    const strikeOptions = await strikeDropdown.locator('option').allInnerTexts();
    console.log('Strike options count:', strikeOptions.length);

    if (strikeOptions.length > 1) {
      // Select a middle strike
      const midIndex = Math.floor(strikeOptions.length / 2);
      await strikeDropdown.selectOption({ index: midIndex });
      console.log('✓ Selected strike at index:', midIndex, '- value:', strikeOptions[midIndex]);
    }

    // 3. Enter entry price
    const entryInput = legRow.locator('input[type="number"]').first();
    if (await entryInput.isVisible()) {
      await entryInput.fill('70');
      console.log('✓ Entered entry price: 70');
    }

    await page.waitForTimeout(500);

    // 4. Click ReCalculate
    const recalcButton = page.locator('button').filter({ hasText: /recalculate|calculate/i }).first();
    await recalcButton.waitFor({ state: 'visible', timeout: 5000 });
    await recalcButton.click();
    console.log('✓ Clicked ReCalculate');

    // Wait for P/L calculation
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'tests/screenshots/sb-09-pnl-grid.png', fullPage: true });

    // Check for P/L columns (spot prices like 24000, 25000, 26000)
    const pageContent = await page.content();
    const hasPnLColumns = /2[4-6]\d{3}/.test(pageContent);
    console.log('P/L columns visible:', hasPnLColumns ? '✓' : '✗');

    // Check for Max Profit/Loss stats
    const hasMaxProfit = /max.*profit/i.test(pageContent);
    const hasMaxLoss = /max.*loss/i.test(pageContent);
    console.log('Max Profit stat:', hasMaxProfit ? '✓' : '✗');
    console.log('Max Loss stat:', hasMaxLoss ? '✓' : '✗');
  });

  test('10. Toggle P/L Mode (At Expiry / Current)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Find mode toggle
    const modeToggle = page.locator('button, select').filter({ hasText: /expiry|current|mode/i }).first();

    if (await modeToggle.isVisible()) {
      const initialText = await modeToggle.innerText();
      console.log('Initial mode:', initialText);

      await modeToggle.click();
      await page.waitForTimeout(1000);

      const newText = await modeToggle.innerText().catch(() => '');
      console.log('After toggle:', newText);
    }

    await page.screenshot({ path: 'tests/screenshots/sb-10-mode-toggle.png' });
  });

  test('11. Add second leg (Iron Condor setup)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Add two legs
    const addButton = page.locator('button').filter({ hasText: /add.*row|add.*leg|\+/i }).first();

    if (await addButton.isVisible()) {
      await addButton.click();
      await page.waitForTimeout(500);
      await addButton.click();
      await page.waitForTimeout(500);
      console.log('✓ Added 2 legs');
    }

    // Count leg rows
    const legRows = page.locator('tr, [class*="leg-row"]').filter({ has: page.locator('select') });
    const count = await legRows.count();
    console.log('Total legs:', count);

    await page.screenshot({ path: 'tests/screenshots/sb-11-multiple-legs.png', fullPage: true });
  });

  test('12. Verify color coding (red=loss, green=profit)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Check for red/green colored cells
    const redCells = page.locator('[class*="red"], [class*="loss"], [style*="red"]');
    const greenCells = page.locator('[class*="green"], [class*="profit"], [style*="green"]');

    const redCount = await redCells.count();
    const greenCount = await greenCells.count();

    console.log('Red (loss) cells:', redCount);
    console.log('Green (profit) cells:', greenCount);

    await page.screenshot({ path: 'tests/screenshots/sb-12-color-coding.png' });
  });

  test('13. Test Save Strategy button', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Click Save button
    const saveButton = page.locator('button').filter({ hasText: /^save$/i }).first();

    if (await saveButton.isVisible()) {
      const isDisabled = await saveButton.isDisabled();
      console.log('Save button visible:', '✓');
      console.log('Save button disabled:', isDisabled ? 'Yes (no legs configured)' : 'No');

      if (!isDisabled) {
        await saveButton.click();
        await page.waitForTimeout(1000);
        console.log('✓ Clicked Save button');

        // Check for save modal/dialog
        const modal = page.locator('[role="dialog"], .modal, [class*="modal"]');
        const modalVisible = await modal.first().isVisible().catch(() => false);
        console.log('Save modal appeared:', modalVisible ? '✓' : '✗');
      }

      await page.screenshot({ path: 'tests/screenshots/sb-13-save-modal.png' });
    }
  });

  test('14. Test Share Strategy functionality', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Click Share button
    const shareButton = page.locator('button').filter({ hasText: /share/i }).first();

    if (await shareButton.isVisible()) {
      await shareButton.click();
      await page.waitForTimeout(1000);
      console.log('✓ Clicked Share button');

      await page.screenshot({ path: 'tests/screenshots/sb-14-share.png' });
    }
  });

  test('15. Test Buy Basket Order button (UI only)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Find Buy Basket Order button
    const buyButton = page.locator('button').filter({ hasText: /buy.*basket|basket.*order|execute/i }).first();

    if (await buyButton.isVisible()) {
      console.log('✓ Buy Basket Order button found');

      // DON'T actually click it - just verify it exists
      // Clicking would attempt real orders

      await page.screenshot({ path: 'tests/screenshots/sb-15-buy-basket.png' });
    } else {
      console.log('Buy Basket Order button not found');
    }
  });

  test('16. Verify summary stats (Max Profit, Max Loss, Breakeven)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Look for summary stats
    const pageText = await page.locator('body').innerText();

    const hasMaxProfit = /max.*profit|maximum.*profit/i.test(pageText);
    const hasMaxLoss = /max.*loss|maximum.*loss/i.test(pageText);
    const hasBreakeven = /breakeven|break.*even/i.test(pageText);

    console.log('Max Profit display:', hasMaxProfit ? '✓' : '✗');
    console.log('Max Loss display:', hasMaxLoss ? '✓' : '✗');
    console.log('Breakeven display:', hasBreakeven ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/sb-16-summary-stats.png' });
  });

  test('17. Verify footer (Last Updated, Last Price)', async ({ page }) => {
    await page.goto(FRONTEND_URL);
    await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    const pageText = await page.locator('body').innerText();

    const hasLastUpdated = /last.*updated|updated.*at/i.test(pageText);
    const hasLastPrice = /last.*price|spot.*price|current.*price/i.test(pageText);

    console.log('Last Updated display:', hasLastUpdated ? '✓' : '✗');
    console.log('Last Price display:', hasLastPrice ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/sb-17-footer.png' });
  });

  test('18. API Test - Get Expiries', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/options/expiries?underlying=NIFTY`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    console.log('GET /api/options/expiries status:', response.status());

    if (response.ok()) {
      const data = await response.json();
      // API returns {expiries: [...]} object
      const expiries = Array.isArray(data) ? data : (data.expiries || []);
      console.log('Expiries count:', expiries.length);
      console.log('First 5 expiries:', expiries.slice(0, 5));
    }

    expect(response.status()).toBeLessThan(500);
  });

  test('19. API Test - Get Strikes', async ({ request }) => {
    // First get an expiry
    const expiriesRes = await request.get(`${API_BASE}/api/options/expiries?underlying=NIFTY`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    let expiry = '2025-12-09';
    if (expiriesRes.ok()) {
      const expiriesData = await expiriesRes.json();
      // API returns {expiries: [...]} object
      const expiries = Array.isArray(expiriesData) ? expiriesData : (expiriesData.expiries || []);
      if (expiries.length > 0) expiry = expiries[0];
    }

    const response = await request.get(`${API_BASE}/api/options/strikes?underlying=NIFTY&expiry=${expiry}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    console.log('GET /api/options/strikes status:', response.status());

    if (response.ok()) {
      const data = await response.json();
      // API returns {strikes: [...]} object
      const strikes = Array.isArray(data) ? data : (data.strikes || []);
      console.log('Strikes count:', strikes.length);
      console.log('Sample strikes:', strikes.slice(0, 10));
    }

    expect(response.status()).toBeLessThan(500);
  });

  test('20. API Test - Calculate P/L', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategies/calculate`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      data: {
        underlying: 'NIFTY',
        legs: [
          {
            strike: 26000,
            contract_type: 'PE',
            transaction_type: 'SELL',
            lots: 1,
            lot_size: 75,
            entry_price: 70,
            expiry_date: '2025-12-09'
          }
        ],
        mode: 'expiry'
      }
    });

    console.log('POST /api/strategies/calculate status:', response.status());

    if (response.ok()) {
      const data = await response.json();
      console.log('Spot prices count:', data.spot_prices?.length);
      console.log('Max Profit:', data.max_profit);
      console.log('Max Loss:', data.max_loss);
      console.log('Breakeven:', data.breakeven);
    } else {
      console.log('Error:', await response.text());
    }

    expect(response.status()).toBeLessThan(500);
  });

});
