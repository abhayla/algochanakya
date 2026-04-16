<template>
  <div class="suggestions-panel" data-testid="autopilot-suggestions-panel">
    <!-- Panel Header -->
    <div class="panel-header">
      <div class="header-left">
        <h3>AI Suggestions</h3>
        <span class="suggestions-count">{{ suggestions.length }} {{ suggestions.length === 1 ? 'suggestion' : 'suggestions' }}</span>
      </div>
      <button
        @click="refreshSuggestions"
        :disabled="loading"
        class="refresh-btn"
        data-testid="autopilot-suggestions-refresh-btn"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4v6h-6M1 20v-6h6"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        Refresh
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state" data-testid="autopilot-suggestions-loading">
      <div class="spinner"></div>
      <p>Analyzing strategy and generating suggestions...</p>
    </div>

    <!-- Suggestions List -->
    <div v-else-if="suggestions.length > 0" class="suggestions-list">
      <div
        v-for="suggestion in suggestions"
        :key="suggestion.id"
        class="suggestion-card"
        :class="`priority-${suggestion.urgency?.toLowerCase()}`"
        :data-testid="`autopilot-suggestion-card-${suggestion.id}`"
      >
        <!-- Card Header -->
        <div class="card-header">
          <div class="title-section">
            <h4 data-testid="autopilot-suggestion-title">{{ suggestion.title }}</h4>
            <span
              class="priority-badge"
              :class="`urgency-${suggestion.urgency?.toLowerCase()}`"
              data-testid="autopilot-suggestion-priority"
            >
              {{ suggestion.urgency }}
            </span>
          </div>
          <div class="action-type">{{ formatActionType(suggestion.action_type) }}</div>
        </div>

        <!-- Description -->
        <p class="description" data-testid="autopilot-suggestion-description">
          {{ suggestion.description }}
        </p>

        <!-- Reasoning -->
        <div class="reasoning-section">
          <div class="reasoning-header">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>Why this suggestion?</span>
          </div>
          <p class="reasoning-text" data-testid="autopilot-suggestion-reasoning">
            {{ suggestion.reasoning }}
          </p>
        </div>

        <!-- Impact Section -->
        <div class="impact-section" data-testid="autopilot-suggestion-impact">
          <h5>Estimated Impact</h5>
          <div class="impact-grid">
            <div class="impact-item" v-if="suggestion.details?.estimated_cost">
              <span class="label">Cost:</span>
              <span class="value">₹{{ suggestion.details.estimated_cost.toFixed(2) }}</span>
            </div>
            <div class="impact-item" v-if="suggestion.details?.delta_change">
              <span class="label">Δ Change:</span>
              <span class="value">{{ suggestion.details.delta_change.toFixed(3) }}</span>
            </div>
            <div class="impact-item" v-if="suggestion.details?.risk_reduction">
              <span class="label">Risk Reduction:</span>
              <span class="value profit">{{ suggestion.details.risk_reduction }}%</span>
            </div>
            <div class="impact-item" v-if="suggestion.details?.confidence">
              <span class="label">Confidence:</span>
              <span class="value">{{ suggestion.details.confidence }}%</span>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="card-actions">
          <button
            @click="openExecuteModal(suggestion)"
            class="btn btn-primary"
            data-testid="autopilot-suggestion-execute-btn"
          >
            Execute
          </button>
          <button
            @click="openDismissDialog(suggestion.id)"
            class="btn btn-secondary"
            data-testid="autopilot-suggestion-dismiss-btn"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state" data-testid="autopilot-suggestions-empty">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M9 3h6l3 3v13a2 2 0 01-2 2H8a2 2 0 01-2-2V6l3-3z"/>
        <path d="M9 3v3h6"/>
        <path d="M9 13h6m-6 4h6"/>
      </svg>
      <p data-testid="autopilot-suggestions-empty-message">No suggestions at this time</p>
      <p class="hint">AI will analyze your strategy and provide suggestions based on market conditions</p>
    </div>

    <!-- Execute Confirmation Modal -->
    <Teleport to="body">
      <div v-if="executeModal.visible" class="modal-overlay" @click.self="closeExecuteModal">
        <div class="modal-content" data-testid="autopilot-execute-suggestion-modal">
          <div class="modal-header">
            <h3 data-testid="autopilot-execute-modal-title">{{ executeModal.suggestion?.title }}</h3>
            <button @click="closeExecuteModal" class="close-btn">×</button>
          </div>
          <div class="modal-body">
            <p>{{ executeModal.suggestion?.description }}</p>
            <div class="confirm-info">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>This will execute the suggested adjustment. Are you sure?</span>
            </div>
          </div>
          <div class="modal-footer">
            <button
              @click="closeExecuteModal"
              class="btn btn-secondary"
              data-testid="autopilot-execute-modal-cancel"
            >
              Cancel
            </button>
            <button
              @click="executeSuggestion"
              :disabled="executing"
              class="btn btn-primary"
              data-testid="autopilot-execute-modal-confirm"
            >
              {{ executing ? 'Executing...' : 'Confirm Execute' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Dismiss Confirmation Dialog -->
    <Teleport to="body">
      <div v-if="dismissDialog.visible" class="modal-overlay" @click.self="closeDismissDialog">
        <div class="modal-content small" data-testid="autopilot-dismiss-suggestion-dialog">
          <div class="modal-header">
            <h3>Dismiss Suggestion</h3>
            <button @click="closeDismissDialog" class="close-btn">×</button>
          </div>
          <div class="modal-body">
            <p>Are you sure you want to dismiss this suggestion?</p>
          </div>
          <div class="modal-footer">
            <button @click="closeDismissDialog" class="btn btn-secondary">
              Cancel
            </button>
            <button
              @click="dismissSuggestion"
              class="btn btn-danger"
              data-testid="autopilot-dismiss-confirm-btn"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const autopilotStore = useAutopilotStore()

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  }
})

