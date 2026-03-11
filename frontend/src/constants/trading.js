/**
 * Trading Constants
 *
 * Fetched from backend API on app initialization.
 * This ensures frontend always has consistent data with backend.
 *
 * Updated: 2025-12-21
 */

import { ref, computed } from 'vue'
import api from '@/services/api'

// =============================================================================
// STATE - Reactive references for trading constants
// =============================================================================

export const tradingConstants = ref({
  underlyings: ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX'],
  lot_sizes: { NIFTY: 75, BANKNIFTY: 35, FINNIFTY: 65, SENSEX: 20 },
  strike_steps: { NIFTY: 100, BANKNIFTY: 100, FINNIFTY: 100, SENSEX: 100 },
  index_tokens: { NIFTY: 256265, BANKNIFTY: 260105, FINNIFTY: 257801, SENSEX: 265 },
  index_exchanges: { NIFTY: 'NSE', BANKNIFTY: 'NSE', FINNIFTY: 'NSE', SENSEX: 'BSE' },
  index_symbols: {
    NIFTY: 'NSE:NIFTY 50',
    BANKNIFTY: 'NSE:NIFTY BANK',
    FINNIFTY: 'NSE:NIFTY FIN SERVICE',
    SENSEX: 'BSE:SENSEX'
  }
})

export const isLoaded = ref(false)
export const isLoading = ref(false)
export const error = ref(null)

// =============================================================================
// COMPUTED - Convenient accessors
// =============================================================================

export const UNDERLYINGS = computed(() => tradingConstants.value.underlyings)
export const LOT_SIZES = computed(() => tradingConstants.value.lot_sizes)
export const STRIKE_STEPS = computed(() => tradingConstants.value.strike_steps)
export const INDEX_TOKENS = computed(() => tradingConstants.value.index_tokens)
export const INDEX_SYMBOLS = computed(() => tradingConstants.value.index_symbols)
export const INDEX_EXCHANGES = computed(() => tradingConstants.value.index_exchanges)

// =============================================================================
// FUNCTIONS
// =============================================================================

/**
 * Load trading constants from backend API
 * @param {boolean} force - Force reload even if already loaded
 */
export async function loadTradingConstants(force = false) {
  if (isLoaded.value && !force) return

  isLoading.value = true
  error.value = null

  try {
    const response = await api.get('/api/constants/trading')
    tradingConstants.value = response.data
    isLoaded.value = true
    console.log('[Trading Constants] Loaded from backend:', response.data)
  } catch (err) {
    console.error('[Trading Constants] Failed to load from backend:', err)
    error.value = err.message
    // Keep fallback values defined above
  } finally {
    isLoading.value = false
  }
}

/**
 * Get lot size for an underlying
 * @param {string} underlying - Underlying symbol (NIFTY, BANKNIFTY, etc.)
 * @returns {number} Lot size (defaults to 25)
 */
export function getLotSize(underlying) {
  return tradingConstants.value.lot_sizes[underlying?.toUpperCase()] || 25
}

/**
 * Get strike step for an underlying
 * @param {string} underlying - Underlying symbol (NIFTY, BANKNIFTY, etc.)
 * @returns {number} Strike step in points (defaults to 100)
 */
export function getStrikeStep(underlying) {
  return tradingConstants.value.strike_steps[underlying?.toUpperCase()] || 100
}

/**
 * Get index token for an underlying
 * @param {string} underlying - Underlying symbol (NIFTY, BANKNIFTY, etc.)
 * @returns {number|undefined} Index token or undefined if not found
 */
export function getIndexToken(underlying) {
  return tradingConstants.value.index_tokens[underlying?.toUpperCase()]
}

/**
 * Get index symbol for an underlying (for LTP API)
 * @param {string} underlying - Underlying symbol (NIFTY, BANKNIFTY, etc.)
 * @returns {string|undefined} Trading symbol or undefined if not found
 */
export function getIndexSymbol(underlying) {
  return tradingConstants.value.index_symbols[underlying?.toUpperCase()]
}

/**
 * Get all index tokens as array for WebSocket subscription
 * @returns {number[]} Array of index tokens
 */
export function getAllIndexTokens() {
  return Object.values(tradingConstants.value.index_tokens)
}

/**
 * Check if an underlying is valid/supported
 * @param {string} underlying - Underlying symbol to check
 * @returns {boolean} True if supported
 */
export function isValidUnderlying(underlying) {
  return tradingConstants.value.underlyings.includes(underlying?.toUpperCase())
}

// =============================================================================
// COMPOSABLE
// =============================================================================

/**
 * Vue composable for trading constants
 * @returns {object} Trading constants state and functions
 */
export function useTradingConstants() {
  return {
    tradingConstants,
    isLoaded,
    isLoading,
    error,
    UNDERLYINGS,
    LOT_SIZES,
    STRIKE_STEPS,
    INDEX_TOKENS,
    INDEX_SYMBOLS,
    INDEX_EXCHANGES,
    loadTradingConstants,
    getLotSize,
    getStrikeStep,
    getIndexToken,
    getIndexSymbol,
    getAllIndexTokens,
    isValidUnderlying
  }
}

export default useTradingConstants
