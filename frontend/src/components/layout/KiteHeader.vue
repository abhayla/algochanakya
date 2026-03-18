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
        <div class="index-item" data-testid="kite-header-index-sensex">
          <span class="index-name">SENSEX</span>
          <span :class="['index-price', (indexTicks.sensex?.change || 0) >= 0 ? 'up' : 'down']" data-testid="kite-header-index-value-sensex">
            {{ formatNumber(indexTicks.sensex?.ltp) }}
          </span>
          <span :class="['index-change', (indexTicks.sensex?.change || 0) >= 0 ? 'up' : 'down']">
            {{ formatChange(indexTicks.sensex?.change) }} ({{ formatPct(indexTicks.sensex?.change_percent) }})
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
          :aria-current="isActive(item.path) ? 'page' : undefined"
          :title="item.title || ''"
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
          <!-- Brain icon for AI Settings -->
          <svg
            v-if="item.icon === 'brain'"
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
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/>
            <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/>
          </svg>
          {{ item.label }}
        </router-link>
      </nav>

      <!-- Actions -->
      <div class="header-actions">
        <!-- Connection Status -->
        <div class="market-status-badge" :style="{ color: marketStatus.color, borderColor: marketStatus.color + '40' }" data-testid="kite-header-market-status">
          <span class="market-dot" :style="{ background: marketStatus.color }"></span>
          {{ marketStatus.label }}
        </div>

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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useWatchlistStore } from '@/stores/watchlist';
import { fetchIndexPrices, startPollingFallback, stopPollingFallback } from '@/services/priceService';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const watchlistStore = useWatchlistStore();

const showUserDropdown = ref(false);

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/optionchain', label: 'Option Chain' },
  { path: '/ofo', label: 'OFO', title: 'Options For Options — Find optimal strategy combinations' },
  { path: '/strategy', label: 'Strategy' },
  { path: '/positions', label: 'Positions' },
  // Hidden for initial deployment - not fully tested
  // { path: '/autopilot', label: 'AutoPilot', icon: 'robot' },
  // { path: '/ai/settings', label: 'AI Settings', icon: 'brain' },
];

const indexTicks = computed(() => watchlistStore.indexTicks);

const marketStatus = computed(() => {
  const now = new Date();
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const hours = ist.getHours();
  const minutes = ist.getMinutes();
  const day = ist.getDay();
  const timeInMinutes = hours * 60 + minutes;

  // Weekend
  if (day === 0 || day === 6) return { label: 'Market Closed', color: '#ef4444', isOpen: false };

  // Pre-market: 9:00 - 9:15
  if (timeInMinutes >= 540 && timeInMinutes < 555) return { label: 'Pre-Market', color: '#f59e0b', isOpen: false };

  // Market open: 9:15 - 15:30
  if (timeInMinutes >= 555 && timeInMinutes <= 930) return { label: 'Market Open', color: '#22c55e', isOpen: true };

  // Post-market: 15:30 - 16:00
  if (timeInMinutes > 930 && timeInMinutes <= 960) return { label: 'Post-Market', color: '#f59e0b', isOpen: false };

  // Closed
  return { label: 'Market Closed', color: '#ef4444', isOpen: false };
});

const userId = computed(() => {
  return authStore.user?.first_name || authStore.user?.broker_user_id || 'Guest';
});

const userName = computed(() => {
  return authStore.user?.first_name || authStore.user?.broker_user_id || 'User';
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

// Stop polling when WebSocket connects
watch(() => watchlistStore.isConnected, (connected) => {
  if (connected) stopPollingFallback();
});

onMounted(() => {
  document.addEventListener('click', closeDropdown);

  // Fetch index prices via API as initial data (fallback for WebSocket)
  // Wait a bit for WebSocket to potentially connect first
  setTimeout(() => {
    const ticks = indexTicks.value;
    const anyMissing = !ticks.nifty50?.ltp || !ticks.niftyBank?.ltp || !ticks.finnifty?.ltp || !ticks.sensex?.ltp;
    if (anyMissing) {
      fetchIndexPrices((token, tick) => watchlistStore.updateTick(token, tick));
    }
    // Start polling if WebSocket is still not connected after 2s
    if (!watchlistStore.isConnected) {
      startPollingFallback(
        () => fetchIndexPrices((token, tick) => watchlistStore.updateTick(token, tick)),
        10000
      );
    }
  }, 2000);
});

onUnmounted(() => {
  document.removeEventListener('click', closeDropdown);
  stopPollingFallback();
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
  color: #2d68b0;
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

.index-price.up { color: #00875a; }
.index-price.down { color: #d43f3a; }  /* WCAG AA compliant (4.59:1 contrast) */

.index-change {
  font-size: 11px;
}

.index-change.up { color: #00875a; }
.index-change.down { color: #d43f3a; }  /* WCAG AA compliant (4.59:1 contrast) */

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
  color: #2d68b0;
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

.market-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border: 1px solid;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.market-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
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
  background: #2d68b0;
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
  position: fixed;
  top: 48px;
  right: 16px;
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
