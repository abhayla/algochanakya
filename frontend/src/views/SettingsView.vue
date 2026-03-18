<script setup>
/**
 * General Settings View
 *
 * User preferences and application settings
 */
import { ref, onMounted } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useUserPreferencesStore } from '@/stores/userPreferences'
import { useBrokerPreferencesStore } from '@/stores/brokerPreferences'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import SmartAPISettings from '@/components/settings/SmartAPISettings.vue'
import BrokerSettings from '@/components/settings/BrokerSettings.vue'
import KiteSettings from '@/components/settings/KiteSettings.vue'
import DhanSettings from '@/components/settings/DhanSettings.vue'
import UpstoxSettings from '@/components/settings/UpstoxSettings.vue'
import FyersSettings from '@/components/settings/FyersSettings.vue'
import PaytmSettings from '@/components/settings/PaytmSettings.vue'

const router = useRouter()
const store = useUserPreferencesStore()
const brokerPreferencesStore = useBrokerPreferencesStore()
const brokerSettingsRef = ref(null)

const handleCredentialsUpdated = () => {
  brokerPreferencesStore.fetchCredentialStatus()
}

const localPreferences = ref(null)
const hasChanges = ref(false)
const showSaveToast = ref(false)
const saveError = ref(null)

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
    saveError.value = null
    showSaveToast.value = true
    setTimeout(() => { showSaveToast.value = false }, 3000)
  } catch (error) {
    console.error('Failed to save settings:', error)
    saveError.value = 'Failed to save. Please try again.'
    setTimeout(() => { saveError.value = null }, 5000)
  }
}

const handleReset = () => {
  localPreferences.value = { ...store.preferences }
  hasChanges.value = false
}

const retryLoad = async () => {
  await store.fetchPreferences()
  if (!store.error) {
    localPreferences.value = { ...store.preferences }
  }
}

// #3: Unsaved changes guard
onBeforeRouteLeave(() => {
  if (hasChanges.value) {
    return window.confirm('You have unsaved changes. Leave without saving?')
  }
})
</script>

<template>
  <KiteLayout>
    <div class="settings-page" data-testid="settings-page">
      <!-- Header -->
      <div class="settings-header">
        <div>
          <div class="settings-title-row">
            <button
              @click="router.back()"
              class="back-btn"
              data-testid="settings-back"
              title="Go back to previous page"
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
            :title="!hasChanges ? 'No changes to save' : 'Save your preference changes'"
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

      <!-- Load Error -->
      <div v-else-if="store.error && !localPreferences" class="settings-error-banner" data-testid="settings-load-error">
        <p>{{ store.error }}</p>
        <button @click="retryLoad" class="retry-btn" data-testid="settings-retry-btn">Retry</button>
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

        <!-- Broker Selection Settings -->
        <div class="settings-section" id="broker-selection">
          <div class="section-header">
            <h2 class="section-title">Broker Selection</h2>
            <p class="section-subtitle">Configure your market data source and order execution broker</p>
          </div>
          <div class="section-content">
            <BrokerSettings />
          </div>
        </div>

        <!-- Zerodha / Kite Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Zerodha (Kite Connect)</h2>
            <p class="section-subtitle">Connect your Zerodha account via OAuth. Token expires daily at ~6 AM IST.</p>
          </div>
          <div class="section-content">
            <KiteSettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>

        <!-- SmartAPI Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">AngelOne SmartAPI</h2>
            <p class="section-subtitle">Configure AngelOne credentials for market data and order execution</p>
          </div>
          <div class="section-content">
            <SmartAPISettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>

        <!-- Dhan Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Dhan</h2>
            <p class="section-subtitle">Configure Dhan credentials (static token from developer console)</p>
          </div>
          <div class="section-content">
            <DhanSettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>

        <!-- Upstox Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Upstox</h2>
            <p class="section-subtitle">Connect your Upstox account via OAuth</p>
          </div>
          <div class="section-content">
            <UpstoxSettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>

        <!-- Fyers Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Fyers</h2>
            <p class="section-subtitle">Connect your Fyers account via OAuth</p>
          </div>
          <div class="section-content">
            <FyersSettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>

        <!-- Paytm Money Settings -->
        <div class="settings-section">
          <div class="section-header">
            <h2 class="section-title">Paytm Money</h2>
            <p class="section-subtitle">Connect your Paytm Money account via OAuth</p>
          </div>
          <div class="section-content">
            <PaytmSettings @credentials-updated="handleCredentialsUpdated" />
          </div>
        </div>
      </div>

      <!-- Sticky Save Bar (#2: visible when scrolled) -->
      <Transition name="slide-up">
        <div v-if="hasChanges" class="sticky-save-bar" data-testid="settings-sticky-save">
          <span class="unsaved-label">You have unsaved changes</span>
          <div class="sticky-actions">
            <button @click="handleReset" class="strategy-btn strategy-btn-outline">Reset</button>
            <button @click="handleSave" :disabled="store.saving" class="strategy-btn strategy-btn-primary">
              {{ store.saving ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- Save Toast (#9) -->
      <Transition name="toast-fade">
        <div v-if="showSaveToast" class="save-toast success" data-testid="settings-save-toast">
          Settings saved successfully!
        </div>
      </Transition>
      <Transition name="toast-fade">
        <div v-if="saveError" class="save-toast error" data-testid="settings-save-error">
          {{ saveError }}
          <button @click="handleSave" class="retry-link" data-testid="settings-save-retry">Retry</button>
        </div>
      </Transition>
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

/* Sticky Save Bar (#2) */
.sticky-save-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.08);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 100;
}

.unsaved-label {
  font-size: 14px;
  color: #f57f17;
  font-weight: 500;
}

.sticky-actions {
  display: flex;
  gap: 12px;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* Save Toast (#9) */
.save-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  z-index: 2000;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.save-toast.success {
  background: #00b386;
  color: white;
}

.save-toast.error {
  background: #e74c3c;
  color: white;
  display: flex;
  align-items: center;
  gap: 12px;
}

.retry-link {
  background: none;
  border: 1px solid rgba(255,255,255,0.6);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.retry-link:hover {
  background: rgba(255,255,255,0.15);
}

.settings-error-banner {
  text-align: center;
  padding: 24px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  margin-top: 16px;
}

.settings-error-banner p {
  margin: 0 0 12px;
}

.retry-btn {
  padding: 8px 20px;
  background: #387ed1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.retry-btn:hover {
  background: #2d6ab8;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
