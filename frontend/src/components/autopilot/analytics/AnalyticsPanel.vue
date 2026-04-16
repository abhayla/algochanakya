<template>
  <div class="analytics-panel">
    <!-- Payoff Chart Section -->
    <div class="payoff-section">
      <div class="section-header">
        <h3>Payoff Chart</h3>
        <div class="mode-toggle" data-testid="autopilot-payoff-mode-toggle">
          <button
            @click="payoffMode = 'expiry'"
            :class="{ active: payoffMode === 'expiry' }"
            class="mode-btn"
            data-testid="autopilot-payoff-mode-expiry"
          >
            At Expiry
          </button>
          <button
            @click="payoffMode = 'current'"
            :class="{ active: payoffMode === 'current' }"
            class="mode-btn"
            data-testid="autopilot-payoff-mode-current"
          >
            <span data-testid="autopilot-payoff-current-label">Current</span>
          </button>
        </div>
      </div>

      <!-- Chart Container -->
      <div class="chart-container" data-testid="autopilot-payoff-chart">
        <canvas ref="chartCanvas" class="payoff-canvas"></canvas>

        <!-- Breakeven Markers (overlay on chart) -->
        <div class="breakeven-markers">
          <div
            v-for="(be, index) in breakevens"
            :key="index"
            class="breakeven-marker"
            :style="{ left: getBreakevenPosition(be) + '%' }"
            :data-testid="`autopilot-payoff-breakeven-${be}`"
          >
            <div class="marker-line"></div>
            <div class="marker-label">
              <span class="marker-title">BE</span>
              <span class="marker-value" data-testid="autopilot-breakeven-value">{{ be }}</span>
            </div>
          </div>
        </div>

        <!-- Tooltip (shown on hover) -->
        <div
          v-if="tooltip.visible"
          class="chart-tooltip"
          :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
          data-testid="autopilot-payoff-tooltip"
        >
          <div class="tooltip-row">
            <span>Spot:</span>
            <strong>{{ tooltip.spot }}</strong>
          </div>
          <div class="tooltip-row">
            <span>P&L:</span>
            <strong :class="tooltip.pnl >= 0 ? 'profit' : 'loss'">
              {{ formatPnL(tooltip.pnl) }}
            </strong>
          </div>
        </div>
      </div>
    </div>

    <!-- Risk Metrics Section -->
    <div class="risk-metrics-section" data-testid="autopilot-risk-metrics">
      <h4>Risk Metrics</h4>
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Max Profit</div>
          <div class="metric-value profit" data-testid="autopilot-max-profit">
            {{ riskMetrics.maxProfit !== null ? formatPnL(riskMetrics.maxProfit) : 'Unlimited' }}
          </div>
          <div class="metric-hint" v-if="riskMetrics.maxProfitAt">
            at {{ riskMetrics.maxProfitAt }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">Max Loss</div>
          <div class="metric-value loss" data-testid="autopilot-max-loss">
            {{ riskMetrics.maxLoss !== null ? formatPnL(riskMetrics.maxLoss) : 'Unlimited' }}
          </div>
          <div class="metric-hint" v-if="riskMetrics.maxLossAt">
            at {{ riskMetrics.maxLossAt }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">Risk/Reward</div>
          <div class="metric-value" data-testid="autopilot-risk-reward">
            {{ riskMetrics.riskRewardRatio?.toFixed(2) || '-' }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">Breakevens</div>
          <div class="metric-value" data-testid="autopilot-breakevens">
            {{ breakevens.length > 0 ? breakevens.join(', ') : 'None' }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">Net Credit</div>
          <div class="metric-value" :class="riskMetrics.netCredit >= 0 ? 'profit' : 'loss'">
            {{ formatPnL(riskMetrics.netCredit || 0) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">P(Profit)</div>
          <div class="metric-value">
            {{ riskMetrics.probabilityOfProfit ? riskMetrics.probabilityOfProfit.toFixed(1) + '%' : '-' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const autopilotStore = useAutopilotStore()

const props = defineProps({
  strategyId: {
    type: Number,
    required: true
  }
})

const chartCanvas = ref(null)
const payoffMode = ref('expiry')
const payoffData = ref(null)
const riskMetrics = ref({
  maxProfit: null,
  maxLoss: null,
  maxProfitAt: null,
  maxLossAt: null,
  riskRewardRatio: null,
  netCredit: 0,
  probabilityOfProfit: null
})
const breakevens = ref([])

const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  spot: 0,
  pnl: 0
})

let chartInstance = null

const fetchPayoffData = async () => {
  const result = await autopilotStore.fetchStrategyPayoff(props.strategyId, {
    mode: payoffMode.value,
    spot_range_pct: 10,
    num_points: 100,
  })

  if (!result.success) {
    console.error('Failed to fetch payoff data:', result.error)
    return
  }

  payoffData.value = result.data.data
  breakevens.value = payoffData.value.breakeven_points || []

  riskMetrics.value = {
    maxProfit: payoffData.value.max_profit,
    maxLoss: payoffData.value.max_loss,
    maxProfitAt: payoffData.value.max_profit_at,
    maxLossAt: payoffData.value.max_loss_at,
    riskRewardRatio: payoffData.value.risk_reward_ratio,
    netCredit: payoffData.value.net_credit,
    probabilityOfProfit: payoffData.value.probability_of_profit,
  }

  await nextTick()
  renderChart()
}

const renderChart = () => {
  if (!chartCanvas.value || !payoffData.value) return

  const ctx = chartCanvas.value.getContext('2d')
  const canvas = chartCanvas.value
  canvas.width = canvas.offsetWidth
  canvas.height = 400

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const spotPrices = payoffData.value.spot_prices
  const pnlValues = payoffData.value.pnl_values
  const currentSpot = payoffData.value.current_spot

  if (!spotPrices || !pnlValues || spotPrices.length === 0) return

  const padding = { top: 40, right: 40, bottom: 40, left: 60 }
  const chartWidth = canvas.width - padding.left - padding.right
  const chartHeight = canvas.height - padding.top - padding.bottom

  // Calculate scales
  const minSpot = Math.min(...spotPrices)
  const maxSpot = Math.max(...spotPrices)
  const minPnl = Math.min(...pnlValues, 0)
  const maxPnl = Math.max(...pnlValues, 0)

  const xScale = (spot) => padding.left + ((spot - minSpot) / (maxSpot - minSpot)) * chartWidth
  const yScale = (pnl) => padding.top + chartHeight - ((pnl - minPnl) / (maxPnl - minPnl)) * chartHeight

  // Draw axes
  ctx.strokeStyle = '#d1d5db'
  ctx.lineWidth = 1

  // X-axis
  ctx.beginPath()
  ctx.moveTo(padding.left, yScale(0))
  ctx.lineTo(canvas.width - padding.right, yScale(0))
  ctx.stroke()

  // Y-axis
  ctx.beginPath()
  ctx.moveTo(padding.left, padding.top)
  ctx.lineTo(padding.left, canvas.height - padding.bottom)
  ctx.stroke()

  // Draw grid lines
  ctx.strokeStyle = '#f3f4f6'
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (chartHeight / 4) * i
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(canvas.width - padding.right, y)
    ctx.stroke()
  }

  // Draw P&L line
  ctx.strokeStyle = '#3b82f6'
  ctx.lineWidth = 2
  ctx.beginPath()
  spotPrices.forEach((spot, i) => {
    const x = xScale(spot)
    const y = yScale(pnlValues[i])
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  ctx.stroke()

  // Fill area
  const gradient = ctx.createLinearGradient(0, padding.top, 0, canvas.height - padding.bottom)
  gradient.addColorStop(0, 'rgba(59, 130, 246, 0.2)')
  gradient.addColorStop(1, 'rgba(59, 130, 246, 0.05)')

  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.moveTo(xScale(spotPrices[0]), yScale(0))
  spotPrices.forEach((spot, i) => {
    ctx.lineTo(xScale(spot), yScale(pnlValues[i]))
  })
  ctx.lineTo(xScale(spotPrices[spotPrices.length - 1]), yScale(0))
  ctx.closePath()
  ctx.fill()

  // Draw current spot line
  if (currentSpot) {
    ctx.strokeStyle = '#f59e0b'
    ctx.lineWidth = 2
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(xScale(currentSpot), padding.top)
    ctx.lineTo(xScale(currentSpot), canvas.height - padding.bottom)
    ctx.stroke()
    ctx.setLineDash([])

    // Current spot label
    ctx.fillStyle = '#f59e0b'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Current', xScale(currentSpot), padding.top - 10)
  }

  // Y-axis labels
  ctx.fillStyle = '#6b7280'
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'right'
  for (let i = 0; i <= 4; i++) {
    const pnl = minPnl + ((maxPnl - minPnl) / 4) * i
    const y = yScale(pnl)
    ctx.fillText(formatPnL(pnl), padding.left - 10, y + 4)
  }

  // X-axis labels
  ctx.textAlign = 'center'
  for (let i = 0; i <= 4; i++) {
    const spot = minSpot + ((maxSpot - minSpot) / 4) * i
    const x = xScale(spot)
    ctx.fillText(Math.round(spot), x, canvas.height - padding.bottom + 20)
  }
}

const getBreakevenPosition = (breakeven) => {
  if (!payoffData.value) return 0
  const spotPrices = payoffData.value.spot_prices
  if (!spotPrices || spotPrices.length === 0) return 0

  const minSpot = Math.min(...spotPrices)
  const maxSpot = Math.max(...spotPrices)
  const position = ((breakeven - minSpot) / (maxSpot - minSpot)) * 100
  return Math.max(5, Math.min(95, position)) // Clamp between 5% and 95%
}

const formatPnL = (pnl) => {
  if (pnl === null || pnl === undefined) return '₹0'
  const prefix = pnl >= 0 ? '+' : ''
  return `${prefix}₹${pnl.toFixed(0)}`
}

onMounted(() => {
  fetchPayoffData()
})

watch(payoffMode, () => {
  fetchPayoffData()
})
</script>

<style scoped>
.analytics-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.payoff-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.section-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.mode-toggle {
  display: flex;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  overflow: hidden;
}

.mode-btn {
  padding: 8px 16px;
  border: none;
  background: white;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn:not(:last-child) {
  border-right: 1px solid #d1d5db;
}

.mode-btn:hover {
  background: #f9fafb;
}

.mode-btn.active {
  background: #3b82f6;
  color: white;
}

.chart-container {
  position: relative;
  padding: 24px;
}

.payoff-canvas {
  width: 100%;
  display: block;
}

.breakeven-markers {
  position: absolute;
  top: 64px;
  left: 84px;
  right: 64px;
  bottom: 64px;
  pointer-events: none;
}

.breakeven-marker {
  position: absolute;
  top: 0;
  bottom: 0;
}

.marker-line {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 2px;
  background: #16a34a;
  opacity: 0.6;
}

.marker-label {
  position: absolute;
  top: -30px;
  left: -30px;
  background: #16a34a;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.marker-title {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 9px;
  letter-spacing: 0.5px;
}

.marker-value {
  font-weight: 700;
  font-size: 12px;
}

.chart-tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  pointer-events: none;
  z-index: 10;
  transform: translate(-50%, -100%);
  margin-top: -10px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.tooltip-row:not(:last-child) {
  margin-bottom: 6px;
}

.tooltip-row span {
  color: #d1d5db;
}

.tooltip-row strong {
  font-weight: 600;
}

.tooltip-row .profit {
  color: #86efac;
}

.tooltip-row .loss {
  color: #fca5a5;
}

.risk-metrics-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

.risk-metrics-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 20px 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.metric-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.metric-value.profit {
  color: #16a34a;
}

.metric-value.loss {
  color: #dc2626;
}

.metric-hint {
  font-size: 11px;
  color: #9ca3af;
}
</style>
