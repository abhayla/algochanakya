<template>
  <div class="autonomy-trust-ladder" data-testid="autonomy-trust-ladder">
    <!-- Header -->
    <div class="ladder-header">
      <div class="header-title">
        <i class="fas fa-stairs"></i>
        <h3>Autonomy Trust Ladder</h3>
      </div>
      <div
        v-if="isPaused"
        class="pause-badge"
        data-testid="pause-badge"
      >
        <i class="fas fa-pause-circle"></i>
        Paused
      </div>
    </div>

    <!-- Visual Ladder -->
    <div class="ladder-visual" data-testid="ladder-visual">
      <div
        v-for="(level, index) in levels"
        :key="level.id"
        class="ladder-step"
        :class="{
          'step-current': level.is_current,
          'step-unlocked': level.is_unlocked,
          'step-locked': !level.is_unlocked
        }"
        :data-testid="`ladder-step-${level.id}`"
      >
        <div class="step-connector" v-if="index < levels.length - 1">
          <div
            class="connector-line"
            :class="{ 'connector-filled': levels[index + 1].is_unlocked }"
          ></div>
        </div>

        <div class="step-icon" :class="`icon-${level.color}`">
          <i :class="`fas fa-${level.icon}`"></i>
        </div>

        <div class="step-content">
          <div class="step-name">{{ level.name }}</div>
          <div class="step-description">{{ level.description }}</div>
          <div v-if="level.is_current" class="step-badge">
            <i class="fas fa-location-dot"></i> You are here
          </div>
        </div>

        <div v-if="level.is_current && !level.is_locked" class="step-features">
          <div class="feature-tag" v-for="feature in level.features.slice(0, 2)" :key="feature">
            {{ feature }}
          </div>
        </div>
      </div>
    </div>

    <!-- Progress Section -->
    <div
      v-if="progress && progress.next_level"
      class="progress-section"
      data-testid="progress-section"
    >
      <div class="progress-header">
        <span class="progress-title">Progress to {{ progress.next_level_name }}</span>
        <span class="progress-percent">{{ progress.overall_percent }}%</span>
      </div>
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: progress.overall_percent + '%' }"
        ></div>
      </div>
    </div>

    <!-- Unlock Criteria -->
    <div
      v-if="unlockCriteria && unlockCriteria.length > 0"
      class="criteria-section"
      data-testid="criteria-section"
    >
      <div class="criteria-title">
        <i class="fas fa-lock-open"></i>
        Unlock Requirements
      </div>
      <div class="criteria-list">
        <div
          v-for="criterion in unlockCriteria"
          :key="criterion.id"
          class="criterion-item"
          :class="{ 'criterion-met': criterion.met }"
          :data-testid="`criterion-${criterion.id}`"
        >
          <div class="criterion-check">
            <i :class="criterion.met ? 'fas fa-check-circle' : 'far fa-circle'"></i>
          </div>
          <div class="criterion-content">
            <div class="criterion-label">{{ criterion.label }}</div>
            <div class="criterion-description">{{ criterion.description }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Warnings Section -->
    <div
      v-if="warnings && warnings.length > 0"
      class="warnings-section"
      data-testid="warnings-section"
    >
      <div
        v-for="(warning, index) in warnings"
        :key="index"
        class="warning-item"
        :class="`warning-${warning.type}`"
        :data-testid="`warning-${index}`"
      >
        <i :class="warning.type === 'critical' ? 'fas fa-exclamation-circle' : 'fas fa-exclamation-triangle'"></i>
        <span>{{ warning.message }}</span>
      </div>
    </div>

    <!-- Pause Reason -->
    <div
      v-if="isPaused && pauseReason"
      class="pause-reason"
      data-testid="pause-reason"
    >
      <i class="fas fa-info-circle"></i>
      <span>{{ pauseReason }}</span>
    </div>

    <!-- Stats Summary -->
    <div
      v-if="stats && showStats"
      class="stats-section"
      data-testid="stats-section"
    >
      <div class="stat-item" data-testid="stat-trades">
        <div class="stat-value">{{ stats.trades_completed }}</div>
        <div class="stat-label">Trades</div>
      </div>
      <div class="stat-item" data-testid="stat-winrate">
        <div class="stat-value" :class="stats.win_rate >= 55 ? 'text-success' : ''">
          {{ stats.win_rate.toFixed(1) }}%
        </div>
        <div class="stat-label">Win Rate</div>
      </div>
      <div class="stat-item" data-testid="stat-pnl">
        <div class="stat-value" :class="stats.total_pnl >= 0 ? 'text-success' : 'text-danger'">
          {{ formatPnl(stats.total_pnl) }}
        </div>
        <div class="stat-label">Total P&L</div>
      </div>
      <div class="stat-item" data-testid="stat-days">
        <div class="stat-value">{{ stats.days_trading }}</div>
        <div class="stat-label">Days</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAIAnalyticsStore } from '@/stores/aiAnalytics'

const aiAnalytics = useAIAnalyticsStore()

