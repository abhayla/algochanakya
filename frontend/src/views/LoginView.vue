<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const error = ref('')
const showSafetyInfo = ref(false)
const selectedBroker = ref('zerodha')

const angelClientId = ref('')
const angelPin = ref('')
const angelTotp = ref('')
const dhanClientId = ref('')
const dhanAccessToken = ref('')

const brokers = [
  { id: 'zerodha', name: 'Zerodha', type: 'oauth', color: '#e74c3c' },
  { id: 'angelone', name: 'Angel One', type: 'credentials', color: '#2196f3' },
  { id: 'upstox', name: 'Upstox', type: 'oauth', color: '#6b21a8' },
  { id: 'fyers', name: 'Fyers', type: 'oauth', color: '#0ea5e9' },
  { id: 'dhan', name: 'Dhan', type: 'inline', color: '#059669' },
  { id: 'paytm', name: 'Paytm Money', type: 'oauth', color: '#1e40af' },
]

const currentBroker = computed(() => brokers.find(b => b.id === selectedBroker.value))

const isLoading = computed(() => {
  const map = {
    zerodha: authStore.zerodhaLoading,
    angelone: authStore.angelOneLoading,
    upstox: authStore.upstoxLoading,
    fyers: authStore.fyersLoading,
    dhan: authStore.dhanLoading,
    paytm: authStore.paytmLoading,
  }
  return map[selectedBroker.value] || false
})

const handleLogin = async () => {
  error.value = ''
  let result

  switch (selectedBroker.value) {
    case 'zerodha':
      result = await authStore.initiateZerodhaLogin()
      break
    case 'angelone':
      if (!angelClientId.value || !angelPin.value || !angelTotp.value) {
        error.value = 'Please enter Client ID, PIN, and TOTP code'
        return
      }
      result = await authStore.initiateAngelOneLogin(
        angelClientId.value,
        angelPin.value,
        angelTotp.value
      )
      break
    case 'upstox':
      result = await authStore.initiateUpstoxLogin()
      break
    case 'fyers':
      result = await authStore.initiateFyersLogin()
      break
    case 'dhan':
      if (!dhanClientId.value || !dhanAccessToken.value) {
        error.value = 'Please enter both Client ID and Access Token'
        return
      }
      result = await authStore.initiateDhanLogin(dhanClientId.value, dhanAccessToken.value)
      break
    case 'paytm':
      result = await authStore.initiatePaytmLogin()
      break
  }

  if (result && !result.success) {
    error.value = result.error
  }
}

