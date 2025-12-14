<template>
  <div class="spot-distance-config" data-testid="spot-distance-config">
    <div class="config-header">
      <h4 class="text-sm font-medium text-gray-900">Spot Distance Alert (#48)</h4>
      <p class="text-xs text-gray-500 mt-1">
        Alert or exit when spot price comes within X% of short strikes
      </p>
    </div>

    <div class="config-body mt-4 space-y-6">
      <!-- Enable/Disable Toggle -->
      <div class="flex items-center justify-between">
        <div>
          <label class="text-sm font-medium text-gray-700">Enable Spot Distance Rule</label>
          <p class="text-xs text-gray-500 mt-0.5">
            Monitor distance between spot and short strikes
          </p>
        </div>
        <input
          type="checkbox"
          v-model="localConfig.enabled"
          @change="emitUpdate"
          data-testid="spot-distance-enabled"
          class="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
        />
      </div>

      <div v-if="localConfig.enabled" class="space-y-4">
        <!-- Distance Threshold -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Distance Threshold
          </label>
          <p class="text-xs text-gray-500 mb-3">
            Alert when spot price is within this percentage of any short strike
          </p>

          <!-- Preset Buttons -->
          <div class="preset-buttons mb-3">
            <button
              v-for="pct in [1, 2, 3, 5]"
              :key="pct"
              @click="setDistancePreset(pct)"
              :class="getPresetClass(pct)"
              :data-testid="`distance-preset-${pct}`"
            >
              {{ pct }}%
            </button>
          </div>

          <!-- Slider -->
          <div class="flex items-center space-x-3">
            <input
              type="range"
              v-model="localConfig.distance_pct"
              @input="emitUpdate"
              min="0.5"
              max="10"
              step="0.5"
              data-testid="distance-slider"
              class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <span class="text-lg font-semibold w-16 text-right">
              {{ localConfig.distance_pct }}%
            </span>
          </div>

          <!-- Visual Indicator -->
          <div class="visual-indicator mt-3">
            <div class="indicator-bar">
              <div
                class="indicator-fill"
                :style="{ width: (localConfig.distance_pct / 10 * 100) + '%' }"
                :class="getIndicatorClass()"
              ></div>
            </div>
            <div class="indicator-labels">
              <span class="text-xs text-gray-500">Tight (0.5%)</span>
              <span class="text-xs text-gray-500">Loose (10%)</span>
            </div>
          </div>
        </div>

        <!-- Apply To -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Apply To
          </label>
          <div class="space-y-2">
            <label class="flex items-center">
              <input
                type="radio"
                v-model="localConfig.apply_to"
                value="all_shorts"
                @change="emitUpdate"
                data-testid="apply-to-all"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">All short strikes</span>
            </label>
            <label class="flex items-center">
              <input
                type="radio"
                v-model="localConfig.apply_to"
                value="specific_leg"
                @change="emitUpdate"
                data-testid="apply-to-specific"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">Specific leg only</span>
            </label>
          </div>

          <!-- Leg Selector (if specific_leg) -->
          <div v-if="localConfig.apply_to === 'specific_leg'" class="mt-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Select Leg
            </label>
            <select
              v-model="localConfig.leg_id"
              @change="emitUpdate"
              data-testid="leg-selector"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="" disabled>Choose a leg...</option>
              <option v-for="leg in availableLegs" :key="leg.id" :value="leg.id">
                {{ leg.label }}
              </option>
            </select>
          </div>
        </div>

        <!-- Action -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Action When Triggered
          </label>
          <div class="action-buttons">
            <button
              @click="setAction('notify')"
              :class="getActionClass('notify')"
              data-testid="action-notify"
            >
              <i class="fas fa-bell"></i>
              <div class="action-label">
                <span class="font-medium">Notify Only</span>
                <span class="text-xs opacity-75">Alert without action</span>
              </div>
            </button>
            <button
              @click="setAction('adjust')"
              :class="getActionClass('adjust')"
              data-testid="action-adjust"
            >
              <i class="fas fa-arrows-alt"></i>
              <div class="action-label">
                <span class="font-medium">Auto-Adjust</span>
                <span class="text-xs opacity-75">Shift threatened leg</span>
              </div>
            </button>
            <button
              @click="setAction('exit')"
              :class="getActionClass('exit')"
              data-testid="action-exit"
            >
              <i class="fas fa-sign-out-alt"></i>
              <div class="action-label">
                <span class="font-medium">Exit Position</span>
                <span class="text-xs opacity-75">Close all legs</span>
              </div>
            </button>
          </div>
        </div>

        <!-- Educational Info -->
        <div class="info-box">
          <div class="info-header">
            <i class="fas fa-lightbulb"></i>
            <span class="font-medium">Professional Tip</span>
          </div>
          <p class="text-sm mt-2">
            <strong>3% Spot Distance Rule:</strong> Many professional traders adjust iron condors
            when spot price comes within 3% of a short strike. This gives time to manage the
            position before it moves deep ITM. Tighter thresholds (1-2%) are aggressive but
            give earlier warnings.
          </p>
          <div class="recommendations mt-3">
            <div class="recommendation-item">
              <span class="badge conservative">Conservative</span>
              <span class="text-sm">5% distance, notify only</span>
            </div>
            <div class="recommendation-item">
              <span class="badge moderate">Moderate</span>
              <span class="text-sm">3% distance, auto-adjust</span>
            </div>
            <div class="recommendation-item">
              <span class="badge aggressive">Aggressive</span>
              <span class="text-sm">1-2% distance, exit position</span>
            </div>
          </div>
        </div>

        <!-- Example Calculation -->
        <div class="example-box">
          <h5 class="text-sm font-medium text-gray-700 mb-2">
            <i class="fas fa-calculator"></i> Example Calculation
          </h5>
          <div class="example-content">
            <div class="example-row">
              <span class="text-sm text-gray-600">Short Strike:</span>
              <span class="text-sm font-semibold">25,500</span>
            </div>
            <div class="example-row">
              <span class="text-sm text-gray-600">{{ localConfig.distance_pct }}% Distance:</span>
              <span class="text-sm font-semibold">{{ calculateDistancePoints() }} points</span>
            </div>
            <div class="example-row highlight">
              <span class="text-sm text-gray-600">Alert Trigger Zone:</span>
              <span class="text-sm font-semibold">
                {{ calculateAlertZone().lower }} - {{ calculateAlertZone().upper }}
              </span>
            </div>
            <div class="example-note mt-2">
              <i class="fas fa-info-circle text-blue-500"></i>
              <span class="text-xs text-gray-600">
                Alert will trigger if spot enters this range
              </span>
            </div>
          </div>
        </div>

        <!-- Auto-Close Toggle (if action is 'exit') -->
        <div v-if="localConfig.action === 'exit'" class="auto-close-section">
          <div class="flex items-center justify-between">
            <div>
              <label class="text-sm font-medium text-gray-700">Auto-Close Position</label>
              <p class="text-xs text-gray-500 mt-0.5">
                Automatically close position when spot distance threshold is breached
              </p>
            </div>
            <input
              type="checkbox"
              v-model="localConfig.auto_close"
              @change="emitUpdate"
              data-testid="auto-close-enabled"
              class="h-4 w-4 text-red-600 rounded focus:ring-red-500"
            />
          </div>

          <div v-if="localConfig.auto_close" class="warning-box mt-3">
            <i class="fas fa-exclamation-triangle"></i>
            <p class="text-sm">
              <strong>Warning:</strong> Position will be automatically closed when spot price
              breaches the {{ localConfig.distance_pct }}% threshold. Ensure this aligns with
              your risk management strategy.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      enabled: false,
      distance_pct: 3,
      apply_to: 'all_shorts',
      leg_id: '',
      action: 'notify',
      auto_close: false
    })
  },
  availableLegs: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const localConfig = ref({ ...props.modelValue })

