<script setup>
/**
 * Activity Timeline Component (Phase 4)
 *
 * Displays recent orders, adjustments, alerts, and strategy events
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const props = defineProps({
  activities: {
    type: Array,
    default: () => []
  },
  maxItems: {
    type: Number,
    default: 10
  },
  isRealtime: {
    type: Boolean,
    default: false
  },
  groupByStrategy: {
    type: Boolean,
    default: false
  }
})

// Filter state
const selectedFilter = ref('all')

// Navigate to activity logs page
const viewAllActivities = () => {
  router.push('/autopilot/activity')
}

// Event type configuration
const eventConfig = {
  order_placed: { icon: '📝', color: '#3b82f6', label: 'Order Placed', category: 'orders' },
  order_filled: { icon: '✅', color: '#10b981', label: 'Order Filled', category: 'orders' },
  order_rejected: { icon: '❌', color: '#ef4444', label: 'Order Rejected', category: 'orders' },
  strategy_activated: { icon: '🚀', color: '#8b5cf6', label: 'Strategy Activated', category: 'events' },
  strategy_paused: { icon: '⏸️', color: '#f59e0b', label: 'Strategy Paused', category: 'events' },
  strategy_exited: { icon: '🚪', color: '#6b7280', label: 'Strategy Exited', category: 'events' },
  condition_met: { icon: '✓', color: '#10b981', label: 'Condition Met', category: 'events' },
  adjustment_executed: { icon: '🔧', color: '#8b5cf6', label: 'Adjustment', category: 'adjustments' },
  alert_triggered: { icon: '🔔', color: '#f59e0b', label: 'Alert', category: 'alerts' },
  reentry_triggered: { icon: '🔄', color: '#8b5cf6', label: 'Re-Entry', category: 'adjustments' },
  risk_alert: { icon: '⚠️', color: '#ef4444', label: 'Risk Alert', category: 'alerts' }
}

// Filter activities by selected filter
const filteredActivities = computed(() => {
  if (selectedFilter.value === 'all') return props.activities

  return props.activities.filter(activity => {
    const config = getEventConfig(activity.event_type)
    return config.category === selectedFilter.value
  })
})

// Group activities by strategy
const groupedActivities = computed(() => {
  if (!props.groupByStrategy) return filteredActivities.value

  const groups = {}
  filteredActivities.value.forEach(activity => {
    const strategyName = activity.strategy_name || 'General'
    if (!groups[strategyName]) {
      groups[strategyName] = []
    }
    groups[strategyName].push(activity)
  })

  return groups
})

// Limited activities
const displayedActivities = computed(() => {
  if (props.groupByStrategy) {
    // For grouped view, return grouped object limited per group
    const limited = {}
    Object.keys(groupedActivities.value).forEach(strategyName => {
      limited[strategyName] = groupedActivities.value[strategyName].slice(0, props.maxItems)
    })
    return limited
  }

  return filteredActivities.value.slice(0, props.maxItems)
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
  <div class="activity-timeline" data-testid="autopilot-activity-timeline">
    <div class="timeline-header" data-testid="autopilot-timeline-header">
      <div class="header-left">
        <h3 class="timeline-title">Recent Activity</h3>
        <!-- Real-time Indicator -->
        <span v-if="isRealtime" class="realtime-indicator" data-testid="autopilot-activity-realtime-indicator">
          <span class="realtime-dot"></span>
          <span class="realtime-text">Live</span>
        </span>
      </div>
      <div class="header-right">
        <!-- Filter Dropdown -->
        <select
          v-model="selectedFilter"
          class="filter-select"
          data-testid="autopilot-activity-filter"
        >
          <option value="all">All</option>
          <option value="orders">Orders</option>
          <option value="adjustments">Adjustments</option>
          <option value="alerts">Alerts</option>
          <option value="events">Events</option>
        </select>
        <span class="timeline-count" data-testid="autopilot-timeline-count">{{ filteredActivities.length }} events</span>
      </div>
    </div>

    <div v-if="(groupByStrategy ? Object.keys(displayedActivities).length === 0 : displayedActivities.length === 0)" class="empty-state" data-testid="autopilot-timeline-empty-state">
      <div class="empty-icon">📭</div>
      <p class="empty-text">No recent activity</p>
      <p class="empty-subtext">Activity will appear here when strategies start executing</p>
    </div>

    <!-- Grouped View -->
    <div v-else-if="groupByStrategy" class="timeline-list">
      <div
        v-for="(strategyActivities, strategyName) in displayedActivities"
        :key="strategyName"
        class="strategy-group"
      >
        <div class="group-header" :data-testid="`autopilot-activity-strategy-group-${strategyName}`">
          <span class="group-icon">📊</span>
          <span class="group-name">{{ strategyName }}</span>
          <span class="group-count">{{ strategyActivities.length }}</span>
        </div>

        <div class="group-items">
          <div
            v-for="(activity, index) in strategyActivities"
            :key="activity.id || index"
            class="timeline-item"
            :data-testid="'autopilot-timeline-item-' + (activity.id || index)"
          >
            <!-- Icon and Line -->
            <div class="timeline-marker">
              <div
                class="marker-icon"
                data-testid="autopilot-timeline-marker-icon"
                :style="{ background: getEventConfig(activity.event_type).color }"
              >
                {{ getEventConfig(activity.event_type).icon }}
              </div>
              <div v-if="index < strategyActivities.length - 1" class="marker-line"></div>
            </div>

            <!-- Content -->
            <div class="timeline-content">
              <div class="content-header">
                <span class="event-label" :style="{ color: getEventConfig(activity.event_type).color }">
                  {{ getEventConfig(activity.event_type).label }}
                </span>
                <span class="event-time" data-testid="autopilot-timeline-event-time">{{ formatTime(activity.timestamp || activity.created_at) }}</span>
              </div>

              <div class="event-message" data-testid="autopilot-timeline-event-message">{{ activity.message || activity.description }}</div>

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
      </div>
    </div>

    <!-- Regular Ungrouped View -->
    <div v-else class="timeline-list">
      <div
        v-for="(activity, index) in displayedActivities"
        :key="activity.id || index"
        class="timeline-item"
        :data-testid="'autopilot-timeline-item-' + (activity.id || index)"
      >
        <!-- Icon and Line -->
        <div class="timeline-marker">
          <div
            class="marker-icon"
            data-testid="autopilot-timeline-marker-icon"
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
            <span class="event-time" data-testid="autopilot-timeline-event-time">{{ formatTime(activity.timestamp || activity.created_at) }}</span>
          </div>

          <div class="event-message" data-testid="autopilot-timeline-event-message">{{ activity.message || activity.description }}</div>

          <!-- Strategy Name -->
          <div v-if="activity.strategy_name" class="event-meta" data-testid="autopilot-timeline-event-meta">
            <span class="meta-badge" data-testid="autopilot-timeline-meta-badge">{{ activity.strategy_name }}</span>
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
      <button class="view-all-btn" data-testid="autopilot-timeline-view-all-btn" @click="viewAllActivities">
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

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
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

/* Real-time Indicator */
.realtime-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #dcfce7;
  border-radius: 12px;
}

.realtime-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.realtime-text {
  font-size: 11px;
  font-weight: 600;
  color: #059669;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Filter Select */
.filter-select {
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-select:hover {
  border-color: #3b82f6;
}

.filter-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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

/* Grouped View */
.strategy-group {
  margin-bottom: 24px;
}

.strategy-group:last-child {
  margin-bottom: 0;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid #d1d5db;
}

.group-icon {
  font-size: 16px;
}

.group-name {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.group-count {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: white;
  padding: 3px 8px;
  border-radius: 10px;
}

.group-items {
  padding-left: 8px;
}
</style>
