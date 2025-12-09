/**
 * AutoPilot Pinia Store
 *
 * Reference: docs/autopilot/component-design.md
 */
import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAutopilotStore = defineStore('autopilot', {
  state: () => ({
    // Strategies
    strategies: [],
    currentStrategy: null,

    // Dashboard
    dashboardSummary: null,

    // Settings
    settings: null,

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
      validation: {}
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
    // BUILDER
    // ========================================================================

    initBuilder(strategy = null) {
      if (strategy) {
        this.builder.strategy = { ...strategy }
      } else {
        this.builder.strategy = createEmptyStrategy()
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
