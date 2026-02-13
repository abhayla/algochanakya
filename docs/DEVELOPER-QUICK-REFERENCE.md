# Developer Quick Reference

**Last Updated:** 2026-02-13

This guide provides quick access to all architecture documentation organized by development task.

---

## Quick Commands

**Most Common Commands** - Quick reference for daily development:

| Task | Command | Location |
|------|---------|----------|
| **Start dev backend** | `venv\Scripts\activate && python run.py` | `backend/` |
| **Start frontend** | `npm run dev` | `frontend/` |
| **Run all E2E tests** | `npm test` | root |
| **Run single E2E test** | `npx playwright test path/to/spec.js` | root |
| **Database migration** | `alembic revision --autogenerate -m "msg" && alembic upgrade head` | `backend/` |
| **Apply migrations only** | `alembic upgrade head` | `backend/` |
| **Check git status** | `git status && git log --oneline -5` | root |
| **Auto-verify after changes** | `Skill(skill="auto-verify")` | Claude Code |
| **Backend tests** | `pytest tests/ -v` | `backend/` |
| **Frontend unit tests** | `npm run test` | `frontend/` |
| **Debug E2E test** | `npx playwright test path/to/spec --debug` | root |
| **Check backend health** | `curl http://localhost:8001/api/health` | terminal |

**Port Reference:**

| Service | Development | Production (DO NOT TOUCH) |
|---------|-------------|---------------------------|
| Backend API | `localhost:8001` | `localhost:8000` |
| Frontend | `localhost:5173` | `localhost:3004` |
| WebSocket | `ws://localhost:8001/ws/ticks` | `wss://algochanakya.com/ws/ticks` |
| Database | `localhost:5432` | `localhost:5432` |
| Redis | `localhost:6379` | `localhost:6379` |

---

## 🚀 Getting Started

| What You Need | Documentation |
|---------------|---------------|
| **Project Overview** | [Main README](../README.md) |
| **Tech Stack** | [ADR-001: Tech Stack](decisions/001-tech-stack.md) |
| **System Architecture** | [Architecture Overview](architecture/overview.md) |
| **Setup & Installation** | [Backend README](../backend/README.md) |

---

## 📐 Core Architecture

### Multi-Broker System (Primary Architecture)

