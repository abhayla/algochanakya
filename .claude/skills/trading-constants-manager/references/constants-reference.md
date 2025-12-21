# Trading Constants - Complete Reference

Complete reference for all trading constants available in AlgoChanakya.

## Source of Truth

- **Backend:** `D:\Abhay\VibeCoding\algochanakya\backend\app\constants\trading.py`
- **Frontend:** `D:\Abhay\VibeCoding\algochanakya\frontend\src\constants\trading.js`
- **API Endpoint:** `GET /api/constants/trading`

Last Updated: 2025-12-21 (All strike steps set to 100 per user requirement)

---

## Available Underlyings

```python
["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
```

---

## Lot Sizes

Fixed quantity per lot for each underlying.

| Underlying | Lot Size |
|------------|----------|
| NIFTY | 25 |
| BANKNIFTY | 15 |
| FINNIFTY | 25 |
| SENSEX | 10 |
| MIDCPNIFTY | 75 |

**Usage:**
```python
# Backend
from app.constants.trading import get_lot_size
lot_size = get_lot_size("NIFTY")  # 25
```

```javascript
// Frontend
import { getLotSize } from '@/constants/trading'
const lotSize = getLotSize('NIFTY')  // 25
```

---

## Strike Steps

Points between consecutive strike prices (all set to 100).

| Underlying | Strike Step |
|------------|-------------|
| NIFTY | 100 |
| BANKNIFTY | 100 |
| FINNIFTY | 100 |
| SENSEX | 100 |

**Note:** User requirement from 2025-12-21 - All strike steps should be 100 for consistent rounding.

**Usage:**
```python
# Backend
from app.constants.trading import get_strike_step

strike_step = get_strike_step("NIFTY")  # 100

# Round spot price to nearest strike
atm_strike = round(spot_price / strike_step) * strike_step
```

```javascript
// Frontend
import { getStrikeStep } from '@/constants/trading'

const strikeStep = getStrikeStep('NIFTY')  // 100

// Round spot price to nearest strike
const atmStrike = Math.round(spotPrice / strikeStep) * strikeStep
```

---

## Index Tokens

NSE/BSE instrument tokens for WebSocket subscriptions.

| Underlying | Token | Exchange | Description |
|------------|-------|----------|-------------|
| NIFTY | 256265 | NSE | NIFTY 50 |
| BANKNIFTY | 260105 | NSE | NIFTY BANK |
| FINNIFTY | 257801 | NSE | NIFTY FIN SERVICE |
| SENSEX | 265 | BSE | SENSEX |
| INDIAVIX | 264969 | NSE | INDIA VIX |

**Usage:**
```python
# Backend - WebSocket subscription
from app.constants.trading import get_index_token

nifty_token = get_index_token("NIFTY")  # 256265
kite_ticker.subscribe([nifty_token])
```

```javascript
// Frontend - WebSocket subscription
import { getIndexToken } from '@/constants/trading'

const niftyToken = getIndexToken('NIFTY')  // 256265
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [niftyToken],
  mode: 'quote'
}))
```

---

## Index Symbols

Kite Connect trading symbols for LTP API.

| Underlying | Symbol | Exchange |
|------------|--------|----------|
| NIFTY | NSE:NIFTY 50 | NSE |
| BANKNIFTY | NSE:NIFTY BANK | NSE |
| FINNIFTY | NSE:NIFTY FIN SERVICE | NSE |
| SENSEX | BSE:SENSEX | BSE |

**Usage:**
```python
# Backend - Get LTP via Kite API
from app.constants.trading import get_index_symbol

symbol = get_index_symbol("NIFTY")  # "NSE:NIFTY 50"
ltp_data = kite.ltp([symbol])
```

```javascript
// Frontend - Fallback LTP API
import { getIndexSymbol } from '@/constants/trading'

const symbol = getIndexSymbol('NIFTY')  // "NSE:NIFTY 50"
const response = await api.post('/api/orders/ltp', { symbols: [symbol] })
```

---

## Backend Helper Functions

### get_lot_size(underlying: str) -> int

Get lot size for an underlying.

```python
from app.constants.trading import get_lot_size

lot_size = get_lot_size("NIFTY")  # 25
lot_size = get_lot_size("BANKNIFTY")  # 15
lot_size = get_lot_size("UNKNOWN")  # 25 (default)
```

**Returns:** Lot size (defaults to 25 if underlying not found)

