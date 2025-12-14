<template>
  <div class="staged-entry-config" data-testid="staged-entry-config">
    <!-- Staged Entry Toggle -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Staged Entry</h3>
        <p class="text-sm text-gray-600">
          Enter position in stages: half-size or staggered legs
        </p>
      </div>
      <label class="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          v-model="localConfig.enabled"
          class="sr-only peer"
          data-testid="staged-entry-toggle"
          @change="emitUpdate"
        >
        <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
      </label>
    </div>

    <!-- Configuration Panel (shown when enabled) -->
    <div v-if="localConfig.enabled" class="mt-4 space-y-4">
      <!-- Mode Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Entry Mode
        </label>
        <div class="grid grid-cols-2 gap-3">
          <button
            @click="selectMode('half_size')"
            :class="[
              'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
              localConfig.mode === 'half_size'
                ? 'border-blue-600 bg-blue-50 text-blue-700'
                : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
            ]"
            data-testid="mode-half-size-button"
          >
            <div class="text-left">
              <div class="font-semibold">Half-Size Entry</div>
              <div class="text-xs mt-1">Start 50%, add remaining</div>
            </div>
          </button>
          <button
            @click="selectMode('staggered')"
            :class="[
              'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
              localConfig.mode === 'staggered'
                ? 'border-blue-600 bg-blue-50 text-blue-700'
                : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
            ]"
            data-testid="mode-staggered-button"
          >
            <div class="text-left">
              <div class="font-semibold">Staggered Entry</div>
              <div class="text-xs mt-1">Time legs independently</div>
            </div>
          </button>
        </div>
      </div>

      <!-- Half-Size Configuration -->
      <div v-if="localConfig.mode === 'half_size'" class="space-y-4">
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 class="font-semibold text-blue-900 mb-2">How it works</h4>
          <p class="text-sm text-blue-800">
            Enter 50% of position initially. Add remaining 50% when market moves in your favor.
          </p>
        </div>

        <!-- Initial Stage -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-gray-900 mb-3">Stage 1: Initial Entry (50%)</h4>

          <!-- Legs Selection -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Apply to legs
            </label>
            <select
              v-model="localConfig.config.initial_stage.legs[0]"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="half-size-legs-select"
              @change="emitUpdate"
            >
              <option value="all">All Legs</option>
              <option v-for="leg in availableLegs" :key="leg.id" :value="leg.id">
                {{ leg.label }}
              </option>
            </select>
          </div>

          <!-- Lot Multiplier -->
          <div class="mt-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Lot Size: {{ (localConfig.config.initial_stage.lots_multiplier * 100).toFixed(0) }}%
            </label>
            <input
              type="range"
              v-model.number="localConfig.config.initial_stage.lots_multiplier"
              min="0.1"
              max="1.0"
              step="0.1"
              class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              data-testid="half-size-initial-multiplier"
              @input="emitUpdate"
            >
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>10%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        <!-- Add Stage -->
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-gray-900 mb-3">Stage 2: Add Remaining</h4>

          <!-- Trigger Condition -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Add when:
            </label>
            <div class="grid grid-cols-3 gap-2">
              <select
                v-model="localConfig.config.add_stage.condition.variable"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="half-size-add-variable"
                @change="emitUpdate"
              >
                <option value="SPOT.CHANGE_PCT">Spot moves %</option>
                <option value="VOLATILITY.VIX">VIX drops to</option>
                <option value="TIME.CURRENT">Time reaches</option>
              </select>

              <select
                v-model="localConfig.config.add_stage.condition.operator"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="half-size-add-operator"
                @change="emitUpdate"
              >
                <option value="greater_than">></option>
                <option value="less_than"><</option>
                <option value="equals">=</option>
              </select>

              <input
                type="text"
                v-model="localConfig.config.add_stage.condition.value"
                placeholder="Value"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="half-size-add-value"
                @input="emitUpdate"
              >
            </div>
          </div>

          <!-- Add Lot Multiplier -->
          <div class="mt-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Additional Lots: {{ (localConfig.config.add_stage.lots_multiplier * 100).toFixed(0) }}%
            </label>
            <input
              type="range"
              v-model.number="localConfig.config.add_stage.lots_multiplier"
              min="0.1"
              max="1.0"
              step="0.1"
              class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              data-testid="half-size-add-multiplier"
              @input="emitUpdate"
            >
          </div>
        </div>
      </div>

      <!-- Staggered Configuration -->
      <div v-if="localConfig.mode === 'staggered'" class="space-y-4">
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 class="font-semibold text-blue-900 mb-2">How it works</h4>
          <p class="text-sm text-blue-800">
            Enter different legs at different times based on independent conditions.
          </p>
        </div>

        <!-- Leg Entries -->
        <div
          v-for="(entry, index) in localConfig.config.leg_entries"
          :key="index"
          class="bg-gray-50 rounded-lg p-4 relative"
        >
          <div class="flex items-start justify-between mb-3">
            <h4 class="font-medium text-gray-900">Stage {{ index + 1 }}</h4>
            <button
              v-if="localConfig.config.leg_entries.length > 1"
              @click="removeLegEntry(index)"
              class="text-red-600 hover:text-red-700 text-sm"
              data-testid="remove-stage-button"
            >
              Remove
            </button>
          </div>

          <!-- Leg Selection -->
          <div class="mb-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Legs to enter
            </label>
            <select
              v-model="entry.leg_ids"
              multiple
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :data-testid="`staggered-legs-select-${index}`"
              @change="emitUpdate"
            >
              <option v-for="leg in availableLegs" :key="leg.id" :value="leg.id">
                {{ leg.label }}
              </option>
            </select>
          </div>

          <!-- Entry Condition -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Enter when:
            </label>
            <div class="grid grid-cols-3 gap-2">
              <select
                v-model="entry.condition.variable"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                :data-testid="`staggered-variable-${index}`"
                @change="emitUpdate"
              >
                <option value="">Immediate</option>
                <option value="TIME.CURRENT">Time</option>
                <option value="VOLATILITY.VIX">VIX</option>
                <option value="SPOT.CHANGE_PCT">Spot %</option>
              </select>

              <select
                v-if="entry.condition.variable"
                v-model="entry.condition.operator"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                :data-testid="`staggered-operator-${index}`"
                @change="emitUpdate"
              >
                <option value="greater_than">></option>
                <option value="less_than"><</option>
                <option value="equals">=</option>
              </select>

              <input
                v-if="entry.condition.variable"
                type="text"
                v-model="entry.condition.value"
                placeholder="Value"
                class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                :data-testid="`staggered-value-${index}`"
                @input="emitUpdate"
              >
            </div>
          </div>

          <!-- Lot Multiplier -->
          <div class="mt-3">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Lot Size: {{ (entry.lots_multiplier * 100).toFixed(0) }}%
            </label>
            <input
              type="range"
              v-model.number="entry.lots_multiplier"
              min="0.1"
              max="1.0"
              step="0.1"
              class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              :data-testid="`staggered-multiplier-${index}`"
              @input="emitUpdate"
            >
          </div>
        </div>

        <!-- Add Stage Button -->
        <button
          @click="addLegEntry"
          class="w-full py-2 px-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-500 hover:text-blue-600 transition-colors"
          data-testid="add-staggered-stage-button"
        >
          + Add Another Stage
        </button>
      </div>

      <!-- Preview/Summary -->
      <div class="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
        <h4 class="font-semibold text-green-900 mb-2">
          <span v-if="localConfig.mode === 'half_size'">Half-Size Entry Summary</span>
          <span v-else>Staggered Entry Summary</span>
        </h4>
        <div class="text-sm text-green-800">
          <div v-if="localConfig.mode === 'half_size'">
            <p>✓ Enter {{ (localConfig.config.initial_stage.lots_multiplier * 100).toFixed(0) }}% position initially</p>
            <p>✓ Add {{ (localConfig.config.add_stage.lots_multiplier * 100).toFixed(0) }}% when {{ localConfig.config.add_stage.condition.variable }} {{ localConfig.config.add_stage.condition.operator }} {{ localConfig.config.add_stage.condition.value }}</p>
          </div>
          <div v-else>
            <p>✓ Total stages: {{ localConfig.config.leg_entries.length }}</p>
            <p v-for="(entry, index) in localConfig.config.leg_entries" :key="index">
              ✓ Stage {{ index + 1 }}: {{ entry.leg_ids.length }} leg(s) at {{ (entry.lots_multiplier * 100).toFixed(0) }}%
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StagedEntryConfig',
  props: {
    modelValue: {
      type: Object,
      default: () => null
    },
    availableLegs: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      localConfig: this.getDefaultConfig()
    }
  },
  watch: {
    modelValue: {
      handler(newVal) {
        if (newVal) {
          this.localConfig = { ...this.getDefaultConfig(), ...newVal }
        } else {
          this.localConfig = this.getDefaultConfig()
        }
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    getDefaultConfig() {
      return {
        enabled: false,
        mode: 'half_size',
        config: {
          initial_stage: {
            legs: ['all'],
            lots_multiplier: 0.5
          },
          add_stage: {
            condition: {
              id: 'add_condition_1',
              enabled: true,
              variable: 'SPOT.CHANGE_PCT',
              operator: 'greater_than',
              value: 1.0
            },
            lots_multiplier: 0.5
          },
          leg_entries: [
            {
              leg_ids: [],
              condition: {
                id: 'stage_1',
                enabled: true,
                variable: '',
                operator: 'equals',
                value: ''
              },
              lots_multiplier: 1.0
            }
          ]
        }
      }
    },
    selectMode(mode) {
      this.localConfig.mode = mode
      this.emitUpdate()
    },
    addLegEntry() {
      this.localConfig.config.leg_entries.push({
        leg_ids: [],
        condition: {
          id: `stage_${this.localConfig.config.leg_entries.length + 1}`,
          enabled: true,
          variable: '',
          operator: 'equals',
          value: ''
        },
        lots_multiplier: 1.0
      })
      this.emitUpdate()
    },
    removeLegEntry(index) {
      this.localConfig.config.leg_entries.splice(index, 1)
      this.emitUpdate()
    },
    emitUpdate() {
      this.$emit('update:modelValue', this.localConfig.enabled ? this.localConfig : null)
    }
  }
}
</script>

<style scoped>
.staged-entry-config {
  @apply bg-white rounded-lg p-6 border border-gray-200;
}
</style>
