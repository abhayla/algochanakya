# Backend Development Guide

> This file provides backend-specific guidance for Claude Code. It loads automatically when working with `backend/` files.
> For cross-cutting rules and mandatory behaviors, see the [root CLAUDE.md](../CLAUDE.md).

---

## Development Commands

From `backend/`:

```bash
source venv/Scripts/activate   # Activate venv (bash on Windows)
python run.py                  # Start server (auto-refreshes instruments via InstrumentMasterService)
alembic upgrade head           # Apply migrations (run after git pull)
pytest tests/ -v               # Run backend tests
pytest tests/ -v --cov=app     # With coverage
pytest tests/ -m unit -v       # Unit tests only
pytest tests/ -m "not slow" -v # Skip slow tests
pytest tests/test_file.py::test_function -v  # Single test function
pytest tests/live/ -m live -v                # Run live broker tests (needs real credentials in .env)
pytest tests/live/ -m "live and not slow" -v # Live tests excluding slow ones (e.g. historical fetches)
# Markers: @unit, @api, @integration, @slow, @live
# @live — hits real broker APIs; skips cleanly when credentials are missing from .env
pytest -p no:cov tests/test_file.py -v     # Skip coverage (pytest.ini enables it by default)

# Linting & formatting (ruff)
ruff check app/                            # Lint
ruff check app/ --fix                      # Lint + auto-fix
ruff format app/                           # Format
```

---

## Architecture Overview

