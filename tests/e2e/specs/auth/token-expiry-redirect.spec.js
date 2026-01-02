import { test, expect } from '@playwright/test';

/**
 * Token Expiry Redirect Test
 *
 * Tests that when Kite access token expires (401 response),
 * the app redirects to login page.
 */
test.describe('Token Expiry Redirect @auth', () => {

  test('should redirect to login when API returns 401', async ({ page }) => {
    // Set an invalid/expired token in localStorage
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'invalid_expired_token_12345');
    });

    // Try to navigate to option chain (requires auth)
    await page.goto('/optionchain');

    // Wait for the API call to fail with 401 and redirect to happen
    await page.waitForURL('**/login**', { timeout: 15000 });

    // Verify we're on login page
    expect(page.url()).toContain('/login');
  });

  test('should redirect to login when positions API returns 401', async ({ page }) => {
    // Set an invalid token
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'invalid_expired_token_12345');
    });

    // Try to navigate to positions page
    await page.goto('/positions');

    // Wait for redirect to login
    await page.waitForURL('**/login**', { timeout: 15000 });

    expect(page.url()).toContain('/login');
  });

  test('should clear token from localStorage on 401', async ({ page }) => {
    // Set an invalid token
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'invalid_expired_token_12345');
    });

    // Navigate to a protected page
    await page.goto('/optionchain');

    // Wait for redirect
    await page.waitForURL('**/login**', { timeout: 15000 });

    // Verify token was cleared
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });
});
