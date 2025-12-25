<template>
  <div class="position-sync-status" :class="statusClass" data-testid="position-sync-status">
    <div class="sync-indicator" data-testid="sync-indicator">
      <div class="sync-icon" :class="{ pulse: isSyncing }">
        <i :class="statusIcon"></i>
      </div>
      <div class="sync-content">
        <div class="sync-label">Position Sync</div>
        <div class="sync-time" data-testid="sync-time">{{ syncMessage }}</div>
      </div>
    </div>

    <div v-if="lastSyncData && showDetails" class="sync-details" data-testid="sync-details">
      <div class="detail-row">
        <span class="detail-label">Total Positions:</span>
        <span class="detail-value" data-testid="total-positions">{{ lastSyncData.totalPositions || 0 }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Total P&L:</span>
        <span class="detail-value" :class="pnlClass" data-testid="total-pnl">
          {{ formatPnl(lastSyncData.totalPnl || 0) }}
        </span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Health Score:</span>
        <span class="detail-value" :class="healthClass" data-testid="health-score">
          {{ healthScore }}/100
        </span>
      </div>
    </div>

    <div v-if="error" class="sync-error" data-testid="sync-error">
      <i class="fas fa-exclamation-circle"></i>
      <span>{{ error }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'idle',  // idle, syncing, success, error
    validator: (value) => ['idle', 'syncing', 'success', 'error'].includes(value)
  },
  lastSyncTime: {
    type: String,
    default: null
  },
  lastSyncData: {
    type: Object,
    default: null
  },
  error: {
    type: String,
    default: null
  },
  showDetails: {
    type: Boolean,
    default: false
  }
})

const isSyncing = computed(() => props.status === 'syncing')

const statusClass = computed(() => {
  return `sync-${props.status}`
})

const statusIcon = computed(() => {
  switch (props.status) {
    case 'syncing':
      return 'fas fa-sync-alt fa-spin'
    case 'success':
      return 'fas fa-check-circle'
    case 'error':
      return 'fas fa-exclamation-triangle'
    default:
      return 'fas fa-circle-notch'
  }
})

const syncMessage = computed(() => {
  if (props.status === 'syncing') {
    return 'Syncing positions...'
  }

  if (props.status === 'error') {
    return 'Sync failed'
  }

  if (!props.lastSyncTime) {
    return 'Not synced yet'
  }

  const lastSync = new Date(props.lastSyncTime)
  const now = new Date()
  const diff = Math.floor((now - lastSync) / 1000)  // seconds

  if (diff < 10) {
    return 'Just now'
  } else if (diff < 60) {
    return `${diff}s ago`
  } else if (diff < 3600) {
    const mins = Math.floor(diff / 60)
    return `${mins}m ago`
  } else {
    const hours = Math.floor(diff / 3600)
    return `${hours}h ago`
  }
})

const healthScore = computed(() => {
  if (!props.lastSyncData || props.lastSyncData.healthScore === undefined) {
    return 0
  }
  return Math.round(props.lastSyncData.healthScore)
})

const healthClass = computed(() => {
  const score = healthScore.value
  if (score >= 80) return 'health-good'
  if (score >= 50) return 'health-warning'
  return 'health-bad'
})

const pnlClass = computed(() => {
  const pnl = props.lastSyncData?.totalPnl || 0
  return pnl >= 0 ? 'pnl-profit' : 'pnl-loss'
})

const formatPnl = (pnl) => {
  const sign = pnl >= 0 ? '+' : ''
  return `${sign}₹${Math.abs(pnl).toFixed(2)}`
}
</script>

<style scoped>
.position-sync-status {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  padding: 14px 16px;
  transition: all 0.2s ease;
}

.sync-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sync-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 16px;
  transition: all 0.2s ease;
}

.sync-idle .sync-icon {
  background: var(--kite-bg-light, #f8f9fa);
  color: var(--kite-text-secondary, #666);
}

.sync-syncing .sync-icon {
  background: rgba(56, 126, 209, 0.1);
  color: var(--kite-primary, #387ed1);
}

.sync-success .sync-icon {
  background: rgba(0, 179, 134, 0.1);
  color: var(--kite-green, #00b386);
}

.sync-error .sync-icon {
  background: rgba(229, 57, 53, 0.1);
  color: var(--kite-red, #e53935);
}

.pulse {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
}

.sync-content {
  flex: 1;
}

.sync-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin-bottom: 2px;
}

.sync-time {
  font-size: 11px;
  color: var(--kite-text-secondary, #666);
}

.sync-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.detail-label {
  color: var(--kite-text-secondary, #666);
}

.detail-value {
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

.detail-value.pnl-profit {
  color: var(--kite-green, #00b386);
}

.detail-value.pnl-loss {
  color: var(--kite-red, #e53935);
}

.detail-value.health-good {
  color: var(--kite-green, #00b386);
}

.detail-value.health-warning {
  color: #ff9800;
}

.detail-value.health-bad {
  color: var(--kite-red, #e53935);
}

.sync-error {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(229, 57, 53, 0.1);
  border-left: 3px solid var(--kite-red, #e53935);
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--kite-red, #e53935);
}
</style>
