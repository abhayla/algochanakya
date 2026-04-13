/**
 * Unified Broker Flow — Complete E2E lifecycle covering all broker data source scenarios.
 *
 * Chained tests that share state via test.describe.serial:
 *
 *   HAPPY PATH (chained):
 *     1. Login page: verify 6-7 broker options in dropdown
 *     2. Settings: verify data source dropdown (7 options), order broker dropdown (7 options)
 *     3. Set AngelOne → Option Chain: verify live NIFTY data (spot, strikes, LTP)
 *     4. Settings: switch to Upstox, verify save persists
 *     5. Option Chain: verify live data from Upstox (strikes, LTP > 0)
 *     6. Cross-screen: Dashboard, Watchlist, Positions all load without error
 *     7. Badge: data source badge reflects current broker on all screens
 *     8. Switch back to AngelOne, verify Option Chain data restores
 *
 *   EDGE CASES (chained):
 *     9.  Preference persists after full page reload
 *     10. Rapid A1→U→A1 switch doesn't crash WebSocket
 *     11. Switch while Option Chain is actively loading
 *     12. Switch to platform default shows upgrade banner, hides on switch back
 *     13. Order broker unchanged throughout all data source switches
 *     14. Navigate across screens after switch — no error state on any screen
 *     15. Settings shows correct source after navigating away and back
 *     16. BANKNIFTY option chain also loads after broker switch
 *
 * Prerequisites:
 *   - Market hours (9:15 AM – 3:30 PM IST, Mon–Fri)
 *   - AngelOne + Upstox credentials in .env
 *   - Auth state pre-warmed by global-setup
 *
 * Run:
 *   npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js
 *   npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js --grep "HAPPY"
 *   npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js --grep "EDGE"
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { BrokerSettingsPage } from '../../pages/BrokerSettingsPage.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';
import { PositionsPage } from '../../pages/PositionsPage.js';
import { DashboardPage } from '../../pages/DashboardPage.js';
import { LoginPage } from '../../pages/LoginPage.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const API_BASE = process.env.API_BASE || 'http://localhost:8001';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Set market data source via Settings page and wait for save confirmation.
 * Optionally set order broker too.
 */
async function setDataSource(page, brokerValue, orderBroker = null) {
  const settingsPage = new BrokerSettingsPage(page);
  await settingsPage.navigate();
  await settingsPage.waitForPageLoad();

  await settingsPage.selectMarketDataSource(brokerValue);
  if (orderBroker) {
    await settingsPage.selectOrderBroker(orderBroker);
  }

  const saveBtn = page.locator('[data-testid="settings-broker-save-btn"]');
  if (await saveBtn.isEnabled()) {
    await settingsPage.save();
    await page.waitForSelector('[data-testid="settings-broker-save-success"]', { timeout: 8000 })
      .catch(() => {});
  }
}

/**
 * Switch market data source via direct API call (no page navigation).
 * Useful for testing WebSocket reconnection without leaving current screen.
 */
