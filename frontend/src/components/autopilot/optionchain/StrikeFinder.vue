<template>
  <div class="strike-finder" v-if="visible">
    <div class="finder-header">
      <h3>Strike Finder</h3>
      <button @click="$emit('close')" class="close-btn">×</button>
    </div>

    <div class="finder-content">
      <!-- Mode Selection -->
      <div class="form-group">
        <label>Find By</label>
        <select v-model="mode" data-testid="autopilot-strike-finder-mode" class="form-select">
          <option value="delta">Delta</option>
          <option value="premium">Premium</option>
        </select>
      </div>

      <!-- Option Type Selection -->
      <div class="form-group">
        <label>Option Type</label>
        <select v-model="optionType" data-testid="autopilot-strike-finder-type" class="form-select">
          <option value="CE">Call (CE)</option>
          <option value="PE">Put (PE)</option>
        </select>
      </div>

      <!-- Delta Input -->
      <div v-if="mode === 'delta'" class="form-group">
        <label>Target Delta (0-1)</label>
        <input
          v-model.number="targetDelta"
          type="number"
          step="0.01"
          min="0"
          max="1"
          placeholder="e.g., 0.30"
          data-testid="autopilot-strike-finder-delta-input"
          class="form-input"
        />
        <small class="hint">Enter delta value between 0 and 1</small>
      </div>

      <!-- Premium Input -->
      <div v-if="mode === 'premium'" class="form-group">
        <label>Target Premium (₹)</label>
        <input
          v-model.number="targetPremium"
          type="number"
          step="0.5"
          min="0"
          placeholder="e.g., 180"
          data-testid="autopilot-strike-finder-premium-input"
          class="form-input"
        />
        <small class="hint">Enter target premium in rupees</small>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="error-message" data-testid="autopilot-strike-finder-error">
        {{ error }}
      </div>

      <!-- Search Button -->
      <button
        @click="handleSearch"
        :disabled="!canSearch || loading"
        data-testid="autopilot-strike-finder-search-btn"
        class="btn btn-primary btn-block"
      >
        <span v-if="loading">Searching...</span>
        <span v-else>Find Strike</span>
      </button>

      <!-- Result Display -->
      <div v-if="result" class="result-section" data-testid="autopilot-strike-finder-result">
        <h4>Result</h4>
        <div class="result-content">
          <div class="result-item">
            <span class="label">Strike:</span>
            <span class="value strike-value">{{ result.strike }}</span>
          </div>
          <div class="result-item">
            <span class="label">LTP:</span>
            <span class="value">₹{{ result.ltp?.toFixed(2) }}</span>
          </div>
          <div class="result-item">
            <span class="label">Delta:</span>
            <span class="value">{{ result.delta?.toFixed(3) }}</span>
          </div>
          <div class="result-item">
            <span class="label">IV:</span>
            <span class="value">{{ result.iv ? (result.iv * 100).toFixed(1) + '%' : '-' }}</span>
          </div>
        </div>
        <button @click="$emit('select-strike', result)" class="btn btn-secondary btn-block">
          Select This Strike
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useOptionChain } from '@/composables/autopilot/useOptionChain'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  underlying: {
    type: String,
    required: true
  },
  expiry: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close', 'select-strike'])

const { findStrikeByDelta, findStrikeByPremium } = useOptionChain()

const mode = ref('delta')
const optionType = ref('CE')
const targetDelta = ref(null)
const targetPremium = ref(null)
const result = ref(null)
const loading = ref(false)
const error = ref(null)

const canSearch = computed(() => {
  if (mode.value === 'delta') {
    return targetDelta.value !== null && targetDelta.value >= 0 && targetDelta.value <= 1
  } else {
    return targetPremium.value !== null && targetPremium.value > 0
  }
})

const handleSearch = async () => {
  error.value = null
  result.value = null
  loading.value = true

  try {
    if (mode.value === 'delta') {
      const response = await findStrikeByDelta({
        underlying: props.underlying,
        expiry: props.expiry,
        option_type: optionType.value,
        target_delta: targetDelta.value
      })
      result.value = response
    } else {
      const response = await findStrikeByPremium({
        underlying: props.underlying,
        expiry: props.expiry,
        option_type: optionType.value,
        target_premium: targetPremium.value
      })
      result.value = response
    }
  } catch (err) {
    error.value = err.message || 'Failed to find strike'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.strike-finder {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 16px;
  border: 2px solid #3b82f6;
}

.finder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.finder-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.finder-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.form-select,
.form-input {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.hint {
  font-size: 12px;
  color: #6b7280;
}

.error-message {
  padding: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 13px;
}

.btn {
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-block {
  width: 100%;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.result-section {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 6px;
  padding: 16px;
  margin-top: 8px;
}

.result-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #166534;
  margin: 0 0 12px 0;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-item .label {
  font-size: 13px;
  color: #6b7280;
}

.result-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.strike-value {
  font-size: 18px;
  color: #166534;
}
</style>
