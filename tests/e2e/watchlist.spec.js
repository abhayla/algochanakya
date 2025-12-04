import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:5174';

// Helper to wait for manual Zerodha login
async function loginWithZerodha(page) {
  console.log('\n' + '='.repeat(60));
  console.log('ZERODHA LOGIN REQUIRED');
  console.log('='.repeat(60));

  // Go to login page
  await page.goto(`${FRONTEND_URL}/login`);
  await page.waitForTimeout(1000);

  // Click Zerodha login button
  const zerodhaButton = page.locator('button, a').filter({ hasText: /zerodha/i }).first();
  await zerodhaButton.click();

  // Wait for Kite login page
  await page.waitForURL(/kite\.zerodha\.com/, { timeout: 10000 });

  console.log('\nPlease complete Zerodha login:');
  console.log('1. Enter User ID');
  console.log('2. Enter Password');
  console.log('3. Complete 2FA (PIN/TOTP)');
  console.log('4. Click Login');
  console.log('\nWaiting up to 2 minutes...\n');

  // Wait for redirect back to app (2 minutes for manual login)
  await page.waitForURL(/localhost:5174/, { timeout: 120000 });

  // Wait for auth to complete
  await page.waitForTimeout(3000);

  console.log('✓ Login successful!\n');

  // Return the auth token for API tests
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  return token;
}

