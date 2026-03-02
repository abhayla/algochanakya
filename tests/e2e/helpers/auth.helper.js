/**
 * Authentication Helper Functions for Playwright Tests
 *
 * These helpers provide utilities for managing authentication state
 * during testing.
 */

/**
 * Get the auth token from localStorage
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<string|null>} The auth token or null
 */
const API_BASE = process.env.API_BASE || 'http://localhost:8001';

export async function getAuthToken(page) {
  return await page.evaluate(() => localStorage.getItem('access_token'));
}

/**
 * Set the auth token in localStorage
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - JWT token to set
 */
export async function setAuthToken(page, token) {
  await page.evaluate((t) => {
    localStorage.setItem('access_token', t);
  }, token);
}

/**
 * Clear all authentication data from localStorage
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function clearAuth(page) {
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem('token'); // Alternative token key
  });
}

/**
 * Check if user is authenticated
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<boolean>} True if token exists
 */
export async function isAuthenticated(page) {
  const token = await getAuthToken(page);
  return token !== null && token !== undefined && token !== '';
}

/**
 * Get user info from API
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<object|null>} User info or null
 */
export async function getUserInfo(page) {
  const token = await getAuthToken(page);
  if (!token) return null;

  return await page.evaluate(async (tokenValue) => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${tokenValue}` }
      });

      if (response.ok) {
        return await response.json();
      }

      return null;
    } catch (err) {
      console.error('Failed to fetch user info:', err);
      return null;
    }
  }, token);
}

/**
 * Login with a given token (skip OAuth flow)
 * Useful for testing protected routes without going through full OAuth
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Valid JWT token
 */
export async function loginWithToken(page, token) {
  await page.goto('/');
  await setAuthToken(page, token);
  await page.reload();
}

/**
 * Logout by clearing auth and navigating to login
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function logout(page) {
  // Try to call logout API if authenticated
  const token = await getAuthToken(page);

  if (token) {
    try {
      await page.evaluate(async (tokenValue) => {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${tokenValue}` }
        });
      }, token);
    } catch (err) {
      console.warn('Logout API call failed:', err);
    }
  }

  // Clear local auth state
  await clearAuth(page);

  // Navigate to login
  await page.goto('/login');
}

/**
 * Wait for authentication to complete
 * Useful after OAuth callback
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 * @returns {Promise<boolean>} True if authenticated
 */
export async function waitForAuth(page, timeout = 5000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const authenticated = await isAuthenticated(page);
    if (authenticated) {
      return true;
    }
    await page.waitForLoadState('domcontentloaded');
  }

  return false;
}

/**
 * Mock auth state for testing
 * Creates a fake token and user object
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function mockAuth(page) {
  const mockToken = 'mock_jwt_token_' + Date.now();
  const mockUser = {
    id: 'mock-user-id',
    email: 'test@example.com',
    created_at: new Date().toISOString()
  };

  await page.evaluate((data) => {
    localStorage.setItem('access_token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
  }, { token: mockToken, user: mockUser });

  return { token: mockToken, user: mockUser };
}
