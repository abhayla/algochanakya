<template>
  <div
    class="suggestion-card"
    :class="[
      `urgency-${urgency.toLowerCase()}`,
      `category-${category.toLowerCase()}`
    ]"
    data-testid="autopilot-suggestion-card"
  >
    <!-- Card Header -->
    <div class="card-header">
      <div class="header-left">
        <i :class="`fas fa-${getCategoryIcon()}`" class="category-icon"></i>
        <div class="title-section">
          <div class="urgency-badge" :class="`badge-${urgency.toLowerCase()}`">
            {{ urgency }}
          </div>
          <span class="category-label">{{ formatCategory(category) }}</span>
        </div>
      </div>
      <div class="action-type-badge" data-testid="suggestion-action-type">
        {{ formatActionType(suggestionType) }}
      </div>
    </div>

    <!-- Trigger Reason (Main Message) -->
    <h4 class="trigger-reason" data-testid="suggestion-trigger-reason">
      {{ triggerReason }}
    </h4>

    <!-- Description -->
    <p class="description" data-testid="suggestion-description">
      {{ description }}
    </p>

    <!-- Confidence Score -->
    <div v-if="confidence !== null" class="confidence-section">
      <div class="confidence-header">
        <span class="confidence-label">Confidence Score</span>
        <span class="confidence-value" data-testid="suggestion-confidence">{{ Math.round(confidence * 100) }}%</span>
      </div>
      <div class="confidence-bar">
        <div
          class="confidence-fill"
          :style="{ width: `${confidence * 100}%` }"
        ></div>
      </div>
    </div>

    <!-- Action Parameters (Key Details) -->
    <div v-if="hasActionParams" class="action-params" data-testid="suggestion-action-params">
      <h5 class="params-title">Details</h5>
      <div class="params-grid">
        <div
          v-for="(value, key) in displayableParams"
          :key="key"
          class="param-item"
        >
          <span class="param-label">{{ formatParamKey(key) }}</span>
          <span class="param-value">{{ formatParamValue(value) }}</span>
        </div>
      </div>
    </div>

    <!-- Time Frame (if available) -->
    <div v-if="actionParams?.time_frame" class="time-frame">
      <i class="fas fa-clock"></i>
      <span>Suggested timeframe: <strong>{{ actionParams.time_frame }}</strong></span>
    </div>

    <!-- Action Buttons -->
    <div class="card-actions" v-if="!hideActions">
      <button
        @click="handleExecute"
        class="action-btn btn-execute"
        data-testid="suggestion-execute-btn"
        :disabled="executing"
      >
        <i class="fas fa-play"></i>
        {{ executing ? 'Executing...' : 'Execute' }}
      </button>
      <button
        @click="handleDismiss"
        class="action-btn btn-dismiss"
        data-testid="suggestion-dismiss-btn"
        :disabled="dismissing"
      >
        <i class="fas fa-times"></i>
        {{ dismissing ? 'Dismissing...' : 'Dismiss' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SuggestionCard',

  props: {
    suggestionType: {
      type: String,
      required: true,
      // Types: EXIT, SHIFT, ROLL, BREAK, ADD_HEDGE, NO_ACTION
    },
    urgency: {
      type: String,
      required: true,
      // CRITICAL, HIGH, MEDIUM, LOW
    },
    triggerReason: {
      type: String,
      required: true
    },
    description: {
      type: String,
      required: true
    },
    actionParams: {
      type: Object,
      default: () => ({})
    },
    category: {
      type: String,
      default: 'defensive',
      // defensive, offensive, neutral
    },
    confidence: {
      type: Number,
      default: null, // 0-1 probability
    },
    hideActions: {
      type: Boolean,
      default: false
    },
    executing: {
      type: Boolean,
      default: false
    },
    dismissing: {
      type: Boolean,
      default: false
    }
  },

  emits: ['execute', 'dismiss'],

  computed: {
    hasActionParams() {
      return Object.keys(this.displayableParams).length > 0
    },

    displayableParams() {
      // Filter out internal params and only show user-friendly ones
      const excludeKeys = ['reason', 'urgency', 'time_frame', 'execution_mode']
      const params = {}

      for (const [key, value] of Object.entries(this.actionParams)) {
        if (!excludeKeys.includes(key) && value !== null && value !== undefined) {
          // Only show simple types (string, number, boolean)
          if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
            params[key] = value
          }
        }
      }

      return params
    }
  },

  methods: {
    getCategoryIcon() {
      const icons = {
        defensive: 'shield-alt',
        offensive: 'bullseye',
        neutral: 'balance-scale'
      }
      return icons[this.category.toLowerCase()] || 'info-circle'
    },

    formatCategory(category) {
      return category ? category.charAt(0).toUpperCase() + category.slice(1) : 'Neutral'
    },

    formatActionType(type) {
      if (!type) return ''
      return type
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    },

    formatParamKey(key) {
      // Convert snake_case to Title Case
      return key
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    },

    formatParamValue(value) {
      if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No'
      }
      if (typeof value === 'number') {
        // Format numbers with appropriate precision
        if (Math.abs(value) < 1) {
          return value.toFixed(3)
        }
        return value.toFixed(2)
      }
      return String(value)
    },

    handleExecute() {
      this.$emit('execute')
    },

    handleDismiss() {
      this.$emit('dismiss')
    }
  }
}
</script>

