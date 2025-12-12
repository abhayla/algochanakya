/**
 * Centralized price fallback composable
 *
 * Provides API fallback for live prices when WebSocket is unavailable.
 * Used across KiteHeader, WatchlistView, IndexHeader, Strategy Builder, and AutoPilot.
 */
import api from '@/services/api'

// Index token constants
export const INDEX_TOKENS = {
  NIFTY_50: 256265,
  NIFTY_BANK: 260105
}

/**
 * Convert API response to tick format
 * @param {Object} data - API response with last_price, change, etc.
 * @returns {Object} Tick format { ltp, change, change_percent }
 */
function toTickFormat(data) {
  return {
    ltp: data.last_price,
    change: data.change || 0,
    change_percent: data.change
      ? (data.change / (data.last_price - data.change)) * 100
      : 0
  }
}

/**
 * Core LTP fetch from API
 * @param {string|string[]} instruments - Instrument string(s) like "NSE:NIFTY 50" or array
 * @returns {Promise<Object>} Map of instrument to price data
 */
export async function fetchLTP(instruments) {
  if (!instruments || instruments.length === 0) return {}

  const instrumentStr = Array.isArray(instruments)
    ? instruments.join(',')
    : instruments

  const response = await api.get('/api/orders/ltp', {
    params: { instruments: instrumentStr }
  })
  return response.data
}

/**
 * Fetch index prices (NIFTY 50 & NIFTY BANK) and update via callback
 * @param {Function} updateTickFn - Callback (token, tickData) to update store
 */
export async function fetchIndexPrices(updateTickFn) {
  try {
    const data = await fetchLTP('NSE:NIFTY 50,NSE:NIFTY BANK')

    if (data['NSE:NIFTY 50']) {
      updateTickFn(INDEX_TOKENS.NIFTY_50, toTickFormat(data['NSE:NIFTY 50']))
    }
    if (data['NSE:NIFTY BANK']) {
      updateTickFn(INDEX_TOKENS.NIFTY_BANK, toTickFormat(data['NSE:NIFTY BANK']))
    }
  } catch (error) {
    console.error('Failed to fetch index prices:', error)
  }
}

/**
 * Fetch prices for watchlist instruments and update via callback
 * @param {Array} instruments - Array of { exchange, tradingsymbol, token }
 * @param {Function} updateTickFn - Callback (token, tickData) to update store
 */
export async function fetchWatchlistPrices(instruments, updateTickFn) {
  if (!instruments?.length) return

  try {
    const instrumentStrs = instruments.map(
      inst => `${inst.exchange}:${inst.tradingsymbol}`
    )
    const data = await fetchLTP(instrumentStrs)

    for (const [key, priceData] of Object.entries(data)) {
      const inst = instruments.find(
        i => `${i.exchange}:${i.tradingsymbol}` === key
      )
      if (inst) {
        updateTickFn(inst.token, toTickFormat(priceData))
      }
    }
  } catch (error) {
    console.error('Failed to fetch watchlist prices:', error)
  }
}

/**
 * Fetch LTP for a strategy leg and update via callback
 * @param {Object} leg - Leg object with instrument_token and tradingsymbol
 * @param {Function} updatePriceFn - Callback (token, tickData) to update store
 */
export async function fetchLegLTP(leg, updatePriceFn) {
  if (!leg.instrument_token || !leg.tradingsymbol) return

  try {
    const instrument = `NFO:${leg.tradingsymbol}`
    const data = await fetchLTP(instrument)

    if (data[instrument]) {
      updatePriceFn(leg.instrument_token, toTickFormat(data[instrument]))
    }
  } catch (error) {
    console.debug('fetchLegLTP failed:', error.message)
  }
}

// Polling fallback state
let pollingInterval = null

/**
 * Start polling fallback when WebSocket is unavailable
 * @param {Function} callback - Async function to call on each interval
 * @param {number} intervalMs - Interval in milliseconds (default 10000)
 */
export function startPollingFallback(callback, intervalMs = 10000) {
  if (pollingInterval) return

  console.log('Starting API polling fallback')
  pollingInterval = setInterval(callback, intervalMs)
}

/**
 * Stop polling fallback
 */
export function stopPollingFallback() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
    console.log('Stopped API polling fallback')
  }
}

/**
 * Check if polling is currently active
 * @returns {boolean}
 */
export function isPollingActive() {
  return pollingInterval !== null
}
