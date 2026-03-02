/**
 * Base Page Object - Common methods for all page objects
 *
 * All page objects should extend this class.
 *
 * Usage:
 *   import { BasePage } from './BasePage.js';
 *   export class LoginPage extends BasePage { ... }
 */

export class BasePage {
  constructor(page) {
    this.page = page;
    this.url = '/';
  }

  /**
   * Navigate to the page URL.
   * storageState from playwright.config.js injects localStorage at context creation time,
   * so direct navigation is safe — no need to visit home first.
   */
  async navigate() {
    const baseUrl = process.env.FRONTEND_URL || 'http://localhost:5173';
    const targetUrl = this.url && this.url !== '/' ? baseUrl + this.url : baseUrl;
    await this.page.goto(targetUrl);
    // Use domcontentloaded — networkidle never fires with persistent WebSocket connections
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Navigate to a specific URL (uses this.url as fallback)
   */
  async goto(url) {
    const targetUrl = url || this.url;
    await this.page.goto(targetUrl);
    // Don't use networkidle - WebSocket connections keep network active
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Wait for element by data-testid
   */
  async waitForTestId(testId, options = {}) {
    const selector = `[data-testid="${testId}"]`;
    await this.page.waitForSelector(selector, { timeout: 10000, ...options });
    return this.page.locator(selector);
  }

  /**
   * Get element by data-testid
   */
  getByTestId(testId) {
    return this.page.locator(`[data-testid="${testId}"]`);
  }

  /**
   * Click element by data-testid
   */
  async clickTestId(testId) {
    await this.page.locator(`[data-testid="${testId}"]`).click();
  }

  /**
   * Check if element with data-testid is visible
   */
  async isTestIdVisible(testId) {
    return await this.page.locator(`[data-testid="${testId}"]`).isVisible();
  }

  /**
   * Assert element with data-testid is visible (throws if not)
   */
  async assertVisible(testId) {
    const locator = this.page.locator(`[data-testid="${testId}"]`);
    await locator.waitFor({ state: 'visible', timeout: 10000 });
  }

  /**
   * Assert element with data-testid is hidden (throws if visible)
   */
  async assertHidden(testId) {
    const locator = this.page.locator(`[data-testid="${testId}"]`);
    await locator.waitFor({ state: 'hidden', timeout: 10000 });
  }

  /**
   * Get text content by data-testid
   */
  async getTestIdText(testId) {
    return await this.page.locator(`[data-testid="${testId}"]`).textContent();
  }

  /**
   * Wait for page to be fully loaded.
   * Note: We don't use 'networkidle' because WebSocket connections keep the network active.
   */
  async waitForLoad() {
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Take a screenshot with descriptive name
   */
  async screenshot(name) {
    await this.page.screenshot({
      path: `tests/screenshots/${name}.png`,
      fullPage: false
    });
  }

  /**
   * Take a full page screenshot
   */
  async screenshotFullPage(name) {
    await this.page.screenshot({
      path: `tests/screenshots/${name}.png`,
      fullPage: true
    });
  }

  /**
   * Get current URL
   */
  getUrl() {
    return this.page.url();
  }

  /**
   * Check if current URL contains path
   */
  urlContains(path) {
    return this.page.url().includes(path);
  }

  /**
   * Wait for URL to contain path
   */
  async waitForUrl(path, options = {}) {
    await this.page.waitForURL(`**/${path}**`, { timeout: 10000, ...options });
  }

  /**
   * Get viewport size
   */
  getViewportSize() {
    return this.page.viewportSize();
  }

  /**
   * Set viewport size
   */
  async setViewportSize(width, height) {
    await this.page.setViewportSize({ width, height });
  }

  /**
   * Check for horizontal overflow
   */
  async hasHorizontalOverflow() {
    return await this.page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
  }

  /**
   * Get page dimensions
   */
  async getPageDimensions() {
    return await this.page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      clientWidth: document.documentElement.clientWidth,
      clientHeight: document.documentElement.clientHeight
    }));
  }
}
