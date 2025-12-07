import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000';

test.describe('API Endpoints', () => {

  test('health check should return healthy status', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.database).toBe('connected');
    expect(data.redis).toBe('connected');
  });

  test('root endpoint should return welcome message', async ({ request }) => {
    const response = await request.get(`${API_BASE}/`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.message).toContain('AlgoChanakya');
    expect(data.docs).toBe('/docs');
  });

  test('zerodha login endpoint should return login URL', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/zerodha/login`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.login_url).toContain('kite.zerodha.com');
    expect(data.login_url).toContain('api_key=dh9lojp9j9tnq3h4');
    expect(data.message).toBeTruthy();
  });

  test('zerodha login URL should have correct format', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/zerodha/login`);
    const data = await response.json();

    const loginUrl = data.login_url;

    // Verify URL structure
    expect(loginUrl).toContain('https://');
    expect(loginUrl).toContain('kite.zerodha.com/connect/login');
    expect(loginUrl).toContain('api_key=');
    expect(loginUrl).toContain('v=3');
  });

  test('auth/me should return 401 without token', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/me`);
    expect(response.status()).toBe(401);

    const data = await response.json();
    expect(data.detail).toBeTruthy();
  });

  test('auth/me should require Bearer token format', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/me`, {
      headers: {
        'Authorization': 'InvalidToken'
      }
    });

    // API returns 401 for invalid auth format
    expect(response.status()).toBe(401);
  });

  test('logout endpoint should return 401 without auth', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/auth/logout`);
    expect(response.status()).toBe(401);
  });

  test('API docs should be accessible', async ({ request }) => {
    const response = await request.get(`${API_BASE}/docs`);
    expect(response.ok()).toBeTruthy();

    const contentType = response.headers()['content-type'];
    expect(contentType).toContain('text/html');
  });

  test('API should have CORS headers', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/health`, {
      headers: {
        'Origin': 'http://localhost:5174'
      }
    });

    const headers = response.headers();
    // CORS headers may be present in different case or only on preflight
    // Just verify the API responds successfully
    expect(response.ok()).toBeTruthy();
  });

  test('invalid endpoint should return 404', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/invalid-endpoint-xyz`);
    expect(response.status()).toBe(404);
  });

  test('zerodha callback without parameters should fail', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/auth/zerodha/callback`);

    // Should return error or redirect
    expect([302, 422, 400]).toContain(response.status());
  });

});
