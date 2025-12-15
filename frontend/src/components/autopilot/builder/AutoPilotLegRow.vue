<script setup>
/**
 * AutoPilot Leg Row Component
 * Individual leg row in the AutoPilot legs configuration table
 */
import { computed, ref, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import api from '@/services/api'

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

// Strike finder state
const isSearchingStrike = ref(false)
const strikeSearchError = ref('')

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

// Strike selection mode
const strikeMode = computed(() => props.leg.strike_selection_mode || 'fixed')

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

  // Reset strike when mode changes
  if (field === 'strike_selection_mode') {
    emit('update', props.index, { strike_price: null })
    strikeSearchError.value = ''
  }

  // Validate delta range inputs
  if (field === 'min_delta' || field === 'max_delta') {
    const minDelta = parseFloat(field === 'min_delta' ? value : props.leg.min_delta)
    const maxDelta = parseFloat(field === 'max_delta' ? value : props.leg.max_delta)

    if (!isNaN(minDelta) && !isNaN(maxDelta) && minDelta >= maxDelta) {
      strikeSearchError.value = 'Min delta must be less than max delta'
    } else {
      strikeSearchError.value = ''
    }
  }

  // Validate premium range inputs
  if (field === 'min_premium' || field === 'max_premium') {
    const minPremium = parseFloat(field === 'min_premium' ? value : props.leg.min_premium)
    const maxPremium = parseFloat(field === 'max_premium' ? value : props.leg.max_premium)

    if (!isNaN(minPremium) && !isNaN(maxPremium) && minPremium >= maxPremium) {
      strikeSearchError.value = 'Min premium must be less than max premium'
    } else {
      strikeSearchError.value = ''
    }
  }
}

// Find strike by delta range
const findStrikeByDelta = async () => {
  if (!props.leg.expiry_date || !props.leg.contract_type) {
    strikeSearchError.value = 'Please select expiry and option type first'
    return
  }

  const minDelta = parseFloat(props.leg.min_delta)
  const maxDelta = parseFloat(props.leg.max_delta)

  if (isNaN(minDelta) || isNaN(maxDelta)) {
    strikeSearchError.value = 'Please enter valid delta values'
    return
  }

  if (minDelta >= maxDelta) {
    strikeSearchError.value = 'Min delta must be less than max delta'
    return
  }

  isSearchingStrike.value = true
  strikeSearchError.value = ''

  try {
    const underlying = store.builder.strategy.underlying || 'NIFTY'
    const expiry = props.leg.expiry_date

    if (!expiry) {
      strikeSearchError.value = 'Please select an expiry date first'
      isSearchingStrike.value = false
      return
    }

    // Use the strikes-in-range endpoint
    const response = await api.get(`/api/v1/autopilot/option-chain/strikes-in-range/${underlying}/${expiry}`, {
      params: {
        option_type: props.leg.contract_type,
        min_value: minDelta,
        max_value: maxDelta,
        range_type: 'delta'
      }
    })

    if (response.data.strikes && response.data.strikes.length > 0) {
      let strikes = response.data.strikes

      // Apply round strike preference if enabled
      if (props.leg.prefer_round_strike) {
        const roundStrikes = strikes.filter(s => s % 100 === 0)
        if (roundStrikes.length > 0) {
          strikes = roundStrikes
        }
      }

      // Select the first (closest) strike
      const selectedStrike = strikes[0]
      emit('update', props.index, { strike_price: selectedStrike })
      strikeSearchError.value = ''
    } else {
      strikeSearchError.value = 'No strike found in this delta range'
    }
  } catch (error) {
    console.error('Error finding strike by delta:', error)
    strikeSearchError.value = error.response?.data?.detail || 'Error finding strike'
  } finally {
    isSearchingStrike.value = false
  }
}

