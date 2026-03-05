<template>
  <div class="adjustment-cost-card">
    <div class="card-header">
      <h3 class="card-title">Adjustment Cost Tracking</h3>
      <span class="info-icon" title="Tracks the cumulative cost of adjustments vs original premium. Professional traders avoid exceeding 50% of original premium.">
        ℹ️
      </span>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Loading adjustment costs...</span>
    </div>

    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span>{{ error }}</span>
    </div>

    <div v-else-if="summary" class="cost-summary">
      <!-- Alert Badge -->
      <div class="alert-badge" :class="`alert-${summary.alert_level}`">
        <span class="alert-icon">{{ getAlertIcon(summary.alert_level) }}</span>
        <span class="alert-text">{{ summary.alert_message }}</span>
      </div>

      <!-- Key Metrics -->
      <div class="metrics-grid">
        <div class="metric-item">
          <span class="metric-label">Original Premium</span>
          <span class="metric-value">₹{{ formatNumber(summary.original_premium) }}</span>
        </div>

        <div class="metric-item">
          <span class="metric-label">Total Adjustment Cost</span>
          <span class="metric-value cost-value">₹{{ formatNumber(summary.total_adjustment_cost) }}</span>
        </div>

        <div class="metric-item">
          <span class="metric-label">Cost Percentage</span>
          <span class="metric-value" :class="getCostPercentageClass(summary.adjustment_cost_pct)">
            {{ summary.adjustment_cost_pct.toFixed(1) }}%
          </span>
        </div>

        <div class="metric-item">
          <span class="metric-label">Net Potential Profit</span>
          <span class="metric-value" :class="summary.net_potential_profit >= 0 ? 'positive' : 'negative'">
            ₹{{ formatNumber(summary.net_potential_profit) }}
          </span>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-section">
        <div class="progress-header">
          <span class="progress-label">Cost as % of Original Premium</span>
          <span class="progress-value">{{ summary.adjustment_cost_pct.toFixed(1) }}%</span>
        </div>
        <div class="progress-bar-container">
          <div
            class="progress-bar"
            :class="`progress-${summary.alert_level}`"
            :style="{ width: Math.min(summary.adjustment_cost_pct, 100) + '%' }"
          ></div>
          <!-- Warning threshold marker -->
          <div
            class="threshold-marker"
            :style="{ left: summary.warning_threshold_pct + '%' }"
            :title="`Warning threshold: ${summary.warning_threshold_pct}%`"
          >
            <div class="threshold-line"></div>
            <span class="threshold-label">{{ summary.warning_threshold_pct }}%</span>
          </div>
        </div>
        <div class="progress-legend">
          <span class="legend-item">
            <span class="legend-dot success"></span>
            Low (&lt;25%)
          </span>
          <span class="legend-item">
            <span class="legend-dot info"></span>
            Moderate (25-50%)
          </span>
          <span class="legend-item">
            <span class="legend-dot warning"></span>
            High (50-75%)
          </span>
          <span class="legend-item">
            <span class="legend-dot danger"></span>
            Excessive (&gt;75%)
          </span>
        </div>
      </div>

      <!-- Adjustments History -->
      <div v-if="summary.adjustments && summary.adjustments.length > 0" class="adjustments-section">
        <h4 class="section-title">Adjustment History ({{ summary.adjustments.length }})</h4>
        <div class="adjustments-list">
          <div
            v-for="(adjustment, index) in summary.adjustments"
            :key="index"
            class="adjustment-item"
          >
            <div class="adjustment-header">
              <span class="adjustment-index">#{{ index + 1 }}</span>
              <span class="adjustment-action">{{ formatActionType(adjustment.action_type) }}</span>
              <span class="adjustment-cost" :class="adjustment.cost > 0 ? 'cost-debit' : 'cost-credit'">
                {{ adjustment.cost > 0 ? '-' : '+' }}₹{{ formatNumber(Math.abs(adjustment.cost)) }}
              </span>
            </div>
            <div class="adjustment-details">
              <span class="adjustment-time">{{ formatTimestamp(adjustment.timestamp) }}</span>
              <span class="adjustment-reason">{{ adjustment.reason }}</span>
              <span class="adjustment-status" :class="`status-${adjustment.status}`">{{ adjustment.status }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="no-adjustments">
        <span class="info-icon">ℹ️</span>
        <span>No adjustments have been made yet</span>
      </div>
    </div>

    <div v-else class="no-data">
      <span>No adjustment cost data available</span>
    </div>
  </div>
</template>

<script>
import api from '@/services/api'

export default {
  name: 'AdjustmentCostCard',
  props: {
    strategyId: {
      type: Number,
      required: true
    },
    autoRefresh: {
      type: Boolean,
      default: false
    },
    refreshInterval: {
      type: Number,
      default: 10000 // 10 seconds
    }
  },
  data() {
    return {
      summary: null,
      loading: false,
      error: null,
      refreshTimer: null
    }
  },
  mounted() {
    this.fetchAdjustmentCosts()

    if (this.autoRefresh) {
      this.startAutoRefresh()
    }
  },
  beforeUnmount() {
    this.stopAutoRefresh()
  },
  methods: {
    async fetchAdjustmentCosts() {
      this.loading = true
      this.error = null

      try {
        const response = await api.get(`/api/v1/autopilot/analytics/${this.strategyId}/adjustment-costs`)
        this.summary = response.data
      } catch (err) {
        this.error = err.response?.data?.detail || err.message || 'Failed to load adjustment costs'
        console.error('Error fetching adjustment costs:', err)
      } finally {
        this.loading = false
      }
    },

    formatNumber(value) {
      if (!value) return '0'
      return new Intl.NumberFormat('en-IN').format(Math.abs(value))
    },

    formatActionType(actionType) {
      const typeMap = {
        'roll_strike': 'Roll Strike',
        'roll_expiry': 'Roll Expiry',
        'add_hedge': 'Add Hedge',
        'close_leg': 'Close Leg',
        'scale_down': 'Scale Down',
        'scale_up': 'Scale Up',
        'exit_all': 'Exit All'
      }
      return typeMap[actionType] || actionType
    },

    formatTimestamp(timestamp) {
      const date = new Date(timestamp)
      return date.toLocaleString('en-IN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    getAlertIcon(level) {
      const icons = {
        success: '✓',
        info: 'ℹ️',
        warning: '⚠️',
        danger: '🚨'
      }
      return icons[level] || 'ℹ️'
    },

    getCostPercentageClass(percentage) {
      if (percentage >= 75) return 'danger'
      if (percentage >= 50) return 'warning'
      if (percentage >= 25) return 'info'
      return 'success'
    },

    startAutoRefresh() {
      this.refreshTimer = setInterval(() => {
        this.fetchAdjustmentCosts()
      }, this.refreshInterval)
    },

    stopAutoRefresh() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
        this.refreshTimer = null
      }
    }
  }
}
</script>

