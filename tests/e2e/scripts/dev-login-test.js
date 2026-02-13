/**
 * Dev Login Test - Test Kite OAuth on localhost and check index prices
 *
 * Run with: node tests/e2e/dev-login-test.js
 */

import { chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Dev URLs
const DEV_FRONTEND_URL = 'http://localhost:5173';
const DEV_API_BASE = 'http://localhost:8000';

// Auth state files for dev
const AUTH_STATE_PATH = path.join(__dirname, '../config/.auth-state.json');
const TOKEN_FILE = path.join(__dirname, '../config/.auth-token');

// Load credentials
let credentials = null;
try {
  const module = await import('../config/credentials.js');
  credentials = module.credentials;
} catch (e) {
  console.log('No credentials.js found - will need manual login');
}

/**
 * Check if existing dev auth state is valid
 */
async function isAuthStateValid() {
  try {
    if (!fs.existsSync(TOKEN_FILE)) {
      console.log('No dev token file found');
      return false;
    }

    const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
    if (!token) {
      console.log('Dev token file is empty');
      return false;
    }

    console.log('Validating JWT token with dev API...');
    const response = await fetch(`${DEV_API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      console.log('Dev JWT token is expired or invalid');
      return false;
    }

    console.log('Validating Kite broker token...');
    const brokerResponse = await fetch(`${DEV_API_BASE}/api/auth/broker/validate`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!brokerResponse.ok) {
      console.log('Kite broker token is expired or invalid');
      return false;
    }

    const brokerData = await brokerResponse.json();
    if (!brokerData.is_valid) {
      console.log('Kite broker token validation failed');
      return false;
    }

    console.log('Dev auth state is valid!');
    return true;
  } catch (e) {
    console.log('Error checking dev auth state:', e.message);
    return false;
  }
}

/**
 * Perform login on dev
 */
async function performDevLogin() {
  console.log('\n========================================');
  console.log('  DEV LOGIN TEST');
  console.log('  Target: ' + DEV_FRONTEND_URL);
  console.log('========================================\n');

  const browser = await chromium.launch({
    headless: false,
    args: ['--start-maximized']
  });
  const context = await browser.newContext({ viewport: null });
  const page = await context.newPage();

  try {
    console.log('Navigating to dev login page...');
    await page.goto(DEV_FRONTEND_URL + '/login');
    await page.waitForLoadState('networkidle');
    console.log('Login page loaded');

    console.log('Clicking Zerodha login button...');
    await page.click('[data-testid="login-zerodha-button"]');

    await page.waitForURL('**/kite.zerodha.com/**', { timeout: 60000 });
    console.log('Reached Kite login page');

    if (credentials?.kite?.userId && credentials?.kite?.password) {
      const userIdInput = page.locator('input[type="text"]#userid, input[name="user_id"], input[placeholder*="User"]').first();
      await userIdInput.waitFor({ state: 'visible', timeout: 10000 });
      await userIdInput.fill(credentials.kite.userId);
      console.log(`Auto-filled User ID: ${credentials.kite.userId}`);

      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
      await passwordInput.fill(credentials.kite.password);
      console.log('Auto-filled password');

      const loginButton = page.locator('button[type="submit"], button:has-text("Login")').first();
      await loginButton.click();
      console.log('Clicked login button');

      console.log('\n========================================');
      console.log('  ENTER TOTP NOW (60 seconds)');
      console.log('========================================\n');
    }

    await page.waitForURL('**/callback**', { timeout: 120000 });
    console.log('Login successful, processing callback...');

    await page.waitForURL(`${DEV_FRONTEND_URL}/**`, { timeout: 15000 });
    await page.waitForLoadState('networkidle');

    const token = await page.evaluate(() => {
      return localStorage.getItem('access_token') || localStorage.getItem('token');
    });

    if (!token) {
      throw new Error('Failed to get token after login');
    }

    fs.writeFileSync(TOKEN_FILE, token);
    console.log('Dev token saved');

    await context.storageState({ path: AUTH_STATE_PATH });
    console.log('Dev auth state saved');

    return { browser, context, page, token };

  } catch (error) {
    console.error('Dev login failed:', error.message);
    await browser.close();
    throw error;
  }
}

/**
 * Check index prices on dashboard
 */
async function checkIndexPrices(page) {
  console.log('\n========================================');
  console.log('  CHECKING INDEX PRICES');
  console.log('========================================\n');

  // Navigate to dashboard
  await page.goto('http://localhost:5173/dashboard');
  await page.waitForLoadState('networkidle');

  // Wait for potential WebSocket data or API fallback (give it 5 seconds)
  console.log('Waiting 5 seconds for data to load...');
  await page.waitForTimeout(5000);

  // Get NIFTY 50 value
  const nifty50Element = await page.locator('[data-testid="kite-header-index-value-nifty50"]');
  const nifty50Value = await nifty50Element.textContent();

  // Get NIFTY BANK value
  const niftyBankElement = await page.locator('[data-testid="kite-header-index-value-niftybank"]');
  const niftyBankValue = await niftyBankElement.textContent();

  // Get connection status
  const statusDot = await page.locator('[data-testid="kite-header-connection-status"]');
  const isConnected = await statusDot.evaluate(el => el.classList.contains('connected'));

  console.log('Results:');
  console.log('  WebSocket Connected:', isConnected ? 'YES (green dot)' : 'NO (grey dot)');
  console.log('  NIFTY 50:', nifty50Value);
  console.log('  NIFTY BANK:', niftyBankValue);

  // Check console for errors
  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push({ type: msg.type(), text: msg.text() }));

  // Try to get more data from the page
  const indexData = await page.evaluate(() => {
    // Check if there's any tick data in the store
    const ticksData = window.__PINIA_DEVTOOLS_TOAST__?.('watchlist')?.ticks || {};
    return {
      nifty50Tick: ticksData[256265] || null,
      niftyBankTick: ticksData[260105] || null
    };
  });

  console.log('\n  Raw tick data from store:');
  console.log('    NIFTY 50 tick:', indexData.nifty50Tick || 'null/undefined');
  console.log('    NIFTY BANK tick:', indexData.niftyBankTick || 'null/undefined');

  return {
    nifty50: nifty50Value,
    niftyBank: niftyBankValue,
    isConnected
  };
}

/**
 * Main function
 */
async function main() {
  console.log('\n=== Dev Kite Login + Index Price Check ===\n');
  console.log('Target:', DEV_FRONTEND_URL);

  // Check if dev backend is running
  try {
    const healthCheck = await fetch(`${DEV_API_BASE}/api/health`);
    if (!healthCheck.ok) {
      console.error('Dev backend is not healthy!');
      process.exit(1);
    }
    console.log('Dev backend is running\n');
  } catch (e) {
    console.error('Dev backend is not running! Start it with: cd backend && python run.py');
    process.exit(1);
  }

  // Check existing auth
  const isValid = await isAuthStateValid();

  let browser, context, page, token;

  if (isValid) {
    console.log('\nAuth state valid, opening browser to check prices...\n');

    token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
    browser = await chromium.launch({ headless: false, args: ['--start-maximized'] });
    context = await browser.newContext({
      viewport: null,
      storageState: AUTH_STATE_PATH
    });
    page = await context.newPage();
  } else {
    console.log('\nFresh login required...\n');
    const result = await performDevLogin();
    browser = result.browser;
    context = result.context;
    page = result.page;
    token = result.token;
  }

  try {
    // Check index prices
    const prices = await checkIndexPrices(page);

    console.log('\n========================================');
    console.log('  SUMMARY');
    console.log('========================================');
    console.log('  NIFTY 50:', prices.nifty50 === '--' ? 'BLANK (no data)' : prices.nifty50);
    console.log('  NIFTY BANK:', prices.niftyBank === '--' ? 'BLANK (no data)' : prices.niftyBank);
    console.log('  WebSocket:', prices.isConnected ? 'Connected' : 'Disconnected');
    console.log('========================================\n');

    // Keep browser open for manual inspection
    console.log('Browser will stay open for 30 seconds for manual inspection...');
    await page.waitForTimeout(30000);

  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
