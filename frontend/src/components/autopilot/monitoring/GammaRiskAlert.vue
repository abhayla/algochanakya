<template>
  <div
    v-if="shouldShowAlert"
    class="gamma-risk-alert"
    :class="`risk-${assessment.risk_level}`"
    data-testid="autopilot-gamma-risk-alert"
  >
    <!-- Alert Header -->
    <div class="alert-header">
      <div class="header-left">
        <i :class="`fas fa-${getIcon()}`" class="alert-icon"></i>
        <h4 class="alert-title">Gamma Risk Alert</h4>
      </div>
      <div class="gamma-zone-badge" :class="`zone-${assessment.zone}`">
        {{ formatZone(assessment.zone) }}
      </div>
    </div>

    <!-- Alert Body -->
    <div class="alert-body">
      <!-- Recommendation -->
      <p class="recommendation" data-testid="gamma-risk-recommendation">
        {{ assessment.recommendation }}
      </p>

      <!-- Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">Days to Expiry</span>
          <span class="metric-value" data-testid="gamma-risk-dte">{{ dte }} DTE</span>
        </div>

        <div class="metric-card">
          <span class="metric-label">Gamma Multiplier</span>
          <span class="metric-value multiplier" data-testid="gamma-risk-multiplier">
            {{ assessment.multiplier?.toFixed(1) || '1.0' }}x
          </span>
        </div>

        <div class="metric-card">
          <span class="metric-label">Net Gamma</span>
          <span class="metric-value" data-testid="gamma-risk-net-gamma">
            {{ formatGamma(netGamma) }}
          </span>
        </div>

        <div class="metric-card" v-if="explosionProbability !== null">
          <span class="metric-label">Explosion Risk</span>
          <span class="metric-value probability" data-testid="gamma-risk-probability">
            {{ (explosionProbability * 100).toFixed(0) }}%
          </span>
        </div>
      </div>

      <!-- Risk Level Indicator -->
      <div class="risk-indicator">
        <div class="risk-level-label">Risk Level</div>
        <div class="risk-level-bar">
          <div
            class="risk-level-fill"
            :class="`level-${assessment.risk_level}`"
            :style="{ width: getRiskPercentage() + '%' }"
          ></div>
        </div>
        <div class="risk-level-text" data-testid="gamma-risk-level">
          {{ formatRiskLevel(assessment.risk_level) }}
        </div>
      </div>

      <!-- Position Type Badge -->
      <div class="position-info" v-if="assessment.position_type">
        <i class="fas fa-chart-line"></i>
        <span>{{ formatPositionType(assessment.position_type) }} Position</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GammaRiskAlert',

  props: {
    dte: {
      type: Number,
      required: true
    },
    netGamma: {
      type: Number,
      required: true
    },
    assessment: {
      type: Object,
      required: true,
      // Expected structure from gamma_risk_service.assess_gamma_risk():
      // {
      //   zone: 'safe|warning|danger',
      //   risk_level: 'low|medium|high|critical',
      //   multiplier: number,
      //   recommendation: string,
      //   dte: number,
      //   net_gamma: number,
      //   position_type: 'short|long'
      // }
    },
    explosionProbability: {
      type: Number,
      default: null // 0-1 probability from calculate_gamma_explosion_probability()
    },
    autoHide: {
      type: Boolean,
      default: true // Auto-hide when risk is low
    }
  },

  computed: {
    shouldShowAlert() {
      // Always show if autoHide is disabled
      if (!this.autoHide) return true

      // Hide only when in safe zone with low risk
      return !(this.assessment.zone === 'safe' && this.assessment.risk_level === 'low')
    }
  },

  methods: {
    getIcon() {
      const icons = {
        critical: 'exclamation-circle',
        high: 'exclamation-triangle',
        medium: 'info-circle',
        low: 'check-circle'
      }
      return icons[this.assessment.risk_level] || 'info-circle'
    },

    formatZone(zone) {
      const labels = {
        safe: 'Safe Zone',
        warning: 'Warning Zone',
        danger: 'Danger Zone'
      }
      return labels[zone] || zone
    },

    formatRiskLevel(level) {
      return level ? level.charAt(0).toUpperCase() + level.slice(1) : 'Unknown'
    },

    formatPositionType(type) {
      return type ? type.charAt(0).toUpperCase() + type.slice(1) : ''
    },

    formatGamma(gamma) {
      if (gamma === null || gamma === undefined) return '0.000'
      return gamma.toFixed(3)
    },

    getRiskPercentage() {
      // Convert risk level to percentage for visual bar
      const percentages = {
        low: 25,
        medium: 50,
        high: 75,
        critical: 100
      }
      return percentages[this.assessment.risk_level] || 0
    }
  }
}
</script>

