<script setup>
/**
 * AutoPilot Leg Row Component
 * Individual leg row in the AutoPilot legs configuration table
 */
import { computed, ref, watch } from 'vue'
import { useAutopilotStore } from '@/stores/autopilot'
import api from '@/services/api'
import StrikeSelector from './StrikeSelector.vue'

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

const emit = defineEmits(['update', 'delete', 'toggle-select', 'open-strike-ladder'])

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

// Strike selection config for StrikeSelector component
const strikeSelection = computed({
  get() {
    return props.leg.strike_selection || {
      mode: 'atm_offset',
      offset: 0,
      target_delta: 0.30,
      target_premium: 100,
      standard_deviations: 1.0,
      outside_sd: false,
      prefer_round_strike: true,
      fixed_strike: props.leg.strike_price
    }
  },
  set(value) {
    handleStrikeSelectorChange(value)
  }
})

// Calculated lots (read-only, auto-calculated from base lots × multiplier)
const calculatedLots = computed(() => {
  const baseLots = store.builder.strategy.lots || 1
  const multiplier = props.leg.quantity_multiplier || 1
  return baseLots * multiplier
})

// Handle StrikeSelector changes
const handleStrikeSelectorChange = (strikeConfig) => {
  emit('update', props.index, {
    strike_selection: strikeConfig,
    strike_selection_mode: strikeConfig.mode,
    // For fixed mode, update strike_price immediately
    ...(strikeConfig.mode === 'fixed' && strikeConfig.fixed_strike ? {
      strike_price: strikeConfig.fixed_strike
    } : {})
  })
}

// Handle preview loaded from StrikeSelector - update leg with instrument data
const handlePreviewLoaded = (data) => {
  if (data.instrument_token && data.tradingsymbol) {
    emit('update', props.index, {
      instrument_token: data.instrument_token,
      tradingsymbol: data.tradingsymbol,
      strike_price: data.strike
    })
    // Trigger CMP fetch with the new instrument data
    store.fetchLegLTP({
      ...props.leg,
      instrument_token: data.instrument_token,
      tradingsymbol: data.tradingsymbol
    })
  }
}

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
        const roundStrikes = strikes.filter(s => s.strike % 100 === 0)
        if (roundStrikes.length > 0) {
          strikes = roundStrikes
        }
      }

      // Select the first (closest) strike - extract strike number from object
      const selected = strikes[0]
      emit('update', props.index, {
        strike_price: selected.strike,
        entry_price: selected.ltp,
        instrument_token: selected.instrument_token,
        tradingsymbol: selected.tradingsymbol
      })
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
        const roundStrikes = strikes.filter(s => s.strike % 100 === 0)
        if (roundStrikes.length > 0) {
          strikes = roundStrikes
        }
      }

      // Select the first (closest) strike - extract strike number from object
      const selected = strikes[0]
      emit('update', props.index, {
        strike_price: selected.strike,
        entry_price: selected.ltp,
        instrument_token: selected.instrument_token,
        tradingsymbol: selected.tradingsymbol
      })
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
      emit('update', props.index, {
        strike_price: response.data.strike,
        entry_price: response.data.ltp,
        instrument_token: response.data.instrument_token,
        tradingsymbol: response.data.tradingsymbol
      })
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
      emit('update', props.index, {
        strike_price: response.data.strike,
        entry_price: response.data.ltp,
        instrument_token: response.data.instrument_token,
        tradingsymbol: response.data.tradingsymbol
      })
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
    <td style="padding: 4px;">
      <div class="strike-config">
        <!-- StrikeSelector Component -->
        <StrikeSelector
          v-model="strikeSelection"
          :underlying="store.builder.strategy.underlying || 'NIFTY'"
          :expiry="leg.expiry_date || store.expiries[0] || ''"
          :option-type="leg.contract_type"
          :data-testid="`autopilot-leg-strike-selector-${index}`"
          @preview-loaded="handlePreviewLoaded"
        >
          <!-- Strike Ladder Icon -->
          <template #ladder-icon>
            <button
              @click.stop="emit('open-strike-ladder', index)"
              class="btn-strike-ladder-icon"
              :data-testid="`autopilot-leg-open-ladder-${index}`"
              title="Strike Ladder"
              type="button"
            >
              <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                <path d="M2 1h12a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm0 1v3h12V2H2zm0 4v3h5V6H2zm6 0v3h6V6H8zM2 10v3h5v-3H2zm6 0v3h6v-3H8z"/>
              </svg>
            </button>
          </template>
        </StrikeSelector>
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

    <!-- Lots (Read-only, auto-calculated) -->
    <td class="text-center">
      <span class="lots-display" :data-testid="`autopilot-leg-lots-${index}`">{{ calculatedLots }}</span>
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

.btn-strike-ladder {
  background-color: #10b981;
  color: white;
  padding: 4px 6px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
  min-width: 32px;
}

.btn-strike-ladder:hover {
  background-color: #059669;
}

.btn-strike-ladder svg {
  width: 16px;
  height: 16px;
}

/* New StrikeSelector Integration Styles */
.strike-config {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-strike-ladder-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s ease;
  margin-left: 4px;
  flex-shrink: 0;
}

.btn-strike-ladder-icon:hover {
  background: #f3f4f6;
  color: #374151;
}

.btn-strike-ladder-icon:active {
  background: #e5e7eb;
  transform: scale(0.95);
}
</style>