const suggestions = ref([])
const loading = ref(false)
const executing = ref(false)

const executeModal = ref({
  visible: false,
  suggestion: null
})

const dismissDialog = ref({
  visible: false,
  suggestionId: null
})

const fetchSuggestions = async () => {
  loading.value = true
  const result = await autopilotStore.fetchSuggestionsForStrategy(props.strategyId)
  loading.value = false
  if (result.success) {
    suggestions.value = result.data?.data || []
  } else {
    console.error('Failed to fetch suggestions:', result.error)
    suggestions.value = []
  }
}

const refreshSuggestions = async () => {
  const result = await autopilotStore.refreshSuggestions(props.strategyId)
  if (result.success) {
    suggestions.value = result.data?.data || []
  } else {
    console.error('Failed to refresh suggestions:', result.error)
  }
}

const openExecuteModal = (suggestion) => {
  executeModal.value = {
    visible: true,
    suggestion
  }
}

const closeExecuteModal = () => {
  executeModal.value = {
    visible: false,
    suggestion: null
  }
}

const executeSuggestion = async () => {
  executing.value = true
  const result = await autopilotStore.executeSuggestion(
    props.strategyId,
    executeModal.value.suggestion.id
  )
  executing.value = false
  if (result.success) {
    closeExecuteModal()
    await fetchSuggestions()
  } else {
    console.error('Failed to execute suggestion:', result.error)
    alert('Failed to execute suggestion')
  }
}

const openDismissDialog = (suggestionId) => {
  dismissDialog.value = {
    visible: true,
    suggestionId
  }
}

const closeDismissDialog = () => {
  dismissDialog.value = {
    visible: false,
    suggestionId: null
  }
}

const dismissSuggestion = async () => {
  const result = await autopilotStore.dismissSuggestionScoped(
    props.strategyId,
    dismissDialog.value.suggestionId
  )
  if (result.success) {
    closeDismissDialog()
    await fetchSuggestions()
  } else {
    console.error('Failed to dismiss suggestion:', result.error)
  }
}

const formatActionType = (actionType) => {
  if (!actionType) return ''
  return actionType.replace(/_/g, ' ').toUpperCase()
}

onMounted(() => {
  fetchSuggestions()
})
</script>

<style scoped>
.suggestions-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.suggestions-count {
  font-size: 13px;
  color: #6b7280;
  background: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
}

.spinner {
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

.loading-state p {
  margin-top: 16px;
  color: #6b7280;
  font-size: 14px;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
}

.suggestion-card {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.2s;
}

.suggestion-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.suggestion-card.priority-critical {
  border-color: #fca5a5;
  background: #fef2f2;
}

.suggestion-card.priority-high {
  border-color: #fdba74;
  background: #fffbeb;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.card-header h4 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.priority-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.urgency-critical {
  background: #fecaca;
  color: #991b1b;
}

.urgency-high {
  background: #fed7aa;
  color: #9a3412;
}

.urgency-medium {
  background: #fde047;
  color: #854d0e;
}

.urgency-low {
  background: #e5e7eb;
  color: #374151;
}

.action-type {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 500;
}

.description {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
  margin: 0 0 16px 0;
}

.reasoning-section {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 6px;
  padding: 14px;
  margin-bottom: 16px;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #166534;
  font-weight: 600;
  font-size: 13px;
}

.reasoning-text {
  font-size: 13px;
  color: #166534;
  line-height: 1.5;
  margin: 0;
}

.impact-section {
  margin-bottom: 16px;
}

.impact-section h5 {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.impact-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.impact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.impact-item .label {
  font-size: 12px;
  color: #6b7280;
}

.impact-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.impact-item .value.profit {
  color: #16a34a;
}

.card-actions {
  display: flex;
  gap: 12px;
}

.btn {
  flex: 1;
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

.btn-danger {
  background: #dc2626;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 20px;
  color: #9ca3af;
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 4px 0;
  font-size: 15px;
}

.empty-state .hint {
  font-size: 13px;
  color: #d1d5db;
  max-width: 400px;
  text-align: center;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
  max-width: 500px;
  width: 100%;
}

.modal-content.small {
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  font-size: 18px;
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
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 24px;
}

.modal-body p {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
}

.confirm-info {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  background: #fef3c7;
  border: 1px solid #fde047;
  border-radius: 8px;
}

.confirm-info svg {
  color: #f59e0b;
  flex-shrink: 0;
  margin-top: 2px;
}

.confirm-info span {
  font-size: 13px;
  color: #92400e;
  line-height: 1.5;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}
</style>