<style scoped>
.gamma-risk-alert {
  background: #ffffff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  border-left: 4px solid #ccc;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Risk Level Colors */
.gamma-risk-alert.risk-low {
  border-left-color: #4caf50;
  background: #f1f8f4;
}

.gamma-risk-alert.risk-medium {
  border-left-color: #2196f3;
  background: #f0f7ff;
}

.gamma-risk-alert.risk-high {
  border-left-color: #ff9800;
  background: #fff8f0;
}

.gamma-risk-alert.risk-critical {
  border-left-color: #f44336;
  background: #fff4f4;
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { border-left-color: #f44336; }
  50% { border-left-color: #d32f2f; }
}

/* Alert Header */
.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-icon {
  font-size: 18px;
}

.risk-low .alert-icon {
  color: #4caf50;
}

.risk-medium .alert-icon {
  color: #2196f3;
}

.risk-high .alert-icon {
  color: #ff9800;
}

.risk-critical .alert-icon {
  color: #f44336;
}

.alert-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

/* Gamma Zone Badge */
.gamma-zone-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.gamma-zone-badge.zone-safe {
  background: #e8f5e9;
  color: #2e7d32;
}

.gamma-zone-badge.zone-warning {
  background: #fff3e0;
  color: #f57c00;
}

.gamma-zone-badge.zone-danger {
  background: #ffebee;
  color: #c62828;
}

/* Alert Body */
.alert-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation {
  font-size: 14px;
  font-weight: 500;
  color: #555;
  margin: 0;
  padding: 10px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
  line-height: 1.5;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

@media (min-width: 768px) {
  .metrics-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
}

.metric-label {
  font-size: 11px;
  color: #666;
  text-transform: uppercase;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #333;
}

.metric-value.multiplier {
  color: #ff6b00;
}

.metric-value.probability {
  color: #d32f2f;
}

/* Risk Indicator */
.risk-indicator {
  margin-top: 4px;
}

.risk-level-label {
  font-size: 11px;
  color: #666;
  text-transform: uppercase;
  font-weight: 500;
  margin-bottom: 6px;
  letter-spacing: 0.3px;
}

.risk-level-bar {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 6px;
}

.risk-level-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.risk-level-fill.level-low {
  background: linear-gradient(90deg, #4caf50, #66bb6a);
}

.risk-level-fill.level-medium {
  background: linear-gradient(90deg, #2196f3, #42a5f5);
}

.risk-level-fill.level-high {
  background: linear-gradient(90deg, #ff9800, #ffa726);
}

.risk-level-fill.level-critical {
  background: linear-gradient(90deg, #f44336, #ef5350);
  animation: pulse-fill 1.5s ease-in-out infinite;
}

@keyframes pulse-fill {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.risk-level-text {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  text-align: center;
}

/* Position Info */
.position-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f9f9f9;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.position-info i {
  color: #888;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .gamma-risk-alert {
    background: #1e1e1e;
    border-color: #333;
  }

  .alert-title {
    color: #e0e0e0;
  }

  .recommendation {
    color: #ccc;
    background: rgba(255, 255, 255, 0.05);
  }

  .metric-card {
    background: #2a2a2a;
    border-color: #444;
  }

  .metric-label {
    color: #999;
  }

  .metric-value {
    color: #e0e0e0;
  }

  .risk-level-label,
  .risk-level-text {
    color: #ccc;
  }

  .risk-level-bar {
    background: #333;
  }

  .position-info {
    background: #2a2a2a;
    color: #999;
  }
}
</style>
