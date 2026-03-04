# Planner-Researcher Agent Memory

**Purpose:** Track architectural decisions, estimation accuracy, and research patterns
**Agent:** planner-researcher
**Last Updated:** 2026-02-25

---

## Patterns Observed

### Architectural Decisions

#### Multi-Broker Architecture
- Decision: Dual abstraction (market data + order execution)
- Rationale: Cost optimization (FREE data brokers vs paid trading APIs)
- Status: Phase 4 complete (ticker/WebSocket), Phase 5 complete (frontend UI + order adapters)
- 6 brokers: Zerodha (Kite), AngelOne (SmartAPI), Upstox, Dhan, Fyers, Paytm
- Platform-default model: SmartAPI is free default for all users, user upgrade optional

#### Ticker Architecture (5-Component Design)
- Decision: TickerAdapter + TickerPool + TickerRouter + HealthMonitor + FailoverController
- Rationale: Replace legacy singletons with broker-agnostic, ref-counted, failover-capable system
- Status: COMPLETE (Feb 2026) — all 6 broker adapters implemented
- Key: Uses `Decimal` not `float` for NormalizedTick prices
- Docs: TICKER-DESIGN-SPEC.md (SSOT), supersedes ADR-003

#### Platform Market Data
- Decision: Platform-level shared credentials serve ALL users by default
- Failover chain: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite
- FREE brokers: SmartAPI, Fyers, Paytm. Paid: Upstox (₹499/mo), Kite (₹500/mo)
- User upgrade: Optional, encouraged via persistent banner on data screens

#### Workflow Design
- Decision: 7-step mandatory workflow with fast-track mode for trivial fixes
- Full mode: requirements → tests → implement → run tests → fix loop → visual verification → commit
- Fast-track: requirements → implement → run existing tests → commit
- Status: Active, fast-track added Feb 2026

### Estimation Accuracy

- Phase 4 (ticker refactoring): Estimated 1 week, took ~2 weeks (WebSocket complexity underestimated)
- Phase 5 (frontend UI + order adapters): Estimated 1 week, completed in ~1 week
- Phase 6 (E2E tests): Estimated 2 days, completed in ~2 days

---

## Decisions Made

### Research Approach

#### Primary Documentation Sources
1. CLAUDE.md (cross-cutting rules, production safety)
2. backend/CLAUDE.md (backend patterns, broker adapters, database)
3. frontend/CLAUDE.md (frontend patterns, E2E test rules)
4. .claude/rules.md (enforced architectural constraints)
5. docs/architecture/broker-abstraction.md (broker design SSOT)
6. docs/decisions/TICKER-DESIGN-SPEC.md (ticker architecture SSOT)

#### Code Search Strategy
1. Check CLAUDE.md files first for documented patterns
2. Use Grep for keyword search across codebase
3. Use Glob for file pattern matching
4. Read identified files for context
5. Check related docs in docs/architecture/ and docs/decisions/

### Design Patterns

#### Broker-Related Features
- ALWAYS use broker adapters via factory functions (never direct API imports)
- ALWAYS use canonical symbol format (Kite format) internally
- ALWAYS use unified data models (UnifiedOrder, UnifiedPosition, UnifiedQuote)
- ALWAYS use SymbolConverter for broker-specific symbol conversion
- ALWAYS use TokenManager for cross-broker token/symbol mapping

#### Testing Strategy
- E2E tests: Playwright with `authenticatedPage` fixture, `data-testid` only
- Backend tests: pytest with async fixtures, mock broker APIs
- Frontend tests: Vitest with happy-dom
- All tests must be in screen/module subdirectories (enforced by hooks)

#### AutoPilot Features
- 26 services in `app/services/autopilot/`
- 16 database tables for strategy management
- Kill switch at `app/services/autopilot/kill_switch.py`
- Condition engine + adjustment engine + suggestion engine

---

## Common Issues

### Missing Context

- Broker-specific API quirks — consult broker expert skills (smartapi-expert, zerodha-expert, etc.)
- AutoPilot service interactions — complex 26-service dependency chain
- AI module trust ladder — graduation criteria need docs/ai/ reference

### Documentation Gaps

- Order execution adapter implementations for non-Kite brokers (Phase 7 pending)
- Frontend broker selection UX documentation (Phase 7 pending)
- AI module integration with multi-broker architecture

---

## Last Updated

2026-02-14: Agent memory system initialized
2026-02-25: Populated with baseline architectural decisions and research patterns