// Find strike by premium range
const findStrikeByPremium = async () => {
  if (!props.leg.expiry_date || !props.leg.contract_type) {
    strikeSearchError.value = 'Please select expiry and option type first'
    return
  }

  const minPremium = parseFloat(props.leg.min_premium)
  const maxPremium = parseFloat(props.leg.max_premium)

  if (isNaN(minPremium) || isNaN(maxPremium)) {
    strikeSearchError.value = 'Please enter valid premium values'
    return
  }

  if (minPremium >= maxPremium) {
    strikeSearchError.value = 'Min premium must be less than max premium'
    return
  }

  isSearchingStrike.value = true
  strikeSearchError.value = ''

  try {
    const underlying = store.builder.strategy.underlying || 'NIFTY'
    const expiry = props.leg.expiry_date

    if (!expiry) {
      strikeSearchError.value = 'Please select an expiry date first'
      isSearchingStrike.value = false
      return
    }

    const response = await api.get(`/api/v1/autopilot/option-chain/strikes-in-range/${underlying}/${expiry}`, {
      params: {
        option_type: props.leg.contract_type,
        min_value: minPremium,
        max_value: maxPremium,
        range_type: 'premium'
      }
    })

    if (response.data.strikes && response.data.strikes.length > 0) {
      let strikes = response.data.strikes

      // Apply round strike preference if enabled
      if (props.leg.prefer_round_strike) {
        const roundStrikes = strikes.filter(s => s % 100 === 0)
        if (roundStrikes.length > 0) {
          strikes = roundStrikes
        }
      }

      const selectedStrike = strikes[0]
      emit('update', props.index, { strike_price: selectedStrike })
      strikeSearchError.value = ''
    } else {
      strikeSearchError.value = 'No strike found in this premium range'
    }
  } catch (error) {
    console.error('Error finding strike by premium:', error)
    strikeSearchError.value = error.response?.data?.detail || 'Error finding strike'
  } finally {
    isSearchingStrike.value = false
  }
}

// Find strike by standard deviation
const findStrikeBySD = async () => {
  if (!props.leg.expiry_date || !props.leg.contract_type) {
    strikeSearchError.value = 'Please select expiry and option type first'
    return
  }

  const sdMultiplier = parseFloat(props.leg.sd_multiplier)
  if (isNaN(sdMultiplier) || sdMultiplier <= 0) {
    strikeSearchError.value = 'Please select a valid SD multiplier'
    return
  }

  isSearchingStrike.value = true
  strikeSearchError.value = ''

  try {
    const underlying = store.builder.strategy.underlying || 'NIFTY'
    const expiry = props.leg.expiry_date

    const response = await api.get(`/api/v1/autopilot/option-chain/strike-by-sd/${underlying}/${expiry}`, {
      params: {
        option_type: props.leg.contract_type,
        sd_multiplier: sdMultiplier
      }
    })

    if (response.data.strike) {
      emit('update', props.index, { strike_price: response.data.strike })
      strikeSearchError.value = ''
    } else {
      strikeSearchError.value = 'No strike found for this SD'
    }
  } catch (error) {
    console.error('Error finding strike by SD:', error)
    strikeSearchError.value = error.response?.data?.detail || 'Error finding strike'
  } finally {
    isSearchingStrike.value = false
  }
}

