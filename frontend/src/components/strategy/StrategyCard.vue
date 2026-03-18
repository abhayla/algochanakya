<template>
  <div
    :class="['strategy-card', { 'in-comparison': inComparison }]"
    @click="$emit('click')"
    :data-testid="`strategy-card-${template.name}`"
  >
    <!-- Category Badge -->
    <div
      class="category-badge"
      :style="{ background: categoryColor }"
      :data-testid="`strategy-card-${template.name}-category`"
    >
      {{ categoryIcon }} {{ categoryName }}
    </div>

    <!-- Card Content -->
    <div class="card-content">
      <h3 class="strategy-name" :data-testid="`strategy-card-${template.name}-name`">{{ template.display_name }}</h3>
      <p class="strategy-desc">{{ template.description }}</p>

      <!-- Match Reasons (for recommendations) -->
      <div v-if="matchReasons && matchReasons.length" class="match-reasons">
        <div v-for="reason in matchReasons" :key="reason" class="reason">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 13l4 4L19 7"/>
          </svg>
          {{ reason }}
        </div>
      </div>

      <!-- Metrics -->
      <div class="metrics">
        <div class="metric">
          <span class="label">Max Profit</span>
          <span class="value profit" :title="formatMetric(template.max_profit)" :data-testid="`strategy-card-${template.name}-max-profit`">{{ formatMetric(template.max_profit) }}</span>
        </div>
        <div class="metric">
          <span class="label">Max Loss</span>
          <span class="value loss" :title="formatMetric(template.max_loss)" :data-testid="`strategy-card-${template.name}-max-loss`">{{ formatMetric(template.max_loss) }}</span>
        </div>
        <div class="metric">
          <span class="label">Win Rate</span>
          <span class="value" :title="template.win_probability || '--'" :data-testid="`strategy-card-${template.name}-win-probability`">{{ template.win_probability || '--' }}</span>
        </div>
      </div>

      <!-- Tags -->
      <div class="tags">
        <span :class="['tag', `risk-${template.risk_level}`]" :title="riskTooltip" :data-testid="`strategy-card-${template.name}-risk-level`">
          {{ template.risk_level }} risk
        </span>
        <span v-if="template.theta_positive" class="tag theta" :data-testid="`strategy-card-${template.name}-theta`">
          Theta+
        </span>
        <span v-if="template.delta_neutral" class="tag neutral" :data-testid="`strategy-card-${template.name}-delta`">
          Delta Neutral
        </span>
        <span :class="['tag', `level-${template.difficulty_level}`]">
          {{ template.difficulty_level }}
        </span>
      </div>

      <!-- Legs Preview -->
      <div class="legs-preview">
        <span class="legs-count">{{ template.legs_config?.length || 0 }} legs:</span>
        <div class="legs-visual">
          <span
            v-for="(leg, idx) in template.legs_config?.slice(0, 4)"
            :key="idx"
            :class="['leg-dot', leg.position.toLowerCase(), leg.type.toLowerCase()]"
            :title="`${leg.position} ${leg.type}`"
          ></span>
        </div>
      </div>
    </div>

    <!-- Card Actions -->
    <div class="card-actions" @click.stop>
      <button class="action-btn details" @click="$emit('click')" title="View Details" :data-testid="`strategy-card-${template.name}-view-details`">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16v-4m0-4h.01"/>
        </svg>
      </button>
      <button
        :class="['action-btn', 'compare', { active: inComparison }]"
        @click="$emit('compare')"
        title="Add to Compare"
        :data-testid="`strategy-card-${template.name}-compare`"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
        </svg>
      </button>
      <button class="action-btn deploy primary" @click="$emit('deploy')" title="Deploy Strategy" :data-testid="`strategy-card-${template.name}-deploy`">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12l5 5L20 7"/>
        </svg>
        Deploy
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useStrategyLibraryStore } from '@/stores/strategyLibrary'

const props = defineProps({
  template: {
    type: Object,
    required: true
  },
  matchReasons: {
    type: Array,
    default: null
  },
  inComparison: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click', 'deploy', 'compare'])

const store = useStrategyLibraryStore()

const categoryConfig = computed(() => store.categoryConfig[props.template.category] || {})
const categoryColor = computed(() => categoryConfig.value.color || '#6c757d')
const categoryIcon = computed(() => categoryConfig.value.icon || '')
const categoryName = computed(() => categoryConfig.value.name || props.template.category)

const RISK_TOOLTIPS = {
  low: 'Low risk: Limited and defined maximum loss',
  medium: 'Medium risk: Moderate loss potential, requires active monitoring',
  high: 'High risk: Significant or unlimited loss potential',
}

const riskTooltip = computed(() => RISK_TOOLTIPS[props.template.risk_level] || '')

function formatMetric(value) {
  if (!value) return '--'
  if (value.length > 20) {
    return value.substring(0, 17) + '...'
  }
  return value
}
</script>

<style scoped>
.strategy-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s ease;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}

.strategy-card:hover {
  border-color: #adb5bd;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.strategy-card.in-comparison {
  border-color: #387ed1;
  box-shadow: 0 0 0 2px rgba(56, 126, 209, 0.2);
}

/* Category Badge */
.category-badge {
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Card Content */
.card-content {
  padding: 16px;
  flex: 1;
}

.strategy-name {
  font-size: 16px;
  font-weight: 600;
  color: #212529;
  margin: 0 0 8px;
}

.strategy-desc {
  font-size: 13px;
  color: #6c757d;
  line-height: 1.5;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Match Reasons */
.match-reasons {
  margin-bottom: 12px;
}

.reason {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #00b386;
  margin-bottom: 4px;
}

.reason svg {
  width: 14px;
  height: 14px;
}

/* Metrics */
.metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.metric {
  text-align: center;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 6px;
}

.metric .label {
  display: block;
  font-size: 10px;
  color: #6c757d;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.metric .value {
  font-size: 12px;
  font-weight: 600;
  color: #212529;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric .value.profit {
  color: #00b386;
}

.metric .value.loss {
  color: #e74c3c;
}

/* Tags */
.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
}

.tag.risk-low {
  background: #d4edda;
  color: #155724;
}

.tag.risk-medium {
  background: #fff3cd;
  color: #856404;
}

.tag.risk-high {
  background: #f8d7da;
  color: #721c24;
}

.tag.theta {
  background: #e2f0ff;
  color: #0056b3;
}

.tag.neutral {
  background: #e9ecef;
  color: #495057;
}

.tag.level-beginner {
  background: #d4edda;
  color: #155724;
}

.tag.level-intermediate {
  background: #fff3cd;
  color: #856404;
}

.tag.level-advanced {
  background: #f8d7da;
  color: #721c24;
}

/* Legs Preview */
.legs-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #6c757d;
}

.legs-visual {
  display: flex;
  gap: 4px;
}

.leg-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.leg-dot.buy.ce {
  background: #00b386;
}

.leg-dot.sell.ce {
  background: #e74c3c;
}

.leg-dot.buy.pe {
  background: #00b386;
}

.leg-dot.sell.pe {
  background: #e74c3c;
}

/* Card Actions */
.card-actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 12px;
  color: #495057;
  background: white;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn.compare.active {
  background: #387ed1;
  border-color: #387ed1;
  color: white;
}

.action-btn.deploy.primary {
  background: #387ed1;
  border-color: #387ed1;
  color: white;
  margin-left: auto;
}

.action-btn.deploy.primary:hover {
  background: #2c5aa0;
}
</style>