<style scoped>
.adjustment-cost-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0;
}

.info-icon {
  font-size: 0.875rem;
  color: #718096;
  cursor: help;
}

.loading-state,
.error-state,
.no-data,
.no-adjustments {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: #718096;
}

.error-state {
  color: #e53e3e;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e2e8f0;
  border-top-color: #3182ce;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Alert Badge */
.alert-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.alert-success {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #86efac;
}

.alert-info {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.alert-warning {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.alert-danger {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-label {
  font-size: 0.75rem;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a202c;
}

.metric-value.cost-value {
  color: #e53e3e;
}

.metric-value.positive {
  color: #16a34a;
}

.metric-value.negative {
  color: #dc2626;
}

.metric-value.success {
  color: #16a34a;
}

.metric-value.info {
  color: #2563eb;
}

.metric-value.warning {
  color: #d97706;
}

.metric-value.danger {
  color: #dc2626;
}

/* Progress Bar */
.progress-section {
  margin-bottom: 1.5rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.progress-label {
  font-size: 0.875rem;
  color: #4a5568;
}

.progress-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1a202c;
}

.progress-bar-container {
  position: relative;
  height: 24px;
  background: #e2e8f0;
  border-radius: 12px;
  overflow: visible;
  margin-bottom: 0.75rem;
}

.progress-bar {
  height: 100%;
  border-radius: 12px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.progress-success {
  background: linear-gradient(90deg, #10b981, #059669);
}

.progress-info {
  background: linear-gradient(90deg, #3b82f6, #2563eb);
}

.progress-warning {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.progress-danger {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.threshold-marker {
  position: absolute;
  top: -4px;
  transform: translateX(-50%);
  z-index: 10;
}

.threshold-line {
  width: 2px;
  height: 32px;
  background: #64748b;
  margin: 0 auto;
}

.threshold-label {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.625rem;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.progress-legend {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: #64748b;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.success {
  background: #10b981;
}

.legend-dot.info {
  background: #3b82f6;
}

.legend-dot.warning {
  background: #f59e0b;
}

.legend-dot.danger {
  background: #ef4444;
}

/* Adjustments Section */
.adjustments-section {
  border-top: 1px solid #e2e8f0;
  padding-top: 1.5rem;
}

.section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.adjustments-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 300px;
  overflow-y: auto;
}

.adjustment-item {
  padding: 0.75rem;
  background: #f7fafc;
  border-radius: 6px;
  border-left: 3px solid #cbd5e0;
}

.adjustment-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.adjustment-index {
  font-size: 0.75rem;
  color: #718096;
  font-weight: 600;
}

.adjustment-action {
  font-size: 0.875rem;
  font-weight: 600;
  color: #2d3748;
  flex: 1;
}

.adjustment-cost {
  font-size: 0.875rem;
  font-weight: 700;
}

.cost-debit {
  color: #dc2626;
}

.cost-credit {
  color: #16a34a;
}

.adjustment-details {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: #64748b;
}

.adjustment-time,
.adjustment-reason {
  flex-shrink: 0;
}

.adjustment-status {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-pending {
  background: #fef3c7;
  color: #78350f;
}

.status-failed {
  background: #fee2e2;
  color: #991b1b;
}
</style>
