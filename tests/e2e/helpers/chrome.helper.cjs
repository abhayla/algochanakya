/**
 * Chrome Testing Helper
 * Utilities for Claude Chrome integration with AlgoChanakya
 *
 * This file provides helper functions for:
 * - Auth token management
 * - URL generation
 * - Token validation
 * - localStorage injection scripts
 */

const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
  baseUrl: 'http://localhost:5173',
  authTokenPath: path.join(__dirname, '../../config/.auth-token'),
  authStatePath: path.join(__dirname, '../../config/.auth-state.json'),
};

/**
 * Get authentication token from stored file
 * @returns {string|null} JWT token or null if not found
 */
function getAuthToken() {
  try {
    if (fs.existsSync(CONFIG.authTokenPath)) {
      return fs.readFileSync(CONFIG.authTokenPath, 'utf-8').trim();
    }
  } catch (error) {
    console.error('Error reading auth token:', error);
  }
  return null;
}

/**
 * Check if JWT token is expired
 * @param {string} token - JWT token to validate
 * @returns {boolean} true if expired or invalid, false if still valid
 */
function isTokenExpired(token) {
  if (!token) return true;

  try {
    // JWT format: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      return true; // Invalid format
    }

    // Decode payload (base64)
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf-8'));

    // Check expiry timestamp
    if (!payload.exp) {
      return true; // No expiry field
    }

    // Compare with current time (exp is in seconds, Date.now() is in ms)
    const expiryTime = payload.exp * 1000;
    const currentTime = Date.now();

    return expiryTime < currentTime;
  } catch (error) {
    console.error('Error validating token:', error);
    return true; // Treat errors as expired
  }
}

/**
 * Generate full URL for Chrome navigation
 * @param {string} path - URL path (e.g., '/positions', '/strategy')
 * @returns {string} Full URL (e.g., 'http://localhost:5173/positions')
 */
function getUrl(path = '/dashboard') {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${CONFIG.baseUrl}${normalizedPath}`;
}

/**
 * Get localStorage injection script for Chrome
 * @param {string} token - JWT token to inject
 * @returns {string} JavaScript code to execute in browser
 */
function getAuthInjectionScript(token) {
  return `localStorage.setItem('token', '${token}');`;
}

/**
 * Get token payload (decoded) without validation
 * @param {string} token - JWT token
 * @returns {object|null} Decoded payload or null if invalid
 */
function getTokenPayload(token) {
  if (!token) return null;

  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf-8'));
    return payload;
  } catch (error) {
    console.error('Error decoding token payload:', error);
    return null;
  }
}

/**
 * Get token expiry time in human-readable format
 * @param {string} token - JWT token
 * @returns {string} Formatted expiry time or error message
 */
function getTokenExpiry(token) {
  const payload = getTokenPayload(token);
  if (!payload || !payload.exp) {
    return 'Unknown';
  }

  const expiryTime = new Date(payload.exp * 1000);
  const now = new Date();
  const diffMs = expiryTime - now;

  if (diffMs < 0) {
    return 'Expired';
  }

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  return `${diffHours}h ${diffMinutes}m`;
}

/**
 * Save auth token to file
 * @param {string} token - JWT token to save
 * @returns {boolean} true if successful, false otherwise
 */
function saveAuthToken(token) {
  try {
    const dir = path.dirname(CONFIG.authTokenPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(CONFIG.authTokenPath, token, 'utf-8');
    return true;
  } catch (error) {
    console.error('Error saving auth token:', error);
    return false;
  }
}

/**
 * Clear stored auth token
 * @returns {boolean} true if successful, false otherwise
 */
function clearAuthToken() {
  try {
    if (fs.existsSync(CONFIG.authTokenPath)) {
      fs.unlinkSync(CONFIG.authTokenPath);
    }
    return true;
  } catch (error) {
    console.error('Error clearing auth token:', error);
    return false;
  }
}

/**
 * Get all screen URLs for AlgoChanakya
 * @returns {object} Map of screen names to URLs
 */
function getScreenUrls() {
  return {
    dashboard: getUrl('/dashboard'),
    watchlist: getUrl('/watchlist'),
    positions: getUrl('/positions'),
    optionchain: getUrl('/optionchain'),
    strategy: getUrl('/strategy'),
    strategies: getUrl('/strategies'),
    autopilot: getUrl('/autopilot'),
    autopilotBuilder: getUrl('/autopilot/strategies/new'),
  };
}

/**
 * Get full authentication state from Playwright auth state file
 * This includes localStorage, sessionStorage, cookies, and indexedDB
 * @returns {object|null} Auth state object or null if not found
 */
function getAuthState() {
  try {
    if (fs.existsSync(CONFIG.authStatePath)) {
      const authStateContent = fs.readFileSync(CONFIG.authStatePath, 'utf-8');
      return JSON.parse(authStateContent);
    }
  } catch (error) {
    console.error('Error reading auth state:', error);
  }
  return null;
}

/**
 * Apply full authentication state to a Playwright page
 * This applies localStorage, sessionStorage, and cookies from auth state
 * @param {object} page - Playwright page object
 * @param {object} authState - Auth state object from getAuthState()
 * @returns {Promise<void>}
 */
async function applyAuthState(page, authState) {
  if (!authState || !authState.origins || authState.origins.length === 0) {
    throw new Error('Invalid auth state: missing origins');
  }

  const origin = authState.origins[0];

  // Apply localStorage
  if (origin.localStorage && origin.localStorage.length > 0) {
    await page.evaluate((items) => {
      items.forEach(item => {
        localStorage.setItem(item.name, item.value);
      });
    }, origin.localStorage);
  }

  // Apply sessionStorage
  if (origin.sessionStorage && origin.sessionStorage.length > 0) {
    await page.evaluate((items) => {
      items.forEach(item => {
        sessionStorage.setItem(item.name, item.value);
      });
    }, origin.sessionStorage);
  }

  // Cookies are applied via context.addCookies() in the caller
}

/**
 * Get cookies from auth state for adding to browser context
 * @param {object} authState - Auth state object from getAuthState()
 * @returns {Array} Array of cookie objects for context.addCookies()
 */
function getCookiesFromAuthState(authState) {
  if (!authState || !authState.cookies) {
    return [];
  }
  return authState.cookies;
}

// Export all functions
module.exports = {
  CONFIG,
  getAuthToken,
  isTokenExpired,
  getUrl,
  getAuthInjectionScript,
  getTokenPayload,
  getTokenExpiry,
  saveAuthToken,
  clearAuthToken,
  getScreenUrls,
  getAuthState,
  applyAuthState,
  getCookiesFromAuthState,
};
