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

  // ============ Index Prices Selectors ============

  get indexPricesContainer() {
    return this.getByTestId('kite-header-index-prices');
  }

  get nifty50Item() {
    return this.getByTestId('kite-header-index-nifty50');
  }

  get nifty50Value() {
    return this.getByTestId('kite-header-index-value-nifty50');
  }

  get sensexItem() {
    return this.getByTestId('kite-header-index-sensex');
  }

  get sensexValue() {
    return this.getByTestId('kite-header-index-value-sensex');
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

  // ============ Index Price Helpers ============

  /**
   * Get NIFTY 50 price as a number
   * @returns {Promise<number>} Price value or NaN if not available
   */
  async getNifty50Price() {
    const text = await this.nifty50Value.textContent();
    return parseFloat(text.replace(/,/g, ''));
  }

  /**
   * Get SENSEX price as a number
   * @returns {Promise<number>} Price value or NaN if not available
   */
  async getSensexPrice() {
    const text = await this.sensexValue.textContent();
    return parseFloat(text.replace(/,/g, ''));
  }

  /**
   * Wait for index prices to load (non-zero values).
   * Returns true if live prices arrived, false if market is closed/WebSocket unavailable.
   * Never throws — tests must handle both states.
   * @param {number} timeout - Max wait time in ms (default 5000)
   * @returns {Promise<boolean>}
   */
  async waitForIndexPrices(timeout = 5000) {
    try {
      await this.page.waitForFunction(
        () => {
          const niftyEl = document.querySelector('[data-testid="kite-header-index-value-nifty50"]');
          const sensexEl = document.querySelector('[data-testid="kite-header-index-value-sensex"]');
          if (!niftyEl || !sensexEl) return false;
          const niftyPrice = parseFloat(niftyEl.textContent.replace(/,/g, ''));
          const sensexPrice = parseFloat(sensexEl.textContent.replace(/,/g, ''));
          return niftyPrice > 0 && sensexPrice > 0;
        },
        undefined,   // arg (none needed)
        { timeout }  // options — must be third argument
      );
      return true;
    } catch {
      // Market closed or WebSocket not delivering data — prices show '--'
      return false;
    }
  }
}
