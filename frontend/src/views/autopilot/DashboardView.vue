<script setup>
/**
 * AutoPilot Dashboard View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 1
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'

const router = useRouter()
const store = useAutopilotStore()

const refreshInterval = ref(null)

onMounted(async () => {
  await store.fetchDashboardSummary()
  await store.fetchStrategies()

  // Refresh every 5 seconds
  refreshInterval.value = setInterval(() => {
    store.fetchDashboardSummary()
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})

const navigateToBuilder = () => {
  router.push('/autopilot/strategies/new')
}

const navigateToStrategy = (id) => {
  router.push(`/autopilot/strategies/${id}`)
}

const navigateToSettings = () => {
  router.push('/autopilot/settings')
}

const handlePause = async (strategy) => {
  if (confirm(`Pause strategy "${strategy.name}"?`)) {
    await store.pauseStrategy(strategy.id)
  }
}

const handleResume = async (strategy) => {
  await store.resumeStrategy(strategy.id)
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const getPnLClass = (value) => {
  if (value > 0) return 'text-green-600'
  if (value < 0) return 'text-red-600'
  return 'text-gray-600'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'bg-green-100 text-green-800',
    waiting: 'bg-yellow-100 text-yellow-800',
    pending: 'bg-orange-100 text-orange-800',
    paused: 'bg-gray-100 text-gray-800',
    draft: 'bg-blue-100 text-blue-800',
    completed: 'bg-purple-100 text-purple-800',
    error: 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}
</script>

<template>
  <div class="p-6" data-testid="autopilot-dashboard">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">AutoPilot Dashboard</h1>
        <p class="text-gray-500 mt-1">Automated options trading strategies</p>
      </div>
      <div class="flex gap-2">
        <button
          @click="navigateToSettings"
          data-testid="autopilot-settings-button"
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
        >
          Settings
        </button>
        <button
          @click="navigateToBuilder"
          :disabled="!store.canCreateStrategy"
          data-testid="autopilot-new-strategy-button"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          + New Strategy
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="store.loading && !store.dashboardSummary" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-500">Loading dashboard...</p>
    </div>

    <!-- Dashboard Content -->
    <template v-else-if="store.dashboardSummary">
      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <!-- Today's P&L -->
        <div class="bg-white rounded-lg shadow p-4" data-testid="autopilot-pnl-card">
          <p class="text-sm text-gray-500">Today's P&L</p>
          <p :class="['text-2xl font-bold', getPnLClass(store.dashboardSummary.today_total_pnl)]">
            {{ formatCurrency(store.dashboardSummary.today_total_pnl) }}
          </p>
        </div>

        <!-- Active Strategies -->
        <div class="bg-white rounded-lg shadow p-4" data-testid="autopilot-active-card">
          <p class="text-sm text-gray-500">Active Strategies</p>
          <p class="text-2xl font-bold text-gray-900">
            {{ store.dashboardSummary.active_strategies + store.dashboardSummary.waiting_strategies }}
            <span class="text-sm font-normal text-gray-500">
              / {{ store.dashboardSummary.risk_metrics.max_active_strategies }}
            </span>
          </p>
        </div>

        <!-- Daily Loss Limit -->
        <div class="bg-white rounded-lg shadow p-4" data-testid="autopilot-risk-card">
          <p class="text-sm text-gray-500">Daily Loss Used</p>
          <p class="text-2xl font-bold text-gray-900">
            {{ store.dashboardSummary.risk_metrics.daily_loss_pct.toFixed(0) }}%
          </p>
          <div class="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              class="h-2 rounded-full transition-all"
              :class="{
                'bg-green-500': store.dashboardSummary.risk_metrics.status === 'safe',
                'bg-yellow-500': store.dashboardSummary.risk_metrics.status === 'warning',
                'bg-red-500': store.dashboardSummary.risk_metrics.status === 'critical'
              }"
              :style="{ width: Math.min(store.dashboardSummary.risk_metrics.daily_loss_pct, 100) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Connection Status -->
        <div class="bg-white rounded-lg shadow p-4" data-testid="autopilot-connection-card">
          <p class="text-sm text-gray-500">Broker Status</p>
          <div class="flex items-center mt-1">
            <span
              class="h-3 w-3 rounded-full mr-2"
              :class="store.dashboardSummary.kite_connected ? 'bg-green-500' : 'bg-red-500'"
            ></span>
            <span class="text-lg font-medium">
              {{ store.dashboardSummary.kite_connected ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Strategies List -->
      <div class="bg-white rounded-lg shadow" data-testid="autopilot-strategies-list">
        <div class="p-4 border-b border-gray-200 flex justify-between items-center">
          <h2 class="text-lg font-semibold">Strategies</h2>
          <div class="flex gap-2">
            <select
              v-model="store.filters.status"
              @change="store.fetchStrategies()"
              class="text-sm border border-gray-300 rounded px-2 py-1"
              data-testid="autopilot-status-filter"
            >
              <option :value="null">All Status</option>
              <option value="draft">Draft</option>
              <option value="waiting">Waiting</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </select>
          </div>
        </div>

        <div v-if="store.strategies.length === 0" class="p-8 text-center">
          <p class="text-gray-500 mb-4">No strategies yet. Create your first AutoPilot strategy!</p>
          <button
            @click="navigateToBuilder"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Create Strategy
          </button>
        </div>

        <div v-else class="divide-y divide-gray-200">
          <div
            v-for="strategy in store.strategies"
            :key="strategy.id"
            class="p-4 hover:bg-gray-50 cursor-pointer"
            :data-testid="`autopilot-strategy-${strategy.id}`"
            @click="navigateToStrategy(strategy.id)"
          >
            <div class="flex justify-between items-start">
              <div>
                <div class="flex items-center gap-2">
                  <h3 class="font-medium text-gray-900">{{ strategy.name }}</h3>
                  <span
                    :class="['px-2 py-0.5 text-xs rounded-full', getStatusBadgeClass(strategy.status)]"
                    :data-testid="`autopilot-strategy-status-${strategy.id}`"
                  >
                    {{ strategy.status }}
                  </span>
                </div>
                <p class="text-sm text-gray-500 mt-1">
                  {{ strategy.underlying }} • {{ strategy.lots }} lot(s) • {{ strategy.leg_count }} legs
                </p>
              </div>

              <div class="text-right">
                <p :class="['font-medium', getPnLClass(strategy.current_pnl)]">
                  {{ formatCurrency(strategy.current_pnl) }}
                </p>
                <div class="flex gap-2 mt-2" @click.stop>
                  <button
                    v-if="['active', 'waiting', 'pending'].includes(strategy.status)"
                    @click="handlePause(strategy)"
                    :data-testid="`autopilot-pause-${strategy.id}`"
                    class="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                  >
                    Pause
                  </button>
                  <button
                    v-if="strategy.status === 'paused'"
                    @click="handleResume(strategy)"
                    :data-testid="`autopilot-resume-${strategy.id}`"
                    class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200"
                  >
                    Resume
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Error State -->
    <div v-if="store.error" class="bg-red-50 border border-red-200 rounded-lg p-4 mt-4" data-testid="autopilot-error">
      <p class="text-red-800">{{ store.error }}</p>
      <button @click="store.clearError" class="text-red-600 underline mt-2">Dismiss</button>
    </div>
  </div>
</template>
