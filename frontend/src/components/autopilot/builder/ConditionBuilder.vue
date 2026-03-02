<template>
  <div class="condition-builder" data-testid="condition-builder">
    <div class="builder-header">
      <h4 class="text-sm font-medium text-gray-900">Multi-Condition Entry Logic (#17)</h4>
      <p class="text-xs text-gray-500 mt-1">
        Build complex entry conditions with AND/OR logic groups
      </p>
    </div>

    <div class="builder-body mt-4">
      <!-- Condition Groups -->
      <div class="condition-groups">
        <div
          v-for="(group, groupIndex) in localGroups"
          :key="group.id"
          class="condition-group"
          :data-testid="`condition-group-${groupIndex}`"
        >
          <!-- Group Header -->
          <div class="group-header">
            <div class="group-title">
              <i class="fas fa-layer-group"></i>
              <span>Group {{ groupIndex + 1 }}</span>
              <span class="group-operator-badge" :class="getOperatorClass(group.operator)">
                {{ group.operator }}
              </span>
            </div>
            <button
              v-if="localGroups.length > 1"
              @click="removeGroup(groupIndex)"
              class="remove-group-btn"
              :data-testid="`remove-group-${groupIndex}`"
              title="Remove group"
            >
              <i class="fas fa-trash-alt"></i>
            </button>
          </div>

          <!-- Group Operator (AND/OR within group) -->
          <div class="group-operator-selector">
            <label class="text-xs text-gray-600">Conditions within group:</label>
            <div class="operator-buttons">
              <button
                @click="setGroupOperator(groupIndex, 'AND')"
                :class="getOperatorButtonClass(group.operator, 'AND')"
                :data-testid="`group-${groupIndex}-operator-and`"
              >
                AND
              </button>
              <button
                @click="setGroupOperator(groupIndex, 'OR')"
                :class="getOperatorButtonClass(group.operator, 'OR')"
                :data-testid="`group-${groupIndex}-operator-or`"
              >
                OR
              </button>
            </div>
          </div>

          <!-- Conditions List -->
          <div class="conditions-list">
            <div
              v-for="(condition, conditionIndex) in group.conditions"
              :key="condition.id"
              class="condition-row"
              :data-testid="`condition-${groupIndex}-${conditionIndex}`"
              draggable="true"
              @dragstart="handleDragStart(groupIndex, conditionIndex, $event)"
              @dragover.prevent
              @drop="handleDrop(groupIndex, conditionIndex, $event)"
            >
              <!-- Drag Handle -->
              <div class="drag-handle">
                <i class="fas fa-grip-vertical"></i>
              </div>

              <!-- Status Indicator -->
              <div class="condition-status-indicator">
                <span
                  :class="['status-icon', getStatusClass(getConditionStatus(groupIndex, conditionIndex))]"
                  :title="`Condition ${getConditionStatus(groupIndex, conditionIndex)}`"
                  data-testid="autopilot-condition-status-icon"
                >
                  {{ getStatusIcon(getConditionStatus(groupIndex, conditionIndex)) }}
                </span>
              </div>

              <!-- Variable -->
              <div class="condition-field">
                <label class="text-xs text-gray-600">Variable</label>
                <select
                  v-model="condition.variable"
                  @change="emitUpdate"
                  :data-testid="`condition-${groupIndex}-${conditionIndex}-variable`"
                  class="condition-select"
                >
                  <option value="" disabled>Select variable...</option>
                  <option
                    v-for="variable in availableVariables"
                    :key="variable"
                    :value="variable"
                  >
                    {{ variable }}
                  </option>
                </select>
              </div>

              <!-- Operator -->
              <div class="condition-field">
                <label class="text-xs text-gray-600">Operator</label>
                <select
                  v-model="condition.operator"
                  @change="emitUpdate"
                  :data-testid="`condition-${groupIndex}-${conditionIndex}-operator`"
                  class="condition-select"
                >
                  <option value="equals">=</option>
                  <option value="not_equals">≠</option>
                  <option value="greater_than">></option>
                  <option value="less_than"><</option>
                  <option value="greater_equal">≥</option>
                  <option value="less_equal">≤</option>
                  <option value="between">Between</option>
                </select>
              </div>

              <!-- Value -->
              <div class="condition-field">
                <label class="text-xs text-gray-600">Value</label>
                <input
                  v-if="condition.operator !== 'between'"
                  type="text"
                  v-model="condition.value"
                  @input="emitUpdate"
                  :data-testid="`condition-${groupIndex}-${conditionIndex}-value`"
                  class="condition-input"
                  placeholder="Enter value"
                />
                <div v-else class="value-range">
                  <input
                    type="text"
                    v-model="condition.value_min"
                    @input="emitUpdate"
                    class="condition-input-small"
                    placeholder="Min"
                  />
                  <span class="range-separator">to</span>
                  <input
                    type="text"
                    v-model="condition.value_max"
                    @input="emitUpdate"
                    class="condition-input-small"
                    placeholder="Max"
                  />
                </div>
              </div>

              <!-- Remove Condition -->
              <button
                @click="removeCondition(groupIndex, conditionIndex)"
                class="remove-condition-btn"
                :data-testid="`remove-condition-${groupIndex}-${conditionIndex}`"
                title="Remove condition"
              >
                <i class="fas fa-times"></i>
              </button>
            </div>

            <!-- Add Condition Button -->
            <button
              @click="addCondition(groupIndex)"
              class="add-condition-btn"
              :data-testid="`add-condition-group-${groupIndex}`"
            >
              <i class="fas fa-plus"></i>
              Add Condition
            </button>
          </div>
        </div>

        <!-- Group Separator (AND/OR between groups) -->
        <div
          v-if="localGroups.length > 1"
          class="group-separator"
        >
          <div class="separator-line"></div>
          <div class="separator-operator">
            <button
              @click="toggleBetweenGroupsOperator"
              class="between-groups-operator-btn"
              data-testid="between-groups-operator"
            >
              {{ betweenGroupsOperator }}
            </button>
          </div>
          <div class="separator-line"></div>
        </div>
      </div>

      <!-- Add Group Button -->
      <button
        @click="addGroup"
        class="add-group-btn"
        data-testid="add-group-btn"
      >
        <i class="fas fa-plus-circle"></i>
        Add Condition Group
      </button>

      <!-- Natural Language Summary -->
      <div v-if="showNaturalLanguage" class="natural-language-summary" data-testid="natural-language-summary">
        <div class="summary-header" data-testid="autopilot-condition-summary-header">
          <i class="fas fa-comment-dots"></i>
          <span class="font-medium">Plain English Summary</span>
        </div>
        <div class="summary-body" data-testid="autopilot-condition-summary-body">
          <p class="summary-text">{{ generateNaturalLanguage() }}</p>
        </div>
      </div>

      <!-- Tree View Toggle -->
      <div class="view-controls">
        <button
          @click="toggleTreeView"
          class="view-toggle-btn"
          data-testid="tree-view-toggle"
        >
          <i :class="showTreeView ? 'fas fa-list' : 'fas fa-sitemap'"></i>
          {{ showTreeView ? 'Show List View' : 'Show Tree View' }}
        </button>
      </div>

      <!-- Visual Tree View -->
      <div v-if="showTreeView" class="tree-view" data-testid="tree-view">
        <div class="tree-view-header">
          <i class="fas fa-sitemap"></i>
          <span class="font-medium">Visual Flow</span>
        </div>
        <div class="tree-view-body">
          <div class="tree-node tree-root" data-testid="autopilot-condition-tree-root">
            <div class="tree-node-label" data-testid="autopilot-condition-tree-node-label">ENTRY POINT</div>
            <div class="tree-children" data-testid="autopilot-condition-tree-children">
              <div
                v-for="(group, groupIndex) in localGroups"
                :key="group.id"
                class="tree-group"
              >
                <!-- Group Node -->
                <div class="tree-node tree-group-node" :data-testid="'autopilot-condition-tree-group-' + groupIndex">
                  <div class="tree-node-label" data-testid="autopilot-condition-tree-node-label">
                    GROUP {{ groupIndex + 1 }}
                    <span class="tree-operator-badge" data-testid="autopilot-condition-tree-operator" :class="getOperatorClass(group.operator)">
                      {{ group.operator }}
                    </span>
                  </div>
                  <div class="tree-children" data-testid="autopilot-condition-tree-children">
                    <div
                      v-for="(condition, conditionIndex) in group.conditions.filter(c => c.variable && c.value)"
                      :key="condition.id"
                      class="tree-node tree-condition-node"
                    >
                      <span
                        :class="['tree-status-icon', getStatusClass(getConditionStatus(groupIndex, conditionIndex))]"
                        data-testid="autopilot-condition-tree-status-icon"
                      >
                        {{ getStatusIcon(getConditionStatus(groupIndex, conditionIndex)) }}
                      </span>
                      <div class="tree-condition-content">
                        <span class="tree-condition-variable">{{ condition.variable }}</span>
                        <span class="tree-condition-operator">
                          {{ ['equals', 'not_equals', 'greater_than', 'less_than', 'greater_equal', 'less_equal', 'between'].includes(condition.operator) ?
                             { 'equals': '=', 'not_equals': '≠', 'greater_than': '>', 'less_than': '<', 'greater_equal': '≥', 'less_equal': '≤', 'between': 'BETWEEN' }[condition.operator] : condition.operator }}
                        </span>
                        <span class="tree-condition-value">
                          {{ condition.operator === 'between' ? `${condition.value_min} - ${condition.value_max}` : condition.value }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Between Groups Operator -->
                <div v-if="groupIndex < localGroups.length - 1" class="tree-connector">
                  <div class="tree-connector-line"></div>
                  <span class="tree-connector-operator">{{ betweenGroupsOperator }}</span>
                  <div class="tree-connector-line"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Expression Preview -->
      <div v-if="!showTreeView" class="expression-preview" data-testid="expression-preview">
        <div class="preview-header">
          <i class="fas fa-code"></i>
          <span class="font-medium">Expression Preview</span>
        </div>
        <div class="preview-body">
          <code class="expression-code">{{ generateExpression() }}</code>
        </div>
        <div v-if="validationError" class="preview-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>{{ validationError }}</span>
        </div>
      </div>

      <!-- Help Section -->
      <div class="help-section">
        <div class="help-header">
          <i class="fas fa-info-circle"></i>
          <span class="font-medium">How It Works</span>
        </div>
        <div class="help-content">
          <ul class="help-list">
            <li>
              <strong>Within a group:</strong> Choose AND (all conditions must be true) or OR
              (any condition can be true)
            </li>
            <li>
              <strong>Between groups:</strong> Click the operator button to toggle between AND/OR
            </li>
            <li>
              <strong>Drag & drop:</strong> Reorder conditions by dragging the grip icon
            </li>
            <li>
              <strong>Example:</strong> "(TIME > 09:20 AND VIX < 15) OR (SPOT > 25000)"
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  availableVariables: {
    type: Array,
    default: () => [
      'TIME.CURRENT',
      'SPOT.PRICE',
      'VOLATILITY.VIX',
      'STRATEGY.PNL',
      'STRATEGY.DELTA',
      'STRATEGY.GAMMA',
      'STRATEGY.THETA',
      'STRATEGY.VEGA',
      'STRATEGY.DTE',
      'IV.RANK',
      'OI.PCR'
    ]
  }
})

