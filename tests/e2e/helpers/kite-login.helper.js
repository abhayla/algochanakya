/**
 * Kite Login Helper - Automated login with manual TOTP entry
 *
 * This helper automates the Kite login flow:
 * 1. Navigates to Kite login page
 * 2. Enters stored credentials (user ID + password)
 * 3. Pauses for manual TOTP entry
 * 4. Completes login and captures token
 *
 * Usage:
 *   import { kiteLogin, performFullOAuthFlow } from '../helpers/kite-login.helper.js';
 *   const token = await performFullOAuthFlow(page);
 */

import { authFixture } from '../fixtures/auth.fixture.js';

// Try to load credentials - will throw if not configured
let credentials = null;
try {
  const module = await import('../../config/credentials.js');
  credentials = module.credentials;
} catch (e) {
  console.warn('No credentials.js found. Create tests/config/credentials.js from credentials.example.js');
}

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const API_BASE = process.env.API_BASE || 'http://localhost:8000';

/**
 * Check if credentials are configured
 */
export function hasCredentials() {
  return credentials?.kite?.userId && credentials?.kite?.password;
}

/**
 * Get stored credentials
 */
export function getCredentials() {
  if (!hasCredentials()) {
    throw new Error(
      'Kite credentials not configured. Create tests/config/credentials.js from credentials.example.js'
    );
  }
  return credentials.kite;
}

/**
 * Perform Kite login with stored credentials
 * Only prompts for TOTP (manual entry)
 *
 * @param {Page} page - Playwright page object
 * @param {object} options - Options
 * @param {number} options.totpTimeout - Timeout for TOTP entry in ms (default: 60000)
 * @returns {Promise<string>} - Access token
 */
export async function kiteLogin(page, options = {}) {
  const { totpTimeout = 60000 } = options;
  const creds = getCredentials();

  console.log('Starting Kite login flow...');

  // 1. Navigate to login and initiate OAuth
  await page.goto(FRONTEND_URL + '/login');
  await page.waitForLoadState('networkidle');

  // 2. Click Zerodha login button
  await page.click('[data-testid="login-zerodha-button"]');

  // 3. Wait for Kite login page
  await page.waitForURL('**/kite.zerodha.com/**', { timeout: 15000 });
  console.log('Reached Kite login page');

  // 4. Enter User ID
  const userIdInput = page.locator('input[type="text"]#userid, input[name="user_id"], input[placeholder*="User"]').first();
  await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
  await userIdInput.fill(creds.userId);
  console.log(`Entered User ID: ${creds.userId}`);

  // 5. Enter Password
  const passwordInput = page.locator('input[type="password"]').first();
  await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
  await passwordInput.fill(creds.password);
  console.log('Entered password');

  // 6. Click Login button
  const loginButton = page.locator('button[type="submit"], button:has-text("Login")').first();
  await loginButton.click();
  console.log('Clicked login button');

  // 7. Wait for TOTP page
  await page.waitForSelector('input[type="text"][autocomplete="one-time-code"], input[type="number"], input[label*="TOTP"], input.totp-input', {
    timeout: 15000
  });
  console.log('\n========================================');
  console.log('  ENTER TOTP NOW (waiting up to 60s)');
  console.log('========================================\n');

  // 8. Wait for TOTP entry and submission (user enters manually)
  // The page will redirect after successful TOTP
  await page.waitForURL('**/callback**', { timeout: totpTimeout });
  console.log('TOTP accepted, processing callback...');

  // 9. Wait for redirect back to frontend with token
  await page.waitForURL(`${FRONTEND_URL}/**`, { timeout: 15000 });
  await page.waitForLoadState('networkidle');

  // 10. Extract and store token
  const token = await page.evaluate(() => {
    return localStorage.getItem('access_token') || localStorage.getItem('token');
  });

  if (!token) {
    throw new Error('Failed to get token after login');
  }

  console.log('Login successful! Token obtained.');

  // Store token for reuse
  authFixture.storeToken(token);

  return token;
}

/**
 * Perform full OAuth flow with credential automation
 * Convenience wrapper that handles the complete flow
 *
 * @param {Page} page - Playwright page object
 * @returns {Promise<string>} - Access token
 */
export async function performFullOAuthFlow(page) {
  return await kiteLogin(page);
}

/**
 * Login or reuse existing token
 * Tries cached token first, falls back to full login
 *
 * @param {Page} page - Playwright page object
 * @returns {Promise<string>} - Access token
 */
export async function loginOrReuse(page) {
  // Try to use existing token first
  try {
    const token = await authFixture.getValidToken(page);
    console.log('Using existing valid token');
    await authFixture._setTokenInPage(page, token);
    return token;
  } catch (e) {
    // No valid token, perform fresh login
    console.log('No valid token, performing fresh login...');
    return await kiteLogin(page);
  }
}
