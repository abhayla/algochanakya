# ADR-003: Multi-Broker Ticker Architecture (v2)

**Status:** ⚠️ **REDESIGN PROPOSED** - See [TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md)

**Date:** 2026-02-13

**Latest Update:** February 14, 2026 - Redesign documentation phase

**Decision Makers:** Development Team

**Supersedes:** Original ADR-003 (Multiton TickerServiceManager pattern — rejected due to conflated concerns, no failover, passive health monitoring)

---

## 🔄 Redesign Proposal (Feb 14, 2026)

A refined v2 design has been proposed with the following improvements:

**Key changes:**
- **Components:** 6 → 5 (SystemCredentialManager merged into TickerPool)
- **websocket.py:** 495 → ~90 lines (82% reduction)
- **Data model:** NormalizedTick uses `Decimal` for prices (not `float`)
- **Kite positioning:** Failover-only (uses first user's OAuth token)
- **Credential management:** Integrated into TickerPool (simpler wiring)

**See:** [TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md) for complete redesign specification.

**Current document below describes the original v2 proposal (to be updated).**

---

## 1. Context & Problem Statement

AlgoChanakya streams live market data via WebSocket connections. The current implementation has two hardcoded global singletons (`smartapi_ticker_service`, `kite_ticker_service`) managed by a 495-line `websocket.py` route with broker-specific logic throughout.

### Current Architecture Problems

1. **Hardcoded Broker Logic**: `websocket.py` contains `KITE_TO_SMARTAPI_INDEX` dict (lines 32-43), broker-selection if/else branches, and credential-fetching helpers
2. **No Lifecycle Management**: Singletons are always alive, consuming resources even when no users are connected
3. **Dead Interface**: `TickerServiceBase` exists in `market_data/ticker_base.py` but is never implemented — method signatures don't match reality
4. **No Failover**: If SmartAPI goes down, the entire tick pipeline breaks — no automatic switchover
5. **No Health Monitoring**: No visibility into adapter connection state, tick latency, or error rates
6. **System Credentials Missing**: No concept of app-level broker credentials — uses per-user workaround
7. **Blocks Platform Goal**: Adding a new broker (Upstox, Dhan, Fyers, Paytm) requires extensive route modifications

### Two-Tier Architecture Requirement

| Tier | Purpose | Credentials | Pattern |
|------|---------|-------------|---------|
| **Tier 1: Market Data** | Live prices, ticks for all users | App-level (system) | One shared WS per broker |
| **Tier 2: Order Execution** | Place orders for individual users | Per-user (OAuth/TOTP) | Per-user broker connection |

This ADR addresses Tier 1 only. Tier 2 is covered by `BrokerAdapter` and `get_broker_adapter()` in ADR-002.

---

## 2. Decision — 5-Component Architecture

We will replace the legacy singletons and hardcoded route logic with a **5-component architecture** that cleanly separates concerns: adapter (per-broker WS), pool (lifecycle), router (user fan-out), health monitoring, and failover control.

### Why the Original ADR-003 Was Rejected

| Problem | Original ADR-003 | This ADR (v2) |
|---------|------------------|---------------|
| **Conflated concerns** | `MultiTenantTickerService` mixed broker WS + user management + broadcasting in one class | Separated: `TickerAdapter` (broker WS), `TickerRouter` (user fan-out), `TickerPool` (lifecycle) |
| **No failover** | Not addressed | `FailoverController` with make-before-break pattern |
| **Passive health** | Extended existing `WebSocketHealthMonitor` (event-driven only) | Active `HealthMonitor` with 5s heartbeat loop and health scoring |
| **Stateless manager** | `TickerServiceManager` was stateless static methods with class-level dicts | `TickerPool` singleton with proper lifecycle, ref-counting, idle cleanup |
| **No subscription aggregation** | Each user's subscriptions tracked independently per adapter | `TickerPool` ref-counts subscriptions — multiple users subscribing to same token = 1 broker subscription |

### Component Overview

| Component | Responsibility | Pattern | Location |
|-----------|---------------|---------|----------|
| **TickerAdapter** | Per-broker WebSocket connection, binary parsing, tick normalization | Abstract base + 6 implementations | `ticker/adapter_base.py` + `ticker/adapters/` |
| **TickerPool** | Adapter lifecycle, ref-counted subscription aggregation, idle cleanup | Singleton, owns all adapters | `ticker/pool.py` |
| **TickerRouter** | Map canonical_token → Set[user_ws], fan out ticks, user registration | Singleton, decoupled from brokers | `ticker/router.py` |
| **HealthMonitor** | Per-adapter heartbeat, latency, tick rate, error tracking, health scoring | Active monitoring (5s loop) | `ticker/health.py` |
| **FailoverController** | Primary → secondary switchover, failback, flap prevention | Make-before-break | `ticker/failover.py` |
| **SystemCredentialManager** | App-level API keys, auto-refresh tokens | Per-broker refresh loops | `ticker/credential_manager.py` |

---

## 3. Architecture Diagram

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                     FRONTEND (Vue)                            │
                    │   watchlist.js / optionchain.js / dashboard.js / positions.js │
                    └────────────────────────┬─────────────────────────────────────┘
                                             │ ws://localhost:8001/ws/ticks?token=<jwt>
                                             ▼
                    ┌──────────────────────────────────────────────────────────────┐
                    │              websocket.py (~90 lines)                         │
                    │   Authenticate JWT → register user → relay messages           │
                    └────────────────────────┬─────────────────────────────────────┘
                                             │
                                             ▼
                    ┌──────────────────────────────────────────────────────────────┐
                    │                    TickerRouter                               │
                    │   user_id → websocket mapping                                │
                    │   canonical_token → Set[user_id] mapping                     │
                    │   Fan out NormalizedTick to subscribed users                  │
                    └──────────────┬─────────────────────────┬─────────────────────┘
                                   │ subscribe/unsubscribe   │ dispatch(ticks)
                                   ▼                         ▲
                    ┌──────────────────────────────────────────────────────────────┐
                    │                     TickerPool                                │
                    │   Ref-counted subscriptions per broker                        │
                    │   Adapter creation / reuse / idle cleanup                     │
                    │   Wires adapter._on_tick → router.dispatch                    │
                    └─────┬──────────────┬──────────────┬─────────────────────────┘
                          │              │              │
                          ▼              ▼              ▼
                    ┌──────────┐  ┌──────────┐  ┌──────────┐
                    │ SmartAPI │  │   Kite   │  │  Upstox  │  ...
                    │ Adapter  │  │ Adapter  │  │ Adapter  │
                    └────┬─────┘  └────┬─────┘  └────┬─────┘
                         │             │              │
                         ▼             ▼              ▼
                    SmartAPI WS   Kite WS        Upstox WS
                    (binary)      (binary)       (protobuf)

                    ┌──────────────────────────────────────────────────────────────┐
                    │                   HealthMonitor                               │
                    │   Observes all adapters (5s heartbeat loop)                   │
                    │   Scores: Connection 30% + Latency 20% + Errors 20% +        │
                    │           Freshness 30%                                       │
                    │   Notifies FailoverController when health < threshold         │
                    └──────────────────────────┬───────────────────────────────────┘
                                               │ on_health_change callback
                                               ▼
                    ┌──────────────────────────────────────────────────────────────┐
                    │                 FailoverController                            │
                    │   Make-before-break: secondary up BEFORE primary down         │
                    │   Flap prevention: 120s minimum between events                │
                    │   Failback: primary health > 70 sustained 60s                 │
                    └──────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────────────────────┐
                    │              SystemCredentialManager                          │
                    │   Load from DB → authenticate → refresh loops                 │
                    │   Serves credentials to TickerPool on adapter creation        │
                    └──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow Sequences

### Sequence 1: User Subscribes to NIFTY

```
1. Frontend sends: {"action": "subscribe", "tokens": [256265], "mode": "quote"}
2. websocket.py → TickerRouter.subscribe(user_id="42", tokens=[256265], mode="quote")
3. TickerRouter → TickerPool.add_subscriptions(broker_type="smartapi", tokens=[256265], mode="quote")
4. TickerPool checks ref count for token 256265:
   - ref_count was 0 → needs broker subscription
   - ref_count becomes 1
5. TickerPool → SmartAPITickerAdapter.subscribe([256265])
6. SmartAPITickerAdapter translates: 256265 → "99926000" (via TokenManager)
7. SmartAPITickerAdapter sends to SmartAPI WS:
   subscribe(correlation_id="pool", mode=2, token_list=[{"exchangeType": 1, "tokens": ["99926000"]}])
8. websocket.py sends back: {"type": "subscribed", "tokens": [256265], "mode": "quote", "source": "smartapi"}
```

### Sequence 2: Tick Arrives

```
1. SmartAPI WS delivers binary tick on background thread
2. SmartAPITickerAdapter._on_data() parses binary → extracts SmartAPI token "99926000"
3. Adapter._normalize_tick(): token "99926000" → 256265 (canonical), prices ÷100 (paise→rupees)
4. Adapter calls _dispatch_from_thread(ticks) → asyncio.run_coroutine_threadsafe
5. TickerPool._on_adapter_tick(broker_type="smartapi", ticks=[NormalizedTick(token=256265, ltp=24500.50, ...)])
6. TickerPool → TickerRouter.dispatch(ticks)
7. TickerRouter looks up token 256265 → {user_42, user_78, user_103}
8. TickerRouter sends {"type":"ticks","data":[{...}]} to each user's WebSocket
9. HealthMonitor.record_ticks("smartapi", count=1) updates tick_count and last_tick_time
```

### Sequence 3: Failover Triggered

```
1.  HealthMonitor 5s loop: SmartAPI health score = 25 (below threshold 30)
2.  HealthMonitor increments consecutive_low_count for SmartAPI → now 3 (threshold: 3)
3.  HealthMonitor calls FailoverController._on_health_change("smartapi", score=25)
4.  FailoverController checks: last failover was 180s ago (> 120s cooldown) → proceed
5.  FailoverController._execute_failover("smartapi" → "kite"):
    a. TickerPool creates KiteTickerAdapter (if not exists) with system credentials
    b. Get all tokens subscribed on SmartAPI: {256265, 260105, 12345678}
    c. KiteTickerAdapter.subscribe([256265, 260105, 12345678]) — secondary now receiving ticks
    d. Wait 2 seconds (overlap period — both adapters active)
    e. TickerRouter.switch_users_broker("smartapi", "kite") — users now routed to Kite ticks
    f. SmartAPITickerAdapter.unsubscribe(all) — primary cleaned up
6.  FailoverController sets active_broker = "kite", is_failed_over = True
7.  websocket.py broadcasts to all connected users:
    {"type": "failover", "from": "smartapi", "to": "kite", "message": "Switched to Kite (SmartAPI recovering)"}
```

### Sequence 4: System Startup

```
1. main.py lifespan → startup
2. Create singletons: TickerPool, TickerRouter, HealthMonitor, FailoverController, SystemCredentialManager
3. Wire dependencies:
   - TickerPool.set_dependencies(credential_manager, health_monitor, ticker_router)
   - FailoverController.set_dependencies(ticker_pool, ticker_router, health_monitor)
4. SystemCredentialManager.initialize():
   a. Load system_broker_credentials from DB
   b. For SmartAPI: authenticate with auto-TOTP → store jwt_token, feed_token
   c. For Dhan: validate static token
   d. For Kite: log "requires user OAuth — will use first connected user's token"
   e. Start per-broker refresh loops (SmartAPI: 30 min before 5AM IST expiry)
5. HealthMonitor.start() → begins 5s heartbeat loop
6. Log: "Ticker system initialized. Primary: smartapi, Secondary: kite"
7. No adapters connected yet — they connect on first user subscription (lazy)
```

---

## 5. Component Interfaces (Summary)

Full method signatures, parameters, and return types are in the [API Reference](../api/multi-broker-ticker-api.md).

### TickerAdapter (Abstract Base)

```python
class TickerAdapter(ABC):
    # Lifecycle
    async def connect(self, credentials: dict) -> None
    async def disconnect(self) -> None
    async def reconnect(self) -> None

    # Subscriptions
    async def subscribe(self, canonical_tokens: List[int], mode: str = "quote") -> None
    async def unsubscribe(self, canonical_tokens: List[int]) -> None

    # Properties
    broker_type: str
    is_connected: bool
    subscribed_tokens: Set[int]
    last_tick_time: Optional[datetime]

    # Abstract (broker-specific)
    async def _connect_impl(self, credentials: dict) -> None
    async def _disconnect_impl(self) -> None
    async def _subscribe_impl(self, broker_tokens: list, mode: str) -> None
    async def _unsubscribe_impl(self, broker_tokens: list) -> None
    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list
    def _normalize_tick(self, raw_tick: Any) -> NormalizedTick
    def _get_canonical_token(self, broker_token: Any) -> int

    # Dispatch helpers
    def _dispatch_from_thread(self, ticks: List[NormalizedTick]) -> None
    async def _dispatch_async(self, ticks: List[NormalizedTick]) -> None

    # Credential update (for refresh)
    async def update_credentials(self, credentials: dict) -> None
```

### TickerPool

```python
class TickerPool:
    # Singleton
    @classmethod
    def get_instance(cls) -> "TickerPool"

    # Dependency injection
    def set_dependencies(self, credential_manager, health_monitor, ticker_router) -> None

    # Adapter management
    def get_adapter(self, broker_type: str) -> TickerAdapter
    async def add_subscriptions(self, broker_type: str, canonical_tokens: List[int], mode: str) -> None
    async def remove_subscriptions(self, broker_type: str, canonical_tokens: List[int]) -> None
    async def shutdown(self) -> None
```

### TickerRouter

```python
class TickerRouter:
    @classmethod
    def get_instance(cls) -> "TickerRouter"
    def set_pool(self, pool: TickerPool) -> None

    # User management
    async def register_user(self, user_id: str, websocket: WebSocket, broker_type: str) -> None
    async def unregister_user(self, user_id: str) -> None

    # Subscriptions
    async def subscribe(self, user_id: str, canonical_tokens: List[int], mode: str) -> None
    async def unsubscribe(self, user_id: str, canonical_tokens: List[int]) -> None

    # Tick dispatch (hot path)
    async def dispatch(self, ticks: List[NormalizedTick]) -> None

    # Failover support
    async def switch_users_broker(self, from_broker: str, to_broker: str) -> None
    def get_tokens_for_broker(self, broker_type: str) -> Set[int]

    # Properties
    connected_users: int
    total_token_subscriptions: int
```

### HealthMonitor

```python
class HealthMonitor:
    # Registration
    def register_adapter(self, broker_type: str) -> None
    def unregister_adapter(self, broker_type: str) -> None

    # Recording (called by pool/adapters)
    def record_ticks(self, broker_type: str, count: int) -> None
    def record_error(self, broker_type: str, error: str) -> None
    def record_disconnect(self, broker_type: str) -> None
    def record_connect(self, broker_type: str) -> None

    # Health queries
    def get_health(self, broker_type: str) -> AdapterHealth
    def get_all_health(self) -> Dict[str, AdapterHealth]

    # Lifecycle
    async def start(self) -> None   # Start 5s heartbeat loop
    async def stop(self) -> None

    # Callback
    def set_on_health_change(self, callback: Callable) -> None
```

### FailoverController

```python
class FailoverController:
    def set_dependencies(self, pool, router, health_monitor) -> None

    # Properties
    active_broker: str
    is_failed_over: bool

    # Internal (triggered by HealthMonitor callback)
    async def _execute_failover(self, from_broker: str, to_broker: str) -> None
    async def _execute_failback(self) -> None
```

---

## 6. Per-Broker Adapter Specifications

### SmartAPI (Angel One)

| Aspect | Details |
|--------|---------|
| **WS URL** | `wss://smartapisocket.angelone.in/smart-stream` |
| **Auth** | System credentials: auto-TOTP (jwt_token, api_key, client_id, feed_token) |
| **Subscribe format** | `ws.subscribe(correlation_id, mode, [{"exchangeType": 2, "tokens": ["99926000"]}])` |
| **Mode values** | 1=LTP, 2=Quote, 3=Snap Quote |
| **Exchange type codes** | NSE=1, NFO=2, BSE=3, BFO=4, MCX=5 |
| **Tick parsing** | Custom binary (big-endian). SmartWebSocketV2 library handles parsing. |
| **Price normalization** | Paise ÷ 100 → Rupees |
| **Token translation** | TokenManager + `broker_instrument_tokens` table. Index: 256265→"99926000" |
| **Threading model** | `threading.Thread(daemon=True)` running `SmartWebSocketV2.connect()`. Bridge to asyncio via `asyncio.run_coroutine_threadsafe`. **CRITICAL**: Preserve exact pattern from `smartapi_ticker.py:117-124` |
| **Connection limits** | 3000 tokens max, 3 concurrent connections per API key |
| **Quirks** | Exchange type code required per subscription group. Index tokens use NSE exchange type (1), not NFO (2). Feed token required alongside JWT. |

### Kite (Zerodha)

| Aspect | Details |
|--------|---------|
| **WS URL** | `wss://ws.kite.trade/` (handled by KiteTicker library) |
| **Auth** | User OAuth only — no system credentials possible. Uses first connected user's token as fallback. |
| **Subscribe format** | `ticker.subscribe([256265, 260105])` then `ticker.set_mode(MODE_QUOTE, [256265])` |
| **Mode values** | `MODE_LTP`, `MODE_QUOTE`, `MODE_FULL` |
| **Tick parsing** | Custom binary (big-endian). KiteTicker library handles parsing — delivers Python dicts. |
| **Price normalization** | WS data in paise ÷ 100 → Rupees. REST data already in Rupees. |
| **Token translation** | None — Kite format IS canonical format (identity mapping) |
| **Threading model** | KiteTicker library manages its own thread internally. `ticker.connect(threaded=True)`. Bridge to asyncio via `asyncio.run_coroutine_threadsafe`. |
| **Connection limits** | 3000 tokens max, 3 concurrent connections per API key |
| **Quirks** | No system credentials (OAuth per-user only). `instrument_token` is integer, same as canonical. |

### Upstox

| Aspect | Details |
|--------|---------|
| **WS URL** | Obtained via `GET /v2/feed/market-data-feed/authorize` → returns WS URL |
| **Auth** | System credentials: OAuth 2.0 with extended token (valid ~1 year) |
| **Subscribe format** | JSON: `{"guid": "id", "method": "sub", "data": {"mode": "full", "instrumentKeys": ["NSE_FO|12345"]}}` |
| **Tick parsing** | **Protobuf** — requires `MarketDataFeed` proto deserialization |
| **Price normalization** | Prices in Rupees (no conversion needed) |
| **Token translation** | `NSE_FO|{instrument_token}` format. Lookup via instrument master CSV. |
| **Threading model** | asyncio-native (`websockets` library) — no threading needed |
| **Connection limits** | 1 connection per access token |
| **Quirks** | Protobuf adds dependency. WS URL must be fetched fresh each session. Extended token simplifies system credential management. |

### Dhan

| Aspect | Details |
|--------|---------|
| **WS URL** | `wss://api-feed.dhan.co` |
| **Auth** | System credentials: static API token (never expires unless revoked) |
| **Subscribe format** | Binary packet: 83-byte header + instrument list (little-endian) |
| **Tick parsing** | **Little-endian binary** — `struct.unpack('<...')`. Note: opposite endianness from SmartAPI/Kite. |
| **Price normalization** | Prices in Rupees (no conversion needed) |
| **Token translation** | Numeric `security_id` — requires full CSV instrument master mapping |
| **Threading model** | `threading.Thread` — Dhan WS client is synchronous |
| **Connection limits** | 5 connections max, 100 instruments per connection |
| **Quirks** | Little-endian binary (unusual). 200-level market depth available. Static token makes system credential management trivial. Free if 25+ F&O trades/month. |

### Fyers

| Aspect | Details |
|--------|---------|
| **WS URL** | `wss://socket.fyers.in/hsm/v3/` (data) and separate orders WS |
| **Auth** | System credentials: OAuth 2.0. WS auth format: `{app_id}:{access_token}` |
| **Subscribe format** | JSON: `{"T": "SUB_L2", "L2LIST": ["NSE:NIFTY50-INDEX"], "SUB_T": 1}` |
| **Tick parsing** | **JSON** (simplest parser). Data arrives as JSON objects. |
| **Price normalization** | Prices in Rupees (no conversion needed) |
| **Token translation** | `NSE:{symbol}` prefix format. Strip `NSE:` prefix for canonical. |
| **Threading model** | asyncio-native (`fyers_api` library has async WS client) |
| **Connection limits** | 200 symbols per connection |
| **Quirks** | Dual WebSocket system (data + orders — only data WS needed for tickers). JSON parsing is simplest of all brokers. Symbol format close to canonical (just prefix stripping). |

### Paytm Money

| Aspect | Details |
|--------|---------|
| **WS URL** | `wss://developer-ws.paytmmoney.com/broadcast/user/v1/data` |
| **Auth** | System credentials: OAuth 2.0 with 3 JWTs (access, read, public). WS uses `public_access_token`. |
| **Subscribe format** | JSON: `{"method": "subscribe", "data": [{"ric": "4.1!1234", "mode": "FULL"}]}` |
| **Tick parsing** | **JSON** |
| **Price normalization** | Prices in Rupees (no conversion needed) |
| **Token translation** | `{exchange_segment}.{exchange_type}!{security_id}` format. Numeric security_id requires CSV lookup. |
| **Threading model** | asyncio-native |
| **Connection limits** | 200 instruments per connection |
| **Quirks** | 3-token auth system (access_token for REST, read_access_token for portfolio, public_access_token for WS). RIC format is unique. |

---

## 7. System Credentials Design

### New Database Table: `system_broker_credentials`

```sql
CREATE TABLE system_broker_credentials (
    id              BIGSERIAL PRIMARY KEY,
    broker          VARCHAR(20) NOT NULL UNIQUE,  -- 'smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm'

    -- Encrypted credential storage
    jwt_token       TEXT,          -- SmartAPI JWT
    access_token    TEXT,          -- Kite/Upstox/Fyers/Paytm
    refresh_token   TEXT,          -- SmartAPI/Upstox/Fyers refresh
    feed_token      TEXT,          -- SmartAPI feed token for WS
    api_key         TEXT,          -- Broker API key (encrypted)
    api_secret      TEXT,          -- Broker API secret (encrypted)

    -- Session metadata
    client_id       VARCHAR(50),   -- Broker client/user ID
    token_expiry    TIMESTAMPTZ,   -- When current tokens expire

    -- Status
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_auth_at    TIMESTAMPTZ,
    last_error      TEXT,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_system_broker_credentials_broker ON system_broker_credentials(broker);
```

### Per-Broker System Credential Support

| Broker | System Creds? | Auth Method | Token Lifetime | Auto-Refresh |
|--------|--------------|-------------|----------------|--------------|
| **SmartAPI** | Yes | Auto-TOTP (reuse `smartapi_auth.py`) | Until 5 AM IST next day | Yes — refresh 30 min before expiry |
| **Kite** | No (user OAuth only) | Uses first connected user's OAuth token | 1 trading day | No — requires manual re-login |
| **Upstox** | Yes | OAuth 2.0 with extended token | ~1 year | Yes — refresh before expiry |
| **Dhan** | Yes | Static API token | Never expires (until revoked) | No — static token |
| **Fyers** | Yes | OAuth 2.0 | Until midnight IST | Yes — refresh before midnight |
| **Paytm** | Yes | OAuth 2.0 (3 JWTs) | 1 trading day | Yes — refresh before close |

### Kite Exception

Kite Connect requires per-user OAuth (no way to authenticate without user browser interaction). The system handles this by:
1. On first Kite user connection, capture their OAuth token
2. Use this token for system-level Kite WS if configured as secondary
3. If no Kite users connected, Kite adapter cannot start (documented limitation)
4. Failover TO Kite requires at least one user with active Kite credentials

---

## 8. Health Scoring & Failover Rules

### Health Score Formula

Each adapter has a health score (0-100) calculated every 5 seconds:

```
health_score = (
    connection_score * 0.30 +    # 30%: Is WS connected?
    latency_score    * 0.20 +    # 20%: Average tick latency
    error_score      * 0.20 +    # 20%: Error rate in last 60s
    freshness_score  * 0.30      # 30%: Time since last tick
)
```

**Component scoring:**

| Component | Score 100 | Score 50 | Score 0 |
|-----------|-----------|----------|---------|
| Connection | Connected | Reconnecting | Disconnected |
| Latency | < 100ms | 100-500ms | > 1000ms |
| Error rate | 0 errors/60s | 1-3 errors/60s | > 5 errors/60s |
| Freshness | Tick < 5s ago | Tick 5-30s ago | No tick > 60s |

### Failover Rules

| Event | Condition | Action |
|-------|-----------|--------|
| **Failover trigger** | Health < 30 for 3 consecutive checks (15s total) | Execute failover to secondary |
| **Failback trigger** | Primary health > 70 sustained for 60s | Execute failback to primary |
| **Flap prevention** | < 120s since last failover event | Skip — too recent |
| **Make-before-break** | Always | Subscribe on secondary BEFORE unsubscribing from primary. 2s overlap. |

### Failover Sequence (Make-Before-Break)

```
Step 1: TickerPool creates secondary adapter (e.g., Kite) with credentials
Step 2: Subscribe all current tokens on secondary adapter
Step 3: Wait 2 seconds (both adapters now receiving ticks)
Step 4: TickerRouter.switch_users_broker("smartapi", "kite")
        → All user WS connections now receive Kite ticks
Step 5: SmartAPITickerAdapter.unsubscribe(all)
        → Primary cleaned up but not disconnected (may recover)
Step 6: Notify frontend: {"type": "failover", "from": "smartapi", "to": "kite"}
```

---

## 9. Database Changes

### New Table

- `system_broker_credentials` — see schema in Section 7

### No Changes to Existing Tables

- `broker_instrument_tokens` — already exists, used by TokenManager for cross-broker symbol/token mapping
- `user_preferences` — already has `market_data_source` column
- `smartapi_credentials` — per-user credentials, separate from system credentials

---

## 10. File Structure

```
backend/app/services/brokers/market_data/ticker/
├── __init__.py              # Package exports
├── models.py                # NormalizedTick dataclass
├── adapter_base.py          # TickerAdapter ABC
├── pool.py                  # TickerPool singleton
├── router.py                # TickerRouter singleton
├── health.py                # HealthMonitor + AdapterHealth
├── failover.py              # FailoverController + FailoverConfig
├── credential_manager.py    # SystemCredentialManager
└── adapters/
    ├── __init__.py
    ├── smartapi.py           # SmartAPITickerAdapter
    ├── kite.py               # KiteTickerAdapter
    ├── upstox.py             # UpstoxTickerAdapter (stub)
    ├── dhan.py               # DhanTickerAdapter (stub)
    ├── fyers.py              # FyersTickerAdapter (stub)
    └── paytm.py              # PaytmTickerAdapter (stub)

backend/app/models/
└── system_broker_credentials.py  # SystemBrokerCredential SQLAlchemy model
```

---

## 11. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| SmartAPI threading breaks during port | HIGH | MEDIUM | Preserve exact `threading.Thread + asyncio.run_coroutine_threadsafe` pattern from `smartapi_ticker.py:117-124` and `208-211` |
| Failover triggers too aggressively | MEDIUM | MEDIUM | 3-check threshold (15s), 120s flap prevention, health score weighting tuned for trading hours |
| Token refresh race condition | MEDIUM | LOW | Per-broker `asyncio.Lock` in SystemCredentialManager. Adapters notified via `update_credentials()` callback. |
| Token mapping incomplete for new brokers | MEDIUM | MEDIUM | Use `broker_instrument_tokens` table via `TokenManager` as primary. Hardcoded fallback for index tokens only. |
| Kite system credentials unavailable | LOW | HIGH | Kite is secondary-only. If no Kite users connected, failover TO Kite is blocked. Documented limitation. |
| Hot path (dispatch) performance | MEDIUM | LOW | No locks on dispatch path. Python GIL makes dict reads thread-safe. Worst case: tick to just-unsubscribed user (harmless). |
| WebSocket disconnect cascade | MEDIUM | LOW | Reconnect with exponential backoff. Frontend keeps connection open during failover — no reconnect needed. |

---

## 12. Consequences

### Positive

1. **websocket.py: 495 → ~90 lines** (82% reduction). Zero broker-specific code in routes.
2. **Adding new broker = 1 adapter file + factory registration**. Zero changes to pool/router/route.
3. **Automatic failover** for production reliability — no manual intervention needed.
4. **Ref-counted subscriptions** — 100 users subscribing to NIFTY = 1 broker subscription. Efficient.
5. **Active health monitoring** with quantitative scores — visible via `/api/ticker/health` endpoint.
6. **System credentials** properly separated from user credentials (Tier 1 vs Tier 2).
7. **Clean separation of concerns** — adapter (broker WS), pool (lifecycle), router (users), health, failover.

### Negative

1. **Migration complexity** — Must carefully port SmartAPI/Kite threading logic from legacy services.
2. **More files** — 8 core files + 6 adapter files vs current 2 singletons + 1 route.
3. **Kite limitation** — Cannot be primary system data source (requires user OAuth).
4. **Testing burden** — Need to test failover scenarios, health scoring, ref-counting edge cases.

---

## Alternatives Considered

### Alternative 1: Keep Singletons, Add Router Only

**Rejected**: Doesn't solve lifecycle management, system credentials, or failover. Can't scale to 6 brokers.

### Alternative 2: Original ADR-003 (Multiton TickerServiceManager)

**Rejected**: Conflated adapter + user management in one class. No failover. Passive health monitoring. See comparison table in Section 2.

### Alternative 3: Event Bus / Message Queue Pattern

**Description**: Use Redis pub/sub or similar message bus between adapters and users.

**Rejected**: Adds infrastructure dependency (Redis already used for sessions, but pub/sub for real-time ticks adds latency). In-process dispatch is faster and simpler for single-server deployment.

---

## References

- [ADR-002: Multi-Broker Abstraction](./002-broker-abstraction.md) — Parent architecture
- [Broker Abstraction Architecture](../architecture/broker-abstraction.md) — Complete technical design
- [Multi-Broker Ticker Implementation Guide](../architecture/multi-broker-ticker-implementation.md) — Step-by-step phased guide
- [Multi-Broker Ticker API Reference](../api/multi-broker-ticker-api.md) — Full interface specifications
- [WebSocket Architecture](../architecture/websocket.md) — WebSocket connection flow and protocol
- [Legacy SmartAPI Ticker](../../backend/app/services/legacy/smartapi_ticker.py) — Reference threading pattern
- [Legacy Kite Ticker](../../backend/app/services/legacy/kite_ticker.py) — Reference connection pattern
- [Current WebSocket Route](../../backend/app/api/routes/websocket.py) — To be refactored

---

## Approval

- [ ] Development Team Review
- [ ] Architecture Review
- [ ] Security Review (system credentials encryption, DB storage)
- [ ] Testing Strategy Approved
- [ ] Migration Plan Approved
- [ ] Rollback Plan Defined

## Rollback Plan

1. **Phase 1 Rollback**: Drop `system_broker_credentials` table, remove `ticker/` directory, no route changes yet
2. **Phase 2 Rollback**: Revert `websocket.py` from git, reconnect to legacy singletons
3. **Phase 3 Rollback**: Revert failover components, keep basic adapter architecture

**Git Tags**: Tag `pre-ticker-refactor` before Phase 1, `post-phase-{N}` after each phase.
