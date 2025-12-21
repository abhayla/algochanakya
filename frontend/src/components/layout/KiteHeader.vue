<template>
  <header class="kite-header" data-testid="kite-header">
    <!-- Left: Logo + Index Prices -->
    <div class="header-left">
      <!-- Logo -->
      <router-link to="/" class="logo" data-testid="kite-header-logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span class="logo-text">AlgoChanakya</span>
      </router-link>

      <!-- Index Prices -->
      <div class="index-prices" data-testid="kite-header-index-prices">
        <div class="index-item" data-testid="kite-header-index-nifty50">
          <span class="index-name">NIFTY 50</span>
          <span :class="['index-price', (indexTicks.nifty50?.change || 0) >= 0 ? 'up' : 'down']" data-testid="kite-header-index-value-nifty50">
            {{ formatNumber(indexTicks.nifty50?.ltp) }}
          </span>
          <span :class="['index-change', (indexTicks.nifty50?.change || 0) >= 0 ? 'up' : 'down']">
            {{ formatChange(indexTicks.nifty50?.change) }} ({{ formatPct(indexTicks.nifty50?.change_percent) }})
          </span>
        </div>
        <div class="index-item" data-testid="kite-header-index-niftybank">
          <span class="index-name">NIFTY BANK</span>
          <span :class="['index-price', (indexTicks.niftyBank?.change || 0) >= 0 ? 'up' : 'down']" data-testid="kite-header-index-value-niftybank">
            {{ formatNumber(indexTicks.niftyBank?.ltp) }}
          </span>
          <span :class="['index-change', (indexTicks.niftyBank?.change || 0) >= 0 ? 'up' : 'down']">
            {{ formatChange(indexTicks.niftyBank?.change) }} ({{ formatPct(indexTicks.niftyBank?.change_percent) }})
          </span>
        </div>
      </div>
    </div>

    <!-- Right: Navigation + User -->
    <div class="header-right">
      <!-- Main Navigation -->
      <nav class="main-nav" data-testid="kite-header-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { active: isActive(item.path) }]"
          :data-testid="`kite-header-nav-${item.path.slice(1)}`"
        >
          <!-- Robot icon for AutoPilot -->
          <svg
            v-if="item.icon === 'robot'"
            class="nav-icon"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="3" y="11" width="18" height="10" rx="2"/>
            <circle cx="12" cy="5" r="2"/>
            <path d="M12 7v4"/>
            <circle cx="8" cy="16" r="1"/>
            <circle cx="16" cy="16" r="1"/>
          </svg>
          {{ item.label }}
        </router-link>
      </nav>

      <!-- Actions -->
      <div class="header-actions">
        <!-- Connection Status -->
        <div :class="['status-dot', { connected: watchlistStore.isConnected }]" :title="watchlistStore.isConnected ? 'Live' : 'Disconnected'" data-testid="kite-header-connection-status"></div>

        <!-- Header Icons -->
        <div class="header-icons">
          <!-- Orders/Cart icon -->
          <button class="icon-btn" title="Orders">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"/>
            </svg>
          </button>
          <!-- Notifications bell -->
          <button class="icon-btn" title="Notifications">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
          </button>
        </div>

        <!-- User Menu -->
        <div class="user-menu" @click="toggleUserDropdown" data-testid="kite-header-user-menu">
          <div class="user-avatar" data-testid="kite-header-user-avatar">
            {{ userInitials }}
          </div>
          <span class="user-id">{{ userId }}</span>
          <svg class="dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </div>

        <!-- User Dropdown -->
        <div v-if="showUserDropdown" class="user-dropdown" data-testid="kite-header-user-dropdown">
          <div class="dropdown-item user-info">
            <span class="user-name" data-testid="kite-header-user-name">{{ userName }}</span>
            <span class="user-broker">Zerodha</span>
          </div>
          <div class="dropdown-divider"></div>
          <button class="dropdown-item" @click="router.push('/settings'); showUserDropdown = false" data-testid="kite-header-settings-button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"/>
            </svg>
            Settings
          </button>
          <button class="dropdown-item" @click="logout" data-testid="kite-header-logout-button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
              <polyline points="16,17 21,12 16,7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Logout
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useWatchlistStore } from '@/stores/watchlist';
import { fetchIndexPrices } from '@/composables/usePriceFallback';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const watchlistStore = useWatchlistStore();

