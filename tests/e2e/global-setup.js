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
// Dev backend uses port 8001 (production uses 8000 - NEVER use 8000 for dev)
const API_BASE = process.env.API_BASE || 'http://localhost:8001';
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
 * Perform AngelOne/SmartAPI login via direct API call.
 * Uses stored SmartAPI credentials in DB with auto-TOTP — no browser UI needed.
 * Falls back to UI-based login (broker dropdown + submit) if API call fails.
 */
async function performAngelOneLogin() {
  console.log('\n========================================');
  console.log('  PERFORMING ANGELONE/SMARTAPI LOGIN');
  console.log('  (direct API — auto-TOTP, no UI needed)');
  console.log('========================================\n');

  // --- Attempt direct API login (fastest, most reliable) ---
  try {
    console.log('Calling POST /api/auth/angelone/login with stored credentials...');
    const response = await fetch(`${API_BASE}/api/auth/angelone/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})  // empty body = use stored SmartAPI credentials + auto-TOTP
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`API login failed (${response.status}): ${text}`);
    }

    const data = await response.json();
    const token = data.access_token || data.token;
    if (!token) throw new Error('API login response missing access_token');

    console.log('API login successful');

    // Save token file
    const tokenDir = path.dirname(TOKEN_FILE);
    if (!fs.existsSync(tokenDir)) fs.mkdirSync(tokenDir, { recursive: true });
    fs.writeFileSync(TOKEN_FILE, token);
    console.log('Token saved to:', TOKEN_FILE);

    // Build auth state JSON that Playwright storageState expects
    const authState = {
      cookies: [],
      origins: [
        {
          origin: FRONTEND_URL,
          localStorage: [
            { name: 'access_token', value: token }
          ]
        }
      ]
    };
    const stateDir = path.dirname(AUTH_STATE_PATH);
    if (!fs.existsSync(stateDir)) fs.mkdirSync(stateDir, { recursive: true });
    fs.writeFileSync(AUTH_STATE_PATH, JSON.stringify(authState, null, 2));
    console.log('Auth state saved to:', AUTH_STATE_PATH);

    console.log('\n========================================');
    console.log('  LOGIN COMPLETE - Ready for tests');
    console.log('  Using AngelOne/SmartAPI for market data');
    console.log('========================================\n');
    return;
  } catch (err) {
    console.log('Direct API login failed, falling back to UI login:', err.message);
  }

  // --- Fallback: UI-based login via browser ---
  console.log('Attempting UI login (broker dropdown + submit)...');
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(FRONTEND_URL + '/login');
    await page.waitForLoadState('networkidle');
    console.log('Login page loaded');

    // Select AngelOne from broker dropdown
    await page.selectOption('[data-testid="login-broker-select"]', 'angelone');
    await page.waitForSelector('[data-testid="login-angelone-fields"]', { timeout: 5000 });

    // Fill credentials from env (set in CI / local .env.test)
    const clientId = process.env.ANGEL_CLIENT_ID;
    const pin = process.env.ANGEL_PIN;
    if (!clientId || !pin) {
      throw new Error('ANGEL_CLIENT_ID and ANGEL_PIN must be set for UI fallback login');
    }
    await page.fill('[data-testid="login-angelone-client-id"]', clientId);
    await page.fill('[data-testid="login-angelone-pin"]', pin);
    // TOTP must be provided externally (CI secret or manual)
    const totp = process.env.ANGEL_TOTP_CODE;
    if (!totp) throw new Error('ANGEL_TOTP_CODE env var required for UI fallback login');
    await page.fill('[data-testid="login-angelone-totp"]', totp);

    await page.click('[data-testid="login-submit-button"]');

    try {
      await Promise.race([
        page.waitForURL('**/dashboard**', { timeout: 35000 }),
        page.waitForSelector('[data-testid="login-error-message"]', { timeout: 35000 })
      ]);
    } catch (e) {
      throw new Error('Timeout waiting for login response');
    }

    const errorElement = await page.$('[data-testid="login-error-message"]');
    if (errorElement) {
      const errorText = await errorElement.textContent();
      throw new Error(`Login failed: ${errorText}`);
    }

    await page.waitForLoadState('networkidle');
    const token = await page.evaluate(() => localStorage.getItem('access_token') || localStorage.getItem('token'));
    if (!token) throw new Error('Failed to get token after UI login');

    const tokenDir = path.dirname(TOKEN_FILE);
    if (!fs.existsSync(tokenDir)) fs.mkdirSync(tokenDir, { recursive: true });
    fs.writeFileSync(TOKEN_FILE, token);
    await context.storageState({ path: AUTH_STATE_PATH });

    console.log('\n========================================');
    console.log('  LOGIN COMPLETE (via UI fallback)');
    console.log('========================================\n');

  } finally {
    await browser.close();
  }
}

/**
 * Pre-warm SmartAPI instrument cache
 * Downloads 185k instruments BEFORE tests run to avoid cold-start penalty
 */
async function prewarmSmartAPIInstruments(token) {
  console.log('\n--- Pre-warming SmartAPI Instrument Cache ---\n');
  console.log('This downloads 185k instruments (~20-30s) to avoid slow first API call...');

  try {
    // Call options expiries endpoint - this triggers SmartAPI instrument download
    const response = await fetch(`${API_BASE}/api/options/expiries?underlying=NIFTY`, {
      headers: { 'Authorization': `Bearer ${token}` },
      timeout: 60000
    });

    if (response.ok) {
      const data = await response.json();
      console.log(`SmartAPI instruments pre-warmed. Found ${data.expiries?.length || 0} NIFTY expiries.`);
    } else {
      console.log(`Pre-warm response: ${response.status} ${response.statusText}`);
    }
  } catch (e) {
    console.log('SmartAPI pre-warm failed (will retry on first test):', e.message);
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

  // Pre-warm SmartAPI instrument cache
  // This ensures first option chain test doesn't hit cold-start penalty
  const token = fs.existsSync(TOKEN_FILE) ? fs.readFileSync(TOKEN_FILE, 'utf8').trim() : null;
  if (token) {
    await prewarmSmartAPIInstruments(token);
  }

  console.log('\n--- Global Setup Complete ---\n');
}

export default globalSetup;
