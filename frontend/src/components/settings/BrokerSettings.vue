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

const sourceCardOptions = [
  { value: 'platform', label: 'Platform Default', description: 'Shared AngelOne + Upstox connection with automatic failover.' },
  { value: 'smartapi', label: 'AngelOne SmartAPI', description: 'Free real-time data with 20-level market depth.' },
  { value: 'kite', label: 'Zerodha Kite', description: 'Uses your Kite login. Requires daily re-login (~6 AM IST).' },
  { value: 'upstox', label: 'Upstox', description: 'Free market data via Upstox API.' },
  { value: 'dhan', label: 'Dhan', description: 'Free market data via Dhan API.' },
  { value: 'fyers', label: 'Fyers', description: 'Free market data via Fyers API.' },
  { value: 'paytm', label: 'Paytm Money', description: 'Free market data via Paytm Money API.' },
]

onMounted(async () => {
  await Promise.all([
    store.preferences ? Promise.resolve() : store.fetchPreferences(),
    store.fetchCredentialStatus(),
  ])
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

const refreshCredentialStatus = () => {
  store.fetchCredentialStatus()
}

defineExpose({ refreshCredentialStatus })

const handleReset = () => {
  localMarketDataSource.value = store.marketDataSource
  localOrderBroker.value = store.orderBroker
  saveError.value = null
  saveSuccess.value = false
}
</script>

<template>
  <div class="broker-settings" data-testid="settings-broker-section">

    <!-- Market Data Source — Rich Cards -->
    <div class="broker-setting-group">
      <div class="group-header">
        <h3 class="group-title">Market Data Source</h3>
        <p class="group-subtitle">
          Choose where live quotes and OHLC data come from.
          Platform Default uses our shared AngelOne + Upstox connections with automatic failover.
        </p>
      </div>

      <div class="source-cards" data-testid="settings-broker-market-data-cards">
        <label
          v-for="option in sourceCardOptions"
          :key="option.value"
          :class="['source-card', {
            selected: localMarketDataSource === option.value,
            unconfigured: option.value !== 'platform' && !store.isBrokerConfigured(option.value)
          }]"
          :data-testid="'settings-source-card-' + option.value"
        >
          <input
            type="radio"
            name="market-data-source"
            :value="option.value"
            v-model="localMarketDataSource"
          />
          <div class="source-card-content">
            <div class="source-card-header">
              <span class="source-card-name">{{ option.label }}</span>
              <span v-if="localMarketDataSource === option.value" class="badge badge-current">Current</span>
              <span v-else-if="option.value === 'platform'" class="badge badge-available">Available</span>
              <span v-else-if="store.isBrokerConfigured(option.value)" class="badge badge-configured">Configured</span>
              <span v-else class="badge badge-not-configured">Not Configured</span>
            </div>
            <p class="source-card-desc">{{ option.description }}</p>
          </div>
        </label>
      </div>

      <p v-if="localMarketDataSource !== 'platform' && !store.isBrokerConfigured(localMarketDataSource)" class="source-warning" data-testid="settings-source-warning">
        Configure {{ store.marketDataSourceOptions.find(o => o.value === localMarketDataSource)?.label }} credentials below first — data will use platform default until connected.
      </p>
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

/* Source Cards */
.source-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.source-card:hover:not(.selected) {
  border-color: #93c5fd;
  background: #f8fafc;
}

.source-card.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.source-card.unconfigured:not(.selected) {
  opacity: 0.7;
}

.source-card input[type="radio"] {
  margin-top: 3px;
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.source-card-content {
  flex: 1;
  min-width: 0;
}

.source-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.source-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.source-card-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  line-height: 1.4;
}

.badge {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 10px;
  white-space: nowrap;
}

.badge-current {
  background: #dcfce7;
  color: #16a34a;
}

.badge-configured {
  background: #dbeafe;
  color: #2563eb;
}

.badge-available {
  background: #f0f9ff;
  color: #0284c7;
}

.badge-not-configured {
  background: #fef3c7;
  color: #d97706;
}

.source-warning {
  margin: 12px 0 0;
  padding: 10px 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  font-size: 13px;
  color: #92400e;
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
