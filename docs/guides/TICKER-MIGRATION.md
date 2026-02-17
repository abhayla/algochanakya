# Migrating from Legacy Tickers to New Architecture

**Date:** 2026-02-17
**Status:** Migration complete (Phase T5)

## What Changed

### Before (Legacy)
- **2 hardcoded singletons:** `SmartAPITickerService` and `KiteTickerService`
- **~500-line websocket.py** with broker-specific logic inline
- **No failover** — if SmartAPI died, manual switch to Kite required
- **No health monitoring** — connection drops went undetected until ticks stopped
- **No adapter pattern** — adding a new broker meant rewriting websocket.py

### After (New — Phase T4)
- **5-component architecture:**
  - `TickerAdapter` — per-broker WebSocket interface (ABC)
  - `TickerPool` — adapter lifecycle management, ref-counted subscriptions, integrated credentials
  - `TickerRouter` — user fan-out, maps subscriptions to correct broker adapter
  - `HealthMonitor` — 5-second heartbeat, per-adapter health scoring
  - `FailoverController` — automatic make-before-break failover
- **~90-line websocket.py** — fully broker-agnostic
- **Automatic failover** with configurable priority chain
- **Active health monitoring** with degradation detection
- **6 broker adapters** — SmartAPI, Kite (implemented), Dhan, Fyers, Upstox, Paytm (stubs)

## File Locations

### New Architecture (use these)

| Component | Path |
|-----------|------|
| Adapter ABC | `backend/app/services/brokers/market_data/ticker/adapter_base.py` |
| TickerPool | `backend/app/services/brokers/market_data/ticker/pool.py` |
| TickerRouter | `backend/app/services/brokers/market_data/ticker/router.py` |
| HealthMonitor | `backend/app/services/brokers/market_data/ticker/health.py` |
| FailoverController | `backend/app/services/brokers/market_data/ticker/failover.py` |
| Models (NormalizedTick) | `backend/app/services/brokers/market_data/ticker/models.py` |
| SmartAPI Adapter | `backend/app/services/brokers/market_data/ticker/adapters/smartapi.py` |
| Kite Adapter | `backend/app/services/brokers/market_data/ticker/adapters/kite.py` |
| Broker Stubs | `backend/app/services/brokers/market_data/ticker/adapters/{dhan,fyers,upstox,paytm}.py` |

### Deprecated (reference only)

| File | Replaced By |
|------|-------------|
| `backend/app/services/deprecated/smartapi_ticker.py` | `ticker/adapters/smartapi.py` |
| `backend/app/services/deprecated/kite_ticker.py` | `ticker/adapters/kite.py` |

## Migration Checklist

1. **Backend: New ticker system wired in main.py startup** — TickerPool, TickerRouter, HealthMonitor, FailoverController initialized during app lifespan
2. **Backend: WebSocket route refactored** — `websocket.py` uses TickerRouter (broker-agnostic)
3. **Backend: Ticker API routes added** — `/api/ticker/health`, `/api/ticker/failover/status`
4. **Backend: All 6 broker adapters registered** — SmartAPI + Kite (full), Dhan/Fyers/Upstox/Paytm (stubs)
5. **Backend: Legacy services moved to `deprecated/`** — Import paths updated
6. **Frontend: WebSocket message format** — Already uses NormalizedTick format

## How to Use the New System

### Subscribing to ticks (backend internal)

```python
from app.services.brokers.market_data.ticker import TickerPool, TickerRouter

# TickerPool manages adapter lifecycle
pool = app.state.ticker_pool

# TickerRouter handles user fan-out
router = app.state.ticker_router

# Subscribe tokens for a user's WebSocket connection
await router.subscribe(user_id="user123", tokens=[256265, 260105], mode="quote")
```

### Health monitoring

```bash
# Check adapter health
curl http://localhost:8001/api/ticker/health

# Check failover status
curl http://localhost:8001/api/ticker/failover/status
```

### Adding a new broker adapter

1. Implement `TickerAdapter` ABC in `ticker/adapters/{broker}.py`
2. Register in `TickerPool` via `pool.register_adapter()`
3. Add to failover priority chain in `FailoverController`
4. No changes needed to websocket.py, router, or any other component

## Rollback

If issues arise with the new system, the legacy services are preserved in `backend/app/services/deprecated/`. The legacy `get_ticker_service()` factory in `ticker_base.py` still works (with deprecation warning).

## Related Documentation

- [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) — Architecture design
- [TICKER-IMPLEMENTATION-GUIDE.md](TICKER-IMPLEMENTATION-GUIDE.md) — Phase-by-phase implementation
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Endpoint docs
- [Ticker Documentation Index](../decisions/ticker-documentation-index.md) — All ticker docs
