<script setup>
/**
 * BrokerUpgradeBanner
 *
 * Persistent upgrade prompt shown on all data screens when the user is on
 * platform-default market data. Dismissed state persists for the session
 * (sessionStorage), so it won't re-appear on navigation within the same tab.
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBrokerPreferencesStore } from '@/stores/brokerPreferences'

const props = defineProps({
  /** Screen name used for data-testid namespacing (e.g. "dashboard", "watchlist") */
  screen: {
    type: String,
    required: true
  }
})

const router = useRouter()
const brokerStore = useBrokerPreferencesStore()

const dismissed = ref(false)

const sessionKey = computed(() => `broker-upgrade-banner-dismissed-${props.screen}`)

onMounted(async () => {
  // Check dismissal state from sessionStorage
  if (sessionStorage.getItem(sessionKey.value)) {
    dismissed.value = true
  }

  // Load preferences if not already loaded
  if (!brokerStore.preferences) {
    try {
      await brokerStore.fetchPreferences()
    } catch {
      // Silently fail — banner shows by default if preferences unavailable
    }
  }
})

const showBanner = computed(() => {
  return !dismissed.value && brokerStore.isUsingPlatformDefault
})

const handleDismiss = () => {
  dismissed.value = true
  sessionStorage.setItem(sessionKey.value, '1')
}

const goToSettings = () => {
  router.push('/settings')
}
</script>

<template>
  <div
    v-if="showBanner"
    class="broker-upgrade-banner"
    :data-testid="`${screen}-upgrade-banner`"
  >
    <div class="banner-content">
      <div class="banner-icon">
        <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
        </svg>
      </div>
      <p class="banner-text">
        You're using platform data.
        <button
          class="banner-link"
          @click="goToSettings"
          :data-testid="`${screen}-upgrade-banner-settings-link`"
        >
          Connect your own broker API
        </button>
        for faster, direct quotes.
      </p>
    </div>
    <button
      class="banner-dismiss"
      @click="handleDismiss"
      :data-testid="`${screen}-upgrade-banner-dismiss`"
      aria-label="Dismiss upgrade banner"
    >
      <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.broker-upgrade-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  margin-bottom: 12px;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.banner-icon {
  color: #3b82f6;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.banner-text {
  font-size: 13px;
  color: #1e40af;
  margin: 0;
  line-height: 1.4;
}

.banner-link {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.banner-link:hover {
  color: #1d4ed8;
}

.banner-dismiss {
  background: none;
  border: none;
  color: #93c5fd;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: color 0.15s;
}

.banner-dismiss:hover {
  color: #3b82f6;
}
</style>
