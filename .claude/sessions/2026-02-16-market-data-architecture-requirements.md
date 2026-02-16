# Session: Market Data Architecture Requirements Gathering
**Saved:** 2026-02-16
**Auto-generated:** false

## Summary
Interactive Q&A session to define requirements for how broker APIs handle market data (live ticks + OHLC) at App-level (shared across all users) vs User-level (per-user). This is a **requirements gathering session** — no code changes were made. The goal is to capture decisions and update architecture documentation before implementation.

## What Was Accomplished

### Research Phase
1. **Explored current architecture** — 3 parallel agents analyzed:
   - Current market data code (singletons, factories, adapters)
   - Planned 5-component ticker architecture (design specs, implementation guide)
   - Broker connection models and credential storage
2. **Deep-dived the planned ticker architecture** — Read all 5 components in detail:
   - TickerAdapter, TickerPool, TickerRouter, HealthMonitor, FailoverController
   - System credentials DB model (`system_broker_credentials`)
   - Startup sequence, failover sequence, ref-counting
3. **Researched broker WebSocket limits** — All 6 brokers' WS and REST limits documented

### Requirements Captured (User Decisions)

| # | Question | Decision |
|---|----------|----------|
| 1 | Does planned architecture (system creds for ticks, per-user for OHLC) match vision? | **No, needs changes** |
| 2 | What's your vision for app-level market data? | **App-level for BOTH ticks AND OHLC** |
| 3 | Should all users share system creds for OHLC, or allow user override? | **App-level default + user override** |
| 4 | Same pattern for live ticks? | **Yes, same pattern** (app-level default + user override) |
| 5 | When user overrides ticks, separate WS or share? | **Separate connection** for user-level |
| 6 | Order execution stays per-user? | **Yes, always per-user** |
| 7 | Who sets app-level system credentials? | **Backend config / .env** (no admin UI yet) |
| 8 | Which broker is default app-level? | **SmartAPI (Angel One)** |
| 9 | Scale requirement? | **10,000+ concurrent users** |
| 10 | Rate limit strategy for shared OHLC? | **Multi-layer: Cache + WS ticks replacing REST + user fallback + request coalescing** |

### Requirements NOT Yet Decided (Session Paused Here)
- **Tick subscription strategy** — On-demand vs pre-subscribe active F&O vs hybrid (question was asked but user paused session)
- Cache TTL values for different data types
- How user override is configured in the UI
- Failover broker ranking when using app-level
- How to handle brokers with low WS limits (Dhan=500, Fyers=200, Paytm=200) at app-level

## Broker WebSocket Limits (Research Result)

| Broker | Max Tokens/Conn | Max Connections | Total Capacity |
|--------|----------------|-----------------|----------------|
| SmartAPI | 3,000 | 3 | **9,000** |
| Kite | 3,000 | 3 | **9,000** |
| Upstox | ~1,500-5,000 | 1 | **1,500-5,000** |
| Dhan | 100 (Ticker) | 5 | **500** |
| Fyers | 200 | 1 | **200** |
| Paytm | 200 | 1 | **200** |

## Key Architectural Insight
Only SmartAPI and Kite can serve as app-level brokers for 10K+ users (9,000 token capacity each). Dhan/Fyers/Paytm are too limited (200-500 tokens) for app-level primary use.

## Working Files (Read During Session)
- `backend/app/api/routes/websocket.py` (read lines 1-80) - Current WS route with legacy singletons
- `backend/app/services/brokers/market_data/factory.py` (read full) - Per-user adapter factory
- `backend/app/models/user_preferences.py` (read full) - MarketDataSource enum + model
- `backend/app/config.py` (read full) - App-level API keys
- `backend/app/services/brokers/market_data/market_data_base.py` (read lines 1-80) - Interface + credentials
- `docs/decisions/TICKER-DESIGN-SPEC.md` (read full) - 5-component design spec
- `docs/guides/TICKER-IMPLEMENTATION-GUIDE.md` (read ~2000 lines) - Implementation guide with code
- `.claude/skills/broker-shared/comparison-matrix.md` - Broker comparison
- `.claude/skills/*/references/websocket-protocol.md` - All 6 broker WS protocols
- `.claude/rules.md` (read lines 1-100) - Architectural rules

## Recent Changes
- `CLAUDE.md` was modified earlier in this session (added Quick Reference Card, Automation System section, enhanced port config warnings) — these are unrelated to the requirements gathering

## Key Decisions Made
1. **OHLC should use app-level credentials by default** (change from current per-user-only design)
2. **Consistent pattern across ticks AND OHLC**: app-level default + user override
3. **User override = separate dedicated connection** (not sharing app-level connection)
4. **10K+ scale requires multi-layer rate limit strategy**, not just caching
5. **SmartAPI is the right default** for app-level (FREE, 9K token capacity, auto-TOTP)

## Relevant Docs
- [TICKER-DESIGN-SPEC.md](../../docs/decisions/TICKER-DESIGN-SPEC.md) - Current 5-component design (needs updating with new requirements)
- [TICKER-IMPLEMENTATION-GUIDE.md](../../docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) - 3,868-line implementation guide (needs updating)
- [Broker Abstraction Architecture](../../docs/architecture/broker-abstraction.md) - Multi-broker architecture
- [ADR-002](../../docs/decisions/002-broker-abstraction.md) - Broker abstraction decision record
- [Market Data Factory](../../backend/app/services/brokers/market_data/factory.py) - Current per-user factory (needs app-level support)

## Where I Left Off
- **Just completed:** Researched all 6 broker WS/REST limits, presented findings
- **In progress:** Q&A session on requirements — paused at "tick subscription strategy" question (on-demand vs pre-subscribe vs hybrid)
- **Next steps when resuming:**
  1. Continue Q&A: decide tick subscription strategy
  2. Decide cache TTL values
  3. Decide how user override is configured in UI
  4. Compile all requirements into a formal document
  5. Get user confirmation on complete requirements
  6. Update architecture docs (TICKER-DESIGN-SPEC, implementation guide, broker-abstraction)

## Plan File
A plan file exists at `C:\Users\Administrator\.claude\plans\dreamy-baking-blossom.md` with initial research report. This will need to be updated with final requirements before implementation.

## Resume Prompt
```
/start-session

Resume the market data architecture requirements gathering session from 2026-02-16.

Context: We're doing an interactive Q&A to define how broker APIs handle market data at App-level (shared, 10K+ users) vs User-level.

Decisions made so far:
- App-level system credentials for BOTH ticks AND OHLC (not just ticks)
- App-level default + user override pattern (consistent for ticks and OHLC)
- User override = separate dedicated connection
- SmartAPI as default app-level broker (9K token capacity, FREE)
- Multi-layer rate limit strategy (cache + WS ticks + user fallback + coalescing)
- 10,000+ concurrent users target scale

Next question to answer: Tick subscription strategy — on-demand vs pre-subscribe active F&O vs hybrid. The user asked me to explain broker limits before deciding (done). Now continue the Q&A.

Session file: .claude/sessions/2026-02-16-market-data-architecture-requirements.md
```
