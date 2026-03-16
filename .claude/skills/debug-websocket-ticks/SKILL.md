---
name: debug-websocket-ticks
description: >
  Debug when WebSocket ticks are not flowing or option chain shows LTP=0.
  Traces the 5-component ticker architecture to find the failure point.
type: workflow
allowed-tools: "Bash Read Grep Glob"
argument-hint: "[--ltp-zero | --no-ticks]"
version: "1.0.0"
synthesized: true
private: false
---

# Debug WebSocket Ticks

## STEP 1: Check Startup Logs

Look for these critical startup messages in server output:

- `[SUCCESS] SmartAPI token mappings: N rows` -- MUST be > 0. If 0, all option chain LTPs will be 0.
- `[SUCCESS] SmartAPI instruments cached: N` -- Should be ~185k
- `[SUCCESS] Ticker system initialized` -- Confirms Pool + Router + Health started
- `[WARNING] SmartAPI token mappings: 0 rows` -- THIS IS THE PROBLEM if LTPs are 0

## STEP 2: Verify Environment

Check `backend/.env` for: ANGEL_API_KEY (live market data), ANGEL_HIST_API_KEY (historical), ANGEL_TRADE_API_KEY (orders). Using the wrong AngelOne key returns AG8001 Invalid Token.

## STEP 3: Check Database Tables

Query `broker_instrument_tokens` for smartapi broker -- should have thousands of rows. If 0, `populate_broker_token_mappings()` failed at startup. Also check `instruments` table has NFO exchange records.

## STEP 4: Test WebSocket Directly

Browser console test (dev port 8001):
```
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=JWT')
ws.onmessage = e => console.log(JSON.parse(e.data))
ws.onopen = () => ws.send(JSON.stringify({action:'subscribe',tokens:[256265],mode:'quote'}))
```
Index tokens have hardcoded fallback: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265.

## STEP 5: Trace Token Map Loading

In `websocket.py`, `_ensure_broker_credentials()` loads canonical-to-broker token mapping from `broker_instrument_tokens` table into `credentials["token_map"]`. Without this, SmartAPITickerAdapter subscribes to nothing (no ticks flow).

## STEP 6: Check Failover

If ticks were flowing but stopped: HealthMonitor scores adapters on 5-second heartbeat. FailoverController triggers make-before-break failover. Check if secondary broker has valid credentials.

## CRITICAL RULES

- Token mapping = 0 is the #1 cause of LTP=0 in option chain
- ANGEL_API_KEY must be the live market data key (not the historical or trade key)
- Index tokens always work (hardcoded fallback) even without DB mappings
- Never restart production to debug -- observe read-only first
