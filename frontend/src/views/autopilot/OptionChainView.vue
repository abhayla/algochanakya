<template>
  <KiteLayout>
    <div class="optionchain-view" data-testid="autopilot-optionchain-view">
      <div class="view-header">
        <h1>Option Chain</h1>
        <p class="subtitle">View option chain with Greeks, OI, and volume data</p>
      </div>

      <!-- Option Chain Header with Controls -->
      <OptionChainHeader
        v-model:underlying="underlying"
        v-model:expiry="selectedExpiry"
        v-model:showGreeks="filters.showGreeks"
        :expiries="expiries"
        :loading="loading"
        @refresh="refreshOptionChain"
        @toggle-strike-finder="showStrikeFinder = !showStrikeFinder"
      />

      <!-- Strike Finder Panel -->
      <StrikeFinder
        :visible="showStrikeFinder"
        :underlying="underlying"
        :expiry="selectedExpiry"
        @close="showStrikeFinder = false"
        @select-strike="handleStrikeSelected"
      />

      <!-- Option Chain Table -->
      <OptionChainTable
        v-if="!loading || optionChainData"
        :groupedByStrike="groupedByStrike"
        :spotPrice="spotPrice"
        :atmStrike="atmStrike"
        :showGreeks="filters.showGreeks"
        :loading="loading"
        :isCached="isCached"
        :cachedAt="cachedAt"
        :error="error"
        @option-selected="handleOptionSelected"
      />
    </div>
  </KiteLayout>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useOptionChain } from '@/composables/autopilot/useOptionChain'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import OptionChainHeader from '@/components/autopilot/optionchain/OptionChainHeader.vue'
import StrikeFinder from '@/components/autopilot/optionchain/StrikeFinder.vue'
import OptionChainTable from '@/components/autopilot/optionchain/OptionChainTable.vue'

const router = useRouter()

const {
  underlying,
  selectedExpiry,
  expiries,
  optionChainData,
  loading,
  error,
  filters,
  groupedByStrike,
  atmStrike,
  spotPrice,
  isCached,
  cachedAt,
  fetchExpiries,
  fetchOptionChain,
  refreshOptionChain
} = useOptionChain()

const showStrikeFinder = ref(false)

onMounted(async () => {
  // Initialize with NIFTY
  underlying.value = 'NIFTY'
  await fetchExpiries()

  // Select first expiry if available
  if (expiries.value.length > 0) {
    selectedExpiry.value = expiries.value[0]
    await fetchOptionChain()
  }
})

// Watch underlying changes to fetch new expiries
watch(() => underlying.value, async (newUnderlying) => {
  if (newUnderlying) {
    selectedExpiry.value = null
    await fetchExpiries()

    // Auto-select first expiry
    if (expiries.value.length > 0) {
      selectedExpiry.value = expiries.value[0]
      await fetchOptionChain()
    }
  }
})

// Watch expiry changes to fetch option chain
watch(() => selectedExpiry.value, async (newExpiry) => {
  if (newExpiry) {
    await fetchOptionChain()
  }
})

const handleOptionSelected = (option) => {
  console.log('Option selected:', option)
  // Can emit event or navigate to strategy builder with pre-filled option
}

const handleStrikeSelected = (strike) => {
  showStrikeFinder.value = false
  console.log('Strike selected from finder:', strike)
  // Optionally scroll to the strike row in the table
}
</script>

<style scoped>
.optionchain-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.view-header {
  margin-bottom: 24px;
}

.view-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}
</style>
