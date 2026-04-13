/**
 * Broker Preferences Pinia Store
 *
 * Manages broker selection preferences:
 * - market_data_source: which broker provides live market data
 * - order_broker:       which broker executes orders
 *
 * Platform-default data flow: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

/** Human-readable labels for each source value */
const SOURCE_LABELS = {
  platform: 'Platform Default',
  smartapi: 'SmartAPI',
  kite: 'Kite Connect',
  upstox: 'Upstox',
  dhan: 'Dhan',
  fyers: 'Fyers',
  paytm: 'Paytm Money',
}

/** Human-readable labels for order brokers */
const BROKER_LABELS = {
  kite: 'Kite Connect (Zerodha)',
  angel: 'AngelOne (SmartAPI)',
  upstox: 'Upstox',
  dhan: 'Dhan',
  fyers: 'Fyers',
  paytm: 'Paytm Money',
}

export const useBrokerPreferencesStore = defineStore('brokerPreferences', {
  state: () => ({
    preferences: null,   // null until fetched
    credentialStatus: null, // { smartapi: bool, kite: bool, ... }
    activeSource: null,  // actual broker in use (set from WebSocket 'connected' message)
    loading: false,
    saving: false,
    error: null,
  }),

  getters: {
    /** The currently active market data source (fallback: 'platform') */
    marketDataSource: (state) => state.preferences?.market_data_source ?? 'platform',

    /** The currently selected order broker (may be null / not set) */
    orderBroker: (state) => state.preferences?.order_broker ?? null,

    /** True when user is relying on platform-default data (no personal broker) */
    isUsingPlatformDefault: (state) => {
      const src = state.preferences?.market_data_source ?? 'platform'
      return src === 'platform'
    },

    /** Human-readable label for the active data source.
     *  Prefers the real-time source reported by WebSocket over stored preference. */
    activeSourceLabel: (state) => {
      const src = state.activeSource ?? state.preferences?.market_data_source ?? 'platform'
      return SOURCE_LABELS[src] ?? src
    },

    /** Human-readable label for the order broker */
    orderBrokerLabel: (state) => {
      const broker = state.preferences?.order_broker
      if (!broker) return 'Not configured'
      return BROKER_LABELS[broker] ?? broker
    },

    /** Available market data source options for UI dropdowns */
    marketDataSourceOptions: () => Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label })),

    /** Available order broker options for UI dropdowns */
    orderBrokerOptions: () => Object.entries(BROKER_LABELS).map(([value, label]) => ({ value, label })),

    /** Check if a broker has configured credentials */
    isBrokerConfigured: (state) => (broker) => {
      if (broker === 'platform') return true
      return state.credentialStatus?.[broker] ?? false
    },
  },

  actions: {
    /**
     * Fetch broker preferences from API.
     * Merges into existing preferences store.
     */
    async fetchPreferences() {
      this.loading = true
      this.error = null
      try {
        const response = await api.get('/api/user/preferences/')
        this.preferences = response.data
        return this.preferences
      } catch (error) {
        this.error = error.response?.data?.detail ?? error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update broker preferences (partial update supported).
     *
     * @param {Object} updates - e.g. { market_data_source: 'dhan' } or { order_broker: 'upstox' }
     */
    async updatePreferences(updates) {
      this.saving = true
      this.error = null
      try {
        const response = await api.put('/api/user/preferences/', updates)
        this.preferences = response.data
        // Clear stale WebSocket activeSource so the badge immediately reflects
        // the saved preference (WebSocket will set it again once reconnected)
        if ('market_data_source' in updates) {
          this.activeSource = null
        }
        return this.preferences
      } catch (error) {
        this.error = error.response?.data?.detail ?? error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * Fetch credential status for all brokers.
     */
    async fetchCredentialStatus() {
      try {
        const response = await api.get('/api/user/preferences/broker-status')
        this.credentialStatus = response.data
        return this.credentialStatus
      } catch (error) {
        console.error('[BrokerPreferences] Failed to fetch credential status:', error)
      }
    },

    /**
     * Shortcut: set market data source.
     * @param {string} source - 'platform' | 'smartapi' | 'kite' | 'upstox' | 'dhan' | 'fyers' | 'paytm'
     */
    async setMarketDataSource(source) {
      return this.updatePreferences({ market_data_source: source })
    },

    /**
     * Shortcut: set order execution broker.
     * @param {string} broker - 'kite' | 'angel' | 'upstox' | 'dhan' | 'fyers' | 'paytm'
     */
    async setOrderBroker(broker) {
      return this.updatePreferences({ order_broker: broker })
    },

    /**
     * Update the runtime-active data source from the WebSocket 'connected' message.
     * This reflects the actual broker serving data (which may differ from preference
     * when a fallback occurred).
     * @param {string} source - e.g. 'smartapi', 'kite', 'dhan'
     */
    setActiveSource(source) {
      this.activeSource = source
    },
  },
})

export { SOURCE_LABELS, BROKER_LABELS }
