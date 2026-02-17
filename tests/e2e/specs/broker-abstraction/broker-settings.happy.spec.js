/**
 * Broker Settings Happy Path Tests
 *
 * Tests normal user flows for the broker selection UI:
 * - Visiting /settings shows the broker section
 * - Market data source dropdown has 7 options (platform + 6 brokers)
 * - Order broker dropdown has 6 options
 * - Save button persists the selection
 * - Reset button reverts unsaved changes
 *
 * NOTE: These tests mock the API responses — no live broker credentials needed.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { BrokerSettingsPage } from '../../pages/BrokerSettingsPage.js';

test.describe('Broker Settings - Happy Path @happy', () => {
  let brokerPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    brokerPage = new BrokerSettingsPage(authenticatedPage);

    // Intercept preferences API calls
    await authenticatedPage.route('**/api/user/preferences/**', route => {
      const method = route.request().method();
      if (method === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            market_data_source: 'platform',
            order_broker: null,
          }),
        });
      } else if (method === 'PUT') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok' }),
        });
      } else {
        route.continue();
      }
    });

    await brokerPage.navigate();
    await brokerPage.waitForPageLoad();
  });

  test('settings page loads', async ({ authenticatedPage }) => {
    await expect(brokerPage.settingsPage).toBeVisible();
  });

  test('broker section is visible', async () => {
    await expect(brokerPage.brokerSection).toBeVisible();
  });

  test('market data select has platform + 6 broker options (7 total)', async () => {
    const options = await brokerPage.marketDataSelect.locator('option').all();
    expect(options.length).toBe(7);
  });

  test('order broker select has not-configured + 6 broker options (7 total)', async () => {
    const options = await brokerPage.orderBrokerSelect.locator('option').all();
    expect(options.length).toBe(7); // "" (not configured) + 6 brokers
  });

  test('market data select defaults to platform', async () => {
    const value = await brokerPage.marketDataSelect.inputValue();
    expect(value).toBe('platform');
  });

  test('order broker select defaults to empty (not configured)', async () => {
    const value = await brokerPage.orderBrokerSelect.inputValue();
    expect(value).toBe('');
  });

  test('can select smartapi as market data source', async () => {
    await brokerPage.selectMarketDataSource('smartapi');
    const value = await brokerPage.marketDataSelect.inputValue();
    expect(value).toBe('smartapi');
  });

  test('can select kite as order broker', async () => {
    await brokerPage.selectOrderBroker('kite');
    const value = await brokerPage.orderBrokerSelect.inputValue();
    expect(value).toBe('kite');
  });

  test('save button is visible', async () => {
    await expect(brokerPage.saveBtn).toBeVisible();
  });

  test('reset button is visible', async () => {
    await expect(brokerPage.resetBtn).toBeVisible();
  });

  test('save shows success message', async ({ authenticatedPage }) => {
    await brokerPage.selectMarketDataSource('dhan');
    await brokerPage.save();
    await expect(brokerPage.saveSuccess).toBeVisible();
  });

  test('reset reverts unsaved market data selection', async () => {
    await brokerPage.selectMarketDataSource('upstox');
    await brokerPage.reset();
    const value = await brokerPage.marketDataSelect.inputValue();
    expect(value).toBe('platform');
  });

  test('reset reverts unsaved order broker selection', async () => {
    await brokerPage.selectOrderBroker('angel');
    await brokerPage.reset();
    const value = await brokerPage.orderBrokerSelect.inputValue();
    expect(value).toBe('');
  });

  test('all six order brokers are selectable', async () => {
    const brokers = ['kite', 'angel', 'upstox', 'dhan', 'fyers', 'paytm'];
    for (const broker of brokers) {
      await brokerPage.selectOrderBroker(broker);
      const value = await brokerPage.orderBrokerSelect.inputValue();
      expect(value).toBe(broker);
    }
  });

  test('all seven market data sources are selectable', async () => {
    const sources = ['platform', 'smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm'];
    for (const source of sources) {
      await brokerPage.selectMarketDataSource(source);
      const value = await brokerPage.marketDataSelect.inputValue();
      expect(value).toBe(source);
    }
  });
});