const emit = defineEmits(['update:modelValue'])

// Initialize with default group if empty
const localGroups = ref(
  props.modelValue.length > 0
    ? props.modelValue
    : [createDefaultGroup()]
)

const betweenGroupsOperator = ref('OR')
const validationError = ref(null)
const draggedItem = ref(null)
const showTreeView = ref(false)
const showNaturalLanguage = ref(true)

// Mock evaluation status (in real implementation, this would come from backend)
const evaluationStatus = ref({
  isEvaluating: false,
  results: {}
})

watch(() => props.modelValue, (newValue) => {
  if (newValue.length > 0) {
    localGroups.value = newValue
  }
}, { deep: true })

function createDefaultGroup() {
  return {
    id: generateId(),
    operator: 'AND',
    conditions: [createDefaultCondition()]
  }
}

function createDefaultCondition() {
  return {
    id: generateId(),
    variable: '',
    operator: 'greater_than',
    value: '',
    value_min: '',
    value_max: ''
  }
}

function generateId() {
  return `id_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function addGroup() {
  localGroups.value.push(createDefaultGroup())
  emitUpdate()
}

function removeGroup(groupIndex) {
  localGroups.value.splice(groupIndex, 1)
  if (localGroups.value.length === 0) {
    localGroups.value = [createDefaultGroup()]
  }
  emitUpdate()
}

function addCondition(groupIndex) {
  localGroups.value[groupIndex].conditions.push(createDefaultCondition())
  emitUpdate()
}

function removeCondition(groupIndex, conditionIndex) {
  localGroups.value[groupIndex].conditions.splice(conditionIndex, 1)
  // Remove group if no conditions left
  if (localGroups.value[groupIndex].conditions.length === 0) {
    removeGroup(groupIndex)
  } else {
    emitUpdate()
  }
}

function setGroupOperator(groupIndex, operator) {
  localGroups.value[groupIndex].operator = operator
  emitUpdate()
}

function toggleBetweenGroupsOperator() {
  betweenGroupsOperator.value = betweenGroupsOperator.value === 'AND' ? 'OR' : 'AND'
  emitUpdate()
}

function getOperatorClass(operator) {
  return operator === 'AND' ? 'operator-and' : 'operator-or'
}

function getOperatorButtonClass(currentOperator, buttonOperator) {
  return [
    'operator-btn',
    currentOperator === buttonOperator ? 'operator-btn-active' : 'operator-btn-inactive'
  ]
}

function handleDragStart(groupIndex, conditionIndex, event) {
  draggedItem.value = { groupIndex, conditionIndex }
  event.dataTransfer.effectAllowed = 'move'
  event.target.classList.add('dragging')
}

function handleDrop(groupIndex, conditionIndex, event) {
  event.preventDefault()
  const dragged = draggedItem.value

  if (!dragged) return

  // Only allow reordering within the same group for now
  if (dragged.groupIndex === groupIndex && dragged.conditionIndex !== conditionIndex) {
    const group = localGroups.value[groupIndex]
    const draggedCondition = group.conditions[dragged.conditionIndex]

    // Remove from old position
    group.conditions.splice(dragged.conditionIndex, 1)

    // Insert at new position
    const newIndex = dragged.conditionIndex < conditionIndex ? conditionIndex - 1 : conditionIndex
    group.conditions.splice(newIndex, 0, draggedCondition)

    emitUpdate()
  }

  draggedItem.value = null
  document.querySelector('.dragging')?.classList.remove('dragging')
}

function generateExpression() {
  if (localGroups.value.length === 0) {
    return 'No conditions defined'
  }

  const groupExpressions = localGroups.value.map(group => {
    const conditions = group.conditions
      .filter(c => c.variable && c.value)
      .map(c => {
        const operatorSymbol = {
          'equals': '=',
          'not_equals': '≠',
          'greater_than': '>',
          'less_than': '<',
          'greater_equal': '≥',
          'less_equal': '≤',
          'between': 'BETWEEN'
        }[c.operator] || c.operator

        if (c.operator === 'between' && c.value_min && c.value_max) {
          return `${c.variable} BETWEEN ${c.value_min} AND ${c.value_max}`
        }

        return `${c.variable} ${operatorSymbol} ${c.value}`
      })

    if (conditions.length === 0) return ''
    if (conditions.length === 1) return conditions[0]

    return `(${conditions.join(` ${group.operator} `)})`
  }).filter(expr => expr.length > 0)

  if (groupExpressions.length === 0) {
    return 'Enter at least one complete condition'
  }

  if (groupExpressions.length === 1) {
    return groupExpressions[0]
  }

  return groupExpressions.join(` ${betweenGroupsOperator.value} `)
}

function validateConditions() {
  validationError.value = null

  // Check for incomplete conditions
  for (const group of localGroups.value) {
    for (const condition of group.conditions) {
      if (!condition.variable) {
        validationError.value = 'All conditions must have a variable selected'
        return false
      }
      if (!condition.value && condition.operator !== 'between') {
        validationError.value = 'All conditions must have a value'
        return false
      }
      if (condition.operator === 'between' && (!condition.value_min || !condition.value_max)) {
        validationError.value = 'Between conditions must have both min and max values'
        return false
      }
    }
  }

  return true
}

function emitUpdate() {
  validateConditions()
  emit('update:modelValue', localGroups.value)
}

// Generate natural language summary
function generateNaturalLanguage() {
  if (localGroups.value.length === 0) {
    return 'No conditions have been configured yet.'
  }

  const groupSummaries = localGroups.value.map((group, groupIndex) => {
    const conditions = group.conditions
      .filter(c => c.variable && c.value)
      .map(c => {
        const variable = c.variable.replace(/\./g, ' ').toLowerCase()
        const operatorText = {
          'equals': 'equals',
          'not_equals': 'does not equal',
          'greater_than': 'is greater than',
          'less_than': 'is less than',
          'greater_equal': 'is greater than or equal to',
          'less_equal': 'is less than or equal to',
          'between': 'is between'
        }[c.operator] || c.operator

        if (c.operator === 'between' && c.value_min && c.value_max) {
          return `${variable} ${operatorText} ${c.value_min} and ${c.value_max}`
        }

        return `${variable} ${operatorText} ${c.value}`
      })

    if (conditions.length === 0) return ''
    if (conditions.length === 1) return conditions[0]

    const connector = group.operator === 'AND' ? ' and ' : ' or '
    return conditions.join(connector)
  }).filter(summary => summary.length > 0)

  if (groupSummaries.length === 0) {
    return 'Please complete at least one condition.'
  }

  if (groupSummaries.length === 1) {
    return `Enter when ${groupSummaries[0]}.`
  }

  const connector = betweenGroupsOperator.value === 'AND' ? ', and ' : ', or '
  return `Enter when ${groupSummaries.join(connector)}.`
}

// Toggle tree view
function toggleTreeView() {
  showTreeView.value = !showTreeView.value
}

// Get condition status (mock for now)
function getConditionStatus(groupIndex, conditionIndex) {
  const key = `${groupIndex}-${conditionIndex}`
  return evaluationStatus.value.results[key] || 'unknown'
}

// Get status icon
function getStatusIcon(status) {
  const icons = {
    'met': '✓',
    'not_met': '✗',
    'unknown': '○'
  }
  return icons[status] || '○'
}

// Get status class
function getStatusClass(status) {
  const classes = {
    'met': 'status-met',
    'not_met': 'status-not-met',
    'unknown': 'status-unknown'
  }
  return classes[status] || 'status-unknown'
}
</script>

<style scoped>
.condition-builder {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
}

.builder-header h4 {
  color: #1f2937;
}

.builder-body {
  margin-top: 1rem;
}

.condition-groups {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.condition-group {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  background: #f9fafb;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #1f2937;
}

.group-title i {
  color: #3b82f6;
}

.group-operator-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.operator-and {
  background: #dbeafe;
  color: #1e40af;
}

.operator-or {
  background: #fef3c7;
  color: #92400e;
}

.remove-group-btn {
  padding: 0.375rem 0.75rem;
  background: white;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  color: #dc2626;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-group-btn:hover {
  background: #fef2f2;
  border-color: #dc2626;
}

.group-operator-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: white;
  border-radius: 6px;
}

.operator-buttons {
  display: flex;
  gap: 0.5rem;
}

.operator-btn {
  padding: 0.375rem 1rem;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  font-size: 0.875rem;
}

.operator-btn-inactive:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.operator-btn-active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.condition-row {
  display: grid;
  grid-template-columns: auto auto 1fr 1fr 1.5fr auto;
  gap: 0.75rem;
  align-items: end;
  padding: 0.75rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: move;
  transition: all 0.2s;
}

.condition-row:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.condition-row.dragging {
  opacity: 0.5;
}

.drag-handle {
  display: flex;
  align-items: center;
  color: #9ca3af;
  cursor: grab;
  padding: 0.5rem 0;
}

.drag-handle:active {
  cursor: grabbing;
}

.condition-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.condition-field label {
  font-weight: 500;
}

.condition-select,
.condition-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  font-size: 0.875rem;
}

.condition-select:focus,
.condition-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.value-range {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.condition-input-small {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
}

.range-separator {
  color: #6b7280;
  font-size: 0.875rem;
}

.remove-condition-btn {
  padding: 0.5rem 0.75rem;
  background: white;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  color: #dc2626;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-condition-btn:hover {
  background: #fef2f2;
  border-color: #dc2626;
}

.add-condition-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px dashed #9ca3af;
  border-radius: 4px;
  color: #3b82f6;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.add-condition-btn:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

.group-separator {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: -0.5rem 0;
}

.separator-line {
  flex: 1;
  height: 2px;
  background: #e5e7eb;
}

.between-groups-operator-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 2px solid #3b82f6;
  border-radius: 6px;
  color: #3b82f6;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 60px;
}

.between-groups-operator-btn:hover {
  background: #3b82f6;
  color: white;
}

.add-group-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  background: white;
  border: 2px dashed #9ca3af;
  border-radius: 8px;
  color: #3b82f6;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-weight: 600;
  margin-top: 1rem;
}

.add-group-btn:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

.expression-preview {
  margin-top: 1.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  border-bottom: 1px solid #e5e7eb;
  color: #1f2937;
}

.preview-body {
  padding: 1rem;
  background: #1f2937;
}

.expression-code {
  display: block;
  color: #10b981;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.preview-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border-top: 1px solid #fca5a5;
  color: #991b1b;
  font-size: 0.875rem;
}

.help-section {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #eff6ff;
  border: 1px solid #93c5fd;
  border-radius: 8px;
}

.help-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #1e40af;
  margin-bottom: 0.75rem;
}

.help-content {
  color: #1e40af;
}

.help-list {
  margin-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.help-list li {
  line-height: 1.6;
}

/* ===== Status Indicators ===== */
.condition-status-indicator {
  display: flex;
  align-items: center;
  padding: 0.5rem 0;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
}

.status-met {
  background: #d1fae5;
  color: #10b981;
}

.status-not-met {
  background: #fee2e2;
  color: #ef4444;
}

.status-unknown {
  background: #f3f4f6;
  color: #9ca3af;
}

/* ===== Natural Language Summary ===== */
.natural-language-summary {
  margin-top: 1.5rem;
  border: 2px solid #bfdbfe;
  border-radius: 8px;
  overflow: hidden;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #3b82f6;
  color: white;
  font-weight: 600;
}

.summary-body {
  padding: 1rem;
}

.summary-text {
  font-size: 1rem;
  color: #1e40af;
  line-height: 1.6;
  margin: 0;
  font-weight: 500;
}

/* ===== View Controls ===== */
.view-controls {
  margin-top: 1.5rem;
  display: flex;
  justify-content: center;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: white;
  border: 2px solid #3b82f6;
  border-radius: 6px;
  color: #3b82f6;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.view-toggle-btn:hover {
  background: #3b82f6;
  color: white;
}

/* ===== Tree View ===== */
.tree-view {
  margin-top: 1rem;
  border: 2px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
}

.tree-view-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  border-bottom: 2px solid #d1d5db;
  color: #1f2937;
  font-weight: 600;
}

.tree-view-body {
  padding: 1.5rem;
  background: white;
  overflow-x: auto;
}

.tree-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tree-root {
  width: 100%;
}

.tree-node-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.875rem;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
  margin-bottom: 1.5rem;
}

.tree-operator-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.2);
}

.tree-children {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  width: 100%;
}

.tree-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tree-group-node .tree-node-label {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  box-shadow: 0 4px 6px rgba(139, 92, 246, 0.3);
}

.tree-condition-node {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 0.75rem;
  transition: all 0.2s;
  min-width: 300px;
}

.tree-condition-node:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
  transform: translateY(-2px);
}

.tree-status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.tree-condition-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  font-size: 0.875rem;
}

.tree-condition-variable {
  font-weight: 600;
  color: #1f2937;
}

.tree-condition-operator {
  color: #3b82f6;
  font-weight: 700;
  font-size: 1rem;
}

.tree-condition-value {
  font-weight: 600;
  color: #10b981;
}

.tree-connector {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  margin: 0.5rem 0;
}

.tree-connector-line {
  flex: 1;
  height: 3px;
  background: linear-gradient(90deg, #e5e7eb 0%, #d1d5db 50%, #e5e7eb 100%);
  border-radius: 2px;
}

.tree-connector-operator {
  padding: 0.5rem 1rem;
  background: white;
  border: 3px solid #f59e0b;
  border-radius: 6px;
  color: #f59e0b;
  font-weight: 800;
  font-size: 0.875rem;
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.2);
}
</style>
