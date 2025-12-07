/**
 * Kite Login Credentials - EXAMPLE FILE
 *
 * Copy this file to credentials.js and fill in your details.
 * credentials.js is gitignored - never commit your actual credentials!
 *
 * Usage in tests:
 *   import { credentials } from '../config/credentials.js';
 */

export const credentials = {
  kite: {
    userId: 'YOUR_KITE_USER_ID',    // e.g., 'AB1234'
    password: 'YOUR_KITE_PASSWORD',  // Your Kite password
    // TOTP is entered manually during test execution
  }
};
