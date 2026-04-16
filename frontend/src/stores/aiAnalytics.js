import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useAIAnalyticsStore = defineStore('aiAnalytics', () => {
  // Per-feature loading refs (keep UI sections unblocked from each other)
  const autonomyLoading = ref(false)
  const capitalRiskLoading = ref(false)
  const regimeStrengthsLoading = ref(false)
  const analyticsLoading = ref(false)
  const paperTradingLoading = ref(false)
  const error = ref(null)

  async function fetchAutonomyStatus() {
    autonomyLoading.value = true
    try {
      const response = await api.get('/api/v1/ai/autonomy/status')
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        data: null,
      }
    } finally {
      autonomyLoading.value = false
    }
  }

  async function fetchAutonomyLevels() {
    try {
      const response = await api.get('/api/v1/ai/autonomy/levels')
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        data: null,
      }
    }
  }

  async function fetchCapitalRisk(params = {}) {
    capitalRiskLoading.value = true
    try {
      const response = await api.get('/api/v1/ai/capital-risk/current', { params })
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        data: null,
      }
    } finally {
      capitalRiskLoading.value = false
    }
  }

  async function fetchRegimeStrengths(params = {}) {
    regimeStrengthsLoading.value = true
    try {
      const response = await api.get('/api/v1/ai/regime-quality/regime-strengths', { params })
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        data: null,
      }
    } finally {
      regimeStrengthsLoading.value = false
    }
  }

  async function fetchAIPerformance(startDate, endDate) {
    try {
      const response = await api.get('/api/v1/ai/analytics/performance', {
        params: { start_date: startDate, end_date: endDate },
      })
      return { success: true, data: response.data }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || err.message, data: null }
    }
  }

  async function fetchByRegime(startDate, endDate) {
    try {
      const response = await api.get('/api/v1/ai/analytics/by-regime', {
        params: { start_date: startDate, end_date: endDate },
      })
      return { success: true, data: response.data }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || err.message, data: null }
    }
  }

  async function fetchByStrategy(startDate, endDate) {
    try {
      const response = await api.get('/api/v1/ai/analytics/by-strategy', {
        params: { start_date: startDate, end_date: endDate },
      })
      return { success: true, data: response.data }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || err.message, data: null }
    }
  }

  async function fetchDecisions(startDate, endDate) {
    try {
      const response = await api.get('/api/v1/ai/analytics/decisions', {
        params: { start_date: startDate, end_date: endDate },
      })
      return { success: true, data: response.data }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || err.message, data: null }
    }
  }

  async function fetchLearningProgress() {
    try {
      const response = await api.get('/api/v1/ai/analytics/learning')
      return { success: true, data: response.data }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || err.message, data: null }
    }
  }

  async function triggerAIDeploy(payload) {
    try {
      const response = await api.post('/api/v1/ai/deploy/trigger', payload)
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        status: err.response?.status,
        data: null,
      }
    }
  }

  async function exitPaperTrade(payload) {
    try {
      const response = await api.post('/api/v1/ai/deploy/paper-trade/exit', payload)
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        data: null,
      }
    }
  }

  async function fetchPaperTrades() {
    paperTradingLoading.value = true
    try {
      const response = await api.get('/api/v1/ai/deploy/paper-trade/list')
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message,
        data: null,
      }
    } finally {
      paperTradingLoading.value = false
    }
  }

  return {
    autonomyLoading,
    capitalRiskLoading,
    regimeStrengthsLoading,
    analyticsLoading,
    paperTradingLoading,
    error,
    fetchAutonomyStatus,
    fetchAutonomyLevels,
    fetchCapitalRisk,
    fetchRegimeStrengths,
    fetchAIPerformance,
    fetchByRegime,
    fetchByStrategy,
    fetchDecisions,
    fetchLearningProgress,
    triggerAIDeploy,
    exitPaperTrade,
    fetchPaperTrades,
  }
})
