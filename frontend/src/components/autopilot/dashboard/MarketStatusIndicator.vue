<script setup>
/**
 * Market Status Indicator Component
 *
 * Shows market status, countdown, and key index prices
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  indexPrices: {
    type: Object,
    default: () => ({})
  }
})

// Current time tracking
const now = ref(Date.now())
let timeInterval = null

onMounted(() => {
  timeInterval = setInterval(() => {
    now.value = Date.now()
  }, 1000) // Update every second
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})

// Market hours (IST)
const MARKET_OPEN_HOUR = 9
const MARKET_OPEN_MINUTE = 15
const MARKET_CLOSE_HOUR = 15
const MARKET_CLOSE_MINUTE = 30

// Check if market is open
const isMarketOpen = computed(() => {
  const date = new Date(now.value)
  const day = date.getDay() // 0 = Sunday, 6 = Saturday

  // Market closed on weekends
  if (day === 0 || day === 6) return false

  const hours = date.getHours()
  const minutes = date.getMinutes()
  const currentMinutes = hours * 60 + minutes
  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
  const closeMinutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

  return currentMinutes >= openMinutes && currentMinutes < closeMinutes
})

// Countdown to next market event
const countdown = computed(() => {
  const date = new Date(now.value)
  const day = date.getDay()
  const hours = date.getHours()
  const minutes = date.getMinutes()

  // If weekend, show time until Monday
  if (day === 0) { // Sunday
    return 'Opens Monday 9:15 AM'
  }
  if (day === 6) { // Saturday
    return 'Opens Monday 9:15 AM'
  }

  const currentMinutes = hours * 60 + minutes
  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
  const closeMinutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

  if (currentMinutes < openMinutes) {
    // Before market opens
    const diff = openMinutes - currentMinutes
    const h = Math.floor(diff / 60)
    const m = diff % 60
    return `Opens in ${h > 0 ? h + 'h ' : ''}${m}m`
  } else if (currentMinutes < closeMinutes) {
    // Market is open
    const diff = closeMinutes - currentMinutes
    const h = Math.floor(diff / 60)
    const m = diff % 60
    return `Closes in ${h > 0 ? h + 'h ' : ''}${m}m`
  } else {
    // After market closes
    return 'Opens tomorrow 9:15 AM'
  }
})

// Format price change
const formatChange = (change, changePct) => {
  if (!change && !changePct) return { text: '-', color: '#6b7280' }

  const sign = change >= 0 ? '+' : ''
  const color = change >= 0 ? 'var(--kite-green)' : 'var(--kite-red)'
  const text = `${sign}${change?.toFixed(2) || 0} (${sign}${changePct?.toFixed(2) || 0}%)`

  return { text, color }
}

// Get index data
const getNiftyData = computed(() => {
  const data = props.indexPrices?.NIFTY || {}
  return {
    price: data.ltp?.toLocaleString() || '-',
    change: formatChange(data.change, data.change_percent)
  }
})

const getBankNiftyData = computed(() => {
  const data = props.indexPrices?.BANKNIFTY || {}
  return {
    price: data.ltp?.toLocaleString() || '-',
    change: formatChange(data.change, data.change_percent)
  }
})

const getVixData = computed(() => {
  const data = props.indexPrices?.VIX || {}
  return {
    price: data.ltp?.toFixed(2) || '-',
    change: formatChange(data.change, data.change_percent)
  }
})
</script>

<template>
  <div class="market-status-indicator" data-testid="autopilot-market-status">
    <!-- Market Status -->
    <div class="status-section">
      <span
        class="status-dot"
        :class="{ 'open': isMarketOpen, 'closed': !isMarketOpen }"
        data-testid="autopilot-market-status-dot"
      ></span>
      <span class="status-text">
        <strong>{{ isMarketOpen ? 'Market Open' : 'Market Closed' }}</strong>
        <span class="separator">·</span>
        <span data-testid="autopilot-market-countdown">{{ countdown }}</span>
      </span>
    </div>

    <!-- Index Prices -->
    <div class="indices-section">
      <!-- NIFTY -->
      <div class="index-item" data-testid="autopilot-nifty-price">
        <span class="index-label">NIFTY</span>
        <span class="index-price">{{ getNiftyData.price }}</span>
        <span class="index-change" :style="{ color: getNiftyData.change.color }">
          {{ getNiftyData.change.text }}
        </span>
      </div>

      <!-- BANK NIFTY -->
      <div class="index-item" data-testid="autopilot-banknifty-price">
        <span class="index-label">BANKNIFTY</span>
        <span class="index-price">{{ getBankNiftyData.price }}</span>
        <span class="index-change" :style="{ color: getBankNiftyData.change.color }">
          {{ getBankNiftyData.change.text }}
        </span>
      </div>

      <!-- VIX -->
      <div class="index-item" data-testid="autopilot-vix-price">
        <span class="index-label">VIX</span>
        <span class="index-price">{{ getVixData.price }}</span>
        <span class="index-change" :style="{ color: getVixData.change.color }">
          {{ getVixData.change.text }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.market-status-indicator {
  background: white;
  border-radius: 8px;
  border: 1px solid var(--kite-border);
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  box-shadow: var(--kite-shadow-sm);
  margin-bottom: 20px;
}

/* Status Section */
.status-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.open {
  background: var(--kite-green);
}

.status-dot.closed {
  background: var(--kite-red);
  animation: none;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-text {
  font-size: 13px;
  color: var(--kite-text-primary);
}

.status-text strong {
  font-weight: 600;
}

.separator {
  margin: 0 6px;
  color: var(--kite-text-muted);
}

/* Indices Section */
.indices-section {
  display: flex;
  gap: 32px;
  align-items: center;
}

.index-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.index-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--kite-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.index-price {
  font-size: 14px;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.index-change {
  font-size: 12px;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 1200px) {
  .market-status-indicator {
    flex-wrap: wrap;
  }

  .indices-section {
    gap: 20px;
  }
}

@media (max-width: 768px) {
  .indices-section {
    flex-wrap: wrap;
  }

  .index-item {
    min-width: 120px;
  }
}
</style>
