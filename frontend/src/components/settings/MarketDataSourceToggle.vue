<script setup>
/**
 * Market Data Source Toggle Component
 *
 * Allows switching between SmartAPI and Kite for market data
 */
import { ref, onMounted, computed } from 'vue'
import * as smartapi from '@/services/smartapi'

const props = defineProps({
  refreshTrigger: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['source-changed'])

// State
const loading = ref(true)
const saving = ref(false)
const error = ref(null)

const sourceData = ref({
  source: 'smartapi',
  smartapi_configured: false,
  kite_configured: false
})

// Computed
const currentSource = computed(() => sourceData.value.source)
const canUseSmartAPI = computed(() => sourceData.value.smartapi_configured)
const canUseKite = computed(() => sourceData.value.kite_configured)

// Methods
async function fetchSource() {
  loading.value = true
  error.value = null
  try {
    sourceData.value = await smartapi.getMarketDataSource()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load market data source'
  } finally {
    loading.value = false
  }
}

async function handleSourceChange(newSource) {
  if (newSource === currentSource.value) return

  // Validate source is configured
  if (newSource === 'smartapi' && !canUseSmartAPI.value) {
    error.value = 'Please configure SmartAPI credentials first'
    return
  }
  if (newSource === 'kite' && !canUseKite.value) {
    error.value = 'Please login with Zerodha first'
    return
  }

  saving.value = true
  error.value = null

  try {
    sourceData.value = await smartapi.updateMarketDataSource(newSource)
    emit('source-changed', newSource)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to update market data source'
    // Revert on error
    await fetchSource()
  } finally {
    saving.value = false
  }
}

// Watch for refresh trigger from parent
import { watch } from 'vue'
watch(() => props.refreshTrigger, () => {
  fetchSource()
})

onMounted(() => {
  fetchSource()
})
</script>

<template>
  <div class="source-toggle" data-testid="market-data-source-toggle">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner-small"></div>
      <span>Loading...</span>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Error -->
      <div v-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <!-- Source Options -->
      <div class="source-options">
        <!-- SmartAPI Option -->
        <label
          class="source-option"
          :class="{
            selected: currentSource === 'smartapi',
            disabled: !canUseSmartAPI
          }"
          data-testid="source-smartapi"
        >
          <input
            type="radio"
            name="market-data-source"
            value="smartapi"
            :checked="currentSource === 'smartapi'"
            :disabled="!canUseSmartAPI || saving"
            @change="handleSourceChange('smartapi')"
          />
          <div class="option-content">
            <div class="option-header">
              <span class="option-title">AngelOne SmartAPI</span>
              <span v-if="currentSource === 'smartapi'" class="current-badge">Current</span>
              <span v-else-if="!canUseSmartAPI" class="not-configured-badge">Not Configured</span>
            </div>
            <p class="option-desc">
              Free real-time data with 20-level market depth. Recommended for live trading.
            </p>
          </div>
        </label>

        <!-- Kite Option -->
        <label
          class="source-option"
          :class="{
            selected: currentSource === 'kite',
            disabled: !canUseKite
          }"
          data-testid="source-kite"
        >
          <input
            type="radio"
            name="market-data-source"
            value="kite"
            :checked="currentSource === 'kite'"
            :disabled="!canUseKite || saving"
            @change="handleSourceChange('kite')"
          />
          <div class="option-content">
            <div class="option-header">
              <span class="option-title">Zerodha Kite</span>
              <span v-if="currentSource === 'kite'" class="current-badge">Current</span>
              <span v-else-if="!canUseKite" class="not-configured-badge">Not Logged In</span>
            </div>
            <p class="option-desc">
              Uses your Kite login for market data. Required for order execution.
            </p>
          </div>
        </label>
      </div>

      <!-- Saving Indicator -->
      <div v-if="saving" class="saving-indicator">
        <div class="loading-spinner-small"></div>
        <span>Switching data source...</span>
      </div>

      <!-- Info Note -->
      <div class="info-note">
        <strong>Note:</strong> Orders are always executed through Zerodha Kite regardless of market data source.
      </div>
    </div>
  </div>
</template>

<style scoped>
.source-toggle {
  padding: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.loading-spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.alert {
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 16px;
}

.alert-error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.source-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.source-option:hover:not(.disabled) {
  border-color: #93c5fd;
  background: #f8fafc;
}

.source-option.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.source-option.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.source-option input[type="radio"] {
  margin-top: 2px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.source-option.disabled input[type="radio"] {
  cursor: not-allowed;
}

.option-content {
  flex: 1;
}

.option-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.option-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.current-badge {
  padding: 2px 8px;
  background: #dcfce7;
  color: #16a34a;
  font-size: 11px;
  font-weight: 500;
  border-radius: 10px;
}

.not-configured-badge {
  padding: 2px 8px;
  background: #fef3c7;
  color: #d97706;
  font-size: 11px;
  font-weight: 500;
  border-radius: 10px;
}

.option-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  line-height: 1.4;
}

.saving-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
}

.info-note {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  font-size: 13px;
  color: #0369a1;
}

.info-note strong {
  font-weight: 600;
}
</style>
