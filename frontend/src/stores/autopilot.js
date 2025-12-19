/**
 * AutoPilot Pinia Store
 *
 * Reference: docs/autopilot/component-design.md
 */
import { defineStore } from 'pinia'
import api from '@/services/api'
import { fetchLegLTP as fetchLegLTPFromAPI } from '@/composables/usePriceFallback'

export const useAutopilotStore = defineStore('autopilot', {
  state: () => ({
    // Strategies
    strategies: [],
    currentStrategy: null,

    // Dashboard
    dashboardSummary: null,

    // Settings
    settings: null,

    // Activity logs
    recentLogs: [],

    // UI State
    loading: false,
    saving: false,
    error: null,

    // Pagination
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0
    },

    // Filters
    filters: {
      status: null,
      underlying: null
    },

    // Builder State
    builder: {
      step: 1,
      strategy: createEmptyStrategy(),
      validation: {},
      expiry: null
    },

    // Options data for leg configuration
    expiries: [],
    strikes: {},  // { expiry_date: [strike1, strike2, ...] }
    livePrices: {},  // { instrument_token: { ltp, change, change_percent } }

    // Lot sizes per underlying
    lotSizes: {
      'NIFTY': 75,
      'BANKNIFTY': 15,
      'FINNIFTY': 25,
      'SENSEX': 10
    },

    // Leg selection for bulk actions
    selectedLegIndices: [],

    // Phase 5: Option Chain & Position Legs
    optionChain: {
      underlying: 'NIFTY',
      expiry: null,
      data: null,
      loading: false,
      error: null,
      cached: false
    },

    positionLegs: {
      legs: [],
      loading: false,
      error: null
    },

    suggestions: {
      list: [],
      loading: false,
      error: null
    },

    whatIfSimulation: {
      scenarios: [],
      comparison: null,
      loading: false,
      error: null
    },

    payoffChart: {
      data: null,
      mode: 'expiry', // 'expiry' or 'current'
      loading: false,
      error: null
    }
  }),

  getters: {
    activeStrategies: (state) =>
      state.strategies.filter(s => ['active', 'waiting', 'pending'].includes(s.status)),

    draftStrategies: (state) =>
      state.strategies.filter(s => s.status === 'draft'),

    completedStrategies: (state) =>
      state.strategies.filter(s => ['completed', 'error', 'expired'].includes(s.status)),

    hasActiveStrategies: (state) =>
      state.strategies.some(s => ['active', 'waiting', 'pending'].includes(s.status)),

    todayPnL: (state) =>
      state.dashboardSummary?.today_total_pnl || 0,

    riskStatus: (state) =>
      state.dashboardSummary?.risk_metrics?.status || 'safe',

    isKiteConnected: (state) =>
      state.dashboardSummary?.kite_connected || false,

    canCreateStrategy: (state) => {
      if (!state.settings || !state.dashboardSummary) return true
      const active = state.dashboardSummary.active_strategies +
                     state.dashboardSummary.waiting_strategies
      return active < state.settings.max_active_strategies
    },

    // Leg configuration getters
    lotSize: (state) => state.lotSizes[state.builder.strategy.underlying] || 75,

    totalQty: (state) => {
      const legs = state.builder.strategy.legs_config
      const lotSize = state.lotSizes[state.builder.strategy.underlying] || 75
      return legs.reduce((sum, leg) => sum + ((leg.lots || 1) * lotSize), 0)
    }
  },

  actions: {
    // ========================================================================
    // STRATEGIES
    // ========================================================================

    async fetchStrategies(options = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          page: options.page || this.pagination.page,
          page_size: options.pageSize || this.pagination.pageSize,
          ...this.filters
        }

        // Remove null values
        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/strategies', { params })

        this.strategies = response.data.data
        this.pagination = {
          page: response.data.page,
          pageSize: response.data.page_size,
          total: response.data.total,
          totalPages: response.data.total_pages
        }
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchStrategy(id) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/strategies/${id}`)
        this.currentStrategy = response.data.data
        return this.currentStrategy
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createStrategy(strategyData) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/strategies', strategyData)
        const newStrategy = response.data.data

        // Add to list
        this.strategies.unshift(newStrategy)

        return newStrategy
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async updateStrategy(id, updates) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put(`/api/v1/autopilot/strategies/${id}`, updates)
        const updated = response.data.data

        // Update in list
        const index = this.strategies.findIndex(s => s.id === id)
        if (index !== -1) {
          this.strategies[index] = updated
        }

        // Update current if same
        if (this.currentStrategy?.id === id) {
          this.currentStrategy = updated
        }

        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async deleteStrategy(id) {
      this.saving = true
      this.error = null

      try {
        await api.delete(`/api/v1/autopilot/strategies/${id}`)

        // Remove from list
        this.strategies = this.strategies.filter(s => s.id !== id)

        // Clear current if same
        if (this.currentStrategy?.id === id) {
          this.currentStrategy = null
        }
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async activateStrategy(id, options = {}) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/activate`, {
          confirm: true,
          paper_trading: options.paperTrading || false
        })

        const updated = response.data.data
        this.updateStrategyInList(id, updated)

        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async pauseStrategy(id) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/pause`)
        const updated = response.data.data
        this.updateStrategyInList(id, updated)
        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async resumeStrategy(id) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/resume`)
        const updated = response.data.data
        this.updateStrategyInList(id, updated)
        return updated
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async cloneStrategy(id, newName = null) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${id}/clone`, {
          new_name: newName,
          reset_schedule: true
        })

        const cloned = response.data.data
        this.strategies.unshift(cloned)

        return cloned
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // DASHBOARD
    // ========================================================================

    async fetchDashboardSummary() {
      this.loading = true
      this.error = null

      try {
        const response = await api.get('/api/v1/autopilot/dashboard/summary')
        this.dashboardSummary = response.data.data
        return this.dashboardSummary
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    // ========================================================================
    // SETTINGS
    // ========================================================================

    async fetchSettings() {
      this.loading = true
      this.error = null

      try {
        const response = await api.get('/api/v1/autopilot/settings')
        this.settings = response.data.data
        return this.settings
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateSettings(updates) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put('/api/v1/autopilot/settings', updates)
        this.settings = response.data.data
        return this.settings
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // KILL SWITCH (Phase 3 Enhanced)
    // ========================================================================

    async activateKillSwitch() {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/kill-switch')
        // Refresh strategies after kill switch
        await this.fetchStrategies()
        await this.fetchDashboardSummary()
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async getKillSwitchStatus() {
      try {
        const response = await api.get('/api/v1/autopilot/kill-switch/status')
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async triggerKillSwitch(reason = null, force = false) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/kill-switch/trigger', {
          reason,
          force
        })
        // Refresh strategies after kill switch
        await this.fetchStrategies()
        await this.fetchDashboardSummary()
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async resetKillSwitch() {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/kill-switch/reset')
        await this.fetchDashboardSummary()
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // CONFIRMATIONS (Phase 3)
    // ========================================================================

    async fetchPendingConfirmations(strategyId = null) {
      try {
        const params = strategyId ? { strategy_id: strategyId } : {}
        const response = await api.get('/api/v1/autopilot/confirmations', { params })
        return response.data.data || []
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async confirmAction(confirmationId) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/confirmations/${confirmationId}/confirm`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async rejectAction(confirmationId, reason = null) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/confirmations/${confirmationId}/reject`, {
          reason
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // ADJUSTMENTS (Phase 3)
    // ========================================================================

    async triggerManualAdjustment(strategyId, action, description = null, executionMode = 'auto') {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${strategyId}/adjust`, {
          action,
          description,
          execution_mode: executionMode
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async fetchAdjustmentHistory(strategyId, page = 1, pageSize = 20) {
      try {
        const response = await api.get(`/api/v1/autopilot/strategies/${strategyId}/adjustments`, {
          params: { page, page_size: pageSize }
        })
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    // ========================================================================
    // TRAILING STOP (Phase 3)
    // ========================================================================

    async fetchTrailingStopStatus(strategyId) {
      try {
        const response = await api.get(`/api/v1/autopilot/strategies/${strategyId}/trailing-stop`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async updateTrailingStopConfig(strategyId, config) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put(`/api/v1/autopilot/strategies/${strategyId}/trailing-stop`, config)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // POSITION SIZING (Phase 3)
    // ========================================================================

    async calculatePositionSize(request) {
      try {
        const response = await api.post('/api/v1/autopilot/position-sizing/calculate', request)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    // ========================================================================
    // GREEKS (Phase 3)
    // ========================================================================

    async fetchStrategyGreeks(strategyId) {
      try {
        const response = await api.get(`/api/v1/autopilot/strategies/${strategyId}/greeks`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async calculateGreeks(legs, spotPrice) {
      try {
        const response = await api.post('/api/v1/autopilot/greeks/calculate', legs, {
          params: { spot_price: spotPrice }
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    // ========================================================================
    // LOGS
    // ========================================================================

    async fetchRecentLogs(limit = 10) {
      try {
        const response = await api.get('/api/v1/autopilot/logs', {
          params: { limit }
        })
        this.recentLogs = response.data.data || []
        return this.recentLogs
      } catch (error) {
        // Non-critical, don't show error
        console.error('Failed to fetch logs:', error)
        return []
      }
    },

    // ========================================================================
    // BUILDER
    // ========================================================================

    initBuilder(strategy = null) {
      if (strategy) {
        this.builder.strategy = { ...strategy }
        this.builder.expiry = strategy.expiry_date || null
      } else {
        this.builder.strategy = createEmptyStrategy()
        this.builder.expiry = null
      }
      this.builder.step = 1
      this.builder.validation = {}
    },

    setBuilderStep(step) {
      this.builder.step = step
    },

    updateBuilderStrategy(updates) {
      this.builder.strategy = {
        ...this.builder.strategy,
        ...updates
      }
    },

    addLeg(leg) {
      this.builder.strategy.legs_config.push({
        id: `leg_${Date.now()}`,
        ...leg
      })
    },

    updateLeg(index, updates) {
      if (this.builder.strategy.legs_config[index]) {
        this.builder.strategy.legs_config[index] = {
          ...this.builder.strategy.legs_config[index],
          ...updates
        }
      }
    },

    removeLeg(index) {
      this.builder.strategy.legs_config.splice(index, 1)
    },

    addCondition(condition) {
      this.builder.strategy.entry_conditions.conditions.push({
        id: `cond_${Date.now()}`,
        enabled: true,
        ...condition
      })
    },

    updateCondition(index, updates) {
      if (this.builder.strategy.entry_conditions.conditions[index]) {
        this.builder.strategy.entry_conditions.conditions[index] = {
          ...this.builder.strategy.entry_conditions.conditions[index],
          ...updates
        }
      }
    },

    removeCondition(index) {
      this.builder.strategy.entry_conditions.conditions.splice(index, 1)
    },

    // ========================================================================
    // LEG OPTIONS DATA
    // ========================================================================

    async fetchExpiries() {
      const underlying = this.builder.strategy.underlying
      try {
        const response = await api.get(`/api/options/expiries?underlying=${underlying}`)
        this.expiries = response.data.expiries

        // Only set builder.expiry if not already set (new strategy)
        if (this.expiries.length > 0 && !this.builder.expiry) {
          this.builder.expiry = this.expiries[0]
          await this.fetchStrikes(this.expiries[0])
        } else if (this.builder.expiry) {
          // Fetch strikes for the existing expiry
          await this.fetchStrikes(this.builder.expiry)
        }

        // Populate leg expiry dates after expiries are loaded
        // This ensures legs get expiry_date when editing an existing strategy
        this.populateLegExpiries()
      } catch (error) {
        console.error('Failed to fetch expiries:', error)
        this.expiries = []
        if (!this.builder.expiry) {
          this.builder.expiry = null
        }
      }
    },

    async fetchStrikes(expiry) {
      const underlying = this.builder.strategy.underlying
      try {
        const response = await api.get(`/api/options/strikes?underlying=${underlying}&expiry=${expiry}`)
        this.strikes[expiry] = response.data.strikes.map(s => parseFloat(s))
      } catch (error) {
        console.error('Failed to fetch strikes:', error)
        this.strikes[expiry] = []
      }
    },

    /**
     * Calculate expiry date from expiry type
     * @param {string} expiryType - 'current_week', 'next_week', or 'monthly'
     * @returns {string|null} Expiry date string or null
     */
    getExpiryFromType(expiryType) {
      const expiries = this.expiries
      if (!expiries || expiries.length === 0) return null

      // Sort expiries by date
      const sortedExpiries = [...expiries].sort((a, b) => new Date(a) - new Date(b))

      if (expiryType === 'current_week') {
        // Find the nearest Thursday (or first available expiry)
        return sortedExpiries[0] || null
      } else if (expiryType === 'next_week') {
        // Find the second Thursday (or second available expiry)
        return sortedExpiries[1] || sortedExpiries[0] || null
      } else if (expiryType === 'monthly') {
        // Find monthly expiry (last expiry of each month)
        // Group expiries by month and find the last one
        const monthlyExpiries = []
        let lastMonth = null

        for (let i = 0; i < sortedExpiries.length; i++) {
          const exp = sortedExpiries[i]
          const [year, month] = exp.split('-').map(Number)
          const monthKey = `${year}-${month.toString().padStart(2, '0')}`

          // Check if next expiry is in a different month
          const nextExp = sortedExpiries[i + 1]
          if (nextExp) {
            const [nextYear, nextMonth] = nextExp.split('-').map(Number)
            const nextMonthKey = `${nextYear}-${nextMonth.toString().padStart(2, '0')}`

            // If next expiry is in different month, current is last of this month
            if (nextMonthKey !== monthKey) {
              monthlyExpiries.push(exp)
            }
          } else {
            // Last expiry overall
            monthlyExpiries.push(exp)
          }
        }

        return monthlyExpiries[0] || sortedExpiries[sortedExpiries.length - 1] || null
      }
      return sortedExpiries[0] || null
    },

    /**
     * Populate expiry_date on all legs from strategy expiry_type
     * Called after expiries are loaded when editing a strategy
     */
    populateLegExpiries() {
      const expiry = this.getExpiryFromType(this.builder.strategy.expiry_type) || this.builder.expiry
      if (!expiry) return

      // Update legs to trigger reactivity
      this.builder.strategy.legs_config = this.builder.strategy.legs_config.map(leg => ({
        ...leg,
        expiry_date: leg.expiry_date || expiry
      }))
    },

    async fetchInstrumentToken(expiry, strike, contractType) {
      const underlying = this.builder.strategy.underlying
      try {
        const response = await api.get('/api/options/instrument', {
          params: { underlying, expiry, strike, contract_type: contractType }
        })
        return {
          instrument_token: response.data.instrument_token,
          tradingsymbol: response.data.tradingsymbol
        }
      } catch (error) {
        console.error('Failed to fetch instrument token:', error)
        return { instrument_token: null, tradingsymbol: null }
      }
    },

    async fetchLegLTP(leg) {
      if (!leg.instrument_token || !leg.tradingsymbol) return
      if (this.livePrices[leg.instrument_token]?.ltp) return

      await fetchLegLTPFromAPI(leg, (token, tick) => {
        this.livePrices[token] = tick
      })
    },

    updateLivePrices(prices) {
      prices.forEach(p => {
        this.livePrices[p.token] = {
          ltp: p.ltp,
          change: p.change,
          change_percent: p.change_percent
        }
      })
    },

    getLegCMP(leg) {
      if (!leg.instrument_token) return null
      return this.livePrices[leg.instrument_token]?.ltp || null
    },

    getLegExitPnL(leg) {
      const cmp = this.getLegCMP(leg)
      if (cmp === null || !leg.entry_price) return null
      const qty = (leg.lots || 1) * this.lotSize
      const multiplier = leg.transaction_type === 'BUY' ? 1 : -1
      return (cmp - parseFloat(leg.entry_price)) * qty * multiplier
    },

    // ========================================================================
    // LEG SELECTION
    // ========================================================================

    toggleLegSelection(index) {
      const idx = this.selectedLegIndices.indexOf(index)
      if (idx > -1) {
        this.selectedLegIndices.splice(idx, 1)
      } else {
        this.selectedLegIndices.push(index)
      }
    },

    selectAllLegs() {
      this.selectedLegIndices = this.builder.strategy.legs_config.map((_, i) => i)
    },

    deselectAllLegs() {
      this.selectedLegIndices = []
    },

    removeSelectedLegs() {
      const sorted = [...this.selectedLegIndices].sort((a, b) => b - a)
      sorted.forEach(i => this.builder.strategy.legs_config.splice(i, 1))
      this.selectedLegIndices = []
    },

    // ========================================================================
    // HELPERS
    // ========================================================================

    updateStrategyInList(id, updated) {
      const index = this.strategies.findIndex(s => s.id === id)
      if (index !== -1) {
        this.strategies[index] = updated
      }
      if (this.currentStrategy?.id === id) {
        this.currentStrategy = updated
      }
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },

    clearFilters() {
      this.filters = { status: null, underlying: null }
    },

    clearError() {
      this.error = null
    },

    // ========================================================================
    // PHASE 4: TEMPLATES
    // ========================================================================

    async fetchTemplates(options = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          page: options.page || 1,
          page_size: options.pageSize || 20,
          category: options.category || null,
          underlying: options.underlying || null,
          market_outlook: options.marketOutlook || null,
          risk_level: options.riskLevel || null,
          search: options.search || null
        }

        // Remove null values
        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/templates', { params })
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchTemplate(id) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/templates/${id}`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchTemplateCategories() {
      try {
        const response = await api.get('/api/v1/autopilot/templates/categories')
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async fetchPopularTemplates(limit = 10) {
      try {
        const response = await api.get('/api/v1/autopilot/templates/popular', {
          params: { limit }
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async deployTemplate(templateId, options = {}) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/templates/${templateId}/deploy`, options)
        const newStrategy = response.data.data

        // Add to strategies list
        this.strategies.unshift(newStrategy)

        return newStrategy
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async createTemplate(templateData) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/templates', templateData)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async rateTemplate(templateId, rating, review = null) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/templates/${templateId}/rate`, {
          rating,
          review
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // PHASE 4: TRADE JOURNAL
    // ========================================================================

    async fetchJournalTrades(options = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          page: options.page || 1,
          page_size: options.pageSize || 20,
          start_date: options.startDate || null,
          end_date: options.endDate || null,
          underlying: options.underlying || null,
          exit_reason: options.exitReason || null,
          tags: options.tags ? options.tags.join(',') : null,
          is_open: options.isOpen,
          min_pnl: options.minPnl || null,
          max_pnl: options.maxPnl || null
        }

        // Remove null/undefined values
        Object.keys(params).forEach(key => {
          if (params[key] === null || params[key] === undefined) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/journal', { params })
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchJournalTrade(tradeId) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/journal/${tradeId}`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchJournalStats(options = {}) {
      try {
        const params = {
          start_date: options.startDate || null,
          end_date: options.endDate || null
        }

        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/journal/stats', { params })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async updateJournalTrade(tradeId, updates) {
      this.saving = true
      this.error = null

      try {
        const response = await api.put(`/api/v1/autopilot/journal/${tradeId}`, updates)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async updateTradeNotes(tradeId, notes) {
      return this.updateJournalTrade(tradeId, { notes })
    },

    async exportJournalTrades(options = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          start_date: options.startDate || null,
          end_date: options.endDate || null,
          underlying: options.underlying || null,
          exit_reason: options.exitReason || null,
          format: options.format || 'csv'
        }

        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/journal/export', { params })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    // ========================================================================
    // PHASE 4: ANALYTICS
    // ========================================================================

    async fetchAnalyticsPerformance(period = '30d', underlying = null) {
      this.loading = true
      this.error = null

      try {
        const params = { period }
        if (underlying) params.underlying = underlying

        const response = await api.get('/api/v1/autopilot/analytics/performance', { params })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchDailyPnL(options = {}) {
      try {
        const params = {
          start_date: options.startDate || null,
          end_date: options.endDate || null
        }

        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/analytics/daily-pnl', { params })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async fetchAnalyticsByStrategy(period = '30d') {
      try {
        const response = await api.get('/api/v1/autopilot/analytics/by-strategy', {
          params: { period }
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async fetchAnalyticsByWeekday(period = '30d') {
      try {
        const response = await api.get('/api/v1/autopilot/analytics/by-weekday', {
          params: { period }
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    async fetchDrawdownAnalysis(period = '30d') {
      try {
        const response = await api.get('/api/v1/autopilot/analytics/drawdown', {
          params: { period }
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    // ========================================================================
    // PHASE 4: REPORTS
    // ========================================================================

    async fetchReports(options = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          page: options.page || 1,
          page_size: options.pageSize || 20,
          report_type: options.reportType || null
        }

        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/reports', { params })
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchReport(reportId) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/reports/${reportId}`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async generateReport(reportData) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/reports/generate', reportData)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async deleteReport(reportId) {
      this.saving = true
      this.error = null

      try {
        await api.delete(`/api/v1/autopilot/reports/${reportId}`)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async fetchTaxSummary(financialYear) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/reports/tax-summary/${financialYear}`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    // ========================================================================
    // PHASE 4: BACKTESTS
    // ========================================================================

    async fetchBacktests(options = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          page: options.page || 1,
          page_size: options.pageSize || 20,
          status: options.status || null
        }

        Object.keys(params).forEach(key => {
          if (params[key] === null) delete params[key]
        })

        const response = await api.get('/api/v1/autopilot/backtests', { params })
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchBacktest(backtestId) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/backtests/${backtestId}`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createBacktest(backtestData) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post('/api/v1/autopilot/backtests', backtestData)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async cancelBacktest(backtestId) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/backtests/${backtestId}/cancel`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async deleteBacktest(backtestId) {
      this.saving = true
      this.error = null

      try {
        await api.delete(`/api/v1/autopilot/backtests/${backtestId}`)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // PHASE 4: STRATEGY SHARING
    // ========================================================================

    async shareStrategy(strategyId, shareMode = 'link') {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/strategies/${strategyId}/share`, {
          share_mode: shareMode
        })
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async unshareStrategy(strategyId) {
      this.saving = true
      this.error = null

      try {
        await api.delete(`/api/v1/autopilot/strategies/${strategyId}/share`)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    async fetchSharedStrategy(shareToken) {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/shared/${shareToken}`)
        return response.data.data
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async cloneSharedStrategy(shareToken, options = {}) {
      this.saving = true
      this.error = null

      try {
        const response = await api.post(`/api/v1/autopilot/shared/${shareToken}/clone`, options)
        const newStrategy = response.data.data

        // Add to strategies list
        this.strategies.unshift(newStrategy)

        return newStrategy
      } catch (error) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.saving = false
      }
    },

    // ========================================================================
    // PHASE 5: OPTION CHAIN
    // ========================================================================

    async fetchOptionChain(underlying, expiry, useCache = true) {
      this.optionChain.loading = true
      this.optionChain.error = null

      try {
        const response = await api.get(
          `/api/v1/autopilot/option-chain/${underlying}/${expiry}`,
          { params: { use_cache: useCache } }
        )

        this.optionChain.data = response.data.data
        this.optionChain.underlying = underlying
        this.optionChain.expiry = expiry
        this.optionChain.cached = response.data.data.cached || false

        return this.optionChain.data
      } catch (error) {
        this.optionChain.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.optionChain.loading = false
      }
    },

    clearOptionChain() {
      this.optionChain.data = null
      this.optionChain.error = null
      this.optionChain.cached = false
    },

    // ========================================================================
    // PHASE 5: POSITION LEGS
    // ========================================================================

    async fetchPositionLegs(strategyId, statusFilter = null) {
      this.positionLegs.loading = true
      this.positionLegs.error = null

      try {
        const params = statusFilter ? { status_filter: statusFilter } : {}

        const response = await api.get(
          `/api/v1/autopilot/legs/strategies/${strategyId}/legs`,
          { params }
        )

        this.positionLegs.legs = response.data.data
        return this.positionLegs.legs
      } catch (error) {
        this.positionLegs.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.positionLegs.loading = false
      }
    },

    // ========================================================================
    // PHASE 5: SUGGESTIONS
    // ========================================================================

    async fetchSuggestions(strategyId) {
      this.suggestions.loading = true
      this.suggestions.error = null

      try {
        const response = await api.get(
          `/api/v1/autopilot/suggestions/strategies/${strategyId}`
        )

        this.suggestions.list = response.data.data
        return this.suggestions.list
      } catch (error) {
        this.suggestions.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.suggestions.loading = false
      }
    },

    async dismissSuggestion(suggestionId) {
      try {
        await api.post(`/api/v1/autopilot/suggestions/${suggestionId}/dismiss`)

        // Remove from list
        this.suggestions.list = this.suggestions.list.filter(s => s.id !== suggestionId)
      } catch (error) {
        this.suggestions.error = error.response?.data?.detail || error.message
        throw error
      }
    },

    // ========================================================================
    // PHASE 5: WHAT-IF SIMULATION
    // ========================================================================

    async simulateAdjustment(strategyId, scenarioType, params) {
      this.whatIfSimulation.loading = true
      this.whatIfSimulation.error = null

      try {
        const response = await api.post(
          `/api/v1/autopilot/simulate/${strategyId}/${scenarioType}`,
          params
        )

        return response.data.data
      } catch (error) {
        this.whatIfSimulation.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.whatIfSimulation.loading = false
      }
    },

    async compareScenarios(strategyId, scenarios) {
      this.whatIfSimulation.loading = true
      this.whatIfSimulation.error = null

      try {
        const response = await api.post(
          `/api/v1/autopilot/simulate/${strategyId}/compare`,
          { scenarios }
        )

        this.whatIfSimulation.comparison = response.data.data
        return this.whatIfSimulation.comparison
      } catch (error) {
        this.whatIfSimulation.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.whatIfSimulation.loading = false
      }
    },

    // ========================================================================
    // PHASE 5: PAYOFF CHART
    // ========================================================================

    async fetchPayoffChart(strategyId, mode = 'expiry') {
      this.payoffChart.loading = true
      this.payoffChart.error = null

      try {
        const response = await api.get(
          `/api/v1/autopilot/payoff/${strategyId}`,
          { params: { mode } }
        )

        this.payoffChart.data = response.data.data
        this.payoffChart.mode = mode

        return this.payoffChart.data
      } catch (error) {
        this.payoffChart.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.payoffChart.loading = false
      }
    }
  }
})

// Helper function to create empty strategy
function createEmptyStrategy() {
  return {
    name: '',
    description: '',
    underlying: 'NIFTY',
    expiry_type: 'current_week',
    expiry_date: null,
    lots: 1,
    position_type: 'intraday',
    legs_config: [],
    entry_conditions: {
      logic: 'AND',
      conditions: []
    },
    adjustment_rules: [],
    order_settings: {
      order_type: 'MARKET',
      execution_style: 'sequential',
      leg_sequence: [],
      delay_between_legs: 2,
      slippage_protection: {
        enabled: true,
        max_per_leg_pct: 2.0,
        max_total_pct: 5.0,
        on_exceed: 'retry',
        max_retries: 3
      },
      on_leg_failure: 'stop'
    },
    risk_settings: {
      max_loss: null,
      max_loss_pct: null,
      trailing_stop: { enabled: false },
      max_margin: null,
      time_stop: null
    },
    entry_requirements: {
      min_dte: null,
      max_dte: null,
      require_delta_neutral: false,
      delta_neutral_min: -0.10,
      delta_neutral_max: 0.10
    },
    monitoring_config: {
      spot_distance_pe_threshold: 2.0,
      spot_distance_ce_threshold: 2.0,
      enable_toast_alerts: true
    },
    schedule_config: {
      activation_mode: 'always',
      active_days: ['MON', 'TUE', 'WED', 'THU', 'FRI'],
      start_time: '09:15',
      end_time: '15:30',
      expiry_days_only: false
    },
    priority: 100
  }
}
