<template>
  <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm h-full">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-semibold text-gray-700">Payoff Diagram</h3>
      <div class="flex gap-3 text-xs">
        <span class="flex items-center text-green-600">
          <span class="w-3 h-0.5 bg-green-500 mr-1"></span> Profit
        </span>
        <span class="flex items-center text-red-600">
          <span class="w-3 h-0.5 bg-red-500 mr-1"></span> Loss
        </span>
      </div>
    </div>
    <div class="h-48">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';
import Chart from 'chart.js/auto';

const props = defineProps({
  spotPrices: { type: Array, default: () => [] },
  totalPnl: { type: Array, default: () => [] },
  currentSpot: { type: Number, default: 0 }
});

const chartCanvas = ref(null);
let chartInstance = null;

const splitPnlData = (pnlArray) => {
  const profitData = pnlArray.map(val => val >= 0 ? val : 0);
  const lossData = pnlArray.map(val => val <= 0 ? val : 0);
  return { profitData, lossData };
};

const createChart = () => {
  if (!chartCanvas.value || !props.spotPrices.length) return;
  if (chartInstance) chartInstance.destroy();

  const ctx = chartCanvas.value.getContext('2d');
  const { profitData, lossData } = splitPnlData(props.totalPnl);

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: props.spotPrices,
      datasets: [
        {
          label: 'Profit',
          data: profitData,
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.1)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.1,
          fill: true
        },
        {
          label: 'Loss',
          data: lossData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.1)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.1,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => 'Spot: ' + items[0].label,
            label: (item) => 'P/L: ₹' + item.raw.toLocaleString('en-IN')
          }
        }
      },
      scales: {
        x: { display: true, grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
        y: { display: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 } } }
      }
    }
  });
};

watch(() => [props.spotPrices, props.totalPnl], createChart, { deep: true });
onMounted(createChart);
onUnmounted(() => { if (chartInstance) chartInstance.destroy(); });
</script>
