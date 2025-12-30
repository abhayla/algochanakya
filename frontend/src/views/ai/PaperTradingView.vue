<template>
  <KiteLayout>
    <AISubNav />
    <div class="paper-trading-view" data-testid="paper-trading-view">
    <div class="page-header">
      <h1 class="page-title">Paper Trading Dashboard</h1>
      <div class="header-actions">
        <button
          @click="triggerDeploy"
          :disabled="deploying || !aiEnabled"
          class="btn-deploy"
          data-testid="btn-trigger-deploy"
        >
          <i class="fas fa-rocket"></i>
          {{ deploying ? 'Deploying...' : 'Trigger Deploy' }}
        </button>
        <MarketRegimeIndicator
          v-if="currentRegime"
          :regimeType="currentRegime.regime_type"
          :confidence="currentRegime.confidence"
          :reasoning="currentRegime.reasoning"
          data-testid="header-regime"
        />
        <PositionSyncStatus
          :status="syncStatus"
          :lastSyncTime="lastSyncTime"
          :lastSyncData="positionAnalysis"
          :showDetails="false"
          data-testid="header-sync"
        />
      </div>
    </div>

    <div class="dashboard-content">
      <!-- Graduation Progress Section -->
      <section class="section-graduation">
        <GraduationProgress
          :tradesCompleted="graduationData.tradesCompleted"
          :tradesTarget="graduationData.tradesTarget"
          :winRate="graduationData.winRate"
          :winRateTarget="graduationData.winRateTarget"
          :totalPnl="graduationData.totalPnl"
          :startDate="graduationData.startDate"
          :graduationApproved="graduationData.approved"
          @graduate="handleGraduation"
          data-testid="graduation-section"
        />
      </section>

      <!-- Paper Trades Section -->
      <section class="section-paper-trades" data-testid="paper-trades-section">
        <div class="section-header">
          <h2 class="section-title">Paper Trades</h2>
          <button class="btn-refresh" @click="fetchPaperTrades" :disabled="loadingTrades" data-testid="btn-refresh-trades">
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingTrades }"></i>
            Refresh
          </button>
        </div>

        <div v-if="paperTrades.active.length === 0 && paperTrades.closed.length === 0" class="empty-message">
          <i class="fas fa-file-invoice"></i>
          <p>No paper trades yet. Click "Trigger Deploy" to start.</p>
        </div>

        <div v-else class="trades-content">
          <!-- Active Trades -->
          <div v-if="paperTrades.active.length > 0" class="trades-subsection">
            <h3 class="subsection-title">Active Trades ({{ paperTrades.active.length }})</h3>
            <div class="table-wrapper">
              <table class="paper-trades-table" data-testid="paper-trades-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Entry Time</th>
                    <th>Regime</th>
                    <th>Confidence</th>
                    <th>Lots</th>
                    <th>Sizing</th>
                    <th>Entry Premium</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="trade in paperTrades.active" :key="trade.id" :data-testid="`paper-trade-row-${trade.id}`">
                    <td class="td-strategy">{{ trade.strategy_name }}</td>
                    <td>{{ formatDateTime(trade.entry_time) }}</td>
                    <td><span class="badge-regime">{{ trade.entry_regime }}</span></td>
                    <td>{{ trade.entry_confidence.toFixed(1) }}%</td>
                    <td>{{ trade.lots }}</td>
                    <td><span class="badge-sizing">{{ trade.sizing_mode }}</span></td>
                    <td class="td-premium">₹{{ trade.entry_total_premium.toFixed(2) }}</td>
                    <td>
                      <button
                        @click="exitTrade(trade.id)"
                        class="btn-exit"
                        :data-testid="`btn-exit-trade-${trade.id}`"
                      >
                        <i class="fas fa-sign-out-alt"></i> Exit
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Closed Trades -->
          <div v-if="paperTrades.closed.length > 0" class="trades-subsection">
            <h3 class="subsection-title">Closed Trades ({{ paperTrades.closed.length }})</h3>
            <div class="table-wrapper">
              <table class="paper-trades-table" data-testid="closed-trades-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Entry Time</th>
                    <th>Exit Time</th>
                    <th>Regime</th>
                    <th>Lots</th>
                    <th>Entry Premium</th>
                    <th>Exit Premium</th>
                    <th>P&L</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="trade in paperTrades.closed" :key="trade.id" :data-testid="`closed-trade-row-${trade.id}`">
                    <td class="td-strategy">{{ trade.strategy_name }}</td>
                    <td>{{ formatDateTime(trade.entry_time) }}</td>
                    <td>{{ formatDateTime(trade.exit_time) }}</td>
                    <td><span class="badge-regime">{{ trade.entry_regime }}</span></td>
                    <td>{{ trade.lots }}</td>
                    <td class="td-premium">₹{{ trade.entry_total_premium.toFixed(2) }}</td>
                    <td class="td-premium">₹{{ (trade.exit_total_premium || 0).toFixed(2) }}</td>
                    <td :class="pnlClass(trade.realized_pnl)">{{ formatPnl(trade.realized_pnl) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Summary Stats -->
          <div v-if="paperTrades.summary" class="trades-summary" data-testid="trades-summary">
            <div class="summary-card">
              <div class="summary-label">Total Trades</div>
              <div class="summary-value">{{ paperTrades.summary.total_trades }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">Win Rate</div>
              <div class="summary-value">{{ paperTrades.summary.win_rate.toFixed(1) }}%</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">Total P&L</div>
              <div class="summary-value" :class="pnlClass(paperTrades.summary.total_pnl)">
                {{ formatPnl(paperTrades.summary.total_pnl) }}
              </div>
            </div>
            <div class="summary-card">
              <div class="summary-label">Avg P&L/Trade</div>
              <div class="summary-value" :class="pnlClass(paperTrades.summary.avg_pnl_per_trade)">
                {{ formatPnl(paperTrades.summary.avg_pnl_per_trade) }}
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Main Content Grid -->
      <div class="content-grid">
        <!-- Recent Decisions -->
        <section class="section-decisions">
          <div class="section-header">
            <h2 class="section-title">Recent AI Decisions</h2>
            <button class="btn-view-all" @click="viewAllDecisions" data-testid="btn-view-all-decisions">
              View All <i class="fas fa-arrow-right"></i>
            </button>
          </div>

          <div v-if="decisions.length === 0" class="empty-message">
            <i class="fas fa-robot"></i>
            <p>No AI decisions yet</p>
          </div>

          <div v-else class="decisions-list">
            <AIDecisionCard
              v-for="decision in recentDecisions"
              :key="decision.id"
              :decision="decision"
              data-testid="decision-card"
            />
          </div>
        </section>

        <!-- Activity Feed -->
        <section class="section-activity">
          <AIActivityFeed
            :activities="activities"
            :maxVisible="5"
            @clear="clearActivities"
            data-testid="activity-feed"
          />
        </section>
      </div>

      <!-- Position Sync Details -->
      <section class="section-positions" v-if="positionAnalysis">
        <div class="section-header">
          <h2 class="section-title">Position Analysis</h2>
          <button class="btn-refresh" @click="syncPositions" :disabled="syncStatus === 'syncing'" data-testid="btn-refresh-positions">
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': syncStatus === 'syncing' }"></i>
            Refresh
          </button>
        </div>

        <div class="position-stats">
          <div class="stat-card" data-testid="stat-total-positions">
            <div class="stat-value">{{ positionAnalysis.totalPositions || 0 }}</div>
            <div class="stat-label">Total Positions</div>
          </div>

          <div class="stat-card" data-testid="stat-total-pnl">
            <div class="stat-value" :class="positionAnalysis.totalPnl >= 0 ? 'profit' : 'loss'">
              {{ formatPnl(positionAnalysis.totalPnl) }}
            </div>
            <div class="stat-label">Total P&L</div>
          </div>

          <div class="stat-card" data-testid="stat-health-score">
            <div class="stat-value" :class="healthClass">
              {{ healthScore }}/100
            </div>
            <div class="stat-label">Health Score</div>
          </div>

          <div class="stat-card" data-testid="stat-margin">
            <div class="stat-value">₹{{ (positionAnalysis.totalMarginUsed || 0).toFixed(0) }}</div>
            <div class="stat-label">Margin Used</div>
          </div>
        </div>
      </section>
    </div>
    </div>
  </KiteLayout>
</template>

<script setup>
import KiteLayout from '@/components/layout/KiteLayout.vue'
import AISubNav from '@/components/ai/AISubNav.vue'

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import MarketRegimeIndicator from '@/components/ai/MarketRegimeIndicator.vue'
import AIDecisionCard from '@/components/ai/AIDecisionCard.vue'
import GraduationProgress from '@/components/ai/GraduationProgress.vue'
import PositionSyncStatus from '@/components/ai/PositionSyncStatus.vue'
import AIActivityFeed from '@/components/ai/AIActivityFeed.vue'
import { useToast } from '@/composables/useToast'
import { useAIConfigStore } from '@/stores/aiConfig'
import api from '@/services/api'

const router = useRouter()
const { showToast } = useToast()
const aiConfigStore = useAIConfigStore()

// State
const currentRegime = ref(null)
const decisions = ref([])
const activities = ref([])
const syncStatus = ref('idle')
const lastSyncTime = ref(null)
const positionAnalysis = ref(null)
const deploying = ref(false)
const loadingTrades = ref(false)

const paperTrades = ref({
  active: [],
  closed: [],
  summary: {
    total_trades: 0,
    active_trades: 0,
    closed_trades: 0,
    total_pnl: 0,
    win_rate: 0,
    avg_pnl_per_trade: 0
  }
})

const graduationData = ref({
  tradesCompleted: 0,
  tradesTarget: 30,
  winRate: 0,
  winRateTarget: 65,
  totalPnl: 0,
  startDate: '',
  approved: false
})

// Computed
const aiEnabled = computed(() => aiConfigStore.isAIEnabled)

const recentDecisions = computed(() => {
  return decisions.value.slice(0, 5)
})

const healthScore = computed(() => {
  return Math.round(positionAnalysis.value?.healthScore || 0)
})

const healthClass = computed(() => {
  const score = healthScore.value
  if (score >= 80) return 'health-good'
  if (score >= 50) return 'health-warning'
  return 'health-bad'
})

const formatPnl = (pnl) => {
  if (!pnl) pnl = 0
  const sign = pnl >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(pnl).toFixed(2)}`
}

const formatDateTime = (datetime) => {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('en-IN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const pnlClass = (pnl) => {
  if (!pnl) return ''
  return pnl >= 0 ? 'profit' : 'loss'
}

// Methods
const fetchRegime = async () => {
  try {
    // Placeholder - would call API
    // const response = await api.get('/api/v1/ai/regime/current?underlying=NIFTY')
    // currentRegime.value = response.data

    // Mock data for now
    currentRegime.value = {
      regime_type: 'RANGEBOUND',
      confidence: 75,
      reasoning: 'Market trading within Bollinger Bands with low ADX'
    }
  } catch (error) {
    console.error('Error fetching regime:', error)
  }
}

const fetchDecisions = async () => {
  try {
    // Placeholder - would call API
    // const response = await api.get('/api/v1/ai/decisions')
    // decisions.value = response.data

    // Mock data
    decisions.value = []
  } catch (error) {
    console.error('Error fetching decisions:', error)
  }
}

const fetchGraduationData = async () => {
  try {
    // Placeholder - would call API
    // const response = await api.get('/api/v1/ai/config')
    // graduationData.value = response.data

    // Mock data
    graduationData.value = {
      tradesCompleted: 12,
      tradesTarget: 30,
      winRate: 58.3,
      winRateTarget: 65,
      totalPnl: 2450.50,
      startDate: '2025-12-01',
      approved: false
    }
  } catch (error) {
    console.error('Error fetching graduation data:', error)
  }
}

const syncPositions = async () => {
  syncStatus.value = 'syncing'

  try {
    // Placeholder - would call position sync API
    // const response = await api.post('/api/v1/ai/positions/sync')
    // positionAnalysis.value = response.data

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))

    // Mock data
    positionAnalysis.value = {
      totalPositions: 3,
      totalPnl: 1250.75,
      totalMarginUsed: 45000,
      healthScore: 85
    }

    syncStatus.value = 'success'
    lastSyncTime.value = new Date().toISOString()

    addActivity({
      id: Date.now(),
      type: 'sync_complete',
      message: 'Position sync completed successfully',
      timestamp: new Date().toISOString(),
      metadata: {
        positions: positionAnalysis.value.totalPositions,
        pnl: formatPnl(positionAnalysis.value.totalPnl)
      }
    })
  } catch (error) {
    console.error('Error syncing positions:', error)
    syncStatus.value = 'error'
    showToast('Failed to sync positions', 'error')
  }
}

const addActivity = (activity) => {
  activities.value.unshift(activity)
  // Keep only last 50 activities
  if (activities.value.length > 50) {
    activities.value = activities.value.slice(0, 50)
  }
}

const clearActivities = () => {
  activities.value = []
  showToast('Activity feed cleared', 'success')
}

const viewAllDecisions = () => {
  // Navigate to full decisions page (to be created)
  showToast('Full decisions view coming soon', 'info')
}

const triggerDeploy = async () => {
  deploying.value = true
  try {
    const response = await api.post('/api/v1/ai/deploy/trigger', {
      underlying: 'NIFTY',
      force: true  // Use test mode with mock data
    })

    if (response.data.success) {
      showToast(`Deployed ${response.data.strategy_name} with ${response.data.position_size_lots} lots`, 'success')

      addActivity({
        id: Date.now(),
        type: 'deployment',
        message: `AI deployed ${response.data.strategy_name} in ${response.data.regime} regime`,
        timestamp: new Date().toISOString(),
        metadata: {
          strategy: response.data.strategy_name,
          lots: response.data.position_size_lots,
          confidence: response.data.confidence
        }
      })

      // Refresh paper trades and graduation data
      await Promise.all([
        fetchPaperTrades(),
        fetchGraduationData()
      ])
    } else {
      showToast(response.data.error || 'Deployment failed', 'error')
    }
  } catch (error) {
    console.error('Error triggering deployment:', error)
    showToast(error.response?.data?.detail || 'Failed to trigger deployment', 'error')
  } finally {
    deploying.value = false
  }
}

const exitTrade = async (tradeId) => {
  try {
    const confirmed = confirm('Are you sure you want to exit this paper trade?')
    if (!confirmed) return

    const response = await api.post('/api/v1/ai/deploy/paper-trade/exit', {
      paper_trade_id: tradeId,
      exit_reason: 'manual'
    })

    if (response.data.success) {
      const pnl = response.data.realized_pnl || 0
      const pnlText = pnl >= 0 ? `profit of ₹${pnl.toFixed(2)}` : `loss of ₹${Math.abs(pnl).toFixed(2)}`
      showToast(`Trade exited with ${pnlText}`, pnl >= 0 ? 'success' : 'warning')

      addActivity({
        id: Date.now(),
        type: 'exit',
        message: `Paper trade exited: ${pnlText}`,
        timestamp: new Date().toISOString(),
        metadata: {
          pnl: pnl,
          hold_time: response.data.hold_time_minutes
        }
      })

      // Refresh paper trades and graduation data
      await Promise.all([
        fetchPaperTrades(),
        fetchGraduationData()
      ])
    } else {
      showToast(response.data.error || 'Exit failed', 'error')
    }
  } catch (error) {
    console.error('Error exiting trade:', error)
    showToast(error.response?.data?.detail || 'Failed to exit trade', 'error')
  }
}

const fetchPaperTrades = async () => {
  loadingTrades.value = true
  try {
    const response = await api.get('/api/v1/ai/deploy/paper-trade/list')
    paperTrades.value = response.data
  } catch (error) {
    console.error('Error fetching paper trades:', error)
    showToast('Failed to fetch paper trades', 'error')
  } finally {
    loadingTrades.value = false
  }
}

const handleGraduation = () => {
  // Show confirmation dialog and graduate to live trading
  if (confirm('Are you sure you want to graduate to live trading? This will enable real order placement.')) {
    graduatToLiveTrading()
  }
}

const graduatToLiveTrading = async () => {
  try {
    // Placeholder - would call API
    // await api.post('/api/v1/ai/config/graduate')

    showToast('Congratulations! Graduated to live trading', 'success')
    graduationData.value.approved = true

    addActivity({
      id: Date.now(),
      type: 'info',
      message: 'Graduated to live trading mode',
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error graduating:', error)
    showToast('Failed to graduate to live trading', 'error')
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([
    aiConfigStore.fetchConfig(),
    fetchRegime(),
    fetchDecisions(),
    fetchGraduationData(),
    fetchPaperTrades(),
    syncPositions()
  ])

  // Auto-refresh every 30 seconds
  const refreshInterval = setInterval(() => {
    fetchRegime()
    fetchDecisions()
    fetchPaperTrades()
  }, 30000)

  onUnmounted(() => {
    clearInterval(refreshInterval)
  })
})
</script>

<style scoped>
.paper-trading-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 20px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-graduation {
  margin-bottom: 8px;
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.btn-view-all,
.btn-refresh {
  padding: 6px 12px;
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  color: var(--kite-primary, #387ed1);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-view-all:hover,
.btn-refresh:hover {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-primary, #387ed1);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-message {
  padding: 40px 20px;
  text-align: center;
  color: var(--kite-text-secondary, #666);
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
}

.empty-message i {
  font-size: 36px;
  margin-bottom: 12px;
  opacity: 0.3;
}

.empty-message p {
  margin: 0;
  font-size: 14px;
}

.decisions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.position-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 8px;
}

.stat-value.profit {
  color: var(--kite-green, #00b386);
}

.stat-value.loss {
  color: var(--kite-red, #e53935);
}

.stat-value.health-good {
  color: var(--kite-green, #00b386);
}

.stat-value.health-warning {
  color: #ff9800;
}

.stat-value.health-bad {
  color: var(--kite-red, #e53935);
}

.stat-label {
  font-size: 13px;
  color: var(--kite-text-secondary, #666);
}

/* Deploy Button */
.btn-deploy {
  padding: 10px 20px;
  background: var(--kite-primary, #387ed1);
  border: none;
  border-radius: 4px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-deploy:hover:not(:disabled) {
  background: #2d6bb3;
  transform: translateY(-1px);
}

.btn-deploy:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Paper Trades Section */
.section-paper-trades {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
}

.trades-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.trades-subsection {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subsection-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.table-wrapper {
  overflow-x: auto;
}

.paper-trades-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.paper-trades-table th {
  background: var(--kite-bg-light, #f8f9fa);
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--kite-text-secondary, #666);
  border-bottom: 2px solid var(--kite-border, #e8e8e8);
  white-space: nowrap;
}

.paper-trades-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
  color: var(--kite-text-primary, #394046);
}

.paper-trades-table tbody tr:hover {
  background: var(--kite-bg-light, #f8f9fa);
}

.td-strategy {
  font-weight: 500;
}

.td-premium {
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.badge-regime,
.badge-sizing {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-regime {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-sizing {
  background: #f3e5f5;
  color: #7b1fa2;
}

.btn-exit {
  padding: 6px 12px;
  background: var(--kite-red, #e53935);
  border: none;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-exit:hover {
  background: #c62828;
}

/* Trades Summary */
.trades-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  padding: 20px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
}

.summary-card {
  text-align: center;
}

.summary-label {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
  margin-bottom: 6px;
  font-weight: 500;
}

.summary-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
}

.summary-value.profit {
  color: var(--kite-green, #00b386);
}

.summary-value.loss {
  color: var(--kite-red, #e53935);
}
</style>
