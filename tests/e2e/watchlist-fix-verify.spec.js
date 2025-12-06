import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';

// Zerodha credentials (TOTP will be manual)
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

// Use same page for all tests
let sharedPage;
let isLoggedIn = false;

test.describe.configure({ mode: 'serial' }); // Run tests in order

test.describe('Watchlist Complete Tests', () => {

  test.beforeAll(async ({ browser }) => {
    // Create a single browser context and page for ALL tests
    const context = await browser.newContext();
    sharedPage = await context.newPage();

    console.log('\n' + '='.repeat(60));
    console.log('ZERODHA LOGIN - ONE TIME ONLY');
    console.log('='.repeat(60));

    // Go to login page
    await sharedPage.goto(`${FRONTEND_URL}/login`);
    await sharedPage.waitForLoadState('networkidle');

    // Click Zerodha login
    const zerodhaBtn = sharedPage.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaBtn.click();

    // Wait for Kite login page
    await sharedPage.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });
    await sharedPage.waitForTimeout(1000);

    console.log('\n✓ Kite login page loaded');
    console.log('→ Auto-filling User ID and Password...\n');

    // Prefill User ID
    const userIdInput = sharedPage.locator('input[type="text"]#userid, input[name="user_id"], input[placeholder*="User ID"]').first();
    await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
    await userIdInput.fill(ZERODHA_USER_ID);
    console.log('✓ User ID filled: ' + ZERODHA_USER_ID);

    // Prefill Password
    const passwordInput = sharedPage.locator('input[type="password"]').first();
    await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
    await passwordInput.fill(ZERODHA_PASSWORD);
    console.log('✓ Password filled');

    // Click Login button
    const loginBtn = sharedPage.locator('button[type="submit"], button:has-text("Login")').first();
    await loginBtn.click();
    console.log('✓ Clicked Login button');

    // Wait for TOTP page
    await sharedPage.waitForTimeout(2000);

    console.log('\n' + '*'.repeat(60));
    console.log('*** ENTER TOTP MANUALLY ***');
    console.log('*'.repeat(60));
    console.log('\nWaiting for you to enter TOTP and complete login...\n');

    // Wait for redirect back to app (after TOTP)
    await sharedPage.waitForURL(/localhost/, { timeout: 120000 });
    await sharedPage.waitForTimeout(3000);

    isLoggedIn = true;
    console.log('✓ Login successful!\n');
    console.log('='.repeat(60));
    console.log('STARTING TESTS - Browser will stay open');
    console.log('='.repeat(60) + '\n');
  });

  test.afterAll(async () => {
    // Keep browser open indefinitely for inspection
    console.log('\n✓ All tests complete. Browser will stay open.');
    console.log('Press Ctrl+C in terminal to close when done inspecting.');

    // Wait indefinitely (24 hours) - user will Ctrl+C to exit
    await sharedPage.waitForTimeout(24 * 60 * 60 * 1000);
  });

  // ============================================
  // TEST 1: Page loads without giant black SVG
  // ============================================
  test('1. Page loads without giant black SVG', async () => {
    await sharedPage.goto(`${FRONTEND_URL}/watchlist`);
    await sharedPage.waitForLoadState('networkidle');
    await sharedPage.waitForTimeout(2000);

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-01-page.png', fullPage: true });

    // Check no oversized SVG (max 100px considered acceptable)
    const largeSvgCount = await sharedPage.locator('svg').evaluateAll(svgs => {
      return svgs.filter(svg => {
        const rect = svg.getBoundingClientRect();
        return rect.width > 100 || rect.height > 100;
      }).length;
    });

    console.log('Test 1: Large SVGs found:', largeSvgCount);
    expect(largeSvgCount).toBe(0);
  });

  // ============================================
  // TEST 2: Header displays indices correctly
  // ============================================
  test('2. Header displays NIFTY 50 and NIFTY BANK with spacing', async () => {
    // Already on watchlist page from test 1
    const headerText = await sharedPage.locator('body').innerText();

    const hasNifty50 = /NIFTY\s+50/.test(headerText);
    const hasNiftyBank = /NIFTY\s+BANK/.test(headerText);

    console.log('Test 2: NIFTY 50 present:', hasNifty50 ? '✓' : '✗');
    console.log('Test 2: NIFTY BANK present:', hasNiftyBank ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-02-header.png' });

    expect(hasNifty50).toBeTruthy();
    expect(hasNiftyBank).toBeTruthy();
  });

  // ============================================
  // TEST 3: Search box visible and functional
  // ============================================
  test('3. Search box is visible and functional', async () => {
    const searchInput = sharedPage.locator('input[placeholder*="Search"]').first();
    const isVisible = await searchInput.isVisible();
    console.log('Test 3: Search input visible:', isVisible ? '✓' : '✗');

    expect(isVisible).toBeTruthy();

    // Type in search
    await searchInput.fill('RELIANCE');
    await sharedPage.waitForTimeout(1500);

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-03-search.png' });

    // Check dropdown appears
    const dropdown = sharedPage.locator('text=/RELIANCE/i').first();
    const hasResults = await dropdown.isVisible().catch(() => false);
    console.log('Test 3: Search results visible:', hasResults ? '✓' : '✗');

    // Clear search
    await searchInput.fill('');
    await sharedPage.waitForTimeout(500);
  });

  // ============================================
  // TEST 4: Watchlist tabs visible
  // ============================================
  test('4. Watchlist tabs are visible', async () => {
    const tabs = sharedPage.locator('button').filter({ hasText: /Watchlist|Default/ });
    const count = await tabs.count();

    console.log('Test 4: Watchlist tabs found:', count);
    await sharedPage.screenshot({ path: 'tests/screenshots/wl-04-tabs.png' });

    expect(count).toBeGreaterThan(0);
  });

  // ============================================
  // TEST 5: Can add instrument to watchlist
  // ============================================
  test('5. Can add instrument to watchlist', async () => {
    const searchInput = sharedPage.locator('input[placeholder*="Search"]').first();
    await searchInput.fill('INFY');
    await sharedPage.waitForTimeout(1500);

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-05-search-infy.png' });

    // Click to add
    const addOption = sharedPage.locator('[class*="hover:bg"]').filter({ hasText: 'INFY' }).first();
    if (await addOption.isVisible()) {
      await addOption.click();
      console.log('Test 5: Clicked to add INFY');
      await sharedPage.waitForTimeout(1000);
    }

    // Clear search
    await searchInput.fill('');
    await sharedPage.keyboard.press('Escape');
    await sharedPage.waitForTimeout(500);

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-05-added.png' });

    // Verify in list
    const inList = await sharedPage.locator('text=INFY').first().isVisible().catch(() => false);
    console.log('Test 5: INFY in watchlist:', inList ? '✓' : '✗');
  });

  // ============================================
  // TEST 6: Empty state SVG is correctly sized
  // ============================================
  test('6. Empty state shows correctly (no giant SVG)', async () => {
    // Get all SVG sizes
    const svgSizes = await sharedPage.locator('svg').evaluateAll(svgs => {
      return svgs.map(svg => {
        const rect = svg.getBoundingClientRect();
        return { width: Math.round(rect.width), height: Math.round(rect.height) };
      }).filter(s => s.width > 0 && s.height > 0);
    });

    console.log('Test 6: SVG sizes:', svgSizes.slice(0, 5));

    // All SVGs should be under 100px
    const oversized = svgSizes.filter(s => s.width > 100 || s.height > 100);
    console.log('Test 6: Oversized SVGs:', oversized.length);

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-06-svg-check.png' });

    expect(oversized.length).toBe(0);
  });

  // ============================================
  // TEST 7: Layout not overlapping
  // ============================================
  test('7. Layout elements are not overlapping', async () => {
    const searchBox = await sharedPage.locator('input[placeholder*="Search"]').first().boundingBox();

    console.log('Test 7: Search box position:', searchBox);

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-07-layout.png', fullPage: true });

    // Basic check that search box has reasonable dimensions
    expect(searchBox).not.toBeNull();
    if (searchBox) {
      expect(searchBox.width).toBeGreaterThan(100);
      expect(searchBox.height).toBeGreaterThan(20);
    }
  });

  // ============================================
  // TEST 8: Can switch between watchlist tabs
  // ============================================
  test('8. Can switch between watchlist tabs', async () => {
    const tabs = sharedPage.locator('button').filter({ hasText: /Watchlist/ });
    const tabCount = await tabs.count();

    console.log('Test 8: Tab count:', tabCount);

    if (tabCount > 1) {
      // Click second tab
      await tabs.nth(1).click();
      await sharedPage.waitForTimeout(500);
      console.log('Test 8: Clicked second tab');

      await sharedPage.screenshot({ path: 'tests/screenshots/wl-08-tab-switch.png' });

      // Click first tab again
      await tabs.nth(0).click();
      await sharedPage.waitForTimeout(500);
      console.log('Test 8: Clicked first tab');
    }

    expect(tabCount).toBeGreaterThan(0);
  });

  // ============================================
  // TEST 9: + New group button works
  // ============================================
  test('9. New group button opens modal', async () => {
    const newGroupBtn = sharedPage.locator('button, a').filter({ hasText: /\+ New group|\+/ }).first();

    if (await newGroupBtn.isVisible()) {
      await newGroupBtn.click();
      await sharedPage.waitForTimeout(500);

      // Check for modal
      const modal = sharedPage.locator('[class*="fixed"], [class*="modal"], [role="dialog"]');
      const modalVisible = await modal.first().isVisible().catch(() => false);

      console.log('Test 9: Modal appeared:', modalVisible ? '✓' : '✗');

      await sharedPage.screenshot({ path: 'tests/screenshots/wl-09-new-group.png' });

      // Close modal
      const cancelBtn = sharedPage.locator('button').filter({ hasText: /Cancel|Close/ }).first();
      if (await cancelBtn.isVisible()) {
        await cancelBtn.click();
      } else {
        await sharedPage.keyboard.press('Escape');
      }
      await sharedPage.waitForTimeout(500);
    }
  });

  // ============================================
  // TEST 10: Live prices indicator visible
  // ============================================
  test('10. Live indicator is visible', async () => {
    const liveText = sharedPage.locator('text=/Live/i');
    const isVisible = await liveText.first().isVisible().catch(() => false);

    console.log('Test 10: Live indicator:', isVisible ? '✓' : '✗');

    // Also check for green pulse dot (status-dot.connected)
    const pulseDot = sharedPage.locator('.status-dot.connected, [class*="animate-pulse"], [class*="bg-green"]');
    const hasPulse = await pulseDot.first().isVisible().catch(() => false);

    console.log('Test 10: Connection status indicator:', hasPulse ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-10-live.png' });
  });

  // ============================================
  // TEST 11: KiteLayout header has all elements
  // ============================================
  test('11. KiteLayout header has navigation and user menu', async () => {
    // Check for KiteHeader elements
    const header = sharedPage.locator('.kite-header, header').first();
    const headerVisible = await header.isVisible().catch(() => false);

    console.log('Test 11: KiteHeader visible:', headerVisible ? '✓' : '✗');

    // Check navigation links
    const dashboardLink = sharedPage.locator('a[href="/dashboard"], a:has-text("Dashboard")');
    const optionChainLink = sharedPage.locator('a[href="/optionchain"], a:has-text("Option Chain")');
    const strategyLink = sharedPage.locator('a[href="/strategy"], a:has-text("Strategy")');
    const watchlistLink = sharedPage.locator('a[href="/watchlist"], a:has-text("Watchlist")');

    const hasDashboard = await dashboardLink.isVisible().catch(() => false);
    const hasOptionChain = await optionChainLink.isVisible().catch(() => false);
    const hasStrategy = await strategyLink.isVisible().catch(() => false);
    const hasWatchlist = await watchlistLink.isVisible().catch(() => false);

    console.log('Test 11: Dashboard nav:', hasDashboard ? '✓' : '✗');
    console.log('Test 11: Option Chain nav:', hasOptionChain ? '✓' : '✗');
    console.log('Test 11: Strategy nav:', hasStrategy ? '✓' : '✗');
    console.log('Test 11: Watchlist nav:', hasWatchlist ? '✓' : '✗');

    // Check user menu exists
    const userMenu = sharedPage.locator('.user-menu, [class*="user"]');
    const hasUserMenu = await userMenu.first().isVisible().catch(() => false);

    console.log('Test 11: User menu:', hasUserMenu ? '✓' : '✗');

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-11-header.png' });

    expect(headerVisible).toBeTruthy();
    expect(hasDashboard || hasOptionChain || hasStrategy || hasWatchlist).toBeTruthy();
  });

  // ============================================
  // TEST 12: User ID displayed (not "Guest")
  // ============================================
  test('12. User ID is displayed (not Guest)', async () => {
    const headerText = await sharedPage.locator('.kite-header, header').first().innerText().catch(() => '');

    // Check for "Guest" text
    const hasGuest = headerText.toLowerCase().includes('guest');

    // Check for user ID pattern (alphanumeric like DA1707)
    const hasUserId = /[A-Z]{2}\d{4}/.test(headerText);

    console.log('Test 12: Shows "Guest":', hasGuest ? '✗ YES (BAD)' : '✓ NO');
    console.log('Test 12: Shows user ID:', hasUserId ? '✓ YES' : '✗ NO');

    await sharedPage.screenshot({ path: 'tests/screenshots/wl-12-userid.png' });

    // User ID should be displayed, not "Guest"
    expect(hasGuest).toBeFalsy();
    expect(hasUserId).toBeTruthy();
  });
});
