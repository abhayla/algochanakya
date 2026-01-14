# AutoPilot Documentation

Auto-execution and adjustment system for AlgoChanakya options trading platform.

## Overview

AutoPilot enables traders to automate their options trading strategies with:
- Conditional entry based on time, price, VIX, and custom indicators
- Real-time position monitoring with live P&L
- Automatic adjustments (hedge, roll, scale, exit)
- Semi-auto mode with manual confirmations
- Risk management with daily loss limits

## Documents

| Document | Description | Status |
|----------|-------------|--------|
| [UI/UX Design](ui-ux-design.md) | Screens, user flows, wireframes | Complete |
| [Component Design](component-design.md) | Vue.js 3 component specifications | Complete |
| [Database Schema](database-schema.md) | PostgreSQL tables, indexes, triggers | Complete |
| [API Contracts](api-contracts.md) | FastAPI endpoints, Pydantic models | Complete |

## Quick Start

### Database Setup

```bash
cd backend
alembic upgrade head
```

### API Testing

Import `tests\postman\autopilot-collection.json` into Postman.

### Development

```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

## Key URLs

| Page | Route |
|------|-------|
| Dashboard | `/autopilot` |
| Strategy Builder | `/autopilot/strategies/new` |
| Strategy Detail | `/autopilot/strategies/:id` |
| Settings | `/autopilot/settings` |
| Templates | `/autopilot/templates` |

## Architecture

```
Frontend (Vue.js 3)          Backend (FastAPI)           Database (PostgreSQL)
┌──────────────────┐         ┌──────────────────┐        ┌──────────────────┐
│ views/autopilot/ │ ──API──▶│ api/v1/autopilot/│ ──────▶│ autopilot_*      │
│ components/      │◀──WS────│ websocket/       │◀───────│ tables           │
│ composables/     │         │ services/        │        │                  │
└──────────────────┘         └──────────────────┘        └──────────────────┘
                                     │
                                     ▼
                             ┌──────────────────┐
                             │ Kite Connect API │
                             │ (Zerodha)        │
                             └──────────────────┘
```

## Feature Status

- [x] **Phase 1: Core Strategy Builder** - 16 DB tables, ConditionEngine with 10+ trigger types, StrategyBuilderView with wizard UI
- [x] **Phase 2: Real-time Monitoring** - Premium/Theta/Delta charts, Greeks calculator, DTEZoneIndicator, GammaRiskAlert
- [x] **Phase 3: Adjustments & Semi-Auto** - 13+ adjustment triggers, 8 action types (exit, hedge, roll, scale), Kill switch, Re-entry config
- [x] **Phase 4: Templates & Analytics** - 8 system templates, Analytics service, Trade journal, Backtesting, Performance metrics
- [x] **Phase 5: Advanced Features** - 9 sub-phases (5A-5I) including position leg tracking, AI suggestions, staged entry, what-if simulation

**Implementation Summary:**
- 47+ frontend components in `frontend/src/components/autopilot/`
- 80+ backend services across `backend/app/services/` and `backend/app/api/`
- 37+ E2E test spec files in `tests/e2e/specs/autopilot/`
- See phase completion docs in this directory for detailed implementation notes

## Related Documentation

- [UI/UX Design](ui-ux-design.md) - Detailed screen designs and user flows
- [Component Design](component-design.md) - Vue.js component specifications
- [Database Schema](database-schema.md) - All 16 AutoPilot tables
- [API Contracts](api-contracts.md) - FastAPI endpoint specifications
- [Broker Abstraction](../architecture/broker-abstraction.md) - Order execution via broker adapters
- [WebSocket Architecture](../architecture/websocket.md) - Live price monitoring

**See also:**
- [CLAUDE.md - AutoPilot](../../CLAUDE.md#architecture-overview) for key services reference
- [Testing Guide](../testing/README.md) - E2E test architecture
