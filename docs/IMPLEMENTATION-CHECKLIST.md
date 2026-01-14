# Implementation Checklist

**Last Updated:** 2026-01-14

This checklist tracks remaining implementation tasks with links to relevant documentation.

---

## 🎯 Current Focus: Complete Broker Abstraction

**Reference:** [Broker Abstraction Architecture](architecture/broker-abstraction.md) | [ADR-002](decisions/002-broker-abstraction.md)

### Phase 2: Market Data Abstraction

**Goal:** Abstract SmartAPI and Kite market data services behind a unified interface.

**Status:** Not started

#### Tasks

- [ ] **Create MarketDataBrokerAdapter interface**
  - File: `backend/app/services/brokers/market_data/base.py`
  - Define abstract methods:
    - `get_live_quote(symbol)` → `UnifiedQuote`
    - `get_historical_data(symbol, from_date, to_date, interval)` → List[OHLC]
    - `subscribe_ticks(symbols, callback)` → None
    - `unsubscribe_ticks(symbols)` → None
    - `search_instruments(query)` → List[Instrument]
  - **Docs:** [Broker Abstraction - Market Data](architecture/broker-abstraction.md#market-data-abstraction)

- [ ] **Create SmartAPIMarketDataAdapter**
  - File: `backend/app/services/brokers/market_data/smartapi_adapter.py`
  - Wrap existing SmartAPI services:
    - `SmartAPIMarketData` → `get_live_quote()`
    - `SmartAPIHistorical` → `get_historical_data()`
    - `SmartAPITickerService` → `subscribe_ticks()`, `unsubscribe_ticks()`
    - `SmartAPIInstruments` → `search_instruments()`
  - **Code Reference:**
    - `backend/app/services/smartapi_market_data.py`
    - `backend/app/services/smartapi_historical.py`
    - `backend/app/services/smartapi_ticker.py`
    - `backend/app/services/smartapi_instruments.py`

- [ ] **Create KiteMarketDataAdapter**
  - File: `backend/app/services/brokers/market_data/kite_adapter.py`
  - Implement interface using Kite Connect API
  - **Code Reference:** `backend/app/services/kite_ticker.py` (for WebSocket patterns)

- [ ] **Create market data factory**
  - File: `backend/app/services/brokers/market_data/factory.py`
  - Function: `get_market_data_adapter(broker_type: BrokerType, credentials) → MarketDataBrokerAdapter`
  - Registry pattern similar to order broker factory
  - **Code Reference:** `backend/app/services/brokers/factory.py`

- [ ] **Update module exports**
  - File: `backend/app/services/brokers/market_data/__init__.py`
  - Export interface, factory, and adapters

**Estimated effort:** 2-3 days

---

### Phase 3: Order Execution Completion

**Goal:** Refactor API routes to use broker factory instead of direct broker calls.

**Status:** Partially complete (adapters exist but routes don't use them)

#### Tasks

- [ ] **Refactor `auth.py` routes**
  - File: `backend/app/api/routes/auth.py`
  - Replace 7 instances of direct `KiteConnect` instantiation
  - Use `get_broker_adapter(BrokerType.KITE, credentials)`
  - **Lines:** Throughout file (search for `KiteConnect(`)
  - **Docs:** [Broker Abstraction - Implementation Note](architecture/broker-abstraction.md#-implementation-note)

- [ ] **Refactor `orders.py` routes**
  - File: `backend/app/api/routes/orders.py`
  - Replace `KiteOrderService` with `get_broker_adapter()`
  - Update to use `UnifiedOrder` model
  - **Docs:** [Broker Abstraction - Unified Models](architecture/broker-abstraction.md#unified-data-models)

- [ ] **Refactor `positions.py` routes**
  - File: `backend/app/api/routes/positions.py`
  - Replace `KiteOrderService` with broker adapter
  - Update to use `UnifiedPosition` model

- [ ] **Refactor `ofo.py` routes**
  - File: `backend/app/api/routes/ofo.py`
  - Replace `KiteOrderService` and direct `SmartAPIMarketData`
  - Use both order broker adapter + market data adapter (once Phase 2 complete)

- [ ] **Refactor `optionchain.py` routes**
  - File: `backend/app/api/routes/optionchain.py`
  - Replace direct `KiteConnect` and `SmartAPIMarketData`
  - Use market data adapter for quotes

- [ ] **Refactor `strategy_wizard.py` routes**
  - File: `backend/app/api/routes/strategy_wizard.py`
  - Replace direct `KiteConnect` for LTP calls
  - Use market data adapter

- [ ] **Update OrderExecutor service**
  - File: `backend/app/services/order_executor.py` (if exists)
  - Accept `BrokerAdapter` instead of `KiteConnect`

- [ ] **Create AngelAdapter for order execution**
  - File: `backend/app/services/brokers/angel_adapter.py`
  - Implement `BrokerAdapter` interface for Angel One
  - Use SmartAPI for order placement
  - **Docs:** [Broker Abstraction - Adding a Broker](architecture/broker-abstraction.md#adding-a-new-broker-future-state)

**Estimated effort:** 3-4 days

---

### Phase 4: Ticker Service Abstraction

**Goal:** Unified WebSocket ticker interface.

**Status:** Not started

#### Tasks

- [ ] **Create TickerService interface**
  - File: `backend/app/services/brokers/ticker/base.py`
  - Abstract methods:
    - `connect()` → None
    - `disconnect()` → None
    - `subscribe(tokens, mode, callback)` → None
    - `unsubscribe(tokens)` → None
  - **Docs:** [WebSocket Architecture](architecture/websocket.md)

- [ ] **Update KiteTickerService to implement interface**
  - File: `backend/app/services/kite_ticker.py`
  - Inherit from `TickerService`
  - Keep singleton pattern

- [ ] **Update SmartAPITickerService to implement interface**
  - File: `backend/app/services/smartapi_ticker.py`
  - Inherit from `TickerService`
  - Keep singleton pattern

- [ ] **Create ticker factory/registry**
  - File: `backend/app/services/brokers/ticker/factory.py`
  - Function: `get_ticker_service(broker_type: BrokerType) → TickerService`
  - Singleton management per broker type

- [ ] **Update WebSocket routes**
  - File: `backend/app/api/routes/websocket.py`
  - Use ticker factory instead of direct imports

**Estimated effort:** 2-3 days

---

### Phase 5: User Configuration

**Goal:** Allow users to select their preferred brokers.

**Status:** Not started

#### Tasks

- [ ] **Add broker columns to users table**
  - Migration: `alembic revision --autogenerate -m "add broker preferences to users"`
  - Columns:
    - `market_data_broker` (String, default: "smartapi")
    - `order_execution_broker` (String, default: "kite")
  - **Docs:** [Database Architecture](architecture/database.md) | [CLAUDE.md - Adding Models](../CLAUDE.md#adding-new-database-models)

- [ ] **Create broker credentials tables**
  - Already exists for SmartAPI: `smartapi_credentials`
  - Create for others as needed
  - Encrypt sensitive fields using `app.utils.encryption`
  - **Docs:** [CLAUDE.md - Encryption](../CLAUDE.md#encryption-for-credentials)

- [ ] **Create frontend broker settings UI**
  - File: `frontend/src/components/settings/BrokerSettings.vue`
  - Dropdowns for market data broker + order broker
  - Credential management forms
  - Test connection buttons

- [ ] **Add broker selection API endpoints**
  - File: `backend/app/api/routes/user.py`
  - `PATCH /api/user/broker-preferences`
  - `GET /api/user/broker-preferences`

**Estimated effort:** 2-3 days

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
  - Command: `python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > docs/api/openapi.json`
  - **Status:** Currently just placeholder

- [ ] **Update feature docs after broker refactor**
  - Use `docs-maintainer` skill after completing Phase 3
  - Update feature-registry.yaml
  - **Docs:** [docs/README.md - Feature Registry](README.md#feature-registry)

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
| **Phase 2: Market Data Abstraction** | 5 | 0 | 🔴 Not Started |
| **Phase 3: Order Execution** | 9 | 0 | 🟡 Partial (adapters exist) |
| **Phase 4: Ticker Abstraction** | 5 | 0 | 🔴 Not Started |
| **Phase 5: User Configuration** | 4 | 0 | 🔴 Not Started |

---

## 🎯 Suggested Implementation Order

1. **Phase 2** (Market Data Abstraction) - Foundation for all market data access
2. **Phase 3** (Refactor Routes) - Use the new abstractions in production code
3. **Phase 4** (Ticker Abstraction) - Complete WebSocket abstraction
4. **Phase 5** (User Config) - Enable user broker selection
5. **Testing & Docs** - Comprehensive tests and documentation updates

**Total estimated effort:** 12-15 days of focused development

---

## 📚 Key Documentation References

| Topic | Link |
|-------|------|
| **Multi-Broker Architecture** | [Broker Abstraction](architecture/broker-abstraction.md) |
| **Decision Rationale** | [ADR-002](decisions/002-broker-abstraction.md) |
| **Developer Guide** | [Developer Quick Reference](DEVELOPER-QUICK-REFERENCE.md) |
| **Important Patterns** | [CLAUDE.md - Patterns](../CLAUDE.md#important-patterns) |
| **Common Pitfalls** | [CLAUDE.md - Pitfalls](../CLAUDE.md#common-pitfalls) |
| **Testing Rules** | [Testing Guide](testing/README.md) |

---

**Questions or blockers?** Refer to [Developer Quick Reference](DEVELOPER-QUICK-REFERENCE.md) or check [CLAUDE.md](../CLAUDE.md) for troubleshooting.
