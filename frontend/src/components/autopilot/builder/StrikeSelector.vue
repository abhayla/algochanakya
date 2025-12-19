<template>
  <div class="strike-selector-compact">
    <!-- Main Row: Dropdown + Input + Preview + Ladder Button -->
    <div class="selector-row">
      <!-- Mode Dropdown -->
      <select
        v-model="localValue.mode"
        @change="onModeChange"
        class="mode-dropdown"
        :data-testid="`strike-selector-mode-dropdown`"
      >
        <option value="fixed">Fixed Strike</option>
        <option value="atm_offset">ATM Offset</option>
        <option value="delta_based">Delta</option>
        <option value="premium_based">Premium</option>
        <option value="sd_based">SD</option>
      </select>

      <!-- Mode-specific inline configuration -->
      <div class="config-inline">
        <!-- Fixed Strike -->
        <template v-if="localValue.mode === 'fixed'">
          <input
            type="number"
            v-model.number="localValue.fixed_strike"
            @input="onConfigChange"
            placeholder="Strike"
            class="compact-input"
            :step="strikeStep"
            data-testid="strike-selector-fixed-input"
          />
        </template>

        <!-- ATM Offset -->
        <template v-else-if="localValue.mode === 'atm_offset'">
          <input
            type="number"
            v-model.number="localValue.offset"
            @input="onConfigChange"
            class="compact-input"
            :step="1"
            placeholder="0"
          />
          <span class="unit">strikes</span>
        </template>

        <!-- Delta Based -->
        <template v-else-if="localValue.mode === 'delta_based'">
          <input
            type="number"
            v-model.number="localValue.target_delta"
            @input="onConfigChange"
            class="compact-input"
            step="0.01"
            min="0.01"
            max="0.99"
            placeholder="0.30"
          />
          <span class="unit">Δ</span>
        </template>

        <!-- Premium Based -->
        <template v-else-if="localValue.mode === 'premium_based'">
          <span class="unit">₹</span>
          <input
            type="number"
            v-model.number="localValue.target_premium"
            @input="onConfigChange"
            class="compact-input"
            :step="5"
            min="1"
            placeholder="100"
          />
        </template>

        <!-- Standard Deviation Based -->
        <template v-else-if="localValue.mode === 'sd_based'">
          <input
            type="number"
            v-model.number="localValue.standard_deviations"
            @input="onConfigChange"
            class="compact-input"
            step="0.1"
            min="0.1"
            max="3.0"
            placeholder="1.0"
          />
          <span class="unit">σ</span>
          <label class="checkbox-inline">
            <input
              type="checkbox"
              v-model="localValue.outside_sd"
              @change="onConfigChange"
            />
            <span>Outside</span>
          </label>
        </template>
      </div>

      <!-- Preview (always visible) -->
      <div class="preview-inline" v-if="preview && !loadingPreview">
        <span class="arrow">→</span>
        <span class="strike-value">{{ preview.strike }} {{ optionType }}</span>
        <span class="price-value">@ ₹{{ preview.ltp }}</span>
        <span class="delta-value" v-if="preview.delta">({{ preview.delta }}Δ)</span>
      </div>

      <!-- Loading indicator -->
      <div class="preview-loading" v-if="loadingPreview">
        <span class="spinner-small"></span>
      </div>

      <!-- Error indicator -->
      <div class="preview-error-inline" v-if="previewError">
        <span class="error-text">{{ previewError }}</span>
      </div>
    </div>

    <!-- Quick Presets Row (only for delta/premium/sd modes) -->
    <div
      class="quick-presets"
      v-if="['delta_based', 'premium_based', 'sd_based'].includes(localValue.mode)"
    >
      <!-- Delta Presets -->
      <template v-if="localValue.mode === 'delta_based'">
        <button
          v-for="preset in deltaPresets"
          :key="preset"
          @click="selectDeltaPreset(preset)"
          class="preset-chip"
          :class="{ 'active': localValue.target_delta === preset }"
          type="button"
        >
          {{ preset }}
        </button>
      </template>

      <!-- Premium Presets -->
      <template v-if="localValue.mode === 'premium_based'">
        <button
          v-for="preset in premiumPresets"
          :key="preset"
          @click="selectPremiumPreset(preset)"
          class="preset-chip"
          :class="{ 'active': localValue.target_premium === preset }"
          type="button"
        >
          ₹{{ preset }}
        </button>
      </template>

      <!-- SD Presets -->
      <template v-if="localValue.mode === 'sd_based'">
        <button
          v-for="preset in sdPresets"
          :key="preset"
          @click="selectSDPreset(preset)"
          class="preset-chip"
          :class="{ 'active': localValue.standard_deviations === preset }"
          type="button"
        >
          {{ preset }}σ
        </button>
      </template>

      <!-- Prefer Round Strikes Checkbox (for applicable modes) -->
      <label class="checkbox-inline prefer-round">
        <input
          type="checkbox"
          v-model="localValue.prefer_round_strike"
          @change="onConfigChange"
        />
        <span>Round strikes</span>
      </label>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StrikeSelector',
  props: {
    underlying: {
      type: String,
      required: true
    },
    expiry: {
      type: String,
      required: true
    },
    optionType: {
      type: String,
      required: true,
      validator: (value) => ['CE', 'PE'].includes(value)
    },
    value: {
      type: Object,
      default: () => ({
        mode: 'atm_offset',
        offset: 0,
        target_delta: 0.30,
        target_premium: 100,
        standard_deviations: 1.0,
        outside_sd: false,
        prefer_round_strike: true,
        fixed_strike: null
      })
    }
  },
  data() {
    return {
      localValue: { ...this.value },
      preview: null,
      loadingPreview: false,
      previewError: null,
      previewDebounce: null,
      deltaPresets: [0.15, 0.20, 0.25, 0.30, 0.35],
      premiumPresets: [50, 75, 100, 150, 200],
      sdPresets: [1.0, 1.5, 2.0, 2.5, 3.0]
    }
  },
  computed: {
    strikeStep() {
      const steps = {
        'NIFTY': 50,
        'BANKNIFTY': 100,
        'FINNIFTY': 50,
        'SENSEX': 100
      }
      return steps[this.underlying?.toUpperCase()] || 50
    }
  },
  watch: {
    value: {
      handler(newVal) {
        this.localValue = { ...newVal }
        this.fetchPreview()
      },
      deep: true
    }
  },
  methods: {
    onModeChange() {
      // Reset mode-specific values when mode changes
      if (this.localValue.mode === 'fixed' && !this.localValue.fixed_strike) {
        this.localValue.fixed_strike = null
      } else if (this.localValue.mode === 'atm_offset' && this.localValue.offset === undefined) {
        this.localValue.offset = 0
      } else if (this.localValue.mode === 'delta_based' && !this.localValue.target_delta) {
        this.localValue.target_delta = 0.30
      } else if (this.localValue.mode === 'premium_based' && !this.localValue.target_premium) {
        this.localValue.target_premium = 100
      } else if (this.localValue.mode === 'sd_based' && !this.localValue.standard_deviations) {
        this.localValue.standard_deviations = 1.0
        this.localValue.outside_sd = false
      }

      this.onConfigChange()
    },
    onConfigChange() {
      this.$emit('input', { ...this.localValue })
      this.debouncedFetchPreview()
    },
    selectDeltaPreset(delta) {
      this.localValue.target_delta = delta
      this.onConfigChange()
    },
    selectPremiumPreset(premium) {
      this.localValue.target_premium = premium
      this.onConfigChange()
    },
    selectSDPreset(sd) {
      this.localValue.standard_deviations = sd
      this.onConfigChange()
    },
    debouncedFetchPreview() {
      clearTimeout(this.previewDebounce)
      this.previewDebounce = setTimeout(() => {
        this.fetchPreview()
      }, 500)
    },
    async fetchPreview() {
      // Fetch preview for ALL modes now (including atm_offset and fixed)
      if (!this.underlying || !this.expiry || !this.optionType) {
        return
      }

      this.loadingPreview = true
      this.previewError = null

      try {
        const params = {
          underlying: this.underlying,
          expiry: this.expiry,
          option_type: this.optionType,
          mode: this.localValue.mode
        }

        if (this.localValue.mode === 'fixed') {
          if (!this.localValue.fixed_strike) {
            this.preview = null
            this.loadingPreview = false
            return
          }
          params.fixed_strike = this.localValue.fixed_strike
        } else if (this.localValue.mode === 'atm_offset') {
          params.offset = this.localValue.offset || 0
        } else if (this.localValue.mode === 'delta_based') {
          params.target_delta = this.localValue.target_delta
        } else if (this.localValue.mode === 'premium_based') {
          params.target_premium = this.localValue.target_premium
        } else if (this.localValue.mode === 'sd_based') {
          params.standard_deviations = this.localValue.standard_deviations
          params.outside_sd = this.localValue.outside_sd
        }

        const response = await this.$axios.get('/api/v1/autopilot/strikes/preview', { params })
        this.preview = response.data.data
      } catch (error) {
        console.error('Error fetching strike preview:', error)
        this.previewError = 'Preview unavailable'
      } finally {
        this.loadingPreview = false
      }
    }
  },
  mounted() {
    this.fetchPreview()
  }
}
</script>

