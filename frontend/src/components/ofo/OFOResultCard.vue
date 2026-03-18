<template>
  <div
    class="ofo-result-card"
    :data-testid="`ofo-card-${result.strategy_type}-${rank}`"
  >
    <!-- Rank Badge -->
    <div
      class="rank-badge"
      :class="getRankClass(rank)"
      :data-testid="`ofo-card-rank-${rank}`"
    >
      #{{ rank }}
    </div>

    <!-- Header -->
    <div class="card-header">
      <h3
        class="strategy-name"
        :data-testid="`ofo-card-name-${rank}`"
      >
        {{ result.strategy_name }}
      </h3>
      <div
        class="profit-badge"
        :class="result.max_profit > 0 ? 'profit' : 'loss'"
        :data-testid="`ofo-card-profit-${rank}`"
      >
        Max Profit: {{ formatCurrency(result.max_profit) }}
      </div>
    </div>

    <!-- Legs Table -->
    <div class="legs-table-wrapper">
      <table
        class="legs-table"
        :data-testid="`ofo-card-legs-${rank}`"
      >
        <thead>
          <tr>
            <th>Expiry</th>
            <th>Type</th>
            <th>B/S</th>
            <th>Strike</th>
            <th>CMP</th>
            <th>Lots</th>
            <th>Qty</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(leg, idx) in result.legs" :key="idx">
            <td class="expiry">{{ formatExpiry(leg.expiry) }}</td>
            <td :class="getTypeClass(leg.contract_type)">{{ leg.contract_type }}</td>
            <td :class="getActionClass(leg.transaction_type)">{{ leg.transaction_type }}</td>
            <td class="strike">{{ formatNumber(leg.strike) }}</td>
            <td class="cmp">{{ formatPrice(leg.cmp) }}</td>
            <td class="lots">{{ leg.lots }}</td>
            <td class="qty">{{ leg.qty }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Summary -->
    <div class="card-summary">
      <div class="summary-item">
        <span class="label">Net Premium</span>
        <span class="value" :class="result.net_premium > 0 ? 'credit' : 'debit'">
          {{ result.net_premium > 0 ? '+' : '' }}{{ formatCurrency(result.net_premium) }}
        </span>
      </div>
      <div class="summary-item">
        <span class="label">Max Loss</span>
        <span class="value loss">{{ formatCurrency(result.max_loss) }}</span>
      </div>
      <div class="summary-item">
        <span class="label">R:R Ratio</span>
        <span class="value">{{ result.risk_reward_ratio }}x</span>
      </div>
      <div v-if="result.breakevens.length > 0" class="summary-item breakevens">
        <span class="label">Breakeven</span>
        <span class="value">{{ result.breakevens.map(b => formatNumber(b)).join(', ') }}</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="card-actions">
      <button
        class="btn-builder"
        @click="$emit('open-in-builder', result)"
        :data-testid="`ofo-card-builder-${rank}`"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="12" y1="18" x2="12" y2="12"></line>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
        Open in Builder
      </button>
      <button
        class="btn-order btn-coming-soon"
        disabled
        title="Place Order — coming soon"
        :data-testid="`ofo-card-order-${rank}`"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <polyline points="19 12 12 19 5 12"></polyline>
        </svg>
        Place Order
        <span class="coming-soon-tag">Soon</span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  result: {
    type: Object,
    required: true
  },
  rank: {
    type: Number,
    required: true
  }
})

defineEmits(['open-in-builder', 'place-order'])

function formatCurrency(value) {
  if (value === null || value === undefined) return '-'
  const absValue = Math.abs(value)
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(absValue)
  return value < 0 ? `-${formatted}` : formatted
}

function formatPrice(value) {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

function formatNumber(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('en-IN').format(value)
}

function formatExpiry(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short'
  })
}

function getRankClass(rank) {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return 'bronze'
  return ''
}

function getTypeClass(type) {
  return type === 'CE' ? 'ce' : 'pe'
}

function getActionClass(action) {
  return action === 'BUY' ? 'buy' : 'sell'
}
</script>

