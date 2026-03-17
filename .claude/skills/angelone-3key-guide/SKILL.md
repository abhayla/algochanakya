---
name: angelone-3key-guide
description: >
  Diagnose and fix AngelOne AG8001 "Invalid Token" errors caused by the 3-key JWT binding
  issue. Maps each API key to its purpose and shows the correct credential flow for live data,
  historical data, and order execution adapters. Use when encountering AG8001 errors.
type: workflow
allowed-tools: "Read Grep Glob"
argument-hint: "[--diagnose] [--verify-keys]"
version: "1.0.0"
synthesized: true
private: true
source_hash: "angelone-3key-v1"
---

# AngelOne 3-Key Troubleshooting Guide

Diagnose AG8001 "Invalid Token" errors caused by AngelOne's 3-key JWT binding system.

**Request:** $ARGUMENTS

---

## STEP 1: Understand the 3-Key Architecture

AngelOne (SmartAPI) uses 3 separate API keys. Each key generates a JWT that is **bound to that key** — using a JWT from Key A with Key B returns `AG8001 Invalid Token`.

| `.env` Key | Variable | Purpose | Used By |
|-----------|----------|---------|---------|
| `ANGEL_API_KEY` | Live market data | WebSocket ticks, REST quotes, option chain | `smartapi_adapter.py` |
| `ANGEL_HIST_API_KEY` | Historical candles | OHLCV candle data for backtesting and charts | `smartapi_adapter.py` (historical methods) |
| `ANGEL_TRADE_API_KEY` | Order execution | Place/modify/cancel orders, get positions | `angelone_adapter.py` |

Each key also has a corresponding secret:
- `ANGEL_API_SECRET` — paired with `ANGEL_API_KEY`
- `ANGEL_HIST_API_SECRET` — paired with `ANGEL_HIST_API_KEY`
- `ANGEL_TRADE_API_SECRET` — paired with `ANGEL_TRADE_API_KEY`

## STEP 2: Diagnose the AG8001 Error

When you see `AG8001 Invalid Token`, determine which adapter threw the error:

```bash
# Search for the AG8001 error in recent logs
grep -r "AG8001\|Invalid Token" backend/logs/ --include="*.log" | tail -10
```

| Error Location | Likely Cause | Fix |
|---------------|-------------|-----|
| `smartapi_adapter.py` (live data) | JWT was generated with wrong key | Verify `ANGEL_API_KEY` in `.env` matches the key used for login |
| `smartapi_adapter.py` (historical) | Historical JWT used live key's JWT | Ensure `hist_api_key != api_key` triggers fresh login (see Step 3) |
| `angelone_adapter.py` (orders) | Trade JWT used live key's JWT | Ensure `ANGEL_TRADE_API_KEY` is set and different from `ANGEL_API_KEY` |

## STEP 3: Verify the JWT Binding Logic

Read the critical JWT handling code:

### Live → Historical handoff (smartapi_adapter.py)

```bash
grep -n "hist_api_key\|hist_jwt\|ANGEL_HIST" backend/app/services/brokers/market_data/smartapi_adapter.py
```

The correct pattern (around lines 77-87):
```python
hist_api_key = getattr(settings, 'ANGEL_HIST_API_KEY', None) or api_key
# CRITICAL: If keys differ, do NOT pass the live JWT — it's bound to the live key
hist_jwt = credentials.jwt_token if hist_api_key == api_key else None
```

When `hist_jwt=None`, the historical adapter performs its own fresh login with `ANGEL_HIST_API_KEY`, generating a JWT bound to that key.

### Live → Trade handoff (angelone_adapter.py)

```bash
grep -n "ANGEL_TRADE_API_KEY\|trade.*api_key\|fallback" backend/app/services/brokers/angelone_adapter.py
```

The correct pattern (around lines 135-138):
```python
api_key = self.api_key or (
    getattr(settings, "ANGEL_TRADE_API_KEY", "")
    or getattr(settings, "ANGEL_API_KEY", "")  # Fallback if trade key not set
)
```

## STEP 4: Verify .env Configuration

```bash
# Check all 3 keys are set (mask actual values)
grep "ANGEL_API_KEY\|ANGEL_HIST_API_KEY\|ANGEL_TRADE_API_KEY" backend/.env | sed 's/=.*/=****/'
```

Expected output:
```
ANGEL_API_KEY=****
ANGEL_API_SECRET=****
ANGEL_HIST_API_KEY=****
ANGEL_HIST_API_SECRET=****
ANGEL_TRADE_API_KEY=****
ANGEL_TRADE_API_SECRET=****
```

| Check | Expected | If Wrong |
|-------|----------|----------|
| All 6 values present | Yes | Add missing keys from AngelOne SmartAPI dashboard |
| `ANGEL_API_KEY` != `ANGEL_HIST_API_KEY` | Different keys | If same, historical queries reuse live JWT (works but defeats key isolation) |
| `ANGEL_API_KEY` != `ANGEL_TRADE_API_KEY` | Different keys | If same, orders reuse live JWT (works but defeats key isolation) |
| No empty values | All have content | Empty key causes fallback chain, which may use wrong key |

## STEP 5: Test Each Key Independently

If you have access to the Python REPL, verify each key works independently:

1. **Live data key:** Check if a REST quote endpoint returns data without AG8001
2. **Historical key:** Check if a candle data endpoint returns data without AG8001
3. **Trade key:** Check if the order book endpoint returns data without AG8001

```bash
# Run the broker connection test (if available)
cd backend && pytest tests/backend/brokers/test_angelone*.py -v -k "test_connection" -m live
```

## STEP 6: Common Fix Patterns

| Scenario | Root Cause | Fix |
|----------|-----------|-----|
| AG8001 on historical queries only | `hist_api_key == api_key` but keys are actually different | Verify `ANGEL_HIST_API_KEY` is loaded correctly in `config.py` |
| AG8001 on order placement only | Trade adapter using live JWT | Set `ANGEL_TRADE_API_KEY` explicitly in `.env` |
| AG8001 on everything after restart | TOTP token expired | Re-authenticate — SmartAPI TOTP tokens expire after market close |
| AG8001 intermittently | JWT expiry mid-session | Check token refresh logic in the adapter's `_ensure_session()` method |
| AG8001 after key rotation | Old JWT cached | Clear any cached JWTs and restart the backend |

---

## CRITICAL RULES

- NEVER share JWT tokens between adapters that use different API keys — this is the root cause of AG8001
- NEVER hardcode API keys in source code — always read from `.env` via `config.py` settings
- ALWAYS pass `jwt_token=None` when the target adapter uses a different API key than the one that generated the JWT
- ALWAYS verify all 6 env vars are set (3 keys + 3 secrets) before debugging token issues
- NEVER log actual API key values — use masked output (`****`) for diagnostics
- ALWAYS check TOTP expiry first — the simplest explanation for AG8001 is an expired session, not a key mismatch
