<script setup>
/**
 * UpstoxSettings
 *
 * OAuth connection management + Tier 3 API credential storage for Upstox.
 * Section 1: OAuth connect/disconnect (existing behavior preserved).
 * Section 2: Save user's own Upstox API key + secret for personal market data.
 */
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import * as upstoxCredentials from '@/services/upstox_credentials'

const emit = defineEmits(['credentials-updated'])

const authStore = useAuthStore()
const error = ref(null)
const disconnecting = ref(false)

const isConnected = ref(
  authStore.user?.broker_connections?.some(bc => bc.broker === 'upstox' && bc.is_active) || false
)

// Tier 3 credential state
const credsLoading = ref(false)
const credsSaving = ref(false)
const credsDeleting = ref(false)
const credsError = ref(null)
const credsSuccess = ref(null)
const isEditing = ref(false)
const saved = ref(null)

const form = ref({ api_key: '', api_secret: '' })
const canSubmit = computed(() => form.value.api_key && form.value.api_secret)

onMounted(async () => {
  await loadCredentials()
})

async function loadCredentials() {
  credsLoading.value = true
  try {
    saved.value = await upstoxCredentials.getCredentials()
  } catch {
    // Non-critical — OAuth section still works
  } finally {
    credsLoading.value = false
  }
}

async function handleConnect() {
  error.value = null
  const result = await authStore.initiateUpstoxLogin()
  if (!result.success) error.value = result.error
}

async function handleDisconnect() {
  error.value = null
  disconnecting.value = true
  const result = await authStore.disconnectBroker('upstox')
  disconnecting.value = false
  if (result.success) {
    isConnected.value = false
    emit('credentials-updated')
  } else {
    error.value = result.error
  }
}

async function handleCredsSave() {
  if (!canSubmit.value) return
  credsSaving.value = true
  credsError.value = null
  credsSuccess.value = null
  try {
    saved.value = await upstoxCredentials.storeCredentials({
      api_key: form.value.api_key,
      api_secret: form.value.api_secret,
    })
    credsSuccess.value = 'API credentials saved'
    isEditing.value = false
    form.value = { api_key: '', api_secret: '' }
    emit('credentials-updated')
  } catch (err) {
    credsError.value = err.response?.data?.detail || 'Failed to save credentials'
  } finally {
    credsSaving.value = false
  }
}

async function handleCredsDelete() {
  if (!confirm('Remove saved Upstox API credentials?')) return
  credsDeleting.value = true
  credsError.value = null
  try {
    await upstoxCredentials.deleteCredentials()
    saved.value = { has_credentials: false, is_active: false }
    credsSuccess.value = 'API credentials removed'
    emit('credentials-updated')
  } catch (err) {
    credsError.value = err.response?.data?.detail || 'Failed to remove credentials'
  } finally {
    credsDeleting.value = false
  }
}

function startEdit() {
  form.value = { api_key: saved.value?.api_key || '', api_secret: '' }
  isEditing.value = true
  credsError.value = null
  credsSuccess.value = null
}

function cancelEdit() {
  isEditing.value = false
  form.value = { api_key: '', api_secret: '' }
}
</script>

