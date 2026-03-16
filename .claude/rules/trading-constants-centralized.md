---
description: >
  Lot sizes, strike steps, index tokens MUST come from app.constants.trading, never hardcoded.
  Frontend uses centralized getLotSize() from constants/trading.js.
globs: ["backend/**/*.py", "frontend/**/*.{js,vue}"]
synthesized: true
private: false
---

# Centralized Trading Constants

## Single Source of Truth

`backend/app/constants/trading.py` is the single source of truth for:
- `LOT_SIZES` — lot size per underlying (NIFTY=75, BANKNIFTY=35, etc.)
- `STRIKE_STEPS` — strike interval per underlying (all 100 per user requirement)
- `INDEX_TOKENS` — NSE instrument tokens for WebSocket (NIFTY=256265, BANKNIFTY=260105)
- `INDEX_SYMBOLS` — Kite trading symbols for LTP API
- `INDEX_EXCHANGES` — exchange mappings

## Backend Usage

```python
from app.constants.trading import get_lot_size, get_strike_step, INDEX_TOKENS

lot_size = get_lot_size("NIFTY")       # 75
step = get_strike_step("BANKNIFTY")    # 100
token = INDEX_TOKENS["NIFTY"]          # 256265
```

## Frontend Usage

Frontend constants are loaded from `/api/constants/trading` on app init, with fallbacks:

```javascript
import { getLotSize, getStrikeStep } from "@/constants/trading"
const lotSize = getLotSize("NIFTY")  // 75
```

## MUST NOT Hardcode

```python
# NEVER do this:
lot_size = 75
strike_step = 50
nifty_token = 256265

# ALWAYS do this:
from app.constants.trading import get_lot_size, get_strike_step, INDEX_TOKENS
```

These values change with NSE circulars (e.g., NIFTY lot size changed from 50 to 75 in Nov 2024).
Hardcoding causes silent calculation errors across the entire system.

