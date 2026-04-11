<script setup>
/**
 * MarketStatusBanner
 *
 * Shown when data_freshness === 'LAST_KNOWN' — market is closed and
 * prices reflect the previous trading session's close, not live ticks.
 * Mirrors the behavior of NSE India, Sensibull, and Opstra.
 */
defineProps({
  /** 'LIVE' | 'LAST_KNOWN' */
  dataFreshness: {
    type: String,
    default: 'LIVE'
  },
  /** Screen name for data-testid namespacing */
  screen: {
    type: String,
    required: true
  }
})
</script>

<template>
  <div
    v-if="dataFreshness === 'LAST_KNOWN'"
    class="market-status-banner"
    role="status"
    :data-testid="`${screen}-market-closed-banner`"
  >
    <span class="banner-icon" aria-hidden="true">🕒</span>
    <span class="banner-text">
      Market closed &mdash; showing previous session's closing prices
    </span>
  </div>
</template>

<style scoped>
.market-status-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: #fefce8;
  border: 1px solid #fde047;
  border-radius: 6px;
  font-size: 13px;
  color: #854d0e;
  font-weight: 500;
  margin-bottom: 8px;
}

.banner-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.banner-text {
  line-height: 1.3;
}
</style>