<template>
  <div class="upstox-settings" data-testid="settings-upstox-section">
    <!-- OAuth section -->
    <div class="oauth-section">
      <div class="connection-status">
        <span :class="['status-dot', isConnected ? 'active' : 'inactive']"></span>
        <span class="status-text">{{ isConnected ? 'Connected via OAuth' : 'Not connected' }}</span>
      </div>

      <p v-if="error" class="error-msg" data-testid="settings-upstox-error">{{ error }}</p>

      <div class="btn-row">
        <button
          @click="handleConnect"
          :disabled="authStore.upstoxLoading"
          class="btn btn-primary"
          data-testid="settings-upstox-connect-btn"
        >
          {{ authStore.upstoxLoading ? 'Connecting...' : (isConnected ? 'Reconnect' : 'Connect Upstox') }}
        </button>

        <button
          v-if="isConnected"
          @click="handleDisconnect"
          :disabled="disconnecting"
          class="btn btn-danger"
          data-testid="settings-upstox-disconnect-btn"
        >
          {{ disconnecting ? 'Disconnecting...' : 'Disconnect' }}
        </button>
      </div>

      <p class="form-hint">Uses OAuth 2.0. Token valid for ~1 year.</p>
    </div>

    <!-- Divider -->
    <div class="section-divider"></div>

    <!-- Tier 3: Personal API credentials -->
    <div class="api-creds-section">
      <p class="api-creds-label">Personal API Credentials (optional)</p>
      <p class="form-hint" style="margin-bottom: 12px;">
        Save your own Upstox app key + secret for personal market data access.
        Get them from the <a href="https://developer.upstox.com" target="_blank" rel="noopener" class="link">Upstox developer portal</a>.
      </p>

      <div v-if="credsLoading" class="loading-row">
        <div class="mini-spinner"></div>
        <span>Loading...</span>
      </div>

      <!-- Saved display -->
      <template v-else-if="saved?.has_credentials && !isEditing">
        <div class="status-row">
          <span :class="['status-dot', saved.is_active ? 'active' : 'inactive']"></span>
          <span class="status-text">{{ saved.is_active ? 'Saved' : 'Inactive' }}</span>
          <span class="api-key-badge">{{ saved.api_key }}</span>
        </div>

        <p v-if="credsError" class="error-msg" data-testid="settings-upstox-creds-error">{{ credsError }}</p>
        <p v-if="credsSuccess" class="success-msg">{{ credsSuccess }}</p>

        <div class="btn-row">
          <button @click="startEdit" class="btn btn-outline" data-testid="settings-upstox-creds-edit-btn">Edit</button>
          <button
            @click="handleCredsDelete"
            :disabled="credsDeleting"
            class="btn btn-danger"
            data-testid="settings-upstox-creds-delete-btn"
          >
            {{ credsDeleting ? 'Removing...' : 'Remove' }}
          </button>
        </div>
      </template>

      <!-- Form -->
      <template v-else>
        <div v-if="!saved?.has_credentials" class="no-creds-notice">
          No API credentials saved.
        </div>

        <div class="form-group">
          <label class="form-label" for="upstox-api-key">API Key</label>
          <input
            id="upstox-api-key"
            v-model="form.api_key"
            type="text"
            placeholder="Upstox API Key"
            class="form-input"
            data-testid="settings-upstox-api-key"
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="upstox-api-secret">API Secret</label>
          <input
            id="upstox-api-secret"
            v-model="form.api_secret"
            type="password"
            placeholder="Upstox API Secret"
            class="form-input"
            data-testid="settings-upstox-api-secret"
          />
        </div>

        <p v-if="credsError" class="error-msg" data-testid="settings-upstox-creds-error">{{ credsError }}</p>
        <p v-if="credsSuccess" class="success-msg">{{ credsSuccess }}</p>

        <div class="btn-row">
          <button
            @click="handleCredsSave"
            :disabled="!canSubmit || credsSaving"
            class="btn btn-primary"
            data-testid="settings-upstox-creds-save-btn"
          >
            {{ credsSaving ? 'Saving...' : 'Save API Credentials' }}
          </button>
          <button
            v-if="isEditing"
            @click="cancelEdit"
            class="btn btn-outline"
            data-testid="settings-upstox-creds-cancel-btn"
          >
            Cancel
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.upstox-settings {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.oauth-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-divider {
  border-top: 1px solid #e5e7eb;
  margin: 20px 0;
}

.api-creds-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.api-creds-label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.connection-status, .status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.active { background: #22c55e; }
.status-dot.inactive { background: #9ca3af; }

.status-text { font-size: 13px; color: #374151; }

.api-key-badge {
  font-size: 12px;
  color: #6b7280;
  background: #e5e7eb;
  padding: 2px 8px;
  border-radius: 12px;
  font-family: monospace;
}

.loading-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.mini-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.no-creds-notice {
  font-size: 13px;
  color: #6b7280;
  padding: 10px 14px;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px dashed #d1d5db;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label { font-size: 14px; font-weight: 500; color: #374151; }

.form-input {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  max-width: 320px;
}
.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-hint { font-size: 12px; color: #6b7280; margin: 0; }
.error-msg { font-size: 13px; color: #dc2626; margin: 0; }
.success-msg { font-size: 13px; color: #059669; margin: 0; }
.link { color: #3b82f6; text-decoration: none; }
.link:hover { text-decoration: underline; }

.btn-row { display: flex; gap: 8px; flex-wrap: wrap; }

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  width: fit-content;
}

.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #9ca3af; cursor: not-allowed; }

.btn-outline { background: white; border: 1px solid #d1d5db; color: #374151; }
.btn-outline:hover { background: #f9fafb; }

.btn-danger { background: white; color: #dc2626; border: 1px solid #fca5a5; }
.btn-danger:hover:not(:disabled) { background: #fef2f2; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
