# Implementation Checklist

**Last Updated:** 2026-02-17

This checklist tracks remaining implementation tasks with links to relevant documentation.

---

## 🎯 Current Focus: Multi-Broker Ticker Architecture (ADR-003)

**Reference:** [Broker Abstraction Architecture](architecture/broker-abstraction.md) | [ADR-002](decisions/002-broker-abstraction.md) | [ADR-003: Multi-Broker Ticker](decisions/003-multi-broker-ticker-architecture.md)

### Phase 2: Market Data Abstraction ✅ COMPLETE

**Goal:** Abstract SmartAPI and Kite market data services behind a unified interface.

**Status:** ✅ Complete (Jan 2026)

**Delivered:**
- `MarketDataBrokerAdapter` interface (`backend/app/services/brokers/market_data/market_data_base.py`)
- `SmartAPIMarketDataAdapter` implementation (`backend/app/services/brokers/market_data/smartapi_adapter.py`)
- `get_market_data_adapter()` factory (`backend/app/services/brokers/market_data/factory.py`)
- `TickerServiceBase` interface (`backend/app/services/brokers/market_data/ticker_base.py`)
- `TokenManager` for cross-broker token/symbol mapping (`token_manager.py`)
- `RateLimiter` for per-broker rate limiting (`rate_limiter.py`)
- `SymbolConverter` for canonical ↔ broker symbols (`symbol_converter.py`)
- `broker_instrument_tokens` database table for token mapping
- Unified exceptions (`exceptions.py`)

---

### Phase 3: Route Refactoring & Order Execution ✅ COMPLETE

**Goal:** Refactor all API routes to use broker factories instead of direct broker calls.

**Status:** ✅ Complete (Jan 2026)

**Delivered:**
- All routes refactored: `optionchain.py`, `ofo.py`, `orders.py`, `strategy_wizard.py`, `websocket.py`
- `KiteMarketDataAdapter` implemented (`backend/app/services/brokers/market_data/kite_adapter.py`)
- Routes use `get_broker_adapter()` and `get_market_data_adapter()` factories
- No more direct `KiteConnect` or `SmartAPI` imports in route files

**Deferred to Phase 5:**
- `AngelAdapter` for Angel One order execution (moved from Phase 3)

---

### Phase 4: Multi-Broker Ticker Architecture ✅ COMPLETE (Feb 2026)

**Goal:** Unified multi-tenant WebSocket ticker system supporting concurrent broker connections.

**Status:** ✅ Complete (Feb 2026) — 714 broker tests passing

**Design Documents:**
- [TICKER-DESIGN-SPEC.md](decisions/TICKER-DESIGN-SPEC.md) — 5-component architecture spec
- [API Reference](api/multi-broker-ticker-api.md) — Complete API documentation
- [Documentation Index](decisions/ticker-documentation-index.md) — All ticker docs

**Delivered:**
- `ticker/adapter_base.py` — `TickerAdapter` ABC (NormalizedTick with `Decimal` prices)
- `ticker/pool.py` — `TickerPool` (adapter lifecycle, ref-counted subscriptions, integrated credentials)
- `ticker/router.py` — `TickerRouter` (user fan-out, broker-to-user dispatch)
- `ticker/health.py` — `HealthMonitor` (5s heartbeat, per-adapter scoring, triggers failover)
- `ticker/failover.py` — `FailoverController` (make-before-break with configurable priority chain)
- `ticker/adapters/{smartapi,kite,dhan,fyers,paytm,upstox}.py` — All 6 broker adapters
- `backend/app/api/routes/websocket.py` — Refactored to 292 lines (broker-agnostic)
- `backend/app/api/routes/ticker.py` — New REST ticker management endpoints
- `backend/app/services/brokers/market_data/paytm_adapter.py` — Paytm REST adapter
- `backend/app/services/brokers/market_data/upstox_adapter.py` — Upstox REST adapter
- 714 broker tests: 413 ticker adapter + 122 core component + 179 REST adapter

---

### Phase 5: Order Execution Adapters & Frontend Broker UI ✅ COMPLETE (Feb 2026)

