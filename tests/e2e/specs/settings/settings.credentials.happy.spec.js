/**
 * Settings - Tier 3 Credentials UI Tests
 *
 * Tests for the per-broker credential forms in /settings:
 * - KiteSettings (Zerodha): api_key + api_secret → OAuth
 * - UpstoxSettings: api_key + api_secret → OAuth
 * - DhanSettings: client_id + access_token (static)
 * - SmartAPISettings: client_id + pin + totp_secret → authenticate
 *
 * API calls are intercepted — no real broker credentials needed.
 *
 * Real API endpoints (from service files):
 *   GET/POST/DELETE /api/zerodha-credentials/credentials
 *   GET/POST/DELETE /api/upstox-credentials/credentials
 *   GET/POST/DELETE /api/dhan-credentials/credentials
 *   GET/POST/DELETE /api/smartapi/credentials
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

// ── Route helpers ─────────────────────────────────────────────────────────

async function stubCreds(page, urlPattern, getBody, postBody) {
  await page.route(urlPattern, route => {
    const m = route.request().method();
    if (m === 'GET') {
      route.fulfill({ status: getBody ? 200 : 404,
        contentType: 'application/json',
        body: JSON.stringify(getBody ?? { detail: 'Not found' }) });
    } else if (m === 'POST') {
      route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify(postBody ?? getBody ?? {}) });
    } else if (m === 'DELETE') {
      route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ status: 'deleted' }) });
    } else {
      route.continue();
    }
  });
}

async function navigateToSettings(page, waitTestId) {
  await page.goto(FRONTEND_URL + '/settings');
  await page.waitForSelector(`[data-testid="${waitTestId}"]`, { timeout: 10000 });
}

// ── Kite (Zerodha) ────────────────────────────────────────────────────────

test.describe('Settings - Kite (Zerodha) Credentials @happy', () => {
  test('section is visible with no saved credentials', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/zerodha-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-kite-section');
    await expect(authenticatedPage.getByTestId('settings-kite-section')).toBeVisible();
  });

  test('connect button visible when no creds saved', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/zerodha-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-kite-section');
    await expect(authenticatedPage.getByTestId('settings-kite-connect-btn')).toBeVisible();
  });

  test('edit and delete buttons visible when creds saved', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/zerodha-credentials/credentials',
      { has_credentials: true, is_active: true, api_key: 'test_key', api_secret: 'test_secret' });
    await navigateToSettings(authenticatedPage, 'settings-kite-section');
    await expect(authenticatedPage.getByTestId('settings-kite-creds-edit-btn')).toBeVisible();
    await expect(authenticatedPage.getByTestId('settings-kite-creds-delete-btn')).toBeVisible();
  });

  test('edit reveals api_key and api_secret fields', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/zerodha-credentials/credentials',
      { has_credentials: true, is_active: true, api_key: 'test_key', api_secret: 'test_secret' });
    await navigateToSettings(authenticatedPage, 'settings-kite-section');
    await authenticatedPage.getByTestId('settings-kite-creds-edit-btn').click();
    await expect(authenticatedPage.getByTestId('settings-kite-api-key')).toBeVisible();
    await expect(authenticatedPage.getByTestId('settings-kite-api-secret')).toBeVisible();
  });

  test('save triggers POST to credentials endpoint', async ({ authenticatedPage }) => {
    let postCalled = false;
    await authenticatedPage.route('**/api/zerodha-credentials/credentials', route => {
      const m = route.request().method();
      if (m === 'GET') {
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ has_credentials: true, is_active: true, api_key: 'old', api_secret: 'old' }) });
      } else if (m === 'POST') {
        postCalled = true;
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ has_credentials: true, is_active: true, api_key: 'new', api_secret: 'new' }) });
      } else { route.continue(); }
    });
    await navigateToSettings(authenticatedPage, 'settings-kite-section');
    await authenticatedPage.getByTestId('settings-kite-creds-edit-btn').click();
    await authenticatedPage.getByTestId('settings-kite-api-key').fill('new_key');
    await authenticatedPage.getByTestId('settings-kite-api-secret').fill('new_secret');
    await authenticatedPage.getByTestId('settings-kite-creds-save-btn').click();
    expect(postCalled).toBe(true);
  });

  test('cancel hides the credential form', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/zerodha-credentials/credentials',
      { has_credentials: true, is_active: true, api_key: 'k', api_secret: 's' });
    await navigateToSettings(authenticatedPage, 'settings-kite-section');
    await authenticatedPage.getByTestId('settings-kite-creds-edit-btn').click();
    await expect(authenticatedPage.getByTestId('settings-kite-api-key')).toBeVisible();
    await authenticatedPage.getByTestId('settings-kite-creds-cancel-btn').click();
    await expect(authenticatedPage.getByTestId('settings-kite-api-key')).not.toBeVisible();
  });
});

// ── Upstox ────────────────────────────────────────────────────────────────

