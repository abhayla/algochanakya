<script setup>
/**
 * General Settings View
 *
 * User preferences and application settings
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserPreferencesStore } from '@/stores/userPreferences'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import SmartAPISettings from '@/components/settings/SmartAPISettings.vue'
import MarketDataSourceToggle from '@/components/settings/MarketDataSourceToggle.vue'
import BrokerSettings from '@/components/settings/BrokerSettings.vue'

const router = useRouter()
const store = useUserPreferencesStore()

// Trigger for refreshing MarketDataSourceToggle after credentials change
const sourceRefreshTrigger = ref(0)

const handleCredentialsUpdated = () => {
  sourceRefreshTrigger.value++
}

const localPreferences = ref(null)
const hasChanges = ref(false)

onMounted(async () => {
  await store.fetchPreferences()
  localPreferences.value = { ...store.preferences }
})

const handleChange = () => {
  hasChanges.value = true
}

const handleSave = async () => {
  try {
    await store.updatePreferences(localPreferences.value)
    hasChanges.value = false
  } catch (error) {
    console.error('Failed to save settings:', error)
  }
}

const handleReset = () => {
  localPreferences.value = { ...store.preferences }
  hasChanges.value = false
}
</script>

<template>
  <KiteLayout>
    <div class="settings-page" data-testid="settings-page">
      <!-- Header -->
      <div class="settings-header">
        <div>
          <div class="settings-title-row">
            <button
              @click="router.push('/dashboard')"
              class="back-btn"
              data-testid="settings-back"
            >
              &larr;
            </button>
            <h1 class="page-title">Settings</h1>
          </div>
          <p class="page-subtitle">Configure your application preferences</p>
        </div>

        <div class="header-actions">
          <button
            v-if="hasChanges"
            @click="handleReset"
            data-testid="settings-reset"
            class="strategy-btn strategy-btn-outline"
          >
            Reset
          </button>
          <button
            @click="handleSave"
            :disabled="!hasChanges || store.saving"
            data-testid="settings-save"
            class="strategy-btn strategy-btn-primary"
          >
            {{ store.saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="store.loading && !localPreferences" class="loading-state">
        <div class="loading-spinner"></div>
        <p class="loading-text">Loading preferences...</p>
      </div>

      <!-- Settings Form -->
      <div v-else-if="localPreferences" class="settings-sections">
        <!-- P/L Grid Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">P/L Grid Settings</h2>
            <p class="section-subtitle">Configure how the P/L grid is displayed in the Strategy Builder</p>
          </div>

          <div class="section-content">
            <!-- Interval Setting -->
            <div class="setting-row">
              <div class="setting-label">
                <label for="pnl-grid-interval">Grid Interval</label>
                <p class="setting-help">
                  Spacing between spot price columns in the P/L grid
                </p>
              </div>
              <div class="setting-control">
                <div class="radio-group">
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="pnl-grid-interval"
                      :value="50"
                      v-model="localPreferences.pnl_grid_interval"
                      @change="handleChange"
                      data-testid="interval-50"
                    />
                    <span>50 points (More granular)</span>
                  </label>
                  <label class="radio-label">
                    <input
                      type="radio"
                      name="pnl-grid-interval"
                      :value="100"
                      v-model="localPreferences.pnl_grid_interval"
                      @change="handleChange"
                      data-testid="interval-100"
                    />
                    <span>100 points (Less cluttered)</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Market Data Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Market Data Source</h2>
            <p class="section-subtitle">Choose where to get live market data from</p>
          </div>
          <div class="section-content">
            <MarketDataSourceToggle
              :refresh-trigger="sourceRefreshTrigger"
              @source-changed="handleCredentialsUpdated"
            />
          </div>
        </div>

        <!-- Broker Selection Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Broker Selection</h2>
            <p class="section-subtitle">Configure your market data source and order execution broker</p>
          </div>
          <div class="section-content">
            <BrokerSettings />
          </div>
        </div>

        <!-- SmartAPI Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">AngelOne SmartAPI</h2>
            <p class="section-subtitle">Configure AngelOne credentials for market data</p>
          </div>
          <div class="section-content">
            <SmartAPISettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>
      </div>
    </div>
  </KiteLayout>
</template>

<style scoped>
.settings-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.settings-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  background: transparent;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #f3f4f6;
  color: #111827;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 8px 0 0 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.strategy-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.strategy-btn-outline {
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.strategy-btn-outline:hover {
  background: #f9fafb;
}

.strategy-btn-primary {
  background: #3b82f6;
  color: white;
}

.strategy-btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.strategy-btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: #6b7280;
  font-size: 14px;
}

.settings-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.section-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.section-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 4px 0 0 0;
}

.section-content {
  padding: 24px;
}

.setting-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

.setting-label label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  margin-bottom: 4px;
}

.setting-help {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.setting-control {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
  cursor: pointer;
}

.radio-label input[type="radio"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