| Topic | Documentation |
|-------|---------------|
| **Overview & Rationale** | [ADR-002: Broker Abstraction](decisions/002-broker-abstraction.md) |
| **Technical Design** | [Broker Abstraction Architecture](architecture/broker-abstraction.md) |
| **Implementation Status** | [Broker Abstraction - Current Status](architecture/broker-abstraction.md#current-implementation-status) |
| **Code Reference** | `backend/app/services/brokers/` |

**Quick Facts:**
- Two independent systems: Market Data Brokers + Order Execution Brokers
- Unified data models: `UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`
- Factory pattern for broker instantiation
- ✅ All routes refactored to use broker factories (Phase 3 complete)

**Broker Expert Skills:** `/smartapi-expert`, `/kite-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert` — API-specific guidance for each broker. See [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) for cross-broker differences.

### Authentication & Security

| Topic | Documentation |
|-------|---------------|
| **OAuth Flow** | [Authentication Architecture](architecture/authentication.md) |
| **JWT Management** | [Authentication Architecture](architecture/authentication.md#jwt-token-structure) |
| **Credential Encryption** | [CLAUDE.md - Encryption](../CLAUDE.md#encryption-for-credentials) |
| **SmartAPI Auth** | [SmartAPI Integration](../CLAUDE.md#architecture-overview) (auto-TOTP) |

**Key Files:**
- `backend/app/utils/dependencies.py` - `get_current_user`, `get_current_broker_connection`
- `backend/app/services/legacy/smartapi_auth.py` - Auto-TOTP authentication
- `backend/app/utils/encryption.py` - Credential encryption

### WebSocket Live Prices

| Topic | Documentation |
|-------|---------------|
| **WebSocket Design** | [WebSocket Architecture](architecture/websocket.md) |
| **Connection Flow** | [WebSocket - Connection Flow](architecture/websocket.md#connection-flow) |
| **Message Types** | [WebSocket - Messages](architecture/websocket.md#message-types) |

**Key Files:**
- `backend/app/services/legacy/kite_ticker.py` - Kite WebSocket (singleton, legacy)
- `backend/app/services/legacy/smartapi_ticker.py` - SmartAPI WebSocket V2 (singleton, legacy)
- `backend/app/services/brokers/market_data/ticker_base.py` - `TickerServiceBase` interface
- `backend/app/api/routes/websocket.py` - WebSocket endpoint

**Ticker Architecture:** [ADR-003: Multi-Broker Ticker](decisions/003-multi-broker-ticker-architecture.md) | [Implementation Guide](architecture/multi-broker-ticker-implementation.md) | [API Reference](api/multi-broker-ticker-api.md)

**Quick Reference:**
- Dev: `ws://localhost:8001/ws/ticks?token=<jwt>`
- Prod: `wss://algochanakya.com/ws/ticks?token=<jwt>`
- Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265

### Database Schema

| Topic | Documentation |
|-------|---------------|
| **Schema Overview** | [Database Architecture](architecture/database.md) |
| **Models Reference** | [Database - Models](architecture/database.md#model-definitions) |
| **Migrations** | [Database - Alembic](architecture/database.md#alembic-migrations) |
| **Adding Models** | [CLAUDE.md - Adding Models](../CLAUDE.md#adding-new-database-models) |

**Quick Commands:**
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🎯 Feature Development

### AutoPilot (Auto-Execution System)

| Topic | Documentation |
|-------|---------------|
| **Feature Overview** | [AutoPilot README](autopilot/README.md) |
| **UI/UX Design** | [AutoPilot UI/UX](autopilot/ui-ux-design.md) |
| **Components** | [AutoPilot Components](autopilot/component-design.md) |
| **Database Schema** | [AutoPilot Database](autopilot/database-schema.md) |
| **API Contracts** | [AutoPilot API](autopilot/api-contracts.md) |

**Implementation Status:** ✅ All 5 phases complete
- 16 database tables
- 47+ frontend components
- 80+ backend services
- 37+ E2E test specs

**Key Services:**
- `backend/app/services/autopilot/condition_engine.py` - Condition evaluation
- `backend/app/services/autopilot/adjustment_engine.py` - 13+ triggers, 8 actions
- `backend/app/services/autopilot/kill_switch.py` - Emergency stop

### AI Module

| Topic | Documentation |
|-------|---------------|
| **Feature Overview** | [AI README](ai/README.md) |
| **Requirements** | [AI Requirements](features/ai/REQUIREMENTS.md) |
| **Architecture** | [AI README - Architecture](ai/README.md#architecture) |
| **API Endpoints** | [AI README - API](ai/README.md#api-endpoints) |

**Key Concepts:**
- 6 market regime types (TRENDING_BULLISH, RANGEBOUND, VOLATILE, etc.)
- Risk states: GREEN/YELLOW/RED
- Trust ladder: Sandbox → Supervised → Autonomous
- Paper trading graduation: 15 days + 25 trades + 55% win rate

**Key Services:**
- `backend/app/services/ai/market_regime.py`
- `backend/app/services/ai/risk_state_engine.py`
- `backend/app/services/ai/strategy_recommender.py`

### Option Chain

| Topic | Documentation |
|-------|---------------|
| **Greeks Calculation** | [CLAUDE.md - Option Chain](../CLAUDE.md#architecture-overview) |
| **API Reference** | [API Docs](api/README.md#option-chain) |

**Calculations:**
- IV via Newton-Raphson method
- Greeks via Black-Scholes
- Max Pain, PCR calculated

### Strategy Builder

| Topic | Documentation |
|-------|---------------|
| **P/L Calculation** | [CLAUDE.md - Strategy Builder](../CLAUDE.md#architecture-overview) |
| **API Reference** | [API Docs](api/README.md#strategies) |

**P/L Modes:**
- "At Expiry" - Intrinsic value
- "Current" - Black-Scholes via scipy

---

## 🧪 Testing

### E2E Testing (Playwright)

| Topic | Documentation |
|-------|---------------|
| **Test Architecture** | [Testing README](testing/README.md) |
| **Test Rules** | [CLAUDE.md - E2E Rules](../CLAUDE.md#e2e-test-rules-critical) |
| **Writing Tests** | [Testing - Writing Tests](testing/README.md#writing-new-tests) |
| **Page Objects** | [Testing - Page Objects](testing/README.md#page-object-model) |

**Critical Rules:**
- ✅ Use `data-testid` ONLY (never CSS/text selectors)
- ✅ Import from `auth.fixture.js` (NOT `@playwright/test`)
- ✅ Use `authenticatedPage` fixture
- ✅ Convention: `[screen]-[component]-[element]`

**Quick Commands:**
```bash
# Run all tests
npm test

# Run by screen
npm run test:specs:positions

# Run single test
npx playwright test tests/e2e/specs/positions/positions.happy.spec.js

# Debug
npm run test:debug
```

### Backend Testing (pytest)

**Quick Commands:**
```bash
cd backend
pytest tests/ -v                    # All tests
pytest tests/ -v --cov=app          # With coverage
pytest tests/ -m unit -v            # Unit tests only
pytest tests/ -m "not slow" -v      # Skip slow tests
```

---

## 🔧 Common Development Tasks

### Adding a New API Route

1. Create `backend/app/api/routes/<name>.py` with `router = APIRouter()`
2. Include in `backend/app/main.py`
3. Use `Depends(get_current_user)` for authentication
4. **Use broker adapters** (not direct `KiteConnect` or `SmartAPI`)

**Reference:** [CLAUDE.md - Adding Routes](../CLAUDE.md#adding-new-api-routes)

### Adding a Database Model

1. Create in `backend/app/models/<name>.py` (inherit from `Base`)
2. Import in `backend/app/models/__init__.py`
3. Import in `backend/alembic/env.py` ⚠️ **CRITICAL**
4. Run migration commands

**Reference:** [CLAUDE.md - Adding Models](../CLAUDE.md#adding-new-database-models)

### Using Trading Constants

**Never hardcode:** lot sizes, strike steps, index tokens

```python
# Backend
from app.constants.trading import get_lot_size, get_strike_step
lot_size = get_lot_size("NIFTY")  # 25

# Frontend
import { getLotSize, getStrikeStep } from '@/constants/trading'
```

**Reference:** [CLAUDE.md - Trading Constants](../CLAUDE.md#trading-constants-critical)

### Using Broker Adapters

**Never use:** Direct `KiteConnect`, `SmartAPI`, or `KiteOrderService`

```python
# ✅ Correct
from app.services.brokers.factory import get_broker_adapter
adapter = get_broker_adapter(user.order_broker_type, credentials)
order = await adapter.place_order(...)  # Returns UnifiedOrder

# ❌ Wrong
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=...)
```

**Market data adapter** (Phase 2 complete — use this for quotes and historical data):

```python
# ✅ Correct - Market Data
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter(user.market_data_broker_type, credentials, db)
quote = await data_adapter.get_live_quote(symbol)  # Returns UnifiedQuote

# ❌ Wrong
from app.services.legacy.smartapi_market_data import SmartAPIMarketData
```

**Skill guidance:** Use `/smartapi-expert` or `/kite-expert` for broker-specific API details when debugging adapter issues.

**Reference:** [CLAUDE.md - Broker Abstraction](../CLAUDE.md#broker-abstraction-critical)

---

## 🐛 Debugging & Troubleshooting

### Backend Debugging

```bash
# Check dev backend health (port 8001)
curl http://localhost:8001/api/health

# Check logs
# (Check console output)
```

### Frontend Debugging

```javascript
// Test WebSocket (dev on port 8001)
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))
```

### Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| Alembic not detecting model | Import in `alembic/env.py` | [CLAUDE.md - Pitfalls](../CLAUDE.md#common-pitfalls) |
| Direct broker API used | Use broker adapters from `app.services.brokers/` | [CLAUDE.md - Pitfalls](../CLAUDE.md#common-pitfalls) |
| Missing data-testid | Add to element with `[screen]-[component]-[element]` format | [CLAUDE.md - Pitfalls](../CLAUDE.md#common-pitfalls) |
| WebSocket not cleaned up | Close subscriptions in `onUnmounted()` | [CLAUDE.md - Pitfalls](../CLAUDE.md#common-pitfalls) |
| Broker API errors (auth, rate limit, symbol) | Consult relevant broker expert skill (`/smartapi-expert`, `/kite-expert`, etc.) | [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) |

---

## 📦 Production Deployment

| Topic | Documentation |
|-------|---------------|
| **Production Info** | [CLAUDE.md - Production](../CLAUDE.md#production-debugging) |
| **Environment Vars** | [CLAUDE.md - Env Vars](../CLAUDE.md#environment-variables) |
| **Deployment Checklist** | VPS docs: `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md` |

**⚠️ CRITICAL:** Production runs on SAME machine
- Dev: `D:\Abhay\VibeCoding\algochanakya` (port 8001)
- Prod: `C:\Apps\algochanakya` (port 8000) - **NEVER touch**

---

## 📚 All Documentation Index

### Architecture Docs
- [Overview](architecture/overview.md)
- [Authentication](architecture/authentication.md)
- [Broker Abstraction](architecture/broker-abstraction.md)
- [Database](architecture/database.md)
- [WebSocket](architecture/websocket.md)

### Decision Records (ADRs)
- [ADR-001: Tech Stack](decisions/001-tech-stack.md)
- [ADR-002: Multi-Broker Abstraction](decisions/002-broker-abstraction.md)
- [ADR-003: Multi-Broker Ticker Architecture](decisions/003-multi-broker-ticker-architecture.md)
  - [Ticker Implementation Guide](architecture/multi-broker-ticker-implementation.md)
  - [Ticker API Reference](api/multi-broker-ticker-api.md)
  - [Architecture Comparison](architecture/websocket-ticker-architectures-comparison.md)
- [ADR Template](decisions/template.md)

### Feature Documentation
- [AutoPilot](autopilot/)
- [AI Module](ai/)
- [Testing](testing/)
- [API Reference](api/)
- [Feature Registry](feature-registry.yaml)

### Guides
- [Main README](../README.md)
- [CLAUDE.md](../CLAUDE.md) - Complete project guide for AI assistants
- [CHANGELOG](../CHANGELOG.md)

---

## 🔗 Quick Links by Role

### Backend Developer
1. [Architecture Overview](architecture/overview.md)
2. [Broker Abstraction](architecture/broker-abstraction.md) ⭐
3. [Database Schema](architecture/database.md)
4. [API Reference](api/README.md)
5. [CLAUDE.md - Important Patterns](../CLAUDE.md#important-patterns)
6. Broker Expert Skills: `/smartapi-expert`, `/kite-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert`

### Frontend Developer
1. [Architecture Overview](architecture/overview.md)
2. [WebSocket Architecture](architecture/websocket.md)
3. [AutoPilot Components](autopilot/component-design.md)
4. [Testing - Page Objects](testing/README.md)
5. [CLAUDE.md - Frontend Pitfalls](../CLAUDE.md#frontend)

### QA/Test Engineer
1. [Testing README](testing/README.md) ⭐
2. [E2E Test Rules](../CLAUDE.md#e2e-test-rules-critical)
3. [Test Commands](../CLAUDE.md#e2e-tests-from-project-root)
4. [AutoPilot Testing](autopilot/README.md)

### DevOps/Deployment
1. [Production Debugging](../CLAUDE.md#production-debugging)
2. [Environment Variables](../CLAUDE.md#environment-variables)
3. [CI/CD](../CLAUDE.md#cicd)
4. VPS Setup: `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md`

---

**Need something not here?** Check [docs/README.md](README.md) or search the codebase.
