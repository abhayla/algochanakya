/**
 * Global Setup - Runs once before all tests
 *
 * This script:
 * 1. Checks if valid auth state exists (reuse if valid)
 * 2. If not, performs login with stored credentials (only TOTP manual)
 * 3. Saves auth state for all tests to reuse
 *
 * Result: Login happens ONCE, all tests share the same session.
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const API_BASE = process.env.API_BASE || 'http://localhost:8000';
const AUTH_STATE_PATH = './tests/config/.auth-state.json';
const TOKEN_FILE = './tests/config/.auth-token';

// Load credentials
let credentials = null;
try {
  const module = await import('../config/credentials.js');
  credentials = module.credentials;
} catch (e) {
  console.log('No credentials.js found - will need manual login');
}

/**
 * Check if existing auth state is still valid
 * Validates both JWT token AND Kite broker access token
 */
async function isAuthStateValid() {
  try {
    // Check if auth state file exists
    if (!fs.existsSync(AUTH_STATE_PATH)) {
      console.log('No auth state file found');
      return false;
    }

    // Check if token file exists
    if (!fs.existsSync(TOKEN_FILE)) {
      console.log('No token file found');
      return false;
    }

    const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
    if (!token) {
      console.log('Token file is empty');
      return false;
    }

    // Step 1: Validate JWT token with API
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      console.log('Token is expired or invalid');
      return false;
    }

    console.log('JWT token is valid');

    // Step 2: Validate Kite broker access token
    // Kite tokens expire daily around 6 AM IST, so we need to check this
    const brokerResponse = await fetch(`${API_BASE}/api/auth/broker/validate`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!brokerResponse.ok) {
      const errorData = await brokerResponse.json().catch(() => ({}));
      console.log('Kite broker token is expired or invalid:', errorData.detail || 'Unknown error');
      console.log('Fresh login required to get new Kite access token');
      return false;
    }

    const brokerData = await brokerResponse.json();
    if (!brokerData.is_valid) {
      console.log('Kite broker token validation failed:', brokerData.message || 'Token invalid');
      return false;
    }

    console.log('Existing auth state is valid - reusing');
    return true;
  } catch (e) {
    console.log('Error checking auth state:', e.message);
    return false;
  }
}

/**
 * Perform login and save auth state
 */
async function performLogin() {
  console.log('\n========================================');
  console.log('  PERFORMING LOGIN (one-time setup)');
  console.log('========================================\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login
    await page.goto(FRONTEND_URL + '/login');
    await page.waitForLoadState('networkidle');

    // Click Zerodha login
    await page.click('[data-testid="login-zerodha-button"]');

    // Wait for Kite login page
    await page.waitForURL('**/kite.zerodha.com/**', { timeout: 15000 });
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

    // Wait for callback (after TOTP)
    await page.waitForURL('**/callback**', { timeout: 120000 });
    console.log('Login successful, processing callback...');

    // Wait for redirect to frontend
    await page.waitForURL(`${FRONTEND_URL}/**`, { timeout: 15000 });
    await page.waitForLoadState('networkidle');

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
    console.log('Token saved to:', TOKEN_FILE);

    // Save browser storage state (cookies, localStorage)
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log('Auth state saved to:', AUTH_STATE_PATH);

    console.log('\n========================================');
    console.log('  LOGIN COMPLETE - Ready for tests');
    console.log('========================================\n');

  } finally {
    await browser.close();
  }
}

/**
 * Global setup function - called by Playwright
 */
async function globalSetup() {
  console.log('\n--- Global Setup Started ---\n');

  // Check if existing auth is valid
  const isValid = await isAuthStateValid();

  if (!isValid) {
    // Need fresh login
    await performLogin();
  }

  console.log('\n--- Global Setup Complete ---\n');
}

export default globalSetup;
