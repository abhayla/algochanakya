/**
 * Positions API Validation Tests
 *
 * Tests for API endpoint responses and data integrity.
 */

import { test, expect } from '@playwright/test';

const API_BASE = process.env.API_BASE || 'http://localhost:8000';

test.describe('Positions - API Validation @api', () => {
  const authHeader = process.env.TEST_AUTH_TOKEN
    ? { 'Authorization': `Bearer ${process.env.TEST_AUTH_TOKEN}` }
    : {};

  test('GET /api/positions/ returns positions list', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const response = await request.get(`${API_BASE}/api/positions/`, {
      headers: authHeader
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // Check response structure
    expect(data).toHaveProperty('positions');
    expect(data).toHaveProperty('summary');
    expect(Array.isArray(data.positions)).toBe(true);
  });

  test('GET /api/positions/?type=day returns day positions', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const response = await request.get(`${API_BASE}/api/positions/?type=day`, {
      headers: authHeader
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('positions');
  });

  test('GET /api/positions/?type=net returns net positions', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const response = await request.get(`${API_BASE}/api/positions/?type=net`, {
      headers: authHeader
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('positions');
  });

  test('positions list without auth returns 401', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/positions/`);
    expect(response.status()).toBe(401);
  });

  test('summary contains expected fields', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const response = await request.get(`${API_BASE}/api/positions/`, {
      headers: authHeader
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    const expectedFields = [
      'total_positions',
      'total_quantity',
      'realized_pnl',
      'unrealized_pnl',
      'total_pnl',
      'total_pnl_pct'
    ];

    for (const field of expectedFields) {
      expect(data.summary).toHaveProperty(field);
    }
  });
});
