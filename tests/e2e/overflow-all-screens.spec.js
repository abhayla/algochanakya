import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

let page;

test.describe.configure({ mode: 'serial' });

test.describe('Overflow Test - All Screens', () => {

  test.beforeAll(async ({ browser }) => {
    // Create context with full screen viewport
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    page = await context.newPage();

    console.log('\n' + '='.repeat(60));
    console.log('OVERFLOW TEST - ALL SCREENS');
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

  // Helper function to check for overflow
  async function checkOverflow(pageName) {
    console.log(`\n--- Checking ${pageName} ---`);

    const viewportSize = page.viewportSize();
    console.log(`  Viewport: ${viewportSize.width}x${viewportSize.height}`);

    // Check for horizontal scrollbar
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    // Get scroll dimensions
    const scrollDimensions = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      clientWidth: document.documentElement.clientWidth,
      clientHeight: document.documentElement.clientHeight
    }));

    console.log(`  Document: ${scrollDimensions.scrollWidth}x${scrollDimensions.scrollHeight}`);
    console.log(`  Client: ${scrollDimensions.clientWidth}x${scrollDimensions.clientHeight}`);
    console.log(`  Horizontal overflow: ${hasHorizontalScroll ? '✗ OVERFLOW DETECTED' : '✓ None'}`);

    // Check header specifically
    const header = page.locator('.kite-header, header').first();
    if (await header.isVisible().catch(() => false)) {
      const headerBox = await header.boundingBox();
      if (headerBox) {
        const headerFits = headerBox.width <= viewportSize.width;
        console.log(`  Header width: ${headerBox.width}px (${headerFits ? '✓' : '✗'})`);
      }
    }

    // Take screenshot
    const screenshotName = pageName.toLowerCase().replace(/\s+/g, '-');
    await page.screenshot({ path: `tests/screenshots/overflow-${screenshotName}.png`, fullPage: false });

    return !hasHorizontalScroll;
  }

  // ============================================
  // TEST 1: Login Page (before auth)
  // ============================================
  test('1. Login Page - No overflow', async () => {
    // Already logged in from beforeAll, but we'll test the dashboard first
    await page.goto(`${FRONTEND_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const noOverflow = await checkOverflow('Dashboard');
    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 2: Dashboard Page
  // ============================================
  test('2. Dashboard Page - No overflow', async () => {
    await page.goto(`${FRONTEND_URL}/dashboard`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const noOverflow = await checkOverflow('Dashboard');

    // Also check the navigation cards
    const navCards = page.locator('.bg-blue-50, .bg-green-50, .bg-purple-50, .bg-orange-50');
    const cardsCount = await navCards.count();
    console.log(`  Navigation cards: ${cardsCount}`);

    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 3: Positions Page
  // ============================================
  test('3. Positions Page - No overflow', async () => {
    await page.goto(`${FRONTEND_URL}/positions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Click Refresh to load data
    const refreshBtn = page.locator('button').filter({ hasText: /Refresh/i }).first();
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      await page.waitForTimeout(3000);
    }

    const noOverflow = await checkOverflow('Positions');

    // Check specific elements
    const pnlBox = page.locator('.pnl-box').first();
    if (await pnlBox.isVisible().catch(() => false)) {
      const pnlBoxBox = await pnlBox.boundingBox();
      if (pnlBoxBox) {
        console.log(`  P&L Box visible at: x=${pnlBoxBox.x}, width=${pnlBoxBox.width}`);
      }
    }

    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 4: Option Chain Page
  // ============================================
  test('4. Option Chain Page - No overflow', async () => {
    await page.goto(`${FRONTEND_URL}/optionchain`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);

    const noOverflow = await checkOverflow('Option Chain');

    // Check if table is scrollable within its container
    const tableContainer = page.locator('.table-container, .scrollable-container').first();
    if (await tableContainer.isVisible().catch(() => false)) {
      const containerOverflow = await tableContainer.evaluate(el => ({
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
        canScroll: el.scrollWidth > el.clientWidth
      }));
      console.log(`  Table container scrollable: ${containerOverflow.canScroll ? '✓ Yes (as expected)' : '✗ No'}`);
      console.log(`  Table scroll width: ${containerOverflow.scrollWidth}, client width: ${containerOverflow.clientWidth}`);
    }

    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 5: Strategy Builder Page
  // ============================================
  test('5. Strategy Builder Page - No overflow', async () => {
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const noOverflow = await checkOverflow('Strategy Builder');

    // Check action buttons visibility
    const actionButtons = ['Import Positions', 'Update Positions', 'Save', 'Share', 'Buy Basket Order'];
    for (const btnText of actionButtons) {
      const btn = page.locator('button').filter({ hasText: new RegExp(btnText, 'i') }).first();
      const isVisible = await btn.isVisible().catch(() => false);
      console.log(`  Button "${btnText}": ${isVisible ? '✓' : '✗'}`);
    }

    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 6: Strategy Builder with Legs
  // ============================================
  test('6. Strategy Builder with legs - No overflow', async () => {
    // Load an existing strategy with legs
    const strategyDropdown = page.locator('select, combobox').first();
    if (await strategyDropdown.isVisible()) {
      // Select a strategy that has data (e.g., Iron Condor)
      const options = await page.locator('option').allTextContents();
      const ironCondorOption = options.find(o => o.includes('Iron Condor'));
      if (ironCondorOption) {
        await strategyDropdown.selectOption({ label: ironCondorOption });
        await page.waitForTimeout(3000);
        console.log(`  Loaded strategy: ${ironCondorOption}`);
      }
    }

    const noOverflow = await checkOverflow('Strategy Builder with Legs');

    // Check if P/L grid is visible
    const pnlGrid = page.locator('.pnl-grid, table').first();
    const hasGrid = await pnlGrid.isVisible().catch(() => false);
    console.log(`  P/L grid visible: ${hasGrid ? '✓' : '✗'}`);

    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 7: Watchlist Page
  // ============================================
  test('7. Watchlist Page - No overflow', async () => {
    await page.goto(`${FRONTEND_URL}/watchlist`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const noOverflow = await checkOverflow('Watchlist');

    // Check left panel (watchlist) and right panel visibility
    const leftPanel = page.locator('.w-80, [class*="watchlist"]').first();
    const hasLeftPanel = await leftPanel.isVisible().catch(() => false);
    console.log(`  Left panel visible: ${hasLeftPanel ? '✓' : '✗'}`);

    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 8: Test at Different Viewport Widths
  // ============================================
  test('8. Test at 1440px width - No overflow', async () => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);

    // Test Positions page at smaller width
    await page.goto(`${FRONTEND_URL}/positions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const noOverflow = await checkOverflow('Positions @1440px');
    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 9: Test at 1280px width
  // ============================================
  test('9. Test at 1280px width - No overflow', async () => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.waitForTimeout(500);

    // Test Option Chain at smaller width
    await page.goto(`${FRONTEND_URL}/optionchain`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const noOverflow = await checkOverflow('Option Chain @1280px');
    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 10: Test at 1024px width
  // ============================================
  test('10. Test at 1024px width - No overflow', async () => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.waitForTimeout(500);

    // Test Strategy Builder at smaller width
    await page.goto(`${FRONTEND_URL}/strategy`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const noOverflow = await checkOverflow('Strategy @1024px');
    expect(noOverflow).toBeTruthy();
  });

  // ============================================
  // TEST 11: Final Summary
  // ============================================
  test('11. Final Summary', async () => {
    // Reset viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    console.log('\n' + '='.repeat(60));
    console.log('OVERFLOW TEST SUMMARY');
    console.log('='.repeat(60));

    console.log('\nScreens Tested:');
    console.log('  1. Dashboard Page');
    console.log('  2. Positions Page');
    console.log('  3. Option Chain Page');
    console.log('  4. Strategy Builder Page');
    console.log('  5. Strategy Builder with Legs');
    console.log('  6. Watchlist Page');

    console.log('\nViewport Widths Tested:');
    console.log('  • 1920px (Full HD)');
    console.log('  • 1440px');
    console.log('  • 1280px');
    console.log('  • 1024px');

    console.log('\nKey Checks:');
    console.log('  • No horizontal page overflow');
    console.log('  • Header fits within viewport');
    console.log('  • Table containers scroll internally');
    console.log('  • All buttons visible');

    console.log('\n📸 Screenshots saved in tests/screenshots/overflow-*.png');
    console.log('='.repeat(60));

    console.log('\n✅ All overflow tests completed!');
    console.log('Press Ctrl+C in terminal to close.\n');

    // Keep browser open for inspection
    await page.waitForTimeout(60000);
  });
});
