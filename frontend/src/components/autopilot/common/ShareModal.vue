<script setup>
/**
 * AutoPilot Share Modal Component
 *
 * Allows users to share strategies with a public link.
 * Backend API: POST /api/v1/autopilot/strategies/{id}/share
 */
import { ref, computed, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  strategyId: {
    type: Number,
    required: true
  },
  strategyName: {
    type: String,
    default: ''
  },
  isShared: {
    type: Boolean,
    default: false
  },
  existingToken: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['close', 'shared', 'unshared'])

const store = useAutopilotStore()

// Form state
const isPublic = ref(false)
const description = ref('')
const expiration = ref(7) // Days
const shareLink = ref('')
const showCopiedToast = ref(false)
const loading = ref(false)
const error = ref(null)

// Reset state when modal opens
watch(() => props.show, (newVal) => {
  if (newVal) {
    error.value = null
    showCopiedToast.value = false
    if (props.existingToken) {
      shareLink.value = buildShareLink(props.existingToken)
    } else {
      shareLink.value = ''
      isPublic.value = false
      description.value = ''
      expiration.value = 7
    }
  }
})

// Build the share link URL
const buildShareLink = (token) => {
  const baseUrl = window.location.origin
  return `${baseUrl}/autopilot/shared/${token}`
}

// Generate share link
const generateShareLink = async () => {
  loading.value = true
  error.value = null

  try {
    const result = await store.shareStrategy(props.strategyId, isPublic.value ? 'public' : 'link')
    if (result && result.share_token) {
      shareLink.value = buildShareLink(result.share_token)
      emit('shared', result)
    }
  } catch (e) {
    error.value = e.message || 'Failed to generate share link'
  } finally {
    loading.value = false
  }
}

// Copy link to clipboard
const copyShareLink = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.value)
    showCopiedToast.value = true
    setTimeout(() => {
      showCopiedToast.value = false
    }, 2000)
  } catch (e) {
    error.value = 'Failed to copy link'
  }
}

// Cancel/close modal
const handleCancel = () => {
  emit('close')
}

// Unshare the strategy
const handleUnshare = async () => {
  loading.value = true
  error.value = null

  try {
    await store.unshareStrategy(props.strategyId)
    shareLink.value = ''
    emit('unshared')
    emit('close')
  } catch (e) {
    error.value = e.message || 'Failed to unshare'
  } finally {
    loading.value = false
  }
}

// Confirm unshare action
const showUnshareConfirm = ref(false)

const confirmUnshare = () => {
  showUnshareConfirm.value = true
}

const cancelUnshare = () => {
  showUnshareConfirm.value = false
}

const executeUnshare = async () => {
  await handleUnshare()
  showUnshareConfirm.value = false
}
</script>