const showUserDropdown = ref(false);

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/optionchain', label: 'Option Chain' },
  { path: '/strategy', label: 'Strategy' },
  { path: '/positions', label: 'Positions' },
  { path: '/autopilot', label: 'AutoPilot', icon: 'robot' },
];

const indexTicks = computed(() => watchlistStore.indexTicks);

const userId = computed(() => {
  return authStore.user?.broker_user_id || authStore.user?.user_id || 'Guest';
});

const userName = computed(() => {
  return authStore.user?.name || authStore.user?.broker_user_id || 'User';
});

const userInitials = computed(() => {
  const name = userName.value;
  if (!name) return 'U';
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
});

const isActive = (path) => {
  return route.path === path || route.path.startsWith(path + '/');
};

const formatNumber = (num) => {
  if (!num) return '--';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(num);
};

const formatChange = (change) => {
  if (change === null || change === undefined) return '--';
  return (change >= 0 ? '+' : '') + change.toFixed(2);
};

const formatPct = (pct) => {
  if (pct === null || pct === undefined) return '--%';
  return (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
};

const toggleUserDropdown = () => {
  showUserDropdown.value = !showUserDropdown.value;
};

const closeDropdown = (e) => {
  if (!e.target.closest('.user-menu') && !e.target.closest('.user-dropdown')) {
    showUserDropdown.value = false;
  }
};

const logout = async () => {
  await authStore.logout();
  watchlistStore.disconnectWebSocket();
  router.push('/login');
};

onMounted(() => {
  document.addEventListener('click', closeDropdown);

  // Fetch index prices via API as initial data (fallback for WebSocket)
  // Wait a bit for WebSocket to potentially connect first
  setTimeout(() => {
    if (!indexTicks.value.nifty50?.ltp) {
      fetchIndexPrices((token, tick) => watchlistStore.updateTick(token, tick));
    }
  }, 2000);
});

onUnmounted(() => {
  document.removeEventListener('click', closeDropdown);
});
</script>

<style scoped>
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
  width: 100%;
  max-width: 100vw;
  min-width: 0;
  overflow-x: hidden;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 0;
  flex-shrink: 1;
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

/* Index Prices */
.index-prices {
  display: flex;
  gap: 20px;
}

.index-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 3px;
  transition: background 0.15s ease;
}

.index-item:hover {
  background: #f5f5f5;
}

.index-name {
  font-size: 11px;
  color: #6c757d;
  text-transform: uppercase;
  font-weight: 500;
}

.index-price {
  font-size: 13px;
  font-weight: 600;
}

.index-price.up { color: #00b386; }
.index-price.down { color: #e74c3c; }

.index-change {
  font-size: 11px;
}

.index-change.up { color: #00b386; }
.index-change.down { color: #e74c3c; }

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 0;
  flex-shrink: 1;
}

/* Navigation */
.main-nav {
  display: flex;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 13px;
  color: #6c757d;
  text-decoration: none;
  border-radius: 3px;
  transition: all 0.15s ease;
}

.nav-icon {
  flex-shrink: 0;
}

.nav-item:hover {
  color: #212529;
  background: #f5f5f5;
}

.nav-item.active {
  color: #387ed1;
  background: transparent;
  font-weight: 500;
}

/* Actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9aa3ad;
}

.status-dot.connected {
  background: #00b386;
  box-shadow: 0 0 6px rgba(0, 179, 134, 0.6);
}

/* User Menu */
.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.user-menu:hover {
  background: #f5f5f5;
}

/* Header Icons */
.header-icons {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: 3px;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-btn:hover {
  background: #f5f5f5;
  color: #212529;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

/* User Avatar Circle */
.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #387ed1;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.user-id {
  font-size: 12px;
  font-weight: 500;
  color: #394046;
}

.dropdown-arrow {
  width: 14px;
  height: 14px;
  color: #6c757d;
}

/* User Dropdown */
.user-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  min-width: 180px;
  overflow: hidden;
  z-index: 1001;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #212529;
  cursor: pointer;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

.dropdown-item svg {
  width: 16px;
  height: 16px;
  color: #6c757d;
}

.dropdown-item.user-info {
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  cursor: default;
}

.dropdown-item.user-info:hover {
  background: white;
}

.user-name {
  font-weight: 500;
}

.user-broker {
  font-size: 11px;
  color: #6c757d;
}

.dropdown-divider {
  height: 1px;
  background: #e0e0e0;
  margin: 4px 0;
}
</style>
