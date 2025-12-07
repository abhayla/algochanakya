/**
 * Auth Fixture - Token Injection for Fast Test Execution
 *
 * This fixture bypasses OAuth flow by injecting a valid JWT token directly.
 * Use manual TOTP only for oauth-full-flow.spec.js tests.
 *
 * Usage:
 *   import { authFixture } from '../fixtures/auth.fixture.js';
 *   await authFixture.injectToken(page);
 */

import { test as base } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { StyleAudit } from '../helpers/style-audit.helper.js';

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const API_BASE = process.env.API_BASE || 'http://localhost:8000';
const TOKEN_FILE = path.join(process.cwd(), 'tests', 'config', '.auth-token');

// Token cache for session reuse
let cachedToken = null;
let tokenExpiry = null;

export const authFixture = {
  /**
   * Inject a valid auth token into localStorage (skip OAuth flow)
   * Uses cached token if still valid
   */
  async injectToken(page) {
    // Check if we have a valid cached token
    if (cachedToken && tokenExpiry && Date.now() < tokenExpiry) {
      await this._setTokenInPage(page, cachedToken);
      return cachedToken;
    }

    // Need to get a valid token
    const token = await this.getValidToken(page);
    await this._setTokenInPage(page, token);
    return token;
  },

  /**
   * Set token in page localStorage and reload
   */
  async _setTokenInPage(page, token) {
    await page.goto(FRONTEND_URL);
    await page.evaluate((t) => {
      localStorage.setItem('access_token', t);
      localStorage.setItem('token', t);
    }, token);
    await page.reload();
    await page.waitForLoadState('networkidle');
  },

  /**
   * Get a valid token - reads from env, file, or throws error
   */
  async getValidToken(page) {
    // First try: Use environment token if available
    const envToken = process.env.TEST_AUTH_TOKEN;
    if (envToken) {
      const isValid = await this.validateToken(page, envToken);
      if (isValid) {
        cachedToken = envToken;
        tokenExpiry = Date.now() + (8 * 60 * 60 * 1000); // 8 hours
        return envToken;
      }
    }

    // Second try: Use stored token from file
    const storedToken = this.loadStoredToken();
    if (storedToken) {
      const isValid = await this.validateToken(page, storedToken);
      if (isValid) {
        cachedToken = storedToken;
        tokenExpiry = Date.now() + (8 * 60 * 60 * 1000);
        return storedToken;
      }
    }

    // Third: Manual OAuth flow required
    throw new Error(
      'No valid auth token available. Either:\n' +
      '1. Set TEST_AUTH_TOKEN environment variable\n' +
      '2. Run: npm run test:oauth to generate a token\n' +
      '3. Create tests/config/.auth-token file with valid JWT'
    );
  },

  /**
   * Validate token by calling /api/auth/me
   */
  async validateToken(page, token) {
    try {
      const response = await page.request.get(`${API_BASE}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return response.ok();
    } catch {
      return false;
    }
  },

  /**
   * Load stored token from file
   */
  loadStoredToken() {
    try {
      if (fs.existsSync(TOKEN_FILE)) {
        return fs.readFileSync(TOKEN_FILE, 'utf8').trim();
      }
    } catch {
      return null;
    }
    return null;
  },

  /**
   * Store token to file (after manual OAuth)
   */
  storeToken(token) {
    const dir = path.dirname(TOKEN_FILE);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(TOKEN_FILE, token);
    console.log(`Token stored at: ${TOKEN_FILE}`);
  },

  /**
   * Clear cached token
   */
  clearCache() {
    cachedToken = null;
    tokenExpiry = null;
  }
};

/**
 * Extended test fixture with automatic auth injection
 *
 * Usage:
 *   import { test } from '../fixtures/auth.fixture.js';
 *   test('my test', async ({ authenticatedPage }) => {
 *     // Page is already authenticated
 *   });
 *
 *   // For style audit tests:
 *   test('audit test', async ({ auditablePage }) => {
 *     const results = await auditablePage.styleAudit.runFullAudit();
 *   });
 */
export const test = base.extend({
  // Authenticated page fixture with cleanup
  authenticatedPage: async ({ page }, use) => {
    await authFixture.injectToken(page);
    await use(page);
    // Cleanup after test: close any open modals
    await cleanupPageState(page);
  },

  // Page with StyleAudit instance attached
  auditablePage: async ({ page }, use) => {
    await authFixture.injectToken(page);
    page.styleAudit = new StyleAudit(page);
    await use(page);
    // Cleanup after test
    await cleanupPageState(page);
  },

  // Standalone StyleAudit instance
  styleAudit: async ({ page }, use) => {
    await use(new StyleAudit(page));
  },
});

/**
 * Cleanup page state between tests to prevent state pollution
 * Closes modals, dropdowns, and resets any open UI elements
 */
async function cleanupPageState(page) {
  try {
    // Close any open modals by clicking close buttons
    const closeSelectors = [
      '[data-testid*="-close"]',
      '[data-testid*="-modal"] button[aria-label="Close"]',
      '[data-testid*="modal-close"]',
      '.modal button[aria-label="Close"]',
      '[role="dialog"] button[aria-label="Close"]',
    ];

    for (const selector of closeSelectors) {
      const closeButtons = await page.locator(selector).all();
      for (const btn of closeButtons) {
        if (await btn.isVisible()) {
          await btn.click().catch(() => {});
        }
      }
    }

    // Press Escape to close any remaining modals/dropdowns
    await page.keyboard.press('Escape').catch(() => {});

    // Wait briefly for animations to complete
    await page.waitForTimeout(100);
  } catch {
    // Ignore cleanup errors - they shouldn't fail tests
  }
}

export { expect } from '@playwright/test';
