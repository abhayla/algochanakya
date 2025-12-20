<template>
  <div
    class="batch-card"
    :data-testid="`autopilot-order-batch-${batch.id}`"
  >
    <!-- Collapsed Header -->
    <div
      class="batch-header"
      @click="toggleExpanded"
      data-testid="autopilot-order-batch-header"
    >
      <!-- Mode Indicator -->
      <div class="mode-indicator-wrapper">
        <span
          class="mode-dot"
          :class="batch.trading_mode === 'live' ? 'mode-live' : 'mode-paper'"
          :title="batch.trading_mode === 'live' ? 'Live Trading' : 'Paper Trading'"
        ></span>
      </div>

      <!-- Timestamp -->
      <div class="batch-time">
        <span class="time-primary">{{ formatTime(batch.created_at) }}</span>
        <span class="time-secondary">{{ formatDate(batch.created_at) }}</span>
      </div>

      <!-- Purpose Badge -->
      <div class="batch-purpose">
        <span
          class="purpose-badge"
          :class="`purpose-${batch.purpose}`"
        >
          {{ formatPurpose(batch.purpose) }}
        </span>
      </div>

      <!-- Strategy Name (optional) -->
      <div v-if="showStrategyName" class="batch-strategy">
        {{ batch.strategy_name || `Strategy #${batch.strategy_id}` }}
      </div>

      <!-- Leg Count -->
      <div class="batch-legs">
        <span class="leg-count">{{ batch.total_orders }} {{ batch.total_orders === 1 ? 'Leg' : 'Legs' }}</span>
      </div>

      <!-- Net P/L -->
      <div class="batch-pnl">
        <span
          class="pnl-value"
          :class="getPnlClass(batch.net_pnl)"
        >
          {{ formatPnl(batch.net_pnl) }}
        </span>
      </div>

      <!-- Expand/Collapse Icon -->
      <div class="batch-toggle">
        <span class="chevron" :class="{ 'chevron-expanded': isExpanded }">
          &#9662;
        </span>
      </div>
    </div>

    <!-- Expanded Details -->
    <transition name="expand">
      <div
        v-if="isExpanded"
        class="batch-details"
        data-testid="autopilot-order-batch-details"
      >
        <!-- Triggered Condition -->
        <div v-if="batch.triggered_condition" class="detail-section">
          <h4 class="section-title">Triggered Condition</h4>
          <div class="condition-info">
            <div class="condition-item">
              <span class="condition-label">Type:</span>
              <span class="condition-value">{{ batch.triggered_condition.type || 'N/A' }}</span>
            </div>
            <div class="condition-item">
              <span class="condition-label">Condition:</span>
              <span class="condition-value">{{ batch.triggered_condition.expression || 'N/A' }}</span>
            </div>
            <div v-if="batch.trigger_value" class="condition-item">
              <span class="condition-label">Trigger Value:</span>
              <span class="condition-value">{{ JSON.stringify(batch.trigger_value) }}</span>
            </div>
          </div>
        </div>

        <!-- Market Snapshot -->
        <div class="detail-section">
          <h4 class="section-title">Market Snapshot</h4>
          <div class="snapshot-grid">
            <div class="snapshot-item">
              <span class="snapshot-label">Spot Price</span>
              <span class="snapshot-value">{{ formatNumber(batch.spot_price) }}</span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">VIX</span>
              <span class="snapshot-value">{{ formatNumber(batch.vix, 2) }}</span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">Net Delta</span>
              <span class="snapshot-value">{{ formatNumber(batch.net_delta, 4) }}</span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">Net Gamma</span>
              <span class="snapshot-value">{{ formatNumber(batch.net_gamma, 6) }}</span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">Net Theta</span>
              <span class="snapshot-value">{{ formatNumber(batch.net_theta, 2) }}</span>
            </div>
            <div class="snapshot-item">
              <span class="snapshot-label">Net Vega</span>
              <span class="snapshot-value">{{ formatNumber(batch.net_vega, 4) }}</span>
            </div>
          </div>
        </div>

        <!-- Order Legs Table -->
        <div class="detail-section">
          <h4 class="section-title">Order Legs</h4>
          <div class="legs-table-wrapper">
            <table class="legs-table">
              <thead>
                <tr>
                  <th>Instrument</th>
                  <th>Type</th>
                  <th>Qty</th>
                  <th>Entry Price</th>
                  <th>Exit Price</th>
                  <th>Slippage</th>
                  <th>Delta</th>
                  <th>Gamma</th>
                  <th>Theta</th>
                  <th>Vega</th>
                  <th>Status</th>
                  <th>P&L</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(order, index) in batch.orders"
                  :key="order.id"
                  :data-testid="`autopilot-order-leg-${index}`"
                >
                  <td class="leg-instrument">{{ order.tradingsymbol }}</td>
                  <td class="leg-type">
                    <span :class="order.contract_type === 'CE' ? 'type-ce' : 'type-pe'">
                      {{ order.contract_type }}
                    </span>
                  </td>
                  <td class="leg-qty">{{ order.quantity }}</td>
                  <td class="leg-price">{{ formatNumber(order.entry_price, 2) }}</td>
                  <td class="leg-price">{{ order.exit_price ? formatNumber(order.exit_price, 2) : '-' }}</td>
                  <td class="leg-slippage">{{ formatNumber(order.slippage, 2) }}</td>
                  <td class="leg-greek">{{ formatNumber(order.delta_at_order, 4) }}</td>
                  <td class="leg-greek">{{ formatNumber(order.gamma_at_order, 6) }}</td>
                  <td class="leg-greek">{{ formatNumber(order.theta_at_order, 2) }}</td>
                  <td class="leg-greek">{{ formatNumber(order.vega_at_order, 4) }}</td>
                  <td class="leg-status">
                    <span
                      class="status-badge"
                      :class="`status-${order.status.toLowerCase()}`"
                    >
                      {{ order.status }}
                    </span>
                  </td>
                  <td class="leg-pnl">
                    <span :class="getPnlClass(order.pnl)">
                      {{ formatPnl(order.pnl) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Batch Stats Footer -->
        <div class="batch-stats">
          <div class="stat-item">
            <span class="stat-label">Status:</span>
            <span class="stat-value">{{ batch.status }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Completed:</span>
            <span class="stat-value">{{ batch.completed_orders }} / {{ batch.total_orders }}</span>
          </div>
          <div v-if="batch.failed_orders > 0" class="stat-item stat-failed">
            <span class="stat-label">Failed:</span>
            <span class="stat-value">{{ batch.failed_orders }}</span>
          </div>
          <div v-if="batch.total_slippage" class="stat-item">
            <span class="stat-label">Total Slippage:</span>
            <span class="stat-value">{{ formatNumber(batch.total_slippage, 2) }}</span>
          </div>
          <div v-if="batch.execution_duration_ms" class="stat-item">
            <span class="stat-label">Execution Time:</span>
            <span class="stat-value">{{ batch.execution_duration_ms }}ms</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  batch: {
    type: Object,
    required: true
  },
  showStrategyName: {
    type: Boolean,
    default: false
  }
})

const isExpanded = ref(false)

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

const formatTime = (timestamp) => {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

const formatDate = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const formatPurpose = (purpose) => {
  const purposeMap = {
    entry: 'Entry',
    adjustment: 'Adjustment',
    hedge: 'Hedge',
    exit: 'Exit',
    roll_close: 'Roll Close',
    roll_open: 'Roll Open',
    kill_switch: 'Kill Switch'
  }
  return purposeMap[purpose] || purpose
}

const formatNumber = (value, decimals = 2) => {
  if (value === null || value === undefined) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  return num.toFixed(decimals)
}

const formatPnl = (pnl) => {
  if (pnl === null || pnl === undefined) return '₹0.00'
  const num = typeof pnl === 'string' ? parseFloat(pnl) : pnl
  if (isNaN(num)) return '₹0.00'
  const sign = num >= 0 ? '+' : ''
  return `${sign}₹${num.toFixed(2)}`
}

const getPnlClass = (pnl) => {
  if (pnl === null || pnl === undefined) return 'pnl-neutral'
  const num = typeof pnl === 'string' ? parseFloat(pnl) : pnl
  if (isNaN(num) || num === 0) return 'pnl-neutral'
  return num > 0 ? 'pnl-positive' : 'pnl-negative'
}
</script>

<style scoped>
.batch-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.batch-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Header */
.batch-header {
  display: grid;
  grid-template-columns: 40px 100px 120px 1fr 80px 120px 40px;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.batch-header:hover {
  background-color: #f9fafb;
}

.mode-indicator-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.mode-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.mode-live {
  background-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.mode-paper {
  background-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
}

.batch-time {
  display: flex;
  flex-direction: column;
}

.time-primary {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.time-secondary {
  font-size: 12px;
  color: #6b7280;
}

.batch-purpose {
  display: flex;
  align-items: center;
}

.purpose-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.purpose-entry {
  background-color: #dbeafe;
  color: #1e40af;
}

.purpose-adjustment {
  background-color: #fef3c7;
  color: #92400e;
}

.purpose-hedge {
  background-color: #e0e7ff;
  color: #3730a3;
}

.purpose-exit {
  background-color: #fee2e2;
  color: #991b1b;
}

.purpose-roll_close,
.purpose-roll_open {
  background-color: #e0f2fe;
  color: #075985;
}

.purpose-kill_switch {
  background-color: #fecaca;
  color: #7f1d1d;
}

.batch-strategy {
  font-size: 14px;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.batch-legs {
  text-align: center;
}

.leg-count {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.batch-pnl {
  text-align: right;
}

.pnl-value {
  font-size: 15px;
  font-weight: 700;
}

.pnl-positive {
  color: #10b981;
}

.pnl-negative {
  color: #ef4444;
}

.pnl-neutral {
  color: #6b7280;
}

.batch-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
}

.chevron {
  font-size: 16px;
  color: #9ca3af;
  transition: transform 0.3s;
  display: inline-block;
}

.chevron-expanded {
  transform: rotate(180deg);
}

/* Expanded Details */
.batch-details {
  padding: 0 20px 20px 20px;
  background-color: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 2000px;
  opacity: 1;
}

.detail-section {
  margin-top: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Condition Info */
.condition-info {
  background: white;
  padding: 12px 16px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.condition-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.condition-item:last-child {
  margin-bottom: 0;
}

.condition-label {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  min-width: 120px;
}

.condition-value {
  font-size: 13px;
  color: #111827;
  font-family: 'Courier New', monospace;
}

/* Market Snapshot */
.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.snapshot-item {
  background: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.snapshot-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.snapshot-value {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

/* Legs Table */
.legs-table-wrapper {
  overflow-x: auto;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.legs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.legs-table th {
  background-color: #f3f4f6;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e5e7eb;
}

.legs-table td {
  padding: 12px;
  border-bottom: 1px solid #f3f4f6;
  color: #111827;
}

.legs-table tbody tr:last-child td {
  border-bottom: none;
}

.legs-table tbody tr:hover {
  background-color: #f9fafb;
}

.leg-instrument {
  font-weight: 600;
  color: #1f2937;
}

.leg-type {
  text-align: center;
}

.type-ce {
  color: #10b981;
  font-weight: 600;
}

.type-pe {
  color: #ef4444;
  font-weight: 600;
}

.leg-qty,
.leg-price,
.leg-slippage,
.leg-greek {
  text-align: right;
  font-family: 'Courier New', monospace;
}

.leg-status {
  text-align: center;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-complete {
  background-color: #d1fae5;
  color: #065f46;
}

.status-pending {
  background-color: #fef3c7;
  color: #92400e;
}

.status-failed {
  background-color: #fee2e2;
  color: #991b1b;
}

.status-cancelled {
  background-color: #f3f4f6;
  color: #6b7280;
}

.leg-pnl {
  text-align: right;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

/* Batch Stats */
.batch-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 16px;
  padding: 12px 16px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.stat-item {
  display: flex;
  gap: 6px;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
}

.stat-value {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
}

.stat-failed .stat-value {
  color: #ef4444;
}

/* Responsive */
@media (max-width: 1200px) {
  .batch-header {
    grid-template-columns: 40px 90px 110px 1fr 70px 100px 40px;
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .batch-header {
    grid-template-columns: 30px 80px 100px 60px 90px 30px;
    gap: 8px;
    padding: 12px 16px;
  }

  .batch-strategy {
    display: none;
  }

  .snapshot-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .legs-table {
    font-size: 11px;
  }

  .legs-table th,
  .legs-table td {
    padding: 8px 6px;
  }
}
</style>
