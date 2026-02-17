<script setup>
/**
 * DataSourceBadge
 *
 * Small badge showing the active market data source (e.g. "SmartAPI ●").
 * Placed in the corner of data screens so users always know what data
 * provider is active.
 */
import { computed, onMounted } from 'vue'
import { useBrokerPreferencesStore } from '@/stores/brokerPreferences'

const props = defineProps({
  /** Screen name used for data-testid namespacing */
  screen: {
    type: String,
    required: true
  }
})

const brokerStore = useBrokerPreferencesStore()

onMounted(async () => {
  if (!brokerStore.preferences) {
    try {
      await brokerStore.fetchPreferences()
    } catch {
      // Silently fail
    }
  }
})

const label = computed(() => brokerStore.activeSourceLabel)
</script>

<template>
  <div
    class="data-source-badge"
    :data-testid="`${screen}-data-source-badge`"
    :title="`Market data: ${label}`"
  >
    <span class="badge-dot" aria-hidden="true"></span>
    <span class="badge-label">{{ label }}</span>
  </div>
</template>

<style scoped>
.data-source-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  font-size: 11px;
  color: #166534;
  font-weight: 500;
  white-space: nowrap;
  user-select: none;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  flex-shrink: 0;
}

.badge-label {
  line-height: 1;
}
</style>