test.describe('Settings - Upstox Credentials @happy', () => {
  test('section is visible', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/upstox-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-upstox-section');
    await expect(authenticatedPage.getByTestId('settings-upstox-section')).toBeVisible();
  });

  test('connect button visible when no OAuth token', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/upstox-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-upstox-section');
    await expect(authenticatedPage.getByTestId('settings-upstox-connect-btn')).toBeVisible();
  });

  test('edit reveals api_key and api_secret fields', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/upstox-credentials/credentials',
      { has_credentials: true, is_active: true, api_key: 'upstox_key', api_secret: 'upstox_secret' });
    await navigateToSettings(authenticatedPage, 'settings-upstox-section');
    await authenticatedPage.getByTestId('settings-upstox-creds-edit-btn').click();
    await expect(authenticatedPage.getByTestId('settings-upstox-api-key')).toBeVisible();
    await expect(authenticatedPage.getByTestId('settings-upstox-api-secret')).toBeVisible();
  });

  test('save triggers POST to credentials endpoint', async ({ authenticatedPage }) => {
    let postCalled = false;
    await authenticatedPage.route('**/api/upstox-credentials/credentials', route => {
      const m = route.request().method();
      if (m === 'GET') {
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ has_credentials: true, is_active: true, api_key: 'old', api_secret: 'old' }) });
      } else if (m === 'POST') {
        postCalled = true;
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ has_credentials: true, is_active: true, api_key: 'new', api_secret: 'new' }) });
      } else { route.continue(); }
    });
    await navigateToSettings(authenticatedPage, 'settings-upstox-section');
    await authenticatedPage.getByTestId('settings-upstox-creds-edit-btn').click();
    await authenticatedPage.getByTestId('settings-upstox-api-key').fill('new_key');
    await authenticatedPage.getByTestId('settings-upstox-api-secret').fill('new_secret');
    await authenticatedPage.getByTestId('settings-upstox-creds-save-btn').click();
    expect(postCalled).toBe(true);
  });

  test('cancel hides the credential form', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/upstox-credentials/credentials',
      { has_credentials: true, is_active: true, api_key: 'k', api_secret: 's' });
    await navigateToSettings(authenticatedPage, 'settings-upstox-section');
    await authenticatedPage.getByTestId('settings-upstox-creds-edit-btn').click();
    await expect(authenticatedPage.getByTestId('settings-upstox-api-key')).toBeVisible();
    await authenticatedPage.getByTestId('settings-upstox-creds-cancel-btn').click();
    await expect(authenticatedPage.getByTestId('settings-upstox-api-key')).not.toBeVisible();
  });
});

// ── Dhan ──────────────────────────────────────────────────────────────────

test.describe('Settings - Dhan Credentials @happy', () => {
  test('section is visible', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/dhan-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-dhan-section');
    await expect(authenticatedPage.getByTestId('settings-dhan-section')).toBeVisible();
  });

  test('inline form fields visible (client_id + access_token)', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/dhan-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-dhan-section');
    await expect(authenticatedPage.getByTestId('settings-dhan-client-id')).toBeVisible();
    await expect(authenticatedPage.getByTestId('settings-dhan-access-token')).toBeVisible();
  });

  test('save button is present', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/dhan-credentials/credentials', null);
    await navigateToSettings(authenticatedPage, 'settings-dhan-section');
    await expect(authenticatedPage.getByTestId('settings-dhan-save-btn')).toBeVisible();
  });

  test('filling fields and saving triggers POST', async ({ authenticatedPage }) => {
    let postCalled = false;
    await authenticatedPage.route('**/api/dhan-credentials/credentials', route => {
      const m = route.request().method();
      if (m === 'GET') {
        route.fulfill({ status: 404, body: '{}' });
      } else if (m === 'POST') {
        postCalled = true;
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ client_id: 'C123', access_token: 'tok', is_active: true }) });
      } else { route.continue(); }
    });
    await navigateToSettings(authenticatedPage, 'settings-dhan-section');
    await authenticatedPage.getByTestId('settings-dhan-client-id').fill('C123');
    await authenticatedPage.getByTestId('settings-dhan-access-token').fill('my_token');
    await authenticatedPage.getByTestId('settings-dhan-save-btn').click();
    expect(postCalled).toBe(true);
  });

  test('success message appears after successful save', async ({ authenticatedPage }) => {
    await authenticatedPage.route('**/api/dhan-credentials/credentials', route => {
      const m = route.request().method();
      if (m === 'GET') {
        route.fulfill({ status: 404, body: '{}' });
      } else if (m === 'POST') {
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ client_id: 'C123', access_token: 'tok', is_active: true }) });
      } else { route.continue(); }
    });
    await navigateToSettings(authenticatedPage, 'settings-dhan-section');
    await authenticatedPage.getByTestId('settings-dhan-client-id').fill('C123');
    await authenticatedPage.getByTestId('settings-dhan-access-token').fill('my_token');
    await authenticatedPage.getByTestId('settings-dhan-save-btn').click();
    await expect(authenticatedPage.getByTestId('settings-dhan-success')).toBeVisible();
  });

  test('edit button visible when creds saved', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/dhan-credentials/credentials',
      { has_credentials: true, is_active: true, client_id: 'C123', access_token: 'tok' });
    await navigateToSettings(authenticatedPage, 'settings-dhan-section');
    await expect(authenticatedPage.getByTestId('settings-dhan-edit-btn')).toBeVisible();
  });
});

