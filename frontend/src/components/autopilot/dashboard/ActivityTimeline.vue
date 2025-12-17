<script setup>
/**
 * Activity Timeline Component (Phase 4)
 *
 * Displays recent orders, adjustments, alerts, and strategy events
 */
import { computed } from 'vue'

const props = defineProps({
  activities: {
    type: Array,
    default: () => []
  },
  maxItems: {
    type: Number,
    default: 10
  }
})

// Event type configuration
const eventConfig = {
  order_placed: { icon: '📝', color: '#3b82f6', label: 'Order Placed' },
  order_filled: { icon: '✅', color: '#10b981', label: 'Order Filled' },
  order_rejected: { icon: '❌', color: '#ef4444', label: 'Order Rejected' },
  strategy_activated: { icon: '🚀', color: '#8b5cf6', label: 'Strategy Activated' },
  strategy_paused: { icon: '⏸️', color: '#f59e0b', label: 'Strategy Paused' },
  strategy_exited: { icon: '🚪', color: '#6b7280', label: 'Strategy Exited' },
  condition_met: { icon: '✓', color: '#10b981', label: 'Condition Met' },
  adjustment_executed: { icon: '🔧', color: '#8b5cf6', label: 'Adjustment' },
  alert_triggered: { icon: '🔔', color: '#f59e0b', label: 'Alert' },
  reentry_triggered: { icon: '🔄', color: '#8b5cf6', label: 'Re-Entry' },
  risk_alert: { icon: '⚠️', color: '#ef4444', label: 'Risk Alert' }
}

// Limited activities
const displayedActivities = computed(() => {
  return props.activities.slice(0, props.maxItems)
})

// Format timestamp
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  // Less than a minute
  if (diff < 60000) {
    return 'Just now'
  }

  // Less than an hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes}m ago`
  }

  // Less than a day
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }

  // Format as time
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

// Get config for event type
const getEventConfig = (eventType) => {
  return eventConfig[eventType] || { icon: '•', color: '#6b7280', label: eventType }
}
</script>

<template>
  <div class="activity-timeline">
    <div class="timeline-header">
      <h3 class="timeline-title">Recent Activity</h3>
      <span class="timeline-count">{{ activities.length }} events</span>
    </div>

    <div v-if="displayedActivities.length === 0" class="empty-state">
      <div class="empty-icon">📭</div>
      <p class="empty-text">No recent activity</p>
      <p class="empty-subtext">Activity will appear here when strategies start executing</p>
    </div>

    <div v-else class="timeline-list">
      <div
        v-for="(activity, index) in displayedActivities"
        :key="activity.id || index"
        class="timeline-item"
      >
        <!-- Icon and Line -->
        <div class="timeline-marker">
          <div
            class="marker-icon"
            :style="{ background: getEventConfig(activity.event_type).color }"
          >
            {{ getEventConfig(activity.event_type).icon }}
          </div>
          <div v-if="index < displayedActivities.length - 1" class="marker-line"></div>
        </div>

        <!-- Content -->
        <div class="timeline-content">
          <div class="content-header">
            <span class="event-label" :style="{ color: getEventConfig(activity.event_type).color }">
              {{ getEventConfig(activity.event_type).label }}
            </span>
            <span class="event-time">{{ formatTime(activity.timestamp || activity.created_at) }}</span>
          </div>

          <div class="event-message">{{ activity.message || activity.description }}</div>

          <!-- Strategy Name -->
          <div v-if="activity.strategy_name" class="event-meta">
            <span class="meta-badge">{{ activity.strategy_name }}</span>
            <span v-if="activity.underlying" class="meta-badge secondary">
              {{ activity.underlying }}
            </span>
          </div>

          <!-- Order Details -->
          <div v-if="activity.order_details" class="event-details">
            <span class="detail-item">
              {{ activity.order_details.transaction_type }}
              {{ activity.order_details.quantity }} × {{ activity.order_details.instrument }}
              @ ₹{{ activity.order_details.price }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activities.length > maxItems" class="timeline-footer">
      <button class="view-all-btn">
        View All Activities ({{ activities.length }})
        <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.activity-timeline {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  max-height: 600px;
  display: flex;
  flex-direction: column;
}

/* Header */
.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}

.timeline-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.timeline-count {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
  background: #f3f4f6;
  padding: 4px 10px;
  border-radius: 12px;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: 15px;
  color: #6b7280;
  margin: 0 0 8px 0;
}

.empty-subtext {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
  max-width: 300px;
}

/* Timeline List */
.timeline-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.timeline-list::-webkit-scrollbar {
  width: 6px;
}

.timeline-list::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 3px;
}

.timeline-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.timeline-list::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.timeline-item {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

/* Marker */
.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.marker-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.marker-line {
  flex: 1;
  width: 2px;
  background: #e5e7eb;
  margin-top: 8px;
  min-height: 20px;
}

/* Content */
.timeline-content {
  flex: 1;
  padding-bottom: 8px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.event-label {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.event-time {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
}

.event-message {
  font-size: 14px;
  color: #374151;
  line-height: 1.5;
  margin-bottom: 8px;
}

.event-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.meta-badge {
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 500;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 4px;
}

.meta-badge.secondary {
  background: #f3f4f6;
  color: #6b7280;
}

.event-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item {
  font-size: 12px;
  color: #6b7280;
  font-family: 'Courier New', monospace;
  background: #f9fafb;
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

/* Footer */
.timeline-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.view-all-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  color: #3b82f6;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.view-all-btn:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

.view-all-btn .icon {
  width: 16px;
  height: 16px;
}
</style>
