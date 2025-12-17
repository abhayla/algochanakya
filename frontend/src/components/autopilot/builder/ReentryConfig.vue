<script setup>
/**
 * Re-Entry Configuration Component
 *
 * Allows users to configure automatic re-entry after exit.
 * Phase 3: Re-Entry & Advanced Adjustments
 */
import { ref, computed, watch } from 'vue'
import ConditionBuilder from './ConditionBuilder.vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({
      enabled: false,
      max_reentries: 2,
      cooldown_minutes: 15,
      conditions: { logic: 'AND', conditions: [] },
      reentry_count: 0
    })
  }
})

const emit = defineEmits(['update:modelValue'])

// Local state
const config = ref({ ...props.modelValue })

// Computed properties
const isEnabled = computed({
  get: () => config.value.enabled,
  set: (value) => {
    config.value.enabled = value
    emitUpdate()
  }
})

const maxReentries = computed({
  get: () => config.value.max_reentries,
  set: (value) => {
    config.value.max_reentries = parseInt(value)
    emitUpdate()
  }
})

const cooldownMinutes = computed({
  get: () => config.value.cooldown_minutes,
  set: (value) => {
    config.value.cooldown_minutes = parseInt(value)
    emitUpdate()
  }
})

const conditions = computed({
  get: () => config.value.conditions || { logic: 'AND', conditions: [] },
  set: (value) => {
    config.value.conditions = value
    emitUpdate()
  }
})

const reentryCount = computed(() => config.value.reentry_count || 0)

// Watch for external changes
watch(() => props.modelValue, (newValue) => {
  config.value = { ...newValue }
}, { deep: true })

// Emit update to parent
const emitUpdate = () => {
  emit('update:modelValue', config.value)
}

// Max reentries options
const maxReentriesOptions = [
  { value: 1, label: '1 time' },
  { value: 2, label: '2 times' },
  { value: 3, label: '3 times' },
  { value: 5, label: '5 times' },
  { value: 10, label: '10 times' }
]

// Cooldown options (in minutes)
const cooldownOptions = [
  { value: 5, label: '5 minutes' },
  { value: 10, label: '10 minutes' },
  { value: 15, label: '15 minutes' },
  { value: 30, label: '30 minutes' },
  { value: 60, label: '1 hour' },
  { value: 120, label: '2 hours' }
]
</script>

