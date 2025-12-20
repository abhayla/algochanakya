<template>
  <div
    class="autopilot-badge"
    :class="{ 'badge-clickable': strategy.id }"
    :title="`AutoPilot ${tradingModeLabel} - ${strategy.name || 'Unknown Strategy'}`"
    @click="handleClick"
    data-testid="positions-autopilot-badge"
  >
    <!-- Robot Icon -->
    <span class="robot-icon">🤖</span>

    <!-- AP Text -->
    <span class="badge-text">AP</span>

    <!-- Mode Indicator Dot -->
    <span
      class="mode-dot"
      :class="tradingMode === 'live' ? 'dot-live' : 'dot-paper'"
      :title="tradingModeLabel"
    ></span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  strategy: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && (value.id !== undefined || value.id !== null)
    }
  }
})

const router = useRouter()

const tradingMode = computed(() => {
  return props.strategy.trading_mode || 'paper'
})

const tradingModeLabel = computed(() => {
  return tradingMode.value === 'live' ? 'Live Trading' : 'Paper Trading'
})

const handleClick = () => {
  if (props.strategy.id) {
    router.push(`/autopilot/strategies/${props.strategy.id}`)
  }
}
</script>

<style scoped>
.autopilot-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #0369a1;
  transition: all 0.2s;
  user-select: none;
}

.badge-clickable {
  cursor: pointer;
}

.badge-clickable:hover {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-color: #7dd3fc;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(3, 105, 161, 0.15);
}

.robot-icon {
  font-size: 14px;
  line-height: 1;
}

.badge-text {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.mode-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-live {
  background-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
  animation: pulse-live 2s infinite;
}

.dot-paper {
  background-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
}

@keyframes pulse-live {
  0%, 100% {
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.4);
  }
}

/* Tooltip enhancement */
.autopilot-badge::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 8px;
  background: linear-gradient(135deg, transparent, rgba(3, 105, 161, 0.1));
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.badge-clickable:hover::before {
  opacity: 1;
}
</style>
