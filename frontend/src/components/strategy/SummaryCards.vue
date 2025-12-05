<template>
  <div class="grid grid-cols-5 gap-4 p-4 bg-gray-50 border-t border-gray-200">
    <!-- Max Profit -->
    <div class="bg-white rounded-xl border border-green-200 p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
          <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
          </svg>
        </div>
        <span class="text-xs font-medium text-gray-500 uppercase">Max Profit</span>
      </div>
      <div class="text-2xl font-bold text-green-600">{{ formatNum(maxProfit) }}</div>
    </div>

    <!-- Max Loss -->
    <div class="bg-white rounded-xl border border-red-200 p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center">
          <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/>
          </svg>
        </div>
        <span class="text-xs font-medium text-gray-500 uppercase">Max Loss</span>
      </div>
      <div class="text-2xl font-bold text-red-600">{{ formatNum(maxLoss) }}</div>
    </div>

    <!-- Breakeven -->
    <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
          <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/>
          </svg>
        </div>
        <span class="text-xs font-medium text-gray-500 uppercase">Breakeven</span>
      </div>
      <div class="text-lg font-bold text-gray-800">
        {{ breakeven.length >= 2 ? formatNum(breakeven[0]) + ' - ' + formatNum(breakeven[1]) : (breakeven.length === 1 ? formatNum(breakeven[0]) : '-') }}
      </div>
    </div>

    <!-- Risk/Reward -->
    <div class="bg-white rounded-xl border border-blue-200 p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
          <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
          </svg>
        </div>
        <span class="text-xs font-medium text-gray-500 uppercase">Risk/Reward</span>
      </div>
      <div class="text-2xl font-bold text-blue-600">{{ riskReward }}</div>
    </div>

    <!-- Current Spot -->
    <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl border-2 border-yellow-300 p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-8 h-8 rounded-lg bg-yellow-200 flex items-center justify-center">
          <div class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></div>
        </div>
        <span class="text-xs font-medium text-yellow-700 uppercase">{{ underlying }} Spot</span>
      </div>
      <div class="text-2xl font-bold text-yellow-700">{{ formatNum(currentSpot) }}</div>
      <div class="text-xs text-yellow-600 mt-1">{{ lastUpdated }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  maxProfit: { type: Number, default: 0 },
  maxLoss: { type: Number, default: 0 },
  breakeven: { type: Array, default: () => [] },
  riskReward: { type: String, default: '-' },
  currentSpot: { type: Number, default: 0 },
  underlying: { type: String, default: 'NIFTY' },
  lastUpdated: { type: String, default: '' }
});

const formatNum = (n) => n ? new Intl.NumberFormat('en-IN').format(Math.round(n)) : '-';
</script>
