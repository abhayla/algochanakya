/**
 * Login API Validation Tests
 *
 * Tests for API endpoint responses and data integrity.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

const API_BASE = process.env.API_BASE || 'http://localhost:8001';

test.describe('Login - API Validation @api', () => {

  test('GET /api/auth/zerodha/login returns valid login URL', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/zerodha/login`);

    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data.login_url).toBeDefined();
    expect(data.login_url).toContain('kite.zerodha.com');
  });

  test('health check endpoint responds', async ({ request }) => {
    const response = await request.get(`${API_BASE}/health`);

    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('GET /api/auth/me with invalid token returns 401', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/me`, {
      headers: {
        'Authorization': 'Bearer invalid-token-12345'
      }
    });

    expect(response.status()).toBe(401);
  });
});
