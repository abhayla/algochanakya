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

- [ ] Phase 1: Core Strategy Builder
- [ ] Phase 2: Real-time Monitoring
- [ ] Phase 3: Adjustments & Semi-Auto
- [ ] Phase 4: Templates & Analytics
