<script setup>
import { onMounted } from 'vue'
import { loadTradingConstants } from './constants/trading'

// Auth check is owned by router.beforeEach (authInitialized guard).
// Calling authStore.checkAuth() here too caused two concurrent /api/auth/me
// requests on every initial page load.

onMounted(async () => {
  loadTradingConstants().catch(err => {
    console.warn('[App] Failed to load trading constants, using fallback values:', err)
  })
})
</script>

<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />
  </div>
</template>
