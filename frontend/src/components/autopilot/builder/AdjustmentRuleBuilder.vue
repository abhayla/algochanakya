<script setup>
/**
 * Adjustment Rule Builder Component
 *
 * Visual builder for creating adjustment rules with:
 * - Trigger conditions (P&L, Delta, Time, Premium, VIX, Spot)
 * - Actions (Exit, Add Hedge, Roll, Scale)
 * - Cooldown and max executions
 * - Drag-drop reordering
 *
 * Phase 3: Re-Entry & Advanced Adjustments
 */
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

// Local state
const rules = ref([...props.modelValue])
const editingRule = ref(null)
const showRuleModal = ref(false)

// Trigger types
const triggerTypes = [
  { value: 'pnl_based', label: 'P&L Based', icon: '💰', description: 'Trigger based on profit/loss amount or percentage' },
  { value: 'delta_based', label: 'Delta Based', icon: 'Δ', description: 'Trigger when net delta exceeds threshold' },
  { value: 'time_based', label: 'Time Based', icon: '⏰', description: 'Trigger at specific time or after duration' },
  { value: 'premium_based', label: 'Premium Based', icon: '📊', description: 'Trigger based on premium captured %' },
  { value: 'vix_based', label: 'VIX Based', icon: '📈', description: 'Trigger when VIX crosses threshold' },
  { value: 'spot_based', label: 'Spot Based', icon: '🎯', description: 'Trigger when spot price moves by %' }
]

// Action types
const actionTypes = [
  { value: 'exit_all', label: 'Exit All', icon: '🚪', description: 'Close all positions immediately' },
  { value: 'add_hedge', label: 'Add Hedge', icon: '🛡️', description: 'Add hedge on both sides' },
  { value: 'close_leg', label: 'Close Leg', icon: '❌', description: 'Close specific leg(s)' },
  { value: 'roll_strike', label: 'Roll Strike', icon: '🔄', description: 'Roll to new strikes' },
  { value: 'roll_expiry', label: 'Roll Expiry', icon: '📅', description: 'Roll to next expiry' },
  { value: 'scale_down', label: 'Scale Down', icon: '📉', description: 'Reduce position size' },
  { value: 'scale_up', label: 'Scale Up', icon: '📈', description: 'Increase position size' }
]

// Add new rule
const addRule = () => {
  editingRule.value = {
    name: `Rule ${rules.value.length + 1}`,
    trigger_type: 'pnl_based',
    trigger_config: {
      threshold: 0,
      comparison: 'greater_than'
    },
    action_type: 'exit_all',
    action_config: {},
    cooldown_seconds: 300,
    max_executions: 1,
    execution_count: 0,
    enabled: true
  }
  showRuleModal.value = true
}

// Edit existing rule
const editRule = (rule, index) => {
  editingRule.value = { ...rule, _index: index }
  showRuleModal.value = true
}

// Save rule
const saveRule = () => {
  if (editingRule.value._index !== undefined) {
    // Update existing rule
    rules.value[editingRule.value._index] = { ...editingRule.value }
    delete rules.value[editingRule.value._index]._index
  } else {
    // Add new rule
    rules.value.push({ ...editingRule.value })
  }
  emitUpdate()
  closeRuleModal()
}

// Delete rule
const deleteRule = (index) => {
  if (confirm(`Delete "${rules.value[index].name}"?`)) {
    rules.value.splice(index, 1)
    emitUpdate()
  }
}

// Close modal
const closeRuleModal = () => {
  showRuleModal.value = false
  editingRule.value = null
}

// Move rule up/down
const moveRule = (index, direction) => {
  const newIndex = direction === 'up' ? index - 1 : index + 1
  if (newIndex < 0 || newIndex >= rules.value.length) return

  const temp = rules.value[index]
  rules.value[index] = rules.value[newIndex]
  rules.value[newIndex] = temp
  emitUpdate()
}

// Emit update to parent
const emitUpdate = () => {
  emit('update:modelValue', rules.value)
}

// Get trigger type object
const getTriggerType = (value) => {
  return triggerTypes.find(t => t.value === value) || triggerTypes[0]
}

// Get action type object
const getActionType = (value) => {
  return actionTypes.find(a => a.value === value) || actionTypes[0]
}

