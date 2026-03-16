---
name: investigate-option-chain-ltp-zero
description: >
  Investigate when option chain shows all LTPs as 0. Root cause is almost always
  the SmartAPI token mapping population at startup.
type: workflow
allowed-tools: "Bash Read Grep Glob"
argument-hint: ""
version: "1.0.0"
synthesized: true
private: false
---

# Investigate Option Chain LTP = 0

## STEP 1: Check the Startup Warning

The most likely cause is this startup log message:

```
[WARNING] SmartAPI token mappings: 0 rows stored -- option chain LTPs will be 0!
[WARNING] Fix: ensure NFO instruments are in DB and ANGEL_API_KEY is set.
```

This means `InstrumentMasterService.populate_broker_token_mappings()` returned 0 rows.

## STEP 2: Verify ANGEL_API_KEY

Check `backend/.env` has `ANGEL_API_KEY` set to a valid SmartAPI key (the live market data key, not the historical or trade key). AngelOne uses 3 separate API keys.

## STEP 3: Check Instruments Table

The token mapping requires NFO instruments in the database:

```sql
SELECT COUNT(*) FROM instruments WHERE exchange = 'NFO';
```

If 0: instrument refresh failed. Check if Kite CSV fallback also failed (network issue or missing Kite credentials).

## STEP 4: Check broker_instrument_tokens Table

```sql
SELECT COUNT(*) FROM broker_instrument_tokens WHERE broker = 'smartapi';
```

If 0: the mapping population failed. If > 0 but LTPs still 0: the issue is downstream (WebSocket subscription).

## STEP 5: Verify WebSocket Token Map Loading

In `backend/app/api/routes/websocket.py`, `_ensure_broker_credentials()` loads the canonical-to-broker token mapping from the `broker_instrument_tokens` table and passes it via `credentials["token_map"]`.

Without this token map, `SmartAPITickerAdapter` cannot translate canonical Kite tokens to SmartAPI tokens and subscribes to nothing -- resulting in zero ticks.

## STEP 6: Test with Index Tokens

Index tokens (NIFTY=256265, BANKNIFTY=260105) have a hardcoded fallback and should ALWAYS show prices even when the DB mapping is empty. If even index prices are 0, the issue is deeper (SmartAPI credentials invalid or WebSocket not connecting).

## STEP 7: Manual Re-population

If the startup population failed but the server is running:

```python
# In a Python shell with app context
from app.services.instrument_master import InstrumentMasterService
async with AsyncSessionLocal() as db:
    count = await InstrumentMasterService.populate_broker_token_mappings(db)
    print(f"Populated {count} token mappings")
```

## CRITICAL RULES

- Token mapping = 0 is the #1 cause of LTP=0
- Index tokens always work (hardcoded fallback)
- ANGEL_API_KEY must be the live market data key specifically
- Check startup logs FIRST -- the warning is explicit
- Do not restart production -- diagnose first