const props = defineProps({
  showStats: {
    type: Boolean,
    default: true
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['level-change', 'loaded'])

// State
const loading = ref(true)
const error = ref(null)
const currentLevel = ref('sandbox')
const levelIndex = ref(0)
const levels = ref([])
const progress = ref(null)
const unlockCriteria = ref([])
const warnings = ref([])
const isPaused = ref(false)
const pauseReason = ref(null)
const stats = ref(null)
const aiEnabled = ref(false)

// Computed
const currentLevelDetails = computed(() => {
  return levels.value.find(l => l.is_current) || levels.value[0] || {}
})

// Methods
const fetchAutonomyStatus = async () => {
  loading.value = true
  error.value = null

  const [statusResult, levelsResult] = await Promise.all([
    aiAnalytics.fetchAutonomyStatus(),
    aiAnalytics.fetchAutonomyLevels(),
  ])
  loading.value = false

  if (!statusResult.success || !levelsResult.success) {
    console.error('[Autonomy] Error loading status:', statusResult.error || levelsResult.error)
    error.value = statusResult.error || levelsResult.error || 'Failed to load autonomy status'
    return
  }

  const statusData = statusResult.data
  const levelsData = levelsResult.data

  currentLevel.value = statusData.current_level
  levelIndex.value = statusData.level_index
  progress.value = statusData.progress
  unlockCriteria.value = statusData.unlock_criteria
  warnings.value = statusData.warnings
  isPaused.value = statusData.is_paused
  pauseReason.value = statusData.pause_reason
  stats.value = statusData.stats
  aiEnabled.value = statusData.ai_enabled

  levels.value = levelsData.levels.slice().reverse()

  emit('loaded', statusData)

  console.log('[Autonomy] Status loaded:', {
    level: currentLevel.value,
    progress: progress.value?.overall_percent,
    isPaused: isPaused.value,
  })
}

const formatPnl = (pnl) => {
  const sign = pnl >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(pnl).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

// Lifecycle
onMounted(() => {
  fetchAutonomyStatus()
})

// Expose for parent components
defineExpose({
  refresh: fetchAutonomyStatus,
  currentLevel,
  isPaused
})
</script>

<style scoped>
.autonomy-trust-ladder {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 20px;
}

/* Header */
.ladder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title i {
  font-size: 20px;
  color: var(--kite-primary, #387ed1);
}

.header-title h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.pause-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(229, 57, 53, 0.1);
  color: var(--kite-red, #e53935);
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

/* Ladder Visual */
.ladder-visual {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 24px;
}

.ladder-step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 8px;
  position: relative;
  transition: all 0.2s ease;
}

.step-connector {
  position: absolute;
  left: 35px;
  bottom: -8px;
  height: 16px;
  width: 2px;
  z-index: 1;
}

.connector-line {
  width: 100%;
  height: 100%;
  background: var(--kite-border, #e8e8e8);
}

.connector-filled {
  background: var(--kite-green, #00b386);
}

.step-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  border: 2px solid;
  background: white;
  z-index: 2;
}

.icon-blue {
  border-color: var(--kite-primary, #387ed1);
  color: var(--kite-primary, #387ed1);
}

.icon-yellow {
  border-color: #ff9800;
  color: #ff9800;
}

.icon-green {
  border-color: var(--kite-green, #00b386);
  color: var(--kite-green, #00b386);
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 4px;
}

.step-description {
  font-size: 13px;
  color: var(--kite-text-secondary, #666);
  line-height: 1.4;
}

.step-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 4px 10px;
  background: var(--kite-primary, #387ed1);
  color: white;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.step-features {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-left: auto;
}

.feature-tag {
  padding: 4px 8px;
  background: var(--kite-bg-light, #f8f9fa);
  color: var(--kite-text-secondary, #666);
  border-radius: 4px;
  font-size: 11px;
}

/* Step States */
.step-current {
  background: rgba(56, 126, 209, 0.08);
  border: 1px solid rgba(56, 126, 209, 0.2);
}

.step-unlocked {
  opacity: 1;
}

.step-locked {
  opacity: 0.5;
}

.step-locked .step-icon {
  border-color: var(--kite-border, #e8e8e8);
  color: var(--kite-text-secondary, #999);
}

/* Progress Section */
.progress-section {
  margin-bottom: 20px;
  padding: 16px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 8px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--kite-text-secondary, #666);
}

.progress-percent {
  font-size: 14px;
  font-weight: 700;
  color: var(--kite-primary, #387ed1);
}

.progress-bar {
  height: 8px;
  background: white;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--kite-primary, #387ed1), var(--kite-green, #00b386));
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* Criteria Section */
.criteria-section {
  margin-bottom: 20px;
}

.criteria-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 12px;
}

.criteria-title i {
  color: var(--kite-primary, #387ed1);
}

.criteria-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.criterion-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 6px;
  border-left: 3px solid var(--kite-border, #e8e8e8);
}

.criterion-met {
  border-left-color: var(--kite-green, #00b386);
}

.criterion-check {
  font-size: 18px;
  color: var(--kite-text-secondary, #999);
  margin-top: 2px;
}

.criterion-met .criterion-check {
  color: var(--kite-green, #00b386);
}

.criterion-content {
  flex: 1;
}

.criterion-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 2px;
}

.criterion-description {
  font-size: 12px;
  color: var(--kite-text-secondary, #666);
}

/* Warnings Section */
.warnings-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
}

.warning-warning {
  background: rgba(255, 152, 0, 0.1);
  color: #f57c00;
  border-left: 4px solid #ff9800;
}

.warning-critical {
  background: rgba(229, 57, 53, 0.1);
  color: var(--kite-red, #e53935);
  border-left: 4px solid var(--kite-red, #e53935);
}

/* Pause Reason */
.pause-reason {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: rgba(229, 57, 53, 0.08);
  color: var(--kite-red, #e53935);
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 16px;
}

/* Stats Section */
.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 11px;
  color: var(--kite-text-secondary, #999);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.text-success {
  color: var(--kite-green, #00b386) !important;
}

.text-danger {
  color: var(--kite-red, #e53935) !important;
}

/* Responsive */
@media (max-width: 640px) {
  .ladder-step {
    flex-wrap: wrap;
  }

  .step-features {
    width: 100%;
    margin-left: 60px;
    margin-top: 8px;
  }

  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
