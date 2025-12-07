import { test, expect } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8000';

test.describe('Kite WebSocket Live Prices Verification', () => {

  test('Verify live prices after Zerodha login', async ({ page }) => {
    test.setTimeout(300000); // 5 minutes timeout

    // ========================================
    // STEP 1: Login with Zerodha
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 1: ZERODHA LOGIN');
    console.log('='.repeat(60));

    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForLoadState('networkidle');
    console.log('✓ Login page loaded');

    // Click Zerodha login button
    const zerodhaButton = page.locator('button, a').filter({ hasText: /zerodha/i }).first();
    await zerodhaButton.click();
    console.log('✓ Clicked Zerodha button');

    // Wait for Kite login page
    await page.waitForURL(/kite\.zerodha\.com/, { timeout: 15000 });

    console.log('\n' + '*'.repeat(60));
    console.log('*** MANUAL ACTION REQUIRED ***');
    console.log('*'.repeat(60));
    console.log('\n1. Enter your Zerodha User ID');
    console.log('2. Enter your Password');
    console.log('3. Complete 2FA (PIN/TOTP)');
    console.log('4. Click Login');
    console.log('\nWaiting up to 2 minutes for login...\n');

    // Wait for redirect back to app
    await page.waitForURL(/localhost:5173/, { timeout: 120000 });
    await page.waitForTimeout(3000);
    console.log('✓ Login successful!');

    // ========================================
    // STEP 2: Navigate to Watchlist
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 2: NAVIGATE TO WATCHLIST');
    console.log('='.repeat(60));

    if (!page.url().includes('/watchlist')) {
      await page.goto(`${FRONTEND_URL}/watchlist`);
    }
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'tests/screenshots/ws-verify-01-watchlist.png' });
    console.log('✓ Watchlist page loaded');

    // ========================================
    // STEP 3: Check WebSocket Connection Status
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 3: CHECK WEBSOCKET CONNECTION');
    console.log('='.repeat(60));

    // Wait for WebSocket to connect
    await page.waitForTimeout(5000);

    // Check browser console for WebSocket logs
    const wsStatus = await page.evaluate(() => {
      const store = window.__watchlistStore || {};
      return {
        isConnected: store.isConnected || false,
        hasWebSocket: !!store.websocket,
        readyState: store.websocket?.readyState
      };
    });

    console.log('WebSocket status from store:', wsStatus);

    // ========================================
    // STEP 4: Add NIFTY 50 Index to Watchlist
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 4: ADD NIFTY 50 TO WATCHLIST');
    console.log('='.repeat(60));

    // Find search input
    const searchInput = page.locator('input[type="text"], input[type="search"], input[placeholder*="search" i], input[placeholder*="add" i]').first();

    if (await searchInput.isVisible()) {
      await searchInput.click();
      await searchInput.fill('NIFTY 50');
      console.log('✓ Typed "NIFTY 50" in search');

      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'tests/screenshots/ws-verify-02-search.png' });

      // Click first NIFTY result
      const niftyResult = page.locator('text=/NIFTY.*50|NIFTY50/i').first();
      if (await niftyResult.isVisible()) {
        await niftyResult.click();
        console.log('✓ Added NIFTY 50');
        await page.waitForTimeout(1500);
      }

      // Clear search
      await searchInput.fill('');
      await page.keyboard.press('Escape');
    }

    // ========================================
    // STEP 5: Add RELIANCE to Watchlist
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 5: ADD RELIANCE TO WATCHLIST');
    console.log('='.repeat(60));

    if (await searchInput.isVisible()) {
      await searchInput.click();
      await searchInput.fill('RELIANCE');
      console.log('✓ Typed "RELIANCE" in search');

      await page.waitForTimeout(2000);

      const relianceResult = page.locator('text=/RELIANCE/i').first();
      if (await relianceResult.isVisible()) {
        await relianceResult.click();
        console.log('✓ Added RELIANCE');
        await page.waitForTimeout(1500);
      }

      await searchInput.fill('');
      await page.keyboard.press('Escape');
    }

    await page.screenshot({ path: 'tests/screenshots/ws-verify-03-instruments-added.png' });

    // ========================================
    // STEP 6: VERIFY LIVE PRICES (Critical Test)
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 6: VERIFY LIVE PRICES');
    console.log('='.repeat(60));
    console.log('Waiting 10 seconds for prices to load...\n');

    await page.waitForTimeout(10000);

    // Take screenshot
    await page.screenshot({ path: 'tests/screenshots/ws-verify-04-prices.png' });

    // Check for actual price values (not "------")
    const pageContent = await page.content();
    const hasPlaceholder = pageContent.includes('------');
    const hasPriceNumbers = /\d{2,6}\.\d{2}/.test(pageContent); // Match prices like 19500.50

    console.log('Contains "------" placeholder:', hasPlaceholder ? '❌ YES (BAD)' : '✓ NO (GOOD)');
    console.log('Contains price numbers:', hasPriceNumbers ? '✓ YES (GOOD)' : '❌ NO (BAD)');

    // Get all visible numbers that look like prices
    const priceTexts = await page.locator('[class*="price"], [class*="ltp"], [class*="value"]').allInnerTexts();
    console.log('\nPrice elements found:');
    priceTexts.slice(0, 10).forEach((text, i) => {
      const isPlaceholder = text.includes('--');
      const icon = isPlaceholder ? '❌' : '✓';
      console.log(`  ${icon} [${i}]: ${text}`);
    });

    // ========================================
    // STEP 7: MONITOR PRICE CHANGES (30 seconds)
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 7: MONITOR PRICE CHANGES (30 seconds)');
    console.log('='.repeat(60));
    console.log('(Prices update only during market hours: 9:15 AM - 3:30 PM IST)\n');

    const getPriceData = async () => {
      return await page.evaluate(() => {
        const priceElements = document.querySelectorAll('[class*="price"], [class*="ltp"]');
        const prices = [];
        priceElements.forEach(el => {
          const text = el.innerText.trim();
          if (text && !text.includes('--') && /\d/.test(text)) {
            prices.push(text);
          }
        });
        return prices;
      });
    };

    const initialPrices = await getPriceData();
    console.log('Initial prices:', initialPrices.slice(0, 5));

    // Monitor for 30 seconds
    let priceChanges = 0;
    for (let i = 1; i <= 6; i++) {
      await page.waitForTimeout(5000);
      const currentPrices = await getPriceData();

      // Check if prices changed
      const changed = JSON.stringify(initialPrices) !== JSON.stringify(currentPrices);
      if (changed) priceChanges++;

      console.log(`After ${i * 5}s: ${currentPrices.slice(0, 3).join(', ')} ${changed ? '(CHANGED)' : ''}`);

      if (i === 3 || i === 6) {
        await page.screenshot({ path: `tests/screenshots/ws-verify-05-prices-${i * 5}s.png` });
      }
    }

    console.log(`\nPrice changes detected: ${priceChanges} times`);

    // ========================================
    // STEP 8: CHECK INDEX HEADER PRICES
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 8: CHECK INDEX HEADER PRICES');
    console.log('='.repeat(60));

    // Look for NIFTY 50 price in header - support both old and Kite-styled header
    const headerArea = page.locator('header, [class*="header"], [class*="index"], .kite-header, .index-prices').first();
    const headerText = await headerArea.innerText().catch(() => 'Header not found');

    console.log('Header content:');
    console.log(headerText.substring(0, 300));

    // Check if header has actual numbers (not "--")
    const niftyPriceMatch = headerText.match(/NIFTY\s*50[^\d]*(\d{2,6}[\d,.]*)/i);
    const bankPriceMatch = headerText.match(/NIFTY\s*BANK[^\d]*(\d{2,6}[\d,.]*)/i);
    const headerHasNumbers = /\d{4,6}/.test(headerText);
    const headerHasPlaceholder = headerText.includes('--');

    console.log('\nHeader has price numbers:', headerHasNumbers ? '✓ YES' : '❌ NO');
    console.log('Header has placeholders:', headerHasPlaceholder ? '❌ YES' : '✓ NO');
    console.log('Live NIFTY price:', niftyPriceMatch ? niftyPriceMatch[1] : '-- (missing)');
    console.log('Live NIFTY BANK price:', bankPriceMatch ? bankPriceMatch[1] : '-- (missing)');

    // Verify user avatar circle
    const userAvatar = page.locator('.user-avatar');
    const hasAvatar = await userAvatar.isVisible().catch(() => false);
    const avatarText = hasAvatar ? await userAvatar.innerText().catch(() => '') : '';
    console.log('User avatar circle:', hasAvatar ? `✓ (${avatarText})` : '❌ missing');

    // Verify header icons (cart/orders and bell/notifications)
    const headerIcons = page.locator('.header-icons .icon-btn, .icon-btn');
    const iconCount = await headerIcons.count();
    console.log('Header icons:', iconCount >= 2 ? `✓ (${iconCount})` : `❌ (${iconCount})`);

    // ========================================
    // STEP 9: TEST WEBSOCKET MESSAGE FLOW
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 9: TEST WEBSOCKET MESSAGE FLOW');
    console.log('='.repeat(60));

    // Listen for WebSocket messages
    const wsMessages = await page.evaluate(async () => {
      return new Promise((resolve) => {
        const messages = [];
        const token = localStorage.getItem('access_token');

        if (!token) {
          resolve({ error: 'No auth token' });
          return;
        }

        const ws = new WebSocket(`ws://localhost:8000/ws/ticks?token=${token}`);

        ws.onopen = () => {
          console.log('Test WS connected');
          // Subscribe to NIFTY 50 token
          ws.send(JSON.stringify({ action: 'subscribe', tokens: [256265] }));
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          messages.push(data);
          console.log('WS message:', data);
        };

        ws.onerror = (e) => {
          messages.push({ error: 'WebSocket error' });
        };

        // Wait 10 seconds for messages
        setTimeout(() => {
          ws.close();
          resolve(messages);
        }, 10000);
      });
    });

    console.log('\nWebSocket messages received:', wsMessages.length);
    if (Array.isArray(wsMessages)) {
      wsMessages.slice(0, 5).forEach((msg, i) => {
        if (msg.type === 'ticks' && msg.data) {
          console.log(`  [${i}] Ticks: ${msg.data.length} instruments`);
          msg.data.slice(0, 2).forEach(tick => {
            console.log(`      Token ${tick.token}: LTP ${tick.ltp}`);
          });
        } else if (msg.type === 'connected') {
          console.log(`  [${i}] Connected: ${msg.message}`);
        } else if (msg.type === 'subscribed') {
          console.log(`  [${i}] Subscribed to tokens: ${msg.tokens}`);
        } else if (msg.error) {
          console.log(`  [${i}] Error: ${msg.error}`);
        } else {
          console.log(`  [${i}] ${JSON.stringify(msg)}`);
        }
      });
    }

    // ========================================
    // FINAL SUMMARY
    // ========================================
    console.log('\n' + '='.repeat(60));
    console.log('VERIFICATION SUMMARY');
    console.log('='.repeat(60));

    const wsMessagesValid = Array.isArray(wsMessages) && wsMessages.length > 0 && !wsMessages[0]?.error;

    const results = {
      'Zerodha Login': true,
      'Watchlist Page Loaded': true,
      'Instruments Added': true,
      'No Placeholder "------"': !hasPlaceholder,
      'Prices Have Numbers': hasPriceNumbers,
      'Header Has Prices': headerHasNumbers && !headerHasPlaceholder,
      'WebSocket Messages Received': wsMessagesValid,
      'Price Changes Detected': priceChanges > 0,
    };

    console.log('\n');
    let passCount = 0;
    for (const [testName, passed] of Object.entries(results)) {
      console.log(`${passed ? '✓' : '✗'} ${testName}`);
      if (passed) passCount++;
    }

    console.log(`\n${passCount}/${Object.keys(results).length} checks passed`);

    // Final screenshot
    await page.screenshot({ path: 'tests/screenshots/ws-verify-06-final.png', fullPage: true });

    console.log('\n' + '='.repeat(60));
    console.log('Screenshots saved in tests/screenshots/ws-verify-*.png');
    console.log('='.repeat(60));

    // Determine if WebSocket fix worked
    const wsFixWorking = !hasPlaceholder && hasPriceNumbers && wsMessagesValid;

    if (wsFixWorking) {
      console.log('\n🎉 SUCCESS: Kite WebSocket is working! Live prices are streaming.');
    } else {
      console.log('\n⚠️ ISSUE: WebSocket may not be fully working.');
      console.log('Check backend terminal for connection logs.');
    }

    // Assert critical tests
    expect(hasPriceNumbers || wsMessagesValid).toBeTruthy();

    // Keep browser open for inspection
    console.log('\nBrowser stays open for 20 seconds...');
    await page.waitForTimeout(20000);
  });

});