---

### get_strike_step(underlying: str) -> int

Get strike step interval for an underlying.

```python
from app.constants.trading import get_strike_step

strike_step = get_strike_step("NIFTY")  # 100
strike_step = get_strike_step("BANKNIFTY")  # 100
strike_step = get_strike_step("UNKNOWN")  # 100 (default)
```

**Returns:** Strike step in points (defaults to 100 if underlying not found)

---

### get_index_token(underlying: str) -> int | None

Get NSE/BSE instrument token for an underlying.

```python
from app.constants.trading import get_index_token

token = get_index_token("NIFTY")  # 256265
token = get_index_token("BANKNIFTY")  # 260105
token = get_index_token("UNKNOWN")  # None
```

**Returns:** Index token or None if underlying not found

---

### get_index_symbol(underlying: str) -> str | None

Get Kite trading symbol for an underlying.

```python
from app.constants.trading import get_index_symbol

symbol = get_index_symbol("NIFTY")  # "NSE:NIFTY 50"
symbol = get_index_symbol("BANKNIFTY")  # "NSE:NIFTY BANK"
symbol = get_index_symbol("UNKNOWN")  # None
```

**Returns:** Trading symbol or None if underlying not found

---

### is_valid_underlying(underlying: str) -> bool

Check if underlying is supported.

```python
from app.constants.trading import is_valid_underlying

is_valid_underlying("NIFTY")  # True
is_valid_underlying("BANKNIFTY")  # True
is_valid_underlying("UNKNOWN")  # False
```

**Returns:** True if underlying is supported, False otherwise

---

## Frontend Helper Functions

### getLotSize(underlying: string) -> number

Get lot size for an underlying.

```javascript
import { getLotSize } from '@/constants/trading'

const lotSize = getLotSize('NIFTY')  // 25
const lotSize = getLotSize('BANKNIFTY')  // 15
const lotSize = getLotSize('UNKNOWN')  // 25 (default)
```

**Returns:** Lot size (defaults to 25)

---

### getStrikeStep(underlying: string) -> number

Get strike step for an underlying.

```javascript
import { getStrikeStep } from '@/constants/trading'

const strikeStep = getStrikeStep('NIFTY')  // 100
const strikeStep = getStrikeStep('BANKNIFTY')  // 100
const strikeStep = getStrikeStep('UNKNOWN')  // 100 (default)
```

**Returns:** Strike step (defaults to 100)

---

### getIndexToken(underlying: string) -> number | undefined

Get index token for an underlying.

```javascript
import { getIndexToken } from '@/constants/trading'

const token = getIndexToken('NIFTY')  // 256265
const token = getIndexToken('BANKNIFTY')  // 260105
const token = getIndexToken('UNKNOWN')  // undefined
```

**Returns:** Index token or undefined if not found

---

### getIndexSymbol(underlying: string) -> string | undefined

Get index trading symbol for an underlying.

```javascript
import { getIndexSymbol } from '@/constants/trading'

const symbol = getIndexSymbol('NIFTY')  // "NSE:NIFTY 50"
const symbol = getIndexSymbol('BANKNIFTY')  // "NSE:NIFTY BANK"
const symbol = getIndexSymbol('UNKNOWN')  // undefined
```

**Returns:** Trading symbol or undefined if not found

---

### getAllIndexTokens() -> number[]

Get all index tokens as array (for WebSocket subscription).

```javascript
import { getAllIndexTokens } from '@/constants/trading'

const tokens = getAllIndexTokens()
// [256265, 260105, 257801, 265]

// Subscribe to all indices
ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: tokens,
  mode: 'quote'
}))
```

**Returns:** Array of all index tokens

---

### isValidUnderlying(underlying: string) -> boolean

Check if an underlying is valid/supported.

```javascript
import { isValidUnderlying } from '@/constants/trading'

isValidUnderlying('NIFTY')  // true
isValidUnderlying('BANKNIFTY')  // true
isValidUnderlying('UNKNOWN')  // false
```

**Returns:** True if supported, false otherwise

---

## Frontend Reactive Constants

These are Vue computed properties that stay reactive.

### UNDERLYINGS

```javascript
import { UNDERLYINGS } from '@/constants/trading'

// In template
<select v-model="selectedUnderlying">
  <option v-for="u in UNDERLYINGS.value" :key="u">{{ u }}</option>
</select>
```

