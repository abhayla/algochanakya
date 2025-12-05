<template>
  <div class="mt-4 flex items-center justify-between text-sm text-gray-500">
    <div class="flex items-center gap-4">
      <span v-if="lastUpdated">
        Last Updated: {{ formatDateTime(lastUpdated) }}
      </span>
      <span v-else>
        Not calculated yet
      </span>
    </div>
    <div class="flex items-center gap-4">
      <span v-if="currentSpot">
        {{ underlying }} Spot: <span class="font-medium text-gray-900">{{ currentSpot.toFixed(2) }}</span>
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  lastUpdated: {
    type: Date,
    default: null
  },
  currentSpot: {
    type: Number,
    default: 0
  },
  underlying: {
    type: String,
    default: 'NIFTY'
  }
})

function formatDateTime(date) {
  if (!date) return ''
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>
