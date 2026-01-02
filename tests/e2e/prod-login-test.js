/**
 * Production Login Test - Test Kite OAuth on algochanakya.com
 *
 * This standalone script tests the Kite login flow on production.
 * Run with: node tests/e2e/prod-login-test.js
 *
 * Prerequisites:
 * - tests/config/credentials.js with Kite User ID and Password
 * - TOTP authenticator app ready for manual code entry
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Production URLs
const PROD_FRONTEND_URL = 'https://algochanakya.com';
const PROD_API_BASE = 'https://algochanakya.com';

// Auth state files for production (separate from dev)
const AUTH_STATE_PATH = path.join(__dirname, '../config/.auth-state-prod.json');
const TOKEN_FILE = path.join(__dirname, '../config/.auth-token-prod');

// Load credentials
let credentials = null;
try {
  const module = await import('../config/credentials.js');
  credentials = module.credentials;
} catch (e) {
  console.log('No credentials.js found - will need manual login');
}

/**
 * Check if existing production auth state is valid
 */
async function isAuthStateValid() {
  try {
    // Check if token file exists
    if (!fs.existsSync(TOKEN_FILE)) {
      console.log('No production token file found');
      return false;
    }

    const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
    if (!token) {
      console.log('Production token file is empty');
      return false;
    }

    // Step 1: Validate JWT token with production API
    console.log('Validating JWT token with production API...');
    const response = await fetch(`${PROD_API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      console.log('Production JWT token is expired or invalid');
      return false;
    }

    const userData = await response.json();
    console.log(`JWT valid for user: ${userData.name || userData.email || 'Unknown'}`);

    // Step 2: Validate Kite broker access token
    console.log('Validating Kite broker token...');
    const brokerResponse = await fetch(`${PROD_API_BASE}/api/auth/broker/validate`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!brokerResponse.ok) {
      const errorData = await brokerResponse.json().catch(() => ({}));
      console.log('Kite broker token is expired or invalid:', errorData.detail || 'Unknown error');
      return false;
    }

    const brokerData = await brokerResponse.json();
    if (!brokerData.is_valid) {
      console.log('Kite broker token validation failed:', brokerData.message || 'Token invalid');
      return false;
    }

    console.log('Production auth state is valid!');
    return true;
  } catch (e) {
    console.log('Error checking production auth state:', e.message);
    return false;
  }
}

/**
 * Perform login on production
 */
async function performProductionLogin() {
  console.log('\n========================================');
  console.log('  PRODUCTION LOGIN TEST');
  console.log('  Target: ' + PROD_FRONTEND_URL);
  console.log('========================================\n');

  const browser = await chromium.launch({
    headless: false,
    args: ['--start-maximized']
  });
  const context = await browser.newContext({
    viewport: null // Use full window size
  });
  const page = await context.newPage();

  try {
    // Navigate to production login
    console.log('Navigating to production login page...');
    await page.goto(PROD_FRONTEND_URL + '/login');
    await page.waitForLoadState('networkidle');
    console.log('Login page loaded');

    // Pre-flight check: verify production API is working
    const apiCheck = await page.evaluate(async (apiBase) => {
      try {
        const resp = await fetch(apiBase + '/api/auth/zerodha/login');
        return await resp.json();
      } catch (e) {
        return { error: e.message };
      }
    }, PROD_API_BASE);
    console.log('API pre-check:', JSON.stringify(apiCheck));

    if (!apiCheck.login_url) {
      console.error('Production API check failed!');
      if (apiCheck.error) {
        console.error('Error:', apiCheck.error);
      }
    }

    // Click Zerodha login
    console.log('Clicking Zerodha login button...');

    // Listen for console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Browser console error:', msg.text());
      }
    });
    page.on('pageerror', err => console.log('Page error:', err.message));

    await page.click('[data-testid="login-zerodha-button"]');

    // Wait a bit to see if there are any errors
    await page.waitForTimeout(2000);
    console.log('Current URL after click:', page.url());

    // Wait for Kite login page
    await page.waitForURL('**/kite.zerodha.com/**', { timeout: 60000 });
    console.log('Reached Kite login page');

    if (credentials?.kite?.userId && credentials?.kite?.password) {
      // Auto-fill credentials
      const userIdInput = page.locator('input[type="text"]#userid, input[name="user_id"], input[placeholder*="User"]').first();
      await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
      await userIdInput.fill(credentials.kite.userId);
      console.log(`Auto-filled User ID: ${credentials.kite.userId}`);

      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
      await passwordInput.fill(credentials.kite.password);
      console.log('Auto-filled password');

      // Click login
      const loginButton = page.locator('button[type="submit"], button:has-text("Login")').first();
      await loginButton.click();
      console.log('Clicked login button');

      // Wait for TOTP page
      console.log('\n========================================');
      console.log('  ENTER TOTP NOW (60 seconds)');
      console.log('========================================\n');
    } else {
      console.log('\n========================================');
      console.log('  COMPLETE LOGIN MANUALLY');
      console.log('  (credentials not configured)');
      console.log('========================================\n');
    }

    // Wait for callback (after TOTP) - Listen for response errors
    page.on('response', response => {
      if (response.status() >= 400) {
        console.log(`Response error: ${response.status()} ${response.url()}`);
      }
    });
    page.on('requestfailed', request => {
      console.log(`Request failed: ${request.url()} - ${request.failure()?.errorText}`);
    });

    try {
      await page.waitForURL('**/callback**', { timeout: 120000 });
      console.log('Login successful, processing callback...');
    } catch (e) {
      console.log('Current URL when failed:', page.url());
      throw e;
    }

    // Wait for redirect to production frontend
    await page.waitForURL(`${PROD_FRONTEND_URL}/**`, { timeout: 15000 });
    await page.waitForLoadState('networkidle');
    console.log('Redirected to:', page.url());

    // Extract token
    const token = await page.evaluate(() => {
      return localStorage.getItem('access_token') || localStorage.getItem('token');
    });

    if (!token) {
      throw new Error('Failed to get token after login');
    }

    // Save token to file
    const tokenDir = path.dirname(TOKEN_FILE);
    if (!fs.existsSync(tokenDir)) {
      fs.mkdirSync(tokenDir, { recursive: true });
    }
    fs.writeFileSync(TOKEN_FILE, token);
    console.log('Production token saved to:', TOKEN_FILE);

    // Save browser storage state
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log('Production auth state saved to:', AUTH_STATE_PATH);

    console.log('\n========================================');
    console.log('  PRODUCTION LOGIN SUCCESSFUL!');
    console.log('========================================\n');

    // Verify we're on dashboard or authenticated page
    const currentUrl = page.url();
    console.log('Final URL:', currentUrl);

    // Quick verification - call /api/auth/me
    const verifyResponse = await fetch(`${PROD_API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (verifyResponse.ok) {
      const userData = await verifyResponse.json();
      console.log('Verified! Logged in as:', userData.name || userData.email);
    }

  } catch (error) {
    console.error('\n========================================');
    console.error('  PRODUCTION LOGIN FAILED');
    console.error('  Error:', error.message);
    console.error('========================================\n');

    // Take screenshot on failure
    const screenshotPath = path.join(__dirname, '../config/prod-login-failure.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Screenshot saved to:', screenshotPath);

    throw error;
  } finally {
    await browser.close();
  }
}

/**
 * Main function
 */
async function main() {
  console.log('\n=== Production Kite Login Test ===\n');
  console.log('Target:', PROD_FRONTEND_URL);
  console.log('Checking existing auth state...\n');

  // Check if existing auth is valid
  const isValid = await isAuthStateValid();

  if (isValid) {
    console.log('\n========================================');
    console.log('  AUTH STATE VALID - NO LOGIN NEEDED');
    console.log('========================================\n');
    return;
  }

  // Need fresh login
  console.log('Fresh login required...\n');
  await performProductionLogin();
}

// Run
main().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