---

### LOT_SIZES

```javascript
import { LOT_SIZES } from '@/constants/trading'

// In computed
const lotSize = computed(() => LOT_SIZES.value[underlying.value])
```

---

### STRIKE_STEPS

```javascript
import { STRIKE_STEPS } from '@/constants/trading'

// In computed
const strikeStep = computed(() => STRIKE_STEPS.value[underlying.value])
```

---

### INDEX_TOKENS

```javascript
import { INDEX_TOKENS } from '@/constants/trading'

// In computed
const indexToken = computed(() => INDEX_TOKENS.value[underlying.value])
```

---

### INDEX_SYMBOLS

```javascript
import { INDEX_SYMBOLS } from '@/constants/trading'

// In computed
const indexSymbol = computed(() => INDEX_SYMBOLS.value[underlying.value])
```

---

## API Endpoint

### GET /api/constants/trading

Returns all trading constants as JSON.

**Response:**
```json
{
  "underlyings": ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"],
  "lot_sizes": {
    "NIFTY": 25,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "SENSEX": 10,
    "MIDCPNIFTY": 75
  },
  "strike_steps": {
    "NIFTY": 100,
    "BANKNIFTY": 100,
    "FINNIFTY": 100,
    "SENSEX": 100
  },
  "index_tokens": {
    "NIFTY": 256265,
    "BANKNIFTY": 260105,
    "FINNIFTY": 257801,
    "SENSEX": 265,
    "INDIAVIX": 264969
  },
  "index_exchanges": {
    "NIFTY": "NSE",
    "BANKNIFTY": "NSE",
    "FINNIFTY": "NSE",
    "SENSEX": "BSE",
    "INDIAVIX": "NSE"
  },
  "index_symbols": {
    "NIFTY": "NSE:NIFTY 50",
    "BANKNIFTY": "NSE:NIFTY BANK",
    "FINNIFTY": "NSE:NIFTY FIN SERVICE",
    "SENSEX": "BSE:SENSEX"
  }
}
```

**Frontend loads these on app initialization** via `loadTradingConstants()`.

---

## Examples

### Calculate Total Quantity

```python
# Backend
from app.constants.trading import get_lot_size

underlying = "NIFTY"
lots = 3
lot_size = get_lot_size(underlying)  # 25
total_qty = lots * lot_size  # 75
```

```javascript
// Frontend
import { getLotSize } from '@/constants/trading'

const underlying = 'NIFTY'
const lots = 3
const lotSize = getLotSize(underlying)  // 25
const totalQty = lots * lotSize  // 75
```

---

### Round to Nearest Strike

```python
# Backend
from app.constants.trading import get_strike_step

spot_price = 24567.8
underlying = "NIFTY"
strike_step = get_strike_step(underlying)  # 100
atm_strike = round(spot_price / strike_step) * strike_step  # 24600
```

```javascript
// Frontend
import { getStrikeStep } from '@/constants/trading'

const spotPrice = 24567.8
const underlying = 'NIFTY'
const strikeStep = getStrikeStep(underlying)  // 100
const atmStrike = Math.round(spotPrice / strikeStep) * strikeStep  // 24600
```

---

### Subscribe to WebSocket Ticks

```javascript
// Frontend
import { getIndexToken } from '@/constants/trading'

const niftyToken = getIndexToken('NIFTY')  // 256265
const bankniftyToken = getIndexToken('BANKNIFTY')  // 260105

ws.send(JSON.stringify({
  action: 'subscribe',
  tokens: [niftyToken, bankniftyToken],
  mode: 'quote'
}))
```

---

## Common Anti-Patterns

### ❌ Hardcoding Lot Sizes

```python
# WRONG
if underlying == "NIFTY":
    lot_size = 25
elif underlying == "BANKNIFTY":
    lot_size = 15

# RIGHT
lot_size = get_lot_size(underlying)
```

### ❌ Hardcoding Strike Steps

```javascript
// WRONG
const strikeStep = underlying === 'NIFTY' ? 50 : 100

// RIGHT
const strikeStep = getStrikeStep(underlying)
```

### ❌ Hardcoding Index Tokens

```python
# WRONG
tokens = [256265, 260105]  # Hardcoded!

# RIGHT
from app.constants.trading import get_index_token
tokens = [get_index_token("NIFTY"), get_index_token("BANKNIFTY")]
```
