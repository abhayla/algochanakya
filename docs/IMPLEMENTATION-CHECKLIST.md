# Implementation Checklist

**Last Updated:** 2026-02-13

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

### Phase 4: Multi-Broker Ticker Architecture 🟡 PROPOSED (ADR-003)

**Goal:** Unified multi-tenant WebSocket ticker system supporting concurrent broker connections.

**Status:** Proposed — Design documented in [ADR-003](decisions/003-multi-broker-ticker-architecture.md)

**Design Documents:**
- [ADR-003: Multi-Broker Ticker Architecture](decisions/003-multi-broker-ticker-architecture.md) — Decision rationale and architecture
- [Implementation Guide](architecture/multi-broker-ticker-implementation.md) — Step-by-step implementation plan
- [API Reference](api/multi-broker-ticker-api.md) — Complete API documentation
- [Architecture Comparison](architecture/websocket-ticker-architectures-comparison.md) — Evaluated alternatives

**Skill Guidance:** Use `/smartapi-expert` or `/kite-expert` for broker-specific WebSocket protocol details. See [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) section 4 for WebSocket capability comparison.

#### Tasks

- [ ] **Remove dead WebSocket stubs from `MarketDataBrokerAdapter`**
  - Stubs moved to `MultiTenantTickerService` per ADR-003
  - File: `backend/app/services/brokers/market_data/market_data_base.py`

- [ ] **Implement `MultiTenantTickerService`**
  - Per ADR-003 architecture (single service managing multiple broker ticker connections)
  - File: `backend/app/services/brokers/market_data/multi_tenant_ticker.py`

- [ ] **Migrate `SmartAPITickerService` to implement `TickerServiceBase`**
  - File: `backend/app/services/legacy/smartapi_ticker.py`
  - Must implement interface from `ticker_base.py`

- [ ] **Migrate `KiteTickerService` to implement `TickerServiceBase`**
  - File: `backend/app/services/legacy/kite_ticker.py`
  - Must implement interface from `ticker_base.py`

- [ ] **Create ticker factory/registry**
  - File: `backend/app/services/brokers/market_data/ticker_factory.py`
  - Function: `get_ticker_service(broker_type) → TickerServiceBase`

- [ ] **Update WebSocket route to use ticker factory**
  - File: `backend/app/api/routes/websocket.py`
  - Use factory instead of direct imports

- [ ] **Implement subscription routing in `MultiTenantTickerService`**
  - Route subscriptions to correct broker ticker based on token mapping
  - Use `TokenManager` for broker resolution

- [ ] **Add health monitoring and auto-reconnect**
  - Per-broker connection health tracking
  - Automatic reconnection with exponential backoff

**Estimated effort:** 4-5 days

---

### Phase 5: User Configuration & New Broker Adapters

**Goal:** User-facing broker selection and additional broker adapters.

**Status:** Not started

**Skill Guidance:** Use broker expert skills (`/smartapi-expert`, `/kite-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert`) for API-specific guidance when implementing adapters. See [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) for cross-broker feature comparison.

#### Tasks

- [ ] **Create `AngelAdapter` for order execution** (moved from Phase 3)
  - File: `backend/app/services/brokers/angel_adapter.py`
  - Implement `BrokerAdapter` interface for Angel One orders
  - Use SmartAPI SDK for order placement
  - **Docs:** [Broker Abstraction - Adding a Broker](architecture/broker-abstraction.md#adding-a-new-broker-future-state)
  - **Skill:** `/smartapi-expert` for SmartAPI order endpoints and error codes

- [ ] **Create frontend broker settings UI**
  - File: `frontend/src/components/settings/BrokerSettings.vue`
  - Dropdowns for market data broker + order broker
  - Credential management forms per broker
  - Test connection buttons

- [ ] **Add broker selection API endpoints**
  - File: `backend/app/api/routes/user.py`
  - `PATCH /api/user/broker-preferences`
  - `GET /api/user/broker-preferences`

- [ ] **Create `UpstoxMarketDataAdapter`** (next broker)
  - File: `backend/app/services/brokers/market_data/upstox_adapter.py`
  - **Skill:** `/upstox-expert` for Protobuf WebSocket, extended token, instrument_key format

- [ ] **Create `UpstoxAdapter` for order execution**
  - File: `backend/app/services/brokers/upstox_adapter.py`
  - **Skill:** `/upstox-expert` for order endpoints and error handling

**Estimated effort:** 3-4 days per broker adapter

---

## 📋 Other Outstanding Tasks

### Testing

- [ ] **Add E2E tests for broker abstraction**
  - File: `tests/e2e/specs/broker-abstraction/`
  - Test broker selection in settings
  - Test order placement through different brokers
  - **Docs:** [Testing Guide](testing/README.md) | [CLAUDE.md - E2E Rules](../CLAUDE.md#e2e-test-rules-critical)

- [ ] **Add unit tests for broker adapters**
  - File: `backend/tests/unit/test_broker_adapters.py`
  - Mock broker APIs
  - Test unified data model conversion
  - **Command:** `pytest tests/unit/test_broker_adapters.py -v`

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
| **Phase 4: Ticker Architecture** | 8 | 0 | 🟡 Proposed (ADR-003) |
| **Phase 5: User Config & New Adapters** | 5 | 0 | 🔴 Not Started |

---

## 🎯 Suggested Implementation Order

1. **Phase 4** (Multi-Broker Ticker) - Implement ADR-003 architecture
2. **Phase 5** (User Config + Adapters) - Enable broker selection, add Upstox
3. **Testing & Docs** - Comprehensive tests and documentation updates

**Total estimated effort:** 10-14 days of focused development

---

## 📚 Key Documentation References

| Topic | Link |
|-------|------|
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