// Format cooldown display
const formatCooldown = (seconds) => {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}min`
  return `${Math.floor(seconds / 3600)}h`
}

// Trigger summary
const getTriggerSummary = (rule) => {
  const config = rule.trigger_config || {}
  switch (rule.trigger_type) {
    case 'pnl_based':
      return `P&L ${config.comparison === 'greater_than' ? '>' : '<'} ${config.threshold_type === 'pct' ? config.threshold + '%' : '₹' + config.threshold}`
    case 'delta_based':
      return `Net Delta > ${config.threshold || 0}`
    case 'time_based':
      return `At ${config.time || 'time'}`
    case 'premium_based':
      return `Premium captured > ${config.threshold || 0}%`
    case 'vix_based':
      return `VIX ${config.comparison === 'greater_than' ? '>' : '<'} ${config.threshold || 0}`
    case 'spot_based':
      return `Spot change > ${config.threshold || 0}%`
    default:
      return 'Trigger condition'
  }
}
</script>

<template>
  <div class="adjustment-rule-builder" data-testid="autopilot-adjustment-rule-builder">
    <!-- Header -->
    <div class="builder-header">
      <div class="header-left">
        <h3 class="builder-title">Adjustment Rules</h3>
        <p class="builder-subtitle">Automatic actions based on market conditions</p>
      </div>
      <button
        @click="addRule"
        class="btn btn-primary"
        data-testid="autopilot-add-rule-btn"
      >
        + Add Rule
      </button>
    </div>

    <!-- Rules List -->
    <div v-if="rules.length > 0" class="rules-list">
      <div
        v-for="(rule, index) in rules"
        :key="index"
        class="rule-card"
        :data-testid="`autopilot-rule-card-${index}`"
      >
        <!-- Rule Header -->
        <div class="rule-header">
          <div class="rule-header-left">
            <span class="rule-number">{{ index + 1 }}</span>
            <h4 class="rule-name">{{ rule.name }}</h4>
            <span
              class="rule-status"
              :class="{ 'status-enabled': rule.enabled, 'status-disabled': !rule.enabled }"
            >
              {{ rule.enabled ? 'Enabled' : 'Disabled' }}
            </span>
          </div>
          <div class="rule-actions">
            <!-- Move Up -->
            <button
              v-if="index > 0"
              @click="moveRule(index, 'up')"
              class="rule-action-btn"
              title="Move up"
              :data-testid="`autopilot-move-rule-up-${index}`"
            >
              ▲
            </button>
            <!-- Move Down -->
            <button
              v-if="index < rules.length - 1"
              @click="moveRule(index, 'down')"
              class="rule-action-btn"
              title="Move down"
              :data-testid="`autopilot-move-rule-down-${index}`"
            >
              ▼
            </button>
            <!-- Edit -->
            <button
              @click="editRule(rule, index)"
              class="rule-action-btn"
              :data-testid="`autopilot-edit-rule-${index}`"
            >
              ✎
            </button>
            <!-- Delete -->
            <button
              @click="deleteRule(index)"
              class="rule-action-btn rule-action-delete"
              :data-testid="`autopilot-delete-rule-${index}`"
            >
              ×
            </button>
          </div>
        </div>

        <!-- Rule Content -->
        <div class="rule-content">
          <div class="rule-flow">
            <!-- WHEN -->
            <div class="flow-section">
              <span class="flow-label">WHEN</span>
              <div class="flow-value">
                <span class="flow-icon">{{ getTriggerType(rule.trigger_type).icon }}</span>
                <span class="flow-text">{{ getTriggerSummary(rule) }}</span>
              </div>
            </div>

            <!-- Arrow -->
            <div class="flow-arrow">→</div>

            <!-- THEN -->
            <div class="flow-section">
              <span class="flow-label">THEN</span>
              <div class="flow-value">
                <span class="flow-icon">{{ getActionType(rule.action_type).icon }}</span>
                <span class="flow-text">{{ getActionType(rule.action_type).label }}</span>
              </div>
            </div>
          </div>

          <!-- Rule Meta -->
          <div class="rule-meta">
            <span class="meta-item">
              Cooldown: {{ formatCooldown(rule.cooldown_seconds) }}
            </span>
            <span class="meta-separator">•</span>
            <span class="meta-item">
              Max: {{ rule.max_executions }} {{ rule.max_executions === 1 ? 'time' : 'times' }}
            </span>
            <span v-if="rule.execution_count > 0" class="meta-separator">•</span>
            <span v-if="rule.execution_count > 0" class="meta-item meta-executed">
              Executed: {{ rule.execution_count }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="rules-empty">
      <div class="empty-icon">⚙️</div>
      <p class="empty-text">No adjustment rules configured</p>
      <p class="empty-subtext">
        Add rules to automatically adjust your strategy based on market conditions
      </p>
      <button
        @click="addRule"
        class="btn btn-primary"
        data-testid="autopilot-add-first-rule-btn"
      >
        + Add First Rule
      </button>
    </div>

    <!-- Rule Editor Modal -->
    <div v-if="showRuleModal" class="modal-overlay" @click.self="closeRuleModal">
      <div class="modal-content modal-large" data-testid="autopilot-rule-modal">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ editingRule._index !== undefined ? 'Edit Rule' : 'Add Rule' }}
          </h3>
          <button @click="closeRuleModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <!-- Rule Name -->
          <div class="form-group">
            <label class="form-label">Rule Name</label>
            <input
              v-model="editingRule.name"
              type="text"
              class="form-input"
              placeholder="e.g., Delta Hedge"
              data-testid="autopilot-rule-name"
            />
          </div>

          <!-- Trigger Type -->
          <div class="form-group">
            <label class="form-label">Trigger Condition</label>
            <select
              v-model="editingRule.trigger_type"
              class="form-select"
              data-testid="autopilot-rule-trigger-type"
            >
              <option
                v-for="trigger in triggerTypes"
                :key="trigger.value"
                :value="trigger.value"
              >
                {{ trigger.icon }} {{ trigger.label }}
              </option>
            </select>
            <p class="form-help">{{ getTriggerType(editingRule.trigger_type).description }}</p>
          </div>

          <!-- Action Type -->
          <div class="form-group">
            <label class="form-label">Action</label>
            <select
              v-model="editingRule.action_type"
              class="form-select"
              data-testid="autopilot-rule-action-type"
            >
              <option
                v-for="action in actionTypes"
                :key="action.value"
                :value="action.value"
              >
                {{ action.icon }} {{ action.label }}
              </option>
            </select>
            <p class="form-help">{{ getActionType(editingRule.action_type).description }}</p>
          </div>

          <!-- Cooldown -->
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Cooldown (seconds)</label>
              <input
                v-model.number="editingRule.cooldown_seconds"
                type="number"
                min="0"
                step="60"
                class="form-input"
                data-testid="autopilot-rule-cooldown"
              />
            </div>

            <!-- Max Executions -->
            <div class="form-group">
              <label class="form-label">Max Executions</label>
              <input
                v-model.number="editingRule.max_executions"
                type="number"
                min="1"
                class="form-input"
                data-testid="autopilot-rule-max-executions"
              />
            </div>
          </div>

          <!-- Enabled Toggle -->
          <div class="form-group">
            <label class="form-checkbox">
              <input
                v-model="editingRule.enabled"
                type="checkbox"
                data-testid="autopilot-rule-enabled"
              />
              <span>Enable this rule</span>
            </label>
          </div>
        </div>

        <div class="modal-footer">
          <button
            @click="closeRuleModal"
            class="btn btn-secondary"
            data-testid="autopilot-rule-cancel"
          >
            Cancel
          </button>
          <button
            @click="saveRule"
            class="btn btn-primary"
            data-testid="autopilot-rule-save"
          >
            {{ editingRule._index !== undefined ? 'Update Rule' : 'Add Rule' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.adjustment-rule-builder {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 20px;
}

/* ===== Header ===== */
.builder-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.header-left {
  flex: 1;
}

.builder-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px 0;
}

.builder-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

/* ===== Rules List ===== */
.rules-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rule-card {
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 16px;
  transition: all 0.2s;
}

.rule-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

/* ===== Rule Header ===== */
.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.rule-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.rule-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.rule-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.rule-status {
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 4px;
}

.status-enabled {
  background: #d1fae5;
  color: #065f46;
}

.status-disabled {
  background: #fee2e2;
  color: #991b1b;
}

.rule-actions {
  display: flex;
  gap: 4px;
}

.rule-action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.15s;
}

.rule-action-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.rule-action-delete:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

/* ===== Rule Content ===== */
.rule-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-flow {
  display: flex;
  align-items: center;
  gap: 16px;
}

.flow-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flow-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.flow-value {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.flow-icon {
  font-size: 20px;
}

.flow-text {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.flow-arrow {
  font-size: 24px;
  color: #9ca3af;
  flex-shrink: 0;
}

.rule-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
}

.meta-separator {
  color: #d1d5db;
}

.meta-executed {
  color: #3b82f6;
  font-weight: 500;
}

/* ===== Empty State ===== */
.rules-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: #6b7280;
  margin: 0 0 8px 0;
}

.empty-subtext {
  font-size: 14px;
  color: #9ca3af;
  margin: 0 0 24px 0;
  max-width: 400px;
}

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-large {
  max-width: 700px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  font-size: 28px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.modal-close:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}

/* ===== Form Styles ===== */
.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #1f2937;
  transition: border-color 0.15s;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-help {
  font-size: 13px;
  color: #6b7280;
  margin-top: 6px;
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.form-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* ===== Buttons ===== */
.btn {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.btn-primary:hover {
  background: #2563eb;
  border-color: #2563eb;
}

.btn-secondary {
  background: white;
  color: #374151;
  border-color: #d1d5db;
}

.btn-secondary:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}
</style>
