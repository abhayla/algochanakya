<template>
  <KiteLayout>
    <div class="orders-page" data-testid="autopilot-orders-page">
      <!-- Header -->
      <div class="page-header">
        <div>
          <div class="title-row">
            <button
              @click="router.push('/autopilot')"
              class="back-btn"
              data-testid="autopilot-orders-back"
            >
              &larr;
            </button>
            <h1 class="page-title">Order History</h1>
          </div>
          <p class="page-subtitle">
            Complete history of all AutoPilot orders with market snapshots
          </p>
        </div>

        <div class="header-actions">
          <button
            @click="refreshOrders"
            :disabled="loading"
            class="btn-refresh"
            data-testid="autopilot-orders-refresh"
          >
            {{ loading ? 'Refreshing...' : 'Refresh' }}
          </button>
        </div>
      </div>

      <!-- Filters -->
      <OrderFilters
        v-model="filters"
        :strategies="strategies"
        @apply="handleApplyFilters"
      />

      <!-- Summary Stats -->
      <div v-if="!loading && orderBatches.length > 0" class="summary-bar">
        <div class="summary-item">
          <span class="summary-label">Total Batches</span>
          <span class="summary-value">{{ totalBatches }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Total Orders</span>
          <span class="summary-value">{{ totalOrders }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Live Trades</span>
          <span class="summary-value summary-live">{{ liveOrdersCount }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">Paper Trades</span>
          <span class="summary-value summary-paper">{{ paperOrdersCount }}</span>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading && !orderBatches.length" class="loading-state">
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
        <OrderBatchCard
          v-for="batch in orderBatches"
          :key="batch.id"
          :batch="batch"
          :show-strategy-name="true"
        />

        <!-- Pagination -->
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
        <h3 class="empty-title">No Orders Found</h3>
        <p class="empty-text">
          {{ filters.strategy_id || filters.purpose || filters.trading_mode
            ? 'No orders match the selected filters. Try adjusting your filters.'
            : 'No orders have been placed yet. Activate a strategy to start trading.'
          }}
        </p>
        <button
          v-if="hasActiveFilters"
          @click="clearFiltersAndRefresh"
          class="clear-filters-btn"
        >
          Clear Filters
        </button>
      </div>
    </div>
  </KiteLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import OrderFilters from '@/components/autopilot/orders/OrderFilters.vue'
import OrderBatchCard from '@/components/autopilot/orders/OrderBatchCard.vue'

const router = useRouter()
const store = useAutopilotStore()

const loading = ref(false)
const loadingMore = ref(false)
const error = ref(null)
const orderBatches = ref([])
const strategies = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)

const filters = ref({
  from_date: null,
  to_date: null,
  strategy_id: null,
  purpose: null,
  trading_mode: null
})

const hasActiveFilters = computed(() => {
  return filters.value.strategy_id !== null ||
         filters.value.purpose !== null ||
         filters.value.trading_mode !== null ||
         filters.value.from_date !== null ||
         filters.value.to_date !== null
})

const totalBatches = computed(() => orderBatches.value.length)

const totalOrders = computed(() => {
  return orderBatches.value.reduce((sum, batch) => sum + batch.total_orders, 0)
})

const liveOrdersCount = computed(() => {
  return orderBatches.value
    .filter(batch => batch.trading_mode === 'live')
    .reduce((sum, batch) => sum + batch.total_orders, 0)
})

const paperOrdersCount = computed(() => {
  return orderBatches.value
    .filter(batch => batch.trading_mode === 'paper')
    .reduce((sum, batch) => sum + batch.total_orders, 0)
})

const hasMoreOrders = computed(() => {
  return orderBatches.value.length < totalCount.value
})

const fetchOrders = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await store.fetchOrderBatches({
      ...filters.value,
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
    const response = await store.fetchOrderBatches({
      ...filters.value,
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

const refreshOrders = () => {
  currentPage.value = 1
  fetchOrders()
}

const handleApplyFilters = () => {
  currentPage.value = 1
  fetchOrders()
}

const clearFiltersAndRefresh = () => {
  filters.value = {
    from_date: null,
    to_date: null,
    strategy_id: null,
    purpose: null,
    trading_mode: null
  }
  currentPage.value = 1
  fetchOrders()
}

const fetchStrategies = async () => {
  try {
    await store.fetchStrategies()
    strategies.value = store.strategies
  } catch (e) {
    console.error('Failed to load strategies:', e)
  }
}

onMounted(async () => {
  await Promise.all([
    fetchStrategies(),
    fetchOrders()
  ])
})
</script>

<style scoped>
.orders-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.back-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s;
}

.back-btn:hover {
  color: #111827;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn-refresh {
  padding: 8px 16px;
  background-color: white;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  gap: 20px;
  padding: 16px 20px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.summary-live {
  color: #10b981;
}

.summary-paper {
  color: #f59e0b;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
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
  padding: 80px 20px;
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
  margin-bottom: 40px;
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
  padding: 100px 20px;
  text-align: center;
  background: white;
  border: 2px dashed #e5e7eb;
  border-radius: 12px;
}

.empty-icon {
  font-size: 72px;
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
  margin: 0 0 20px 0;
  max-width: 500px;
  line-height: 1.6;
}

.clear-filters-btn {
  padding: 10px 20px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.clear-filters-btn:hover {
  background-color: #2563eb;
}

/* Responsive */
@media (max-width: 768px) {
  .orders-page {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
  }

  .btn-refresh {
    flex: 1;
  }

  .summary-bar {
    flex-wrap: wrap;
    gap: 16px;
  }

  .summary-item {
    flex: 1;
    min-width: 45%;
  }
}
</style>
