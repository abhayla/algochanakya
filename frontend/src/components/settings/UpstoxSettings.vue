<script setup>
/**
 * UpstoxSettings
 *
 * OAuth connection status for Upstox.
 * Connect button redirects to Upstox OAuth flow.
 */
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const error = ref(null)
const disconnecting = ref(false)

// Check if user has an active Upstox connection
const isConnected = ref(
  authStore.user?.broker_connections?.some(bc => bc.broker === 'upstox' && bc.is_active) || false
)

async function handleConnect() {
  error.value = null
  const result = await authStore.initiateUpstoxLogin()
  if (!result.success) {
    error.value = result.error
  }
}

async function handleDisconnect() {
  error.value = null
  disconnecting.value = true
  const result = await authStore.disconnectBroker('upstox')
  disconnecting.value = false
  if (result.success) {
    isConnected.value = false
  } else {
    error.value = result.error
  }
}
</script>

<template>
  <div class="oauth-settings" data-testid="settings-upstox-section">
    <div class="connection-status">
      <span :class="['status-dot', isConnected ? 'active' : 'inactive']"></span>
      <span class="status-text">{{ isConnected ? 'Connected' : 'Not connected' }}</span>
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

.btn-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-danger {
  background: white;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.btn-danger:hover:not(:disabled) { background: #fef2f2; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
