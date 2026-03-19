<script setup>
/**
 * DhanSettings — Tier 3 credential storage for Dhan.
 *
 * Loads saved credentials on mount, shows status if configured,
 * and allows save/edit/delete. Access token stored encrypted in DB.
 */
import { ref, onMounted } from 'vue'
import * as dhanCredentials from '@/services/dhan_credentials'

const emit = defineEmits(['credentials-updated'])

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const error = ref(null)
const success = ref(null)
const isEditing = ref(false)

const saved = ref(null) // { has_credentials, client_id, is_active, last_auth_at, last_error }

const form = ref({
  client_id: '',
  access_token: '',
})

const canSubmit = computed(() => form.value.client_id && form.value.access_token)

import { computed } from 'vue'

onMounted(async () => {
  await loadCredentials()
})

async function loadCredentials() {
  loading.value = true
  error.value = null
  try {
    saved.value = await dhanCredentials.getCredentials()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load credentials'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!canSubmit.value) return
  saving.value = true
  error.value = null
  success.value = null
  try {
    saved.value = await dhanCredentials.storeCredentials({
      client_id: form.value.client_id,
      access_token: form.value.access_token,
    })
    success.value = 'Credentials saved successfully'
    isEditing.value = false
    form.value = { client_id: '', access_token: '' }
    emit('credentials-updated')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to save credentials'
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!confirm('Remove saved Dhan credentials?')) return
  deleting.value = true
  error.value = null
  success.value = null
  try {
    await dhanCredentials.deleteCredentials()
    saved.value = { has_credentials: false, is_active: false }
    success.value = 'Credentials removed'
    emit('credentials-updated')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to remove credentials'
  } finally {
    deleting.value = false
  }
}

function startEdit() {
  form.value = { client_id: saved.value?.client_id || '', access_token: '' }
  isEditing.value = true
  error.value = null
  success.value = null
}

function cancelEdit() {
  isEditing.value = false
  form.value = { client_id: '', access_token: '' }
  error.value = null
  success.value = null
}
</script>

<template>
  <div class="dhan-settings" data-testid="settings-dhan-section">
    <!-- Loading -->
    <div v-if="loading" class="loading-row">
      <div class="mini-spinner"></div>
      <span>Loading...</span>
    </div>

    <!-- Saved credentials display -->
    <template v-else-if="saved?.has_credentials && !isEditing">
      <div class="status-row">
        <span :class="['status-dot', saved.is_active ? 'active' : 'inactive']"></span>
        <span class="status-text">{{ saved.is_active ? 'Active' : 'Inactive' }}</span>
        <span class="client-id-badge">{{ saved.client_id }}</span>
      </div>

      <p v-if="saved.last_auth_at" class="hint-text">
        Saved {{ new Date(saved.last_auth_at).toLocaleDateString('en-IN') }}
      </p>
      <p v-if="saved.last_error" class="error-msg" data-testid="settings-dhan-error">
        {{ saved.last_error }}
      </p>

      <div class="btn-row">
        <button @click="startEdit" class="btn btn-outline" data-testid="settings-dhan-edit-btn">
          Edit
        </button>
        <button
          @click="handleDelete"
          :disabled="deleting"
          class="btn btn-danger"
          data-testid="settings-dhan-delete-btn"
        >
          {{ deleting ? 'Removing...' : 'Remove' }}
        </button>
      </div>
    </template>

    <!-- Credential form (new or edit) -->
    <template v-else>
      <div v-if="!saved?.has_credentials" class="no-creds-notice">
        No credentials saved. Enter your Dhan Client ID and Access Token below.
      </div>

      <div class="form-group">
        <label class="form-label" for="dhan-client-id">Client ID</label>
        <input
          id="dhan-client-id"
          v-model="form.client_id"
          type="text"
          placeholder="Your Dhan Client ID"
          class="form-input"
          data-testid="settings-dhan-client-id"
        />
      </div>

      <div class="form-group">
        <label class="form-label" for="dhan-access-token">Access Token</label>
        <input
          id="dhan-access-token"
          v-model="form.access_token"
          type="password"
          placeholder="Your Dhan Access Token"
          class="form-input"
          data-testid="settings-dhan-access-token"
        />
        <p class="form-hint">Get your access token from the Dhan developer console. Long-lived until manually revoked.</p>
      </div>

      <p v-if="error" class="error-msg" data-testid="settings-dhan-error">{{ error }}</p>
      <p v-if="success" class="success-msg" data-testid="settings-dhan-success">{{ success }}</p>

      <div class="btn-row">
        <button
          @click="handleSave"
          :disabled="!canSubmit || saving"
          class="btn btn-primary"
          data-testid="settings-dhan-save-btn"
        >
          {{ saving ? 'Saving...' : 'Save Credentials' }}
        </button>
        <button
          v-if="isEditing"
          @click="cancelEdit"
          class="btn btn-outline"
          data-testid="settings-dhan-cancel-btn"
        >
          Cancel
        </button>
      </div>
    </template>

    <p v-if="success && !isEditing && saved?.has_credentials" class="success-msg">{{ success }}</p>
  </div>
</template>

<style scoped>
.dhan-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
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
.status-dot.inactive { background: #ef4444; }

.status-text {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.client-id-badge {
  font-size: 12px;
  color: #6b7280;
  background: #e5e7eb;
  padding: 2px 8px;
  border-radius: 12px;
  font-family: monospace;
}

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

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

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

.form-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.hint-text {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
}

.error-msg { font-size: 13px; color: #dc2626; margin: 0; }
.success-msg { font-size: 13px; color: #059669; margin: 0; }

.btn-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

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
