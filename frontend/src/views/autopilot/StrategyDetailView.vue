<script setup>
/**
 * AutoPilot Strategy Detail View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 3
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import ShareModal from '@/components/autopilot/common/ShareModal.vue'
import ActivateModal from '@/components/autopilot/common/ActivateModal.vue'
import LegsPanel from '@/components/autopilot/legs/LegsPanel.vue'
import SuggestionsPanel from '@/components/autopilot/suggestions/SuggestionsPanel.vue'
import AnalyticsPanel from '@/components/autopilot/analytics/AnalyticsPanel.vue'
import WhatIfModal from '@/components/autopilot/simulation/WhatIfModal.vue'
import DTEZoneIndicator from '@/components/autopilot/monitoring/DTEZoneIndicator.vue'
import GammaRiskAlert from '@/components/autopilot/monitoring/GammaRiskAlert.vue'
import BreakTradeWizard from '@/components/autopilot/adjustments/BreakTradeWizard.vue'
import ShiftLegModal from '@/components/autopilot/adjustments/ShiftLegModal.vue'
import AdjustmentCostCard from '@/components/autopilot/analytics/AdjustmentCostCard.vue'
import ActivityTimeline from '@/components/autopilot/dashboard/ActivityTimeline.vue'
import StraddlePremiumChart from '@/components/autopilot/monitoring/StraddlePremiumChart.vue'
import ThetaDecayChart from '@/components/autopilot/monitoring/ThetaDecayChart.vue'
import OrdersTab from '@/components/autopilot/orders/OrdersTab.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const route = useRoute()
const store = useAutopilotStore()

const strategyId = computed(() => parseInt(route.params.id))
const refreshInterval = ref(null)
const showExitModal = ref(false)
const showDeleteModal = ref(false)
const showShareModal = ref(false)
const showWhatIfModal = ref(false)
const showActivateModal = ref(false)
const activeTab = ref('configuration')

// Phase 5F: Adjustment Modals
const showBreakTradeWizard = ref(false)
const showShiftLegModal = ref(false)
const selectedLegForAdjustment = ref(null)
const strategyLegs = ref([])

onMounted(async () => {
  await store.fetchStrategy(strategyId.value)

  // Refresh every 5 seconds for active strategies
  refreshInterval.value = setInterval(async () => {
    if (store.currentStrategy?.status === 'active') {
      await store.fetchStrategy(strategyId.value)
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})

const handlePause = async () => {
  await store.pauseStrategy(strategyId.value)
}

const handleResume = async () => {
  await store.resumeStrategy(strategyId.value)
}

const handleEdit = () => {
  router.push(`/autopilot/strategies/${strategyId.value}/edit`)
}

const handleClone = async () => {
  const cloned = await store.cloneStrategy(strategyId.value)
  router.push(`/autopilot/strategies/${cloned.id}/edit`)
}

const handleActivate = () => {
  showActivateModal.value = true
}

const handleActivateConfirmed = async () => {
  // Modal will handle the activation and emit 'activated' event
  // Just refresh the strategy after activation
  await store.fetchStrategy(strategyId.value)
  showActivateModal.value = false
}

const handleDelete = async () => {
  await store.deleteStrategy(strategyId.value)
  showDeleteModal.value = false
  router.push('/autopilot')
}

const handleExit = async () => {
  // Force exit all positions - this would call an exit endpoint
  showExitModal.value = false
  // For now, just pause the strategy
  await store.pauseStrategy(strategyId.value)
}

const handleShare = () => {
  showShareModal.value = true
}

const closeShareModal = () => {
  showShareModal.value = false
}

const onStrategyShared = () => {
  // Refresh strategy to update share status
  store.fetchStrategy(strategyId.value)
}

const onStrategyUnshared = () => {
  // Refresh strategy to update share status
  store.fetchStrategy(strategyId.value)
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('en-IN')
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'status-badge status-active',
    waiting: 'status-badge status-waiting',
    pending: 'status-badge status-pending',
    paused: 'status-badge status-paused',
    draft: 'status-badge status-draft',
    completed: 'status-badge status-completed',
    error: 'status-badge status-error'
  }
  return classes[status] || 'status-badge status-paused'
}

// Phase 5E: DTE and Gamma Risk Calculations
const calculateDTE = computed(() => {
  if (!store.currentStrategy?.legs_config || store.currentStrategy.legs_config.length === 0) {
    return 0
  }

  // Get expiry from first leg (all legs should have same expiry in a strategy)
  const firstLeg = store.currentStrategy.legs_config[0]
  if (!firstLeg.expiry) return 0

  const expiryDate = new Date(firstLeg.expiry)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  expiryDate.setHours(0, 0, 0, 0)

  const diffTime = expiryDate - today
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

  return Math.max(0, diffDays)
})

const dteZoneConfig = computed(() => {
  const dte = calculateDTE.value

  // Determine zone
  let zone = 'early'
  let deltaWarning = 0.35
  let adjustmentEffectiveness = { rating: 'high', percentage: 90, description: 'Adjustments are highly effective' }
  let warnings = []
  let allowedActions = ['roll_strike', 'shift_strike', 'break_trade', 'add_hedge', 'close_leg', 'exit_all']
  let display = { color: 'green', icon: 'check-circle', label: 'Early Zone', badge_variant: 'success' }

  if (dte >= 21 && dte <= 45) {
    zone = 'early'
    deltaWarning = 0.35
    adjustmentEffectiveness = { rating: 'high', percentage: 90, description: 'Optimal time for adjustments' }
    warnings = []
    display = { color: 'green', icon: 'check-circle', label: 'Early Zone', badge_variant: 'success' }
  } else if (dte >= 14 && dte < 21) {
    zone = 'middle'
    deltaWarning = 0.30
    adjustmentEffectiveness = { rating: 'good', percentage: 70, description: 'Adjustments still effective' }
    warnings = ['Monitor position more closely']
    display = { color: 'blue', icon: 'info-circle', label: 'Middle Zone', badge_variant: 'info' }
  } else if (dte >= 7 && dte < 14) {
    zone = 'late'
    deltaWarning = 0.25
    adjustmentEffectiveness = { rating: 'moderate', percentage: 40, description: 'Adjustment effectiveness declining' }
    warnings = ['Gamma risk increasing', 'Consider rolling or exiting']
    allowedActions = ['close_leg', 'exit_all', 'roll_forward']
    display = { color: 'orange', icon: 'exclamation-triangle', label: 'Late Zone', badge_variant: 'warning' }
  } else {
    zone = 'expiry_week'
    deltaWarning = 0.20
    adjustmentEffectiveness = { rating: 'very_low', percentage: 10, description: 'Exit preferred over adjustments' }
    warnings = ['CRITICAL: Expiry week', 'Gamma explosion risk', 'Exit all positions to avoid assignment']
    allowedActions = ['close_leg', 'exit_all']
    display = { color: 'red', icon: 'exclamation-circle', label: 'Expiry Week', badge_variant: 'danger' }
  }

  return {
    zone,
    dte,
    delta_warning: deltaWarning,
    allowed_actions: allowedActions,
    adjustment_effectiveness: adjustmentEffectiveness,
    warnings,
    display,
    label: display.label,
    icon: display.icon
  }
})

const netGamma = computed(() => {
  return store.currentStrategy?.net_gamma || 0
})

const gammaRiskAssessment = computed(() => {
  const dte = calculateDTE.value
  const gamma = netGamma.value

  // Determine zone
  let zone = 'safe'
  if (dte <= 3) {
    zone = 'danger'
  } else if (dte <= 7) {
    zone = 'warning'
  }

  // Calculate multiplier
  let multiplier = 1.0
  if (dte <= 1) {
    multiplier = 20.0
  } else if (dte <= 3) {
    multiplier = 10.0
  } else if (dte <= 7) {
    multiplier = 3.0
  }

  // Determine risk level
  let riskLevel = 'low'
  let recommendation = 'Normal gamma behavior. Safe to hold.'

  if (zone === 'danger') {
    riskLevel = 'critical'
    recommendation = 'URGENT: Exit position immediately to avoid gamma explosion'
  } else if (zone === 'warning') {
    if (Math.abs(gamma) > 0.05) {
      riskLevel = 'high'
      recommendation = 'Consider exiting position. Adjustments become ineffective.'
    } else {
      riskLevel = 'medium'
      recommendation = 'Monitor closely. Gamma risk increasing.'
    }
  }

  return {
    zone,
    risk_level: riskLevel,
    multiplier,
    recommendation,
    dte,
    net_gamma: gamma,
    position_type: 'short' // Assuming short positions for now
  }
})

const gammaExplosionProbability = computed(() => {
  const dte = calculateDTE.value
  const gamma = netGamma.value
  const zone = gammaRiskAssessment.value.zone

  // Base probability by zone
  let baseProb = 0.05
  if (zone === 'danger') {
    baseProb = 0.80
  } else if (zone === 'warning') {
    baseProb = 0.40
  }

  // Adjust for gamma magnitude
  const gammaAdjustment = Math.min(Math.abs(gamma) * 5, 0.2)

  return Math.min(1.0, baseProb + gammaAdjustment)
})

const showRiskIndicators = computed(() => {
  // Show risk indicators when strategy is active or waiting
  return ['active', 'waiting', 'pending'].includes(store.currentStrategy?.status)
})

// Phase 5F: Adjustment Modal Handlers
const handleBreakTrade = (leg) => {
  selectedLegForAdjustment.value = leg
  showBreakTradeWizard.value = true
}

const handleShiftLeg = (leg) => {
  selectedLegForAdjustment.value = leg
  showShiftLegModal.value = true
}

const handleBreakTradeSuccess = async (result) => {
  console.log('Break trade executed:', result)
  // Refresh strategy to show updated legs
  await store.fetchStrategy(strategyId.value)
  showBreakTradeWizard.value = false
  selectedLegForAdjustment.value = null
}

const handleShiftLegSuccess = async (result) => {
  console.log('Shift leg executed:', result)
  // Refresh strategy to show updated legs
  await store.fetchStrategy(strategyId.value)
  showShiftLegModal.value = false
  selectedLegForAdjustment.value = null
}

const closeBreakTradeWizard = () => {
  showBreakTradeWizard.value = false
  selectedLegForAdjustment.value = null
}

const closeShiftLegModal = () => {
  showShiftLegModal.value = false
  selectedLegForAdjustment.value = null
}

// Format activity logs for ActivityTimeline component
const strategyActivities = computed(() => {
  // In a real implementation, this would fetch logs specific to this strategy
  // For now, using store.recentLogs filtered by strategy_id
  if (!store.recentLogs || store.recentLogs.length === 0) return []

  const severityToEventType = {
    'info': 'condition_met',
    'warning': 'alert_triggered',
    'error': 'order_rejected'
  }

  return store.recentLogs
    .filter(log => log.strategy_id === strategyId.value)
    .map(log => ({
      id: log.id,
      event_type: log.event_type || severityToEventType[log.severity] || 'condition_met',
      message: log.message,
      description: log.message,
      timestamp: log.created_at,
      created_at: log.created_at,
      strategy_name: log.strategy_name || store.currentStrategy?.name,
      underlying: log.underlying || store.currentStrategy?.underlying
    }))
})
</script>

<template>
  <KiteLayout>
  <div class="detail-page" data-testid="autopilot-strategy-detail">
    <!-- Loading -->
    <div v-if="store.loading && !store.currentStrategy" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading strategy...</p>
    </div>

    <!-- Strategy Detail -->
    <template v-else-if="store.currentStrategy">
      <!-- Header -->
      <div class="detail-header">
        <div>
          <div class="detail-title-row">
            <button
              @click="router.push('/autopilot')"
              class="back-btn"
              data-testid="autopilot-detail-back"
            >
              &larr;
            </button>
            <h1 class="page-title" data-testid="autopilot-detail-name">
              {{ store.currentStrategy.name }}
            </h1>
            <span
              :class="getStatusBadgeClass(store.currentStrategy.status)"
              data-testid="autopilot-detail-status"
            >
              {{ store.currentStrategy.status }}
            </span>
          </div>
          <p class="page-subtitle">{{ store.currentStrategy.description || 'No description' }}</p>
        </div>

        <div class="header-actions">
          <button
            @click="showWhatIfModal = true"
            data-testid="autopilot-whatif-btn"
            class="strategy-btn strategy-btn-outline"
          >
            What-If
          </button>

          <button
            v-if="store.currentStrategy.status === 'draft'"
            @click="handleEdit"
            data-testid="autopilot-detail-edit"
            class="strategy-btn strategy-btn-outline"
          >
            Edit
          </button>

          <button
            v-if="store.currentStrategy.status === 'draft'"
            @click="handleActivate"
            data-testid="autopilot-detail-activate"
            class="strategy-btn strategy-btn-success"
          >
            Activate
          </button>

          <button
            v-if="['active', 'waiting', 'pending'].includes(store.currentStrategy.status)"
            @click="handlePause"
            data-testid="autopilot-detail-pause"
            class="strategy-btn strategy-btn-warning"
          >
            Pause
          </button>

          <button
            v-if="store.currentStrategy.status === 'paused'"
            @click="handleResume"
            data-testid="autopilot-detail-resume"
            class="strategy-btn strategy-btn-success"
          >
            Resume
          </button>

          <button
            v-if="['active', 'paused'].includes(store.currentStrategy.status)"
            @click="showExitModal = true"
            data-testid="autopilot-detail-exit"
            class="strategy-btn strategy-btn-exit"
          >
            Exit
          </button>

          <button
            @click="handleClone"
            data-testid="autopilot-detail-clone"
            class="strategy-btn strategy-btn-outline"
          >
            Clone
          </button>

          <button
            @click="handleShare"
            :data-testid="store.currentStrategy.share_token ? 'autopilot-detail-unshare' : 'autopilot-detail-share'"
            class="strategy-btn strategy-btn-outline"
          >
            {{ store.currentStrategy.share_token ? 'Manage Share' : 'Share' }}
          </button>

          <button
            v-if="['draft', 'completed', 'error'].includes(store.currentStrategy.status)"
            @click="showDeleteModal = true"
            data-testid="autopilot-detail-delete"
            class="strategy-btn strategy-btn-danger"
          >
            Delete
          </button>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards-grid">
        <div class="summary-card" data-testid="autopilot-strategy-pnl">
          <p class="summary-label">Current P&L</p>
          <p :class="['summary-value-large', getPnLClass(store.currentStrategy.runtime_state?.current_pnl)]">
            {{ formatCurrency(store.currentStrategy.runtime_state?.current_pnl) }}
          </p>
        </div>

        <div class="summary-card">
          <p class="summary-label">Margin Used</p>
          <p class="summary-value-large">
            {{ formatCurrency(store.currentStrategy.runtime_state?.margin_used) }}
          </p>
        </div>

        <div class="summary-card">
          <p class="summary-label">Underlying</p>
          <p class="summary-value-large">{{ store.currentStrategy.underlying }}</p>
          <p class="summary-label">{{ store.currentStrategy.lots }} lot(s)</p>
        </div>

        <div class="summary-card">
          <p class="summary-label">Activated</p>
          <p class="summary-value">
            {{ formatDateTime(store.currentStrategy.activated_at) }}
          </p>
        </div>
      </div>

      <!-- Phase 5E: Risk Monitoring Section -->
      <div v-if="showRiskIndicators" class="risk-monitoring-section">
        <!-- DTE Zone Indicator -->
        <DTEZoneIndicator
          :dte="calculateDTE"
          :zone-config="dteZoneConfig"
        />

        <!-- Gamma Risk Alert -->
        <GammaRiskAlert
          :dte="calculateDTE"
          :net-gamma="netGamma"
          :assessment="gammaRiskAssessment"
          :explosion-probability="gammaExplosionProbability"
          :auto-hide="true"
        />
      </div>

      <!-- Tabs -->
      <div class="detail-card">
        <div class="tabs-header">
          <nav class="tabs-nav">
            <button
              @click="activeTab = 'configuration'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'configuration' }]"
              data-testid="autopilot-configuration-tab"
            >
              Configuration
            </button>
            <button
              @click="activeTab = 'legs'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'legs' }]"
              data-testid="autopilot-legs-tab"
            >
              Position Legs
            </button>
            <button
              @click="activeTab = 'orders'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'orders' }]"
              data-testid="autopilot-orders-tab-btn"
            >
              Orders
            </button>
            <button
              @click="activeTab = 'charts'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'charts' }]"
              data-testid="strategy-detail-charts-tab"
            >
              Charts
            </button>
            <button
              @click="activeTab = 'activity'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'activity' }]"
              data-testid="autopilot-activity-tab"
            >
              Activity
            </button>
            <button
              @click="activeTab = 'suggestions'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'suggestions' }]"
              data-testid="autopilot-suggestions-tab"
            >
              Suggestions
            </button>
            <button
              @click="activeTab = 'analytics'"
              :class="['tab-btn', { 'tab-btn-active': activeTab === 'analytics' }]"
              data-testid="autopilot-analytics-tab"
            >
              Analytics
            </button>
          </nav>
        </div>

        <div class="tab-content">
          <!-- Configuration Tab -->
          <div v-if="activeTab === 'configuration'">
            <!-- Legs -->
            <div class="section">
              <h3 class="section-title">Strategy Legs</h3>
              <div class="strategy-table-wrapper">
                <div class="table-scroll">
                  <table class="strategy-table">
                    <thead>
                      <tr>
                        <th>Leg</th>
                        <th>Type</th>
                        <th>Action</th>
                        <th>Strike Selection</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(leg, index) in store.currentStrategy.legs_config" :key="leg.id">
                        <td>{{ index + 1 }}</td>
                        <td>{{ leg.contract_type }}</td>
                        <td>
                          <span :class="['tag-select', leg.transaction_type === 'BUY' ? 'tag-buy' : 'tag-sell']">
                            {{ leg.transaction_type }}
                          </span>
                        </td>
                        <td>
                          <span v-if="leg.strike_price">
                            {{ leg.strike_price }}
                          </span>
                          <span v-else-if="leg.strike_selection?.mode === 'fixed'">
                            Fixed Strike
                          </span>
                          <span v-else-if="leg.strike_selection?.mode === 'atm_offset'">
                            ATM{{ leg.strike_selection.offset >= 0 ? '+' : '' }}{{ leg.strike_selection.offset }}
                          </span>
                          <span v-else-if="leg.strike_selection?.mode === 'delta_based'">
                            Delta {{ leg.strike_selection.target_delta }}
                          </span>
                          <span v-else-if="leg.strike_selection?.mode === 'premium_based'">
                            Premium ₹{{ leg.strike_selection.target_premium }}
                          </span>
                          <span v-else>
                            {{ leg.strike_selection?.mode || 'Not set' }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Entry Conditions -->
            <div class="section">
              <h3 class="section-title">Entry Conditions</h3>
              <div v-if="store.currentStrategy.entry_conditions?.conditions?.length > 0">
                <p class="logic-label">
                  Logic: {{ store.currentStrategy.entry_conditions.logic }}
                </p>
                <div class="conditions-list">
                  <div
                    v-for="(cond, index) in store.currentStrategy.entry_conditions.conditions"
                    :key="cond.id"
                    class="condition-item"
                  >
                    <span class="condition-number">{{ index + 1 }}.</span>
                    {{ cond.variable }} {{ cond.operator }} {{ cond.value }}
                    <span :class="['condition-status', cond.enabled ? 'condition-enabled' : 'condition-disabled']">
                      {{ cond.enabled ? 'Active' : 'Disabled' }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">
                <p class="empty-text">No entry conditions configured. Strategy enters immediately.</p>
                <button @click="router.push(`/autopilot/strategies/${store.currentStrategy.id}/edit`)" class="add-condition-btn">
                  + Add Entry Condition
                </button>
              </div>
            </div>

            <!-- Adjustment Rules -->
            <div class="section">
              <h3 class="section-title">Adjustment Rules</h3>
              <div v-if="store.currentStrategy.adjustment_rules?.length > 0">
                <div class="adjustment-rules-list">
                  <div
                    v-for="(rule, index) in store.currentStrategy.adjustment_rules"
                    :key="rule.name || index"
                    class="adjustment-rule-card"
                  >
                    <div class="rule-header">
                      <span class="rule-number">{{ index + 1 }}.</span>
                      <span class="rule-name">{{ rule.name }}</span>
                      <span :class="['rule-status', rule.enabled ? 'rule-enabled' : 'rule-disabled']">
                        {{ rule.enabled ? 'Active' : 'Disabled' }}
                      </span>
                    </div>
                    <div class="rule-details">
                      <div class="rule-detail">
                        <span class="detail-label">Trigger:</span>
                        <span class="detail-value">{{ rule.trigger_type }}</span>
                      </div>
                      <div class="rule-detail">
                        <span class="detail-label">Action:</span>
                        <span class="detail-value">{{ rule.action_type }}</span>
                      </div>
                      <div class="rule-detail" v-if="rule.cooldown_seconds">
                        <span class="detail-label">Cooldown:</span>
                        <span class="detail-value">{{ Math.floor(rule.cooldown_seconds / 60) }} min</span>
                      </div>
                      <div class="rule-detail" v-if="rule.max_executions">
                        <span class="detail-label">Max Executions:</span>
                        <span class="detail-value">{{ rule.max_executions }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="empty-text">No adjustment rules configured.</p>
            </div>

            <!-- Risk Settings -->
            <div class="section">
              <h3 class="section-title">Risk Settings</h3>
              <dl class="risk-grid">
                <div class="risk-item">
                  <dt class="risk-label">Max Loss</dt>
                  <dd class="risk-value">
                    {{ store.currentStrategy.risk_settings?.max_loss
                      ? formatCurrency(store.currentStrategy.risk_settings.max_loss)
                      : 'Not set' }}
                  </dd>
                </div>
                <div class="risk-item">
                  <dt class="risk-label">Max Profit</dt>
                  <dd class="risk-value">
                    {{ store.currentStrategy.risk_settings?.max_profit
                      ? formatCurrency(store.currentStrategy.risk_settings.max_profit)
                      : 'Not set' }}
                  </dd>
                </div>
                <div class="risk-item">
                  <dt class="risk-label">Max Loss %</dt>
                  <dd class="risk-value">
                    {{ store.currentStrategy.risk_settings?.max_loss_pct
                      ? store.currentStrategy.risk_settings.max_loss_pct + '%'
                      : 'Not set' }}
                  </dd>
                </div>
                <div class="risk-item">
                  <dt class="risk-label">Trailing Stop</dt>
                  <dd class="risk-value">
                    {{ store.currentStrategy.risk_settings?.trailing_stop?.enabled ? 'Enabled' : 'Disabled' }}
                  </dd>
                </div>
                <div class="risk-item">
                  <dt class="risk-label">Time Stop</dt>
                  <dd class="risk-value">
                    {{ store.currentStrategy.risk_settings?.time_stop || 'Not set' }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          <!-- Position Legs Tab -->
          <div v-if="activeTab === 'legs'">
            <LegsPanel :strategy-id="strategyId" />
          </div>

          <!-- Orders Tab -->
          <div v-if="activeTab === 'orders'">
            <OrdersTab :strategy-id="strategyId" />
          </div>

          <!-- Charts Tab -->
          <div v-if="activeTab === 'charts'" data-testid="strategy-detail-charts-section">
            <div class="charts-section">
              <!-- Greeks Summary -->
              <div class="chart-card">
                <h3 class="chart-title">Greeks Summary</h3>
                <div class="greeks-grid">
                  <div class="greek-item">
                    <span class="greek-label">Delta</span>
                    <span class="greek-value">
                      {{ store.currentStrategy?.net_delta?.toFixed(3) || '0.000' }}
                    </span>
                  </div>
                  <div class="greek-item">
                    <span class="greek-label">Gamma</span>
                    <span class="greek-value">
                      {{ store.currentStrategy?.net_gamma?.toFixed(4) || '0.0000' }}
                    </span>
                  </div>
                  <div class="greek-item">
                    <span class="greek-label">Theta</span>
                    <span class="greek-value">
                      {{ store.currentStrategy?.net_theta?.toFixed(2) || '0.00' }}
                    </span>
                  </div>
                  <div class="greek-item">
                    <span class="greek-label">Vega</span>
                    <span class="greek-value">
                      {{ store.currentStrategy?.net_vega?.toFixed(2) || '0.00' }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Premium Chart -->
              <div class="chart-card">
                <h3 class="chart-title">Premium Monitor</h3>
                <div class="chart-content">
                  <StraddlePremiumChart
                    v-if="store.currentStrategy?.id"
                    data-testid="straddle-premium-chart"
                    :strategy-id="store.currentStrategy.id"
                    :auto-refresh="store.currentStrategy.status === 'active'"
                    :refresh-interval="5000"
                  />
                  <div v-else class="chart-loading">
                    <p>Loading strategy data...</p>
                  </div>
                </div>
              </div>

              <!-- Theta Decay Chart -->
              <div class="chart-card">
                <h3 class="chart-title">Theta Decay - Expected vs Actual</h3>
                <div class="chart-content">
                  <ThetaDecayChart
                    v-if="store.currentStrategy?.id"
                    data-testid="theta-decay-chart"
                    :strategy-id="store.currentStrategy.id"
                    :auto-refresh="store.currentStrategy.status === 'active'"
                    :refresh-interval="5000"
                  />
                  <div v-else class="chart-loading">
                    <p>Loading strategy data...</p>
                  </div>
                </div>
              </div>

              <!-- P&L Curve Placeholder -->
              <div class="chart-card">
                <h3 class="chart-title">P&L Curve</h3>
                <div class="chart-placeholder">
                  <div class="placeholder-icon">💹</div>
                  <p class="placeholder-text">P&L curve will be displayed here</p>
                  <p class="placeholder-subtext">Real-time P&L visualization across spot prices</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Activity Tab -->
          <div v-if="activeTab === 'activity'">
            <ActivityTimeline
              :activities="strategyActivities"
              :max-items="20"
            />
          </div>

          <!-- Suggestions Tab -->
          <div v-if="activeTab === 'suggestions'">
            <SuggestionsPanel :strategy-id="strategyId" />
          </div>

          <!-- Analytics Tab -->
          <div v-if="activeTab === 'analytics'">
            <AnalyticsPanel :strategy-id="strategyId" />

            <!-- Phase 5G: Adjustment Cost Tracking -->
            <div style="margin-top: 1.5rem;">
              <AdjustmentCostCard
                :strategy-id="strategyId"
                :auto-refresh="store.currentStrategy?.status === 'active'"
                :refresh-interval="10000"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Timestamps -->
      <div class="timestamps">
        <p>Created: {{ formatDateTime(store.currentStrategy.created_at) }}</p>
        <p>Last Updated: {{ formatDateTime(store.currentStrategy.updated_at) }}</p>
        <p>Version: {{ store.currentStrategy.version }}</p>
      </div>
    </template>

    <!-- Error -->
    <div v-if="store.error" class="error-banner">
      <p class="error-text">{{ store.error }}</p>
      <button @click="store.clearError" class="error-dismiss">Dismiss</button>
    </div>

    <!-- Delete Modal -->
    <div
      v-if="showDeleteModal"
      class="modal-overlay"
      data-testid="autopilot-delete-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title">Delete Strategy</h3>
        <p class="modal-text">
          Are you sure you want to delete "{{ store.currentStrategy?.name }}"? This action cannot be undone.
        </p>
        <div class="modal-actions">
          <button
            @click="showDeleteModal = false"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="handleDelete"
            data-testid="autopilot-delete-confirm"
            class="strategy-btn strategy-btn-danger"
          >
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Exit Modal -->
    <div
      v-if="showExitModal"
      class="modal-overlay"
      data-testid="autopilot-exit-modal"
    >
      <div class="modal-content">
        <h3 class="modal-title">Exit Strategy</h3>
        <p class="modal-text">
          Are you sure you want to exit all positions for "{{ store.currentStrategy?.name }}"?
          This will close all active positions at market price.
        </p>
        <div class="modal-actions">
          <button
            @click="showExitModal = false"
            class="strategy-btn strategy-btn-outline"
          >
            Cancel
          </button>
          <button
            @click="handleExit"
            data-testid="autopilot-exit-confirm"
            class="strategy-btn strategy-btn-exit"
          >
            Exit All Positions
          </button>
        </div>
      </div>
    </div>

    <!-- Share Modal -->
    <ShareModal
      :show="showShareModal"
      :strategy-id="store.currentStrategy?.id"
      :strategy-name="store.currentStrategy?.name"
      :is-shared="!!store.currentStrategy?.share_token"
      :existing-token="store.currentStrategy?.share_token"
      @close="closeShareModal"
      @shared="onStrategyShared"
      @unshared="onStrategyUnshared"
    />

    <!-- Activate Modal -->
    <ActivateModal
      :show="showActivateModal"
      :strategy-id="store.currentStrategy?.id"
      :strategy-name="store.currentStrategy?.name"
      @close="showActivateModal = false"
      @activated="handleActivateConfirmed"
    />

    <!-- What-If Modal -->
    <WhatIfModal
      v-if="showWhatIfModal"
      :strategy-id="strategyId"
      @close="showWhatIfModal = false"
    />

    <!-- Phase 5F: Break Trade Wizard -->
    <BreakTradeWizard
      v-if="showBreakTradeWizard"
      :strategy-id="strategyId"
      :legs="strategyLegs"
      @close="closeBreakTradeWizard"
      @success="handleBreakTradeSuccess"
    />

    <!-- Phase 5F: Shift Leg Modal -->
    <ShiftLegModal
      v-if="showShiftLegModal && selectedLegForAdjustment"
      :strategy-id="strategyId"
      :leg="selectedLegForAdjustment"
      :spot-price="store.currentStrategy?.runtime_state?.spot_price"
      @close="closeShiftLegModal"
      @success="handleShiftLegSuccess"
    />
  </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.detail-page {
  padding: 24px;
}

/* ===== Loading State ===== */
.loading-state {
  text-align: center;
  padding: 48px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 2px solid var(--kite-border);
  border-top-color: var(--kite-blue);
  border-radius: 50%;
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: var(--kite-text-secondary);
}