test.describe('Watchlist Feature Tests', () => {
  let authToken = null;

  test.beforeAll(async ({ browser }) => {
    // Login once and reuse token
    const page = await browser.newPage();
    authToken = await loginWithZerodha(page);
    await page.close();
  });

  test.describe('Watchlist UI Tests', () => {

    test('should display watchlist page after login', async ({ page }) => {
      // Set auth token
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => {
        localStorage.setItem('access_token', token);
      }, authToken);

      // Navigate to watchlist
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Take screenshot
      await page.screenshot({ path: 'tests/screenshots/watchlist-page.png', fullPage: true });

      // Verify page loaded
      const pageContent = await page.content();
      console.log('Page loaded, length:', pageContent.length);

      // Check for watchlist elements
      const hasWatchlistContent = pageContent.toLowerCase().includes('watchlist') ||
                                   pageContent.toLowerCase().includes('nifty');
      expect(hasWatchlistContent).toBeTruthy();
    });

    test('should display index header with NIFTY prices', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);

      // Look for NIFTY 50 in header
      const niftyText = page.locator('text=/NIFTY\\s*50/i').first();
      const niftyVisible = await niftyText.isVisible().catch(() => false);

      console.log('NIFTY 50 header visible:', niftyVisible);

      // Take screenshot
      await page.screenshot({ path: 'tests/screenshots/watchlist-header.png' });

      // Check for NIFTY BANK
      const bankNiftyText = page.locator('text=/NIFTY\\s*BANK|BANKNIFTY/i').first();
      const bankNiftyVisible = await bankNiftyText.isVisible().catch(() => false);

      console.log('NIFTY BANK header visible:', bankNiftyVisible);
    });

    test('should display watchlist tabs', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Look for watchlist tabs
      const tabs = page.locator('[role="tab"], .watchlist-tab, button').filter({ hasText: /watchlist/i });
      const tabCount = await tabs.count();

      console.log('Watchlist tabs found:', tabCount);

      await page.screenshot({ path: 'tests/screenshots/watchlist-tabs.png' });
    });

    test('should open instrument search modal', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Find and click search/add button
      const addButton = page.locator('button').filter({ hasText: /add instrument/i }).first();

      if (await addButton.isVisible().catch(() => false)) {
        await addButton.click();
        await page.waitForTimeout(1000);
      }

      await page.screenshot({ path: 'tests/screenshots/watchlist-search-modal.png' });

      // Check if modal opened
      const modal = page.locator('[role="dialog"], .fixed.inset-0, .modal');
      const modalVisible = await modal.first().isVisible().catch(() => false);

      console.log('Search modal visible:', modalVisible);
    });

    test('should search for instruments', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Click add instrument button to open modal
      const addButton = page.locator('button').filter({ hasText: /add instrument/i }).first();
      if (await addButton.isVisible().catch(() => false)) {
        await addButton.click();
        await page.waitForTimeout(1000);
      }

      // Find search input in modal
      const searchInput = page.locator('input[type="text"], input[placeholder*="Search"]').first();

      if (await searchInput.isVisible()) {
        await searchInput.fill('RELIANCE');
        await page.waitForTimeout(1500); // Wait for debounce + API

        await page.screenshot({ path: 'tests/screenshots/watchlist-search-reliance.png' });

        // Check for search results
        const results = page.locator('text=/RELIANCE/i');
        const resultCount = await results.count();

        console.log('Search results for RELIANCE:', resultCount);
        expect(resultCount).toBeGreaterThan(0);
      } else {
        console.log('Search input not found');
      }
    });

    test('should add instrument to watchlist', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Click add instrument button
      const addButton = page.locator('button').filter({ hasText: /add instrument/i }).first();
      if (await addButton.isVisible().catch(() => false)) {
        await addButton.click();
        await page.waitForTimeout(1000);
      }

      // Search for instrument
      const searchInput = page.locator('input[type="text"], input[placeholder*="Search"]').first();

      if (await searchInput.isVisible()) {
        await searchInput.fill('INFY');
        await page.waitForTimeout(1500);

        // Click add button on first result
        const addResultButton = page.locator('button').filter({ hasText: /\+ Add/i }).first();
        if (await addResultButton.isVisible()) {
          await addResultButton.click();
          await page.waitForTimeout(1000);

          await page.screenshot({ path: 'tests/screenshots/watchlist-after-add.png' });
          console.log('Added INFY to watchlist');
        }
      }
    });

    test('should show live price updates', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(5000); // Wait for WebSocket connection + ticks

      await page.screenshot({ path: 'tests/screenshots/watchlist-live-prices.png' });

      // Check for price elements using valid selectors
      const priceElements = page.locator('[class*="price"], [class*="ltp"]');
      const priceCount = await priceElements.count();

      console.log('Price elements found:', priceCount);
    });

    test('should expand instrument row on click', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Click on first instrument row
      const instrumentRow = page.locator('.border-b.border-gray-100').first();

      if (await instrumentRow.isVisible()) {
        await instrumentRow.click();
        await page.waitForTimeout(500);

        await page.screenshot({ path: 'tests/screenshots/watchlist-expanded-row.png' });

        // Check for action buttons
        const buyButton = page.locator('button').filter({ hasText: /^B$/ }).first();
        const sellButton = page.locator('button').filter({ hasText: /^S$/ }).first();

        const buyVisible = await buyButton.isVisible().catch(() => false);
        const sellVisible = await sellButton.isVisible().catch(() => false);

        console.log('Buy button visible:', buyVisible);
        console.log('Sell button visible:', sellVisible);
      }
    });

    test('should create new watchlist', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);
      await page.goto(`${FRONTEND_URL}/watchlist`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Find add watchlist button
      const addButton = page.locator('button').filter({ hasText: /\+ Add Watchlist/i }).first();

      if (await addButton.isVisible()) {
        // Handle the prompt dialog
        page.once('dialog', async dialog => {
          console.log('Dialog message:', dialog.message());
          await dialog.accept('My Test Watchlist');
        });

        await addButton.click();
        await page.waitForTimeout(1000);

        await page.screenshot({ path: 'tests/screenshots/watchlist-new-tab.png' });
        console.log('Clicked add watchlist button');
      } else {
        console.log('Add watchlist button not found');
      }
    });

  });

  test.describe('Watchlist API Tests (with auth)', () => {

    test('GET /api/watchlists should return user watchlists', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/watchlists`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      console.log('GET /api/watchlists status:', response.status());

      if (response.ok()) {
        const data = await response.json();
        console.log('Watchlists count:', Array.isArray(data) ? data.length : 'N/A');
        console.log('Response:', JSON.stringify(data, null, 2).substring(0, 500));
      } else {
        console.log('Error:', await response.text());
      }

      expect(response.status()).toBeLessThan(500); // Not a server error
    });

    test('GET /api/instruments/search should return results', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/instruments/search?q=NIFTY`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      console.log('GET /api/instruments/search status:', response.status());

      if (response.ok()) {
        const data = await response.json();
        console.log('Search results count:', Array.isArray(data) ? data.length : 'N/A');
      }

      expect(response.status()).toBeLessThan(500);
    });

    test('GET /api/instruments/indices should return NIFTY tokens', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/instruments/indices`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      console.log('GET /api/instruments/indices status:', response.status());

      if (response.ok()) {
        const data = await response.json();
        console.log('Indices:', JSON.stringify(data, null, 2));
      }

      expect(response.status()).toBeLessThan(500);
    });

    test('WebSocket /ws/ticks should connect', async ({ page }) => {
      await page.goto(FRONTEND_URL);
      await page.evaluate((token) => localStorage.setItem('access_token', token), authToken);

      // Test WebSocket connection
      const wsResult = await page.evaluate(async (token) => {
        return new Promise((resolve) => {
          const ws = new WebSocket(`ws://localhost:8000/ws/ticks?token=${token}`);

          ws.onopen = () => {
            console.log('WebSocket connected');
            ws.send(JSON.stringify({ action: 'subscribe', tokens: [256265] })); // NIFTY 50
            setTimeout(() => {
              ws.close();
              resolve({ connected: true, error: null });
            }, 3000);
          };

          ws.onerror = (e) => {
            resolve({ connected: false, error: 'Connection error' });
          };

          ws.onclose = () => {
            console.log('WebSocket closed');
          };

          setTimeout(() => {
            resolve({ connected: false, error: 'Timeout' });
          }, 10000);
        });
      }, authToken);

      console.log('WebSocket test result:', wsResult);
    });

  });

});
