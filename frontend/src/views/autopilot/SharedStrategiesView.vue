<script setup>
/**
 * AutoPilot Shared Strategies List View
 *
 * Lists all publicly shared strategies that can be browsed and cloned
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

const sharedStrategies = ref([])
const loading = ref(true)
const error = ref(null)

// For future: fetch public shared strategies
// Currently this is a placeholder - the API endpoint would need to be added
onMounted(async () => {
  loading.value = false
  // await loadSharedStrategies()
})

const openSharedStrategy = (token) => {
  router.push(`/autopilot/shared/${token}`)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN')
}
</script>

<template>
  <KiteLayout>
  <div class="shared-list-page" data-testid="autopilot-shared-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Shared Strategies</h1>
        <p class="page-subtitle">Browse publicly shared strategies</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading shared strategies...</p>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Empty State -->
      <div
        v-if="sharedStrategies.length === 0"
        class="empty-state"
        data-testid="autopilot-shared-strategies-list"
      >
        <p class="empty-text">No publicly shared strategies available.</p>
        <p class="empty-hint">Strategies shared with "public" visibility will appear here.</p>
      </div>

      <!-- Shared Strategies List -->
      <div
        v-else
        class="strategies-list"
        data-testid="autopilot-shared-strategies-list"
      >
        <div
          v-for="strategy in sharedStrategies"
          :key="strategy.share_token"
          class="strategy-card"
          :data-testid="`autopilot-shared-strategy-${strategy.share_token}`"
          @click="openSharedStrategy(strategy.share_token)"
        >
          <div class="strategy-info">
            <h3 class="strategy-name">{{ strategy.name }}</h3>
            <p class="strategy-meta">
              {{ strategy.underlying }} | {{ strategy.legs_count }} legs
            </p>
            <p class="strategy-description">{{ strategy.description || 'No description' }}</p>
          </div>
          <div class="strategy-actions">
            <span class="views-count">{{ strategy.share_views || 0 }} views</span>
            <span class="shared-date">Shared {{ formatDate(strategy.share_created_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
  </KiteLayout>
</template>

<style scoped>
.shared-list-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
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

.empty-state {
  text-align: center;
  padding: 48px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.empty-text {
  color: var(--kite-text-primary);
  font-size: 1.125rem;
  margin-bottom: 8px;
}

.empty-hint {
  color: var(--kite-text-secondary);
  font-size: 0.875rem;
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.strategy-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.strategy-card:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.strategy-name {
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 4px;
}

.strategy-meta {
  font-size: 0.875rem;
  color: var(--kite-blue);
  margin-bottom: 8px;
}

.strategy-description {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.strategy-actions {
  text-align: right;
}

.views-count {
  display: block;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.shared-date {
  display: block;
  font-size: 0.75rem;
  color: var(--kite-text-muted);
}
</style>
