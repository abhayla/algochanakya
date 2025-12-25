/**
 * AI Configuration Pinia Store
 *
 * Manages state for AI autonomous trading configuration including
 * autonomy settings, deployment schedule, position sizing, and limits.
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAIConfigStore = defineStore('aiConfig', {
  state: () => ({
    // Configuration
    config: null,
    defaultConfig: null,

    // Available strategies
    availableStrategies: [],

    // UI State
    loading: false,
    saving: false,
    error: null,
    validationErrors: {},

    // Claude API key validation
    claudeKeyValid: null,
    claudeKeyValidating: false,

    // Paper trading status
    paperTradingStatus: null
  }),

  getters: {
    /**
     * Check if AI is enabled
     */
    isAIEnabled: (state) => state.config?.ai_enabled ?? false,

    /**
     * Get autonomy mode (paper/live)
     */
    autonomyMode: (state) => state.config?.autonomy_mode ?? 'paper',

    /**
     * Check if user can graduate to live trading
     */
    canGraduateToLive: (state) => {
      if (!state.paperTradingStatus) return false

      const { paper_trades_completed, paper_win_rate, paper_graduation_approved } = state.paperTradingStatus

      // Check all criteria
      const tradesComplete = paper_trades_completed >= 25
      const winRateGood = paper_win_rate >= 55
      const approved = paper_graduation_approved

      return tradesComplete && winRateGood && approved
    },

    /**
     * Get confidence tier for a given score
     * @param {number} score - Confidence score (0-100)
     * @returns {object|null} - Matching tier or null
     */
    confidenceTierForScore: (state) => (score) => {
      if (!state.config?.confidence_tiers) return null

      return state.config.confidence_tiers.find(
        tier => tier.min <= score && score <= tier.max
      ) || null
    },

    /**
     * Calculate lots for a confidence score
     * @param {number} confidence - Confidence score (0-100)
     * @returns {number} - Calculated lot size
     */
    lotsForConfidence: (state) => (confidence) => {
      if (!state.config) return 0

      // Check minimum confidence threshold
      if (confidence < state.config.min_confidence_to_trade) {
        return 0
      }

      // Fixed sizing mode
      if (state.config.sizing_mode === 'fixed') {
        return state.config.base_lots
      }

      // Tiered sizing mode
      if (state.config.sizing_mode === 'tiered') {
        const tier = state.config.confidence_tiers?.find(
          t => t.min <= confidence && confidence <= t.max
        )

        if (!tier) return 0

        return Math.floor(state.config.base_lots * tier.multiplier)
      }

      // Kelly (placeholder)
      if (state.config.sizing_mode === 'kelly') {
        console.warn('Kelly sizing not yet implemented')
        return state.config.base_lots
      }

      return state.config.base_lots
    },

    /**
     * Check if deployment should happen today
     * @param {Date} date - Date to check (defaults to today)
     * @returns {boolean}
     */
    shouldDeployToday: (state) => (date = new Date()) => {
      if (!state.config?.auto_deploy_enabled) return false

      const dayOfWeek = date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()
      return state.config.deploy_days?.includes(dayOfWeek) ?? false
    },

    /**
     * Get graduation progress percentage
     */
    graduationProgress: (state) => {
      if (!state.paperTradingStatus) return 0

      const { paper_trades_completed, paper_win_rate } = state.paperTradingStatus

      const tradesProgress = Math.min((paper_trades_completed / 25) * 100, 100)
      const winRateProgress = Math.min((paper_win_rate / 55) * 100, 100)

      return Math.floor((tradesProgress + winRateProgress) / 2)
    }
  },

  actions: {
    /**
     * Fetch user's AI configuration
     */
    async fetchConfig() {
      this.loading = true
      this.error = null

      try {
        const response = await api.get('/api/v1/ai/config')
        this.config = response.data
        console.log('[AI Config] Fetched configuration:', this.config)
      } catch (error) {
        console.error('[AI Config] Error fetching config:', error)
        this.error = error.response?.data?.detail || 'Failed to load AI configuration'
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * Save configuration updates
     * @param {object} updates - Partial configuration updates
     */
    async saveConfig(updates) {
      this.saving = true
      this.error = null
      this.validationErrors = {}

      try {
        const response = await api.put('/api/v1/ai/config', updates)
        this.config = response.data
        console.log('[AI Config] Saved configuration:', this.config)
        return true
      } catch (error) {
        console.error('[AI Config] Error saving config:', error)

        // Handle validation errors
        if (error.response?.status === 400) {
          this.validationErrors = error.response.data.detail || {}
          this.error = 'Validation failed. Please check your inputs.'
        } else {
          this.error = error.response?.data?.detail || 'Failed to save configuration'
        }

        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * Fetch default configuration template
     */
    async fetchDefaults() {
      try {
        const response = await api.get('/api/v1/ai/config/defaults')
        this.defaultConfig = response.data
        console.log('[AI Config] Fetched defaults:', this.defaultConfig)
      } catch (error) {
        console.error('[AI Config] Error fetching defaults:', error)
        throw error
      }
    },

    /**
     * Fetch available strategy templates
     */
    async fetchAvailableStrategies() {
      try {
        const response = await api.get('/api/v1/ai/config/strategies')
        this.availableStrategies = response.data
        console.log('[AI Config] Fetched strategies:', this.availableStrategies.length)
      } catch (error) {
        console.error('[AI Config] Error fetching strategies:', error)
        throw error
      }
    },

    /**
     * Update allowed strategies
     * @param {number[]} strategyIds - Array of strategy template IDs
     */
    async updateStrategies(strategyIds) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put('/api/v1/ai/config/strategies', strategyIds)
        this.config = response.data
        console.log('[AI Config] Updated allowed strategies:', strategyIds)
        return true
      } catch (error) {
        console.error('[AI Config] Error updating strategies:', error)
        this.error = error.response?.data?.detail || 'Failed to update strategies'
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * Update position sizing configuration
     * @param {object} sizingConfig - Position sizing configuration
     */
    async updateSizing(sizingConfig) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put('/api/v1/ai/config/sizing', sizingConfig)
        this.config = response.data
        console.log('[AI Config] Updated sizing config:', sizingConfig)
        return true
      } catch (error) {
        console.error('[AI Config] Error updating sizing:', error)
        this.error = error.response?.data?.detail || 'Failed to update sizing'
        throw error
      } finally {
        this.saving = false
      }
    },

    /**
     * Validate Claude API key
     * @param {string} apiKey - Claude API key to validate
     * @returns {object} - { valid: boolean, message: string }
     */
    async validateClaudeKey(apiKey) {
      this.claudeKeyValidating = true

      try {
        const response = await api.post('/api/v1/ai/config/validate-claude', { api_key: apiKey })
        this.claudeKeyValid = response.data.valid

        console.log('[AI Config] Claude key validation:', response.data)
        return response.data
      } catch (error) {
        console.error('[AI Config] Error validating Claude key:', error)
        this.claudeKeyValid = false
        return {
          valid: false,
          message: 'Validation failed'
        }
      } finally {
        this.claudeKeyValidating = false
      }
    },

    /**
     * Fetch paper trading graduation status
     */
    async fetchPaperTradingStatus() {
      try {
        const response = await api.get('/api/v1/ai/config/paper-trading/status')
        this.paperTradingStatus = response.data
        console.log('[AI Config] Fetched paper trading status:', this.paperTradingStatus)
      } catch (error) {
        console.error('[AI Config] Error fetching paper status:', error)
        throw error
      }
    },

    /**
     * Reset configuration to defaults
     */
    async resetToDefaults() {
      if (!this.defaultConfig) {
        await this.fetchDefaults()
      }

      // Map defaults to update format
      const updates = {
        ai_enabled: false,
        autonomy_mode: 'paper',
        auto_deploy_enabled: this.defaultConfig.deployment.auto_deploy_enabled,
        deploy_time: this.defaultConfig.deployment.deploy_time,
        deploy_days: this.defaultConfig.deployment.deploy_days,
        skip_event_days: this.defaultConfig.deployment.skip_event_days,
        skip_weekly_expiry: this.defaultConfig.deployment.skip_weekly_expiry,
        sizing_mode: this.defaultConfig.sizing.sizing_mode,
        base_lots: this.defaultConfig.sizing.base_lots,
        confidence_tiers: this.defaultConfig.sizing.confidence_tiers,
        max_lots_per_strategy: this.defaultConfig.limits.max_lots_per_strategy,
        max_lots_per_day: this.defaultConfig.limits.max_lots_per_day,
        max_strategies_per_day: this.defaultConfig.limits.max_strategies_per_day,
        min_confidence_to_trade: this.defaultConfig.limits.min_confidence_to_trade,
        max_vix_to_trade: this.defaultConfig.limits.max_vix_to_trade,
        min_dte_to_enter: this.defaultConfig.limits.min_dte_to_enter,
        weekly_loss_limit: this.defaultConfig.limits.weekly_loss_limit
      }

      return await this.saveConfig(updates)
    },

    /**
     * Clear error state
     */
    clearError() {
      this.error = null
      this.validationErrors = {}
    }
  }
})
