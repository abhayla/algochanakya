# Developer Quick Reference

**Last Updated:** 2026-02-16

This guide provides quick access to all architecture documentation organized by development task.

---

## Quick Commands

See [CLAUDE.md Quick Reference Card](../CLAUDE.md#-quick-reference-card) for daily commands.

**Ports:** See [CLAUDE.md - Development Environment](../CLAUDE.md#development-environment)

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

**Broker Expert Skills:** `angelone-expert`, `zerodha-expert`, `upstox-expert`, `dhan-expert`, `fyers-expert`, `paytm-expert` — API-specific guidance for each broker. See [Comparison Matrix](../.claude/skills/broker-shared/comparison-matrix.md) for cross-broker differences.

### Authentication & Security

| Topic | Documentation |
|-------|---------------|
| **OAuth Flow** | [Authentication Architecture](architecture/authentication.md) |
| **JWT Management** | [Authentication Architecture](architecture/authentication.md#jwt-token-structure) |
| **Credential Encryption** | [backend/CLAUDE.md - Encryption](../backend/CLAUDE.md#encryption-for-credentials) |
| **SmartAPI Auth** | [backend/CLAUDE.md](../backend/CLAUDE.md#architecture-overview) (auto-TOTP) |

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

**Key Files (Current — 5-component architecture, Feb 2026):**
- `backend/app/services/brokers/market_data/ticker/` - All ticker components (adapter_base, pool, router, health, failover)
- `backend/app/services/brokers/market_data/ticker/adapters/` - Per-broker adapters (smartapi, kite, dhan, fyers, paytm, upstox)
- `backend/app/api/routes/websocket.py` - WebSocket endpoint (broker-agnostic)

**Legacy (deprecated — replaced by ticker adapters above):**
- ~~`backend/app/services/deprecated/kite_ticker.py`~~ - Kite WebSocket (singleton, superseded)
- ~~`backend/app/services/deprecated/smartapi_ticker.py`~~ - SmartAPI WebSocket V2 (singleton, superseded)

**Ticker Architecture:** [TICKER-DESIGN-SPEC.md](decisions/TICKER-DESIGN-SPEC.md) (current) | [Implementation Guide](guides/TICKER-IMPLEMENTATION-GUIDE.md) | [API Reference](api/multi-broker-ticker-api.md) | [Documentation Index](decisions/ticker-documentation-index.md)

### Database Schema

| Topic | Documentation |
|-------|---------------|
| **Schema Overview** | [Database Architecture](architecture/database.md) |
| **Models Reference** | [Database - Models](architecture/database.md#model-definitions) |
| **Migrations** | [Database - Alembic](architecture/database.md#alembic-migrations) |
| **Adding Models** | [backend/CLAUDE.md - Database Patterns](../backend/CLAUDE.md#database-patterns) |

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

### AI Module

| Topic | Documentation |
|-------|---------------|
| **Feature Overview** | [AI README](ai/README.md) |
| **Requirements** | [AI Requirements](features/ai/REQUIREMENTS.md) |
| **Architecture** | [AI README - Architecture](ai/README.md#architecture) |
| **API Endpoints** | [AI README - API](ai/README.md#api-endpoints) |

### Option Chain

| Topic | Documentation |
|-------|---------------|
| **Greeks Calculation** | [backend/CLAUDE.md](../backend/CLAUDE.md#architecture-overview) |
| **API Reference** | [API Docs](api/README.md#option-chain) |

### Strategy Builder

| Topic | Documentation |
|-------|---------------|
| **P/L Calculation** | [backend/CLAUDE.md](../backend/CLAUDE.md#architecture-overview) |
| **API Reference** | [API Docs](api/README.md#strategies) |

---

## 🧪 Testing

### E2E Testing
**Rules:** [E2E Test Rules](testing/e2e-test-rules.md) | **Architecture:** [Testing README](testing/README.md)

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

**Backend tasks:** [backend/CLAUDE.md](../backend/CLAUDE.md)
**Frontend tasks:** [frontend/CLAUDE.md](../frontend/CLAUDE.md)
**Broker adapters:** [Broker Abstraction](architecture/broker-abstraction.md)
**Broker-specific guidance:** Use broker expert skills (`/angelone-expert`, `/zerodha-expert`, etc.)

---

## 🐛 Debugging & Troubleshooting

**Full guide:** [Troubleshooting Guide](guides/troubleshooting.md)

---

## 📦 Production Deployment

| Topic | Documentation |
|-------|---------------|
| **Production Safety** | [CLAUDE.md - Production](../CLAUDE.md#0-production-vs-development---never-touch-production) |
| **Environment Vars** | [backend/CLAUDE.md - Env Vars](../backend/CLAUDE.md#environment-variables) |
| **Deployment Checklist** | VPS docs: `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md` |

**⚠️ CRITICAL:** Production runs on SAME machine
- Dev: `C:\Abhay\VideCoding\algochanakya` (port 8001)
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
- [TICKER-DESIGN-SPEC.md](decisions/TICKER-DESIGN-SPEC.md) — Current ticker architecture (5-component design)
  - [Ticker Implementation Guide](guides/TICKER-IMPLEMENTATION-GUIDE.md)
  - [Ticker API Reference](api/multi-broker-ticker-api.md)
  - [Ticker Documentation Index](decisions/ticker-documentation-index.md)
- ~~[ADR-003 v2: Ticker Architecture](decisions/003-multi-broker-ticker-architecture.md)~~ - Superseded (historical reference)
- [ADR Template](decisions/template.md)

### Feature Documentation
- [AutoPilot](autopilot/)
- [AI Module](ai/)
- [Testing](testing/)
- [API Reference](api/)
- [Feature Registry](feature-registry.yaml)

### Guides
- [Main README](../README.md)
- [CLAUDE.md](../CLAUDE.md) - Project guide for AI assistants
- [CHANGELOG](../CHANGELOG.md)

---

## 🔗 Quick Links by Role

### Backend Developer
1. [Architecture Overview](architecture/overview.md)
2. [Broker Abstraction](architecture/broker-abstraction.md)
3. [Database Schema](architecture/database.md)
4. [API Reference](api/README.md)
5. [backend/CLAUDE.md](../backend/CLAUDE.md)

### Frontend Developer
1. [Architecture Overview](architecture/overview.md)
2. [WebSocket Architecture](architecture/websocket.md)
3. [AutoPilot Components](autopilot/component-design.md)
4. [Testing - Page Objects](testing/README.md)
5. [frontend/CLAUDE.md](../frontend/CLAUDE.md)

### QA/Test Engineer
1. [Testing README](testing/README.md)
2. [E2E Test Rules](testing/e2e-test-rules.md)
3. [frontend/CLAUDE.md - Test Commands](../frontend/CLAUDE.md#development-commands)

### DevOps/Deployment
1. [CLAUDE.md - Production Safety](../CLAUDE.md#0-production-vs-development---never-touch-production)
2. [backend/CLAUDE.md - Environment Variables](../backend/CLAUDE.md#environment-variables)
3. [CLAUDE.md - CI/CD](../CLAUDE.md#cicd)
4. VPS Setup: `C:\Apps\shared\docs\ALGOCHANAKYA-SETUP.md`

---

**Need something not here?** Check [docs/README.md](README.md) or search the codebase.
