import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5174';

test.describe('Watchlist Manual Verification', () => {

  test('Complete watchlist verification with real Zerodha login', async ({ page }) => {
    test.setTimeout(300000); // 5 minutes total timeout

    // ========================================
    // STEP 1: Login with Zerodha
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 1: ZERODHA LOGIN');
    console.log('='.repeat(60));

    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'tests/screenshots/verify-01-login-page.png' });
    console.log('✓ Login page loaded');

    // Click Zerodha login button
    const zerodhaButton = page.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaButton.click();
    console.log('✓ Clicked Zerodha button');

    // Wait for Kite login page
    await page.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });
    await page.screenshot({ path: 'tests/screenshots/verify-02-kite-login.png' });

    console.log('\n' + '*'.repeat(60));
    console.log('*** MANUAL ACTION REQUIRED ***');
    console.log('*'.repeat(60));
    console.log('\n1. Enter your Zerodha User ID');
    console.log('2. Enter your Password');
    console.log('3. Complete 2FA (PIN/TOTP)');
    console.log('4. Click Login');
    console.log('\nWaiting up to 2 minutes for login...\n');

    // Wait for redirect back to app
    await page.waitForURL(/localhost:5174/, { timeout: 120000 });
    await page.waitForTimeout(3000); // Wait for auth to complete
    await page.screenshot({ path: 'tests/screenshots/verify-03-after-login.png' });
    console.log('✓ Login successful! Redirected back to app.');

    // ========================================
    // STEP 2: Navigate to Watchlist
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 2: NAVIGATE TO WATCHLIST');
    console.log('='.repeat(60));

    // Check current URL and navigate if needed
    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);

    if (!currentUrl.includes('/watchlist')) {
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
    }
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/screenshots/verify-04-watchlist-page.png' });
    console.log('✓ Watchlist page loaded');

    // ========================================
    // STEP 3: Check Index Header (NIFTY 50 & NIFTY BANK)
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 3: VERIFY INDEX HEADER');
    console.log('='.repeat(60));

    // Look for NIFTY 50 in header
    const nifty50 = page.locator('text=/NIFTY\\s*50/i').first();
    const nifty50Visible = await nifty50.isVisible().catch(() => false);
    console.log('NIFTY 50 in header:', nifty50Visible ? '✓ VISIBLE' : '✗ NOT FOUND');

    // Look for NIFTY BANK in header
    const niftyBank = page.locator('text=/NIFTY\\s*BANK|BANKNIFTY/i').first();
    const niftyBankVisible = await niftyBank.isVisible().catch(() => false);
    console.log('NIFTY BANK in header:', niftyBankVisible ? '✓ VISIBLE' : '✗ NOT FOUND');

    // Try to get header prices
    const headerText = await page.locator('header, [class*="header"], [class*="index"]').first().innerText().catch(() => '');
    console.log('Header content:', headerText.substring(0, 200));

    await page.screenshot({ path: 'tests/screenshots/verify-05-index-header.png' });

    // ========================================
    // STEP 4: Add NIFTY 50 to Watchlist
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 4: ADD NIFTY 50 TO WATCHLIST');
    console.log('='.repeat(60));

    // Find search input
    const searchInput = page.locator('input[type="text"], input[type="search"], input[placeholder*="search" i], input[placeholder*="add" i]').first();

    if (await searchInput.isVisible()) {
      // Clear and type search query
      await searchInput.click();
      await searchInput.fill('');
      await searchInput.fill('NIFTY 50');
      console.log('✓ Typed "NIFTY 50" in search');

      await page.waitForTimeout(2000); // Wait for search results
      await page.screenshot({ path: 'tests/screenshots/verify-06-search-nifty50.png' });

      // Click on NIFTY 50 result
      const nifty50Result = page.locator('[class*="result"], [class*="item"], [class*="row"], li, div')
        .filter({ hasText: /NIFTY 50|NIFTY50/i })
        .first();

      if (await nifty50Result.isVisible()) {
        await nifty50Result.click();
        console.log('✓ Clicked NIFTY 50 to add');
        await page.waitForTimeout(1000);
      } else {
        // Try clicking any result with NIFTY
        const anyNiftyResult = page.locator('text=/NIFTY/i').first();
        if (await anyNiftyResult.isVisible()) {
          await anyNiftyResult.click();
          console.log('✓ Clicked first NIFTY result');
        }
      }

      await page.screenshot({ path: 'tests/screenshots/verify-07-added-nifty50.png' });
    } else {
      console.log('✗ Search input not found');
    }

    // ========================================
    // STEP 5: Add RELIANCE to Watchlist
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 5: ADD RELIANCE TO WATCHLIST');
    console.log('='.repeat(60));

    // Clear search and search for RELIANCE
    if (await searchInput.isVisible()) {
      await searchInput.click();
      await searchInput.fill('');
      await searchInput.fill('RELIANCE');
      console.log('✓ Typed "RELIANCE" in search');

      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'tests/screenshots/verify-08-search-reliance.png' });

      // Click on RELIANCE result (prefer NSE)
      const relianceResult = page.locator('[class*="result"], [class*="item"], [class*="row"], li, div')
        .filter({ hasText: /RELIANCE.*NSE|NSE.*RELIANCE/i })
        .first();

      if (await relianceResult.isVisible()) {
        await relianceResult.click();
        console.log('✓ Clicked RELIANCE NSE to add');
      } else {
        // Try any RELIANCE result
        const anyRelianceResult = page.locator('text=/RELIANCE/i').first();
        if (await anyRelianceResult.isVisible()) {
          await anyRelianceResult.click();
          console.log('✓ Clicked first RELIANCE result');
        }
      }

      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'tests/screenshots/verify-09-added-reliance.png' });

      // Clear search to show watchlist
      await searchInput.fill('');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    // ========================================
    // STEP 6: Verify Watchlist Contents
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 6: VERIFY WATCHLIST CONTENTS');
    console.log('='.repeat(60));

    await page.screenshot({ path: 'tests/screenshots/verify-10-watchlist-contents.png' });

    // Check if instruments are in watchlist
    const pageContent = await page.content();
    const hasNifty = pageContent.includes('NIFTY');
    const hasReliance = pageContent.includes('RELIANCE');

    console.log('NIFTY in watchlist:', hasNifty ? '✓ YES' : '✗ NO');
    console.log('RELIANCE in watchlist:', hasReliance ? '✓ YES' : '✗ NO');

    // Get all visible text in watchlist area
    const watchlistText = await page.locator('[class*="watchlist"], [class*="instrument"], main').first().innerText().catch(() => '');
    console.log('\nWatchlist content preview:');
    console.log(watchlistText.substring(0, 500));

    // ========================================
    // STEP 7: Verify Live Price Updates (30 seconds)
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 7: VERIFY LIVE PRICE UPDATES (30 seconds)');
    console.log('='.repeat(60));

    console.log('\nWatching for price changes...');
    console.log('(Note: Prices only update during market hours 9:15 AM - 3:30 PM IST)\n');

    // Capture initial prices
    const getPrices = async () => {
      const priceElements = await page.locator('[class*="price"], [class*="ltp"], [class*="value"]').all();
      const prices = [];
      for (const el of priceElements.slice(0, 10)) {
        const text = await el.innerText().catch(() => '');
        if (text && /\d/.test(text)) {
          prices.push(text.trim());
        }
      }
      return prices;
    };

    const initialPrices = await getPrices();
    console.log('Initial prices captured:', initialPrices.slice(0, 5));

    // Wait and check for updates
    for (let i = 1; i <= 6; i++) {
      await page.waitForTimeout(5000);
      const currentPrices = await getPrices();
      console.log(`After ${i * 5}s:`, currentPrices.slice(0, 5));

      // Take screenshot every 10 seconds
      if (i % 2 === 0) {
        await page.screenshot({ path: `tests/screenshots/verify-11-live-prices-${i * 5}s.png` });
      }
    }

    const finalPrices = await getPrices();
    console.log('\nFinal prices:', finalPrices.slice(0, 5));

    // Check if prices changed
    const pricesChanged = JSON.stringify(initialPrices) !== JSON.stringify(finalPrices);
    console.log('Prices changed during observation:', pricesChanged ? '✓ YES' : '✗ NO (may be outside market hours)');

    // ========================================
    // STEP 8: Test Instrument Row Expansion
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 8: TEST INSTRUMENT ROW EXPANSION');
    console.log('='.repeat(60));

    // Click on first instrument row
    const instrumentRow = page.locator('[class*="instrument"], [class*="stock"], [class*="row"]')
      .filter({ hasText: /NIFTY|RELIANCE/i })
      .first();

    if (await instrumentRow.isVisible()) {
      await instrumentRow.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: 'tests/screenshots/verify-12-expanded-row.png' });

      // Check for action buttons
      const buyBtn = page.locator('button').filter({ hasText: /^B$|Buy/i }).first();
      const sellBtn = page.locator('button').filter({ hasText: /^S$|Sell/i }).first();

      const buyVisible = await buyBtn.isVisible().catch(() => false);
      const sellVisible = await sellBtn.isVisible().catch(() => false);

      console.log('Buy button visible:', buyVisible ? '✓ YES' : '✗ NO');
      console.log('Sell button visible:', sellVisible ? '✓ YES' : '✗ NO');
    }

    // ========================================
    // FINAL SUMMARY
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('VERIFICATION SUMMARY');
    console.log('='.repeat(60));

    const results = {
      'Zerodha Login': true,
      'Watchlist Page Loaded': true,
      'NIFTY 50 in Header': nifty50Visible,
      'NIFTY BANK in Header': niftyBankVisible,
      'NIFTY in Watchlist': hasNifty,
      'RELIANCE in Watchlist': hasReliance,
      'Live Price Updates': pricesChanged,
    };

    console.log('\n');
    for (const [test, passed] of Object.entries(results)) {
      console.log(`${passed ? '✓' : '✗'} ${test}`);
    }

    const passedCount = Object.values(results).filter(v => v).length;
    const totalCount = Object.values(results).length;
    console.log(`\n${passedCount}/${totalCount} checks passed`);

    // Final screenshot
    await page.screenshot({ path: 'tests/screenshots/verify-13-final-state.png', fullPage: true });

    console.log('\n' + '='.repeat(60));
    console.log('Screenshots saved in tests/screenshots/verify-*.png');
    console.log('='.repeat(60));

    // Keep browser open for manual inspection
    console.log('\nBrowser will stay open for 30 seconds for manual inspection...');
    await page.waitForTimeout(30000);
  });

});
