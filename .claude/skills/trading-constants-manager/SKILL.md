---
name: trading-constants-manager
description: Enforce centralized trading constants usage. Use when writing code with "NIFTY", "BANKNIFTY", hardcoded lot sizes (50, 15, 25), strike steps (50, 100), or index tokens. Triggers on trading calculations, strategy builders, or option chain logic.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Trading Constants Manager

Ensure trading constants are NEVER hardcoded. Always import from centralized constants modules.

## When to Use

- User writes code involving lot sizes
- User adds code with strike steps
- User uses index tokens or symbols
- User writes any trading-related calculation
- User creates new features involving underlyings (NIFTY, BANKNIFTY, etc.)

## When NOT to Use

- Non-trading code (general utilities, UI layouts)
- Just querying or reading constants (no code being written)

## Critical Rule

**NEVER hardcode lot sizes, strike steps, or index tokens.**

All trading parameters MUST be imported from:
- **Backend:** `app/constants/trading.py`
- **Frontend:** `src/constants/trading.js`

## Backend Usage

### Import Pattern

```python
from app.constants.trading import (
    get_lot_size,
    get_strike_step,
    get_index_token,
    get_index_symbol,
    UNDERLYINGS,
    LOT_SIZES,
    STRIKE_STEPS,
    INDEX_TOKENS
)
```

### Examples

#### ❌ WRONG - Hardcoded Values
```python
# NEVER do this
lot_size = 25  # Hardcoded!
strike_step = 50  # Hardcoded!

# NEVER do this
if underlying == "NIFTY":
    lot_size = 25
elif underlying == "BANKNIFTY":
    lot_size = 15
```

#### ✅ RIGHT - Use Helper Functions
```python
from app.constants.trading import get_lot_size, get_strike_step

# Calculate position size
lot_size = get_lot_size("NIFTY")  # Returns 25
total_qty = lots * lot_size

# Round strike to nearest valid strike
strike_step = get_strike_step("BANKNIFTY")  # Returns 100
rounded_strike = round(spot_price / strike_step) * strike_step
```

#### ✅ RIGHT - Use Constants Directly
```python
from app.constants.trading import LOT_SIZES, STRIKE_STEPS

# Iterate over all underlyings
for underlying in LOT_SIZES.keys():
    lot_size = LOT_SIZES[underlying]
    print(f"{underlying}: {lot_size} lots")

# Validation
if underlying not in STRIKE_STEPS:
    raise ValueError(f"Invalid underlying: {underlying}")
```

### Available Backend Functions

| Function | Returns | Example |
|----------|---------|---------|
| `get_lot_size(underlying)` | int | `get_lot_size("NIFTY")` → 25 |
| `get_strike_step(underlying)` | int | `get_strike_step("BANKNIFTY")` → 100 |
| `get_index_token(underlying)` | int | `get_index_token("NIFTY")` → 256265 |
| `get_index_symbol(underlying)` | str | `get_index_symbol("NIFTY")` → "NSE:NIFTY 50" |
| `is_valid_underlying(underlying)` | bool | `is_valid_underlying("NIFTY")` → True |

### Available Backend Constants

| Constant | Type | Usage |
|----------|------|-------|
| `UNDERLYINGS` | list | List of valid underlyings |
| `LOT_SIZES` | dict | `{"NIFTY": 25, "BANKNIFTY": 15, ...}` |
| `STRIKE_STEPS` | dict | `{"NIFTY": 100, "BANKNIFTY": 100, ...}` |
| `INDEX_TOKENS` | dict | `{"NIFTY": 256265, ...}` |
| `INDEX_SYMBOLS` | dict | `{"NIFTY": "NSE:NIFTY 50", ...}` |
| `INDEX_EXCHANGES` | dict | `{"NIFTY": "NSE", "SENSEX": "BSE", ...}` |

---

## Frontend Usage

### Import Pattern

```javascript
import {
  getLotSize,
  getStrikeStep,
  getIndexToken,
  getIndexSymbol,
  getAllIndexTokens,
  isValidUnderlying,
  UNDERLYINGS,
  LOT_SIZES,
  STRIKE_STEPS
} from '@/constants/trading'
```

### Examples

