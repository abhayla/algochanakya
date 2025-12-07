/**
 * Login Page Object
 *
 * Usage:
 *   import { LoginPage } from '../pages/LoginPage.js';
 *   const loginPage = new LoginPage(page);
 *   await loginPage.navigate();
 */

import { BasePage } from './BasePage.js';

export class LoginPage extends BasePage {
  constructor(page) {
    super(page);
    this.url = '/login';
  }

  // Selectors
  get container() {
    return this.getByTestId('login-page');
  }

  get zerodhaButton() {
    return this.getByTestId('login-zerodha-button');
  }

  get angelOneButton() {
    return this.getByTestId('login-angelone-button');
  }

  get errorMessage() {
    return this.getByTestId('login-error-message');
  }

  get safetyToggle() {
    return this.getByTestId('login-safety-toggle');
  }

  // Actions
  async waitForPageLoad() {
    await this.waitForTestId('login-page');
    await this.waitForLoad();
  }

  async clickZerodhaLogin() {
    await this.zerodhaButton.click();
  }

  async clickAngelOneLogin() {
    await this.angelOneButton.click();
  }

  async toggleSafetyInfo() {
    await this.safetyToggle.click();
  }

  // Assertions
  async isPageVisible() {
    return await this.isTestIdVisible('login-page');
  }

  async isZerodhaButtonVisible() {
    return await this.isTestIdVisible('login-zerodha-button');
  }

  async isAngelOneButtonVisible() {
    return await this.isTestIdVisible('login-angelone-button');
  }

  async hasError() {
    return await this.isTestIdVisible('login-error-message');
  }

  async getErrorText() {
    return await this.getTestIdText('login-error-message');
  }
}