**Goal:** Order execution adapters for all 6 brokers and user-facing broker selection UI.

**Status:** ✅ Complete (Feb 2026)

**Reference:** [BrokerAdapter interface](../backend/app/services/brokers/base.py) | [KiteAdapter reference impl](../backend/app/services/brokers/kite_adapter.py) | [Working Doc](architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md)

**Delivered:**
- `backend/app/services/brokers/angelone_adapter.py` — AngelOne (SmartAPI) order execution
- `backend/app/services/brokers/upstox_order_adapter.py` — Upstox order execution (OAuth ~1yr)
- `backend/app/services/brokers/dhan_order_adapter.py` — Dhan order execution (static token)
- `backend/app/services/brokers/fyers_order_adapter.py` — Fyers order execution (OAuth)
- `backend/app/services/brokers/paytm_order_adapter.py` — Paytm order execution (3-token)
- `backend/app/services/brokers/factory.py` — All 6 adapters registered
- 61 unit tests in `backend/tests/backend/brokers/test_order_adapters.py`

#### Tasks

- [x] **Create `AngelOneAdapter` for order execution** (moved from Phase 3)
  - File: `backend/app/services/brokers/angelone_adapter.py`
  - Implement `BrokerAdapter` interface for Angel One (SmartAPI) orders

- [x] **Create `UpstoxOrderAdapter` for order execution**
  - File: `backend/app/services/brokers/upstox_order_adapter.py`

- [x] **Create `DhanOrderAdapter` for order execution**
  - File: `backend/app/services/brokers/dhan_order_adapter.py`

- [x] **Create `FyersOrderAdapter` for order execution**
  - File: `backend/app/services/brokers/fyers_order_adapter.py`

- [x] **Create `PaytmOrderAdapter` for order execution**
  - File: `backend/app/services/brokers/paytm_order_adapter.py`

- [x] **Register all new adapters in order execution factory**
  - File: `backend/app/services/brokers/factory.py`

- [x] **Create frontend broker settings UI**
  - Files: `frontend/src/components/settings/BrokerSettings.vue`, `frontend/src/stores/brokerPreferences.js`
  - Persistent upgrade banner: `frontend/src/components/common/BrokerUpgradeBanner.vue`
  - Source indicator badge: `frontend/src/components/common/DataSourceBadge.vue`
  - Market data broker dropdown (7 options: platform + 6 brokers) + order broker dropdown (6 brokers)
  - Banner wired into Dashboard, Watchlist, Option Chain, Positions
  - BrokerSettings section added to SettingsView

- [x] **Add broker selection API endpoints**
  - File: `backend/app/api/routes/user_preferences.py` (extended existing)
  - `PUT /api/user/preferences/` — now accepts `market_data_source` (7 values) and `order_broker` (6 values)
  - `GET /api/user/preferences/` — now returns `order_broker` field
  - Alembic migration: `a1b2c3d4e5f6_add_order_broker_and_platform_source.py`

**Estimated effort:** 3-4 days per order adapter, 2-3 days for frontend UI

---

## 📋 Other Outstanding Tasks

### Testing

- [x] **Add E2E tests for broker abstraction** ✅ Complete (Feb 2026)
  - `tests/e2e/specs/broker-abstraction/broker-settings.happy.spec.js` — settings UI happy path (12 tests)
  - `tests/e2e/specs/broker-abstraction/broker-banner.edge.spec.js` — banner/dismiss edge cases (8 tests)
  - `tests/e2e/pages/BrokerSettingsPage.js` — Page Object Model
  - **Docs:** [Testing Guide](testing/README.md) | [E2E Test Rules](testing/e2e-test-rules.md)

- [x] **Add unit tests for broker adapters** ✅ Complete (Feb 2026)
  - File: `backend/tests/backend/brokers/test_order_adapters.py` (61 tests passing)
  - Covers all 6 order adapters with mocked HTTP/SDK responses
  - Tests unified data model conversion for orders, positions, quotes
  - **Command:** `pytest backend/tests/backend/brokers/test_order_adapters.py -v`