**Key Modules:**
- **Broker Abstraction** - Dual system: Market data brokers (all 6 implemented: SmartAPI, Kite, Dhan, Fyers, Paytm, Upstox) + Order execution brokers (all 6 implemented). Factory pattern with unified data models (`UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`). See [Multi-Broker Architecture](../CLAUDE.md#core-purpose-multi-broker-architecture).
- **Authentication** - 6 broker login flows (OAuth redirect or inline credentials). JWT stored in localStorage + Redis. Login credentials are NOT stored — used once for authentication. Use `get_current_user` / `get_current_broker_connection` dependencies. Platform-level SmartAPI credentials (for universal market data) stored in `.env` with auto-TOTP. User-level market data API credentials stored encrypted in the unified `broker_api_credentials` table (replaces per-broker `smartapi_credentials` table — configured via Settings page). Settings OAuth callbacks at `/api/settings/{broker}/connect-callback` store tokens into `broker_api_credentials` without touching login state.
- **WebSocket Live Prices** - Dev: `ws://localhost:8001/ws/ticks?token=<jwt>` | Prod: `wss://algochanakya.com/ws/ticks?token=<jwt>`. 5-component ticker architecture: TickerAdapter (per-broker WS) + TickerPool (lifecycle/ref-counting) + TickerRouter (user fan-out) + HealthMonitor + FailoverController. All 6 broker ticker adapters implemented. Legacy singletons (`SmartAPITickerService`, `KiteTickerService`) deprecated and moved to `services/deprecated/`. Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265. See [TICKER-DESIGN-SPEC.md](../docs/decisions/TICKER-DESIGN-SPEC.md)
  - **Token map loading (CRITICAL):** `_ensure_broker_credentials()` in `websocket.py` loads the canonical↔broker token mapping from `broker_instrument_tokens` table and passes it via `credentials["token_map"]`. Without this, `SmartAPITickerAdapter` cannot translate canonical tokens to SmartAPI tokens and subscribes to nothing (no ticks flow). Hardcoded index token fallback ensures NIFTY/BANKNIFTY/FINNIFTY/SENSEX work even if the DB table is empty.
  - **Credential loading order:** `_ensure_broker_credentials()` checks (1) user's `broker_api_credentials` row, (2) platform `.env` credentials, (3) `_try_fallback_brokers()` which iterates `ORG_ACTIVE_BROKERS` chain as last resort.
  - **TickerPool expiry checks:** `TickerPool.credentials_valid(broker_type)` and `TickerPool.clear_expired_credentials()` are called on every WebSocket connect to avoid using stale tokens.
- **Option Chain** - IV via Newton-Raphson, Greeks via Black-Scholes. Max Pain, PCR calculated.
- **Strategy Builder** - P/L modes: "At Expiry" (intrinsic) and "Current" (Black-Scholes via scipy)
- **AutoPilot** - Automated execution with conditions, adjustments, kill switch. 16 database tables. See [docs/autopilot/](../docs/autopilot/)
- **AI Module** - Market regime (6 types), risk states (GREEN/YELLOW/RED), trust ladder (Sandbox->Supervised->Autonomous). Paper trading graduation: 15 days + 25 trades + 55% win rate. Key tables: `ai_user_config`, `ai_decisions_log`, `ai_model_registry`, `ai_learning_reports`. See [docs/ai/](../docs/ai/)
- **SmartAPI Integration** (Default Market Data) - AngelOne SmartAPI is the **default market data source** for live WebSocket prices and historical OHLC. Kite remains for order execution. Uses auto-TOTP (no manual TOTP entry). Platform credentials stored in `.env`; user-level credentials stored encrypted in the unified `broker_api_credentials` table (the old per-broker `smartapi_credentials` table is now legacy). AngelOne login requires all three fields: `client_id`, `pin`, `totp_code` — Mode B (auto-TOTP from stored credentials) has been removed; only inline credentials (Mode A) are supported for user login. Key files: `app/services/legacy/smartapi_auth.py` (auth with auto-TOTP), `legacy/smartapi_ticker.py` (WebSocket V2), `legacy/smartapi_historical.py` (OHLC), `app/api/routes/smartapi.py` (endpoints), `frontend/src/components/settings/SmartAPISettings.vue` (UI). API: `POST /api/smartapi/authenticate`, `GET/POST /api/smartapi/credentials`, `POST /api/smartapi/test-connection`.

**Database:** Async PostgreSQL (asyncpg) + Redis for sessions. Run `alembic upgrade head` after git pull.

### Key Service Areas

| Area | Directory | Entry Points |
|------|-----------|-------------|
| Broker Order Execution | `services/brokers/` | `factory.py`, `base.py` |
| Market Data | `services/brokers/market_data/` | `factory.py`, `smartapi_adapter.py` |
| Ticker (5-component) | `services/brokers/market_data/ticker/` | `pool.py`, `router.py` |
| AutoPilot (26 files) | `services/autopilot/` | `condition_engine.py`, `order_executor.py`, `kill_switch.py` |
| Options Math | `services/options/` | `greeks_calculator.py`, `pnl_calculator.py` |
| AI/ML | `services/ai/` | `market_regime.py`, `risk_state_engine.py`, `ml/` |
| Instruments | `services/instrument_master.py` | `InstrumentMasterService` |
| Legacy (deprecated) | `services/deprecated/` | Superseded by ticker adapters |

---

## Broker Abstraction

Canonical code examples for broker adapter usage — see `.claude/rules/broker-adapter-only.md` for the full rule.

```python
# Order Execution
from app.services.brokers.factory import get_broker_adapter
adapter = get_broker_adapter(user.order_broker_type, credentials)
order = await adapter.place_order(...)  # Returns UnifiedOrder

# Market Data
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter(user.market_data_broker_type, credentials)
quote = await data_adapter.get_live_quote(symbol)  # Returns UnifiedQuote

# Token/Symbol Conversion
from app.services.brokers.market_data.token_manager import TokenManager
token_mgr = TokenManager(broker="smartapi", db=session)
await token_mgr.load_cache()
broker_token = await token_mgr.get_token("NIFTY25APR25000CE")
```

**Unified models:** `UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote` in `app/services/brokers/base.py`.

### Adding a New Broker

1. Implement `BrokerAdapter` or `MarketDataBrokerAdapter`
2. Register in factory (`_BROKER_ADAPTERS` dict)
3. Credentials go into `broker_api_credentials` table (use `broker` column to scope)
4. Update frontend settings dropdown — zero changes to routes or business logic

**Docs:** [Broker Architecture](../docs/architecture/broker-abstraction.md) | [Ticker Design](../docs/decisions/TICKER-DESIGN-SPEC.md) | [Ticker Implementation Guide](../docs/guides/TICKER-IMPLEMENTATION-GUIDE.md)

---

## Database Patterns

### Adding New Database Models

1. Create in `app/models/<name>.py` (inherit from `Base`)
2. Import in `app/models/__init__.py`
3. Import in `alembic/env.py` (required for autogenerate)
4. Run: `alembic revision --autogenerate -m "description" && alembic upgrade head`

### Key Tables (Broker Abstraction)

- **`broker_instrument_tokens`** — canonical symbol ↔ broker token mapping (used by `TokenManager`). Unique on `(canonical_symbol, broker)`.
- **`broker_api_credentials`** — unified encrypted per-user per-broker API credentials. One row per user per broker. Replaces legacy `smartapi_credentials`.
- **`user_preferences`** — includes `market_data_source` column for broker selection.

### Adding New API Routes

1. Create `app/api/routes/<name>.py` with `router = APIRouter()`
2. Include in `app/main.py`
3. Use `Depends(get_current_user)` for authentication

### Encryption

Use `app/utils/encryption.py` (`encrypt`/`decrypt`) for stored credentials.

### Auth Dependencies

`app/utils/dependencies.py`: `get_current_user`, `get_current_broker_connection` — returns 401 on invalid/expired JWT or broker access token.

---

## Environment Variables

**Setup:** Copy `.env.example` to `.env` and update with actual values. All `.env` credentials are platform-level — never store user-level credentials.

**Core:** `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_REDIRECT_URL`, `ANTHROPIC_API_KEY`, `FRONTEND_URL`

**AngelOne 3-key setup:** `ANGEL_API_KEY` (live data), `ANGEL_HIST_API_KEY` (history), `ANGEL_TRADE_API_KEY` (orders). Wrong key → `AG8001 Invalid Token`.

**Upstox:** `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `UPSTOX_REDIRECT_URL`, `UPSTOX_LOGIN_PHONE`, `UPSTOX_LOGIN_PIN`, `UPSTOX_USER_ID`, `UPSTOX_TOTP_SECRET`. Individual users auth via OAuth (stored in `broker_connections`).

---

## Backend-Specific Pitfalls

- **Forgot model import in `alembic/env.py`** — autogenerate silently produces empty migration
- **AngelOne `AG8001 Invalid Token`** — using wrong API key (3 keys: data, history, orders)
- **Sync DB operations** — all SQLAlchemy must use `async/await`
- All other pitfalls (broker abstraction, symbol format, name mapping, constants) are enforced by `.claude/rules/`

---

## Learning Engine

Error/fix knowledge base at `.claude/learning/knowledge.db`. Commands: `/learning-engine status`, `/learning-engine query {type}`, `/learning-engine risk-report`. Integrated with `auto-verify` and `test-fixer` skills.

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
