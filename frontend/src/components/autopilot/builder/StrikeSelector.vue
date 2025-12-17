<template>
  <div class="strike-selector">
    <div class="mode-selector">
      <label class="section-label">Strike Selection Mode</label>
      <div class="mode-options">
        <label
          v-for="mode in modes"
          :key="mode.value"
          class="mode-option"
          :class="{ 'active': localValue.mode === mode.value }"
        >
          <input
            type="radio"
            :value="mode.value"
            v-model="localValue.mode"
            @change="onModeChange"
          />
          <span class="mode-label">{{ mode.label }}</span>
        </label>
      </div>
    </div>

    <div class="mode-config" v-if="localValue.mode">
      <!-- Fixed Strike -->
      <div v-if="localValue.mode === 'fixed'" class="config-section">
        <label>Strike Price</label>
        <input
          type="number"
          v-model.number="localValue.fixed_strike"
          @input="onConfigChange"
          placeholder="Enter strike price"
          class="strike-input"
          :step="strikeStep"
        />
      </div>

      <!-- ATM Offset -->
      <div v-if="localValue.mode === 'atm_offset'" class="config-section">
        <label>ATM Offset (strikes)</label>
        <div class="offset-input-group">
          <input
            type="number"
            v-model.number="localValue.offset"
            @input="onConfigChange"
            placeholder="0"
            class="strike-input"
            :step="1"
          />
          <span class="offset-hint">ATM {{ localValue.offset > 0 ? '+' : '' }}{{ localValue.offset || 0 }}</span>
        </div>
      </div>

      <!-- Delta Based -->
      <div v-if="localValue.mode === 'delta_based'" class="config-section">
        <label>Target Delta</label>
        <input
          type="number"
          v-model.number="localValue.target_delta"
          @input="onConfigChange"
          placeholder="0.30"
          class="strike-input"
          step="0.01"
          min="0.01"
          max="0.99"
        />
        <div class="quick-select">
          <span class="quick-label">Quick Select:</span>
          <button
            v-for="preset in deltaPresets"
            :key="preset"
            @click="selectDeltaPreset(preset)"
            class="preset-btn"
            :class="{ 'active': localValue.target_delta === preset }"
            type="button"
          >
            {{ preset }}
          </button>
        </div>
      </div>

      <!-- Premium Based -->
      <div v-if="localValue.mode === 'premium_based'" class="config-section">
        <label>Target Premium (₹)</label>
        <input
          type="number"
          v-model.number="localValue.target_premium"
          @input="onConfigChange"
          placeholder="100"
          class="strike-input"
          :step="5"
          min="1"
        />
        <div class="quick-select">
          <span class="quick-label">Quick Select:</span>
          <button
            v-for="preset in premiumPresets"
            :key="preset"
            @click="selectPremiumPreset(preset)"
            class="preset-btn"
            :class="{ 'active': localValue.target_premium === preset }"
            type="button"
          >
            ₹{{ preset }}
          </button>
        </div>
      </div>

      <!-- Standard Deviation Based -->
      <div v-if="localValue.mode === 'sd_based'" class="config-section">
        <label>Standard Deviations</label>
        <input
          type="number"
          v-model.number="localValue.standard_deviations"
          @input="onConfigChange"
          placeholder="1.0"
          class="strike-input"
          step="0.1"
          min="0.1"
          max="3.0"
        />
        <div class="checkbox-group">
          <label class="checkbox-label">
            <input
              type="checkbox"
              v-model="localValue.outside_sd"
              @change="onConfigChange"
            />
            <span>Outside (farther from spot)</span>
          </label>
        </div>
        <div class="quick-select">
          <span class="quick-label">Quick Select:</span>
          <button
            v-for="preset in sdPresets"
            :key="preset"
            @click="selectSDPreset(preset)"
            class="preset-btn"
            :class="{ 'active': localValue.standard_deviations === preset }"
            type="button"
          >
            {{ preset }}σ
          </button>
        </div>
      </div>

      <!-- Preview -->
      <div v-if="preview && !loadingPreview" class="preview-section">
        <div class="preview-label">Preview:</div>
        <div class="preview-content">
          <span class="preview-strike">~{{ preview.strike }} {{ optionType }}</span>
          <span class="preview-price">@ ₹{{ preview.ltp }}</span>
          <span v-if="preview.delta" class="preview-delta">({{ preview.delta }}Δ)</span>
        </div>
      </div>

      <div v-if="loadingPreview" class="loading-preview">
        <span class="spinner"></span> Loading preview...
      </div>

      <div v-if="previewError" class="preview-error">
        {{ previewError }}
      </div>
    </div>

    <!-- Advanced Options -->
    <div class="advanced-options" v-if="['delta_based', 'premium_based', 'sd_based'].includes(localValue.mode)">
      <label class="checkbox-label">
        <input
          type="checkbox"
          v-model="localValue.prefer_round_strike"
          @change="onConfigChange"
        />
        <span>Prefer round strikes (divisible by 100)</span>
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
      modes: [
        { value: 'fixed', label: 'Fixed Strike' },
        { value: 'atm_offset', label: 'ATM Offset' },
        { value: 'delta_based', label: 'Delta' },
        { value: 'premium_based', label: 'Premium' },
        { value: 'sd_based', label: 'SD' }
      ],
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
      // Only fetch preview for modes that need it
      if (!['delta_based', 'premium_based', 'sd_based'].includes(this.localValue.mode)) {
        this.preview = null
        return
      }

      // Validate required fields
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

        if (this.localValue.mode === 'delta_based') {
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
        this.previewError = 'Unable to load preview'
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
.strike-selector {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.section-label {
  display: block;
  font-weight: 600;
  font-size: 14px;
  color: #374151;
  margin-bottom: 12px;
}

.mode-options {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mode-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f9fafb;
}

.mode-option:hover {
  border-color: #3b82f6;
  background: #eff6ff;
}

.mode-option.active {
  border-color: #3b82f6;
  background: #dbeafe;
}

.mode-option input[type="radio"] {
  margin: 0;
}

.mode-label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.mode-config {
  margin-top: 16px;
}

.config-section {
  margin-bottom: 16px;
}

.config-section label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 6px;
}

.strike-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.strike-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.offset-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.offset-hint {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.quick-select {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.preset-btn {
  padding: 4px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background: #f9fafb;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-btn:hover {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #3b82f6;
}

.preset-btn.active {
  border-color: #3b82f6;
  background: #3b82f6;
  color: #ffffff;
}

.checkbox-group,
.advanced-options {
  margin-top: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.preview-section {
  margin-top: 16px;
  padding: 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
}

.preview-label {
  font-size: 12px;
  font-weight: 600;
  color: #0369a1;
  margin-bottom: 6px;
}

.preview-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-strike {
  font-size: 14px;
  font-weight: 600;
  color: #0c4a6e;
}

.preview-price {
  font-size: 14px;
  color: #0369a1;
}

.preview-delta {
  font-size: 12px;
  color: #0369a1;
  font-weight: 500;
}

.loading-preview {
  margin-top: 16px;
  padding: 12px;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.spinner {
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

.preview-error {
  margin-top: 16px;
  padding: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  font-size: 13px;
  color: #991b1b;
}

.advanced-options {
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}
</style>
