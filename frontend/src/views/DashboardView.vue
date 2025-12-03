<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <h1 class="text-2xl font-bold text-gray-900">AlgoChanakya</h1>
          </div>
          <div class="flex items-center">
            <button
              @click="handleLogout"
              class="ml-4 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4">Welcome to Dashboard</h2>
          <p class="text-gray-600">
            Your options trading platform is ready. Start building your strategies!
          </p>

          <!-- Placeholder for dashboard content -->
          <div class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div class="bg-blue-50 p-6 rounded-lg">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Portfolio</h3>
              <p class="text-gray-600">View your current positions</p>
            </div>
            <div class="bg-green-50 p-6 rounded-lg">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Strategies</h3>
              <p class="text-gray-600">Build and analyze strategies</p>
            </div>
            <div class="bg-purple-50 p-6 rounded-lg">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Analytics</h3>
              <p class="text-gray-600">Market insights and data</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
