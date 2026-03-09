/**
 * Full OAuth Flow Test with Automated Credentials
 *
 * This test performs a complete OAuth flow using stored credentials.
 * Only TOTP entry is manual - you have 60 seconds to enter it.
 *
 * Setup:
 *   1. Copy tests/config/credentials.example.js to tests/config/credentials.js
 *   2. Fill in your Kite User ID and Password
 *   3. Run: npm run test:oauth:auto
 *
 * The token is saved to tests/config/.auth-token for reuse.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { kiteLogin, loginOrReuse, hasCredentials } from '../../helpers/kite-login.helper.js';
import { authFixture } from '../../fixtures/auth.fixture.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

test.describe('OAuth Full Flow - Automated @oauth', () => {

  test.beforeAll(() => {
    if (!hasCredentials()) {
      console.log('\n========================================');
      console.log('  CREDENTIALS NOT CONFIGURED');
      console.log('========================================');
      console.log('1. Copy tests/config/credentials.example.js');
      console.log('   to tests/config/credentials.js');
      console.log('2. Fill in your Kite User ID and Password');
      console.log('========================================\n');
    }
  });

  test('complete OAuth flow with stored credentials', async ({ page }) => {
    test.skip(!hasCredentials(), 'Credentials not configured');

    // Perform login - only TOTP is manual
    const token = await kiteLogin(page);

    expect(token).not.toBe('');
    expect(token.length).toBeGreaterThan(10);

    // Verify we're logged in
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/login');

    console.log('\n========================================');
    console.log('  LOGIN SUCCESSFUL');
    console.log('  Token saved for future tests');
    console.log('========================================\n');
  });

  test('verify saved token works', async ({ page }) => {
    test.skip(!hasCredentials(), 'Credentials not configured');

    // This test assumes previous test saved a token
    const storedToken = authFixture.loadStoredToken();

    if (!storedToken) {
      test.skip('No stored token - run previous test first');
      return;
    }

    // Inject token and verify it works
    await authFixture._validateTokenIsActive(page, storedToken);

    // Navigate to protected route
    await page.goto(FRONTEND_URL + '/dashboard');
    await page.waitForLoadState('networkidle');

    // Should not redirect to login
    expect(page.url()).toContain('/dashboard');
  });

  test('login or reuse existing token', async ({ page }) => {
    test.skip(!hasCredentials(), 'Credentials not configured');

    // This will use cached token if valid, otherwise perform fresh login
    const token = await loginOrReuse(page);

    expect(token).not.toBe('');

    // Verify we're authenticated
    await page.goto(FRONTEND_URL + '/dashboard');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/dashboard');
  });
});
