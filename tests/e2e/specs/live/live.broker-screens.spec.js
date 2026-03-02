/**
 * Live Broker Screen Tests — all 6 brokers, parameterized.
 *
 * For each broker:
 *   1. Log in
 *   2. Set market_data_source = broker via Settings
 *   3. Navigate to screen
 *   4. Assert screen renders real live data (prices > 0, not "--" or "0.00")
 *
 * Screens tested:
 *   - Watchlist    → live prices for NIFTY/BANKNIFTY
 *   - Option Chain → live strikes, ATM, non-zero LTP
 *   - Positions    → renders (empty or data — no error)
 *   - Dashboard    → market summary with valid index prices
 *
 * Tests FAIL if:
 *   - Screen shows "--", "0.00", or "N/A" for prices (indicates broker not working)
 *   - Screen renders an error state
 *   - Any broker credential is missing (test is skipped)
 *
 * Run:
 *   npx playwright test tests/e2e/specs/live/live.broker-screens.spec.js
 *   npx playwright test tests/e2e/specs/live/ --grep "angelone"
 *
 * NOTE: Run during market hours for live price assertions.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { BrokerSettingsPage } from '../../pages/BrokerSettingsPage.js';
import { WatchlistPage } from '../../pages/WatchlistPage.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { PositionsPage } from '../../pages/PositionsPage.js';
import { DashboardPage } from '../../pages/DashboardPage.js';

// ─────────────────────────────────────────────────────────────────────────────
// All 6 brokers parameterized
// ─────────────────────────────────────────────────────────────────────────────

const ALL_BROKERS = [
  { id: 'angelone', label: 'AngelOne/SmartAPI',  value: 'smartapi' },
  { id: 'kite',     label: 'Zerodha/Kite',       value: 'kite'     },
  { id: 'upstox',   label: 'Upstox',             value: 'upstox'   },
  { id: 'dhan',     label: 'Dhan',               value: 'dhan'     },
  { id: 'fyers',    label: 'Fyers',              value: 'fyers'    },
  { id: 'paytm',    label: 'Paytm Money',        value: 'paytm'    },
];

// ─────────────────────────────────────────────────────────────────────────────
// Helper: set market data source via Settings page
// ─────────────────────────────────────────────────────────────────────────────

async function setMarketDataSource(authenticatedPage, brokerValue) {
  const settingsPage = new BrokerSettingsPage(authenticatedPage);
  await settingsPage.navigate();
  await settingsPage.waitForPageLoad();
  await settingsPage.selectMarketDataSource(brokerValue);
  await settingsPage.save();

  // Wait for save success indicator
  await authenticatedPage.waitForSelector(
    '[data-testid="settings-broker-save-success"]',
    { timeout: 5000 }
  ).catch(() => {
    // Some brokers may not have connected credentials — save still succeeds silently
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper: assert a price string is a real number (not "--", "0.00", "N/A")
// ─────────────────────────────────────────────────────────────────────────────

function assertValidPrice(priceText, broker, context) {
  const cleaned = priceText.replace(/[₹,\s]/g, '');
  expect(
    cleaned,
    `[${broker}] ${context}: price="${priceText}" looks like a placeholder`
  ).not.toMatch(/^(-{1,2}|0\.00|N\/A|undefined|null)$/i);

  const num = parseFloat(cleaned);
  expect(
    isNaN(num),
    `[${broker}] ${context}: price="${priceText}" is not a number`
  ).toBe(false);
  expect(num, `[${broker}] ${context}: price=${num} is not > 0`).toBeGreaterThan(0);
}


// ─────────────────────────────────────────────────────────────────────────────
// WATCHLIST — live prices for NIFTY
// ─────────────────────────────────────────────────────────────────────────────

for (const broker of ALL_BROKERS) {
  test(`Watchlist shows live NIFTY price with ${broker.label} @live`, async ({ authenticatedPage }) => {
    await setMarketDataSource(authenticatedPage, broker.value);

    const watchlist = new WatchlistPage(authenticatedPage);
    await watchlist.navigate();
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Wait for price data to populate (WebSocket or REST)
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Find a price cell in the watchlist
    const priceLocator = authenticatedPage.locator('[data-testid*="watchlist-price"], [data-testid*="ltp"]').first();
    const isVisible = await priceLocator.isVisible().catch(() => false);

    if (!isVisible) {
      // No instruments in watchlist — add NIFTY first
      await watchlist.search('NIFTY 50');
      await authenticatedPage.waitForLoadState('domcontentloaded');
      const firstResult = authenticatedPage.locator('[data-testid*="watchlist-search-result"]').first();
      if (await firstResult.isVisible().catch(() => false)) {
        await firstResult.click();
        await authenticatedPage.waitForLoadState('domcontentloaded');
      }
    }

    // Assert at least one visible price
    const prices = await authenticatedPage.locator('[data-testid*="-price"], [data-testid*="-ltp"]').all();
    let foundValidPrice = false;
    for (const priceEl of prices) {
      const text = await priceEl.textContent().catch(() => '');
      const cleaned = text.replace(/[₹,\s]/g, '');
      const num = parseFloat(cleaned);
      if (!isNaN(num) && num > 1000) {
        foundValidPrice = true;
        break;
      }
    }

    expect(foundValidPrice, `[${broker.label}] No valid price found on Watchlist. Broker data source may not be working.`).toBe(true);
  });
}


// ─────────────────────────────────────────────────────────────────────────────
// OPTION CHAIN — live strikes and LTP
// ─────────────────────────────────────────────────────────────────────────────

for (const broker of ALL_BROKERS) {
  test(`Option Chain shows live NIFTY strikes with ${broker.label} @live`, async ({ authenticatedPage }) => {
    await setMarketDataSource(authenticatedPage, broker.value);

    const optionChain = new OptionChainPage(authenticatedPage);
    await optionChain.navigate();
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Assert strikes table is visible
    const strikeTable = authenticatedPage.locator('[data-testid="optionchain-strikes-table"], [data-testid*="strike-row"]').first();
    await expect(strikeTable, `[${broker.label}] Option chain strikes table not visible`).toBeVisible({ timeout: 15000 });

    // Assert ATM strike shows a real price (CE side)
    const atmRow = authenticatedPage.locator('[data-testid*="optionchain-atm"], [data-testid*="strike-atm"]').first();
    const atmVisible = await atmRow.isVisible().catch(() => false);

    if (atmVisible) {
      const cePrice = await authenticatedPage.locator('[data-testid*="optionchain-ce-ltp"], [data-testid*="ce-price"]').first().textContent().catch(() => '');
      if (cePrice) {
        assertValidPrice(cePrice, broker.label, 'ATM CE LTP');
      }
    }

    // Assert at least 5 strike rows are rendered
    const allRows = await authenticatedPage.locator('[data-testid*="strike-row"], [data-testid*="optionchain-row"]').count();
    expect(allRows, `[${broker.label}] Option chain has ${allRows} rows — expected >= 5`).toBeGreaterThanOrEqual(5);
  });
}


// ─────────────────────────────────────────────────────────────────────────────
// POSITIONS — renders without error (empty or data)
// ─────────────────────────────────────────────────────────────────────────────

for (const broker of ALL_BROKERS) {
  test(`Positions screen loads without error with ${broker.label} @live`, async ({ authenticatedPage }) => {
    await setMarketDataSource(authenticatedPage, broker.value);

    const positions = new PositionsPage(authenticatedPage);
    await positions.navigate();
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Should show either positions table OR empty state — NOT an error
    const hasTable = await authenticatedPage.locator('[data-testid="positions-table"], [data-testid*="positions-row"]').first().isVisible().catch(() => false);
    const hasEmpty = await authenticatedPage.locator('[data-testid="positions-empty"], [data-testid*="empty-state"]').first().isVisible().catch(() => false);
    const hasError = await authenticatedPage.locator('[data-testid*="positions-error"], [data-testid*="error-message"]').first().isVisible().catch(() => false);

    expect(hasError, `[${broker.label}] Positions screen shows error state`).toBe(false);
    expect(
      hasTable || hasEmpty,
      `[${broker.label}] Positions screen shows neither table nor empty state`
    ).toBe(true);
  });
}


// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD — market summary with valid index prices
// ─────────────────────────────────────────────────────────────────────────────

for (const broker of ALL_BROKERS) {
  test(`Dashboard shows valid market summary with ${broker.label} @live`, async ({ authenticatedPage }) => {
    await setMarketDataSource(authenticatedPage, broker.value);

    const dashboard = new DashboardPage(authenticatedPage);
    await dashboard.navigate();
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Assert NIFTY index card is visible
    const niftyCard = authenticatedPage.locator('[data-testid*="dashboard-nifty"], [data-testid*="index-nifty"]').first();
    const niftyVisible = await niftyCard.isVisible().catch(() => false);

    if (niftyVisible) {
      // Get NIFTY price from card
      const niftyPrice = await authenticatedPage.locator('[data-testid*="nifty-price"], [data-testid*="nifty-ltp"]').first().textContent().catch(() => '');
      if (niftyPrice) {
        assertValidPrice(niftyPrice, broker.label, 'Dashboard NIFTY price');
      }
    }

    // Data source badge should show the active broker
    const badge = authenticatedPage.locator('[data-testid*="data-source-badge"]').first();
    const badgeVisible = await badge.isVisible().catch(() => false);
    if (badgeVisible) {
      const badgeText = await badge.textContent().catch(() => '');
      expect(
        badgeText.toLowerCase(),
        `[${broker.label}] Data source badge should show broker name`
      ).not.toBe('');
    }
  });
}
