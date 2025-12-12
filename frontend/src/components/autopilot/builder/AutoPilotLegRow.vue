<script setup>
/**
 * AutoPilot Leg Row Component
 * Individual leg row in the AutoPilot legs configuration table
 */
import { computed, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'

const props = defineProps({
  leg: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update', 'delete', 'toggle-select'])

const store = useAutopilotStore()

// Get strikes for this leg's expiry
const availableStrikes = computed(() => {
  return store.strikes[props.leg.expiry_date] || []
})

// CMP value for this leg
const cmp = computed(() => store.getLegCMP(props.leg))

// Exit P/L for this leg
const exitPnL = computed(() => store.getLegExitPnL(props.leg))

// Quantity calculation
const quantity = computed(() => (props.leg.lots || 1) * store.lotSize)

// Is this leg selected?
const isSelected = computed(() => store.selectedLegIndices.includes(props.index))

// Row class based on transaction type
const rowClass = computed(() => ({
  'leg-row': true,
  'leg-buy': props.leg.transaction_type === 'BUY',
  'leg-sell': props.leg.transaction_type === 'SELL'
}))

// Handle field updates
const handleUpdate = (field, value) => {
  emit('update', props.index, { [field]: value })

  // Fetch strikes when expiry changes
  if (field === 'expiry_date' && value) {
    store.fetchStrikes(value)
  }

  // Fetch instrument token when strike, expiry, or contract_type changes
  if (['strike_price', 'expiry_date', 'contract_type'].includes(field)) {
    const leg = { ...props.leg, [field]: value }
    if (leg.strike_price && leg.expiry_date && leg.contract_type) {
      fetchInstrumentForLeg(leg)
    }
  }
}

// Fetch instrument token for live prices
const fetchInstrumentForLeg = async (leg) => {
  const result = await store.fetchInstrumentToken(
    leg.expiry_date,
    leg.strike_price,
    leg.contract_type
  )
  if (result.instrument_token) {
    emit('update', props.index, {
      instrument_token: result.instrument_token,
      tradingsymbol: result.tradingsymbol
    })
  }
}

// Format date for display
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

// Format price
const formatPrice = (value) => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

// Format P/L with color class
const formatPnL = (value) => {
  if (value === null || value === undefined) return '-'
  const prefix = value >= 0 ? '+' : ''
  return prefix + value.toFixed(2)
}

const getPnLClass = (value) => {
  if (value === null || value === undefined) return 'pnl-neutral'
  return value >= 0 ? 'pnl-profit' : 'pnl-loss'
}
</script>

<template>
  <tr :class="rowClass" :data-testid="`autopilot-leg-row-${index}`">
    <!-- Checkbox -->
    <td class="td-checkbox">
      <input
        type="checkbox"
        :checked="isSelected"
        @change="emit('toggle-select', index)"
        :data-testid="`autopilot-leg-checkbox-${index}`"
      />
    </td>

    <!-- Action (BUY/SELL) -->
    <td>
      <select
        :value="leg.transaction_type"
        @change="handleUpdate('transaction_type', $event.target.value)"
        :class="['tag-select', leg.transaction_type === 'BUY' ? 'tag-buy' : 'tag-sell']"
        :data-testid="`autopilot-leg-action-${index}`"
      >
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>
    </td>

    <!-- Expiry -->
    <td>
      <select
        :value="leg.expiry_date"
        @change="handleUpdate('expiry_date', $event.target.value)"
        class="strategy-select compact"
        :data-testid="`autopilot-leg-expiry-${index}`"
      >
        <option value="">Select</option>
        <option v-for="exp in store.expiries" :key="exp" :value="exp">
          {{ formatDate(exp) }}
        </option>
      </select>
    </td>

    <!-- Strike -->
    <td>
      <select
        :value="leg.strike_price"
        @change="handleUpdate('strike_price', parseFloat($event.target.value))"
        class="strategy-select compact"
        :data-testid="`autopilot-leg-strike-${index}`"
      >
        <option value="">Select</option>
        <option v-for="s in availableStrikes" :key="s" :value="s">
          {{ s }}
        </option>
      </select>
    </td>

    <!-- CE/PE -->
    <td>
      <select
        :value="leg.contract_type"
        @change="handleUpdate('contract_type', $event.target.value)"
        :class="['tag-select', leg.contract_type === 'CE' ? 'tag-ce' : 'tag-pe']"
        :data-testid="`autopilot-leg-type-${index}`"
      >
        <option value="CE">CE</option>
        <option value="PE">PE</option>
      </select>
    </td>

    <!-- Lots -->
    <td>
      <input
        type="number"
        :value="leg.lots"
        @input="handleUpdate('lots', parseInt($event.target.value) || 1)"
        min="1"
        class="strategy-input compact text-center"
        style="width: 60px;"
        :data-testid="`autopilot-leg-lots-${index}`"
      />
    </td>

    <!-- Entry Price -->
    <td>
      <input
        type="number"
        :value="leg.entry_price"
        @input="handleUpdate('entry_price', parseFloat($event.target.value))"
        step="0.05"
        placeholder="Entry"
        class="strategy-input compact text-right"
        style="width: 80px;"
        :data-testid="`autopilot-leg-entry-${index}`"
      />
    </td>

    <!-- CMP -->
    <td class="text-right" :data-testid="`autopilot-leg-cmp-${index}`">
      <span v-if="cmp" class="cmp-value">{{ formatPrice(cmp) }}</span>
      <span v-else class="no-value">-</span>
    </td>

    <!-- Exit P/L -->
    <td class="text-right font-semibold" :data-testid="`autopilot-leg-exit-pnl-${index}`">
      <span :class="getPnLClass(exitPnL)">{{ formatPnL(exitPnL) }}</span>
    </td>

    <!-- Target Price -->
    <td>
      <input
        type="number"
        :value="leg.target_price"
        @input="handleUpdate('target_price', parseFloat($event.target.value))"
        step="0.05"
        placeholder="Target"
        class="strategy-input compact text-right"
        style="width: 80px;"
        :data-testid="`autopilot-leg-target-price-${index}`"
      />
    </td>

    <!-- Stop-Loss Price -->
    <td>
      <input
        type="number"
        :value="leg.stop_loss_price"
        @input="handleUpdate('stop_loss_price', parseFloat($event.target.value))"
        step="0.05"
        placeholder="SL"
        class="strategy-input compact text-right"
        style="width: 80px;"
        :data-testid="`autopilot-leg-stop-loss-price-${index}`"
      />
    </td>

    <!-- Trailing SL -->
    <td class="text-center">
      <input
        type="checkbox"
        :checked="leg.trailing_stop_loss?.enabled"
        @change="handleUpdate('trailing_stop_loss', { ...leg.trailing_stop_loss, enabled: $event.target.checked })"
        :data-testid="`autopilot-leg-trailing-sl-${index}`"
      />
    </td>

    <!-- Target % -->
    <td>
      <input
        type="number"
        :value="leg.target_pct"
        @input="handleUpdate('target_pct', parseFloat($event.target.value))"
        step="1"
        placeholder="%"
        class="strategy-input compact text-right"
        style="width: 60px;"
        :data-testid="`autopilot-leg-target-pct-${index}`"
      />
    </td>

    <!-- Stop-Loss % -->
    <td>
      <input
        type="number"
        :value="leg.stop_loss_pct"
        @input="handleUpdate('stop_loss_pct', parseFloat($event.target.value))"
        step="1"
        placeholder="%"
        class="strategy-input compact text-right"
        style="width: 60px;"
        :data-testid="`autopilot-leg-stop-loss-pct-${index}`"
      />
    </td>

    <!-- Max Loss Amount -->
    <td>
      <input
        type="number"
        :value="leg.max_loss_amount"
        @input="handleUpdate('max_loss_amount', parseFloat($event.target.value))"
        step="100"
        placeholder="Max"
        class="strategy-input compact text-right"
        style="width: 80px;"
        :data-testid="`autopilot-leg-max-loss-${index}`"
      />
    </td>

    <!-- Delete Button -->
    <td class="text-center">
      <button
        @click="emit('delete', index)"
        class="text-red-500 hover:text-red-700 text-sm"
        :data-testid="`autopilot-leg-delete-${index}`"
      >
        &times;
      </button>
    </td>
  </tr>
</template>

<style scoped>
.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

.font-semibold {
  font-weight: 600;
}
</style>
