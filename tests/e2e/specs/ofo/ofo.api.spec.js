import { test, expect, authFixture } from '../../fixtures/auth.fixture.js';
import fs from 'fs';
import path from 'path';

const API_BASE = process.env.API_BASE || 'http://localhost:8000';
const TOKEN_FILE = path.join(process.cwd(), 'tests', 'config', '.auth-token');

/**
 * Get stored auth token for API requests
 */
function getAuthToken() {
  try {
    if (fs.existsSync(TOKEN_FILE)) {
      return fs.readFileSync(TOKEN_FILE, 'utf8').trim();
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * OFO API Tests
 * Tests the OFO API endpoints directly
 */
test.describe('OFO - API Tests @api', () => {
  test.describe('GET /api/ofo/strategies', () => {
    test('should return list of available strategies', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/ofo/strategies`);

      expect(response.status()).toBe(200);

      const json = await response.json();
      // API returns { strategies: [...] }
      expect(json).toHaveProperty('strategies');
      const data = json.strategies;
      expect(Array.isArray(data)).toBeTruthy();
      expect(data.length).toBeGreaterThan(0);

      // Check structure of first strategy
      const strategy = data[0];
      expect(strategy).toHaveProperty('key');
      expect(strategy).toHaveProperty('name');
      expect(strategy).toHaveProperty('legs_count');
      expect(strategy).toHaveProperty('category');
    });

    test('should include all 9 strategies', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/ofo/strategies`);
      const json = await response.json();
      const data = json.strategies;

      const strategyKeys = data.map(s => s.key);

      expect(strategyKeys).toContain('iron_condor');
      expect(strategyKeys).toContain('iron_butterfly');
      expect(strategyKeys).toContain('short_straddle');
      expect(strategyKeys).toContain('short_strangle');
      expect(strategyKeys).toContain('long_straddle');
      expect(strategyKeys).toContain('long_strangle');
      expect(strategyKeys).toContain('bull_call_spread');
      expect(strategyKeys).toContain('bear_put_spread');
      expect(strategyKeys).toContain('butterfly_spread');
    });

    test('should have correct legs count for each strategy', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/ofo/strategies`);
      const json = await response.json();
      const data = json.strategies;

      const strategiesMap = {};
      data.forEach(s => strategiesMap[s.key] = s.legs_count);

      expect(strategiesMap['iron_condor']).toBe(4);
      expect(strategiesMap['iron_butterfly']).toBe(4);
      expect(strategiesMap['short_straddle']).toBe(2);
      expect(strategiesMap['short_strangle']).toBe(2);
      expect(strategiesMap['long_straddle']).toBe(2);
      expect(strategiesMap['long_strangle']).toBe(2);
      expect(strategiesMap['bull_call_spread']).toBe(2);
      expect(strategiesMap['bear_put_spread']).toBe(2);
      expect(strategiesMap['butterfly_spread']).toBe(4);
    });

    test('should have correct categories for strategies', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/ofo/strategies`);
      const json = await response.json();
      const data = json.strategies;

      const strategiesMap = {};
      data.forEach(s => strategiesMap[s.key] = s.category);

      // Neutral strategies
      expect(strategiesMap['iron_condor']).toBe('neutral');
      expect(strategiesMap['iron_butterfly']).toBe('neutral');
      expect(strategiesMap['short_straddle']).toBe('neutral');
      expect(strategiesMap['short_strangle']).toBe('neutral');
      expect(strategiesMap['butterfly_spread']).toBe('neutral');

      // Volatile strategies
      expect(strategiesMap['long_straddle']).toBe('volatile');
      expect(strategiesMap['long_strangle']).toBe('volatile');

      // Directional strategies
      expect(strategiesMap['bull_call_spread']).toBe('bullish');
      expect(strategiesMap['bear_put_spread']).toBe('bearish');
    });
  });

  test.describe('POST /api/ofo/calculate', () => {
    test('should require authentication', async ({ request }) => {
      // Make request without auth token
      const response = await request.post(`${API_BASE}/api/ofo/calculate`, {
        data: {
          underlying: 'NIFTY',
          expiry: '2024-01-25',
          strategy_types: ['iron_condor'],
          strike_range: 10,
          lots: 1
        },
        headers: {
          'Authorization': 'Bearer invalid_token'
        }
      });

      // Should return 401 (unauthorized) or 403 (forbidden)
      expect([401, 403]).toContain(response.status());
    });

    test('should validate required fields', async ({ request }) => {
      const token = getAuthToken();
      const response = await request.post(`${API_BASE}/api/ofo/calculate`, {
        data: {},
        headers: { Authorization: `Bearer ${token}` }
      });

      // Should return validation error
      expect(response.status()).toBe(422);
    });

    test('should validate underlying field', async ({ request }) => {
      const token = getAuthToken();
      const response = await request.post(`${API_BASE}/api/ofo/calculate`, {
        data: {
          underlying: 'INVALID_INDEX',
          expiry: '2024-01-25',
          strategy_types: ['iron_condor'],
          strike_range: 10,
          lots: 1
        },
        headers: { Authorization: `Bearer ${token}` }
      });

      // Should return 400 (bad request) or 422 (validation error)
      expect([400, 422]).toContain(response.status());
    });

    test('should handle empty strategy_types gracefully', async ({ request }) => {
      const token = getAuthToken();
      const response = await request.post(`${API_BASE}/api/ofo/calculate`, {
        data: {
          underlying: 'NIFTY',
          expiry: '2024-01-25',
          strategy_types: [],
          strike_range: 10,
          lots: 1
        },
        headers: { Authorization: `Bearer ${token}` }
      });

      // Empty strategy_types should either return 422 (validation) or 404 (no instruments for old expiry)
      // The backend doesn't enforce non-empty at schema level, so it proceeds to query instruments
      expect([404, 422]).toContain(response.status());
    });

    test('should validate lots minimum value', async ({ request }) => {
      const token = getAuthToken();
      const response = await request.post(`${API_BASE}/api/ofo/calculate`, {
        data: {
          underlying: 'NIFTY',
          expiry: '2024-01-25',
          strategy_types: ['iron_condor'],
          strike_range: 10,
          lots: 0
        },
        headers: { Authorization: `Bearer ${token}` }
      });

      // Should return validation error
      expect(response.status()).toBe(422);
    });

    test('should validate strike_range allowed values', async ({ request }) => {
      const token = getAuthToken();
      const response = await request.post(`${API_BASE}/api/ofo/calculate`, {
        data: {
          underlying: 'NIFTY',
          expiry: '2024-01-25',
          strategy_types: ['iron_condor'],
          strike_range: 100,
          lots: 1
        },
        headers: { Authorization: `Bearer ${token}` }
      });

      // Should return validation error (100 is not in [5, 10, 15, 20])
      expect(response.status()).toBe(422);
    });
  });
});
