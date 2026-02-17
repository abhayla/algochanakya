<script setup>
/**
 * FyersSettings
 *
 * OAuth connection status for Fyers.
 * Connect button redirects to Fyers OAuth flow.
 */
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const error = ref(null)

const isConnected = ref(
  authStore.user?.broker_connections?.some(bc => bc.broker === 'fyers' && bc.is_active) || false
)

async function handleConnect() {
  error.value = null
  const result = await authStore.initiateFyersLogin()
  if (!result.success) {
    error.value = result.error
  }
}
</script>

<template>
  <div class="oauth-settings" data-testid="settings-fyers-section">
    <div class="connection-status">
      <span :class="['status-dot', isConnected ? 'active' : 'inactive']"></span>
      <span class="status-text">{{ isConnected ? 'Connected' : 'Not connected' }}</span>
    </div>

    <p v-if="error" class="error-msg" data-testid="settings-fyers-error">{{ error }}</p>

    <button
      @click="handleConnect"
      :disabled="authStore.fyersLoading"
      class="btn btn-primary"
      data-testid="settings-fyers-connect-btn"
    >
      {{ authStore.fyersLoading ? 'Connecting...' : (isConnected ? 'Reconnect' : 'Connect Fyers') }}
    </button>

    <p class="form-hint">Uses OAuth 2.0. Token expires daily at midnight IST.</p>
  </div>
</template>

<style scoped>
.oauth-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.status-dot.inactive { background: #9ca3af; }

.status-text {
  font-size: 13px;
  color: #374151;
}

.error-msg {
  font-size: 13px;
  color: #dc2626;
  margin: 0;
}

.form-hint {
  font-size: 12px;
  color: #6b7280;
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
