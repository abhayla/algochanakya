<template>
  <div class="order-filters" data-testid="autopilot-orders-filters">
    <div class="filters-row">
      <!-- Date Range -->
      <div class="filter-group">
        <label class="filter-label">From Date</label>
        <input
          type="date"
          v-model="localFilters.from_date"
          class="filter-input"
          data-testid="autopilot-orders-filter-from-date"
        />
      </div>

      <div class="filter-group">
        <label class="filter-label">To Date</label>
        <input
          type="date"
          v-model="localFilters.to_date"
          class="filter-input"
          data-testid="autopilot-orders-filter-to-date"
        />
      </div>

      <!-- Strategy Selection -->
      <div class="filter-group">
        <label class="filter-label">Strategy</label>
        <select
          v-model="localFilters.strategy_id"
          class="filter-select"
          data-testid="autopilot-orders-filter-strategy"
        >
          <option :value="null">All Strategies</option>
          <option
            v-for="strategy in strategies"
            :key="strategy.id"
            :value="strategy.id"
          >
            {{ strategy.name }}
          </option>
        </select>
      </div>

      <!-- Purpose Selection -->
      <div class="filter-group">
        <label class="filter-label">Purpose</label>
        <select
          v-model="localFilters.purpose"
          class="filter-select"
          data-testid="autopilot-orders-filter-purpose"
        >
          <option :value="null">All Purposes</option>
          <option value="entry">Entry</option>
          <option value="adjustment">Adjustment</option>
          <option value="hedge">Hedge</option>
          <option value="exit">Exit</option>
          <option value="roll_close">Roll Close</option>
          <option value="roll_open">Roll Open</option>
          <option value="kill_switch">Kill Switch</option>
        </select>
      </div>

      <!-- Trading Mode Selection -->
      <div class="filter-group">
        <label class="filter-label">Mode</label>
        <select
          v-model="localFilters.trading_mode"
          class="filter-select"
          data-testid="autopilot-orders-filter-mode"
        >
          <option :value="null">All Modes</option>
          <option value="live">Live Trading</option>
          <option value="paper">Paper Trading</option>
        </select>
      </div>

      <!-- Action Buttons -->
      <div class="filter-actions">
        <button
          @click="applyFilters"
          class="btn-apply"
          data-testid="autopilot-orders-filter-apply"
        >
          Apply
        </button>
        <button
          @click="clearFilters"
          class="btn-clear"
          data-testid="autopilot-orders-filter-clear"
        >
          Clear
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  strategies: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: Object,
    default: () => ({
      from_date: null,
      to_date: null,
      strategy_id: null,
      purpose: null,
      trading_mode: null
    })
  }
})

const emit = defineEmits(['update:modelValue', 'apply'])

const localFilters = ref({ ...props.modelValue })

// Watch for external changes
watch(() => props.modelValue, (newVal) => {
  localFilters.value = { ...newVal }
}, { deep: true })

const applyFilters = () => {
  emit('update:modelValue', { ...localFilters.value })
  emit('apply', { ...localFilters.value })
}

const clearFilters = () => {
  localFilters.value = {
    from_date: null,
    to_date: null,
    strategy_id: null,
    purpose: null,
    trading_mode: null
  }
  emit('update:modelValue', { ...localFilters.value })
  emit('apply', { ...localFilters.value })
}
</script>

<style scoped>
.order-filters {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.filters-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  align-items: end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.filter-input,
.filter-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #111827;
  background-color: white;
  transition: border-color 0.2s;
}

.filter-input:focus,
.filter-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.filter-input::placeholder {
  color: #9ca3af;
}

.filter-select {
  cursor: pointer;
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-apply,
.btn-clear {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-apply {
  background-color: #3b82f6;
  color: white;
}

.btn-apply:hover {
  background-color: #2563eb;
}

.btn-clear {
  background-color: white;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-clear:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

/* Responsive */
@media (max-width: 1024px) {
  .filters-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .filters-row {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    width: 100%;
  }

  .btn-apply,
  .btn-clear {
    flex: 1;
  }
}
</style>
