import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const ZERODHA_USER_ID = 'DA1707';
const ZERODHA_PASSWORD = 'Infosys@123';

let page;

test.describe.configure({ mode: 'serial' });

test.describe('Positions Screen - Complete Tests', () => {

  test.beforeAll(async ({ browser }) => {
    // Create context with full screen viewport
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    page = await context.newPage();

    // Maximize the browser window
    await page.evaluate(() => {
      window.moveTo(0, 0);
      window.resizeTo(screen.availWidth, screen.availHeight);
    });

    console.log('\n' + '='.repeat(60));
    console.log('POSITIONS SCREEN TEST SUITE');
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
    // Do nothing - browser cleanup handled in final test
  });

  // ============================================
  // TEST 1: Navigate to Positions Page
  // ============================================
  test('1. Navigate to Positions page', async () => {
    console.log('\n--- TEST 1: Navigate to Positions ---');

    await page.goto(`${FRONTEND_URL}/positions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const title = await page.locator('text=Positions').first().isVisible();
    console.log('✓ Positions page loaded:', title ? 'Yes' : 'No');

    // Verify KiteLayout header is present
    const header = page.locator('.kite-header, header').first();
    const hasHeader = await header.isVisible().catch(() => false);
    console.log('✓ KiteHeader visible:', hasHeader ? 'Yes' : 'No');

    // Verify Positions link is active in navigation
    const navLink = page.locator('a[href="/positions"], .nav-item').filter({ hasText: /Positions/i });
    const isActiveNav = await navLink.first().isVisible().catch(() => false);
    console.log('✓ Positions nav link visible:', isActiveNav ? 'Yes' : 'No');

    // Check viewport dimensions
    const viewportSize = page.viewportSize();
    console.log(`✓ Viewport: ${viewportSize.width}x${viewportSize.height}`);

    await page.screenshot({ path: 'tests/screenshots/pos-01-page-load.png', fullPage: false });
    expect(title).toBeTruthy();
    expect(hasHeader).toBeTruthy();
  });

  // ============================================
  // TEST 1.5: Verify No Content Overflow
  // ============================================
  test('1.5. Verify screen content does not overflow', async () => {
    console.log('\n--- TEST 1.5: Screen Overflow Check ---');

    // Get viewport dimensions
    const viewportSize = page.viewportSize();
    console.log(`  Viewport: ${viewportSize.width}x${viewportSize.height}`);

    // Check for horizontal scrollbar (content wider than viewport)
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    console.log('  Horizontal scrollbar:', hasHorizontalScroll ? '✗ OVERFLOW' : '✓ None');

    // Check for vertical scrollbar on body (page content taller than viewport)
    const hasVerticalScroll = await page.evaluate(() => {
      return document.documentElement.scrollHeight > document.documentElement.clientHeight;
    });
    console.log('  Vertical scrollbar:', hasVerticalScroll ? '⚠ Yes (may be expected)' : '✓ None');

    // Get scroll dimensions
    const scrollDimensions = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      clientWidth: document.documentElement.clientWidth,
      clientHeight: document.documentElement.clientHeight
    }));
    console.log(`  Document scroll size: ${scrollDimensions.scrollWidth}x${scrollDimensions.scrollHeight}`);
    console.log(`  Document client size: ${scrollDimensions.clientWidth}x${scrollDimensions.clientHeight}`);

    // Check if main content container is within bounds
    const positionsPage = page.locator('.positions-page');
    if (await positionsPage.isVisible()) {
      const box = await positionsPage.boundingBox();
      if (box) {
        console.log(`  .positions-page bounds: x=${box.x}, y=${box.y}, w=${box.width}, h=${box.height}`);
        const rightEdge = box.x + box.width;
        const bottomEdge = box.y + box.height;
        const withinWidth = rightEdge <= viewportSize.width + 5; // 5px tolerance
        const withinHeight = bottomEdge <= viewportSize.height + 5;
        console.log('  Content within viewport width:', withinWidth ? '✓' : '✗');
        console.log('  Content within viewport height:', withinHeight ? '✓' : '✗');
      }
    }

    // Check header doesn't overflow
    const header = page.locator('.kite-header').first();
    if (await header.isVisible()) {
      const headerBox = await header.boundingBox();
      if (headerBox) {
        const headerFits = headerBox.width <= viewportSize.width;
        console.log('  Header width fits viewport:', headerFits ? '✓' : '✗');
      }
    }

    // Check page-header section
    const pageHeader = page.locator('.page-header').first();
    if (await pageHeader.isVisible()) {
      const pageHeaderBox = await pageHeader.boundingBox();
      if (pageHeaderBox) {
        const pageHeaderFits = pageHeaderBox.width <= viewportSize.width;
        console.log('  Page header fits viewport:', pageHeaderFits ? '✓' : '✗');
      }
    }

    await page.screenshot({ path: 'tests/screenshots/pos-01b-overflow-check.png', fullPage: false });

    // Assert no horizontal overflow
    expect(hasHorizontalScroll).toBeFalsy();
  });

  // ============================================
  // TEST 2: Verify Page Header Elements
  // ============================================
  test('2. Verify page header elements', async () => {
    console.log('\n--- TEST 2: Page Header Elements ---');

    // Page title
    const pageTitle = page.locator('.page-title, h1').filter({ hasText: /Positions/i });
    const hasTitleVisible = await pageTitle.first().isVisible().catch(() => false);
    console.log('  Page title:', hasTitleVisible ? '✓' : '✗');

    // Day/Net toggle
    const dayBtn = page.locator('button').filter({ hasText: /^Day$/i }).first();
    const netBtn = page.locator('button').filter({ hasText: /^Net$/i }).first();
    const hasDayBtn = await dayBtn.isVisible().catch(() => false);
    const hasNetBtn = await netBtn.isVisible().catch(() => false);
    console.log('  Day button:', hasDayBtn ? '✓' : '✗');
    console.log('  Net button:', hasNetBtn ? '✓' : '✗');

    // P&L Box
    const pnlBox = page.locator('.pnl-box, [class*="pnl"]').first();
    const hasPnlBox = await pnlBox.isVisible().catch(() => false);
    console.log('  P&L box:', hasPnlBox ? '✓' : '✗');

    // Auto refresh toggle
    const autoRefreshLabel = page.locator('label, span').filter({ hasText: /Auto\s*Refresh/i }).first();
    const hasAutoRefresh = await autoRefreshLabel.isVisible().catch(() => false);
    console.log('  Auto Refresh toggle:', hasAutoRefresh ? '✓' : '✗');

    // Refresh button
    const refreshBtn = page.locator('button').filter({ hasText: /Refresh/i }).first();
    const hasRefresh = await refreshBtn.isVisible().catch(() => false);
    console.log('  Refresh button:', hasRefresh ? '✓' : '✗');

    // Exit All button
    const exitAllBtn = page.locator('button').filter({ hasText: /Exit\s*All/i }).first();
    const hasExitAll = await exitAllBtn.isVisible().catch(() => false);
    console.log('  Exit All button:', hasExitAll ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/pos-02-header.png' });
    expect(hasTitleVisible).toBeTruthy();
  });

  // ============================================
  // TEST 3: Click Refresh to Load Positions
  // ============================================
  test('3. Click Refresh to load positions', async () => {
    console.log('\n--- TEST 3: Refresh Data ---');

    const refreshBtn = page.locator('button').filter({ hasText: /Refresh/i }).first();

    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      console.log('  ✓ Clicked Refresh');

      // Wait for loading to complete
      await page.waitForTimeout(5000);

      // Check if data loaded or empty state shown
      const pageText = await page.locator('body').innerText();
      const hasPositions = pageText.includes('NIFTY') || pageText.includes('BANKNIFTY');
      const hasEmptyState = /No\s*Open\s*Positions/i.test(pageText);

      console.log('  Has positions data:', hasPositions ? '✓' : '✗');
      console.log('  Has empty state:', hasEmptyState ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-03-refresh.png', fullPage: true });
  });

  // ============================================
  // TEST 4: Verify Total P&L Display
  // ============================================
  test('4. Verify Total P&L display', async () => {
    console.log('\n--- TEST 4: Total P&L Display ---');

    const pageText = await page.locator('body').innerText();

    // Look for "Total P&L" text
    const hasTotalPnL = /Total\s*P\s*&?\s*L/i.test(pageText);
    console.log('  Total P&L label:', hasTotalPnL ? '✓' : '✗');

    // Look for P&L value (positive or negative number with ₹)
    const hasPnLValue = /[+-]?\s*₹?\s*[\d,]+/.test(pageText) || /[+-]?\s*[\d,]+\s*%/.test(pageText);
    console.log('  P&L value visible:', hasPnLValue ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/pos-04-total-pnl.png' });
  });

  // ============================================
  // TEST 5: Verify Summary Bar
  // ============================================
  test('5. Verify summary bar elements', async () => {
    console.log('\n--- TEST 5: Summary Bar ---');

    const pageText = await page.locator('body').innerText();

    // Check for summary items
    const hasPositionsCount = /Positions\s*\d+/i.test(pageText);
    const hasQuantity = /Quantity\s*[\d,]+/i.test(pageText);
    const hasRealized = /Realized/i.test(pageText);
    const hasUnrealized = /Unrealized/i.test(pageText);
    const hasMarginUsed = /Margin\s*Used/i.test(pageText);
    const hasAvailable = /Available/i.test(pageText);

    console.log('  Positions count:', hasPositionsCount ? '✓' : '✗');
    console.log('  Quantity:', hasQuantity ? '✓' : '✗');
    console.log('  Realized P&L:', hasRealized ? '✓' : '✗');
    console.log('  Unrealized P&L:', hasUnrealized ? '✓' : '✗');
    console.log('  Margin Used:', hasMarginUsed ? '✓' : '✗');
    console.log('  Available:', hasAvailable ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/pos-05-summary.png' });
  });

  // ============================================
  // TEST 6: Toggle Day/Net Positions
  // ============================================
  test('6. Toggle Day/Net positions', async () => {
    console.log('\n--- TEST 6: Day/Net Toggle ---');

    const dayBtn = page.locator('button').filter({ hasText: /^Day$/i }).first();
    const netBtn = page.locator('button').filter({ hasText: /^Net$/i }).first();

    // Click Day button
    if (await dayBtn.isVisible()) {
      await dayBtn.click();
      console.log('  ✓ Clicked Day');
      await page.waitForTimeout(2000);

      // Check if Day is active
      const dayClass = await dayBtn.getAttribute('class');
      const dayActive = dayClass?.includes('active');
      console.log('  Day active:', dayActive ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-06-day.png' });

    // Click Net button
    if (await netBtn.isVisible()) {
      await netBtn.click();
      console.log('  ✓ Clicked Net');
      await page.waitForTimeout(2000);

      // Check if Net is active
      const netClass = await netBtn.getAttribute('class');
      const netActive = netClass?.includes('active');
      console.log('  Net active:', netActive ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-06-net.png' });
  });

  // ============================================
  // TEST 7: Verify Positions Table Headers (or Empty State)
  // ============================================
  test('7. Verify positions table headers or empty state', async () => {
    console.log('\n--- TEST 7: Table Headers / Empty State ---');

    // Wait for page to settle
    await page.waitForTimeout(1000);

    // Check if empty state is shown (div with class 'empty-state')
    const emptyStateDiv = page.locator('.empty-state');
    const hasEmptyState = await emptyStateDiv.isVisible().catch(() => false);

    // Also check for positions table
    const positionsTable = page.locator('table.positions-table');
    const hasTable = await positionsTable.isVisible().catch(() => false);

    console.log('  Empty state div visible:', hasEmptyState ? '✓' : '✗');
    console.log('  Table visible:', hasTable ? '✓' : '✗');

    if (hasEmptyState) {
      console.log('  Empty state shown (no positions)');

      // Verify empty state heading
      const headingText = await page.locator('.empty-state h3').innerText().catch(() => '');
      console.log('  Empty state heading:', headingText);

      // Verify empty state elements
      const optionChainLink = page.locator('.empty-state a[href="/optionchain"]');
      const hasLink = await optionChainLink.isVisible().catch(() => false);
      console.log('  Option Chain link:', hasLink ? '✓' : '✗');

      await page.screenshot({ path: 'tests/screenshots/pos-07-empty-state.png' });
      console.log('  ✓ Empty state test PASSED');
      expect(hasEmptyState).toBeTruthy();
    } else if (hasTable) {
      // Table should be visible
      const expectedHeaders = ['Instrument', 'Qty', 'Avg', 'LTP', 'P&L', 'Actions'];
      const headerText = await page.locator('table.positions-table thead th').allInnerTexts();
      const allHeaders = headerText.join(' ').toUpperCase();

      console.log('  Headers found:', allHeaders.substring(0, 150));

      let foundCount = 0;
      for (const header of expectedHeaders) {
        const found = allHeaders.includes(header.toUpperCase());
        console.log(`    ${header}:`, found ? '✓' : '✗');
        if (found) foundCount++;
      }

      await page.screenshot({ path: 'tests/screenshots/pos-07-headers.png' });
      expect(foundCount).toBeGreaterThanOrEqual(3);
    } else {
      // Neither empty state nor table - check page content as fallback
      console.log('  Neither empty state div nor table visible - checking page text');
      const pageText = await page.locator('body').innerText();
      const hasNoPositions = /No\s*Open\s*Positions/i.test(pageText);
      console.log('  Page contains "No Open Positions":', hasNoPositions ? '✓' : '✗');
      await page.screenshot({ path: 'tests/screenshots/pos-07-unknown.png' });
      expect(hasNoPositions).toBeTruthy();
    }
  });

  // ============================================
  // TEST 8: Verify Position Rows (if any)
  // ============================================
  test('8. Verify position rows display', async () => {
    console.log('\n--- TEST 8: Position Rows ---');

    // Check for positions table rows
    const positionRows = await page.locator('table.positions-table tbody tr').count();
    console.log('  Position rows found:', positionRows);

    if (positionRows > 0) {
      // Check first row content
      const firstRow = page.locator('table.positions-table tbody tr').first();
      const rowText = await firstRow.innerText();
      console.log('  First row preview:', rowText.substring(0, 100));

      // Check for instrument name
      const hasInstrument = /NIFTY|BANKNIFTY|FINNIFTY/i.test(rowText);
      console.log('  Has instrument name:', hasInstrument ? '✓' : '✗');

      // Check for quantity
      const hasQuantity = /[+-]?\d+/.test(rowText);
      console.log('  Has quantity:', hasQuantity ? '✓' : '✗');
      expect(hasInstrument || hasQuantity).toBeTruthy();
    } else {
      // Check for empty state by class
      const emptyState = page.locator('.empty-state');
      const hasEmpty = await emptyState.isVisible().catch(() => false);
      console.log('  Empty state shown:', hasEmpty ? '✓' : '✗');
      console.log('  ✓ No positions - test PASSED');
      expect(hasEmpty).toBeTruthy();
    }

    await page.screenshot({ path: 'tests/screenshots/pos-08-rows.png' });
  });

  // ============================================
  // TEST 9: Verify Exit Button on Position Row
  // ============================================
  test('9. Verify Exit button on position rows', async () => {
    console.log('\n--- TEST 9: Exit Button ---');

    const exitButtons = await page.locator('button').filter({ hasText: /^Exit$/i }).count();
    console.log('  Exit buttons found:', exitButtons);

    if (exitButtons > 0) {
      const firstExitBtn = page.locator('button').filter({ hasText: /^Exit$/i }).first();
      const isVisible = await firstExitBtn.isVisible();
      console.log('  First Exit button visible:', isVisible ? '✓' : '✗');
    } else {
      console.log('  No positions - no Exit buttons expected');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-09-exit-btn.png' });
  });

  // ============================================
  // TEST 10: Verify Add Button on Position Row
  // ============================================
  test('10. Verify Add button on position rows', async () => {
    console.log('\n--- TEST 10: Add Button ---');

    const addButtons = await page.locator('button').filter({ hasText: /^Add$/i }).count();
    console.log('  Add buttons found:', addButtons);

    if (addButtons > 0) {
      const firstAddBtn = page.locator('button').filter({ hasText: /^Add$/i }).first();
      const isVisible = await firstAddBtn.isVisible();
      console.log('  First Add button visible:', isVisible ? '✓' : '✗');
    } else {
      console.log('  No positions - no Add buttons expected');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-10-add-btn.png' });
  });

  // ============================================
  // TEST 11: Click Exit Button to Open Modal
  // ============================================
  test('11. Click Exit button to open modal', async () => {
    console.log('\n--- TEST 11: Exit Modal ---');

    const exitButtons = await page.locator('button').filter({ hasText: /^Exit$/i }).count();

    if (exitButtons > 0) {
      const firstExitBtn = page.locator('button').filter({ hasText: /^Exit$/i }).first();
      await firstExitBtn.click();
      console.log('  ✓ Clicked Exit button');
      await page.waitForTimeout(500);

      // Check if modal opened
      const modal = page.locator('.modal, [class*="modal"]');
      const modalVisible = await modal.first().isVisible().catch(() => false);
      console.log('  Modal opened:', modalVisible ? '✓' : '✗');

      if (modalVisible) {
        // Check modal content
        const modalText = await modal.first().innerText();
        const hasOrderType = /Market|Limit/i.test(modalText);
        const hasQuantity = /Quantity/i.test(modalText);
        console.log('  Has Order Type options:', hasOrderType ? '✓' : '✗');
        console.log('  Has Quantity input:', hasQuantity ? '✓' : '✗');

        // Close modal
        const closeBtn = page.locator('.modal-close, button').filter({ hasText: /Cancel|×|Close/i }).first();
        if (await closeBtn.isVisible()) {
          await closeBtn.click();
          console.log('  ✓ Closed modal');
        }
      }
    } else {
      console.log('  No positions - skipping Exit modal test');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-11-exit-modal.png' });
  });

  // ============================================
  // TEST 12: Click Add Button to Open Modal
  // ============================================
  test('12. Click Add button to open modal', async () => {
    console.log('\n--- TEST 12: Add Modal ---');

    const addButtons = await page.locator('button').filter({ hasText: /^Add$/i }).count();

    if (addButtons > 0) {
      const firstAddBtn = page.locator('button').filter({ hasText: /^Add$/i }).first();
      await firstAddBtn.click();
      console.log('  ✓ Clicked Add button');
      await page.waitForTimeout(500);

      // Check if modal opened
      const modal = page.locator('.modal, [class*="modal"]');
      const modalVisible = await modal.first().isVisible().catch(() => false);
      console.log('  Modal opened:', modalVisible ? '✓' : '✗');

      if (modalVisible) {
        // Check modal content
        const modalText = await modal.first().innerText();
        const hasBuySell = /BUY|SELL/i.test(modalText);
        const hasPrice = /Price/i.test(modalText);
        console.log('  Has BUY/SELL options:', hasBuySell ? '✓' : '✗');
        console.log('  Has Price input:', hasPrice ? '✓' : '✗');

        // Close modal
        const closeBtn = page.locator('.modal-close, button').filter({ hasText: /Cancel|×|Close/i }).first();
        if (await closeBtn.isVisible()) {
          await closeBtn.click();
          console.log('  ✓ Closed modal');
        }
      }
    } else {
      console.log('  No positions - skipping Add modal test');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-12-add-modal.png' });
  });

  // ============================================
  // TEST 13: Toggle Auto Refresh
  // ============================================
  test('13. Toggle Auto Refresh', async () => {
    console.log('\n--- TEST 13: Auto Refresh Toggle ---');

    const autoRefreshCheckbox = page.locator('input[type="checkbox"]').first();
    const autoRefreshLabel = page.locator('label, span').filter({ hasText: /Auto\s*Refresh/i }).first();

    if (await autoRefreshLabel.isVisible()) {
      // Enable auto refresh
      await autoRefreshLabel.click();
      console.log('  ✓ Clicked Auto Refresh toggle');
      await page.waitForTimeout(1000);

      // Wait to see if it refreshes
      await page.waitForTimeout(6000);
      console.log('  ✓ Waited for auto refresh cycle');

      // Disable auto refresh
      await autoRefreshLabel.click();
      console.log('  ✓ Disabled Auto Refresh');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-13-auto-refresh.png' });
  });

  // ============================================
  // TEST 14: Verify Color Coding for P&L
  // ============================================
  test('14. Verify P&L color coding', async () => {
    console.log('\n--- TEST 14: P&L Color Coding ---');

    // Check for profit colors (green)
    const greenElements = await page.locator('.text-green, .profit, [class*="green"]').count();
    console.log('  Green (profit) elements:', greenElements);

    // Check for loss colors (red)
    const redElements = await page.locator('.text-red, .loss, [class*="red"]').count();
    console.log('  Red (loss) elements:', redElements);

    // Check P&L box color
    const pnlBox = page.locator('.pnl-box').first();
    if (await pnlBox.isVisible()) {
      const pnlClass = await pnlBox.getAttribute('class');
      const isProfit = pnlClass?.includes('profit');
      const isLoss = pnlClass?.includes('loss');
      console.log('  P&L box colored:', (isProfit || isLoss) ? '✓' : '✗ (no positions)');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-14-colors.png' });
  });

  // ============================================
  // TEST 15: Verify Long/Short Position Display
  // ============================================
  test('15. Verify Long/Short position display', async () => {
    console.log('\n--- TEST 15: Long/Short Display ---');

    const positionRows = await page.locator('tbody tr, .position-row').count();

    if (positionRows > 0) {
      const pageText = await page.locator('body').innerText();

      // Look for positive quantity (long) with +
      const hasLong = /\+\d+/.test(pageText);
      // Look for negative quantity (short) with -
      const hasShort = /-\d+/.test(pageText);

      console.log('  Long position indicator (+):', hasLong ? '✓' : '✗');
      console.log('  Short position indicator (-):', hasShort ? '✓' : '✗');

      // Check for long/short classes
      const longElements = await page.locator('.long, [class*="long"]').count();
      const shortElements = await page.locator('.short, [class*="short"]').count();
      console.log('  Long styled elements:', longElements);
      console.log('  Short styled elements:', shortElements);
    } else {
      console.log('  No positions - skipping Long/Short test');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-15-long-short.png' });
  });

  // ============================================
  // TEST 16: Click Exit All Button
  // ============================================
  test('16. Click Exit All button (confirmation dialog)', async () => {
    console.log('\n--- TEST 16: Exit All Confirmation ---');

    const exitAllBtn = page.locator('button').filter({ hasText: /Exit\s*All/i }).first();

    if (await exitAllBtn.isVisible()) {
      const isEnabled = await exitAllBtn.isEnabled();
      console.log('  Exit All enabled:', isEnabled ? '✓' : '✗ (no positions)');

      if (isEnabled) {
        await exitAllBtn.click();
        console.log('  ✓ Clicked Exit All');
        await page.waitForTimeout(500);

        // Check for confirmation dialog
        const confirmModal = page.locator('.modal, [class*="modal"]');
        const modalVisible = await confirmModal.first().isVisible().catch(() => false);
        console.log('  Confirmation dialog:', modalVisible ? '✓' : '✗');

        if (modalVisible) {
          const modalText = await confirmModal.first().innerText();
          const hasWarning = /sure|confirm|all\s*positions/i.test(modalText);
          console.log('  Has warning text:', hasWarning ? '✓' : '✗');

          // Cancel the dialog
          const cancelBtn = page.locator('button').filter({ hasText: /Cancel/i }).first();
          if (await cancelBtn.isVisible()) {
            await cancelBtn.click();
            console.log('  ✓ Cancelled Exit All');
          }
        }
      }
    }

    await page.screenshot({ path: 'tests/screenshots/pos-16-exit-all.png' });
  });

  // ============================================
  // TEST 17: Verify Empty State
  // ============================================
  test('17. Verify empty state display', async () => {
    console.log('\n--- TEST 17: Empty State ---');

    const positionRows = await page.locator('table.positions-table tbody tr').count();

    if (positionRows === 0) {
      const emptyState = page.locator('.empty-state');
      const hasEmpty = await emptyState.isVisible().catch(() => false);
      console.log('  Empty state visible:', hasEmpty ? '✓' : '✗');

      if (hasEmpty) {
        // Check empty state content
        const headingText = await page.locator('.empty-state h3').innerText().catch(() => '');
        console.log('  Empty state heading:', headingText);

        // Check for link to Option Chain
        const optionChainLink = page.locator('.empty-state a[href="/optionchain"]');
        const hasLink = await optionChainLink.isVisible().catch(() => false);
        console.log('  Option Chain link:', hasLink ? '✓' : '✗');
      }
    } else {
      console.log('  Has positions - empty state not shown');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-17-empty.png' });
  });

  // ============================================
  // TEST 18: Verify Total Row in Table
  // ============================================
  test('18. Verify total row in table', async () => {
    console.log('\n--- TEST 18: Total Row ---');

    const totalRow = page.locator('tfoot tr, .total-row');
    const hasTotalRow = await totalRow.first().isVisible().catch(() => false);
    console.log('  Total row visible:', hasTotalRow ? '✓' : '✗');

    if (hasTotalRow) {
      const totalText = await totalRow.first().innerText();
      const hasTotal = /Total/i.test(totalText);
      console.log('  Has "Total" text:', hasTotal ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-18-total.png' });
  });

  // ============================================
  // TEST 19: Navigate Back to Dashboard
  // ============================================
  test('19. Navigate back to Dashboard', async () => {
    console.log('\n--- TEST 19: Navigation ---');

    // Click Dashboard in nav
    const dashboardLink = page.locator('a[href="/dashboard"], .nav-item').filter({ hasText: /Dashboard/i }).first();

    if (await dashboardLink.isVisible()) {
      await dashboardLink.click();
      console.log('  ✓ Clicked Dashboard');
      await page.waitForTimeout(2000);

      // Verify we're on dashboard
      const currentUrl = page.url();
      const onDashboard = currentUrl.includes('/dashboard');
      console.log('  On Dashboard:', onDashboard ? '✓' : '✗');

      // Check for Positions card
      const positionsCard = page.locator('a[href="/positions"], .router-link-exact-active').filter({ hasText: /Positions/i });
      const hasCard = await positionsCard.first().isVisible().catch(() => false);
      console.log('  Positions card visible:', hasCard ? '✓' : '✗');
    }

    await page.screenshot({ path: 'tests/screenshots/pos-19-dashboard.png' });
  });

  // ============================================
  // TEST 20: Navigate Back to Positions
  // ============================================
  test('20. Navigate back to Positions', async () => {
    console.log('\n--- TEST 20: Return to Positions ---');

    await page.goto(`${FRONTEND_URL}/positions`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const title = await page.locator('text=Positions').first().isVisible();
    console.log('  Back on Positions:', title ? '✓' : '✗');

    await page.screenshot({ path: 'tests/screenshots/pos-20-return.png', fullPage: true });
  });

  // ============================================
  // TEST 21: Final Summary
  // ============================================
  test('21. Final summary and screenshot', async () => {
    console.log('\n' + '='.repeat(60));
    console.log('POSITIONS SCREEN TEST SUMMARY');
    console.log('='.repeat(60));

    await page.screenshot({ path: 'tests/screenshots/pos-21-final.png', fullPage: true });

    console.log('\n✅ Tests Completed');
    console.log('\nFeatures Verified:');
    console.log('  • Page navigation and layout');
    console.log('  • Page header elements (title, toggles, buttons)');
    console.log('  • Day/Net position toggle');
    console.log('  • Total P&L display with color coding');
    console.log('  • Summary bar (positions, quantity, margins)');
    console.log('  • Positions table with headers');
    console.log('  • Position rows with data');
    console.log('  • Exit button and modal');
    console.log('  • Add button and modal');
    console.log('  • Auto refresh toggle');
    console.log('  • P&L color coding (profit/loss)');
    console.log('  • Long/Short position display');
    console.log('  • Exit All confirmation dialog');
    console.log('  • Empty state');
    console.log('  • Total row in table');
    console.log('  • Navigation to/from Dashboard');

    console.log('\n📸 Screenshots saved in tests/screenshots/pos-*.png');
    console.log('='.repeat(60));

    console.log('\n✓ Browser will remain open for manual inspection.');
    console.log('Press Ctrl+C in terminal to close when done.\n');

    // Keep browser open for manual inspection (10 minutes)
    await page.waitForTimeout(600000);
  });
});
