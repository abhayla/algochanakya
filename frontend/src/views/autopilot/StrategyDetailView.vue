<script setup>
/**
 * AutoPilot Strategy Detail View
 *
 * Reference: docs/autopilot/ui-ux-design.md - Screen 3
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'

const router = useRouter()
const route = useRoute()
const store = useAutopilotStore()

const strategyId = computed(() => parseInt(route.params.id))
const refreshInterval = ref(null)
const showExitModal = ref(false)

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

const handleDelete = async () => {
  if (confirm('Are you sure you want to delete this strategy?')) {
    await store.deleteStrategy(strategyId.value)
    router.push('/autopilot')
  }
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
  <div class="p-6" data-testid="autopilot-strategy-detail">
    <!-- Loading -->
    <div v-if="store.loading && !store.currentStrategy" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-500">Loading strategy...</p>
    </div>

    <!-- Strategy Detail -->
    <template v-else-if="store.currentStrategy">
      <!-- Header -->
      <div class="flex justify-between items-start mb-6">
        <div>
          <div class="flex items-center gap-3">
            <button
              @click="router.push('/autopilot')"
              class="text-gray-500 hover:text-gray-700"
            >
              &larr;
            </button>
            <h1 class="text-2xl font-bold text-gray-900" data-testid="autopilot-strategy-name">
              {{ store.currentStrategy.name }}
            </h1>
            <span
              :class="['px-3 py-1 rounded-full text-sm font-medium', getStatusBadgeClass(store.currentStrategy.status)]"
              data-testid="autopilot-strategy-status"
            >
              {{ store.currentStrategy.status }}
            </span>
          </div>
          <p class="text-gray-500 mt-1">{{ store.currentStrategy.description || 'No description' }}</p>
        </div>

        <div class="flex gap-2">
          <button
            v-if="store.currentStrategy.status === 'draft'"
            @click="handleEdit"
            data-testid="autopilot-strategy-edit"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Edit
          </button>

          <button
            v-if="['active', 'waiting', 'pending'].includes(store.currentStrategy.status)"
            @click="handlePause"
            data-testid="autopilot-strategy-pause"
            class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
          >
            Pause
          </button>

          <button
            v-if="store.currentStrategy.status === 'paused'"
            @click="handleResume"
            data-testid="autopilot-strategy-resume"
            class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Resume
          </button>

          <button
            @click="handleClone"
            data-testid="autopilot-strategy-clone"
            class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Clone
          </button>

          <button
            v-if="['draft', 'completed', 'error'].includes(store.currentStrategy.status)"
            @click="handleDelete"
            data-testid="autopilot-strategy-delete"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-4" data-testid="autopilot-strategy-pnl">
          <p class="text-sm text-gray-500">Current P&L</p>
          <p :class="['text-2xl font-bold', getPnLClass(store.currentStrategy.runtime_state?.current_pnl)]">
            {{ formatCurrency(store.currentStrategy.runtime_state?.current_pnl) }}
          </p>
        </div>

        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Margin Used</p>
          <p class="text-2xl font-bold text-gray-900">
            {{ formatCurrency(store.currentStrategy.runtime_state?.margin_used) }}
          </p>
        </div>

        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Underlying</p>
          <p class="text-2xl font-bold text-gray-900">{{ store.currentStrategy.underlying }}</p>
          <p class="text-sm text-gray-500">{{ store.currentStrategy.lots }} lot(s)</p>
        </div>

        <div class="bg-white rounded-lg shadow p-4">
          <p class="text-sm text-gray-500">Activated</p>
          <p class="text-lg font-medium text-gray-900">
            {{ formatDateTime(store.currentStrategy.activated_at) }}
          </p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="bg-white rounded-lg shadow">
        <div class="border-b border-gray-200">
          <nav class="flex -mb-px">
            <button class="px-6 py-3 border-b-2 border-blue-500 text-blue-600 font-medium">
              Configuration
            </button>
          </nav>
        </div>

        <div class="p-6">
          <!-- Legs -->
          <div class="mb-6">
            <h3 class="text-lg font-semibold mb-3">Strategy Legs</h3>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Leg</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strike Selection</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                  <tr v-for="(leg, index) in store.currentStrategy.legs_config" :key="leg.id">
                    <td class="px-4 py-2 text-sm">{{ index + 1 }}</td>
                    <td class="px-4 py-2 text-sm">{{ leg.contract_type }}</td>
                    <td class="px-4 py-2">
                      <span
                        :class="[
                          'px-2 py-0.5 rounded text-xs font-medium',
                          leg.transaction_type === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        ]"
                      >
                        {{ leg.transaction_type }}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-sm">
                      {{ leg.strike_selection?.mode }}
                      <span v-if="leg.strike_selection?.offset !== undefined">
                        ({{ leg.strike_selection.offset >= 0 ? '+' : '' }}{{ leg.strike_selection.offset }})
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Entry Conditions -->
          <div class="mb-6">
            <h3 class="text-lg font-semibold mb-3">Entry Conditions</h3>
            <div v-if="store.currentStrategy.entry_conditions?.conditions?.length > 0">
              <p class="text-sm text-gray-600 mb-2">
                Logic: {{ store.currentStrategy.entry_conditions.logic }}
              </p>
              <div class="space-y-2">
                <div
                  v-for="(cond, index) in store.currentStrategy.entry_conditions.conditions"
                  :key="cond.id"
                  class="bg-gray-50 rounded p-2 text-sm"
                >
                  <span class="font-medium">{{ index + 1 }}.</span>
                  {{ cond.variable }} {{ cond.operator }} {{ cond.value }}
                  <span
                    :class="[
                      'ml-2 px-2 py-0.5 rounded text-xs',
                      cond.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    ]"
                  >
                    {{ cond.enabled ? 'Active' : 'Disabled' }}
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="text-gray-500">No entry conditions configured. Strategy enters immediately.</p>
          </div>

          <!-- Risk Settings -->
          <div>
            <h3 class="text-lg font-semibold mb-3">Risk Settings</h3>
            <dl class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <dt class="text-sm text-gray-500">Max Loss</dt>
                <dd class="font-medium">
                  {{ store.currentStrategy.risk_settings?.max_loss
                    ? formatCurrency(store.currentStrategy.risk_settings.max_loss)
                    : 'Not set' }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500">Max Loss %</dt>
                <dd class="font-medium">
                  {{ store.currentStrategy.risk_settings?.max_loss_pct
                    ? store.currentStrategy.risk_settings.max_loss_pct + '%'
                    : 'Not set' }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500">Trailing Stop</dt>
                <dd class="font-medium">
                  {{ store.currentStrategy.risk_settings?.trailing_stop?.enabled ? 'Enabled' : 'Disabled' }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500">Time Stop</dt>
                <dd class="font-medium">
                  {{ store.currentStrategy.risk_settings?.time_stop || 'Not set' }}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <!-- Timestamps -->
      <div class="mt-4 text-sm text-gray-500">
        <p>Created: {{ formatDateTime(store.currentStrategy.created_at) }}</p>
        <p>Last Updated: {{ formatDateTime(store.currentStrategy.updated_at) }}</p>
        <p>Version: {{ store.currentStrategy.version }}</p>
      </div>
    </template>

    <!-- Error -->
    <div v-if="store.error" class="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-red-800">{{ store.error }}</p>
      <button @click="store.clearError" class="text-red-600 underline mt-2">Dismiss</button>
    </div>
  </div>
</template>