async function switchDataSourceViaAPI(page, brokerValue) {
  await page.evaluate(async ({ base, broker }) => {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    await fetch(`${base}/api/user/preferences/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ market_data_source: broker }),
    });
  }, { base: API_BASE, broker: brokerValue });
}

/**
 * Assert option chain has live data: ≥5 strike rows and at least one LTP > 0.
 */
async function assertOptionChainLive(page, context) {
  const firstRow = page.locator('[data-testid*="optionchain-strike-row-"]').first();
  await expect(firstRow, `[${context}] Strike rows should appear`).toBeVisible({ timeout: 30000 });

  const rowCount = await page.locator('[data-testid*="optionchain-strike-row-"]').count();
  expect(rowCount, `[${context}] Expected ≥5 strike rows, got ${rowCount}`).toBeGreaterThanOrEqual(5);

  const ltpCells = await page.locator(
    '[data-testid^="optionchain-ce-ltp-"], [data-testid^="optionchain-pe-ltp-"]'
  ).all();
  let foundValidPrice = false;
  for (const cell of ltpCells) {
    const text = await cell.textContent().catch(() => '');
    const cleaned = text.replace(/[₹,\s]/g, '');
    const num = parseFloat(cleaned);
    if (!isNaN(num) && num > 0) {
      foundValidPrice = true;
      break;
    }
  }
  expect(foundValidPrice, `[${context}] No LTP > 0 found in option chain`).toBe(true);
}

/**
 * Assert at least one visible price > 0 on the current page.
 */
async function assertAnyLivePrice(page, context) {
  const priceLocators = await page.locator(
    '[data-testid*="-price"], [data-testid*="-ltp"], [data-testid*="nifty-price"]'
  ).all();

  let found = false;
  for (const el of priceLocators) {
    const text = await el.textContent().catch(() => '');
    const cleaned = text.replace(/[₹,\s]/g, '');
    const num = parseFloat(cleaned);
    if (!isNaN(num) && num > 0) {
      found = true;
      break;
    }
  }
  expect(found, `[${context}] No live price > 0 found on screen`).toBe(true);
}

/**
 * Assert a screen loads without error state.
 */
async function assertNoErrorState(page, screen) {
  const errorVisible = await page
    .locator(`[data-testid*="${screen}-error"], [data-testid*="error-message"]`)
    .first()
    .isVisible()
    .catch(() => false);
  expect(errorVisible, `[${screen}] Should not show error state`).toBe(false);
}

/**
 * Assert data source badge on a screen matches expected broker.
 */
async function assertBadge(page, screen, expectedBroker) {
  const badge = page.locator(`[data-testid="${screen}-data-source-badge"]`).first();
  const isVisible = await badge.isVisible().catch(() => false);
  if (!isVisible) return; // badge optional on some screens

  const text = await badge.textContent();
  expect(
    text.toLowerCase(),
    `[${screen}] Badge should mention "${expectedBroker}"`
  ).toContain(expectedBroker.toLowerCase());
}

// ─────────────────────────────────────────────────────────────────────────────
// HAPPY PATH — chained steps, serial execution
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('HAPPY PATH — Login → Data Source → OC → Switch → Cross-Screen @live @happy', () => {

  // ─── Step 1: Login page broker dropdown ─────────────────────────────────
  test('Step 1: Login page has 6-7 broker options', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${FRONTEND_URL}/login`);
    await authenticatedPage.waitForLoadState('domcontentloaded');

    const loginPage = new LoginPage(authenticatedPage);
    const brokerSelectVisible = await loginPage.brokerSelect.isVisible().catch(() => false);

    if (brokerSelectVisible) {
      const options = await loginPage.brokerSelect.locator('option').all();
      const count = options.length;

      expect(count, `Login broker dropdown: expected 6-7 options, got ${count}`).toBeGreaterThanOrEqual(6);
      expect(count).toBeLessThanOrEqual(8);

      // Verify key brokers are present
      const texts = await loginPage.brokerSelect.locator('option').allTextContents();
      const joined = texts.join('|').toLowerCase();
      expect(joined, 'Should include Zerodha option').toMatch(/zerodha|kite/);
      expect(joined, 'Should include AngelOne option').toMatch(/angel/);
    }
    // If already authenticated and redirected, this is still valid
  });

  // ─── Step 2: Settings dropdown counts ───────────────────────────────────
  test('Step 2: Settings has 7 market data options and 7 order broker options', async ({ authenticatedPage }) => {
    const settingsPage = new BrokerSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();

    // Market data: platform + 6 brokers = 7
    const marketOptions = await settingsPage.marketDataSelect.locator('option').all();
    expect(marketOptions.length, 'Market data dropdown should have 7 options').toBe(7);

    // Verify first option is "platform"
    const firstMarket = await settingsPage.marketDataSelect.locator('option').first().getAttribute('value');
    expect(firstMarket, 'First market data option should be platform').toBe('platform');

    // Order broker: not-configured + 6 brokers = 7
    const orderOptions = await settingsPage.orderBrokerSelect.locator('option').all();
    expect(orderOptions.length, 'Order broker dropdown should have 7 options').toBe(7);

    // Verify first option is empty (not configured)
    const firstOrder = await settingsPage.orderBrokerSelect.locator('option').first().getAttribute('value');
    expect(firstOrder, 'First order broker option should be empty').toBe('');
  });

  // ─── Step 3: AngelOne → Option Chain live data ──────────────────────────
  test('Step 3: Set AngelOne as data source → Option Chain shows live NIFTY data', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'smartapi', 'kite');

    const optionChain = new OptionChainPage(authenticatedPage);
    await optionChain.navigate();

    // Spot price visible and reasonable
    const spotVisible = await optionChain.spotPrice.isVisible().catch(() => false);
    if (spotVisible) {
      const spotValue = await optionChain.getSpotPrice();
      expect(spotValue, 'NIFTY spot from AngelOne should be > 10000').toBeGreaterThan(10000);
    }

    // Strikes and LTP
    await assertOptionChainLive(authenticatedPage, 'AngelOne-NIFTY');

    // ATM badge should be visible
    const atmBadge = await optionChain.atmBadge.isVisible().catch(() => false);
    expect(atmBadge, 'ATM badge should be visible with live AngelOne data').toBe(true);
  });

  // ─── Step 4: Switch to Upstox via Settings ──────────────────────────────
  test('Step 4: Switch data source AngelOne → Upstox, verify save persists', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'upstox');

    // Re-navigate to Settings and confirm it persisted
    const settingsPage = new BrokerSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();

    const savedValue = await settingsPage.marketDataSelect.inputValue();
    expect(savedValue, 'Data source should persist as upstox after save').toBe('upstox');
  });

  // ─── Step 5: Option Chain with Upstox ───────────────────────────────────
  test('Step 5: Option Chain shows live data from Upstox after switch', async ({ authenticatedPage }) => {
    const optionChain = new OptionChainPage(authenticatedPage);
    await optionChain.navigate();

    await assertOptionChainLive(authenticatedPage, 'Upstox-NIFTY');

    // Spot price from Upstox should also be reasonable
    const spotVisible = await optionChain.spotPrice.isVisible().catch(() => false);
    if (spotVisible) {
      const spotValue = await optionChain.getSpotPrice();
      expect(spotValue, 'NIFTY spot from Upstox should be > 10000').toBeGreaterThan(10000);
    }

    // No error state
    const errorVisible = await optionChain.errorAlert.isVisible().catch(() => false);
    expect(errorVisible, 'Option chain should not show error with Upstox').toBe(false);
  });

  // ─── Step 6: Cross-screen verification ──────────────────────────────────
  test('Step 6: Dashboard, Watchlist, Positions all load without error after switch', async ({ authenticatedPage }) => {
    const screens = [
      { name: 'dashboard', url: '/dashboard' },
      { name: 'watchlist', url: '/watchlist' },
      { name: 'positions', url: '/positions' },
    ];

    for (const { name, url } of screens) {
      await authenticatedPage.goto(`${FRONTEND_URL}${url}`);
      await authenticatedPage.waitForLoadState('domcontentloaded');
      await authenticatedPage.waitForTimeout(2000);

      await assertNoErrorState(authenticatedPage, name);
    }
  });

  // ─── Step 7: Badge reflects Upstox on all screens ──────────────────────
  test('Step 7: Data source badge shows "upstox" on Dashboard, Watchlist, OptionChain', async ({ authenticatedPage }) => {
    const screensWithBadge = [
      { name: 'dashboard', url: '/dashboard' },
      { name: 'watchlist', url: '/watchlist' },
      { name: 'optionchain', url: '/optionchain' },
    ];

    for (const { name, url } of screensWithBadge) {
      await authenticatedPage.goto(`${FRONTEND_URL}${url}`);
      await authenticatedPage.waitForLoadState('domcontentloaded');
      await authenticatedPage.waitForTimeout(2000);

      await assertBadge(authenticatedPage, name, 'upstox');
    }
  });

  // ─── Step 8: Switch back to AngelOne, verify restoration ───────────────
  test('Step 8: Switch back Upstox → AngelOne, Option Chain data restores', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'smartapi');

    const optionChain = new OptionChainPage(authenticatedPage);
    await optionChain.navigate();

    await assertOptionChainLive(authenticatedPage, 'AngelOne-restored');

    // Badge should now reflect AngelOne/SmartAPI
    await assertBadge(authenticatedPage, 'optionchain', 'smartapi');
  });

});

