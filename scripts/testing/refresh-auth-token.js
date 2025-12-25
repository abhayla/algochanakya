/**
 * Refresh Auth Token - Interactive Login Script
 *
 * Opens browser, performs login, waits for TOTP, and saves new token.
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const API_BASE = process.env.API_BASE || 'http://localhost:8000';
const AUTH_STATE_PATH = path.join(__dirname, '../../tests/config/.auth-state.json');
const TOKEN_FILE = path.join(__dirname, '../../tests/config/.auth-token');

// Load credentials if available
let credentials = null;
try {
  const module = await import('../../tests/config/credentials.js');
  credentials = module.credentials;
  console.log('✓ Credentials loaded from credentials.js');
} catch (e) {
  console.log('ℹ No credentials.js found - will need manual login');
}

async function refreshToken() {
  console.log('\n========================================');
  console.log('  AUTH TOKEN REFRESH');
  console.log('========================================\n');

  const browser = await chromium.launch({
    headless: false,
    args: ['--start-maximized']
  });

  const context = await browser.newContext({
    viewport: null
  });

  const page = await context.newPage();

  try {
    // Navigate to login
    console.log('→ Navigating to login page...');
    await page.goto(FRONTEND_URL + '/login');
    await page.waitForLoadState('networkidle');

    // Click Zerodha login button
    console.log('→ Clicking Zerodha login button...');
    await page.click('[data-testid="login-zerodha-button"]');

    // Wait for Kite login page
    await page.waitForURL('**/kite.zerodha.com/**', { timeout: 15000 });
    console.log('✓ Reached Kite login page');

    if (credentials?.kite?.userId && credentials?.kite?.password) {
      // Auto-fill credentials
      console.log('→ Auto-filling credentials...');

      const userIdInput = page.locator('input[type="text"]#userid, input[name="user_id"], input[placeholder*="User"]').first();
      await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
      await userIdInput.fill(credentials.kite.userId);
      console.log(`  ✓ User ID: ${credentials.kite.userId}`);

      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
      await passwordInput.fill(credentials.kite.password);
      console.log('  ✓ Password filled');

      // Click login
      const loginButton = page.locator('button[type="submit"], button:has-text("Login")').first();
      await loginButton.click();
      console.log('  ✓ Login button clicked');
    } else {
      console.log('\n⚠ Credentials not configured - please login manually');
    }

    // Wait for TOTP page
    console.log('\n========================================');
    console.log('  ⏳ WAITING FOR TOTP INPUT');
    console.log('  Please enter your TOTP code in the browser');
    console.log('  Timeout: 120 seconds');
    console.log('========================================\n');

    // Wait for callback (after TOTP submission)
    await page.waitForURL('**/callback**', { timeout: 120000 });
    console.log('✓ Login successful! Processing callback...');

    // Wait for redirect to frontend
    await page.waitForURL(`${FRONTEND_URL}/**`, { timeout: 15000 });
    await page.waitForLoadState('networkidle');
    console.log('✓ Redirected to frontend');

    // Extract token from localStorage
    const token = await page.evaluate(() => {
      return localStorage.getItem('access_token') || localStorage.getItem('token');
    });

    if (!token) {
      throw new Error('Failed to extract token from localStorage');
    }

    console.log('✓ Token extracted from localStorage');

    // Validate token with API
    console.log('→ Validating token with API...');
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      throw new Error(`Token validation failed: ${response.status} ${response.statusText}`);
    }

    const userData = await response.json();
    console.log(`✓ Token validated - User: ${userData.username || userData.email}`);

    // Save token to file
    const tokenDir = path.dirname(TOKEN_FILE);
    if (!fs.existsSync(tokenDir)) {
      fs.mkdirSync(tokenDir, { recursive: true });
    }
    fs.writeFileSync(TOKEN_FILE, token);
    console.log(`✓ Token saved to: ${TOKEN_FILE}`);

    // Save auth state (cookies, localStorage)
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log(`✓ Auth state saved to: ${AUTH_STATE_PATH}`);

    console.log('\n========================================');
    console.log('  ✅ TOKEN REFRESH COMPLETE');
    console.log('========================================\n');

    // Keep browser open for 5 seconds
    console.log('Keeping browser open for 5 seconds...\n');
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('\n❌ Error during token refresh:');
    console.error(error.message);
    console.error('\nKeeping browser open for debugging...');
    await page.waitForTimeout(30000);
    throw error;
  } finally {
    await browser.close();
  }
}

// Run the refresh
refreshToken().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
