/**
 * Broker Upgrade Banner Edge Case Tests
 *
 * Tests BrokerUpgradeBanner behavior on screens that display it:
 * - Dashboard, Watchlist, OptionChain, Positions
 *
 * Scenarios:
 * - Banner visible when user uses platform (default)
 * - Banner settings link navigates to /settings
 * - Banner can be dismissed (hides after dismiss)
 * - DataSourceBadge shows active source label
 *
 * NOTE: Uses mocked API responses.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { BrokerSettingsPage } from '../../pages/BrokerSettingsPage.js';

const SCREENS_WITH_BANNER = [
  { screen: 'dashboard', url: '/dashboard', testId: 'dashboard-page' },
  { screen: 'watchlist', url: '/watchlist', testId: 'watchlist-page' },
];

/**
 * Mock preferences to return platform (banner should show)
 */
async function mockPlatformPreferences(page) {
  await page.route('**/api/user/preferences/**', route => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          market_data_source: 'platform',
          order_broker: null,
        }),
      });
    } else {
      route.continue();
    }
  });
}

/**
 * Mock preferences to return user-specific broker (banner may hide)
 */
async function mockUserBrokerPreferences(page, broker = 'dhan') {
  await page.route('**/api/user/preferences/**', route => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          market_data_source: broker,
          order_broker: broker,
        }),
      });
    } else {
      route.continue();
    }
  });
}

test.describe('Broker Upgrade Banner - Edge Cases @edge', () => {
  test.describe('Dashboard banner', () => {
    test('upgrade banner is present on dashboard with platform data source', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await authenticatedPage.goto((process.env.FRONTEND_URL || 'http://localhost:5173') + '/dashboard');
      await authenticatedPage.waitForLoadState('domcontentloaded');

      const banner = helper.upgradeBanner('dashboard');
      await expect(banner).toBeVisible();
    });

    test('settings link in dashboard banner navigates to /settings', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await authenticatedPage.goto((process.env.FRONTEND_URL || 'http://localhost:5173') + '/dashboard');
      await authenticatedPage.waitForLoadState('domcontentloaded');

      await helper.clickBannerSettingsLink('dashboard');
      await authenticatedPage.waitForURL('**/settings**');
      expect(authenticatedPage.url()).toContain('/settings');
    });

    test('dismiss button hides the dashboard banner', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await authenticatedPage.goto((process.env.FRONTEND_URL || 'http://localhost:5173') + '/dashboard');
      await authenticatedPage.waitForLoadState('domcontentloaded');

      const banner = helper.upgradeBanner('dashboard');
      await expect(banner).toBeVisible();
      await helper.dismissBanner('dashboard');
      await expect(banner).not.toBeVisible();
    });
  });

  test.describe('Watchlist banner', () => {
    test('upgrade banner is present on watchlist with platform data source', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await authenticatedPage.goto((process.env.FRONTEND_URL || 'http://localhost:5173') + '/watchlist');
      await authenticatedPage.waitForLoadState('domcontentloaded');

      const banner = helper.upgradeBanner('watchlist');
      await expect(banner).toBeVisible();
    });

    test('dismiss button hides the watchlist banner', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await authenticatedPage.goto((process.env.FRONTEND_URL || 'http://localhost:5173') + '/watchlist');
      await authenticatedPage.waitForLoadState('domcontentloaded');

      await helper.dismissBanner('watchlist');
      await expect(helper.upgradeBanner('watchlist')).not.toBeVisible();
    });
  });

  test.describe('Broker Settings - Save error handling', () => {
    test('shows error message when save fails', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);

      // First GET succeeds
      let callCount = 0;
      await authenticatedPage.route('**/api/user/preferences/**', route => {
        const method = route.request().method();
        if (method === 'GET') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ market_data_source: 'platform', order_broker: null }),
          });
        } else if (method === 'PUT') {
          // Simulate a server error on save
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Internal server error' }),
          });
        } else {
          route.continue();
        }
      });

      await helper.navigate();
      await helper.waitForPageLoad();

      await helper.selectMarketDataSource('upstox');
      await helper.save();
      await expect(helper.saveError).toBeVisible();
    });
  });

  test.describe('Broker Settings - Market data source options completeness', () => {
    test('platform option is first market data source', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await helper.navigate();
      await helper.waitForPageLoad();

      const firstOption = helper.marketDataSelect.locator('option').first();
      const value = await firstOption.getAttribute('value');
      expect(value).toBe('platform');
    });

    test('kite option is available in market data source', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await helper.navigate();
      await helper.waitForPageLoad();

      // Check kite option exists in market data select
      const kiteOption = helper.marketDataSelect.locator('option[value="kite"]');
      await expect(kiteOption).toHaveCount(1);
    });

    test('not-configured option is first in order broker select', async ({ authenticatedPage }) => {
      const helper = new BrokerSettingsPage(authenticatedPage);
      await mockPlatformPreferences(authenticatedPage);
      await helper.navigate();
      await helper.waitForPageLoad();

      const firstOption = helper.orderBrokerSelect.locator('option').first();
      const value = await firstOption.getAttribute('value');
      expect(value).toBe('');
    });
  });
});
