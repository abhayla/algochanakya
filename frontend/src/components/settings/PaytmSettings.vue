<script setup>
/**
 * PaytmSettings
 *
 * OAuth connection status for Paytm Money.
 * Also provides a field for the Public Access Token (separate WebSocket token
 * that is NOT returned by OAuth — must be obtained from the Paytm developer console).
 */
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { initiateSettingsConnect } from '@/services/settings_credentials'

const emit = defineEmits(['credentials-updated'])

const authStore = useAuthStore()
const error = ref(null)
const connecting = ref(false)
const disconnecting = ref(false)
const publicTokenSaving = ref(false)
const publicTokenSaved = ref(false)
const publicToken = ref('')

const isConnected = ref(
  authStore.user?.broker_connections?.some(bc => bc.broker === 'paytm' && bc.is_active) || false
)

async function handleConnect() {
  error.value = null
  connecting.value = true
  const result = await initiateSettingsConnect('paytm')
  connecting.value = false
  if (!result.success) {
    error.value = result.error
  }
}

async function handleDisconnect() {
  error.value = null
  disconnecting.value = true
  const result = await authStore.disconnectBroker('paytm')
  disconnecting.value = false
  if (result.success) {
    isConnected.value = false
    emit('credentials-updated')
  } else {
    error.value = result.error
  }
}

async function savePublicToken() {
  if (!publicToken.value.trim()) return
  error.value = null
  publicTokenSaving.value = true
  publicTokenSaved.value = false
  const result = await authStore.savePaytmPublicToken(publicToken.value.trim())
  publicTokenSaving.value = false
  if (result.success) {
    publicTokenSaved.value = true
    emit('credentials-updated')
    setTimeout(() => { publicTokenSaved.value = false }, 3000)
  } else {
    error.value = result.error
  }
}
</script>

<template>
  <div class="oauth-settings" data-testid="settings-paytm-section">
    <div class="connection-status">
      <span :class="['status-dot', isConnected ? 'active' : 'inactive']"></span>
      <span class="status-text">{{ isConnected ? 'Connected' : 'Not connected' }}</span>
    </div>

    <p v-if="error" class="error-msg" data-testid="settings-paytm-error">{{ error }}</p>

    <div class="btn-row">
      <button
        @click="handleConnect"
        :disabled="connecting"
        class="btn btn-primary"
        data-testid="settings-paytm-connect-btn"
      >
        {{ connecting ? 'Connecting...' : (isConnected ? 'Reconnect' : 'Connect Paytm Money') }}
      </button>

      <button
        v-if="isConnected"
        @click="handleDisconnect"
        :disabled="disconnecting"
        class="btn btn-danger"
        data-testid="settings-paytm-disconnect-btn"
      >
        {{ disconnecting ? 'Disconnecting...' : 'Disconnect' }}
      </button>
    </div>

    <p class="form-hint">Uses OAuth 2.0. Returns 3 tokens for different API scopes.</p>

    <!-- Public Access Token (WebSocket) -->
    <div class="token-section">
      <label class="token-label" for="paytm-public-token">
        Public Access Token <span class="token-badge">WebSocket</span>
      </label>
      <p class="form-hint">
        Required for live market data (WebSocket ticks). This is a <strong>separate token</strong>
        from the OAuth access token — get it from your
        <a href="https://developer.paytmmoney.com" target="_blank" rel="noopener" class="link">Paytm developer console</a>.
      </p>
      <div class="token-input-row">
        <input
          id="paytm-public-token"
          v-model="publicToken"
          type="password"
          placeholder="Paste your public_access_token here"
          class="token-input"
          data-testid="settings-paytm-public-token-input"
        />
        <button
          @click="savePublicToken"
          :disabled="publicTokenSaving || !publicToken.trim()"
          class="btn btn-primary"
          data-testid="settings-paytm-public-token-save"
        >
          {{ publicTokenSaving ? 'Saving...' : publicTokenSaved ? 'Saved ✓' : 'Save' }}
        </button>
      </div>
    </div>
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

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-primary:disabled { background: #9ca3af; cursor: not-allowed; }

.btn-danger {
  background: white;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.btn-danger:hover:not(:disabled) { background: #fef2f2; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.token-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.token-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 6px;
}

.token-badge {
  font-size: 10px;
  font-weight: 600;
  background: #ede9fe;
  color: #7c3aed;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.3px;
}

.token-input-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.token-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  font-family: monospace;
  outline: none;
}

.token-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.link {
  color: #3b82f6;
  text-decoration: underline;
}
</style>
