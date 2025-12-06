<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const broker = ref('zerodha')
const error = ref('')

const handleLogin = async () => {
  error.value = ''

  if (broker.value === 'zerodha') {
    const result = await authStore.initiateZerodhaLogin()
    if (!result.success) {
      error.value = result.error
    }
  } else {
    error.value = `${broker.value} integration coming soon!`
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
    <div class="max-w-md w-full space-y-8 bg-white p-10 rounded-2xl shadow-2xl">
      <!-- Logo and Title -->
      <div class="text-center">
        <h1 class="text-4xl font-bold text-gray-900 mb-2">AlgoChanakya</h1>
        <p class="text-gray-600">Options Trading Platform</p>
      </div>

      <!-- Login Form -->
      <div class="mt-8 space-y-6">
        <div>
          <label for="broker" class="block text-sm font-medium text-gray-700 mb-2">
            Select Broker
          </label>
          <select
            id="broker"
            v-model="broker"
            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none"
          >
            <option value="zerodha">Zerodha</option>
            <option value="upstox">Upstox</option>
            <option value="angelone">Angel One</option>
            <option value="fyers">Fyers</option>
          </select>
        </div>

        <!-- Error Message -->
        <div
          v-if="error"
          class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg"
        >
          {{ error }}
        </div>

        <!-- Login Button -->
        <button
          @click="handleLogin"
          :disabled="authStore.loading"
          class="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="!authStore.loading">Connect to {{ broker }}</span>
          <span v-else class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Connecting...
          </span>
        </button>

        <!-- Info -->
        <div class="text-center text-sm text-gray-600 mt-6">
          <p>Secure OAuth connection with your broker</p>
        </div>
      </div>

      <!-- Features -->
      <div class="mt-8 pt-6 border-t border-gray-200">
        <h3 class="text-sm font-semibold text-gray-700 mb-3">Features</h3>
        <div class="space-y-2 text-sm text-gray-600">
          <div class="flex items-center">
            <svg class="text-green-500 mr-2 flex-shrink-0" width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
            </svg>
            Options strategy builder
          </div>
          <div class="flex items-center">
            <svg class="text-green-500 mr-2 flex-shrink-0" width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
            </svg>
            Real-time market data
          </div>
          <div class="flex items-center">
            <svg class="text-green-500 mr-2 flex-shrink-0" width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
            </svg>
            Advanced analytics
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
