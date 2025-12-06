<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import KiteLayout from '../components/layout/KiteLayout.vue'

const router = useRouter()
const authStore = useAuthStore()
</script>

<template>
  <KiteLayout>
    <!-- Main Content -->
    <div class="p-6" style="height: calc(100vh - 48px); overflow-y: auto;">
      <div class="max-w-7xl mx-auto">
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-4">Welcome to Dashboard</h2>
          <p class="text-gray-600">
            Your options trading platform is ready. Start building your strategies!
          </p>

          <!-- Placeholder for dashboard content -->
          <div class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <router-link to="/watchlist" class="bg-blue-50 p-6 rounded-lg hover:bg-blue-100 transition-colors cursor-pointer">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Watchlist</h3>
              <p class="text-gray-600">Track your favorite instruments</p>
            </router-link>
            <router-link to="/strategy" class="bg-green-50 p-6 rounded-lg hover:bg-green-100 transition-colors cursor-pointer">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Strategy Builder</h3>
              <p class="text-gray-600">Build and analyze options strategies</p>
            </router-link>
            <router-link to="/optionchain" class="bg-purple-50 p-6 rounded-lg hover:bg-purple-100 transition-colors cursor-pointer">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Option Chain</h3>
              <p class="text-gray-600">View option chain with OI and Greeks</p>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </KiteLayout>
</template>