/* ===== Header ===== */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  color: var(--kite-text-secondary);
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
}

.back-btn:hover {
  color: var(--kite-text-primary);
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.page-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* ===== Status Badges ===== */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-active {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.status-waiting {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.status-pending {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

.status-paused {
  background: var(--kite-gray-light, #f5f5f5);
  color: var(--kite-text-secondary);
}

.status-draft {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.status-completed {
  background: #f3e5f5;
  color: #7b1fa2;
}

.status-error {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

/* ===== P&L Colors ===== */
.pnl-profit {
  color: var(--kite-green);
}

.pnl-loss {
  color: var(--kite-red);
}

.pnl-neutral {
  color: var(--kite-text-secondary);
}

/* ===== Summary Cards ===== */
.summary-cards-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .summary-cards-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.summary-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.summary-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.summary-value-large {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

/* ===== Phase 5E: Risk Monitoring Section ===== */
.risk-monitoring-section {
  margin-bottom: 24px;
}

/* ===== Detail Card ===== */
.detail-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* ===== Tabs ===== */
.tabs-header {
  border-bottom: 1px solid var(--kite-border);
}

.tabs-nav {
  display: flex;
  margin-bottom: -1px;
}

.tab-btn {
  padding: 12px 24px;
  border: none;
  background: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab-btn:hover {
  color: var(--kite-text-primary);
}

.tab-btn-active {
  color: var(--kite-blue);
  border-bottom-color: var(--kite-blue);
}

.tab-content {
  padding: 24px;
}

/* ===== Sections ===== */
.section {
  margin-bottom: 24px;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

/* ===== Entry Conditions ===== */
.logic-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
  margin-bottom: 8px;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-item {
  background: var(--kite-table-hover);
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 0.875rem;
}

.condition-number {
  font-weight: 500;
}

.condition-status {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.condition-enabled {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.condition-disabled {
  background: var(--kite-gray-light, #f5f5f5);
  color: var(--kite-text-secondary);
}

.empty-state {
  display: flex;
  align-items: center;
  gap: 12px;
}

.empty-text {
  color: var(--kite-text-secondary);
  margin: 0;
}

.add-condition-btn {
  padding: 6px 12px;
  background: var(--kite-blue);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.add-condition-btn:hover {
  background: var(--kite-primary-dark);
}

/* ===== Adjustment Rules ===== */
.adjustment-rules-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.adjustment-rule-card {
  background: var(--kite-table-hover);
  border-radius: 6px;
  padding: 12px 16px;
  border-left: 3px solid var(--kite-blue);
}

.rule-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.rule-number {
  font-weight: 600;
  color: var(--kite-text-secondary);
}

.rule-name {
  font-weight: 500;
  color: var(--kite-text-primary);
}

.rule-status {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.rule-enabled {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.rule-disabled {
  background: var(--kite-gray-light, #f5f5f5);
  color: var(--kite-text-secondary);
}

.rule-details {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.rule-detail {
  display: flex;
  gap: 4px;
  font-size: 0.875rem;
}

.detail-label {
  color: var(--kite-text-secondary);
}

.detail-value {
  color: var(--kite-text-primary);
  font-weight: 500;
}

/* ===== Risk Settings ===== */
.risk-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .risk-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.risk-item {
  display: flex;
  flex-direction: column;
}

.risk-label {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.risk-value {
  font-weight: 500;
  color: var(--kite-text-primary);
}

/* ===== Timestamps ===== */
.timestamps {
  margin-top: 16px;
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

/* ===== Error Banner ===== */
.error-banner {
  margin-top: 16px;
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red-border, #ffcdd2);
  border-radius: 4px;
  padding: 16px;
}

.error-text {
  color: var(--kite-red);
}

.error-dismiss {
  color: var(--kite-red);
  background: none;
  border: none;
  text-decoration: underline;
  margin-top: 8px;
  cursor: pointer;
}

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  padding: 24px;
  max-width: 448px;
  width: calc(100% - 32px);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 16px;
}

.modal-text {
  color: var(--kite-text-secondary);
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Button Styles ===== */
.strategy-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.strategy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.strategy-btn-primary {
  background: var(--kite-blue);
  color: white;
  border-color: var(--kite-blue);
}

.strategy-btn-primary:hover:not(:disabled) {
  background: var(--kite-blue-dark, #1565c0);
}

.strategy-btn-success {
  background: var(--kite-green);
  color: white;
  border-color: var(--kite-green);
}

.strategy-btn-success:hover:not(:disabled) {
  background: #388e3c;
}

.strategy-btn-warning {
  background: var(--kite-orange);
  color: white;
  border-color: var(--kite-orange);
}

.strategy-btn-warning:hover:not(:disabled) {
  background: #f57c00;
}

.strategy-btn-danger {
  background: var(--kite-red);
  color: white;
  border-color: var(--kite-red);
}

.strategy-btn-danger:hover:not(:disabled) {
  background: #c62828;
}

.strategy-btn-exit {
  background: var(--kite-orange);
  color: white;
  border-color: var(--kite-orange);
}

.strategy-btn-exit:hover:not(:disabled) {
  background: #e65100;
}

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

/* ===== Charts Section ===== */
.charts-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  border: 1px solid var(--kite-border);
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--kite-border-light);
}

/* ===== Greeks Grid ===== */
.greeks-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .greeks-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.greek-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 8px;
  border: 1px solid var(--kite-border-light);
}

.greek-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--kite-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.greek-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--kite-text-primary);
}

/* ===== Chart Content ===== */
.chart-content {
  min-height: 300px;
  padding: 16px;
  position: relative;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: var(--kite-text-secondary);
  font-size: 14px;
}

/* ===== Chart Placeholder ===== */
.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 8px;
  border: 2px dashed var(--kite-border);
}

.placeholder-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.placeholder-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin: 0 0 8px 0;
}

.placeholder-subtext {
  font-size: 14px;
  color: var(--kite-text-secondary);
  margin: 0;
  max-width: 400px;
}
</style>
