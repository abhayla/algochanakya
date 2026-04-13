---
name: run-live-broker-tests
description: >
  Run live integration tests against real broker APIs. Manages credentials,
  markers, and graceful skip when credentials are missing.
type: workflow
allowed-tools: "Bash Read Grep Glob"
argument-hint: "[broker-name] [--slow]"
version: "1.0.0"
synthesized: true
private: false
---

# Run Live Broker Tests

## STEP 1: Verify Credentials

Check `backend/.env` has real broker credentials set. Live tests auto-skip cleanly when credentials are missing -- no failures.

## STEP 2: Run All Live Tests

```bash
cd backend
pytest tests/live/ -m live -v
```

## STEP 3: Run Specific Broker Tests

```bash
pytest tests/live/test_live_authentication.py -v       # Auth flow
pytest tests/live/test_live_instrument_search.py -v    # Instrument lookup
pytest tests/live/test_live_market_data.py -v          # Quotes and historical
pytest tests/live/test_live_option_chain.py -v         # Option chain data
pytest tests/live/test_live_order_execution.py -v      # Order placement (CAREFUL)
pytest tests/live/test_live_websocket_ticker.py -v     # WebSocket ticks
pytest tests/live/test_live_screens_api.py -v          # Screen API integration
```

## STEP 4: Skip Slow Tests

```bash
pytest tests/live/ -m "live and not slow" -v
```

Slow tests include historical data fetches that download large datasets.

## STEP 5: Interpret Results

- `SKIPPED` with "credentials not configured" -- normal, credential not in .env
- `FAILED` with "AG8001 Invalid Token" -- wrong AngelOne API key (3 different keys exist)
- `FAILED` with timeout -- broker API may be down or rate limited

## STEP 6: Test Constants

Live test constants are in `backend/tests/live/constants.py` -- known instrument tokens, test symbols, etc.

## STEP 7: Token Refresh & Health Pipeline Tests

These tests use mocks and don't require live broker credentials:

1. **Token policy tests**:
   ```bash
   cd backend && PYTHONPATH=. pytest tests/backend/brokers/test_token_policy.py -v
   ```

2. **Health pipeline tests**:
   ```bash
   PYTHONPATH=. pytest tests/backend/brokers/test_pool_health_wiring.py tests/backend/brokers/test_health_auth_aware.py -v
   ```

3. **Credential refresh tests**:
   ```bash
   PYTHONPATH=. pytest tests/backend/brokers/test_pool_credential_refresh.py tests/backend/brokers/test_failover_credential_check.py -v
   ```

## CRITICAL RULES

- Live tests hit REAL broker APIs -- they cost API quota
- Order execution tests may place REAL orders -- only run with paper/test accounts
- Tests auto-skip when credentials missing -- never mock in live tests
- Do not run live tests in CI -- they require real credentials and market hours
- AngelOne has 3 API keys (market data, historical, trade) -- use the right one
