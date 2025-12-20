<template>
  <div class="orders-tab" data-testid="autopilot-orders-tab">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p class="loading-text">Loading orders...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-text">{{ error }}</p>
      <button @click="fetchOrders" class="retry-btn">Retry</button>
    </div>

    <!-- Orders List -->
    <div v-else-if="orderBatches.length > 0" class="orders-list">
      <div class="orders-header">
        <h3 class="orders-title">Order History</h3>
        <p class="orders-subtitle">
          {{ totalOrders }} {{ totalOrders === 1 ? 'order' : 'orders' }} across {{ orderBatches.length }} {{ orderBatches.length === 1 ? 'batch' : 'batches' }}
        </p>
      </div>

      <!-- Order Batches -->
      <div class="batches-list">
        <OrderBatchCard
          v-for="batch in orderBatches"
          :key="batch.id"
          :batch="batch"
          :show-strategy-name="false"
        />
      </div>

      <!-- Pagination (if needed) -->
      <div v-if="hasMoreOrders" class="pagination">
        <button
          @click="loadMoreOrders"
          :disabled="loadingMore"
          class="load-more-btn"
          data-testid="autopilot-orders-load-more"
        >
          {{ loadingMore ? 'Loading...' : 'Load More' }}
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <div class="empty-icon">📋</div>
      <h3 class="empty-title">No Orders Yet</h3>
      <p class="empty-text">
        Orders will appear here once the strategy starts executing trades.
      </p>
      <p class="empty-hint">
        Make sure the strategy is activated and entry conditions are met.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import OrderBatchCard from './OrderBatchCard.vue'

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  }
})

const store = useAutopilotStore()
const loading = ref(false)
const loadingMore = ref(false)
const error = ref(null)
const orderBatches = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const totalOrders = computed(() => {
  return orderBatches.value.reduce((sum, batch) => sum + batch.total_orders, 0)
})

const hasMoreOrders = computed(() => {
  return orderBatches.value.length < totalCount.value
})

const fetchOrders = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await store.fetchStrategyOrders(props.strategyId, {
      page: currentPage.value,
      page_size: pageSize.value
    })

    if (response) {
      orderBatches.value = response.batches || []
      totalCount.value = response.total || orderBatches.value.length
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to load orders'
  } finally {
    loading.value = false
  }
}

const loadMoreOrders = async () => {
  loadingMore.value = true
  currentPage.value += 1

  try {
    const response = await store.fetchStrategyOrders(props.strategyId, {
      page: currentPage.value,
      page_size: pageSize.value
    })

    if (response && response.batches) {
      orderBatches.value = [...orderBatches.value, ...response.batches]
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to load more orders'
    currentPage.value -= 1 // Revert page increment on error
  } finally {
    loadingMore.value = false
  }
}

onMounted(() => {
  fetchOrders()
})
</script>

<style scoped>
.orders-tab {
  min-height: 400px;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  font-size: 14px;
  color: #6b7280;
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.error-text {
  font-size: 14px;
  color: #ef4444;
  margin-bottom: 16px;
}

.retry-btn {
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.retry-btn:hover {
  background-color: #2563eb;
}

/* Orders List */
.orders-list {
  padding: 0;
}

.orders-header {
  margin-bottom: 20px;
}

.orders-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 4px 0;
}

.orders-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.batches-list {
  display: flex;
  flex-direction: column;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.load-more-btn {
  padding: 10px 24px;
  background-color: white;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.load-more-btn:hover:not(:disabled) {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px 0;
}

.empty-text {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 8px 0;
  max-width: 400px;
}

.empty-hint {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
  font-style: italic;
}
</style>