// Find strike by expected move
const findStrikeByEM = async () => {
  if (!props.leg.expiry_date || !props.leg.contract_type) {
    strikeSearchError.value = 'Please select expiry and option type first'
    return
  }

  const emPosition = props.leg.em_position
  if (!emPosition) {
    strikeSearchError.value = 'Please select above or below expected move'
    return
  }

  isSearchingStrike.value = true
  strikeSearchError.value = ''

  try {
    const underlying = store.builder.strategy.underlying || 'NIFTY'
    const expiry = props.leg.expiry_date

    const response = await api.get(`/api/v1/autopilot/option-chain/strike-by-expected-move/${underlying}/${expiry}`, {
      params: {
        option_type: props.leg.contract_type,
        position: emPosition  // 'above' or 'below'
      }
    })

    if (response.data.strike) {
      emit('update', props.index, { strike_price: response.data.strike })
      strikeSearchError.value = ''
    } else {
      strikeSearchError.value = 'No strike found outside expected move'
    }
  } catch (error) {
    console.error('Error finding strike by EM:', error)
    strikeSearchError.value = error.response?.data?.detail || 'Error finding strike'
  } finally {
    isSearchingStrike.value = false
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

    <!-- Strike Mode & Strike Selection -->
    <td colspan="2" style="padding: 4px;">
      <div class="strike-config">
        <!-- Strike Selection Mode -->
        <select
          :value="strikeMode"
          @change="handleUpdate('strike_selection_mode', $event.target.value)"
          class="strategy-select compact mb-1"
          :data-testid="`autopilot-leg-strike-mode-${index}`"
        >
          <option value="fixed">Fixed Strike</option>
          <option value="delta_range">Delta Range</option>
          <option value="premium_range">Premium Range</option>
          <option value="standard_deviation">Standard Deviation</option>
          <option value="expected_move">Expected Move</option>
        </select>

        <!-- Fixed Strike Mode -->
        <div v-if="strikeMode === 'fixed'" class="strike-fixed">
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
        </div>

        <!-- Delta Range Mode -->
        <div v-if="strikeMode === 'delta_range'" class="strike-delta-range">
          <div class="flex gap-1 mb-1">
            <input
              type="number"
              :value="leg.min_delta"
              @input="handleUpdate('min_delta', $event.target.value)"
              placeholder="Min Δ"
              step="0.01"
              min="0"
              max="1"
              class="strategy-input compact text-xs"
              :data-testid="`autopilot-leg-min-delta-${index}`"
              style="width: 60px;"
            />
            <input
              type="number"
              :value="leg.max_delta"
              @input="handleUpdate('max_delta', $event.target.value)"
              placeholder="Max Δ"
              step="0.01"
              min="0"
              max="1"
              class="strategy-input compact text-xs"
              :data-testid="`autopilot-leg-max-delta-${index}`"
              style="width: 60px;"
            />
            <button
              @click="findStrikeByDelta"
              :disabled="isSearchingStrike"
              class="btn-find-strike"
              :data-testid="`autopilot-leg-find-strike-${index}`"
            >
              {{ isSearchingStrike ? '...' : 'Find' }}
            </button>
          </div>
          <div v-if="leg.strike_price" class="selected-strike" :data-testid="`autopilot-leg-selected-strike-${index}`">
            Strike: <strong>{{ leg.strike_price }}</strong>
          </div>
          <div v-if="strikeSearchError" class="error-message">
            {{ strikeSearchError }}
          </div>
        </div>

        <!-- Premium Range Mode -->
        <div v-if="strikeMode === 'premium_range'" class="strike-premium-range">
          <div class="flex gap-1 mb-1">
            <input
              type="number"
              :value="leg.min_premium"
              @input="handleUpdate('min_premium', $event.target.value)"
              placeholder="Min ₹"
              step="1"
              class="strategy-input compact text-xs"
              :data-testid="`autopilot-leg-min-premium-${index}`"
              style="width: 60px;"
            />
            <input
              type="number"
              :value="leg.max_premium"
              @input="handleUpdate('max_premium', $event.target.value)"
              placeholder="Max ₹"
              step="1"
              class="strategy-input compact text-xs"
              :data-testid="`autopilot-leg-max-premium-${index}`"
              style="width: 60px;"
            />
            <button
              @click="findStrikeByPremium"
              :disabled="isSearchingStrike"
              class="btn-find-strike"
              :data-testid="`autopilot-leg-find-strike-${index}`"
            >
              {{ isSearchingStrike ? '...' : 'Find' }}
            </button>
          </div>
          <div v-if="leg.strike_price" class="selected-strike" :data-testid="`autopilot-leg-selected-strike-${index}`">
            Strike: <strong>{{ leg.strike_price }}</strong>
          </div>
          <div v-if="strikeSearchError" class="error-message">
            {{ strikeSearchError }}
          </div>
        </div>

        <!-- Standard Deviation Mode -->
        <div v-if="strikeMode === 'standard_deviation'" class="strike-sd-mode">
          <div class="flex gap-1 mb-1">
            <select
              :value="leg.sd_multiplier"
              @change="handleUpdate('sd_multiplier', parseFloat($event.target.value))"
              class="strategy-select compact text-xs"
              :data-testid="`autopilot-leg-sd-multiplier-${index}`"
              style="width: 80px;"
            >
              <option value="">Select SD</option>
              <option value="1">1 SD</option>
              <option value="1.5">1.5 SD</option>
              <option value="2">2 SD</option>
              <option value="2.5">2.5 SD</option>
              <option value="3">3 SD</option>
            </select>
            <button
              @click="findStrikeBySD"
              :disabled="isSearchingStrike"
              class="btn-find-strike"
              :data-testid="`autopilot-leg-find-strike-${index}`"
            >
              {{ isSearchingStrike ? '...' : 'Find' }}
            </button>
          </div>
          <div v-if="leg.strike_price" class="selected-strike" :data-testid="`autopilot-leg-selected-strike-${index}`">
            Strike: <strong>{{ leg.strike_price }}</strong>
          </div>
          <div v-if="strikeSearchError" class="error-message">
            {{ strikeSearchError }}
          </div>
        </div>

        <!-- Expected Move Mode -->
        <div v-if="strikeMode === 'expected_move'" class="strike-em-mode">
          <div class="expected-move-info text-xs mb-1">
            <span>Select strikes outside expected move range</span>
          </div>
          <div class="flex gap-1 mb-1">
            <select
              :value="leg.em_position"
              @change="handleUpdate('em_position', $event.target.value)"
              class="strategy-select compact text-xs"
              :data-testid="`autopilot-leg-em-position-${index}`"
              style="width: 100px;"
            >
              <option value="">Select</option>
              <option value="above">Above EM</option>
              <option value="below">Below EM</option>
            </select>
            <button
              @click="findStrikeByEM"
              :disabled="isSearchingStrike"
              class="btn-find-strike"
              :data-testid="`autopilot-leg-find-strike-${index}`"
            >
              {{ isSearchingStrike ? '...' : 'Find' }}
            </button>
          </div>
          <div v-if="leg.strike_price" class="selected-strike" :data-testid="`autopilot-leg-selected-strike-${index}`">
            Strike: <strong>{{ leg.strike_price }}</strong>
          </div>
          <div v-if="strikeSearchError" class="error-message">
            {{ strikeSearchError }}
          </div>
        </div>

        <!-- Round Strike Preference -->
        <div class="round-strike-pref mt-1">
          <label class="flex items-center gap-1 text-xs">
            <input
              type="checkbox"
              :checked="leg.prefer_round_strike"
              @change="handleUpdate('prefer_round_strike', $event.target.checked)"
              :data-testid="`autopilot-leg-round-strike-${index}`"
              class="text-xs"
            />
            <span>Round (÷100)</span>
          </label>
        </div>
      </div>
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

.text-xs {
  font-size: 0.75rem;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.gap-1 {
  gap: 0.25rem;
}

.mb-1 {
  margin-bottom: 0.25rem;
}

.mt-1 {
  margin-top: 0.25rem;
}

.strike-config {
  min-width: 180px;
}

.btn-find-strike {
  background-color: #3b82f6;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  border: none;
  cursor: pointer;
  white-space: nowrap;
}

.btn-find-strike:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-find-strike:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.selected-strike {
  font-size: 0.75rem;
  color: #059669;
  padding: 2px 4px;
  background-color: #d1fae5;
  border-radius: 4px;
  text-align: center;
}

.error-message {
  font-size: 0.7rem;
  color: #dc2626;
  padding: 2px 4px;
  background-color: #fee2e2;
  border-radius: 4px;
  margin-top: 2px;
}

.round-strike-pref label {
  cursor: pointer;
  user-select: none;
}
</style>
