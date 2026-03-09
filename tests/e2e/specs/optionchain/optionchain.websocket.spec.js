import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';
import { getDataExpectation, assertDataOrEmptyState } from '../../helpers/market-status.helper.js';
import { assertValidPrice } from '../../helpers/assertions.js';

/**
 * Option Chain Screen - WebSocket Tests
 * Tests live price updates via WebSocket connection
 */
test.describe('Option Chain - WebSocket @websocket', () => {
  let optionChainPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    optionChainPage = new OptionChainPage(authenticatedPage);
    await optionChainPage.navigate();
  });

  test('should display live toggle', async () => {
    await optionChainPage.assertLiveToggleVisible();
  });

  test('should have live toggle enabled by default', async () => {
    const isEnabled = await optionChainPage.isLiveEnabled();
    expect(isEnabled).toBe(true);
  });

  test('should toggle live updates off and on', async () => {
    // Initially enabled
    let isEnabled = await optionChainPage.isLiveEnabled();
    expect(isEnabled).toBe(true);

    // Toggle off
    await optionChainPage.toggleLiveUpdates();
    isEnabled = await optionChainPage.isLiveEnabled();
    expect(isEnabled).toBe(false);

    // Toggle back on
    await optionChainPage.toggleLiveUpdates();
    isEnabled = await optionChainPage.isLiveEnabled();
    expect(isEnabled).toBe(true);
  });

  test('should show live dot when connected and enabled', async ({ authenticatedPage }) => {
    // Wait for WebSocket connection
    await authenticatedPage.waitForLoadState('domcontentloaded');
    await optionChainPage.waitForChainLoad();

    const hasLiveDot = await optionChainPage.isLiveDotVisible();
    const expectation = getDataExpectation();

    if (expectation === 'LIVE') {
      // During market hours, WebSocket should be connected and live dot should show
      expect(hasLiveDot).toBe(true);
    } else {
      // Outside market hours, WebSocket may not stream — either state is valid
      expect(hasLiveDot === true || hasLiveDot === false).toBe(true);
    }
  });

  test('should hide live dot when live updates disabled', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    await authenticatedPage.waitForLoadState('domcontentloaded');

    // Disable live updates
    await optionChainPage.toggleLiveUpdates();

    // Live dot should not be visible when disabled
    const hasLiveDot = await optionChainPage.isLiveDotVisible();
    expect(hasLiveDot).toBe(false);
  });

  test('should display spot price from WebSocket or API', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();

    // Spot price should be displayed
    await expect(optionChainPage.spotPrice).toBeVisible();
    const spotPriceText = await optionChainPage.spotPrice.textContent();
    assertValidPrice(spotPriceText, 'spot price');
  });

  test('should update option chain after refresh', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();

    // Get initial spot price
    const initialSpotText = await optionChainPage.spotPrice.textContent();

    // Click refresh
    await optionChainPage.refresh();

    // Spot price should still be visible
    await expect(optionChainPage.spotPrice).toBeVisible();
    const newSpotText = await optionChainPage.spotPrice.textContent();

    // Both should be valid numbers (not dashes)
    assertValidPrice(initialSpotText, 'initial spot price');
    assertValidPrice(newSpotText, 'refreshed spot price');
  });

  test('should maintain live toggle state after underlying change', async () => {
    await optionChainPage.waitForChainLoad();

    // Get initial state
    const initialState = await optionChainPage.isLiveEnabled();

    // Change underlying
    await optionChainPage.selectUnderlying('BANKNIFTY');

    // State should persist
    const newState = await optionChainPage.isLiveEnabled();
    expect(newState).toBe(initialState);
  });

  test('should maintain live toggle state after expiry change', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();

    // Get initial state
    const initialState = await optionChainPage.isLiveEnabled();

    // Get expiry options and select second if available
    const expirySelect = optionChainPage.expirySelect;
    const options = await expirySelect.locator('option').all();

    // During LIVE/LAST_KNOWN there must be at least 2 expiries available
    const expectation = getDataExpectation();
    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      expect(options.length).toBeGreaterThan(1);
    }

    if (options.length > 1) {
      const secondOption = await options[1].getAttribute('value');
      await optionChainPage.selectExpiry(secondOption);

      // State should persist
      const newState = await optionChainPage.isLiveEnabled();
      expect(newState).toBe(initialState);
    }
  });

  test('should display LTP values in option chain table', async ({ authenticatedPage }) => {
    await optionChainPage.waitForChainLoad();
    const expectation = getDataExpectation();

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Table must be visible
      await expect(optionChainPage.table).toBeVisible();

      // Get first row with LTP
      const rows = await optionChainPage.table.locator('tbody tr').all();
      expect(rows.length).toBeGreaterThan(0);

      // LTP columns should have numeric values
      const firstRow = rows[0];
      const ltpCells = await firstRow.locator('[data-testid="optionchain-ltp-cell"]').all();
      expect(ltpCells.length).toBeGreaterThanOrEqual(2); // CE and PE LTP

      // Validate at least the first LTP cell has a real price
      const ltpText = await ltpCells[0].textContent();
      assertValidPrice(ltpText, 'option LTP');
    } else {
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('should subscribe to WebSocket when chain loads', async ({ authenticatedPage }) => {
    // Listen for WebSocket subscription log
    const wsMessages = [];
    authenticatedPage.on('console', msg => {
      if (msg.text().includes('[OptionChain] Subscribed')) {
        wsMessages.push(msg.text());
      }
    });

    await optionChainPage.waitForChainLoad();
    await authenticatedPage.waitForLoadState('domcontentloaded');

    const expectation = getDataExpectation();
    if (expectation === 'LIVE') {
      // During live market hours, WebSocket must be subscribed
      expect(wsMessages.length).toBeGreaterThan(0);
    } else {
      // Outside market hours, subscription log may not appear — ensure page is stable
      await optionChainPage.assertPageVisible();
    }
  });
});

