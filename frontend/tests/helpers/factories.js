/**
 * Test data factories for frontend unit tests.
 *
 * Provides builder functions for common test objects so that test files
 * don't each need their own hardcoded mock data.
 *
 * Usage:
 *   import { makeUser, makeBrokerConnection, makePreferences } from '../helpers/factories.js'
 *
 *   const user = makeUser()
 *   const adminUser = makeUser({ email: 'admin@example.com' })
 *   const conn = makeBrokerConnection('upstox', { is_active: false })
 */

// ─────────────────────────────────────────────────────────────────────────────
// User
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @param {object} overrides
 * @returns {{ id: string, email: string, name: string }}
 */
export function makeUser(overrides = {}) {
  return {
    id: 'test-user-id',
    email: 'test@example.com',
    name: 'Test User',
    created_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Broker Connection
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @param {'zerodha'|'angelone'|'upstox'|'dhan'|'fyers'|'paytm'} broker
 * @param {object} overrides
 */
export function makeBrokerConnection(broker = 'zerodha', overrides = {}) {
  const userIds = {
    zerodha:  'ZR1234',
    angelone: 'ANG5678',
    upstox:   'UP9012',
    dhan:     'DH3456',
    fyers:    'FY7890',
    paytm:    'PT1234',
  }
  return {
    id: `conn-${broker}`,
    broker,
    broker_user_id: userIds[broker] || 'TEST123',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

/**
 * All 6 broker connections (one per broker), all active.
 */
export function makeAllBrokerConnections() {
  return ['zerodha', 'angelone', 'upstox', 'dhan', 'fyers', 'paytm']
    .map((b) => makeBrokerConnection(b))
}

// ─────────────────────────────────────────────────────────────────────────────
// User Preferences
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @param {object} overrides
 */
export function makePreferences(overrides = {}) {
  return {
    market_data_source: 'smartapi',
    order_broker: 'kite',
    pnl_grid_interval: 100,
    theme: 'dark',
    ...overrides,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Watchlist
// ─────────────────────────────────────────────────────────────────────────────

export function makeWatchlist(name = 'My Watchlist', overrides = {}) {
  return {
    id: `wl-${name.replace(/\s/g, '-').toLowerCase()}`,
    name,
    instruments: [],
    created_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeInstrument(symbol = 'NIFTY 50', overrides = {}) {
  return {
    tradingsymbol: symbol,
    exchange: 'NSE',
    instrument_token: 256265,
    last_price: 24500.50,
    change: 49.75,
    change_percent: 0.20,
    ...overrides,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Position
// ─────────────────────────────────────────────────────────────────────────────

export function makePosition(overrides = {}) {
  return {
    tradingsymbol: 'NIFTY25APR24000CE',
    exchange: 'NFO',
    quantity: -50,
    average_price: 150.0,
    last_price: 130.0,
    pnl: 1000.0,
    unrealised_pnl: 1000.0,
    realised_pnl: 0.0,
    ...overrides,
  }
}