watch(() => props.modelValue, (newValue) => {
  localConfig.value = { ...newValue }
}, { deep: true })

function emitUpdate() {
  emit('update:modelValue', { ...localConfig.value })
}

function setDistancePreset(pct) {
  localConfig.value.distance_pct = pct
  emitUpdate()
}

function setAction(action) {
  localConfig.value.action = action
  emitUpdate()
}

function getPresetClass(pct) {
  return [
    'preset-btn',
    localConfig.value.distance_pct === pct ? 'preset-btn-active' : 'preset-btn-inactive'
  ]
}

function getActionClass(action) {
  return [
    'action-btn',
    localConfig.value.action === action ? 'action-btn-active' : 'action-btn-inactive'
  ]
}

function getIndicatorClass() {
  if (localConfig.value.distance_pct <= 2) return 'indicator-aggressive'
  if (localConfig.value.distance_pct <= 4) return 'indicator-moderate'
  return 'indicator-conservative'
}

function calculateDistancePoints() {
  const strikePrice = 25500 // Example
  return Math.round(strikePrice * (localConfig.value.distance_pct / 100))
}

function calculateAlertZone() {
  const strikePrice = 25500
  const distance = calculateDistancePoints()
  return {
    lower: strikePrice - distance,
    upper: strikePrice + distance
  }
}
</script>

<style scoped>
.spot-distance-config {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
}

.config-header h4 {
  color: #1f2937;
}

.config-body {
  margin-top: 1rem;
}

.preset-buttons {
  display: flex;
  gap: 0.5rem;
}

.preset-btn {
  flex: 1;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.preset-btn-inactive:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.preset-btn-active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.visual-indicator {
  margin-top: 0.75rem;
}

.indicator-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.indicator-fill {
  height: 100%;
  transition: all 0.3s;
  border-radius: 4px;
}

.indicator-aggressive {
  background: linear-gradient(90deg, #ef4444, #f59e0b);
}

.indicator-moderate {
  background: linear-gradient(90deg, #f59e0b, #10b981);
}

.indicator-conservative {
  background: linear-gradient(90deg, #10b981, #3b82f6);
}

.indicator-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn i {
  font-size: 1.5rem;
  color: #6b7280;
}

.action-btn-active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.action-btn-active i {
  color: #3b82f6;
}

.action-btn:hover:not(.action-btn-active) {
  border-color: #9ca3af;
  background: #f9fafb;
}

.action-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.info-box {
  background: #eff6ff;
  border: 1px solid #93c5fd;
  border-radius: 8px;
  padding: 1rem;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #1e40af;
}

.info-header i {
  font-size: 1.25rem;
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.recommendation-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge.conservative {
  background: #d1fae5;
  color: #065f46;
}

.badge.moderate {
  background: #fef3c7;
  color: #92400e;
}

.badge.aggressive {
  background: #fee2e2;
  color: #991b1b;
}

.example-box {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
}

.example-box h5 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #1f2937;
}

.example-content {
  margin-top: 0.75rem;
}

.example-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.example-row:last-of-type {
  border-bottom: none;
}

.example-row.highlight {
  background: #eff6ff;
  padding: 0.75rem;
  border-radius: 4px;
  margin-top: 0.5rem;
}

.example-note {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 4px;
}

.warning-box {
  display: flex;
  align-items: start;
  gap: 0.75rem;
  padding: 1rem;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
}

.warning-box i {
  color: #dc2626;
  margin-top: 0.125rem;
}

.warning-box p {
  color: #991b1b;
}
</style>
