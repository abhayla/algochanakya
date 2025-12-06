<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="max-w-md w-full space-y-8 p-8">
      <div class="text-center">
        <div v-if="loading" class="space-y-4">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p class="text-gray-600">Completing authentication...</p>
        </div>

        <div v-else-if="error" class="space-y-4">
          <div class="text-red-600 text-5xl">✗</div>
          <h2 class="text-2xl font-bold text-gray-900">Authentication Failed</h2>
          <p class="text-gray-600">{{ errorMessage }}</p>
          <button
            @click="redirectToLogin"
            class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
          >
            Back to Login
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  const token = route.query.token
  const errorParam = route.query.error
  const errorMsg = route.query.message

  if (errorParam) {
    loading.value = false
    error.value = true
    errorMessage.value = errorMsg || 'Authentication failed. Please try again.'
    return
  }

  if (!token) {
    loading.value = false
    error.value = true
    errorMessage.value = 'No authentication token received.'
    return
  }

  try {
    authStore.setToken(token)

    const result = await authStore.fetchUser()

    if (result.success) {
      router.push('/dashboard')
    } else {
      error.value = true
      errorMessage.value = result.error || 'Failed to fetch user information.'
    }
  } catch (err) {
    error.value = true
    errorMessage.value = 'An unexpected error occurred.'
    console.error('Auth callback error:', err)
  } finally {
    loading.value = false
  }
})

function redirectToLogin() {
  router.push('/login')
}
</script>
