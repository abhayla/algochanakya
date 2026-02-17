<script setup>
/**
 * BrokerSettings
 *
 * Settings component for configuring:
 * 1. Market Data Source — platform default or user's own broker API
 * 2. Order Execution Broker — which broker to route orders through
 */
import { ref, computed, onMounted } from 'vue'
import { useBrokerPreferencesStore } from '@/stores/brokerPreferences'
import { useWatchlistStore } from '@/stores/watchlist'

const store = useBrokerPreferencesStore()
const watchlistStore = useWatchlistStore()

// Local state — track unsaved changes
const localMarketDataSource = ref('platform')
const localOrderBroker = ref(null)
const saveSuccess = ref(false)
const saveError = ref(null)

onMounted(async () => {
  if (!store.preferences) {
    await store.fetchPreferences()
  }
  localMarketDataSource.value = store.marketDataSource
  localOrderBroker.value = store.orderBroker
})

const hasChanges = computed(() => {
  return (
    localMarketDataSource.value !== store.marketDataSource ||
    localOrderBroker.value !== store.orderBroker
  )
})

const handleSave = async () => {
  saveError.value = null
  saveSuccess.value = false
  const oldMarketDataSource = store.marketDataSource
  try {
    await store.updatePreferences({
      market_data_source: localMarketDataSource.value,
      order_broker: localOrderBroker.value || undefined,
    })
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 3000)

    // If market data source changed, reconnect WebSocket to use updated broker
    if (oldMarketDataSource !== localMarketDataSource.value && watchlistStore.isConnected) {
      watchlistStore.disconnectWebSocket()
      watchlistStore.connectWebSocket()
    }
  } catch (err) {
    saveError.value = store.error || 'Failed to save broker settings'
  }
}

const handleReset = () => {
  localMarketDataSource.value = store.marketDataSource
  localOrderBroker.value = store.orderBroker
  saveError.value = null
  saveSuccess.value = false
}
</script>

<template>
  <div class="broker-settings" data-testid="settings-broker-section">

    <!-- Market Data Source -->
    <div class="broker-setting-group">
      <div class="group-header">
        <h3 class="group-title">Market Data Source</h3>
        <p class="group-subtitle">
          Choose where live quotes and OHLC data come from.
          Platform Default uses our shared SmartAPI connection — free, zero setup.
        </p>
      </div>

      <div class="setting-row">
        <label class="setting-label" for="broker-market-data-select">Data Source</label>
        <div class="setting-control">
          <select
            id="broker-market-data-select"
            v-model="localMarketDataSource"
            class="broker-select"
            data-testid="settings-broker-market-data-select"
          >
            <option
              v-for="option in store.marketDataSourceOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
          <p v-if="localMarketDataSource === 'platform'" class="setting-hint">
            Using platform SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite failover chain.
          </p>
          <p v-else class="setting-hint">
            Using your personal {{ store.marketDataSourceOptions.find(o => o.value === localMarketDataSource)?.label }} connection.
          </p>
        </div>
      </div>
    </div>

    <div class="broker-settings-divider"></div>

    <!-- Order Execution Broker -->
    <div class="broker-setting-group">
      <div class="group-header">
        <h3 class="group-title">Order Execution Broker</h3>
        <p class="group-subtitle">
          All orders are placed through your personal broker account (SEBI-compliant).
          Configure credentials in your broker's OAuth settings.
        </p>
      </div>

      <div class="setting-row">
        <label class="setting-label" for="broker-order-select">Order Broker</label>
        <div class="setting-control">
          <select
            id="broker-order-select"
            v-model="localOrderBroker"
            class="broker-select"
            data-testid="settings-broker-order-select"
          >
            <option value="">Not configured</option>
            <option
              v-for="option in store.orderBrokerOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
          <p v-if="!localOrderBroker" class="setting-hint setting-hint-warn">
            No order broker configured. Connect a broker to place trades.
          </p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="broker-settings-actions">
      <p v-if="saveSuccess" class="save-success" data-testid="settings-broker-save-success">
        Broker settings saved successfully.
      </p>
      <p v-if="saveError" class="save-error" data-testid="settings-broker-save-error">
        {{ saveError }}
      </p>

      <div class="action-buttons">
        <button
          v-show="hasChanges"
          class="btn btn-outline"
          @click="handleReset"
          data-testid="settings-broker-reset-btn"
        >
          Reset
        </button>
        <button
          class="btn btn-primary"
          :disabled="!hasChanges || store.saving"
          @click="handleSave"
          data-testid="settings-broker-save-btn"
        >
          {{ store.saving ? 'Saving…' : 'Save Broker Settings' }}
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.broker-settings {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.broker-setting-group {
  padding: 4px 0 20px;
}

.group-header {
  margin-bottom: 20px;
}

.group-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px;
}

.group-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

.setting-row {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 16px;
  align-items: start;
}

.setting-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  padding-top: 8px;
}

.setting-control {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.broker-select {
  width: 100%;
  max-width: 320px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #111827;
  background: white;
  cursor: pointer;
  appearance: auto;
}

.broker-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.setting-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.setting-hint-warn {
  color: #d97706;
}

.broker-settings-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 0 20px;
}

.broker-settings-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 8px;
}

.action-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
}

.btn-outline {
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.btn-outline:hover {
  background: #f9fafb;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.save-success {
  font-size: 13px;
  color: #059669;
  margin: 0;
}

.save-error {
  font-size: 13px;
  color: #dc2626;
  margin: 0;
}

@media (max-width: 640px) {
  .setting-row {
    grid-template-columns: 1fr;
  }
}
</style>