const scrollToLogin = () => {
  document.querySelector('.login-card')?.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  })
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 text-gray-900 w-full max-w-full overflow-x-hidden" data-testid="login-page">
    <!-- Header Navigation (identical to KiteHeader) -->
    <header class="kite-header">
      <!-- Left: Logo -->
      <div class="header-left">
        <router-link to="/" class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span class="logo-text">AlgoChanakya</span>
        </router-link>
      </div>

      <!-- Right: Login Button only (no nav links on login page) -->
      <div class="header-right">
        <button @click="scrollToLogin" class="login-btn" data-testid="login-header-scroll-btn">Login</button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-container">
      <div class="login-grid">

        <!-- Left Side - Branding -->
        <div class="space-y-8">
          <div>
            <p class="text-gray-500 text-sm uppercase tracking-wider mb-2">Welcome to</p>
            <div class="flex items-center space-x-3 mb-4">
              <div class="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center">
                <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h1 class="text-4xl font-bold text-gray-900">AlgoChanakya</h1>
            </div>
            <p class="text-xl text-gray-600 leading-relaxed">
              Your intelligent options trading companion. Build strategies, analyze markets, and trade smarter with real-time data and advanced analytics.
            </p>
          </div>

          <!-- Login help 1: Which broker -->
          <div class="flex items-start space-x-4">
            <div class="w-14 h-14 feature-icon-green rounded-2xl flex items-center justify-center flex-shrink-0">
              <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Which broker should I select?</h3>
              <p class="text-gray-500">
                Choose your trading broker from the dropdown. Zerodha and Upstox use OAuth (no password needed). AngelOne and Dhan use your Client ID and PIN.
              </p>
            </div>
          </div>

          <!-- Login help 2: Security -->
          <div class="flex items-start space-x-4">
            <div class="w-14 h-14 feature-icon-blue rounded-2xl flex items-center justify-center flex-shrink-0">
              <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Is it safe to connect?</h3>
              <p class="text-gray-500">
                OAuth brokers redirect to your broker's own site — we never see your password. Your login credentials are never stored on our servers.
              </p>
            </div>
          </div>

          <!-- Login help 3: Troubleshooting -->
          <div class="flex items-start space-x-4">
            <div class="w-14 h-14 feature-icon-purple rounded-2xl flex items-center justify-center flex-shrink-0">
              <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Having trouble logging in?</h3>
              <p class="text-gray-500">
                Zerodha tokens expire daily at ~6 AM IST — reconnect each morning. For AngelOne, use your 6-digit TOTP from your authenticator app.
              </p>
            </div>
          </div>
        </div>

        <!-- Right Side - Login Card -->
        <div class="login-card-wrapper">
          <div class="login-card">
            <h2 class="text-2xl font-bold text-center text-gray-900 mb-8">Login with your broker</h2>

            <!-- Error Message -->
            <div
              v-if="error"
              class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6"
              data-testid="login-error-message"
            >
              {{ error }}
            </div>

            <!-- Broker Dropdown -->
            <label class="block text-sm font-medium text-gray-700 mb-2" for="broker-select">Select your broker</label>
            <div class="broker-select-wrapper mb-6">
              <div
                class="broker-color-indicator"
                :style="{ backgroundColor: currentBroker?.color }"
              ></div>
              <select
                id="broker-select"
                v-model="selectedBroker"
                class="broker-select"
                data-testid="login-broker-select"
              >
                <option
                  v-for="broker in brokers"
                  :key="broker.id"
                  :value="broker.id"
                >
                  {{ broker.name }}
                </option>
              </select>
              <svg class="broker-select-arrow" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>

            <!-- AngelOne Inline Fields -->
            <div v-if="selectedBroker === 'angelone'" class="space-y-3 mb-6" data-testid="login-angelone-fields">
              <input
                v-model="angelClientId"
                type="text"
                placeholder="Client ID (e.g. A12345)"
                class="login-input"
                data-testid="login-angelone-client-id"
              />
              <input
                v-model="angelPin"
                type="password"
                placeholder="PIN"
                class="login-input"
                data-testid="login-angelone-pin"
              />
              <input
                v-model="angelTotp"
                type="text"
                inputmode="numeric"
                maxlength="6"
                placeholder="6-digit TOTP from authenticator"
                class="login-input"
                data-testid="login-angelone-totp"
              />
              <p class="text-xs text-gray-500">
                Enter the 6-digit code from your authenticator app (Google Authenticator, Authy, etc.)
              </p>
            </div>

            <!-- Dhan Inline Fields -->
            <div v-if="selectedBroker === 'dhan'" class="space-y-3 mb-6" data-testid="login-dhan-fields">
              <input
                v-model="dhanClientId"
                type="text"
                placeholder="Client ID"
                class="login-input"
                data-testid="login-dhan-client-id"
              />
              <input
                v-model="dhanAccessToken"
                type="password"
                placeholder="Access Token"
                class="login-input"
                data-testid="login-dhan-access-token"
              />
            </div>

            <!-- Login Button -->
            <button
              @click="handleLogin"
              :disabled="isLoading"
              class="login-submit-btn"
              data-testid="login-submit-button"
            >
              <span v-if="!isLoading">
                {{ selectedBroker === 'angelone' || selectedBroker === 'dhan' ? 'Login' : `Login with ${currentBroker?.name}` }}
              </span>
              <span v-else class="flex items-center justify-center">
                <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" width="20" height="20" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ selectedBroker === 'angelone' ? 'Connecting... (may take 20-30s)' : 'Connecting...' }}
              </span>
            </button>

            <!-- Broker-specific hints -->
            <p v-if="selectedBroker === 'angelone'" class="text-xs text-gray-500 mt-3 text-center">
              Your credentials are used once to authenticate and are not stored.
            </p>
            <p v-if="selectedBroker === 'dhan'" class="text-xs text-gray-500 mt-3 text-center">
              Your credentials are used once to authenticate and are not stored.
            </p>

            <!-- Safety Info Link -->
            <div class="text-center mt-6">
              <button
                @click="showSafetyInfo = !showSafetyInfo"
                class="safety-faq-btn"
                data-testid="login-safety-toggle"
              >
                <svg class="w-4 h-4 flex-shrink-0" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span>Is it safe to login with my broker?</span>
                <svg
                  class="safety-faq-chevron"
                  :class="{ 'safety-faq-chevron--open': showSafetyInfo }"
                  width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <!-- Safety Info Expanded -->
              <div v-if="showSafetyInfo" class="mt-4 p-4 bg-gray-50 rounded-lg text-left text-sm text-gray-600 border border-gray-200">
                <p class="mb-2"><strong class="text-gray-900">Yes, it's completely safe!</strong></p>
                <ul class="list-disc list-inside space-y-1 text-gray-500">
                  <li>OAuth brokers redirect you to your broker's own login page</li>
                  <li>For AngelOne and Dhan, credentials are used once and never stored</li>
                  <li>We only keep a temporary session token from your broker</li>
                  <li>You can revoke access anytime from your broker's app settings</li>
                </ul>
              </div>
            </div>

            <!-- Terms Footer -->
            <p class="text-center text-xs text-gray-400 mt-8">
              By proceeding, you agree to the
              <a href="/terms" class="underline hover:text-gray-600">terms and conditions</a>
            </p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* KiteHeader-style header */
