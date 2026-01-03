<script setup>
/**
 * SmartAPI Settings Component
 *
 * Manages AngelOne SmartAPI credentials for market data
 */
import { ref, onMounted, computed } from 'vue'
import * as smartapi from '@/services/smartapi'

const emit = defineEmits(['credentials-updated'])

// State
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const deleting = ref(false)
const error = ref(null)
const success = ref(null)
const testResult = ref(null)

// Credentials status
const credentialsStatus = ref({
  has_credentials: false,
  client_id: null,
  is_active: false,
  last_auth_at: null,
  last_error: null,
  token_expiry: null
})

// Form data
const form = ref({
  client_id: '',
  pin: '',
  totp_secret: ''
})

const showForm = ref(false)

// Computed
const hasCredentials = computed(() => credentialsStatus.value.has_credentials)
const isActive = computed(() => credentialsStatus.value.is_active)

// Methods
async function fetchCredentials() {
  loading.value = true
  error.value = null
  try {
    credentialsStatus.value = await smartapi.getCredentials()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load credentials'
  } finally {
    loading.value = false
  }
}

async function handleTestConnection() {
  if (!form.value.client_id || !form.value.pin || !form.value.totp_secret) {
    error.value = 'Please fill in all fields'
    return
  }

  testing.value = true
  error.value = null
  testResult.value = null
  success.value = null

  try {
    const result = await smartapi.testConnection({
      client_id: form.value.client_id,
      pin: form.value.pin,
      totp_secret: form.value.totp_secret
    })
    testResult.value = result
    if (result.success) {
      success.value = `Connection successful! Welcome, ${result.client_name || form.value.client_id}`
    } else {
      error.value = result.message
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Connection test failed'
  } finally {
    testing.value = false
  }
}

async function handleSaveCredentials() {
  if (!form.value.client_id || !form.value.pin || !form.value.totp_secret) {
    error.value = 'Please fill in all fields'
    return
  }

  saving.value = true
  error.value = null
  success.value = null

  try {
    credentialsStatus.value = await smartapi.storeCredentials({
      client_id: form.value.client_id,
      pin: form.value.pin,
      totp_secret: form.value.totp_secret
    })
    success.value = 'Credentials saved successfully!'
    showForm.value = false
    form.value = { client_id: '', pin: '', totp_secret: '' }
    testResult.value = null
    emit('credentials-updated')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to save credentials'
  } finally {
    saving.value = false
  }
}

async function handleDeleteCredentials() {
  if (!confirm('Are you sure you want to delete your SmartAPI credentials?')) {
    return
  }

  deleting.value = true
  error.value = null
  success.value = null

  try {
    await smartapi.deleteCredentials()
    credentialsStatus.value = {
      has_credentials: false,
      client_id: null,
      is_active: false,
      last_auth_at: null,
      last_error: null,
      token_expiry: null
    }
    success.value = 'Credentials deleted successfully'
    emit('credentials-updated')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to delete credentials'
  } finally {
    deleting.value = false
  }
}

async function handleAuthenticate() {
  saving.value = true
  error.value = null
  success.value = null

  try {
    const result = await smartapi.authenticate()
    if (result.success) {
      success.value = 'Authentication successful!'
      await fetchCredentials()
      emit('credentials-updated')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Authentication failed'
  } finally {
    saving.value = false
  }
}

function handleShowForm() {
  showForm.value = true
  form.value.client_id = credentialsStatus.value.client_id || ''
  error.value = null
  success.value = null
  testResult.value = null
}

function handleCancelForm() {
  showForm.value = false
  form.value = { client_id: '', pin: '', totp_secret: '' }
  error.value = null
  testResult.value = null
}

function formatDate(dateStr) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

onMounted(() => {
  fetchCredentials()
})
</script>

<template>
  <div class="smartapi-settings" data-testid="smartapi-settings">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner-small"></div>
      <span>Loading...</span>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Alert Messages -->
      <div v-if="error" class="alert alert-error" data-testid="smartapi-error">
        {{ error }}
      </div>
      <div v-if="success" class="alert alert-success" data-testid="smartapi-success">
        {{ success }}
      </div>

      <!-- Current Status (when credentials exist and not showing form) -->
      <div v-if="hasCredentials && !showForm" class="credentials-status">
        <div class="status-header">
          <div class="status-info">
            <div class="status-badge" :class="isActive ? 'active' : 'inactive'">
              {{ isActive ? 'Active' : 'Inactive' }}
            </div>
            <span class="client-id">Client: {{ credentialsStatus.client_id }}</span>
          </div>
          <div class="status-actions">
            <button
              @click="handleAuthenticate"
              :disabled="saving"
              class="btn btn-outline btn-sm"
              data-testid="smartapi-authenticate"
            >
              {{ saving ? 'Authenticating...' : 'Re-authenticate' }}
            </button>
            <button
              @click="handleShowForm"
              class="btn btn-outline btn-sm"
              data-testid="smartapi-edit"
            >
              Edit
            </button>
            <button
              @click="handleDeleteCredentials"
              :disabled="deleting"
              class="btn btn-danger btn-sm"
              data-testid="smartapi-delete"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>

        <div class="status-details">
          <div class="detail-row">
            <span class="detail-label">Last Authenticated:</span>
            <span class="detail-value">{{ formatDate(credentialsStatus.last_auth_at) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Token Expiry:</span>
            <span class="detail-value">{{ formatDate(credentialsStatus.token_expiry) }}</span>
          </div>
          <div v-if="credentialsStatus.last_error" class="detail-row error">
            <span class="detail-label">Last Error:</span>
            <span class="detail-value">{{ credentialsStatus.last_error }}</span>
          </div>
        </div>
      </div>

      <!-- Add/Edit Form -->
      <div v-if="!hasCredentials || showForm" class="credentials-form">
        <div class="form-intro" v-if="!hasCredentials">
          <p>Connect your AngelOne account to use SmartAPI for live market data.</p>
          <p class="form-note">Your credentials are encrypted and stored securely.</p>
        </div>

        <div class="form-group">
          <label for="client-id">Client ID</label>
          <input
            id="client-id"
            v-model="form.client_id"
            type="text"
            placeholder="Your AngelOne Client ID"
            data-testid="smartapi-client-id"
          />
          <p class="field-help">Your AngelOne trading account ID</p>
        </div>

        <div class="form-group">
          <label for="pin">PIN</label>
          <input
            id="pin"
            v-model="form.pin"
            type="password"
            placeholder="Your trading PIN"
            data-testid="smartapi-pin"
          />
          <p class="field-help">Your 4-digit trading PIN</p>
        </div>

        <div class="form-group">
          <label for="totp-secret">TOTP Secret</label>
          <input
            id="totp-secret"
            v-model="form.totp_secret"
            type="password"
            placeholder="Your TOTP secret key"
            data-testid="smartapi-totp-secret"
          />
          <p class="field-help">
            The secret key from your authenticator app setup (not the 6-digit code)
          </p>
        </div>

        <!-- Test Result -->
        <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
          <span v-if="testResult.success">✓ {{ testResult.message }}</span>
          <span v-else>✗ {{ testResult.message }}</span>
        </div>

        <div class="form-actions">
          <button
            v-if="showForm"
            @click="handleCancelForm"
            class="btn btn-outline"
            data-testid="smartapi-cancel"
          >
            Cancel
          </button>
          <button
            @click="handleTestConnection"
            :disabled="testing || !form.client_id || !form.pin || !form.totp_secret"
            class="btn btn-outline"
            data-testid="smartapi-test"
          >
            {{ testing ? 'Testing...' : 'Test Connection' }}
          </button>
          <button
            @click="handleSaveCredentials"
            :disabled="saving || !form.client_id || !form.pin || !form.totp_secret"
            class="btn btn-primary"
            data-testid="smartapi-save"
          >
            {{ saving ? 'Saving...' : 'Save Credentials' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.smartapi-settings {
  padding: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.loading-spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.alert {
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 16px;
}

.alert-error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.alert-success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.credentials-status {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: #dcfce7;
  color: #16a34a;
}

.status-badge.inactive {
  background: #fef3c7;
  color: #d97706;
}

.client-id {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.status-actions {
  display: flex;
  gap: 8px;
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  font-size: 13px;
}

.detail-label {
  color: #6b7280;
  width: 140px;
}

.detail-value {
  color: #374151;
}

.detail-row.error .detail-value {
  color: #dc2626;
}

.credentials-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-intro {
  margin-bottom: 8px;
}

.form-intro p {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #374151;
}

.form-note {
  font-size: 13px !important;
  color: #6b7280 !important;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-group input {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.field-help {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.test-result {
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
}

.test-result.success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.test-result.error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.btn-outline {
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.btn-outline:hover:not(:disabled) {
  background: #f9fafb;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-danger {
  background: #dc2626;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
