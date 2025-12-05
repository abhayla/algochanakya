<template>
  <td :class="['px-2 py-2 text-right text-xs font-medium transition-all', cellClass, isSpotColumn ? 'ring-2 ring-yellow-400 ring-inset' : '']">
    {{ formatValue(value) }}
  </td>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  value: { type: Number, default: 0 },
  maxProfit: { type: Number, default: 1 },
  maxLoss: { type: Number, default: -1 },
  isSpotColumn: { type: Boolean, default: false },
  isTotal: { type: Boolean, default: false }
});

const formatValue = (v) => {
  if (v === null || v === undefined) return '-';
  return Math.abs(v) >= 1000 ? (v/1000).toFixed(1) + 'K' : v.toLocaleString('en-IN');
};

const cellClass = computed(() => {
  const v = props.value;
  if (v === null || v === undefined) return 'bg-gray-50 text-gray-500';

  if (v > 0) {
    const i = Math.min(v / (props.maxProfit || 1), 1);
    if (props.isTotal) return i > 0.5 ? 'bg-green-600 text-white font-bold' : 'bg-green-400 text-white font-semibold';
    if (i > 0.6) return 'bg-green-400 text-green-950';
    if (i > 0.3) return 'bg-green-200 text-green-800';
    return 'bg-green-100 text-green-700';
  } else {
    const i = Math.min(Math.abs(v) / (Math.abs(props.maxLoss) || 1), 1);
    if (props.isTotal) return i > 0.5 ? 'bg-red-600 text-white font-bold' : 'bg-red-400 text-white font-semibold';
    if (i > 0.6) return 'bg-red-400 text-red-950';
    if (i > 0.3) return 'bg-red-200 text-red-800';
    return 'bg-red-100 text-red-700';
  }
});
</script>