<style scoped>
/* Container */
.strike-selector-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

/* Main Row */
.selector-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Mode Dropdown */
.mode-dropdown {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  min-width: 110px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.mode-dropdown:focus {
  outline: none;
  border-color: #3b82f6;
}

/* Config Inline */
.config-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}

.compact-input {
  width: 65px;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
  background: white;
  transition: border-color 0.2s;
}

.compact-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.unit {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

/* Inline Checkbox */
.checkbox-inline {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #6b7280;
  cursor: pointer;
  white-space: nowrap;
}

.checkbox-inline input[type="checkbox"] {
  width: 14px;
  height: 14px;
  cursor: pointer;
}

/* Preview Inline */
.preview-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding: 4px 10px;
  background: #ecfdf5;
  border-radius: 4px;
  font-size: 12px;
  flex-shrink: 0;
}

.arrow {
  color: #059669;
  font-weight: 600;
}

.strike-value {
  font-weight: 600;
  color: #065f46;
}

.price-value {
  color: #059669;
  font-weight: 500;
}

.delta-value {
  color: #047857;
  font-size: 11px;
}

/* Loading Spinner */
.preview-loading {
  display: flex;
  align-items: center;
  margin-left: auto;
}

.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error Inline */
.preview-error-inline {
  margin-left: auto;
  font-size: 11px;
  color: #dc2626;
}

/* Quick Presets Row */
.quick-presets {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 4px;
  border-top: 1px solid #e5e7eb;
}

.preset-chip {
  padding: 3px 10px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  background: white;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-chip:hover {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #3b82f6;
}

.preset-chip.active {
  border-color: #3b82f6;
  background: #3b82f6;
  color: white;
}

.prefer-round {
  margin-left: auto;
  padding-left: 8px;
  border-left: 1px solid #e5e7eb;
}
</style>
