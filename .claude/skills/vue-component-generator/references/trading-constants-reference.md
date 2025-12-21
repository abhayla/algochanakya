# Trading Constants Reference for Vue Components

**NEVER hardcode** lot sizes, strike steps, or index tokens in Vue components.

**For complete documentation, see:** `.claude/skills/trading-constants-manager/references/constants-reference.md`

---

## Quick Reference

### Import Constants

```javascript
import { getLotSize, getStrikeStep, getIndexToken, getIndexSymbol } from '@/constants/trading'
```

---

## Common Use Cases in Vue Components

### Lot Size Calculation

```vue
<script setup>
import { ref, computed } from 'vue'
import { getLotSize } from '@/constants/trading'

const underlying = ref('NIFTY')
const lots = ref(2)

const lotSize = computed(() => getLotSize(underlying.value))  // 25

const totalQuantity = computed(() => {
  return lots.value * lotSize.value  // 50
})
</script>

<template>
  <div>
    <p>Lot Size: {{ lotSize }}</p>
    <p>Total Quantity: {{ totalQuantity }}</p>
  </div>
</template>
```

---

### Strike Rounding

```vue
<script setup>
import { computed } from 'vue'
import { getStrikeStep } from '@/constants/trading'
import { storeToRefs } from 'pinia'
import { useMarketDataStore } from '@/stores/marketData'

const marketStore = useMarketDataStore()
const { spotPrice } = storeToRefs(marketStore)

const underlying = 'NIFTY'

const strikeStep = computed(() => getStrikeStep(underlying))  // 100

const atmStrike = computed(() => {
  return Math.round(spotPrice.value / strikeStep.value) * strikeStep.value
})

const otmStrike = computed(() => {
  return atmStrike.value + (2 * strikeStep.value)  // 2 strikes OTM
})
</script>

<template>
  <div>
    <p>Spot: {{ spotPrice }}</p>
    <p>ATM Strike: {{ atmStrike }}</p>
    <p>OTM Strike: {{ otmStrike }}</p>
  </div>
</template>
```

---

### Index Token for WebSocket

```vue
<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { useWebSocketStore } from '@/stores/websocket'
import { getIndexToken } from '@/constants/trading'

const wsStore = useWebSocketStore()
const { ticks } = storeToRefs(wsStore)

// Get index tokens
const niftyToken = getIndexToken('NIFTY')  // 256265
const bankniftyToken = getIndexToken('BANKNIFTY')  // 260105

onMounted(() => {
  // Subscribe to index ticks
  wsStore.subscribe([niftyToken, bankniftyToken], 'quote')
})

onBeforeUnmount(() => {
  // Unsubscribe on unmount
  wsStore.unsubscribe([niftyToken, bankniftyToken])
})
</script>

<template>
  <div>
    <p>NIFTY: {{ ticks[niftyToken]?.ltp || '--' }}</p>
    <p>BANKNIFTY: {{ ticks[bankniftyToken]?.ltp || '--' }}</p>
  </div>
</template>
```

---

### Dropdown with Underlyings

```vue
<script setup>
import { ref } from 'vue'
import { UNDERLYINGS } from '@/constants/trading'

const selectedUnderlying = ref('NIFTY')
</script>

<template>
  <select
    v-model="selectedUnderlying"
    data-testid="strategy-builder-underlying-dropdown"
  >
    <option
      v-for="u in UNDERLYINGS.value"
      :key="u"
      :value="u"
      :data-testid="`strategy-builder-underlying-option-${u.toLowerCase()}`"
    >
      {{ u }}
    </option>
  </select>
</template>
```

---

## Available Helper Functions

| Function | Returns | Example |
|----------|---------|---------|
| `getLotSize(underlying)` | number | `getLotSize('NIFTY')` → 25 |
| `getStrikeStep(underlying)` | number | `getStrikeStep('NIFTY')` → 100 |
| `getIndexToken(underlying)` | number | `getIndexToken('NIFTY')` → 256265 |
| `getIndexSymbol(underlying)` | string | `getIndexSymbol('NIFTY')` → "NSE:NIFTY 50" |
| `getAllIndexTokens()` | array | `[256265, 260105, 257801, 265]` |
| `isValidUnderlying(underlying)` | boolean | `isValidUnderlying('NIFTY')` → true |

---

## Reactive Constants

```javascript
import { UNDERLYINGS, LOT_SIZES, STRIKE_STEPS, INDEX_TOKENS } from '@/constants/trading'

// These are ComputedRef, use .value to access
const underlyings = UNDERLYINGS.value  // ['NIFTY', 'BANKNIFTY', ...]
const lotSizes = LOT_SIZES.value  // { NIFTY: 25, BANKNIFTY: 15, ... }
const strikeSteps = STRIKE_STEPS.value  // { NIFTY: 100, BANKNIFTY: 100, ... }
```

---

## Anti-Patterns

### ❌ WRONG - Hardcoded Values

```vue
<script setup>
const lotSize = 25  // Hardcoded!
const strikeStep = 50  // Hardcoded!
</script>
```

### ❌ WRONG - If/Else Chains

```vue
<script setup>
let lotSize
if (underlying.value === 'NIFTY') {
  lotSize = 25
} else if (underlying.value === 'BANKNIFTY') {
  lotSize = 15
}
</script>
```

### ✅ RIGHT - Use Helper Functions

```vue
<script setup>
import { computed } from 'vue'
import { getLotSize, getStrikeStep } from '@/constants/trading'

const underlying = ref('NIFTY')

const lotSize = computed(() => getLotSize(underlying.value))
const strikeStep = computed(() => getStrikeStep(underlying.value))
</script>
```

---

## Rules

1. **Import from @/constants/trading** - Never hardcode
2. **Use computed()** - For reactive values based on underlying
3. **Helper functions** - Use getLotSize(), getStrikeStep(), etc.
4. **Reactive constants** - Access .value for ComputedRef constants
5. **Type safety** - All functions return correct types
6. **Validation** - Use isValidUnderlying() to check validity