// ── SmartAPI ──────────────────────────────────────────────────────────────

test.describe('Settings - SmartAPI Credentials @happy', () => {
  test('section is visible', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/smartapi/credentials',
      { has_credentials: false, is_active: false });
    await navigateToSettings(authenticatedPage, 'smartapi-settings');
    await expect(authenticatedPage.getByTestId('smartapi-settings')).toBeVisible();
  });

  test('credential form fields visible when no creds saved', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/smartapi/credentials',
      { has_credentials: false, is_active: false });
    await navigateToSettings(authenticatedPage, 'smartapi-settings');
    await expect(authenticatedPage.getByTestId('smartapi-client-id')).toBeVisible();
    await expect(authenticatedPage.getByTestId('smartapi-pin')).toBeVisible();
    await expect(authenticatedPage.getByTestId('smartapi-totp-secret')).toBeVisible();
  });

  test('save button present in form', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/smartapi/credentials',
      { has_credentials: false, is_active: false });
    await navigateToSettings(authenticatedPage, 'smartapi-settings');
    await expect(authenticatedPage.getByTestId('smartapi-save')).toBeVisible();
  });

  test('authenticate + edit + delete buttons visible when creds saved', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/smartapi/credentials',
      { has_credentials: true, is_active: true, client_id: 'A123' });
    await navigateToSettings(authenticatedPage, 'smartapi-settings');
    await expect(authenticatedPage.getByTestId('smartapi-authenticate')).toBeVisible();
    await expect(authenticatedPage.getByTestId('smartapi-edit')).toBeVisible();
    await expect(authenticatedPage.getByTestId('smartapi-delete')).toBeVisible();
  });

  test('save triggers POST to /api/smartapi/credentials', async ({ authenticatedPage }) => {
    let postCalled = false;
    await authenticatedPage.route('**/api/smartapi/credentials', route => {
      const m = route.request().method();
      if (m === 'GET') {
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ has_credentials: false }) });
      } else if (m === 'POST') {
        postCalled = true;
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ has_credentials: true }) });
      } else { route.continue(); }
    });
    await navigateToSettings(authenticatedPage, 'smartapi-settings');
    await authenticatedPage.getByTestId('smartapi-client-id').fill('A123');
    await authenticatedPage.getByTestId('smartapi-pin').fill('123456');
    await authenticatedPage.getByTestId('smartapi-totp-secret').fill('BASE32SECRET');
    await authenticatedPage.getByTestId('smartapi-save').click();
    expect(postCalled).toBe(true);
  });

  test('cancel button hides the form when editing', async ({ authenticatedPage }) => {
    await stubCreds(authenticatedPage, '**/api/smartapi/credentials',
      { has_credentials: true, is_active: true, client_id: 'A123' });
    await navigateToSettings(authenticatedPage, 'smartapi-settings');
    await authenticatedPage.getByTestId('smartapi-edit').click();
    await expect(authenticatedPage.getByTestId('smartapi-cancel')).toBeVisible();
    await authenticatedPage.getByTestId('smartapi-cancel').click();
    await expect(authenticatedPage.getByTestId('smartapi-client-id')).not.toBeVisible();
  });
});

// ── DataSourceBadge ───────────────────────────────────────────────────────

test.describe('Settings - DataSourceBadge @happy', () => {
  test('badge is visible on dashboard', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(FRONTEND_URL + '/dashboard');
    await authenticatedPage.waitForSelector('[data-testid="dashboard-data-source-badge"]',
      { timeout: 5000 });
    await expect(authenticatedPage.getByTestId('dashboard-data-source-badge')).toBeVisible();
  });

  test('badge shows a non-empty label', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(FRONTEND_URL + '/dashboard');
    await authenticatedPage.waitForSelector('[data-testid="dashboard-data-source-badge"]',
      { timeout: 5000 });
    const text = await authenticatedPage.getByTestId('dashboard-data-source-badge').textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  });

  test('badge is visible on watchlist', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(FRONTEND_URL + '/watchlist');
    await authenticatedPage.waitForSelector('[data-testid="watchlist-data-source-badge"]',
      { timeout: 5000 });
    await expect(authenticatedPage.getByTestId('watchlist-data-source-badge')).toBeVisible();
  });

  test('badge is visible on optionchain', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(FRONTEND_URL + '/optionchain');
    await authenticatedPage.waitForSelector('[data-testid="optionchain-data-source-badge"]',
      { timeout: 5000 });
    await expect(authenticatedPage.getByTestId('optionchain-data-source-badge')).toBeVisible();
  });
});
