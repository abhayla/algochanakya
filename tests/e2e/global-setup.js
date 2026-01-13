/**
 * Global Setup - Runs once before all tests
 *
 * This script:
 * 1. Checks if valid auth state exists (reuse if valid)
 * 2. If not, performs login via AngelOne/SmartAPI with auto-TOTP (no manual entry needed)
 * 3. Saves auth state for all tests to reuse
 *
 * Result: Login happens ONCE, all tests share the same session.
 *
 * AngelOne/SmartAPI Authentication:
 * - Uses stored credentials from database (encrypted)
 * - Auto-generates TOTP code using pyotp
 * - No manual TOTP entry required
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const API_BASE = process.env.API_BASE || 'http://localhost:8000';
const AUTH_STATE_PATH = './tests/config/.auth-state.json';
const TOKEN_FILE = './tests/config/.auth-token';

/**
 * Check if existing auth state is still valid
 * Validates JWT token via /api/auth/me endpoint
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

    // Validate JWT token with API
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      console.log('Token is expired or invalid');
      return false;
    }

    console.log('JWT token is valid');

    // Validate SmartAPI session is active
    const smartapiResponse = await fetch(`${API_BASE}/api/smartapi/credentials`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (smartapiResponse.ok) {
      const smartapiData = await smartapiResponse.json();
      if (smartapiData.has_credentials && smartapiData.is_active) {
        console.log('SmartAPI session is active');
      } else {
        console.log('SmartAPI session needs re-authentication (will auto-refresh)');
      }
    }

    console.log('Existing auth state is valid - reusing');
    return true;
  } catch (e) {
    console.log('Error checking auth state:', e.message);
    return false;
  }
}

/**
 * Perform AngelOne/SmartAPI login
 * Uses stored credentials with auto-TOTP (no manual entry needed)
 */
async function performAngelOneLogin() {
  console.log('\n========================================');
  console.log('  PERFORMING ANGELONE/SMARTAPI LOGIN');
  console.log('  (auto-TOTP - no manual entry needed)');
  console.log('========================================\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login page
    await page.goto(FRONTEND_URL + '/login');
    await page.waitForLoadState('networkidle');
    console.log('Login page loaded');

    // Listen for console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Browser console error:', msg.text());
      }
    });
    page.on('pageerror', err => console.log('Page error:', err.message));

    // Click AngelOne login button (uses SmartAPI with auto-TOTP)
    console.log('Clicking AngelOne login button...');
    await page.click('[data-testid="login-angelone-button"]');

    // Wait for login to complete (auto-TOTP, should be fast)
    console.log('Waiting for AngelOne authentication (auto-TOTP)...');

    // Wait for either redirect to callback or error message
    try {
      await Promise.race([
        page.waitForURL('**/callback**', { timeout: 30000 }),
        page.waitForURL('**/dashboard**', { timeout: 30000 }),
        page.waitForSelector('[data-testid="login-error-message"]', { timeout: 30000 })
      ]);
    } catch (e) {
      console.log('Timeout waiting for login response');
      const errorElement = await page.$('[data-testid="login-error-message"]');
      if (errorElement) {
        const errorText = await errorElement.textContent();
        console.log('Login error:', errorText);
        throw new Error(`Login failed: ${errorText}`);
      }
      throw e;
    }

    // Check if we got an error
    const errorElement = await page.$('[data-testid="login-error-message"]');
    if (errorElement) {
      const errorText = await errorElement.textContent();
      console.log('Login error:', errorText);
      throw new Error(`Login failed: ${errorText}`);
    }

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
    console.log('  Using AngelOne/SmartAPI for market data');
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
    // Need fresh login via AngelOne/SmartAPI
    await performAngelOneLogin();
  }

  console.log('\n--- Global Setup Complete ---\n');
}

export default globalSetup;