#### ❌ WRONG - Hardcoded Values
```javascript
// NEVER do this
const lotSize = 25  // Hardcoded!
const strikeStep = 50  // Hardcoded!

// NEVER do this
let lotSize
if (underlying === 'NIFTY') {
  lotSize = 25
} else if (underlying === 'BANKNIFTY') {
  lotSize = 15
}
```

#### ✅ RIGHT - Use Helper Functions
```javascript
import { getLotSize, getStrikeStep } from '@/constants/trading'

// Calculate total quantity
const lotSize = getLotSize('NIFTY')  // Returns 25
const totalQty = lots * lotSize

// Round strike to nearest valid strike
const strikeStep = getStrikeStep('BANKNIFTY')  // Returns 100
const roundedStrike = Math.round(spotPrice / strikeStep) * strikeStep
```

#### ✅ RIGHT - Use Computed Properties
```javascript
import { getLotSize } from '@/constants/trading'
import { computed } from 'vue'

export const useStrategyStore = defineStore('strategy', () => {
  const underlying = ref('NIFTY')

  // Computed lot size based on current underlying
  const lotSize = computed(() => getLotSize(underlying.value))

  // Total quantity calculation
  const totalQuantity = computed(() => {
    return legs.value.reduce((sum, leg) => {
      return sum + (leg.quantity_multiplier * lotSize.value)
    }, 0)
  })

  return { underlying, lotSize, totalQuantity }
})
```

#### ✅ RIGHT - WebSocket Subscriptions
```javascript
import { getIndexToken, getAllIndexTokens } from '@/constants/trading'

// Subscribe to single index
const niftyToken = getIndexToken('NIFTY')  // Returns 256265
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [niftyToken],
  mode: 'quote'
}))

// Subscribe to all indices
const allTokens = getAllIndexTokens()  // Returns [256265, 260105, 257801, 265]
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: allTokens,
  mode: 'quote'
}))
```

### Available Frontend Functions

| Function | Returns | Example |
|----------|---------|---------|
| `getLotSize(underlying)` | number | `getLotSize('NIFTY')` → 25 |
| `getStrikeStep(underlying)` | number | `getStrikeStep('BANKNIFTY')` → 100 |
| `getIndexToken(underlying)` | number | `getIndexToken('NIFTY')` → 256265 |
| `getIndexSymbol(underlying)` | string | `getIndexSymbol('NIFTY')` → "NSE:NIFTY 50" |
| `getAllIndexTokens()` | array | `[256265, 260105, 257801, 265]` |
| `isValidUnderlying(underlying)` | boolean | `isValidUnderlying('NIFTY')` → true |

### Available Frontend Computed Properties

| Property | Type | Usage |
|----------|------|-------|
| `UNDERLYINGS` | ComputedRef<string[]> | List of valid underlyings |
| `LOT_SIZES` | ComputedRef<Record> | `{ NIFTY: 25, BANKNIFTY: 15, ... }` |
| `STRIKE_STEPS` | ComputedRef<Record> | `{ NIFTY: 100, BANKNIFTY: 100, ... }` |
| `INDEX_TOKENS` | ComputedRef<Record> | `{ NIFTY: 256265, ... }` |
| `INDEX_SYMBOLS` | ComputedRef<Record> | `{ NIFTY: "NSE:NIFTY 50", ... }` |

---

## Common Use Cases

### Use Case 1: P&L Calculation

**Backend:**
```python
from app.constants.trading import get_lot_size

def calculate_pnl(underlying: str, lots: int, entry_price: Decimal, exit_price: Decimal):
    lot_size = get_lot_size(underlying)
    total_qty = lots * lot_size
    pnl = (exit_price - entry_price) * total_qty
    return pnl
```

**Frontend:**
```javascript
import { getLotSize } from '@/constants/trading'

function calculatePnL(underlying, lots, entryPrice, exitPrice) {
  const lotSize = getLotSize(underlying)
  const totalQty = lots * lotSize
  const pnl = (exitPrice - entryPrice) * totalQty
  return pnl
}
```

### Use Case 2: Strike Rounding

**Backend:**
```python
from app.constants.trading import get_strike_step

def round_to_strike(spot_price: Decimal, underlying: str) -> int:
    strike_step = get_strike_step(underlying)
    return int(round(spot_price / strike_step) * strike_step)

# Example: round_to_strike(24567.8, "NIFTY") → 24600
```

