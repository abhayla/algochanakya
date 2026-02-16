# Session: Platform-Default Architecture Documentation Correction
**Saved:** 2026-02-16
**Auto-generated:** false

## Summary
Corrected all architecture documentation from incorrect "user-first" framing to correct "platform-default" framing. The user clarified that platform-level shared credentials are the DEFAULT for market data (all users get data immediately, zero setup). User-level API connections are an OPTIONAL UPGRADE encouraged via persistent banner, not the recommended default. Also updated docs to reflect all 6 brokers for order execution from Phase 1, and added new architectural specs (failover chain, persistent banner, source indicator badge, order execution architecture).

## Working Files
- `CLAUDE.md` (modified) - Rewrote Market Data section, Supported Brokers table, Project Overview
- `docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md` (modified) - Major reframe: 20+ edits, 4 new sections added
- `docs/architecture/broker-abstraction.md` (modified) - Corrected framing, diagrams, examples, design decisions
- `docs/decisions/002-broker-abstraction.md` (modified) - Updated Supported Brokers, Phases 5/6, auth strategy, success metrics
- `C:\Users\Administrator\.claude\projects\C--Abhay-VideCoding-algochanakya\memory\MEMORY.md` (modified) - Corrected from user-first to platform-default

## Recent Changes
All changes are uncommitted. 5 docs files modified with platform-default framing corrections. No code changes.

## Key Decisions (from user Q&A)

| # | Decision | Answer |
|---|----------|--------|
| 1 | Market data default | Platform-level is DEFAULT for all users, NOT user-first |
| 2 | User upgrade UX | Persistent banner on ALL data screens (Dashboard, Watchlist, Option Chain, Positions) |
| 3 | Order broker count | All 6 brokers from Phase 1 (Zerodha, AngelOne, Upstox, Fyers, Dhan, Paytm) |
| 4 | API fallback for orders | refresh_token → OAuth re-login → API key/secret (last resort) |
| 5 | Failover UX | Source indicator badge + toast notification on failover |
| 6 | Platform failover chain | SmartAPI (FREE) → Dhan (FREE†) → Fyers (FREE) → Paytm (FREE) → Upstox (₹499/mo) → Kite Connect (₹500/mo, last resort) |
| 7 | Data vs order broker | Independent choice (user can mix) |
| 8 | Kite as platform data | Include as last resort (platform pays ₹500/mo only if all free options fail) |
| 9 | Credential capture | Broker-specific: SmartAPI (PIN+TOTP), Kite (OAuth), Upstox (OAuth), Dhan (static), Fyers (OAuth), Paytm (OAuth) |

## Relevant Docs
- [Working Doc](../../docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md) - Primary architecture doc, fully reframed
- [Broker Abstraction](../../docs/architecture/broker-abstraction.md) - Multi-broker design, updated with platform-default
- [ADR-002](../../docs/decisions/002-broker-abstraction.md) - Decision record, updated with all 6 brokers
- [CLAUDE.md](../../CLAUDE.md) - Project guide, updated Market Data section

## Implementation Plan (Part 2 — NOT YET STARTED)

The plan has a Part 2 with 5 implementation phases (backend + frontend code). None of this has been started yet.

### Phase 1: Platform Data Foundation (Weeks 1-2)
- Backend config for all 6 platform broker credentials
- BrokerType enum fix (add DHAN, PAYTM)
- Latent bug fix: `conn.api_key` in market_data/factory.py
- New services: PlatformMarketDataService, CircuitBreaker, FailoverController, MarketDataRouter, RequestCoalescer
- Database migrations: market_data_preference, platform_data_status

### Phase 2: Order Execution for All 6 Brokers (Weeks 3-4)
- New adapters: angel_adapter, upstox_adapter, dhan_adapter, fyers_adapter, paytm_adapter
- Factory update, auth routes, token refresh service

### Phase 3: Frontend (Weeks 5-6)
- DataUpgradeBanner.vue, DataSourceIndicator.vue
- Settings redesign, view updates

### Phase 4: WebSocket Refactoring (Week 7)
### Phase 5: Testing (Weeks 8-9)

### Known Issues to Fix
1. `conn.api_key` doesn't exist on BrokerConnection (market_data/factory.py:164)
2. BrokerType missing DHAN, PAYTM (brokers/base.py:25-30)
3. WebSocket uses legacy singletons
4. MarketDataSourceToggle shows only 2 brokers
5. Auth routes hardcoded to Kite + AngelOne

## Where I Left Off
- **Completed:** Part 1 documentation corrections (all 5 files updated and verified)
- **Not started:** Part 2 implementation (backend + frontend code changes)
- **User said:** "update claude.md and other important docs. Then we will continue more discussion"
- **Next:** User wants to continue discussion before starting implementation

## Resume Prompt
Continue discussion on the multi-broker architecture implementation plan. Part 1 (documentation corrections) is complete — all docs now use correct "platform-default" framing. Part 2 (implementation) has 5 phases across ~9 weeks. Key decisions captured in session file at `.claude/sessions/2026-02-16-platform-default-docs-correction.md`. The user may want to discuss implementation priorities, phasing, or ask clarifying questions before coding begins.