<template>
  <div
    v-if="show"
    class="modal-overlay"
    data-testid="autopilot-share-modal"
    @click.self="handleCancel"
  >
    <div class="modal-content">
      <!-- Header -->
      <div class="modal-header">
        <h3 class="modal-title">Share Strategy</h3>
        <button
          @click="handleCancel"
          class="close-btn"
          data-testid="autopilot-share-close-btn"
        >
          &times;
        </button>
      </div>

      <!-- Body -->
      <div class="modal-body">
        <p class="strategy-name-display">{{ strategyName }}</p>

        <!-- Error message -->
        <div v-if="error" class="error-message" data-testid="autopilot-share-error">
          {{ error }}
        </div>

        <!-- Already shared - show existing link -->
        <template v-if="shareLink">
          <div class="share-link-section">
            <label class="form-label">Share Link</label>
            <div class="link-input-group">
              <input
                type="text"
                :value="shareLink"
                readonly
                class="share-link-input"
                data-testid="autopilot-share-link"
              />
              <button
                @click="copyShareLink"
                class="copy-btn"
                data-testid="autopilot-share-copy-btn"
              >
                Copy
              </button>
            </div>
            <p
              v-if="showCopiedToast"
              class="copied-toast"
              data-testid="autopilot-share-copied-toast"
            >
              Link copied to clipboard!
            </p>
          </div>

          <!-- Unshare option -->
          <div class="unshare-section">
            <button
              @click="confirmUnshare"
              class="unshare-btn"
              data-testid="autopilot-unshare-btn"
              :disabled="loading"
            >
              Revoke Share Link
            </button>
          </div>

          <!-- Unshare confirmation -->
          <div v-if="showUnshareConfirm" class="unshare-confirm">
            <p>Are you sure you want to revoke this share link? Anyone with the link will no longer be able to access the strategy.</p>
            <div class="confirm-actions">
              <button @click="cancelUnshare" class="btn-secondary">
                Cancel
              </button>
              <button
                @click="executeUnshare"
                class="btn-danger"
                data-testid="autopilot-unshare-confirm-btn"
                :disabled="loading"
              >
                {{ loading ? 'Revoking...' : 'Revoke' }}
              </button>
            </div>
          </div>
        </template>

        <!-- Not shared - show share options -->
        <template v-else>
          <!-- Public toggle -->
          <div class="form-field">
            <label class="toggle-label">
              <input
                type="checkbox"
                v-model="isPublic"
                class="toggle-checkbox"
                data-testid="autopilot-share-public-toggle"
              />
              <span class="toggle-text">Make publicly discoverable</span>
            </label>
            <p class="field-hint">
              Public strategies can be found by other users. Private links are only accessible to those with the link.
            </p>
          </div>

          <!-- Description (optional) -->
          <div class="form-field">
            <label class="form-label">Description (optional)</label>
            <textarea
              v-model="description"
              class="description-input"
              rows="2"
              placeholder="Add a note about this strategy..."
              data-testid="autopilot-share-description-input"
            ></textarea>
          </div>

          <!-- Expiration -->
          <div class="form-field">
            <label class="form-label">Link Expiration</label>
            <select
              v-model="expiration"
              class="expiration-select"
              data-testid="autopilot-share-expiration"
            >
              <option :value="1">1 day</option>
              <option :value="7">7 days</option>
              <option :value="30">30 days</option>
              <option :value="0">Never</option>
            </select>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button
          @click="handleCancel"
          class="btn-secondary"
          data-testid="autopilot-share-cancel-btn"
        >
          {{ shareLink ? 'Close' : 'Cancel' }}
        </button>
        <button
          v-if="!shareLink"
          @click="generateShareLink"
          class="btn-primary"
          data-testid="autopilot-share-generate-btn"
          :disabled="loading"
        >
          {{ loading ? 'Generating...' : 'Generate Link' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 480px;
  margin: 16px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--kite-border);
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--kite-text-secondary);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: var(--kite-text-primary);
}

.modal-body {
  padding: 20px;
}

.strategy-name-display {
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--kite-border-light);
}

.error-message {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 0.875rem;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 6px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.toggle-text {
  font-size: 0.875rem;
  color: var(--kite-text-primary);
}

.field-hint {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-top: 4px;
  margin-left: 26px;
}

.description-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
  resize: vertical;
}

.description-input:focus {
  outline: none;
  border-color: var(--kite-blue);
}

.expiration-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
}

.share-link-section {
  margin-bottom: 16px;
}

.link-input-group {
  display: flex;
  gap: 8px;
}

.share-link-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
  background: var(--kite-table-hover);
  color: var(--kite-text-primary);
}

.copy-btn {
  padding: 10px 16px;
  background: var(--kite-blue);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.copy-btn:hover {
  background: var(--kite-blue-dark, #1565c0);
}

.copied-toast {
  font-size: 0.75rem;
  color: var(--kite-green);
  margin-top: 8px;
}

.unshare-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.unshare-btn {
  background: none;
  border: none;
  color: var(--kite-red);
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0;
}

.unshare-btn:hover {
  text-decoration: underline;
}

.unshare-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.unshare-confirm {
  margin-top: 12px;
  padding: 12px;
  background: var(--kite-red-light, #ffebee);
  border-radius: 4px;
}

.unshare-confirm p {
  font-size: 0.875rem;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.confirm-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--kite-border);
}

.btn-primary {
  padding: 10px 20px;
  background: var(--kite-blue);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: var(--kite-blue-dark, #1565c0);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 10px 20px;
  background: white;
  color: var(--kite-text-primary);
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--kite-table-hover);
}

.btn-danger {
  padding: 10px 20px;
  background: var(--kite-red);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-danger:hover:not(:disabled) {
  background: var(--kite-red-dark, #c62828);
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
