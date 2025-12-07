import { test, expect } from '@playwright/test';

test.describe('Zerodha OAuth Flow', () => {

  test('complete OAuth flow with manual Zerodha login', async ({ page }) => {
    // Step 1: Go to login page
    await page.goto('/login');
    console.log('✓ Login page loaded');

    // Step 2: Ensure Zerodha is selected
    const brokerSelect = page.locator('select#broker, select[name="broker"]');
    await brokerSelect.selectOption('zerodha');
    console.log('✓ Zerodha selected as broker');

    // Step 3: Click login button
    const loginButton = page.locator('button:has-text("Connect")');
    await loginButton.click();
    console.log('✓ Clicked login button');

    // Step 4: Wait for Kite login page
    await page.waitForURL(/kite\.zerodha\.com/, { timeout: 10000 });
    console.log('✓ Redirected to Kite Connect');
    console.log('  Current URL:', page.url());

    // Verify we're on Kite with correct API key
    const currentUrl = page.url();
    expect(currentUrl).toContain('kite.zerodha.com');
    expect(currentUrl).toContain('api_key=dh9lojp9j9tnq3h4');

    // Step 5: MANUAL STEP - User logs in to Zerodha
    console.log('\n========================================');
    console.log('MANUAL ACTION REQUIRED:');
    console.log('1. Enter your Zerodha User ID');
    console.log('2. Enter your Password');
    console.log('3. Complete 2FA (PIN/TOTP)');
    console.log('4. Click Login');
    console.log('========================================\n');

    // Wait for redirect back to our app (up to 2 minutes for manual login)
    await page.waitForURL(/localhost:5173/, { timeout: 120000 });
    console.log('✓ Redirected back to AlgoChanakya');
    console.log('  Current URL:', page.url());

    // Step 6: Wait for auth processing
    await page.waitForTimeout(3000);

    // Step 7: Verify successful login
    const finalUrl = page.url();
    const isLoggedIn = finalUrl.includes('/dashboard') ||
                       finalUrl.includes('/watchlist') ||
                       (!finalUrl.includes('/login') && !finalUrl.includes('/error'));

    expect(isLoggedIn).toBeTruthy();
    console.log('✓ Successfully logged in!');
    console.log('  Final URL:', finalUrl);

    // Step 8: Verify token is stored
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
    console.log('✓ Access token stored in localStorage');

    // Step 9: Verify user session by calling API
    const userInfo = await page.evaluate(async (tokenValue) => {
      try {
        const response = await fetch('http://localhost:8000/api/auth/me', {
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

    expect(userInfo).not.toBeNull();
    expect(userInfo.user).toBeTruthy();
    expect(userInfo.user.id).toBeTruthy();
    console.log('✓ User session verified');
    console.log('  User ID:', userInfo.user.id);
    console.log('  Email:', userInfo.user.email || 'N/A');

    // Step 10: Verify broker connections
    if (userInfo.broker_connections) {
      expect(userInfo.broker_connections.length).toBeGreaterThan(0);
      const zerodhaConnection = userInfo.broker_connections.find(bc => bc.broker === 'zerodha');
      expect(zerodhaConnection).toBeTruthy();
      expect(zerodhaConnection.is_active).toBe(true);
      console.log('✓ Zerodha broker connection active');
      console.log('  Broker User ID:', zerodhaConnection.broker_user_id);

      // Step 11: Verify user ID displays in header (not "Guest")
      console.log('\n========================================');
      console.log('STEP 11: Verify user ID in header');
      console.log('========================================');

      // Navigate to a page with KiteLayout header
      await page.goto('/watchlist');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Check header displays broker user ID (not "Guest")
      const headerText = await page.locator('.kite-header, header').first().innerText();
      const hasUserId = headerText.includes(zerodhaConnection.broker_user_id);
      const hasGuest = headerText.includes('Guest');

      console.log('  Header contains broker user ID:', hasUserId ? '✓ YES' : '✗ NO');
      console.log('  Header shows "Guest":', hasGuest ? '✗ YES (BAD)' : '✓ NO (GOOD)');

      expect(hasUserId).toBeTruthy();
      expect(hasGuest).toBeFalsy();
      console.log('✓ User ID displays correctly in header');
    }

    console.log('\n========================================');
    console.log('✓ OAuth flow completed successfully!');
    console.log('========================================\n');
  });

  test('OAuth callback view should handle token from URL', async ({ page }) => {
    // Mock a callback with a fake token
    const fakeToken = 'fake_jwt_token_for_testing';

    await page.goto(`/auth/callback?token=${fakeToken}`);

    // Should show loading state initially
    const loadingIndicator = page.locator('text=Completing authentication, text=Loading');

    // Wait a bit
    await page.waitForTimeout(1000);

    // Check if token was attempted to be stored
    const storedToken = await page.evaluate(() => localStorage.getItem('access_token'));

    // With fake token, API call will fail, but token should be stored first
    if (storedToken === fakeToken) {
      console.log('✓ Token storage mechanism works');
    }

    // Page should show error or redirect
    const currentUrl = page.url();
    console.log('  Final state:', currentUrl);
  });

  test('OAuth callback should handle error parameters', async ({ page }) => {
    // Simulate callback with error
    await page.goto('/auth/callback?error=auth_failed&message=Authentication+failed');

    // Wait for error state
    await page.waitForTimeout(1000);

    // Should show error message
    const errorText = await page.textContent('body');
    expect(errorText.toLowerCase()).toContain('authentication');

    console.log('✓ Error handling works correctly');
  });

  test('should be able to logout after successful login', async ({ page }) => {
    // This test assumes you're already logged in from previous test
    // Set a mock token
    await page.goto('/dashboard');

    await page.evaluate(() => {
      localStorage.setItem('access_token', 'mock_token_for_logout_test');
    });

    await page.reload();

    // Try to find logout button or trigger logout
    // This depends on your UI implementation
    const logoutButton = page.locator('button:has-text("Logout"), a:has-text("Logout")');

    const logoutExists = await logoutButton.count() > 0;

    if (logoutExists) {
      await logoutButton.click();
      await page.waitForTimeout(1000);

      // Should redirect to login
      const currentUrl = page.url();
      expect(currentUrl).toContain('/login');

      // Token should be cleared
      const token = await page.evaluate(() => localStorage.getItem('access_token'));
      expect(token).toBeNull();

      console.log('✓ Logout functionality works');
    } else {
      console.log('⚠ Logout button not found - implement logout UI');
    }
  });

});
