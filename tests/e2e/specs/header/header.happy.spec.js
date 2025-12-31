/**
 * Header Happy Path Tests
 *
 * Tests for the Kite Header navigation and user menu.
 * Note: These tests require authentication - use auth fixture.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { KiteHeaderPage } from '../../pages/KiteHeaderPage.js';

test.describe('Header User Menu @happy', () => {
  // Run tests serially to avoid browser context creation timeouts
  test.describe.configure({ mode: 'serial' });

  let headerPage;

  test.beforeEach(async ({ authenticatedPage }) => {
    headerPage = new KiteHeaderPage(authenticatedPage);
    await headerPage.navigate();
    await headerPage.waitForLoad();
  });

  test('user menu trigger is visible', async () => {
    await expect(headerPage.userMenu).toBeVisible();
  });

  test('user menu opens on click', async () => {
    await headerPage.openUserMenu();
    await expect(headerPage.userDropdown).toBeVisible();
  });

  test('user dropdown shows user name', async () => {
    await headerPage.openUserMenu();
    await expect(headerPage.userName).toBeVisible();
  });

  test('user dropdown shows settings button', async () => {
    await headerPage.openUserMenu();
    await expect(headerPage.settingsButton).toBeVisible();
  });

  test('user dropdown shows logout button', async () => {
    await headerPage.openUserMenu();
    await expect(headerPage.logoutButton).toBeVisible();
  });

  test('user dropdown closes when clicking outside', async () => {
    await headerPage.openUserMenu();
    await expect(headerPage.userDropdown).toBeVisible();

    await headerPage.closeUserMenu();
    await expect(headerPage.userDropdown).not.toBeVisible();
  });

  test('header should not show scrollbar when user menu is open', async () => {
    // Get header state before opening menu
    const beforeState = await headerPage.getHeaderScrollbarState();

    // Open user menu
    await headerPage.openUserMenu();
    await expect(headerPage.userDropdown).toBeVisible();

    // Get header state after opening menu
    const afterState = await headerPage.getHeaderScrollbarState();

    // Assert: header should NOT have a vertical scrollbar
    // This test will FAIL if the scrollbar bug is present
    expect(afterState.hasVerticalScrollbar).toBe(false);
  });
});
