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

      <!-- Expression Preview -->
      <div class="expression-preview" data-testid="expression-preview">
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
  grid-template-columns: auto 1fr 1fr 1.5fr auto;
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
</style>
