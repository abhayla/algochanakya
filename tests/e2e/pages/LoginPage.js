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

  get brokerSelect() {
    return this.getByTestId('login-broker-select');
  }

  get submitButton() {
    return this.getByTestId('login-submit-button');
  }

  get errorMessage() {
    return this.getByTestId('login-error-message');
  }

  get safetyToggle() {
    return this.getByTestId('login-safety-toggle');
  }

  // AngelOne inline fields
  get angelOneFields() {
    return this.getByTestId('login-angelone-fields');
  }

  get angelOneClientId() {
    return this.getByTestId('login-angelone-client-id');
  }

  get angelOnePin() {
    return this.getByTestId('login-angelone-pin');
  }

  get angelOneTotp() {
    return this.getByTestId('login-angelone-totp');
  }

  // Dhan inline fields
  get dhanFields() {
    return this.getByTestId('login-dhan-fields');
  }

  get dhanClientId() {
    return this.getByTestId('login-dhan-client-id');
  }

  get dhanAccessToken() {
    return this.getByTestId('login-dhan-access-token');
  }

  // Actions
  async waitForPageLoad() {
    await this.waitForTestId('login-page');
    await this.waitForLoad();
  }

  async selectBroker(broker) {
    await this.brokerSelect.selectOption(broker);
  }

  async submitLogin() {
    await this.submitButton.click();
  }

  async selectZerodhaAndSubmit() {
    await this.selectBroker('zerodha');
    await this.submitLogin();
  }

  async selectAngelOneAndFill(clientId, pin, totp) {
    await this.selectBroker('angelone');
    await this.angelOneFields.waitFor({ state: 'visible' });
    await this.angelOneClientId.fill(clientId);
    await this.angelOnePin.fill(pin);
    await this.angelOneTotp.fill(totp);
    await this.submitLogin();
  }

  async toggleSafetyInfo() {
    await this.safetyToggle.click();
  }

  // Attempt login without credentials to trigger error (for visual test)
  async triggerValidationError() {
    await this.selectBroker('angelone');
    await this.submitLogin();
  }

  // Assertions
  async isPageVisible() {
    return await this.isTestIdVisible('login-page');
  }

  async isBrokerSelectVisible() {
    return await this.isTestIdVisible('login-broker-select');
  }

  async hasError() {
    return await this.isTestIdVisible('login-error-message');
  }

  async getErrorText() {
    return await this.getTestIdText('login-error-message');
  }
}
