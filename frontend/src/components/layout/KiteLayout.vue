<template>
  <div class="kite-layout">
    <!-- Header -->
    <KiteHeader />

    <!-- Main Content Area -->
    <div class="kite-main">
      <!-- Optional Sidebar -->
      <aside v-if="showSidebar" class="kite-sidebar">
        <slot name="sidebar"></slot>
      </aside>

      <!-- Content -->
      <main class="kite-content" :class="{ 'full-width': !showSidebar }">
        <slot></slot>
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import KiteHeader from './KiteHeader.vue';
import { useAuthStore } from '@/stores/auth';
import { useWatchlistStore } from '@/stores/watchlist';

const authStore = useAuthStore();
const watchlistStore = useWatchlistStore();

defineProps({
  showSidebar: {
    type: Boolean,
    default: false
  }
});

// Initialize WebSocket for index prices in header (all protected routes)
onMounted(() => {
  if (authStore.isAuthenticated && !watchlistStore.isConnected) {
    watchlistStore.connectWebSocket();
  }
});
</script>

<style scoped>
.kite-layout {
  min-height: 100vh;
  background: var(--kite-body-bg, #ffffff);
}

.kite-main {
  display: flex;
  padding-top: 48px; /* Header height */
  min-height: calc(100vh - 48px);
}

.kite-sidebar {
  width: 400px;
  flex-shrink: 0;
  background: white;
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
  height: calc(100vh - 48px);
  position: sticky;
  top: 48px;
}

.kite-content {
  flex: 1;
  padding: 0;  /* Removed - child components handle their own padding */
  overflow-x: hidden;  /* Prevent horizontal overflow */
  overflow-y: auto;
  max-width: 100%;
}

.kite-content.full-width {
  max-width: 100%;
}
</style>
