<script setup>
/**
 * Sparkline Chart Component
 *
 * Simple SVG-based line chart for showing trends
 */
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  width: {
    type: Number,
    default: 100
  },
  height: {
    type: Number,
    default: 30
  },
  strokeWidth: {
    type: Number,
    default: 2
  },
  color: {
    type: String,
    default: '#3b82f6'
  }
})

// Calculate SVG path
const path = computed(() => {
  if (!props.data || props.data.length === 0) return ''

  const points = props.data
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1

  const xStep = props.width / (points.length - 1 || 1)

  const pathData = points.map((value, index) => {
    const x = index * xStep
    const y = props.height - ((value - min) / range) * props.height
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')

  return pathData
})

// Determine color based on trend
const strokeColor = computed(() => {
  if (!props.data || props.data.length < 2) return props.color

  const first = props.data[0]
  const last = props.data[props.data.length - 1]

  if (last > first) return 'var(--kite-green)'
  if (last < first) return 'var(--kite-red)'
  return 'var(--kite-text-muted)'
})
</script>

<template>
  <svg :width="width" :height="height" class="sparkline">
    <path
      v-if="path"
      :d="path"
      fill="none"
      :stroke="strokeColor"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<style scoped>
.sparkline {
  display: block;
}
</style>