<style scoped>
.ofo-result-card {
  position: relative;
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  padding: 16px;
  transition: all 0.15s ease;
  min-width: 320px;
  max-width: 380px;
  box-shadow: var(--kite-shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
}

.ofo-result-card:hover {
  border-color: var(--kite-primary, #2d68b0);
  box-shadow: var(--kite-shadow, 0 2px 6px rgba(0,0,0,0.06));
  transform: translateY(-1px);
}

/* Rank Badge */
.rank-badge {
  position: absolute;
  top: -8px;
  right: 12px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  border-radius: 12px;
  background: var(--kite-table-header-bg, #fafbfc);
  border: 2px solid var(--kite-border, #e8e8e8);
  color: var(--kite-text-secondary, #6c757d);
}

.rank-badge.gold {
  background: linear-gradient(135deg, #ffd700, #ff8c00);
  color: #000;
  border-color: #ffd700;
}

.rank-badge.silver {
  background: linear-gradient(135deg, #c0c0c0, #a8a8a8);
  color: #000;
  border-color: #c0c0c0;
}

.rank-badge.bronze {
  background: linear-gradient(135deg, #cd7f32, #8b4513);
  color: #fff;
  border-color: #cd7f32;
}

/* Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-right: 40px;
}

.strategy-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
  margin: 0;
}

.profit-badge {
  font-size: 13px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.profit-badge.profit {
  background: var(--kite-green-light, #e6f9f4);
  color: var(--kite-green-text, #00875a);
}

.profit-badge.loss {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red-text, #d43f3a);
}

/* Legs Table */
.legs-table-wrapper {
  overflow-x: auto;
  margin-bottom: 12px;
}

.legs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.legs-table th {
  text-align: left;
  padding: 6px 8px;
  color: var(--kite-text-secondary, #6c757d);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
  white-space: nowrap;
  background: var(--kite-table-header-bg, #fafbfc);
}

.legs-table td {
  padding: 8px;
  color: var(--kite-text-primary, #394046);
  border-bottom: 1px solid var(--kite-border-light, #f5f5f5);
}

.legs-table tr:last-child td {
  border-bottom: none;
}

.legs-table .ce {
  color: var(--kite-red-text, #d43f3a);
  font-weight: 600;
}

.legs-table .pe {
  color: var(--kite-green-text, #00875a);
  font-weight: 600;
}

.legs-table .buy {
  color: #1565c0;
  font-weight: 600;
}

.legs-table .sell {
  color: #e65100;
  font-weight: 600;
}

.legs-table .strike {
  font-weight: 600;
}

.legs-table .cmp {
  font-family: 'JetBrains Mono', monospace;
}

/* Summary */
.card-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 12px 0;
  border-top: 1px solid var(--kite-border, #e8e8e8);
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
  margin-bottom: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-item.breakevens {
  grid-column: span 3;
}

.summary-item .label {
  font-size: 11px;
  color: var(--kite-text-secondary, #6c757d);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-item .value {
  font-size: 13px;
  font-weight: 600;
  color: var(--kite-text-primary, #394046);
}

.summary-item .value.credit {
  color: var(--kite-green-text, #00875a);
}

.summary-item .value.debit {
  color: var(--kite-red-text, #d43f3a);
}

.summary-item .value.loss {
  color: var(--kite-red-text, #d43f3a);
}

/* Actions */
.card-actions {
  display: flex;
  gap: 8px;
}

.card-actions button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-builder {
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  color: var(--kite-text-primary, #394046);
}

.btn-builder:hover {
  background: var(--kite-primary, #2d68b0);
  border-color: var(--kite-primary, #2d68b0);
  color: white;
}

.btn-order {
  background: var(--kite-primary, #2d68b0);
  border: 1px solid var(--kite-primary, #2d68b0);
  color: white;
}

.btn-order:hover:not(:disabled) {
  background: var(--kite-primary-dark, #245290);
  border-color: var(--kite-primary-dark, #245290);
}

.btn-coming-soon {
  opacity: 0.5;
  cursor: not-allowed !important;
  position: relative;
}

.coming-soon-tag {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 1px 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
}
</style>
