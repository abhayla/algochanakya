<template>
  <KiteLayout>
    <AISubNav />
    <div class="paper-trading-view" data-testid="paper-trading-view">
    <div class="page-header">
      <h1 class="page-title">Paper Trading Dashboard</h1>
      <div class="header-actions">
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

const router = useRouter()
const { showToast } = useToast()

// State
const currentRegime = ref(null)
const decisions = ref([])
const activities = ref([])
const syncStatus = ref('idle')
const lastSyncTime = ref(null)
const positionAnalysis = ref(null)

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
    fetchRegime(),
    fetchDecisions(),
    fetchGraduationData(),
    syncPositions()
  ])

  // Auto-refresh every 30 seconds
  const refreshInterval = setInterval(() => {
    fetchRegime()
    fetchDecisions()
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
</style>
