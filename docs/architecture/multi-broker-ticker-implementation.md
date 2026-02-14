# Multi-Broker Ticker Implementation Guide

**Status**: ⚠️ **REDESIGN PROPOSED** - See [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md)

**Related**: [ADR-003 v2](../decisions/003-multi-broker-ticker-architecture.md) | [TICKER-DESIGN-SPEC.md](../decisions/TICKER-DESIGN-SPEC.md) | [API Reference](../api/multi-broker-ticker-api.md) | [WebSocket Architecture](./websocket.md)

**Goal**: Replace hardcoded ticker singletons with a 5-component broker-agnostic architecture: TickerAdapter + TickerPool + TickerRouter + HealthMonitor + FailoverController

**Note:** This guide describes the original ADR-003 v2 implementation approach. A refined design with improved credential management and component consolidation is documented in TICKER-DESIGN-SPEC.md.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
4. [Phase 2: SmartAPI + Kite Adapters + Route Refactor](#phase-2-smartapi--kite-adapters--route-refactor)
5. [Phase 3: Failover + Production Hardening](#phase-3-failover--production-hardening)
6. [Phase 4: Additional Broker Adapters](#phase-4-additional-broker-adapters)
7. [Phase 5: Order Execution Expansion](#phase-5-order-execution-expansion)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

---

## Overview

### Current State → Target State

```
BEFORE (495 lines, 2 singletons):              AFTER (~90 lines, 5 components):
┌─────────────────────────────┐                ┌──────────────────────────────────┐
│   websocket.py (495 lines)  │                │  websocket.py (~90 lines)        │
│  ┌─────────────────────┐    │                │      │                           │
│  │ KITE_TO_SMARTAPI dict│    │                │  TickerRouter (user fan-out)     │
│  │ if/else broker logic │    │                │      │                           │
│  │ credential fetching  │    │                │  TickerPool (lifecycle/ref-count)│
│  │ token translation    │    │                │      │                           │
│  └─────────────────────┘    │                │  ┌────┼────┬────────┐            │
│       │           │          │                │  │    │    │        │ ...        │
│  SmartAPI WS  Kite WS       │                │  SMA  Kite Upstox  Dhan         │
│  (singleton)  (singleton)   │                │  HealthMonitor + FailoverCtrl    │
└─────────────────────────────┘                └──────────────────────────────────┘
```

**Key improvements**: 82% route reduction, ref-counted subscriptions, automatic failover, health scoring, system credentials, zero broker-specific code in routes.

---

## Prerequisites

### Before Starting

1. **Read these documents first:**
   - [ADR-003 v2](../decisions/003-multi-broker-ticker-architecture.md) — Architecture and component design
   - [API Reference](../api/multi-broker-ticker-api.md) — Full interface specifications and code
   - [broker-abstraction.md](./broker-abstraction.md) — Broker comparison matrix

2. **Critical code to preserve:**
   - SmartAPI threading pattern: `backend/app/services/legacy/smartapi_ticker.py` lines 117-124 and 208-211
   - Index token mapping: `backend/app/api/routes/websocket.py` lines 32-37
   - TokenManager: `backend/app/services/brokers/market_data/token_manager.py`
   - Rate limiter: `backend/app/services/brokers/market_data/rate_limiter.py`

3. **Verify clean state:**
   ```bash
   git status && git log --oneline -5
   git tag pre-ticker-refactor    # Safety tag
   ```

---

## Phase 1: Core Infrastructure

**Timeline**: ~3 days | **Milestone**: App boots with new components. Legacy tickers still work. Zero user-facing changes.

### Step 1: Create Directory Structure

```bash
mkdir -p backend/app/services/brokers/market_data/ticker/adapters
```

Create `__init__.py` files:
- `backend/app/services/brokers/market_data/ticker/__init__.py`
- `backend/app/services/brokers/market_data/ticker/adapters/__init__.py`

### Step 2: Implement NormalizedTick

**File**: `backend/app/services/brokers/market_data/ticker/models.py`

Create the `NormalizedTick` dataclass with `__slots__` and `to_dict()` method. See [API Reference Section 1](../api/multi-broker-ticker-api.md#1-normalizedtick) for complete code.

**Verify**: `python -c "from app.services.brokers.market_data.ticker.models import NormalizedTick; print('OK')"`

### Step 3: Implement TickerAdapter ABC

**File**: `backend/app/services/brokers/market_data/ticker/adapter_base.py`

Create the abstract base class with lifecycle methods, subscription methods, dispatch helpers, and abstract methods. See [API Reference Section 2](../api/multi-broker-ticker-api.md#2-tickeradapter-abstract-base) for complete code.

Key methods:
- `connect()`, `disconnect()`, `reconnect()`, `update_credentials()`
- `subscribe()`, `unsubscribe()`
- `_dispatch_from_thread()`, `_dispatch_async()`
- 7 abstract methods for broker-specific implementation

**Verify**: `python -c "from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter; print('OK')"`

### Step 4: Implement TickerPool

**File**: `backend/app/services/brokers/market_data/ticker/pool.py`

Singleton with adapter creation, ref-counted subscriptions, idle timers, and callback wiring. See [API Reference Section 6](../api/multi-broker-ticker-api.md#6-tickerpool) for complete code.

Key behaviors:
- `get_adapter()`: Lazy creation + system credential connection
- `add_subscriptions()`: Ref count 0→1 triggers broker subscribe
- `remove_subscriptions()`: Ref count 1→0 triggers broker unsubscribe + idle timer

**Verify**: `python -c "from app.services.brokers.market_data.ticker.pool import TickerPool; print('OK')"`

### Step 5: Implement TickerRouter

**File**: `backend/app/services/brokers/market_data/ticker/router.py`

Singleton with user registration, token→user mapping, tick fan-out, cached tick delivery, failover support. See [API Reference Section 7](../api/multi-broker-ticker-api.md#7-tickerrouter) for complete code.

Key behaviors:
- `dispatch()`: HOT PATH — no locks, O(users per token) per tick
- `subscribe()`: Delivers cached ticks immediately for instant UI update
- `switch_users_broker()`: Atomic user routing change for failover

**Verify**: `python -c "from app.services.brokers.market_data.ticker.router import TickerRouter; print('OK')"`

### Step 6: Implement HealthMonitor

**File**: `backend/app/services/brokers/market_data/ticker/health.py`

`AdapterHealth` dataclass + `HealthMonitor` with 5s heartbeat loop and weighted health scoring. See [API Reference Section 8](../api/multi-broker-ticker-api.md#8-healthmonitor) for complete code.

Health score: `Connection(30%) + Latency(20%) + Errors(20%) + Freshness(30%)`

**Verify**: `python -c "from app.services.brokers.market_data.ticker.health import HealthMonitor, AdapterHealth; print('OK')"`

### Step 7: Create SystemBrokerCredential Model

**File**: `backend/app/models/system_broker_credentials.py`

SQLAlchemy model with encrypted columns for JWT, access_token, refresh_token, feed_token, api_key, api_secret. See [API Reference Section 10](../api/multi-broker-ticker-api.md#10-systemcredentialmanager) for complete schema.

### Step 8: Register Model for Alembic

**File**: `backend/app/models/__init__.py` — Add import:
```python
from app.models.system_broker_credentials import SystemBrokerCredential
```

**File**: `backend/alembic/env.py` — Add import:
```python
from app.models.system_broker_credentials import SystemBrokerCredential
```

**Run migration**:
```bash
cd backend
alembic revision --autogenerate -m "add system_broker_credentials table"
alembic upgrade head
```

### Step 9: Implement SystemCredentialManager

**File**: `backend/app/services/brokers/market_data/ticker/credential_manager.py`

Singleton that loads credentials from DB, authenticates per broker, and starts refresh loops. See [API Reference Section 10](../api/multi-broker-ticker-api.md#10-systemcredentialmanager) for interface.

Key behaviors:
- SmartAPI: Reuse auto-TOTP from `smartapi_auth.py`
- Dhan: Validate static token (never expires)
- Kite: Log limitation (user OAuth only)

### Step 10: Add Configuration

**File**: `backend/app/config.py` — Add to `Settings` class:

```python
# Ticker system configuration
DEFAULT_MARKET_DATA_BROKER: str = "smartapi"
TICKER_PRIMARY_BROKER: str = "smartapi"
TICKER_SECONDARY_BROKER: str = "kite"
TICKER_IDLE_TIMEOUT_S: int = 300
TICKER_HEALTH_INTERVAL_S: int = 5
TICKER_FAILOVER_THRESHOLD: float = 30.0
TICKER_FAILOVER_CHECKS: int = 3
TICKER_FAILBACK_THRESHOLD: float = 70.0
TICKER_FAILBACK_SUSTAINED_S: int = 60
TICKER_FLAP_PREVENTION_S: int = 120

# System broker credentials
SYSTEM_SMARTAPI_CLIENT_ID: str = ""
SYSTEM_SMARTAPI_PIN: str = ""
SYSTEM_SMARTAPI_TOTP_SECRET: str = ""
SYSTEM_DHAN_ACCESS_TOKEN: str = ""
SYSTEM_DHAN_CLIENT_ID: str = ""
```

See [API Reference Section 13](../api/multi-broker-ticker-api.md#13-configuration-reference) for full list.

### Step 11: Wire into main.py Lifespan

**File**: `backend/app/main.py` — In the lifespan function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...

    # NEW: Initialize ticker system
    from app.services.brokers.market_data.ticker.pool import TickerPool
    from app.services.brokers.market_data.ticker.router import TickerRouter
    from app.services.brokers.market_data.ticker.health import HealthMonitor
    from app.services.brokers.market_data.ticker.failover import FailoverController
    from app.services.brokers.market_data.ticker.credential_manager import SystemCredentialManager

    pool = TickerPool.get_instance()
    router = TickerRouter.get_instance()
    health_monitor = HealthMonitor()
    failover = FailoverController()
    cred_manager = SystemCredentialManager.get_instance()

    # Wire dependencies
    pool.set_dependencies(cred_manager, health_monitor, router)
    router.set_pool(pool)
    failover.set_dependencies(pool, router, health_monitor)
    health_monitor.set_on_health_change(failover.on_health_change)

    # Initialize credentials and start monitoring
    try:
        await cred_manager.initialize()
        await health_monitor.start()
        logger.info("Ticker system initialized")
    except Exception as e:
        logger.error(f"Ticker system init error (non-fatal): {e}")

    yield

    # Shutdown (reverse order)
    await health_monitor.stop()
    await pool.shutdown()
    await cred_manager.shutdown()
    logger.info("Ticker system shut down")
```

### Phase 1 Verification

```bash
# All imports work
python -c "
from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.pool import TickerPool
from app.services.brokers.market_data.ticker.router import TickerRouter
from app.services.brokers.market_data.ticker.health import HealthMonitor
from app.services.brokers.market_data.ticker.failover import FailoverController
from app.models.system_broker_credentials import SystemBrokerCredential
print('All Phase 1 imports OK')
"

# Backend starts without errors
python run.py
# Check: "Ticker system initialized" in logs
# Legacy tickers still work unchanged

# Existing tests pass
pytest tests/ -v -m "not slow"
```

---

## Phase 2: SmartAPI + Kite Adapters + Route Refactor

**Timeline**: ~4 days | **Milestone**: Full tick pipeline through new architecture. Route reduced from 495 → ~90 lines.

### Step 1: Implement SmartAPITickerAdapter

**File**: `backend/app/services/brokers/market_data/ticker/adapters/smartapi.py`

Port from `legacy/smartapi_ticker.py`. See [API Reference Section 3](../api/multi-broker-ticker-api.md#3-smartapiticker-adapter) for complete code.

**CRITICAL**: Preserve exact threading pattern:
```python
# From smartapi_ticker.py:117-124
def run_websocket():
    try:
        self._ws.connect()
    except Exception as e:
        logger.error(f"[SmartAPI] WebSocket thread error: {e}")

self._thread = threading.Thread(target=run_websocket, daemon=True)
self._thread.start()
```

Key responsibilities:
- Token translation: 256265 → "99926000" via `_INDEX_MAP` + `TokenManager`
- Price normalization: paise ÷ 100 → rupees
- Exchange type codes: NSE=1, NFO=2, BSE=3, BFO=4, MCX=5
- Thread→asyncio bridge: `asyncio.run_coroutine_threadsafe`

### Step 2: Implement KiteTickerAdapter

**File**: `backend/app/services/brokers/market_data/ticker/adapters/kite.py`

Port from `legacy/kite_ticker.py`. See [API Reference Section 4](../api/multi-broker-ticker-api.md#4-kiteticker-adapter) for complete code.

Simpler than SmartAPI:
- No token translation (Kite format IS canonical)
- KiteTicker library manages threading (`connect(threaded=True)`)
- WS prices in paise ÷ 100 → rupees

### Step 3: Create 4 Stub Adapters

**Files**: `ticker/adapters/upstox.py`, `dhan.py`, `fyers.py`, `paytm.py`

Each raises `NotImplementedError` on `_connect_impl()`. Include broker-specific notes in docstrings. See [API Reference Section 5](../api/multi-broker-ticker-api.md#5-stub-adapter-templates).

### Step 4: Register Adapters in TickerPool

Update `ADAPTER_MAP` in `ticker/pool.py`:

```python
ADAPTER_MAP = {
    "smartapi": "app.services.brokers.market_data.ticker.adapters.smartapi.SmartAPITickerAdapter",
    "kite":     "app.services.brokers.market_data.ticker.adapters.kite.KiteTickerAdapter",
    "upstox":   "app.services.brokers.market_data.ticker.adapters.upstox.UpstoxTickerAdapter",
    "dhan":     "app.services.brokers.market_data.ticker.adapters.dhan.DhanTickerAdapter",
    "fyers":    "app.services.brokers.market_data.ticker.adapters.fyers.FyersTickerAdapter",
    "paytm":    "app.services.brokers.market_data.ticker.adapters.paytm.PaytmTickerAdapter",
}
```

### Step 5: Refactor websocket.py

**File**: `backend/app/api/routes/websocket.py`

Replace the entire 495-line file with the ~90-line version from [API Reference Section 11](../api/multi-broker-ticker-api.md#11-refactored-websocketpy).

**Removed:**
- All broker-specific imports
- `KITE_TO_SMARTAPI_INDEX` / `SMARTAPI_TO_KITE_INDEX` dicts
- `get_user_broker_connection()` helper
- `get_smartapi_credentials()` helper
- `fetch_initial_index_quotes()` helper
- Broker selection if/else branches
- Token translation in subscribe handler

**Added:**
- Import `TickerRouter`
- Register user → subscribe/unsubscribe via router → cleanup

### Step 6: Handle Failover Message in Frontend

**File**: `frontend/src/constants/websocket.js` — Add failover message type:

```javascript
export const WS_MESSAGE_TYPE = {
  CONNECTED: 'connected',
  SUBSCRIBED: 'subscribed',
  UNSUBSCRIBED: 'unsubscribed',
  TICKS: 'ticks',
  FAILOVER: 'failover',  // ← ADD THIS
  PONG: 'pong',
  ERROR: 'error'
}
```

**File**: `frontend/src/stores/watchlist.js` (or WebSocket composable) — Add failover handler:

The backend sends a failover notification to all connected users when the data source switches:

```json
{
  "type": "failover",
  "from": "smartapi",
  "to": "kite",
  "message": "Data source switched due to SmartAPI connectivity issues",
  "timestamp": 1706000000
}
```

**Frontend should:**

1. **Handle failover message type** in the WebSocket message handler:

```javascript
case WS_MESSAGE_TYPE.FAILOVER:
  console.log(`[WS] Failover: ${data.from} → ${data.to}`, data.message)

  // Update broker status indicator
  this.activeBroker = data.to

  // Show non-blocking notification to user
  showToast({
    type: 'warning',
    message: `Data source switched to ${data.to}`,
    duration: 5000
  })

  break
```

2. **Update broker status UI** — Show "Data: Kite" instead of "Data: SmartAPI" in the status bar

3. **Handle subsequent subscriptions** — After failover, subsequent `subscribed` confirmations will include `source: "{new_broker}"`:

```json
{
  "type": "subscribed",
  "tokens": [256265],
  "mode": "quote",
  "source": "kite"  // ← Changed after failover
}
```

4. **No reconnection needed** — The WebSocket connection stays open. Data continues to flow seamlessly from the new broker.

### Step 7: Deprecate Legacy Tickers

Add deprecation warnings to:
- `backend/app/services/legacy/smartapi_ticker.py`
- `backend/app/services/legacy/kite_ticker.py`

```python
import warnings
warnings.warn(
    "This module is deprecated. Use ticker/adapters/smartapi.py instead.",
    DeprecationWarning, stacklevel=2
)
```

### Step 8: Integration Test

```bash
# Start backend
python run.py

# Browser console test:
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))

# Expected:
# {"type": "connected", "source": "smartapi"}
# {"type": "subscribed", "tokens": [256265], "mode": "quote", "source": "smartapi"}
# {"type": "ticks", "data": [{...normalized tick...}]}
```

### Phase 2 Verification

```bash
# Route line count
wc -l backend/app/api/routes/websocket.py
# Should be ~90-100 lines

# No broker-specific code in route
grep -c "KITE_TO_SMARTAPI\|get_smartapi_credentials\|fetch_initial_index" backend/app/api/routes/websocket.py
# Should be 0

# All adapter imports work
python -c "
from app.services.brokers.market_data.ticker.adapters.smartapi import SmartAPITickerAdapter
from app.services.brokers.market_data.ticker.adapters.kite import KiteTickerAdapter
print('Adapters OK')
"

# E2E tests pass
npm run test:specs:watchlist
npm run test:specs:optionchain
npm run test:specs:dashboard
```

---

## Phase 3: Failover + Production Hardening

**Timeline**: ~3 days | **Milestone**: Automatic failover works. Health endpoint returns scores. Frontend shows broker status.

### Step 1: Implement FailoverController

**File**: `backend/app/services/brokers/market_data/ticker/failover.py`

`FailoverConfig` dataclass + `FailoverController` with make-before-break sequence. See [API Reference Section 9](../api/multi-broker-ticker-api.md#9-failovercontroller) for complete code.

### Step 2: Wire HealthMonitor → FailoverController

Already done in Phase 1 Step 11 (main.py lifespan). Verify the callback is set:

```python
health_monitor.set_on_health_change(failover.on_health_change)
```

### Step 3: Test Failover

Manual test:
1. Start app with SmartAPI as primary
2. Verify ticks flowing
3. Disconnect SmartAPI adapter manually: `await pool._adapters["smartapi"].disconnect()`
4. Wait 15 seconds (3 × 5s health checks)
5. Verify: HealthMonitor triggers FailoverController
6. Verify: Kite adapter connects and receives ticks
7. Verify: Frontend receives `{"type": "failover"}` message
8. Reconnect SmartAPI, wait 60s, verify failback

### Step 4: Add Health API Endpoint

**File**: Create `backend/app/api/routes/ticker_health.py` or add to existing health route:

```python
@router.get("/api/ticker/health")
async def ticker_health():
    pool = TickerPool.get_instance()
    router = TickerRouter.get_instance()
    failover = FailoverController.get_instance()
    health = HealthMonitor.get_instance()

    return {
        "active_broker": failover.active_broker,
        "is_failed_over": failover.is_failed_over,
        "connected_users": router.connected_users,
        "total_subscriptions": router.total_token_subscriptions,
        "adapters": {
            bt: dataclasses.asdict(h) for bt, h in health.get_all_health().items()
        },
    }
```

See [API Reference Section 14](../api/multi-broker-ticker-api.md#14-health-api-endpoint) for full response format.

### Step 5: Frontend Broker Status Banner

Add a small component showing "Data: SmartAPI" / "Data: Kite (SmartAPI recovering)" based on the failover message.

### Step 6: Remove Dead TickerServiceBase

**File**: `backend/app/services/brokers/market_data/ticker_base.py`

The new `TickerAdapter` in `ticker/adapter_base.py` replaces this. Delete or deprecate.

### Step 7: Grep for Legacy Ticker Imports

```bash
grep -rn "from app.services.legacy.smartapi_ticker\|from app.services.legacy.kite_ticker\|smartapi_ticker_service\|kite_ticker_service" backend/app/
```

Update or remove all remaining references to legacy ticker singletons.

### Phase 3 Verification

```bash
# Health endpoint works
curl http://localhost:8001/api/ticker/health
# Should return JSON with adapter health scores

# Failover test (manual disconnect simulation)
# See Step 3 above

# All tests still pass
pytest tests/ -v -m "not slow"
npm test
```

---

## Phase 4: Additional Broker Adapters

**Timeline**: ~2 days per broker | **Milestone**: Each broker's ticks flow through the new pipeline. Zero changes to websocket.py/TickerPool/TickerRouter.

### Per-Broker Implementation Checklist

For each broker (Upstox → Dhan → Fyers → Paytm):

1. **Implement adapter** — Replace stub in `ticker/adapters/{broker}.py` with full implementation:
   - Upstox: Protobuf deserialization, asyncio-native WS, `NSE_FO|{token}` format
   - Dhan: Little-endian binary (`struct.unpack('<...')`), Thread, numeric security_id
   - Fyers: JSON (simplest), asyncio-native, dual WS, `NSE:` prefix strip
   - Paytm: JSON, asyncio-native, 3-token auth, `{exchange}.{type}!{id}` format

2. **Extend SymbolConverter** — Add broker-specific conversion rules in `market_data/symbol_converter.py`

3. **Populate TokenManager** — Add broker's instrument master download to populate `broker_instrument_tokens` table

4. **Add system credentials** — Add broker's config entries and DB record

5. **Integration test** — Subscribe/unsubscribe/tick-flow for the new broker

6. **Test failover** — Test failover FROM and TO this broker

### Verification per Broker

```bash
# Ticks flow through new pipeline
python -c "
from app.services.brokers.market_data.ticker.adapters.{broker} import {Broker}TickerAdapter
adapter = {Broker}TickerAdapter()
print(f'{adapter.broker_type} adapter ready')
"

# Zero changes to core files
git diff --stat backend/app/api/routes/websocket.py
git diff --stat backend/app/services/brokers/market_data/ticker/pool.py
git diff --stat backend/app/services/brokers/market_data/ticker/router.py
# All three should show 0 changes
```

---

## Phase 5: Order Execution Expansion

**Timeline**: ~1 week | **Milestone**: Users can select broker for orders (6 options).

### Step 1: Implement AngelAdapter

**File**: `backend/app/services/brokers/angel_adapter.py`

Full `BrokerAdapter` implementation for SmartAPI order execution using SmartConnect library.

### Step 2: Create Order Adapter Stubs

Create stubs for Upstox, Dhan, Fyers, Paytm in `backend/app/services/brokers/`.

### Step 3: Register in Order Factory

**File**: `backend/app/services/brokers/factory.py`

```python
_BROKER_ADAPTERS = {
    BrokerType.KITE: KiteAdapter,
    BrokerType.ANGEL: AngelAdapter,
    BrokerType.UPSTOX: UpstoxAdapter,
    BrokerType.DHAN: DhanAdapter,
    BrokerType.FYERS: FyersAdapter,
    BrokerType.PAYTM: PaytmAdapter,
}
```

### Step 4: Add order_execution_broker Column

Add to `UserPreferences` model if not exists. Create migration.

### Step 5: Migrate get_kite_client() Usages

Search: `grep -rn "get_kite_client()" backend/app/`

Replace ~40 usages across AutoPilot/AI routes with broker-agnostic adapter methods.

### Step 6: Frontend Broker Selection UI

Complete the Settings page with market data + order execution dropdowns.

---

## Troubleshooting

### SmartAPI Threading Error

**Symptom**: `RuntimeError: There is no current event loop in thread`

**Fix**: Ensure `self._loop = asyncio.get_event_loop()` is called in `connect()` (before starting thread), and `asyncio.run_coroutine_threadsafe(coro, self._loop)` is used in callbacks.

### Token Mapping Not Working

**Symptom**: Ticks show SmartAPI tokens (e.g., 99926000) instead of canonical tokens (256265)

**Fix**: Check `_REVERSE_INDEX_MAP` is populated. Verify `_get_canonical_token()` is called in `_normalize_tick()`.

### Ref Count Leak (Subscriptions Never Cleaned)

**Symptom**: Broker stays subscribed to tokens even after all users disconnect

**Fix**: Verify `unregister_user()` calls `pool.remove_subscriptions()` for all user tokens. Check that ref counts actually decrement to 0.

### Health Score Always 0

**Symptom**: `GET /api/ticker/health` shows health_score: 0 for connected adapter

**Fix**: Verify `pool._on_adapter_tick()` calls `health_monitor.record_ticks()`. Verify `record_connect()` is called after adapter connects.

### Failover Not Triggering

**Symptom**: SmartAPI disconnects but no failover to Kite

**Fix**: Check `health_monitor.set_on_health_change(failover.on_health_change)` was called in main.py. Check `TICKER_FAILOVER_CHECKS` config (default 3 — takes 15s).

### Circular Import

**Symptom**: `ImportError: cannot import name 'TickerPool'`

**Fix**: Use lazy imports in `_create_adapter()`. Don't import pool from adapters.

---

## Rollback Procedures

### Phase 1 Rollback

```bash
alembic downgrade -1
rm -rf backend/app/services/brokers/market_data/ticker/
rm backend/app/models/system_broker_credentials.py
git checkout backend/app/models/__init__.py
git checkout backend/alembic/env.py
git checkout backend/app/config.py
git checkout backend/app/main.py
```

### Phase 2 Rollback

```bash
git checkout backend/app/api/routes/websocket.py
git checkout backend/app/services/legacy/smartapi_ticker.py
git checkout backend/app/services/legacy/kite_ticker.py
```

### Phase 3 Rollback

Remove failover controller and health endpoint. Keep adapter architecture from Phase 2.

---

## Success Metrics

| Metric | Target | How to Verify |
|--------|--------|---------------|
| websocket.py line count | < 100 | `wc -l backend/app/api/routes/websocket.py` |
| Broker-specific code in route | 0 | `grep -c "smartapi\|kite\|KITE_TO" backend/app/api/routes/websocket.py` |
| New broker addition effort | 1 file + registration | Verify stub adapters don't require route changes |
| Failover time | < 15 seconds | Manual test: disconnect primary → measure time to secondary |
| Health endpoint | Returns scores | `curl localhost:8001/api/ticker/health` |
| Tick latency increase | < 5ms | Compare tick arrival time before/after refactor |
| E2E tests | All pass | `npm test` |

---

## References

- [ADR-003 v2: Multi-Broker Ticker Architecture](../decisions/003-multi-broker-ticker-architecture.md) — Architecture rationale
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Full code and interfaces
- [WebSocket Architecture](./websocket.md) — Connection flow and message protocol
- [Broker Abstraction Architecture](./broker-abstraction.md) — Market data + order execution design
- [Legacy SmartAPI Ticker](../../backend/app/services/legacy/smartapi_ticker.py) — Threading pattern reference
