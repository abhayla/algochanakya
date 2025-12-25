<script setup>
/**
 * AI Status Card Component
 *
 * Displays AI configuration status and daily limits for AutoPilot Dashboard
 * Week 3 - AI + AutoPilot Integration
 */
import { ref, computed, onMounted } from 'vue'
import { useAIConfigStore } from '@/stores/aiConfig'

const aiStore = useAIConfigStore()

onMounted(async () => {
  // Fetch AI config when component mounts
  if (!aiStore.config) {
    await aiStore.fetchConfig()
  }
})

// Computed properties for display
const isAIEnabled = computed(() => aiStore.isAIEnabled)
const autonomyMode = computed(() => aiStore.autonomyMode)

const lotsUsedToday = computed(() => {
  // TODO: Fetch from API endpoint /api/v1/ai/deployment/daily-stats
  return 3 // Placeholder
})

const strategiesDeployedToday = computed(() => {
  // TODO: Fetch from API endpoint /api/v1/ai/deployment/daily-stats
  return 2 // Placeholder
})

const lotsProgress = computed(() => {
  if (!aiStore.config || !aiStore.config.max_lots_per_day) return 0
  return Math.min((lotsUsedToday.value / aiStore.config.max_lots_per_day) * 100, 100)
})

const strategiesProgress = computed(() => {
  if (!aiStore.config || !aiStore.config.max_strategies_per_day) return 0
  return Math.min((strategiesDeployedToday.value / aiStore.config.max_strategies_per_day) * 100, 100)
})

const statusColor = computed(() => {
  if (!isAIEnabled.value) return 'gray'
  if (autonomyMode.value === 'live') return 'green'
  return 'blue' // paper mode
})

const statusText = computed(() => {
  if (!isAIEnabled.value) return 'Disabled'
  if (autonomyMode.value === 'live') return 'Live Trading'
  return 'Paper Trading'
})

const canGraduate = computed(() => aiStore.canGraduateToLive)
</script>

<template>
  <div class="summary-card ai-status-card" data-testid="autopilot-ai-status-card">
    <!-- Header -->
    <div class="ai-status-header">
      <p class="summary-label">
        AI Trading
        <router-link to="/ai/settings" class="ai-settings-link" title="AI Settings">
          <svg class="icon-svg-xs" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
        </router-link>
      </p>
    </div>

    <!-- Status Badge -->
    <div class="ai-status-badge-container">
      <span
        class="ai-status-badge"
        :class="{
          'badge-disabled': !isAIEnabled,
          'badge-live': isAIEnabled && autonomyMode === 'live',
          'badge-paper': isAIEnabled && autonomyMode === 'paper'
        }"
        data-testid="ai-status-badge"
      >
        <span
          class="status-dot"
          :class="{
            'dot-gray': !isAIEnabled,
            'dot-green': isAIEnabled && autonomyMode === 'live',
            'dot-blue': isAIEnabled && autonomyMode === 'paper'
          }"
        ></span>
        {{ statusText }}
      </span>
    </div>

    <!-- AI Limits (only show if AI enabled) -->
    <div v-if="isAIEnabled && aiStore.config" class="ai-limits-container">
      <!-- Daily Lots Limit -->
      <div class="ai-limit-item">
        <div class="ai-limit-header">
          <span class="ai-limit-label">Lots Today</span>
          <span class="ai-limit-value">
            {{ lotsUsedToday }} / {{ aiStore.config.max_lots_per_day || '∞' }}
          </span>
        </div>
        <div class="progress-bar-bg progress-bar-sm">
          <div
            class="progress-bar-fill"
            :class="{
              'fill-safe': lotsProgress < 70,
              'fill-warning': lotsProgress >= 70 && lotsProgress < 90,
              'fill-critical': lotsProgress >= 90
            }"
            :style="{ width: lotsProgress + '%' }"
          ></div>
        </div>
      </div>

      <!-- Daily Strategies Limit -->
      <div class="ai-limit-item">
        <div class="ai-limit-header">
          <span class="ai-limit-label">Strategies Today</span>
          <span class="ai-limit-value">
            {{ strategiesDeployedToday }} / {{ aiStore.config.max_strategies_per_day || '∞' }}
          </span>
        </div>
        <div class="progress-bar-bg progress-bar-sm">
          <div
            class="progress-bar-fill"
            :class="{
              'fill-safe': strategiesProgress < 70,
              'fill-warning': strategiesProgress >= 70 && strategiesProgress < 90,
              'fill-critical': strategiesProgress >= 90
            }"
            :style="{ width: strategiesProgress + '%' }"
          ></div>
        </div>
      </div>

      <!-- Graduation Status (show only in paper mode) -->
      <div v-if="autonomyMode === 'paper'" class="graduation-status">
        <span class="graduation-label">
          {{ canGraduate ? '✓ Eligible for Live' : 'Paper Trading' }}
        </span>
        <router-link v-if="canGraduate" to="/ai/settings" class="graduate-link">
          Graduate →
        </router-link>
      </div>
    </div>

    <!-- AI Disabled Message -->
    <div v-else class="ai-disabled-message">
      <p class="disabled-text">AI Trading is currently disabled</p>
      <router-link to="/ai/settings" class="enable-link">
        Enable AI Trading →
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.ai-status-card {
  position: relative;
}

.ai-status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.ai-settings-link {
  display: inline-flex;
  align-items: center;
  color: #6b7280;
  transition: color 0.2s;
  margin-left: 8px;
}

.ai-settings-link:hover {
  color: #3b82f6;
}

.icon-svg-xs {
  width: 14px;
  height: 14px;
}

.ai-status-badge-container {
  margin-bottom: 16px;
}

.ai-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}

.badge-disabled {
  background-color: #f3f4f6;
  color: #6b7280;
}

.badge-live {
  background-color: #d1fae5;
  color: #065f46;
}

.badge-paper {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-gray {
  background-color: #9ca3af;
}

.dot-green {
  background-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
  animation: pulse-green 2s infinite;
}

.dot-blue {
  background-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

@keyframes pulse-green {
  0%, 100% {
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1);
  }
}

.ai-limits-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-limit-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ai-limit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-limit-label {
  font-size: 12px;
  color: #6b7280;
}

.ai-limit-value {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.progress-bar-sm {
  height: 4px;
}

.graduation-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
  margin-top: 4px;
}

.graduation-label {
  font-size: 12px;
  color: #059669;
  font-weight: 500;
}

.graduate-link {
  font-size: 12px;
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.graduate-link:hover {
  text-decoration: underline;
}

.ai-disabled-message {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 0;
}

.disabled-text {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.enable-link {
  font-size: 13px;
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.enable-link:hover {
  text-decoration: underline;
}
</style>
