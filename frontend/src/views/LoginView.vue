<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const error = ref('')
const showSafetyInfo = ref(false)

const handleZerodhaLogin = async () => {
  error.value = ''
  const result = await authStore.initiateZerodhaLogin()
  if (!result.success) {
    error.value = result.error
  }
}

const handleAngelOneLogin = async () => {
  error.value = 'Angel One integration coming soon!'
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

      <!-- Right: Navigation + Login Button -->
      <div class="header-right">
        <!-- Main Navigation -->
        <nav class="main-nav">
          <button @click="scrollToLogin" class="nav-item">Dashboard</button>
          <button @click="scrollToLogin" class="nav-item">Option Chain</button>
          <button @click="scrollToLogin" class="nav-item">Strategy</button>
          <button @click="scrollToLogin" class="nav-item">Watchlist</button>
        </nav>

        <!-- Login Button -->
        <button @click="scrollToLogin" class="login-btn">Login</button>
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

          <!-- Feature 1 -->
          <div class="flex items-start space-x-4">
            <div class="w-14 h-14 feature-icon-green rounded-2xl flex items-center justify-center flex-shrink-0">
              <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Advanced Strategy Builder</h3>
              <p class="text-gray-500">
                Build complex multi-leg options strategies with real-time P/L visualization, breakeven analysis, and risk metrics.
              </p>
            </div>
          </div>

          <!-- Feature 2 -->
          <div class="flex items-start space-x-4">
            <div class="w-14 h-14 feature-icon-blue rounded-2xl flex items-center justify-center flex-shrink-0">
              <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Live Market Data</h3>
              <p class="text-gray-500">
                Stream real-time prices via WebSocket. Track option chains with IV, Greeks, and open interest analysis.
              </p>
            </div>
          </div>

          <!-- Feature 3 -->
          <div class="flex items-start space-x-4">
            <div class="w-14 h-14 feature-icon-purple rounded-2xl flex items-center justify-center flex-shrink-0">
              <svg class="w-7 h-7 text-white" width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">Secure Broker Integration</h3>
              <p class="text-gray-500">
                Connect securely via OAuth. Your credentials are never stored - we only use authorized API access.
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

            <!-- Zerodha Login Button -->
            <button
              @click="handleZerodhaLogin"
              :disabled="authStore.loading"
              class="w-full text-gray-700 text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-3 mb-3"
              style="height: 48px; background-color: #f5f9ff; border: 0.8px solid #bfd7f2; border-radius: 8px; padding: 11px 12px 11px 16px;"
              data-testid="login-zerodha-button"
            >
              <!-- Kite Logo -->
              <img src="../assets/kite-logo.png" alt="Kite" style="height: 24px; width: auto;" class="flex-shrink-0" />
              <span v-if="!authStore.loading">Login with Zerodha</span>
              <span v-else class="flex items-center">
                <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-gray-500" width="20" height="20" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Connecting...
              </span>
            </button>
            <p class="text-center text-sm text-gray-500 mb-6">
              Don't have a Zerodha account?
              <a href="https://zerodha.com/open-account" target="_blank" class="text-blue-600 hover:text-blue-700 underline">
                Open Now
              </a>
            </p>

            <!-- Divider -->
            <div class="flex items-center my-6">
              <div class="flex-1 border-t border-gray-200"></div>
              <span class="px-4 text-sm text-gray-400">Or login with</span>
              <div class="flex-1 border-t border-gray-200"></div>
            </div>

            <!-- Angel One Login Button -->
            <button
              @click="handleAngelOneLogin"
              class="w-full text-gray-700 text-sm font-medium transition-all flex items-center justify-center space-x-3 mb-3"
              style="height: 44px; background-color: #ffffff; border: 0.8px solid #d8dce3; border-radius: 6px; padding: 11px 15px;"
              data-testid="login-angelone-button"
            >
              <!-- Angel One Logo -->
              <img src="../assets/angelone-logo.png" alt="Angel One" style="height: 24px; width: auto;" class="flex-shrink-0" />
              <span>Angel One</span>
            </button>
            <p class="text-center text-sm text-gray-500 mb-6">
              Don't have an Angel One account?
              <a href="https://www.angelone.in/open-demat-account" target="_blank" class="text-blue-600 hover:text-blue-700 underline">
                Open Now
              </a>
            </p>

            <!-- Safety Info Link -->
            <div class="text-center mt-6">
              <button
                @click="showSafetyInfo = !showSafetyInfo"
                class="text-blue-600 hover:text-blue-700 text-sm flex items-center justify-center space-x-1 mx-auto"
                data-testid="login-safety-toggle"
              >
                <svg class="w-4 h-4 flex-shrink-0" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span>Is it safe to login with my broker?</span>
              </button>

              <!-- Safety Info Expanded -->
              <div v-if="showSafetyInfo" class="mt-4 p-4 bg-gray-50 rounded-lg text-left text-sm text-gray-600 border border-gray-200">
                <p class="mb-2"><strong class="text-gray-900">Yes, it's completely safe!</strong></p>
                <ul class="list-disc list-inside space-y-1 text-gray-500">
                  <li>We use OAuth 2.0, the industry standard for secure authentication</li>
                  <li>Your broker credentials are never shared with us</li>
                  <li>We only receive a temporary access token from your broker</li>
                  <li>You can revoke access anytime from your broker's app settings</li>
                </ul>
              </div>
            </div>

            <!-- Terms Footer -->
            <p class="text-center text-xs text-gray-400 mt-8">
              By proceeding, you agree to terms and conditions
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

/* Navigation */
.main-nav {
  display: none;
  gap: 4px;
}

@media (min-width: 768px) {
  .main-nav {
    display: flex;
  }
}

.nav-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #6c757d;
  text-decoration: none;
  border-radius: 3px;
  transition: all 0.15s ease;
  background: none;
  border: none;
  cursor: pointer;
}

.nav-item:hover {
  color: #212529;
  background: #f5f5f5;
}

/* Login Button */
.login-btn {
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  background: #387ed1;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.login-btn:hover {
  background: #2d6ab8;
}

/* Force two-column layout at lg breakpoint since Tailwind JIT isn't generating responsive classes */
.login-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 3rem;
  align-items: center;
  min-height: calc(100vh - 48px - 6rem); /* Account for header and padding */
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

/* Main container responsive padding */
.main-container {
  max-width: 80rem;
  margin-left: auto;
  margin-right: auto;
  padding: 3rem 1rem;
  padding-top: calc(48px + 3rem); /* Account for fixed header */
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
</style>
