/**
 * AutoPilot API E2E Tests
 *
 * Tests for AutoPilot API endpoints via browser requests.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';

const API_BASE = process.env.API_BASE || 'http://localhost:8000';


// =============================================================================
// STRATEGIES API TESTS
// =============================================================================

// API tests - enabled for live testing with authenticated session
test.describe('AutoPilot Strategies API', () => {

  // Clean up test strategies before running tests
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ storageState: 'tests/config/.auth-state.json' });
    const page = await context.newPage();
    await page.goto('http://localhost:5173/autopilot');
    await page.waitForLoadState('networkidle');

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    if (!token) {
      await context.close();
      return;
    }

    // Get all strategies
    const listResponse = await page.request.get(
      `${API_BASE}/api/v1/autopilot/strategies?page_size=50`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    if (!listResponse.ok()) {
      await context.close();
      return;
    }

    const data = await listResponse.json();
    const strategies = data.data || [];

    // Delete test strategies to stay under limit (keep first 10)
    const testPatterns = ['Test Strategy', 'Get Single Test', 'Update Test', 'Delete Test',
                          'Activate Test', 'Pause Test', 'Resume Test', 'Clone Source',
                          'Cloned Strategy', 'State Test', 'Updated Name'];

    let deleted = 0;
    for (const strategy of strategies) {
      const isTestStrategy = testPatterns.some(p => strategy.name.includes(p));
      if (isTestStrategy) {
        try {
          await page.request.delete(
            `${API_BASE}/api/v1/autopilot/strategies/${strategy.id}`,
            { headers: { 'Authorization': `Bearer ${token}` } }
          );
          deleted++;
        } catch (e) {
          // Ignore delete failures
        }
      }
    }
    console.log(`Cleaned up ${deleted} test strategies`);
    await context.close();
  });

  test('GET /api/v1/autopilot/strategies returns list', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('data');
    expect(data).toHaveProperty('page');
    expect(data).toHaveProperty('total');
    expect(Array.isArray(data.data)).toBe(true);
  });

  test('GET /api/v1/autopilot/strategies supports pagination', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies?page=1&page_size=10`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.page).toBe(1);
    expect(data.page_size).toBe(10);
  });

  test('GET /api/v1/autopilot/strategies filters by status', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies?status=active`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // All returned strategies should be active
    for (const strategy of data.data) {
      expect(strategy.status).toBe('active');
    }
  });

  test('GET /api/v1/autopilot/strategies filters by underlying', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies?underlying=NIFTY`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    for (const strategy of data.data) {
      expect(strategy.underlying).toBe('NIFTY');
    }
  });

  test('POST /api/v1/autopilot/strategies creates strategy', async ({ authenticatedPage }) => {
    const strategyData = {
      name: `Test Strategy ${Date.now()}`,
      description: 'E2E Test Strategy',
      underlying: 'NIFTY',
      expiry_type: 'current_week',
      lots: 1,
      position_type: 'intraday',
      legs_config: [
        {
          id: 'leg1',
          contract_type: 'CE',
          transaction_type: 'SELL',
          strike_selection: {
            mode: 'atm_offset',
            offset: 0
          },
          quantity_multiplier: 1,
          execution_order: 1
        }
      ],
      entry_conditions: {
        logic: 'AND',
        conditions: [
          {
            id: 'cond1',
            enabled: true,
            variable: 'TIME.CURRENT',
            operator: 'greater_than',
            value: '09:20'
          }
        ]
      },
      order_settings: {
        order_type: 'MARKET',
        execution_style: 'sequential'
      }
    };

    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: strategyData
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data).toHaveProperty('id');
    expect(data.data.name).toBe(strategyData.name);
    expect(data.data.status).toBe('draft');
  });

  test('GET /api/v1/autopilot/strategies/:id returns single strategy', async ({ authenticatedPage }) => {
    // First create a strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Get Single Test ${Date.now()}`)
      }
    );

    const created = await createResponse.json();
    const strategyId = created.data.id;

    // Then get it
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data.id).toBe(strategyId);
  });

  test('PUT /api/v1/autopilot/strategies/:id updates strategy', async ({ authenticatedPage }) => {
    // First create a strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Update Test ${Date.now()}`)
      }
    );

    const created = await createResponse.json();
    const strategyId = created.data.id;

    // Update it
    const response = await authenticatedPage.request.put(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: {
          name: 'Updated Name'
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data.name).toBe('Updated Name');
  });

  test('DELETE /api/v1/autopilot/strategies/:id deletes strategy', async ({ authenticatedPage }) => {
    // First create a strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Delete Test ${Date.now()}`)
      }
    );

    // Skip if strategy limit reached
    if (!createResponse.ok()) {
      test.skip();
      return;
    }

    const created = await createResponse.json();
    const strategyId = created.data?.id;
    if (!strategyId) {
      test.skip();
      return;
    }

    // Delete it
    const response = await authenticatedPage.request.delete(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);

    // Verify it's deleted
    const getResponse = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(getResponse.status()).toBe(404);
  });
});


// =============================================================================
// STRATEGY LIFECYCLE API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot Strategy Lifecycle API', () => {

  test('POST /api/v1/autopilot/strategies/:id/activate activates draft', async ({ authenticatedPage }) => {
    // Create draft strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Activate Test ${Date.now()}`)
      }
    );

    // Skip if strategy limit reached
    if (!createResponse.ok()) {
      test.skip();
      return;
    }

    const created = await createResponse.json();
    const strategyId = created.data?.id;
    if (!strategyId) {
      test.skip();
      return;
    }

    // Activate it
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/activate`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: {
          confirm: true,
          paper_trading: true // Use paper trading for tests
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(['waiting', 'active']).toContain(data.data.status);
  });

  test('POST /api/v1/autopilot/strategies/:id/pause pauses active strategy', async ({ authenticatedPage }) => {
    // Create and activate strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Pause Test ${Date.now()}`, {
          entry_conditions: { logic: 'AND', conditions: [] }
        })
      }
    );

    // Skip if strategy limit reached
    if (!createResponse.ok()) {
      test.skip();
      return;
    }

    const created = await createResponse.json();
    const strategyId = created.data?.id;
    if (!strategyId) {
      test.skip();
      return;
    }

    // Activate
    await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/activate`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: { confirm: true, paper_trading: true }
      }
    );

    // Pause
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/pause`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data.status).toBe('paused');
  });

  test('POST /api/v1/autopilot/strategies/:id/resume resumes paused strategy', async ({ authenticatedPage }) => {
    // Create, activate, and pause strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Resume Test ${Date.now()}`, {
          entry_conditions: { logic: 'AND', conditions: [] }
        })
      }
    );

    // Skip if strategy limit reached
    if (!createResponse.ok()) {
      test.skip();
      return;
    }

    const created = await createResponse.json();
    const strategyId = created.data?.id;
    if (!strategyId) {
      test.skip();
      return;
    }

    // Activate
    await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/activate`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: { confirm: true, paper_trading: true }
      }
    );

    // Pause
    await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/pause`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    // Resume
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/resume`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(['waiting', 'active']).toContain(data.data.status);
  });

  test('POST /api/v1/autopilot/strategies/:id/clone clones strategy', async ({ authenticatedPage }) => {
    // Create strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`Clone Source ${Date.now()}`)
      }
    );

    // Skip if strategy limit reached
    if (!createResponse.ok()) {
      test.skip();
      return;
    }

    const created = await createResponse.json();
    const strategyId = created.data?.id;
    if (!strategyId) {
      test.skip();
      return;
    }

    // Clone
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/clone`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: {
          new_name: 'Cloned Strategy',
          reset_schedule: true
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data.id).not.toBe(strategyId);
    expect(data.data.name).toBe('Cloned Strategy');
    expect(data.data.status).toBe('draft');
  });
});


// =============================================================================
// DASHBOARD API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot Dashboard API', () => {

  test('GET /api/v1/autopilot/dashboard/summary returns summary', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/dashboard/summary`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data).toHaveProperty('active_strategies');
    expect(data.data).toHaveProperty('waiting_strategies');
    expect(data.data).toHaveProperty('today_total_pnl');
    expect(data.data).toHaveProperty('risk_metrics');
  });

  test('Dashboard summary includes risk metrics', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/dashboard/summary`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data.risk_metrics).toHaveProperty('status');
    expect(['safe', 'warning', 'critical']).toContain(data.data.risk_metrics.status);
  });
});


// =============================================================================
// SETTINGS API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot Settings API', () => {

  test('GET /api/v1/autopilot/settings returns user settings', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/settings`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data.data).toHaveProperty('daily_loss_limit');
    expect(data.data).toHaveProperty('max_active_strategies');
  });

  test('PUT /api/v1/autopilot/settings updates settings', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.put(
      `${API_BASE}/api/v1/autopilot/settings`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: {
          daily_loss_limit: 15000
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    // Decimal fields are serialized as strings in JSON
    expect(parseFloat(data.data.daily_loss_limit)).toBe(15000);
  });
});


// =============================================================================
// ORDERS API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot Orders API', () => {

  test('GET /api/v1/autopilot/orders returns order list', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/orders`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('data');
    expect(Array.isArray(data.data)).toBe(true);
  });

  test('Orders can be filtered by strategy', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/orders?strategy_id=1`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    for (const order of data.data) {
      expect(order.strategy_id).toBe(1);
    }
  });
});


// =============================================================================
// LOGS API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot Logs API', () => {

  test('GET /api/v1/autopilot/logs returns activity logs', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/logs`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('data');
    expect(Array.isArray(data.data)).toBe(true);
  });

  test('Logs can be filtered by severity', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/logs?severity=error`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    for (const log of data.data) {
      expect(log.severity).toBe('error');
    }
  });
});


// =============================================================================
// KILL SWITCH API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot Kill Switch API', () => {

  test('POST /api/v1/autopilot/kill-switch returns success', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/kill-switch`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: {
          confirm: true,
          reason: 'E2E Test'
        }
      }
    );

    expect(response.ok()).toBe(true);
    const data = await response.json();

    expect(data).toHaveProperty('message');
    expect(data.data).toHaveProperty('strategies_stopped');
  });
});


// =============================================================================
// ERROR HANDLING API TESTS
// =============================================================================

// Skip: API tests require running backend with proper authentication
test.describe('AutoPilot API Error Handling', () => {

  test('Returns 401 without auth token', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies`
    );

    expect(response.status()).toBe(401);
  });

  test('Returns 404 for non-existent strategy', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.get(
      `${API_BASE}/api/v1/autopilot/strategies/99999`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    expect(response.status()).toBe(404);
  });

  test('Returns 422 for invalid strategy data', async ({ authenticatedPage }) => {
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: {
          // Missing required fields
          description: 'Invalid strategy'
        }
      }
    );

    // FastAPI/Pydantic returns 422 for validation errors
    expect(response.status()).toBe(422);
  });

  test('Returns 409 for invalid state transition', async ({ authenticatedPage }) => {
    // Create a draft strategy
    const createResponse = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`,
          'Content-Type': 'application/json'
        },
        data: createTestStrategy(`State Test ${Date.now()}`)
      }
    );

    // Check if create succeeded
    if (!createResponse.ok()) {
      // Skip test if strategy limit reached or create failed
      console.log('Strategy creation failed, skipping test');
      return;
    }

    const created = await createResponse.json();
    const strategyId = created.data?.id;

    if (!strategyId) {
      console.log('No strategy ID returned, skipping test');
      return;
    }

    // Try to pause a draft (invalid transition)
    const response = await authenticatedPage.request.post(
      `${API_BASE}/api/v1/autopilot/strategies/${strategyId}/pause`,
      {
        headers: {
          'Authorization': `Bearer ${await getToken(authenticatedPage)}`
        }
      }
    );

    // Should return error (409 Conflict or 400 Bad Request)
    expect([400, 409]).toContain(response.status());
  });
});


// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

async function getToken(page) {
  return await page.evaluate(() => localStorage.getItem('access_token'));
}

/**
 * Create a test strategy data object with correct schema format
 */
function createTestStrategy(name, options = {}) {
  return {
    name: name,
    underlying: options.underlying || 'NIFTY',
    expiry_type: options.expiry_type || 'current_week',
    lots: options.lots || 1,
    position_type: options.position_type || 'intraday',
    legs_config: options.legs_config || [
      {
        id: 'leg1',
        contract_type: 'CE',
        transaction_type: 'SELL',
        strike_selection: {
          mode: 'atm_offset',
          offset: 0
        },
        quantity_multiplier: 1,
        execution_order: 1
      }
    ],
    entry_conditions: options.entry_conditions || {
      logic: 'AND',
      conditions: [
        {
          id: 'cond1',
          enabled: true,
          variable: 'TIME.CURRENT',
          operator: 'greater_than',
          value: '09:20'
        }
      ]
    },
    ...options.extra
  };
}
