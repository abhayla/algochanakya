# Backend Development Guide

> This file provides backend-specific guidance for Claude Code. It loads automatically when working with `backend/` files.
> For cross-cutting rules and mandatory behaviors, see the [root CLAUDE.md](../CLAUDE.md).

---

## Development Commands

From `backend/`:

```bash
venv\Scripts\activate          # Activate venv (Windows)
python run.py                  # Start server (auto-downloads instruments if DB empty)
alembic upgrade head           # Apply migrations (run after git pull)
pytest tests/ -v               # Run backend tests
pytest tests/ -v --cov=app     # With coverage
pytest tests/ -m unit -v       # Unit tests only
pytest tests/ -m "not slow" -v # Skip slow tests
pytest tests/test_file.py::test_function -v  # Single test function
# Markers: @unit, @api, @integration, @slow
```

---

## Architecture Overview

**Key Modules:**
- **Broker Abstraction** - Dual system: Market data brokers (SmartAPI, planned: Kite/Upstox) + Order execution brokers (Kite implemented, planned: Angel/Upstox). Factory pattern with unified data models (`UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`). See [Multi-Broker Architecture](../CLAUDE.md#core-purpose-multi-broker-architecture).
- **Authentication** - SmartAPI with auto-TOTP (default) or Zerodha OAuth. JWT stored in localStorage + Redis. Use `get_current_user` / `get_current_broker_connection` dependencies. SmartAPI credentials stored encrypted in `smartapi_credentials` table.
- **WebSocket Live Prices** - Dev: `ws://localhost:8001/ws/ticks?token=<jwt>` | Prod: `wss://algochanakya.com/ws/ticks?token=<jwt>`. New 5-component ticker architecture (ADR-003 v2): TickerAdapter (per-broker WS) + TickerPool (lifecycle/ref-counting) + TickerRouter (user fan-out) + HealthMonitor + FailoverController. Legacy singletons (`SmartAPITickerService`, `KiteTickerService`) being replaced. Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265. See [WebSocket Architecture](../docs/architecture/websocket.md)
- **Option Chain** - IV via Newton-Raphson, Greeks via Black-Scholes. Max Pain, PCR calculated.
- **Strategy Builder** - P/L modes: "At Expiry" (intrinsic) and "Current" (Black-Scholes via scipy)
- **AutoPilot** - Automated execution with conditions, adjustments, kill switch. 16 database tables. See [docs/autopilot/](../docs/autopilot/)
- **AI Module** - Market regime (6 types), risk states (GREEN/YELLOW/RED), trust ladder (Sandbox->Supervised->Autonomous). Paper trading graduation: 15 days + 25 trades + 55% win rate. Key tables: `ai_user_config`, `ai_decisions_log`, `ai_model_registry`, `ai_learning_reports`. See [docs/ai/](../docs/ai/)
- **SmartAPI Integration** (Default Market Data) - AngelOne SmartAPI is the **default market data source** for live WebSocket prices and historical OHLC. Kite remains for order execution. Uses auto-TOTP (no manual TOTP entry). Credentials stored encrypted in `smartapi_credentials` table. Key files: `app/services/legacy/smartapi_auth.py` (auth with auto-TOTP), `legacy/smartapi_ticker.py` (WebSocket V2), `legacy/smartapi_historical.py` (OHLC), `app/api/routes/smartapi.py` (endpoints), `frontend/src/components/settings/SmartAPISettings.vue` (UI). API: `POST /api/smartapi/authenticate`, `GET/POST /api/smartapi/credentials`, `POST /api/smartapi/test-connection`.

**Database:** Async PostgreSQL (asyncpg) + Redis for sessions. Run `alembic upgrade head` after git pull.

### Key Services

**Broker Adapters (Order Execution):**
- `app/services/brokers/base.py` - `BrokerAdapter` interface, unified data models
- `app/services/brokers/factory.py` - `get_broker_adapter()` factory
- `app/services/brokers/kite_adapter.py` - Zerodha order execution adapter

**Market Data Abstraction (Phase 2 Complete):**
- `app/services/brokers/market_data/market_data_base.py` - `MarketDataBrokerAdapter` interface
- `app/services/brokers/market_data/ticker_base.py` - `TickerServiceBase` interface
- `app/services/brokers/market_data/factory.py` - `get_market_data_adapter()` factory
- `app/services/brokers/market_data/smartapi_adapter.py` - SmartAPI implementation
- `app/services/brokers/market_data/token_manager.py` - Cross-broker token/symbol mapping
- `app/services/brokers/market_data/rate_limiter.py` - Per-broker rate limiting
- `app/services/brokers/market_data/symbol_converter.py` - Canonical <-> broker symbols
- `app/services/brokers/market_data/exceptions.py` - Market data errors

**Ticker System (Phase 4 — 5-Component Design, to be implemented):**
- `app/services/brokers/market_data/ticker/adapter_base.py` - `TickerAdapter` ABC
- `app/services/brokers/market_data/ticker/pool.py` - `TickerPool` (adapter lifecycle, ref-counted subscriptions, **integrated credentials**)
- `app/services/brokers/market_data/ticker/router.py` - `TickerRouter` (user fan-out, dispatch)
- `app/services/brokers/market_data/ticker/health.py` - `HealthMonitor` (5s heartbeat, scoring)
- `app/services/brokers/market_data/ticker/failover.py` - `FailoverController` (make-before-break)
- `app/services/brokers/market_data/ticker/adapters/smartapi.py` - SmartAPI ticker adapter
- `app/services/brokers/market_data/ticker/adapters/kite.py` - Kite ticker adapter
- `app/services/brokers/market_data/ticker/adapters/` - Upstox, Dhan, Fyers, Paytm stubs
- **Note:** Uses `Decimal` (not `float`) for NormalizedTick prices to eliminate precision errors
- **Docs:** [TICKER-DESIGN-SPEC.md](../docs/decisions/TICKER-DESIGN-SPEC.md) | [Implementation Guide](../docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) (3,868 lines) | [API Reference](../docs/api/multi-broker-ticker-api.md)

**Legacy Market Data Services (to be replaced by ticker adapters):**
- `app/services/legacy/smartapi_ticker.py` - SmartAPI WebSocket V2 (default, deprecated by Phase 4)
- `app/services/legacy/kite_ticker.py` - Kite WebSocket (singleton, deprecated by Phase 4)
- `app/services/legacy/smartapi_historical.py` - Historical OHLCV data

**AutoPilot Services (26 files):**
- `app/services/autopilot/condition_engine.py` - Entry/adjustment condition evaluation
- `app/services/autopilot/order_executor.py` - Order placement and execution
- `app/services/autopilot/strategy_monitor.py` - Real-time strategy monitoring
- `app/services/autopilot/kill_switch.py` - Emergency position exit
- `app/services/autopilot/adjustment_engine.py` - Strategy adjustment logic
- `app/services/autopilot/suggestion_engine.py` - Adjustment suggestions
- (20 more services in `autopilot/` directory)

**Options Calculation Services (8 files):**
- `app/services/options/pnl_calculator.py` - Black-Scholes P/L calculations
- `app/services/options/greeks_calculator.py` - Delta, gamma, theta, vega calculations
- `app/services/options/payoff_calculator.py` - Strategy payoff diagrams
- `app/services/options/iv_metrics_service.py` - Implied volatility metrics
- (4 more services in `options/` directory)

**Key AI Services:**
- `app/services/ai/market_regime.py` - 6 market regime types (TRENDING_BULLISH, TRENDING_BEARISH, RANGEBOUND, VOLATILE, PRE_EVENT, EVENT_DAY)
- `app/services/ai/risk_state_engine.py` - GREEN/YELLOW/RED risk states
- `app/services/ai/strategy_recommender.py` - Strategy recommendations with regime-strategy scoring
- `app/services/ai/deployment_executor.py` - AI-driven trade execution
- `app/services/ai/kelly_calculator.py` - Kelly Criterion position sizing
- `app/services/ai/ml/` - XGBoost/LightGBM models, feature extraction, training pipeline

**OFO (Options Flow Order):** A position sizing and order flow analysis module. Backend: `app/api/routes/ofo.py`, `app/schemas/ofo.py`, `app/services/ofo_calculator.py`. Frontend: `src/components/ofo/`, `src/stores/ofo.js`, `src/views/OFOView.vue`.

**Key AI Endpoints:**
- `GET /api/v1/ai/regime/current` - Current market regime
- `GET /api/v1/ai/config/` - AI user configuration
- `GET /api/v1/ai/recommendations/` - Strategy recommendations
- `GET /api/v1/ai/risk-state/` - Current risk state (GREEN/YELLOW/RED)
- `POST /api/v1/ai/deploy/` - Deploy AI-recommended strategy
- `GET /api/v1/ai/analytics/performance` - Performance metrics
- `POST /api/v1/ai/backtest/run` - Run historical backtest

---

## Broker Abstraction Code Examples

**NEVER directly use broker-specific APIs (KiteConnect, SmartAPI client).** Always use broker adapters and factories:

```python
# Backend - Order Execution
from app.services.brokers.factory import get_broker_adapter
adapter = get_broker_adapter(user.order_broker_type, credentials)
order = await adapter.place_order(...)  # Returns UnifiedOrder

# Backend - Market Data (Phase 2 Complete - Use This!)
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter(user.market_data_broker_type, credentials)
quote = await data_adapter.get_live_quote(symbol)  # Returns UnifiedQuote
historical = await data_adapter.get_historical_data(symbol, from_date, to_date, interval)

# Backend - Token/Symbol Conversion (NEW)
from app.services.brokers.market_data.token_manager import token_manager
broker_token = await token_manager.get_broker_token("NIFTY 26 DEC 24000 CE", "smartapi")
canonical_symbol = await token_manager.get_canonical_symbol(256265, "smartapi")
```

**Unified Data Models** - All broker adapters convert to/from these broker-agnostic models:
- `UnifiedOrder` - Normalized order structure (order_id, tradingsymbol, side, status, etc.)
- `UnifiedPosition` - Normalized position (tradingsymbol, quantity, pnl, average_price, etc.)
- `UnifiedQuote` - Normalized quote (last_price, ohlc, volume, bid/ask, etc.)

See `app/services/brokers/base.py` and `app/services/brokers/market_data/market_data_base.py` for complete definitions.

**Important:** All symbol references must use **canonical format** (Kite format) internally. Use `SymbolConverter` to translate broker-specific symbols.

### Current Implementation Status

**Phase 1 & 2 Complete (Jan 2026):**
- **Order Execution Abstraction:** `BrokerAdapter` interface, `KiteAdapter`, unified data models, factory pattern
- **Market Data Abstraction:** `MarketDataBrokerAdapter` interface, `SmartAPIMarketDataAdapter`, `TickerServiceBase`, `TokenManager`, `RateLimiter`, `SymbolConverter`, `broker_instrument_tokens` table
- **Legacy SmartAPI Services** (to be wrapped by adapter): `smartapi_auth.py`, `smartapi_ticker.py`, `smartapi_market_data.py`, `smartapi_historical.py`, `smartapi_instruments.py`

**Phase 3 Complete (Jan 2026):**
- All routes refactored to use broker factories instead of hardcoded services
- `KiteMarketDataAdapter` implemented for Kite market data
- Routes updated: `optionchain.py`, `ofo.py`, `orders.py`, `strategy_wizard.py`, `websocket.py`

**Phase 4: Ticker/WebSocket Refactoring — PLANNED (Documentation Complete Feb 16, 2026):**
- New 5-component architecture replacing legacy singletons
- Core: `ticker/adapter_base.py`, `ticker/pool.py` (integrated credentials), `ticker/router.py`, `ticker/health.py`, `ticker/failover.py`
- Adapters: `ticker/adapters/smartapi.py`, `ticker/adapters/kite.py` + 4 stubs (Upstox, Dhan, Fyers, Paytm)
- NormalizedTick uses `Decimal` (not `float`) for price precision
- Refactor `websocket.py` from 494 lines → 90 lines (82% reduction, broker-agnostic)
- **Docs:** [TICKER-DESIGN-SPEC.md](../docs/decisions/TICKER-DESIGN-SPEC.md) | [Implementation Guide](../docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) (3,868 lines) | [API Reference](../docs/api/multi-broker-ticker-api.md) | [Documentation Index](../docs/decisions/ticker-documentation-index.md)

**Phase 5-6 To Be Implemented:**
- Phase 5: Additional broker adapters (Upstox, Dhan, Fyers, Paytm) for market data + ticker
- Phase 6: `AngelAdapter` for order execution, order stubs for remaining brokers, frontend broker selection UI

### Adding a New Broker (Future State)

Once abstraction is complete, adding a broker will require:
1. Create adapter class implementing `BrokerAdapter` or `MarketDataBrokerAdapter`
2. Register in factory (`_BROKER_ADAPTERS` dict)
3. Add credentials table (if needed) + migration
4. Update frontend settings dropdown

**Zero changes** to routes, services, or business logic required.

**Skill guidance:** Use the relevant broker expert skill (`/smartapi-expert`, `/kite-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert`) for API-specific guidance. See [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) for cross-broker differences.

**Documentation:**
- [Broker Abstraction Architecture](../docs/architecture/broker-abstraction.md) - Complete technical design (updated Feb 16, 2026)
- [ADR-002: Multi-Broker Abstraction](../docs/decisions/002-broker-abstraction.md) - Decision rationale and alternatives (updated Feb 16, 2026)
- [TICKER-DESIGN-SPEC.md](../docs/decisions/TICKER-DESIGN-SPEC.md) - **Current** ticker architecture (5-component design, Feb 14, 2026)
  - [Implementation Guide](../docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) - 3,868 lines with complete code (Feb 16, 2026)
  - [API Reference](../docs/api/multi-broker-ticker-api.md) - v2.1.0
  - [Documentation Index](../docs/decisions/ticker-documentation-index.md) - Navigation guide
- ~~[ADR-003 v2](../docs/decisions/003-multi-broker-ticker-architecture.md)~~ - Superseded (historical reference)

---

## Trading Constants (Backend)

**NEVER hardcode lot sizes, strike steps, or index tokens.** Always use centralized constants:

```python
from app.constants.trading import get_lot_size, get_strike_step
lot_size = get_lot_size("NIFTY")  # 25
```

---

## Database Patterns

### Adding New Database Models

1. Create in `app/models/<name>.py` (inherit from `Base`)
2. Import in `app/models/__init__.py`
3. Import in `alembic/env.py` (required for autogenerate)
4. Run: `alembic revision --autogenerate -m "description" && alembic upgrade head`

### Broker Abstraction Database Tables

**`broker_instrument_tokens`** (Added Jan 2026) - Cross-broker token/symbol mapping:
- Stores canonical symbol (Kite format) mapped to broker-specific symbols and tokens
- Enables token/symbol conversion across all supported brokers
- Indexed on `canonical_symbol`, `broker`, `broker_symbol`, `broker_token`, `expiry`
- Unique constraint: `(canonical_symbol, broker)`
- Used by `TokenManager` for efficient lookups

**`user_preferences`** - User broker selection (columns added):
- `market_data_source` - Which broker for market data (smartapi, kite, upstox, dhan, fyers, paytm)
- Constraint updated to support 6 brokers (migration: `bc0dd372730d`)

**`smartapi_credentials`** - Encrypted SmartAPI credentials for auto-TOTP authentication

### Adding New API Routes

1. Create `app/api/routes/<name>.py` with `router = APIRouter()`
2. Include in `app/main.py`
3. Use `Depends(get_current_user)` for authentication

### Encryption for Credentials

Use `app/utils/encryption.py` for encrypting sensitive stored credentials:

```python
from app.utils.encryption import encrypt, decrypt
encrypted = encrypt("sensitive_data")
decrypted = decrypt(encrypted)
```

### Rate Limiting for Broker APIs

Market data adapters automatically handle broker-specific rate limits via `RateLimiter`:

```python
from app.services.brokers.market_data.rate_limiter import RateLimiter

# Automatically enforced by adapters - no manual intervention needed
# SmartAPI: 1 request per second
# Kite: 3 requests per second
# Upstox/Dhan/Fyers: 10 requests per second

# Rate limiter is singleton per broker, handles concurrent requests automatically
```

**Important:** Don't bypass the adapter to avoid rate limiting - it will cause API bans!

### Authentication Error Handling (Backend)

All authenticated endpoints use `get_current_user` / `get_current_broker_connection` dependencies that return 401 on:
- Invalid/expired JWT token
- Invalid/expired Kite access token (broker `access_token` fails)

**Key Files:**
- `app/utils/dependencies.py` - Auth dependencies (`get_current_user`, `get_current_broker_connection`)

---

## Folder Structure Rules (ENFORCED by hooks)

See [.claude/rules.md](../.claude/rules.md) for all enforced folder structure rules (backend services, test organization, enforcement details).

---

## Environment Variables

**Setup:** Copy `.env.example` to `.env` and update with actual values.

**Backend (`backend/.env`):** `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_HOURS`, `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_REDIRECT_URL`, `ANTHROPIC_API_KEY` (for AI), `ANGEL_API_KEY` (for SmartAPI market data), `FRONTEND_URL`

---

## Backend-Specific Pitfalls

- **Direct broker API usage** - NEVER import `KiteConnect` or `SmartAPI` directly. Use broker adapters from `app.services.brokers/` and market data adapters from `app.services.brokers.market_data/`
- **Hardcoded broker assumptions** - Don't assume Kite or SmartAPI; code should work with any broker via abstraction
- **Bypassing market data abstraction** - Use `get_market_data_adapter()` instead of directly calling `SmartAPIMarketData`, `SmartAPIHistorical`, etc.
- **Symbol format confusion** - Always use canonical format (Kite format) internally; use `SymbolConverter` for broker-specific symbols
- **Token lookup without TokenManager** - Use `token_manager.get_broker_token()` instead of manual lookups; it handles caching and cross-broker mapping
- **Broker name mismatch** - BrokerConnection stores 'zerodha'/'angelone' but BrokerType uses 'kite'/'angel'. Use the broker name mapping utility when converting between DB values and enum values.
- **Forgot to import model in `alembic/env.py`** - Autogenerate won't detect it
- **Sync database operations** - All SQLAlchemy must use `async/await`
- **Hardcoded trading constants** - Use `app.constants.trading` instead
- **Mixing broker concerns** - Keep market data separate from order execution (dual system)

---

## Learning Engine (Autonomous Fix Loop)

The learning engine at `.claude/learning/knowledge.db` records every error and fix attempt, ranks strategies by success rate with time decay, and auto-synthesizes rules when patterns reach >=70% confidence with >=5 evidence instances.

**Three Core Loops:**
- **Pre-check:** Before fixing, query knowledge.db for ranked strategies
- **Post-record:** After every fix attempt, record outcome and update scores
- **Feedback:** On session start, check git for reverts that invalidate past fixes

**Stuck Conditions (Stop and ask user):**
- Same error 3x with different strategies failing
- All strategies exhausted (scores < 0.1)
- 20 total attempts in session
- Fix requires modifying files outside feature scope
- Error type completely unknown

**Commands:**
```bash
/learning-engine status          # Show knowledge DB stats
/learning-engine query {type}    # Show strategies for error type
/learning-engine risk-report     # Top 10 error-prone files
/learning-engine synthesize      # Force rule synthesis check
```

**Integration:** Automatically integrated with `auto-verify` (Step 2c, Step 8) and `test-fixer` (Step 0, post-fix recording). Runs on session start (feedback loop) and end (synthesis check).

**Storage:** SQLite database at `.claude/learning/knowledge.db` with 6 tables: error_patterns, fix_strategies, fix_attempts, file_risk_scores, synthesized_rules, session_metrics.

---

## Production Debugging

**CRITICAL:** See [root CLAUDE.md](../CLAUDE.md#0-production-vs-development---never-touch-production) for production safety rules.

**PM2 Logs (read-only):** `pm2 logs algochanakya-backend` (NEVER run `pm2 restart`)

**Common Production Issues:**
- **API calls fail:** Check `frontend/.env.production` has `VITE_API_BASE_URL=https://algochanakya.com`
- **OAuth fails:** Verify Kite redirect URL = `https://algochanakya.com/api/auth/zerodha/callback`
- **"Incorrect api_key or access_token":** SmartAPI token expired (8h) or Kite access token expired (24h). SmartAPI auto-refreshes via stored credentials; Kite requires re-login via OAuth.
- **WebSocket won't connect:** Check `VITE_WS_URL` in `.env.production`, ensure wss:// for HTTPS
- **Backend won't start - Database connection refused:** PostgreSQL server blocking your IP. Whitelist IP in `pg_hba.conf`.
- **AngelOne login shows "Failed to login":** Either backend not running on correct port (check 8001 not 8005/8000), or request timeout (login takes 20-25s, needs 35s timeout)

**Full deployment docs:** `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md` on VPS

---

## Debug Commands

```bash
curl http://localhost:8001/api/health          # Check dev backend health (8001)
```

```javascript
// Browser console - test WebSocket (dev on port 8001)
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))

// Production (use wss:// for HTTPS, port 8000)
const ws = new WebSocket('wss://algochanakya.com/ws/ticks?token=YOUR_JWT')
```
