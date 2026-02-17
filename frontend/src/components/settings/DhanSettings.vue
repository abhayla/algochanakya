<script setup>
/**
 * DhanSettings
 *
 * Credential entry form for Dhan (static token auth).
 * User provides client_id + access_token from Dhan developer console.
 */
import { ref, computed } from 'vue'
import api from '@/services/api'

const loading = ref(false)
const error = ref(null)
const success = ref(null)
const connectionStatus = ref(null)

const form = ref({
  client_id: '',
  access_token: '',
})

const canSubmit = computed(() => form.value.client_id && form.value.access_token)

async function testConnection() {
  if (!canSubmit.value) {
    error.value = 'Please fill in both fields'
    return
  }

  loading.value = true
  error.value = null
  success.value = null

  try {
    const resp = await api.post('/api/auth/dhan/login', {
      client_id: form.value.client_id,
      access_token: form.value.access_token,
    })
    if (resp.data.success) {
      success.value = 'Dhan connection successful!'
      connectionStatus.value = 'active'
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Connection test failed'
    connectionStatus.value = 'failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="dhan-settings" data-testid="settings-dhan-section">
    <div class="connection-status" v-if="connectionStatus">
      <span :class="['status-dot', connectionStatus]"></span>
      <span class="status-text">{{ connectionStatus === 'active' ? 'Connected' : 'Not connected' }}</span>
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
      <p class="form-hint">Get your access token from the Dhan developer console</p>
    </div>

    <p v-if="error" class="error-msg" data-testid="settings-dhan-error">{{ error }}</p>
    <p v-if="success" class="success-msg" data-testid="settings-dhan-success">{{ success }}</p>

    <button
      @click="testConnection"
      :disabled="!canSubmit || loading"
      class="btn btn-primary"
      data-testid="settings-dhan-test-btn"
    >
      {{ loading ? 'Testing...' : 'Test Connection' }}
    </button>
  </div>
</template>

<style scoped>
.dhan-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.connection-status {
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
}

.status-dot.active { background: #22c55e; }
.status-dot.failed { background: #ef4444; }

.status-text {
  font-size: 13px;
  color: #374151;
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

.error-msg {
  font-size: 13px;
  color: #dc2626;
  margin: 0;
}

.success-msg {
  font-size: 13px;
  color: #059669;
  margin: 0;
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

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
</style>
