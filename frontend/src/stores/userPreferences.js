/**
 * User Preferences Pinia Store
 *
 * Manages user preferences and settings
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useUserPreferencesStore = defineStore('userPreferences', {
  state: () => ({
    preferences: {
      pnl_grid_interval: 100,  // Default value
      market_data_source: 'smartapi'  // Default to SmartAPI
    },
    loading: false,
    saving: false,
    error: null
  }),

  getters: {
    pnlGridInterval: (state) => state.preferences?.pnl_grid_interval || 100,
    marketDataSource: (state) => state.preferences?.market_data_source || 'smartapi'
  },

  actions: {
    /**
     * Fetch user preferences from API
     */
    async fetchPreferences() {
      this.loading = true
      this.error = null

      try {
        const response = await api.get('/api/user/preferences/')
        this.preferences = response.data
        return this.preferences
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Update user preferences
     *
     * @param {Object} updates - Preference updates
     * @returns {Object} Updated preferences
     */
    async updatePreferences(updates) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put('/api/user/preferences/', updates)
        this.preferences = response.data
        return this.preferences
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * Update P/L grid interval
     *
     * @param {number} interval - 50 or 100
     */
    async updatePnlGridInterval(interval) {
      if (interval !== 50 && interval !== 100) {
        throw new Error('Interval must be either 50 or 100')
      }

      return await this.updatePreferences({
        pnl_grid_interval: interval
      })
    },

    /**
     * Update market data source
     *
     * @param {string} source - 'smartapi' or 'kite'
     */
    async updateMarketDataSource(source) {
      if (source !== 'smartapi' && source !== 'kite') {
        throw new Error('Source must be either "smartapi" or "kite"')
      }

      return await this.updatePreferences({
        market_data_source: source
      })
    }
  }
})
