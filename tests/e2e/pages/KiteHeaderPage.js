/**
 * Kite Header Page Object
 *
 * Tests the fixed header navigation including user menu dropdown.
 *
 * Usage:
 *   import { KiteHeaderPage } from '../pages/KiteHeaderPage.js';
 *   const headerPage = new KiteHeaderPage(page);
 *   await headerPage.openUserMenu();
 */

import { BasePage } from './BasePage.js';

export class KiteHeaderPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/dashboard'; // Header is visible on any authenticated page
  }

  // ============ Selectors ============

  get header() {
    return this.page.locator('header.kite-header');
  }

  get userMenu() {
    return this.getByTestId('kite-header-user-menu');
  }

  get userDropdown() {
    return this.getByTestId('kite-header-user-dropdown');
  }

  get userAvatar() {
    return this.getByTestId('kite-header-user-avatar');
  }

  get userName() {
    return this.getByTestId('kite-header-user-name');
  }

  get settingsButton() {
    return this.getByTestId('kite-header-settings-button');
  }

  get logoutButton() {
    return this.getByTestId('kite-header-logout-button');
  }

  // ============ Actions ============

  async openUserMenu() {
    await this.userMenu.click();
  }

  async closeUserMenu() {
    // Click outside to close the dropdown
    await this.page.locator('body').click({ position: { x: 10, y: 100 } });
  }

  async clickSettings() {
    await this.settingsButton.click();
  }

  async clickLogout() {
    await this.logoutButton.click();
  }

  // ============ Assertions / Data Getters ============

  /**
   * Get the scrollbar state of the header element
   * Used to detect if dropdown causes unwanted scrollbar
   */
  async getHeaderScrollbarState() {
    return await this.header.evaluate((el) => {
      const style = window.getComputedStyle(el);
      const overflowY = style.overflowY;

      // A scrollbar is visible when:
      // 1. Content overflows (scrollHeight > clientHeight)
      // 2. AND overflow is not hidden (allows scrollbar to show)
      const contentOverflows = el.scrollHeight > el.clientHeight;
      const scrollbarCanShow = overflowY !== 'hidden' && overflowY !== 'clip';

      return {
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
        contentOverflows,
        overflowY,
        overflowX: style.overflowX,
        hasVerticalScrollbar: contentOverflows && scrollbarCanShow
      };
    });
  }

  /**
   * Check if the user dropdown is currently visible
   */
  async isUserDropdownVisible() {
    return await this.userDropdown.isVisible();
  }
}
