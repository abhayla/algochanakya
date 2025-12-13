<template>
  <div class="option-chain-header">
    <div class="controls-row">
      <!-- Underlying Selection -->
      <div class="control-group">
        <label for="underlying-select">Underlying</label>
        <select
          id="underlying-select"
          :value="modelValue.underlying"
          @change="$emit('update:underlying', $event.target.value)"
          data-testid="autopilot-optionchain-underlying-select"
          class="control-select"
        >
          <option value="NIFTY">NIFTY</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
          <option value="FINNIFTY">FINNIFTY</option>
          <option value="SENSEX">SENSEX</option>
        </select>
      </div>

      <!-- Expiry Selection -->
      <div class="control-group">
        <label for="expiry-select">Expiry</label>
        <select
          id="expiry-select"
          :value="modelValue.expiry"
          @change="$emit('update:expiry', $event.target.value)"
          data-testid="autopilot-optionchain-expiry-select"
          class="control-select"
          :disabled="loading || expiries.length === 0"
        >
          <option value="" disabled>{{ expiries.length === 0 ? 'No expiries available' : 'Select expiry' }}</option>
          <option v-for="expiry in expiries" :key="expiry" :value="expiry">
            {{ formatExpiry(expiry) }}
          </option>
        </select>
      </div>

      <!-- Greeks Toggle -->
      <div class="control-group">
        <label class="checkbox-label">
          <input
            type="checkbox"
            :checked="modelValue.showGreeks"
            @change="$emit('update:showGreeks', $event.target.checked)"
            data-testid="autopilot-optionchain-greeks-toggle"
          />
          <span>Show Greeks</span>
        </label>
      </div>

      <!-- Refresh Button -->
      <button
        @click="$emit('refresh')"
        class="btn btn-secondary"
        :disabled="loading"
      >
        <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4v6h-6M1 20v-6h6"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        <span v-if="loading">Loading...</span>
        <span v-else>Refresh</span>
      </button>

      <!-- Strike Finder Button -->
      <button
        @click="$emit('toggle-strike-finder')"
        class="btn btn-primary"
        data-testid="autopilot-optionchain-strike-finder-btn"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        Find Strike
      </button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  expiries: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:underlying', 'update:expiry', 'update:showGreeks', 'refresh', 'toggle-strike-finder'])

const formatExpiry = (expiry) => {
  const date = new Date(expiry)
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.option-chain-header {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 16px;
}

.controls-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-group label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.control-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  min-width: 140px;
}

.control-select:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.control-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 0;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-label span {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
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

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn svg {
  flex-shrink: 0;
}
</style>