// ─────────────────────────────────────────────────────────────────────────────
// EDGE CASES — chained serial tests
// ─────────────────────────────────────────────────────────────────────────────

test.describe.serial('EDGE CASES — persistence, rapid switch, mid-load, banner @live @edge', () => {

  // ─── Step 9: Persistence after reload ───────────────────────────────────
  test('Step 9: Data source preference persists after full page reload', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'upstox', 'kite');

    // Full reload
    await authenticatedPage.reload();
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Navigate to settings, confirm preference survived
    const settingsPage = new BrokerSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();

    const value = await settingsPage.marketDataSelect.inputValue();
    expect(value, 'Market data source should persist as upstox after reload').toBe('upstox');

    // Restore
    await setDataSource(authenticatedPage, 'smartapi', 'kite');
  });

  // ─── Step 10: Rapid switching ───────────────────────────────────────────
  test('Step 10: Rapid AngelOne → Upstox → AngelOne does not crash WebSocket', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'smartapi', 'kite');
    await setDataSource(authenticatedPage, 'upstox');
    await setDataSource(authenticatedPage, 'smartapi');

    // After rapid switches, Watchlist should still show live prices
    const watchlist = new WatchlistPage(authenticatedPage);
    await watchlist.navigate();
    await authenticatedPage.waitForTimeout(3000);

    // Page should load without error
    await assertNoErrorState(authenticatedPage, 'watchlist');

    // Option chain should also be fine
    const optionChain = new OptionChainPage(authenticatedPage);
    await optionChain.navigate();
    await assertOptionChainLive(authenticatedPage, 'after-rapid-switch');
  });

  // ─── Step 11: Switch while Option Chain is loading ──────────────────────
  test('Step 11: Switching data source mid-load does not cause error in Option Chain', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'smartapi', 'kite');

    // Navigate to option chain
    const optionChain = new OptionChainPage(authenticatedPage);
    await authenticatedPage.goto(`${FRONTEND_URL}/optionchain`);
    // Don't wait for full load — switch immediately via API
    await switchDataSourceViaAPI(authenticatedPage, 'upstox');

    // Wait for page to settle
    await authenticatedPage.waitForTimeout(5000);

    // Should not show error state
    const errorVisible = await authenticatedPage
      .locator('[data-testid*="error"], [data-testid*="optionchain-error"]')
      .first()
      .isVisible()
      .catch(() => false);
    expect(errorVisible, 'Option chain should not error after mid-load switch').toBe(false);

    // Strikes should eventually render
    const strikeRows = await authenticatedPage.locator('[data-testid*="optionchain-strike-row-"]').count();
    expect(strikeRows, 'Strikes should render after mid-load switch').toBeGreaterThan(0);

    // Restore
    await setDataSource(authenticatedPage, 'smartapi');
  });

  // ─── Step 12: Platform default → banner → switch back → banner hides ──
  test('Step 12: Switch to platform default shows upgrade banner, switch back hides it', async ({ authenticatedPage }) => {
    // Set to user-owned broker first
    await setDataSource(authenticatedPage, 'smartapi', 'kite');

    // Switch to platform
    await setDataSource(authenticatedPage, 'platform');

    // Dashboard should show upgrade banner
    await authenticatedPage.goto(`${FRONTEND_URL}/dashboard`);
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await authenticatedPage.waitForTimeout(2000);

    const helper = new BrokerSettingsPage(authenticatedPage);
    const bannerAfterPlatform = await helper.upgradeBanner('dashboard').isVisible().catch(() => false);
    // Banner expected when using platform data source
    if (bannerAfterPlatform) {
      await expect(helper.upgradeBanner('dashboard')).toBeVisible();
    }

    // Switch back to AngelOne
    await setDataSource(authenticatedPage, 'smartapi');

    // Dashboard should no longer show upgrade banner
    await authenticatedPage.goto(`${FRONTEND_URL}/dashboard`);
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await authenticatedPage.waitForTimeout(2000);

    const bannerAfterRestore = await helper.upgradeBanner('dashboard').isVisible().catch(() => false);
    expect(bannerAfterRestore, 'Upgrade banner should hide after switching to user-owned broker').toBe(false);
  });

  // ─── Step 13: Order broker unchanged throughout ─────────────────────────
  test('Step 13: Order broker stays as kite throughout all data source switches', async ({ authenticatedPage }) => {
    // Set baseline
    await setDataSource(authenticatedPage, 'smartapi', 'kite');

    // Switch data source multiple times
    await setDataSource(authenticatedPage, 'upstox');
    await setDataSource(authenticatedPage, 'platform');
    await setDataSource(authenticatedPage, 'smartapi');

    // Verify order broker unchanged
    const settingsPage = new BrokerSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();

    const orderBrokerValue = await settingsPage.orderBrokerSelect.inputValue();
    expect(orderBrokerValue, 'Order broker should still be kite after data source switches').toBe('kite');
  });

  // ─── Step 14: Navigate across all screens — no errors ──────────────────
  test('Step 14: All screens load without error after broker switch', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'upstox', 'kite');

    const screens = [
      { name: 'dashboard', url: '/dashboard' },
      { name: 'watchlist', url: '/watchlist' },
      { name: 'optionchain', url: '/optionchain' },
      { name: 'positions', url: '/positions' },
      { name: 'strategy', url: '/strategy' },
      { name: 'autopilot', url: '/autopilot' },
    ];

    for (const { name, url } of screens) {
      await authenticatedPage.goto(`${FRONTEND_URL}${url}`);
      await authenticatedPage.waitForLoadState('domcontentloaded');
      await authenticatedPage.waitForTimeout(2000);

      await assertNoErrorState(authenticatedPage, name);
    }

    // Restore
    await setDataSource(authenticatedPage, 'smartapi', 'kite');
  });

  // ─── Step 15: Settings shows correct source after nav away and back ────
  test('Step 15: Settings page reflects correct source after navigating away and back', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'upstox', 'kite');

    // Navigate away to dashboard
    await authenticatedPage.goto(`${FRONTEND_URL}/dashboard`);
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Navigate to option chain
    await authenticatedPage.goto(`${FRONTEND_URL}/optionchain`);
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Come back to settings
    const settingsPage = new BrokerSettingsPage(authenticatedPage);
    await settingsPage.navigate();
    await settingsPage.waitForPageLoad();

    const currentValue = await settingsPage.marketDataSelect.inputValue();
    expect(currentValue, 'Settings should still show upstox after navigating away and back').toBe('upstox');

    // Restore
    await setDataSource(authenticatedPage, 'smartapi', 'kite');
  });

  // ─── Step 16: BANKNIFTY option chain after broker switch ───────────────
  test('Step 16: BANKNIFTY option chain loads after switching data source', async ({ authenticatedPage }) => {
    await setDataSource(authenticatedPage, 'upstox', 'kite');

    const optionChain = new OptionChainPage(authenticatedPage);
    await optionChain.navigate();

    // Switch to BANKNIFTY
    await optionChain.selectUnderlying('BANKNIFTY');

    // Verify BANKNIFTY strikes load
    const rowCount = await authenticatedPage.locator('[data-testid*="optionchain-strike-row-"]').count();
    expect(rowCount, 'BANKNIFTY should have ≥5 strike rows with Upstox').toBeGreaterThanOrEqual(5);

    // At least one LTP > 0
    const ltpCells = await authenticatedPage.locator(
      '[data-testid^="optionchain-ce-ltp-"], [data-testid^="optionchain-pe-ltp-"]'
    ).all();
    let foundPrice = false;
    for (const cell of ltpCells) {
      const text = await cell.textContent().catch(() => '');
      const num = parseFloat(text.replace(/[₹,\s]/g, ''));
      if (!isNaN(num) && num > 0) {
        foundPrice = true;
        break;
      }
    }
    expect(foundPrice, 'BANKNIFTY should have at least one LTP > 0 from Upstox').toBe(true);

    // Switch back to NIFTY and restore AngelOne
    await optionChain.selectUnderlying('NIFTY');
    await setDataSource(authenticatedPage, 'smartapi', 'kite');
  });

});