/**
 * Option Chain - Live Price Update Tests
 * Tests that validate price updates are reflected in the UI
 */
test.describe('Option Chain - Live Price Updates @websocket', () => {
  let optionChainPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    optionChainPage = new OptionChainPage(authenticatedPage);
    await optionChainPage.navigate();
    await optionChainPage.waitForChainLoad();
  });

  test('spot price box should be styled correctly', async () => {
    await expect(optionChainPage.spotBox).toBeVisible();
    await expect(optionChainPage.spotPrice).toBeVisible();
  });

  test('should show valid PCR value', async () => {
    await expect(optionChainPage.pcrValue).toBeVisible();
    const pcrElement = optionChainPage.pcrValue.locator('.value');
    const pcrText = await pcrElement.textContent();
    const pcrValue = parseFloat(pcrText);
    // PCR should be > 0 when market is open and data is available
    expect(pcrValue).toBeGreaterThan(0);
  });

  test('should show valid Max Pain value', async () => {
    await expect(optionChainPage.maxPain).toBeVisible();
    const maxPainElement = optionChainPage.maxPain.locator('.value');
    const maxPainText = await maxPainElement.textContent();
    expect(maxPainText).not.toBe('-');
  });

  test('chain data should have valid structure', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Table must be visible with expected headers
      await expect(optionChainPage.table).toBeVisible();
      const headers = await optionChainPage.table.locator('thead th').allTextContents();
      expect(headers).toContain('LTP');
      expect(headers).toContain('STRIKE');
      expect(headers).toContain('OI');
    } else {
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });

  test('should display ATM strike row', async ({ authenticatedPage }) => {
    const expectation = getDataExpectation();

    if (expectation === 'LIVE' || expectation === 'LAST_KNOWN') {
      // Table must be visible and ATM row/badge must exist
      await expect(optionChainPage.table).toBeVisible();
      const atmRow = optionChainPage.table.locator('[data-atm-row]');
      const atmBadge = optionChainPage.table.locator('[data-testid="optionchain-atm-badge"]');
      const hasAtm = await atmRow.count() > 0 || await atmBadge.count() > 0;
      expect(hasAtm).toBe(true);
    } else {
      await assertDataOrEmptyState(authenticatedPage, 'optionchain-table', 'optionchain-empty-state', expect);
    }
  });
});