.kite-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  padding: 0 16px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
}

.logo-icon {
  width: 24px;
  height: 24px;
  color: #387ed1;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  font-size: 15px;
  font-weight: 600;
  color: #212529;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

/* Login Button */
.login-btn {
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  background: #2d6ab8;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.login-btn:hover {
  background: #2660a4;
}

/* Force two-column layout at lg breakpoint since Tailwind JIT isn't generating responsive classes */
.login-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  align-items: center;
  min-height: calc(100vh - 48px - 2rem);
}

@media (min-width: 1024px) {
  .login-grid {
    grid-template-columns: 1fr 1fr;
  }
}

/* Feature icon gradient backgrounds */
.feature-icon-green {
  background: linear-gradient(to bottom right, #22c55e, #059669);
}

.feature-icon-blue {
  background: linear-gradient(to bottom right, #3b82f6, #4f46e5);
}

.feature-icon-purple {
  background: linear-gradient(to bottom right, #a855f7, #ec4899);
}

/* Login card wrapper */
.login-card-wrapper {
  display: flex;
  justify-content: center;
}

@media (min-width: 1024px) {
  .login-card-wrapper {
    justify-content: flex-end;
  }
}

/* Login card styling */
.login-card {
  width: 100%;
  max-width: 28rem;
  background-color: #ffffff;
  border-radius: 1rem;
  border: 1px solid #e5e7eb;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* Broker dropdown */
.broker-select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.broker-color-indicator {
  position: absolute;
  left: 12px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  z-index: 1;
  pointer-events: none;
  transition: background-color 0.2s ease;
}

.broker-select {
  width: 100%;
  appearance: none;
  -webkit-appearance: none;
  padding: 12px 36px 12px 32px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  background-color: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.broker-select:focus {
  outline: none;
  border-color: #387ed1;
  box-shadow: 0 0 0 3px rgba(56, 126, 209, 0.1);
}

.broker-select-arrow {
  position: absolute;
  right: 12px;
  pointer-events: none;
  color: #9ca3af;
}

/* Login input fields */
.login-input {
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #374151;
  transition: border-color 0.15s ease;
}

.login-input:focus {
  outline: none;
  border-color: #387ed1;
  box-shadow: 0 0 0 3px rgba(56, 126, 209, 0.1);
}

.login-input::placeholder {
  color: #9ca3af;
}

/* Login submit button */
.login-submit-btn {
  width: 100%;
  height: 48px;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  background: #2d6ab8;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.login-submit-btn:hover:not(:disabled) {
  background: #2660a4;
}

.login-submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Main container responsive padding */
.main-container {
  max-width: 80rem;
  margin-left: auto;
  margin-right: auto;
  padding: 3rem 1rem;
  padding-top: calc(48px + 1.5rem); /* Account for fixed header */
}

@media (min-width: 640px) {
  .main-container {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .main-container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

/* Safety FAQ toggle button */
.safety-faq-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
  color: #2d6ab8;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 0;
  border-bottom: 1px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.safety-faq-btn:hover {
  color: #2660a4;
  border-bottom-color: #2660a4;
}

.safety-faq-chevron {
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.safety-faq-chevron--open {
  transform: rotate(180deg);
}
</style>
