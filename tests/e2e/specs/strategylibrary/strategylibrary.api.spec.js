/**
 * Strategy Library API Validation Tests
 *
 * Tests for API endpoint responses and data integrity:
 * - Templates listing
 * - Categories
 * - Template details
 * - Wizard recommendations
 * - Deploy
 * - Compare
 * - Popular strategies
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

const API_BASE = process.env.API_BASE || 'http://localhost:8001';

test.describe('Strategy Library - API Validation @api', () => {
  const authHeader = process.env.TEST_AUTH_TOKEN
    ? { 'Authorization': `Bearer ${process.env.TEST_AUTH_TOKEN}` }
    : {};

  // ==================== Templates Endpoint Tests ====================

  test('GET /api/strategy-library/templates returns templates list', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/strategy-library/templates`);

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(Array.isArray(data)).toBe(true);
    // Strategy templates are static data — there must always be at least one
    expect(data.length).toBeGreaterThan(0);
    const template = data[0];
    expect(template).toHaveProperty('id');
    expect(template).toHaveProperty('name');
    expect(template).toHaveProperty('display_name');
    expect(template).toHaveProperty('category');
    expect(template).toHaveProperty('legs_config');
  });

  test('GET /api/strategy-library/templates with category filter', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates?category=neutral`
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(Array.isArray(data)).toBe(true);
    for (const template of data) {
      expect(template.category).toBe('neutral');
    }
  });

  test('GET /api/strategy-library/templates with search query', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates?search=iron`
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(Array.isArray(data)).toBe(true);
    // Results should contain 'iron' in name or description
    for (const template of data) {
      const matchesName = template.name.toLowerCase().includes('iron');
      const matchesDisplayName = template.display_name.toLowerCase().includes('iron');
      const matchesDescription = template.description.toLowerCase().includes('iron');
      expect(matchesName || matchesDisplayName || matchesDescription).toBe(true);
    }
  });

  test('GET /api/strategy-library/templates with pagination', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates?limit=2&offset=0`
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeLessThanOrEqual(2);
  });

  test('GET /api/strategy-library/templates with risk_level filter', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates?risk_level=low`
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    for (const template of data) {
      expect(template.risk_level).toBe('low');
    }
  });

  test('GET /api/strategy-library/templates ordered by popularity', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/strategy-library/templates`);

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // Verify ordering
    for (let i = 0; i < data.length - 1; i++) {
      expect(data[i].popularity_score).toBeGreaterThanOrEqual(data[i + 1].popularity_score);
    }
  });

  // ==================== Categories Endpoint Tests ====================

  test('GET /api/strategy-library/templates/categories returns categories', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates/categories`
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('categories');
    expect(data).toHaveProperty('total');
    expect(Array.isArray(data.categories)).toBe(true);

    for (const category of data.categories) {
      expect(category).toHaveProperty('category');
      expect(category).toHaveProperty('count');
      expect(category).toHaveProperty('display_name');
      expect(typeof category.count).toBe('number');
    }
  });

  // ==================== Template Details Endpoint Tests ====================

  test('GET /api/strategy-library/templates/{name} returns template details', async ({ request }) => {
    // First get a template name
    const listResponse = await request.get(`${API_BASE}/api/strategy-library/templates`);
    const templates = await listResponse.json();

    if (templates.length === 0) {
      test.skip('No templates available');
      return;
    }

    const templateName = templates[0].name;
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates/${templateName}`
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // Full detail should include educational content
    expect(data).toHaveProperty('name');
    expect(data).toHaveProperty('display_name');
    expect(data).toHaveProperty('description');
    expect(data).toHaveProperty('legs_config');
    expect(data).toHaveProperty('max_profit');
    expect(data).toHaveProperty('max_loss');
    expect(data).toHaveProperty('created_at');
    expect(data).toHaveProperty('updated_at');
  });

  test('GET /api/strategy-library/templates/{name} returns 404 for invalid name', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/api/strategy-library/templates/nonexistent_strategy_xyz`
    );

    expect(response.status()).toBe(404);
  });

  // ==================== Wizard Endpoint Tests ====================

  test('POST /api/strategy-library/wizard returns recommendations', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/wizard`, {
      data: {
        market_outlook: 'neutral',
        volatility_view: 'high_iv',
        risk_tolerance: 'low'
      }
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('recommendations');
    expect(data).toHaveProperty('inputs');
    expect(data).toHaveProperty('total_matches');
    expect(Array.isArray(data.recommendations)).toBe(true);

    // Check recommendation structure
    for (const rec of data.recommendations) {
      expect(rec).toHaveProperty('template');
      expect(rec).toHaveProperty('score');
      expect(rec).toHaveProperty('match_reasons');
      expect(rec.score).toBeGreaterThanOrEqual(0);
      expect(rec.score).toBeLessThanOrEqual(100);
    }
  });

  test('POST /api/strategy-library/wizard validates required fields', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/wizard`, {
      data: {
        // Missing required fields
        volatility_view: 'high_iv'
      }
    });

    expect(response.status()).toBe(422);
  });

  test('POST /api/strategy-library/wizard returns max 5 recommendations', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/wizard`, {
      data: {
        market_outlook: 'neutral',
        volatility_view: 'any',
        risk_tolerance: 'medium'
      }
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.recommendations.length).toBeLessThanOrEqual(5);
  });

  test('POST /api/strategy-library/wizard with all options', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/wizard`, {
      data: {
        market_outlook: 'bullish',
        volatility_view: 'low_iv',
        risk_tolerance: 'low',
        experience_level: 'beginner',
        capital_size: 'medium'
      }
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('recommendations');
  });

  // ==================== Deploy Endpoint Tests ====================

  test('POST /api/strategy-library/deploy requires authentication', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      data: {
        template_name: 'iron_condor',
        underlying: 'NIFTY',
        lots: 1
      }
    });

    // Should fail without auth
    expect([401, 403, 422]).toContain(response.status());
  });

  test('POST /api/strategy-library/deploy with authentication', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'iron_condor',
        underlying: 'NIFTY',
        lots: 1
      }
    });

    // May fail if template doesn't exist, but should not be auth error
    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('template_name');
      expect(data).toHaveProperty('underlying');
      expect(data).toHaveProperty('legs');
    } else {
      expect([404, 500]).toContain(response.status());
    }
  });

  test('POST /api/strategy-library/deploy returns 404 for invalid template', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'nonexistent_template_xyz',
        underlying: 'NIFTY',
        lots: 1
      }
    });

    expect(response.status()).toBe(404);
  });

  // ==================== Compare Endpoint Tests ====================

  test('POST /api/strategy-library/compare with two strategies', async ({ request }) => {
    // First get template names
    const listResponse = await request.get(`${API_BASE}/api/strategy-library/templates`);
    const templates = await listResponse.json();

    if (templates.length < 2) {
      test.skip('Not enough templates for comparison');
      return;
    }

    const response = await request.post(`${API_BASE}/api/strategy-library/compare`, {
      data: {
        template_names: [templates[0].name, templates[1].name]
      }
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('strategies');
    expect(data).toHaveProperty('comparison_matrix');
    expect(data.strategies.length).toBe(2);
  });

  test('POST /api/strategy-library/compare requires minimum 2 strategies', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/compare`, {
      data: {
        template_names: ['iron_condor']
      }
    });

    expect(response.status()).toBe(422);
  });

  test('POST /api/strategy-library/compare returns comparison metrics', async ({ request }) => {
    const listResponse = await request.get(`${API_BASE}/api/strategy-library/templates`);
    const templates = await listResponse.json();

    if (templates.length < 2) {
      test.skip('Not enough templates for comparison');
      return;
    }

    const response = await request.post(`${API_BASE}/api/strategy-library/compare`, {
      data: {
        template_names: [templates[0].name, templates[1].name]
      }
    });

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // Check comparison matrix has metrics
    const matrixKeys = Object.keys(data.comparison_matrix);
    expect(matrixKeys.length).toBe(2);

    for (const key of matrixKeys) {
      const metrics = data.comparison_matrix[key];
      expect(metrics).toHaveProperty('max_profit');
      expect(metrics).toHaveProperty('max_loss');
      expect(metrics).toHaveProperty('risk_level');
    }
  });

  // ==================== Popular Endpoint Tests ====================

  test('GET /api/strategy-library/popular returns popular strategies', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/strategy-library/popular`);

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('strategies');
    expect(Array.isArray(data.strategies)).toBe(true);
  });

  test('GET /api/strategy-library/popular respects limit parameter', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/strategy-library/popular?limit=3`);

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.strategies.length).toBeLessThanOrEqual(3);
  });

  test('GET /api/strategy-library/popular returns strategies ordered by score', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/strategy-library/popular`);

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // Verify ordering
    for (let i = 0; i < data.strategies.length - 1; i++) {
      expect(data.strategies[i].popularity_score).toBeGreaterThanOrEqual(
        data.strategies[i + 1].popularity_score
      );
    }
  });

  // ==================== Error Handling Tests ====================

  test('API handles invalid JSON gracefully', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/wizard`, {
      headers: { 'Content-Type': 'application/json' },
      data: 'invalid json {'
    });

    expect(response.status()).toBe(422);
  });

  test('API handles missing content-type', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/wizard`, {
      data: JSON.stringify({
        market_outlook: 'neutral',
        volatility_view: 'high_iv',
        risk_tolerance: 'low'
      })
    });

    // Should either succeed or return validation error
    expect([200, 422]).toContain(response.status());
  });

  // ==================== Deploy API Integration Tests ====================
  // Skip: Deploy tests require authenticated session

  test.skip('POST /api/strategy-library/deploy validates required fields', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        // Missing template_name
        underlying: 'NIFTY',
        lots: 1
      }
    });

    // Should return validation error
    expect(response.status()).toBe(422);
  });

  test.skip('POST /api/strategy-library/deploy validates underlying values', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'iron_condor',
        underlying: 'INVALID_INDEX',
        lots: 1
      }
    });

    // Should return validation error for invalid underlying
    expect([400, 422]).toContain(response.status());
  });

  test.skip('POST /api/strategy-library/deploy validates lots range', async ({ request }) => {
    // Test minimum boundary (0 lots should fail)
    const responseLow = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'iron_condor',
        underlying: 'NIFTY',
        lots: 0
      }
    });

    expect([400, 422]).toContain(responseLow.status());

    // Test maximum boundary (100 lots should fail if max is 50)
    const responseHigh = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'iron_condor',
        underlying: 'NIFTY',
        lots: 100
      }
    });

    // May succeed or fail depending on server validation
    expect([200, 400, 422]).toContain(responseHigh.status());
  });

  test('POST /api/strategy-library/deploy returns strategy with legs', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    // First get available expiries
    const expiriesResponse = await request.get(`${API_BASE}/api/options/expiries?underlying=NIFTY`);

    if (!expiriesResponse.ok()) {
      test.skip('Cannot fetch expiries');
      return;
    }

    const expiriesData = await expiriesResponse.json();
    const expiry = expiriesData.expiries?.[0];

    if (!expiry) {
      test.skip('No expiries available');
      return;
    }

    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'iron_condor',
        underlying: 'NIFTY',
        expiry: expiry,
        lots: 1
      }
    });

    if (response.ok()) {
      const data = await response.json();

      // Verify response structure
      expect(data).toHaveProperty('strategy_id');
      expect(data).toHaveProperty('legs');
      expect(Array.isArray(data.legs)).toBe(true);

      // Iron Condor should have 4 legs
      expect(data.legs.length).toBe(4);

      // Verify leg structure
      for (const leg of data.legs) {
        expect(leg).toHaveProperty('strike');
        expect(leg).toHaveProperty('contract_type');
        expect(leg).toHaveProperty('transaction_type');
        expect(['CE', 'PE']).toContain(leg.contract_type);
        expect(['BUY', 'SELL']).toContain(leg.transaction_type);
      }
    }
  });

  test('POST /api/strategy-library/deploy returns correct legs for Bull Call Spread', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const expiriesResponse = await request.get(`${API_BASE}/api/options/expiries?underlying=BANKNIFTY`);

    if (!expiriesResponse.ok()) {
      test.skip('Cannot fetch expiries');
      return;
    }

    const expiriesData = await expiriesResponse.json();
    const expiry = expiriesData.expiries?.[0];

    if (!expiry) {
      test.skip('No expiries available');
      return;
    }

    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'bull_call_spread',
        underlying: 'BANKNIFTY',
        expiry: expiry,
        lots: 2
      }
    });

    if (response.ok()) {
      const data = await response.json();

      // Bull Call Spread should have 2 legs
      expect(data.legs.length).toBe(2);

      // Both should be CE options
      for (const leg of data.legs) {
        expect(leg.contract_type).toBe('CE');
      }

      // One BUY, one SELL
      const buyLegs = data.legs.filter(l => l.transaction_type === 'BUY');
      const sellLegs = data.legs.filter(l => l.transaction_type === 'SELL');
      expect(buyLegs.length).toBe(1);
      expect(sellLegs.length).toBe(1);

      // BUY strike should be lower than SELL strike
      expect(buyLegs[0].strike).toBeLessThan(sellLegs[0].strike);
    }
  });

  test('POST /api/strategy-library/deploy respects lots multiplier', async ({ request }) => {
    if (!process.env.TEST_AUTH_TOKEN) {
      test.skip('No TEST_AUTH_TOKEN available');
      return;
    }

    const expiriesResponse = await request.get(`${API_BASE}/api/options/expiries?underlying=NIFTY`);

    if (!expiriesResponse.ok()) {
      test.skip('Cannot fetch expiries');
      return;
    }

    const expiriesData = await expiriesResponse.json();
    const expiry = expiriesData.expiries?.[0];

    if (!expiry) {
      test.skip('No expiries available');
      return;
    }

    // Deploy with 2 lots
    const response = await request.post(`${API_BASE}/api/strategy-library/deploy`, {
      headers: authHeader,
      data: {
        template_name: 'bull_put_spread',
        underlying: 'NIFTY',
        expiry: expiry,
        lots: 2
      }
    });

    if (response.ok()) {
      const data = await response.json();

      // NIFTY lot size is 75, so 2 lots = 150 qty
      for (const leg of data.legs) {
        if (leg.quantity) {
          expect(leg.quantity).toBe(150);
        }
      }
    }
  });
});