- [ ] **Apply Alembic migration** (pending DB access)
  - Migration file: `backend/alembic/versions/a1b2c3d4e5f6_add_order_broker_and_platform_source.py`
  - Adds `order_broker` and `market_data_source` columns to user_preferences table
  - **Command:** `cd backend && alembic upgrade head` (run when DB at 103.118.16.189:5432 is accessible)

### Documentation

- [ ] **Generate OpenAPI spec**
  - File: `docs/api/openapi.yaml`
  - **Status:** Currently just placeholder

- [ ] **Update feature docs after broker refactor**
  - Use `docs-maintainer` skill after completing Phase 4
  - Update feature-registry.yaml

### AI Module Enhancements

- [ ] **Implement Kelly Criterion**
  - File: `backend/app/services/ai/kelly_calculator.py`
  - Currently marked as TBD in requirements
  - **Docs:** [AI Requirements](features/ai/REQUIREMENTS.md)

---

## 📊 Progress Tracking

| Phase | Tasks Total | Completed | Status |
|-------|-------------|-----------|--------|
| **Phase 1: SmartAPI Services** | - | - | ✅ Complete |
| **Phase 2: Market Data Abstraction** | 9 | 9 | ✅ Complete |
| **Phase 3: Route Refactoring** | 7 | 7 | ✅ Complete |
| **Phase 4: Ticker Architecture** | 14 | 14 | ✅ Complete (Feb 2026) |
| **Phase 5: User Config & Order Adapters** | 7 | 7 | ✅ Complete (Feb 2026) — Migration pending DB access |
| **Phase 6: Testing & Docs** | 3 | 2 | 🟡 E2E + unit tests done, Alembic migration pending |

---

## 🎯 Suggested Implementation Order

1. ~~**Phase 4** (Multi-Broker Ticker)~~ — ✅ COMPLETE
2. ~~**Phase 5** (Order Adapters + Frontend UI)~~ — ✅ COMPLETE
3. **Phase 6** (Testing & Docs) — 🟡 E2E + unit tests done; apply Alembic migration when DB accessible

**Total estimated effort:** Apply Alembic migration (30 min) + optional further testing

---

## 📚 Key Documentation References

| Topic | Link |
|-------|------|
| **Broker Data Checklist** | [Per-Broker Data Implementation Checklist](architecture/BROKER-DATA-IMPLEMENTATION-CHECKLIST.md) |
| **Autonomous Implementation Plan** | [Session-by-Session Execution Plan](guides/AUTONOMOUS-IMPLEMENTATION-PLAN.md) |
| **Multi-Broker Architecture** | [Broker Abstraction](architecture/broker-abstraction.md) |
| **Decision Rationale (Broker)** | [ADR-002](decisions/002-broker-abstraction.md) |
| **Ticker Architecture** | [ADR-003: Multi-Broker Ticker](decisions/003-multi-broker-ticker-architecture.md) |
| **Ticker Implementation Guide** | [Implementation Guide](architecture/multi-broker-ticker-implementation.md) |
| **Ticker API Reference** | [API Reference](api/multi-broker-ticker-api.md) |
| **Architecture Comparison** | [Ticker Architectures Comparison](architecture/websocket-ticker-architectures-comparison.md) |
| **Developer Guide** | [Developer Quick Reference](DEVELOPER-QUICK-REFERENCE.md) |
| **Important Patterns** | [CLAUDE.md - Patterns](../CLAUDE.md#important-patterns) |
| **Common Pitfalls** | [CLAUDE.md - Pitfalls](../CLAUDE.md#common-pitfalls) |
| **Testing Rules** | [Testing Guide](testing/README.md) |
| **Broker Expert Skills** | `/smartapi-expert`, `/kite-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert` |
| **Cross-Broker Comparison** | [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) |

---

**Questions or blockers?** Refer to [Developer Quick Reference](DEVELOPER-QUICK-REFERENCE.md) or check [CLAUDE.md](../CLAUDE.md) for troubleshooting.