**Frontend:**
```javascript
import { getStrikeStep } from '@/constants/trading'

function roundToStrike(spotPrice, underlying) {
  const strikeStep = getStrikeStep(underlying)
  return Math.round(spotPrice / strikeStep) * strikeStep
}

// Example: roundToStrike(24567.8, 'NIFTY') → 24600
```

### Use Case 3: ATM Strike Calculation

**Backend:**
```python
from app.constants.trading import get_strike_step

def get_atm_strike(spot_price: Decimal, underlying: str) -> int:
    strike_step = get_strike_step(underlying)
    atm_strike = round(spot_price / strike_step) * strike_step
    return int(atm_strike)
```

**Frontend:**
```javascript
import { getStrikeStep } from '@/constants/trading'

function getATMStrike(spotPrice, underlying) {
  const strikeStep = getStrikeStep(underlying)
  return Math.round(spotPrice / strikeStep) * strikeStep
}
```

### Use Case 4: OTM Strike Calculation

**Backend:**
```python
from app.constants.trading import get_strike_step

def get_otm_strike(spot_price: Decimal, underlying: str, option_type: str, offset: int) -> int:
    """
    Get OTM strike with offset from ATM
    offset: Number of strikes away from ATM (e.g., 2 means 2 strikes OTM)
    """
    strike_step = get_strike_step(underlying)
    atm_strike = round(spot_price / strike_step) * strike_step

    if option_type == "CE":
        # CE OTM is above spot
        otm_strike = atm_strike + (offset * strike_step)
    else:  # PE
        # PE OTM is below spot
        otm_strike = atm_strike - (offset * strike_step)

    return int(otm_strike)
```

**Frontend:**
```javascript
import { getStrikeStep } from '@/constants/trading'

function getOTMStrike(spotPrice, underlying, optionType, offset) {
  const strikeStep = getStrikeStep(underlying)
  const atmStrike = Math.round(spotPrice / strikeStep) * strikeStep

  if (optionType === 'CE') {
    return atmStrike + (offset * strikeStep)
  } else {
    return atmStrike - (offset * strikeStep)
  }
}
```

---

## Loading Constants (Frontend Only)

Constants are loaded from backend API on app initialization:

**In main.js or App.vue:**
```javascript
import { loadTradingConstants } from '@/constants/trading'

// Load constants before app mounts
await loadTradingConstants()
```

**API Endpoint:**
```
GET /api/constants/trading
```

**Response:**
```json
{
  "underlyings": ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"],
  "lot_sizes": { "NIFTY": 25, "BANKNIFTY": 15, ... },
  "strike_steps": { "NIFTY": 100, "BANKNIFTY": 100, ... },
  "index_tokens": { "NIFTY": 256265, ... },
  "index_symbols": { "NIFTY": "NSE:NIFTY 50", ... }
}
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ImportError: cannot import get_lot_size` | Wrong import path | Use `from app.constants.trading import get_lot_size` (backend) or `import { getLotSize } from '@/constants/trading'` (frontend) |
| `KeyError: 'UNKNOWN'` in `getLotSize()` | Invalid underlying passed | Use `isValidUnderlying()` to check before calling, or add underlying to constants |
| Frontend returns `undefined` for lot size | Constants not loaded yet | Call `await loadTradingConstants()` in `main.js` before mounting app |
| Hardcoded value still in code | Forgot to refactor | Search codebase for magic numbers: `25`, `15`, `100`, `256265` |

---

## Enforcement Checklist

Before committing code:

- [ ] No hardcoded lot sizes (25, 15, 10, etc.)
- [ ] No hardcoded strike steps (50, 100, etc.)
- [ ] No hardcoded index tokens (256265, 260105, etc.)
- [ ] All trading constants imported from centralized modules
- [ ] Backend uses `app/constants/trading.py`
- [ ] Frontend uses `@/constants/trading.js`
- [ ] Helper functions used instead of if/else chains
- [ ] Constants are reactive on frontend (use computed properties)

---

## References

- [Constants Reference](./references/constants-reference.md) - Complete list of all available constants and functions
