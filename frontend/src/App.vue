<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { loadTradingConstants } from './constants/trading'

const authStore = useAuthStore()

onMounted(async () => {
  // Load constants from backend (non-blocking)
  loadTradingConstants().catch(err => {
    console.warn('[App] Failed to load trading constants, using fallback values:', err)
  })

  // Check authentication
  authStore.checkAuth()
})
</script>

<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />
  </div>
</template>