<template>
  <div class="reentry-config" data-testid="autopilot-reentry-config">
    <!-- Header -->
    <div class="reentry-header">
      <div class="reentry-header-left">
        <h3 class="reentry-title">Re-Entry Settings</h3>
        <p class="reentry-subtitle">Automatically re-enter after exit</p>
      </div>
      <div class="reentry-header-right">
        <label class="toggle-switch" data-testid="autopilot-reentry-toggle">
          <input
            type="checkbox"
            v-model="isEnabled"
            class="toggle-input"
          />
          <span class="toggle-slider"></span>
          <span class="toggle-label">{{ isEnabled ? 'Enabled' : 'Disabled' }}</span>
        </label>
      </div>
    </div>

    <!-- Configuration (shown when enabled) -->
    <transition name="fade-slide">
      <div v-if="isEnabled" class="reentry-content">
      <!-- Settings Grid -->
      <div class="reentry-settings">
        <!-- Max Re-entries -->
        <div class="reentry-field">
          <label class="reentry-label">
            Max Re-entries
            <span class="reentry-help">Maximum number of times to re-enter</span>
          </label>
          <select
            v-model="maxReentries"
            class="reentry-select"
            data-testid="autopilot-reentry-max-reentries"
          >
            <option
              v-for="option in maxReentriesOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <!-- Cooldown Period -->
        <div class="reentry-field">
          <label class="reentry-label">
            Cooldown after exit
            <span class="reentry-help">Wait time before checking re-entry conditions</span>
          </label>
          <select
            v-model="cooldownMinutes"
            class="reentry-select"
            data-testid="autopilot-reentry-cooldown"
          >
            <option
              v-for="option in cooldownOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <!-- Re-entry Count (Read-only) -->
        <div v-if="reentryCount > 0" class="reentry-field">
          <label class="reentry-label">
            Re-entry Count
            <span class="reentry-help">Current number of re-entries</span>
          </label>
          <div class="reentry-value" data-testid="autopilot-reentry-count">
            {{ reentryCount }} / {{ maxReentries }}
          </div>
        </div>
      </div>

      <!-- Re-Entry Conditions -->
      <div class="reentry-conditions">
        <div class="conditions-header">
          <h4 class="conditions-title">Re-Entry Conditions</h4>
          <p class="conditions-subtitle">
            Strategy will re-enter when these conditions are met after cooldown period
          </p>
        </div>

        <ConditionBuilder
          v-model="conditions"
          :underlying="'NIFTY'"
          data-testid="autopilot-reentry-conditions"
        />
      </div>

      <!-- Info Box -->
      <div class="reentry-info-box">
        <div class="info-icon">ℹ️</div>
        <div class="info-content">
          <p class="info-title">How Re-Entry Works</p>
          <ul class="info-list">
            <li>After strategy exits, it enters <strong>Re-Entry Waiting</strong> status</li>
            <li>System waits for <strong>{{ cooldownMinutes }} minutes</strong> cooldown period</li>
            <li>Then checks if re-entry conditions are met</li>
            <li>If conditions met, strategy re-enters automatically</li>
            <li>Process repeats up to <strong>{{ maxReentries }} times</strong></li>
            <li>After max re-entries, strategy marks as <strong>Completed</strong></li>
          </ul>
        </div>
      </div>
      </div>
    </transition>

    <!-- Disabled State -->
    <transition name="fade-slide">
      <div v-if="!isEnabled" class="reentry-disabled">
      <div class="disabled-icon">🔄</div>
      <p class="disabled-text">
        Enable re-entry to automatically re-enter the strategy after exit conditions trigger
      </p>
      <p class="disabled-subtext">
        Useful for strategies that benefit from multiple entry/exit cycles during the day
      </p>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* ===== Transitions ===== */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ===== Container ===== */
.reentry-config {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s;
}

.reentry-config:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
}

/* ===== Header ===== */
.reentry-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.reentry-header-left {
  flex: 1;
}

.reentry-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px 0;
}

.reentry-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.reentry-header-right {
  display: flex;
  align-items: center;
}

/* ===== Toggle Switch ===== */
.toggle-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  transition: opacity 0.2s;
}

.toggle-switch:hover {
  opacity: 0.8;
}

.toggle-input {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 48px;
  height: 24px;
  background: #d1d5db;
  border-radius: 24px;
  transition: all 0.3s ease;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.toggle-slider::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-input:checked + .toggle-slider {
  background: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}

.toggle-input:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.toggle-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  transition: color 0.2s;
}

.toggle-input:checked ~ .toggle-label {
  color: #10b981;
  font-weight: 600;
}

/* ===== Content ===== */
.reentry-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ===== Settings Grid ===== */
.reentry-settings {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.reentry-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reentry-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.reentry-help {
  font-size: 12px;
  font-weight: 400;
  color: #9ca3af;
}

.reentry-select {
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #1f2937;
  background: white;
  cursor: pointer;
  transition: border-color 0.15s;
}

.reentry-select:hover {
  border-color: #9ca3af;
}

.reentry-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.reentry-value {
  padding: 10px 12px;
  font-size: 16px;
  font-weight: 600;
  color: #3b82f6;
  background: #eff6ff;
  border-radius: 6px;
}

/* ===== Conditions ===== */
.reentry-conditions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conditions-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conditions-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.conditions-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

/* ===== Info Box ===== */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.reentry-info-box {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 8px;
  border: 1px solid #bfdbfe;
  animation: slideIn 0.4s ease-out;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.info-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.info-content {
  flex: 1;
}

.info-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e40af;
  margin: 0 0 8px 0;
}

.info-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #1e40af;
  line-height: 1.6;
}

.info-list li {
  margin-bottom: 4px;
}

.info-list strong {
  font-weight: 600;
}

/* ===== Disabled State ===== */
.reentry-disabled {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.disabled-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.disabled-text {
  font-size: 15px;
  color: #6b7280;
  margin: 0 0 8px 0;
  max-width: 500px;
}

.disabled-subtext {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
  max-width: 500px;
}
</style>
