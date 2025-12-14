<template>
  <div class="dte-zone-indicator" data-testid="autopilot-dte-zone-indicator">
    <div class="zone-header">
      <span class="zone-label">DTE Zone</span>
      <div class="zone-badge" :class="`zone-${zoneConfig.zone}`">
        <i :class="`fas fa-${zoneConfig.icon}`"></i>
        {{ zoneConfig.label }}
      </div>
    </div>

    <div class="zone-body">
      <!-- DTE Progress Bar -->
      <div class="dte-progress">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :class="`zone-${zoneConfig.zone}`"
            :style="{ width: `${dteProgress}%` }"
          ></div>
        </div>
        <div class="dte-value">{{ dte }} DTE</div>
      </div>

      <!-- Zone Metrics -->
      <div class="zone-metrics">
        <div class="metric">
          <span class="metric-label">Delta Threshold</span>
          <span class="metric-value">±{{ zoneConfig.delta_warning?.toFixed(2) || '0.00' }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Adjustment Effectiveness</span>
          <span class="metric-value">{{ zoneConfig.adjustment_effectiveness?.percentage || 0 }}%</span>
        </div>
      </div>

      <!-- Warnings -->
      <div v-if="zoneConfig.warnings && zoneConfig.warnings.length > 0" class="zone-warnings">
        <div
          v-for="(warning, index) in zoneConfig.warnings"
          :key="index"
          class="warning-item"
          :class="`severity-${getWarningSeverity(warning)}`"
        >
          <i class="fas fa-exclamation-triangle"></i>
          <span>{{ warning }}</span>
        </div>
      </div>

      <!-- Allowed Actions -->
      <div class="allowed-actions">
        <span class="actions-label">Allowed Actions:</span>
        <div class="action-chips">
          <span
            v-for="action in zoneConfig.allowed_actions"
            :key="action"
            class="action-chip"
          >
            {{ formatActionName(action) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DTEZoneIndicator',

  props: {
    dte: {
      type: Number,
      required: true
    },
    zoneConfig: {
      type: Object,
      required: true,
      // Expected structure from dte_zone_service.get_zone_config():
      // {
      //   zone: 'early|middle|late|expiry_week',
      //   dte: number,
      //   delta_warning: number,
      //   allowed_actions: string[],
      //   adjustment_effectiveness: { rating, percentage, description },
      //   warnings: string[],
      //   display: { color, icon, label, badge_variant }
      // }
    }
  },

  computed: {
    dteProgress() {
      // Calculate progress bar fill based on zone
      // Expiry week (0-7): 100% filled
      // Late (7-14): 75% filled
      // Middle (14-21): 50% filled
      // Early (21+): 25% filled

      if (this.dte <= 7) return 100
      if (this.dte <= 14) return 75
      if (this.dte <= 21) return 50
      return 25
    }
  },

  methods: {
    getWarningSeverity(warning) {
      // Determine severity based on warning content
      const criticalKeywords = ['CRITICAL', 'URGENT', 'EXIT NOW']
      const highKeywords = ['WARNING', 'ALERT']

      const upperWarning = warning.toUpperCase()

      if (criticalKeywords.some(keyword => upperWarning.includes(keyword))) {
        return 'critical'
      }
      if (highKeywords.some(keyword => upperWarning.includes(keyword))) {
        return 'high'
      }
      return 'medium'
    },

    formatActionName(action) {
      // Convert snake_case to Title Case
      return action
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    }
  }
}
</script>

<style scoped>
.dte-zone-indicator {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.zone-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.zone-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.zone-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 600;
}

.zone-badge.zone-early {
  background: #e8f5e9;
  color: #2e7d32;
}

.zone-badge.zone-middle {
  background: #e3f2fd;
  color: #1976d2;
}

.zone-badge.zone-late {
  background: #fff3e0;
  color: #f57c00;
}

.zone-badge.zone-expiry_week {
  background: #ffebee;
  color: #c62828;
}

.dte-progress {
  margin-bottom: 16px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.progress-fill.zone-early {
  background: linear-gradient(90deg, #4caf50, #66bb6a);
}

.progress-fill.zone-middle {
  background: linear-gradient(90deg, #2196f3, #42a5f5);
}

.progress-fill.zone-late {
  background: linear-gradient(90deg, #ff9800, #ffa726);
}

.progress-fill.zone-expiry_week {
  background: linear-gradient(90deg, #f44336, #ef5350);
}

.dte-value {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  text-align: center;
}

.zone-metrics {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 6px;
}

.metric {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: #666;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #333;
}

.zone-warnings {
  margin-bottom: 16px;
}

.warning-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.warning-item:last-child {
  margin-bottom: 0;
}

.warning-item.severity-critical {
  background: #ffebee;
  border-left: 4px solid #c62828;
  color: #c62828;
}

.warning-item.severity-high {
  background: #fff3e0;
  border-left: 4px solid #f57c00;
  color: #f57c00;
}

.warning-item.severity-medium {
  background: #e3f2fd;
  border-left: 4px solid #1976d2;
  color: #1976d2;
}

.warning-item i {
  margin-top: 2px;
  flex-shrink: 0;
}

.allowed-actions {
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
}

.actions-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  display: block;
  margin-bottom: 8px;
}

.action-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-chip {
  padding: 4px 10px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  color: #666;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .dte-zone-indicator {
    background: #1e1e1e;
    border-color: #333;
  }

  .zone-label,
  .metric-value {
    color: #e0e0e0;
  }

  .metric-label,
  .actions-label {
    color: #999;
  }

  .zone-metrics {
    background: #2a2a2a;
  }

  .progress-bar {
    background: #333;
  }

  .action-chip {
    background: #2a2a2a;
    border-color: #444;
    color: #999;
  }
}
</style>