<style scoped>
.suggestion-card {
  background: #ffffff;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.suggestion-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* Urgency Border Colors */
.suggestion-card.urgency-critical {
  border-left: 6px solid #f44336;
  background: linear-gradient(to right, #ffebee 0%, #ffffff 5%);
}

.suggestion-card.urgency-high {
  border-left: 6px solid #ff9800;
  background: linear-gradient(to right, #fff3e0 0%, #ffffff 5%);
}

.suggestion-card.urgency-medium {
  border-left: 6px solid #2196f3;
  background: linear-gradient(to right, #e3f2fd 0%, #ffffff 5%);
}

.suggestion-card.urgency-low {
  border-left: 6px solid #4caf50;
  background: linear-gradient(to right, #e8f5e9 0%, #ffffff 5%);
}

/* Card Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.category-icon {
  font-size: 20px;
  color: #666;
}

.category-defensive .category-icon {
  color: #2196f3;
}

.category-offensive .category-icon {
  color: #ff9800;
}

.category-neutral .category-icon {
  color: #4caf50;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Urgency Badge */
.urgency-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-critical {
  background: #ffcdd2;
  color: #c62828;
}

.badge-high {
  background: #ffe0b2;
  color: #e65100;
}

.badge-medium {
  background: #bbdefb;
  color: #1565c0;
}

.badge-low {
  background: #c8e6c9;
  color: #2e7d32;
}

.category-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.action-type-badge {
  padding: 4px 10px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Trigger Reason */
.trigger-reason {
  font-size: 16px;
  font-weight: 600;
  color: #222;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

/* Description */
.description {
  font-size: 14px;
  color: #555;
  line-height: 1.6;
  margin: 0 0 12px 0;
}

/* Confidence Section */
.confidence-section {
  margin-bottom: 12px;
}

.confidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.confidence-label {
  font-size: 11px;
  color: #666;
  text-transform: uppercase;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.confidence-value {
  font-size: 14px;
  font-weight: 700;
  color: #333;
}

.confidence-bar {
  width: 100%;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #66bb6a);
  transition: width 0.3s ease;
}

/* Action Parameters */
.action-params {
  background: #f9f9f9;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.params-title {
  font-size: 11px;
  color: #666;
  text-transform: uppercase;
  font-weight: 600;
  margin: 0 0 10px 0;
  letter-spacing: 0.5px;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

@media (min-width: 768px) {
  .params-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.param-label {
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
  font-weight: 500;
}

.param-value {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

/* Time Frame */
.time-frame {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #fffbeb;
  border: 1px solid #fde047;
  border-radius: 6px;
  font-size: 13px;
  color: #92400e;
  margin-bottom: 12px;
}

.time-frame i {
  color: #f59e0b;
}

/* Action Buttons */
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-execute {
  background: #2196f3;
  color: white;
}

.btn-execute:hover:not(:disabled) {
  background: #1976d2;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(33, 150, 243, 0.3);
}

.btn-dismiss {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #e0e0e0;
}

.btn-dismiss:hover:not(:disabled) {
  background: #e0e0e0;
  color: #333;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .suggestion-card {
    background: #1e1e1e;
    border-color: #333;
  }

  .trigger-reason {
    color: #e0e0e0;
  }

  .description {
    color: #ccc;
  }

  .action-params {
    background: #2a2a2a;
    border-color: #444;
  }

  .param-value,
  .confidence-value {
    color: #e0e0e0;
  }

  .confidence-bar {
    background: #333;
  }

  .action-type-badge {
    background: #2a2a2a;
    border-color: #444;
    color: #ccc;
  }

  .btn-dismiss {
    background: #2a2a2a;
    border-color: #444;
    color: #ccc;
  }

  .btn-dismiss:hover:not(:disabled) {
    background: #333;
    color: #e0e0e0;
  }
}
</style>
