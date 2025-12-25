<template>
  <div class="ai-activity-feed" data-testid="ai-activity-feed">
    <div class="feed-header">
      <h3 class="feed-title">AI Activity</h3>
      <button v-if="activities.length > 0" class="btn-clear" @click="$emit('clear')" data-testid="btn-clear">
        <i class="fas fa-trash-alt"></i>
      </button>
    </div>

    <div v-if="activities.length === 0" class="empty-state" data-testid="empty-state">
      <i class="fas fa-robot"></i>
      <p>No AI activity yet</p>
      <span>AI decisions and alerts will appear here</span>
    </div>

    <div v-else class="activity-list" data-testid="activity-list">
      <div
        v-for="activity in sortedActivities"
        :key="activity.id"
        class="activity-item"
        :class="`activity-${activity.type}`"
        data-testid="activity-item"
      >
        <div class="activity-icon" :class="`icon-${activity.type}`">
          <i :class="getActivityIcon(activity.type)"></i>
        </div>

        <div class="activity-content">
          <div class="activity-header">
            <span class="activity-type">{{ formatActivityType(activity.type) }}</span>
            <span class="activity-time">{{ formatTime(activity.timestamp) }}</span>
          </div>

          <div class="activity-message" data-testid="activity-message">
            {{ activity.message }}
          </div>

          <div v-if="activity.metadata" class="activity-metadata">
            <span v-for="(value, key) in activity.metadata" :key="key" class="metadata-tag">
              {{ key }}: {{ value }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activities.length > maxVisible" class="feed-footer">
      <button class="btn-show-more" @click="showAll = !showAll" data-testid="btn-show-more">
        {{ showAll ? 'Show Less' : `Show ${activities.length - maxVisible} More` }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  activities: {
    type: Array,
    default: () => []
  },
  maxVisible: {
    type: Number,
    default: 5
  }
})

defineEmits(['clear'])

const showAll = ref(false)

const sortedActivities = computed(() => {
  const sorted = [...props.activities].sort((a, b) => {
    return new Date(b.timestamp) - new Date(a.timestamp)
  })

  if (showAll.value) {
    return sorted
  }

  return sorted.slice(0, props.maxVisible)
})

const getActivityIcon = (type) => {
  const icons = {
    regime_change: 'fas fa-exchange-alt',
    strategy_selected: 'fas fa-chess-knight',
    order_placed: 'fas fa-shopping-cart',
    order_filled: 'fas fa-check-circle',
    position_entry: 'fas fa-door-open',
    position_exit: 'fas fa-door-closed',
    adjustment: 'fas fa-sliders',
    health_alert: 'fas fa-exclamation-triangle',
    sync_complete: 'fas fa-sync-alt',
    error: 'fas fa-times-circle',
    info: 'fas fa-info-circle'
  }

  return icons[type] || 'fas fa-robot'
}

const formatActivityType = (type) => {
  return type
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, l => l.toUpperCase())
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''

  const date = new Date(timestamp)
  const now = new Date()
  const diff = Math.floor((now - date) / 1000)

  if (diff < 10) {
    return 'Just now'
  } else if (diff < 60) {
    return `${diff}s ago`
  } else if (diff < 3600) {
    const mins = Math.floor(diff / 60)
    return `${mins}m ago`
  } else if (diff < 86400) {
    const hours = Math.floor(diff / 3600)
    return `${hours}h ago`
  } else {
    return date.toLocaleString('en-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}
</script>

<style scoped>
.ai-activity-feed {
  background: white;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 8px;
  overflow: hidden;
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
}

.feed-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.btn-clear {
  padding: 6px 10px;
  background: transparent;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  color: var(--kite-text-secondary, #666);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-clear:hover {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-red, #e53935);
  color: var(--kite-red, #e53935);
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--kite-text-secondary, #666);
}

.empty-state i {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.3;
}

.empty-state p {
  font-size: 15px;
  font-weight: 500;
  margin: 0 0 4px 0;
}

.empty-state span {
  font-size: 12px;
  opacity: 0.7;
}

.activity-list {
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
  transition: background 0.2s ease;
}

.activity-item:hover {
  background: var(--kite-bg-light, #f8f9fa);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 14px;
  flex-shrink: 0;
}

.icon-regime_change,
.icon-strategy_selected {
  background: rgba(56, 126, 209, 0.1);
  color: var(--kite-primary, #387ed1);
}

.icon-order_placed,
.icon-order_filled,
.icon-position_entry {
  background: rgba(0, 179, 134, 0.1);
  color: var(--kite-green, #00b386);
}

.icon-position_exit {
  background: rgba(229, 57, 53, 0.1);
  color: var(--kite-red, #e53935);
}

.icon-adjustment,
.icon-sync_complete,
.icon-info {
  background: rgba(255, 152, 0, 0.1);
  color: #ff9800;
}

.icon-health_alert,
.icon-error {
  background: rgba(229, 57, 53, 0.1);
  color: var(--kite-red, #e53935);
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.activity-type {
  font-size: 12px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.activity-time {
  font-size: 11px;
  color: var(--kite-text-secondary, #999);
}

.activity-message {
  font-size: 13px;
  color: var(--kite-text-primary, #394046);
  line-height: 1.4;
  margin-bottom: 6px;
}

.activity-metadata {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.metadata-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--kite-bg-light, #f8f9fa);
  border-radius: 10px;
  color: var(--kite-text-secondary, #666);
}

.feed-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--kite-border, #e8e8e8);
  text-align: center;
}

.btn-show-more {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  color: var(--kite-primary, #387ed1);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-show-more:hover {
  background: var(--kite-bg-light, #f8f9fa);
  border-color: var(--kite-primary, #387ed1);
}
</style>
