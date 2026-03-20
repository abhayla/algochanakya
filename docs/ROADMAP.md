# AlgoChanakya Roadmap

**Last Updated:** 2026-03-20

This document tracks active work, recently completed features, and planned development.

---

## 🔄 Active Work (March 2026)

### Live Broker Verification — In Progress
**Goal:** Verify all 6 broker integrations work end-to-end with real credentials.
- [x] Upstox platform token auto-refresh (via `upstox-totp` library)
- [ ] Test Upstox WebSocket ticks with refreshed token
- [ ] Test Fyers OAuth flow with real account
- [ ] Test Paytm OAuth flow with real account
- [ ] Test Dhan static token flow end-to-end
- [ ] Verify `DataSourceBadge` reflects actual live data source
- [ ] Load-test `TickerPool` failover under real market conditions

---

## ✅ Recently Completed (March 2026)

### Credential Architecture Overhaul — COMPLETE (Mar 20, 2026)
**Goal:** Unified credential management across all 6 brokers.

- Unified `broker_api_credentials` table (replaces per-broker tables)
- Settings OAuth callbacks for all brokers (`/api/settings/{broker}/connect-callback`)
- WebSocket credential loading: user creds → .env → ORG_ACTIVE_BROKERS fallback chain
- TickerPool credential cache expiry (`credentials_valid()`, `clear_expired_credentials()`)
- Platform token auto-refresh on startup (Upstox HTTP login via `upstox-totp`)
- Dhan v2 OAuth consent flow
- 55+ new backend tests, all 795 broker tests passing
- 16 commits across 4 phases
- **Docs:** [credential-flow-analysis.md](architecture/credential-flow-analysis.md) | [authentication.md](architecture/authentication.md)

### Hook Consolidation — COMPLETE (Mar 20, 2026)
- Fixed all hook paths (wrong drive C:→D:, typo VideCoding→VibeCoding) — all PreToolUse guards were silently broken
- Rewrote `secret-scanner.sh` as `secret-scanner.py` (eliminated `jq` dependency)
- Removed redundant `protect_sensitive_files.py` (covered by permissions deny list)
- Result: 12 → 10 hook scripts, -116 lines, all hooks functional

---

## ✅ Previously Completed (February 2026)

### Broker Settings UX — COMPLETE (Feb 2026)
- Disconnect endpoints for all 6 brokers (`DELETE /api/auth/{broker}/disconnect`)
- `KiteSettings.vue` with connect/reconnect/disconnect
- AngelOne login hint in `LoginView` explaining credentials prerequisite
- Paytm `public_access_token` input in `PaytmSettings` (required for WebSocket ticks)
- `disconnectBroker()` added to auth store

### Alembic Migration Applied — COMPLETE (Feb 2026)
- DB confirmed at head (`efdf0659b0ab`) — `order_broker` and `market_data_source` columns live

### Phase 6: OAuth Flows, DataSourceBadge & WebSocket Reconnect — COMPLETE (Feb 17, 2026)
- OAuth/auth endpoints for Dhan (static token), Upstox, Fyers, and Paytm Money
- `broker_metadata` JSONB column added to `BrokerConnection` model (with migration)
- `DataSourceBadge` placed in Dashboard, Watchlist, OptionChain, Positions views
- Fixed WebSocket double-reconnect bug (nullify `onclose` before disconnect)
- WebSocket auto-reconnect when market data source changes in BrokerSettings
- Broker login buttons added to LoginView (all 6 brokers with SVG logos)
- Per-broker settings components: `DhanSettings`, `UpstoxSettings`, `FyersSettings`, `PaytmSettings`

### Phase 6: Broker Abstraction E2E Tests — COMPLETE (Feb 17, 2026)
- E2E tests for broker settings UI (`broker-settings.happy.spec.js` — 12 tests)
- Banner/dismiss edge cases (`broker-banner.edge.spec.js` — 8 tests)
- `BrokerSettingsPage` Page Object Model
- Reset button visibility and interaction tests
- Fixed SQLite test compilers for CI (ARRAY, UUID, BigInteger, ENUM)
- Added `aiosqlite` to requirements.txt for async SQLite tests

### Phase 5: Order Execution Adapters & Frontend Broker UI — COMPLETE (Feb 17, 2026)
**Goal:** Order execution adapters for all 6 brokers and user-facing broker selection UI.

- `AngelOneAdapter` — Angel One (SmartAPI) order execution
- `UpstoxOrderAdapter` — Upstox order execution (OAuth ~1yr token)
- `DhanOrderAdapter` — Dhan order execution (static token)
- `FyersOrderAdapter` — Fyers order execution (OAuth)
- `PaytmOrderAdapter` — Paytm Money order execution (3-token system)
- All 6 adapters registered in `brokers/factory.py`
- 61 unit tests in `tests/backend/brokers/test_order_adapters.py`
- Frontend `BrokerSettings.vue`, `BrokerUpgradeBanner.vue`, `DataSourceBadge.vue`
- Market data source dropdown (platform + 6 brokers) + order broker dropdown
- `PUT /api/user/preferences/` and `GET /api/user/preferences/` updated

### Phase 4: Ticker/WebSocket Architecture — COMPLETE (Feb 17, 2026)
**Goal:** Unified multi-tenant WebSocket ticker system supporting all 6 brokers.

- 5-component architecture: `TickerAdapter`, `TickerPool`, `TickerRouter`, `HealthMonitor`, `FailoverController`
- All 6 broker ticker adapters: `smartapi`, `kite`, `dhan`, `fyers`, `paytm`, `upstox`
- `websocket.py` refactored 494 → 292 lines (fully broker-agnostic)
- 714 broker tests passing (413 ticker adapter + 122 core + 179 REST adapter)
- `NormalizedTick` uses `Decimal` for price precision
- **Docs:** [TICKER-DESIGN-SPEC.md](decisions/TICKER-DESIGN-SPEC.md) | [API Reference](api/multi-broker-ticker-api.md)

### auto-verify Skill Enhancements — COMPLETE (Feb 15, 2026)
- AI-powered analysis and structured error parsing (Steps 4–5)
- Smart test execution and performance optimization (Step 3)
- Decision matrix, MCP tools, auto-diagnosis (Steps 6–7)
- Learning-engine integration and consolidated approvals (Step 8)
- Enhanced iteration tracking (Section 10)

---

## ✅ Completed (January 2026)

### Multi-Broker Abstraction (Phases 1–3)
- ✅ `BrokerAdapter` interface and factory pattern
- ✅ `MarketDataBrokerAdapter` interface
- ✅ SmartAPI market data adapter (FREE) + Kite market data adapter
- ✅ `TokenManager`, `RateLimiter`, `SymbolConverter`
- ✅ All routes refactored to use broker factories
- ✅ `broker_instrument_tokens` database table
- ✅ Dhan and Fyers REST market data adapters

**Status:** Production-ready (Jan 2026)

### SmartAPI Integration
- ✅ Auto-TOTP authentication, encrypted credentials, WebSocket V2, historical OHLC, frontend settings UI

**Status:** Production-ready (Jan 2026)

### E2E Test Suite
- ✅ Auto-login via SmartAPI, auth state reuse, Allure reporting

**Status:** Production-ready (Jan 2026)

---

## 📋 Planned Features

### Q2 2026: Live Broker Verification & Hardening

**Goal:** Verify all 6 broker integrations with real credentials end-to-end.

- [ ] Test all OAuth flows with real broker accounts (Upstox, Fyers, Paytm)
- [ ] Test Dhan static token flow end-to-end
- [ ] Verify `DataSourceBadge` reflects actual live data source
- [ ] Load-test `TickerPool` failover under real market conditions
- [ ] Apply pending Alembic migration to production DB

**Status:** Unblocked, ready to start

---

### Q2 2026: Kelly Criterion & AI Enhancements

**Goal:** Complete AI module outstanding tasks.

- [x] Fix `KellyCalculator` data model bug (was querying `AutoPilotOrder.realized_pnl` which doesn't exist; fixed to use `AutoPilotPositionLeg.realized_pnl`)
- [x] Fix `DrawdownTracker` same bug (now queries `AutoPilotPositionLeg`)
- [x] Wire `deploy.py` Kelly mode to real `KellyCalculator` (replaced hardcoded `kelly_fraction = 0.5`)
- [x] Frontend: remove "(Week 9)" placeholder label, add `fetchKellyRecommendation` action
- [ ] Enhanced regime detection (additional regime types)
- [ ] Better strategy recommendations
- [ ] Paper trading graduation refinements

**Status:** Kelly Criterion bug fixed and wired. Regime/recommendations planned for Q2.

---

### Q2 2026: OpenAPI Spec & Docs

- [x] Generate `docs/api/openapi.json` from FastAPI (243 paths, 199 schemas) — via `backend/scripts/generate_openapi.py`
- [ ] Update `docs/features/feature-registry.yaml` post-broker-refactor
- [x] Workflow Redesign (hook consolidation — 12 → 10 scripts, fixed broken paths, eliminated jq dep)

**To regenerate OpenAPI spec:** `cd backend && python scripts/generate_openapi.py`

---

### Q3 2026: Advanced Features

**Backtesting System**
- Historical strategy backtesting with performance metrics
- Monte Carlo simulation, report generation

**Risk Management Enhancements**
- Portfolio-level risk limits, exposure tracking, margin utilization alerts

**AI Improvements**
- ML model improvements (XGBoost/LightGBM), trust ladder refinements

---

## 🎯 Long-Term Vision (2026+)

- **Multi-Timeframe Analysis** — Intraday + swing trading, overnight risk management
- **Social Trading** — Anonymous strategy sharing, leaderboards
- **Mobile App** — React Native, push notifications
- **Advanced Analytics** — ML price prediction, sentiment analysis

---

## Implementation Priority

| Priority | Feature | Timeline | Status |
|----------|---------|----------|--------|
| **P0** | Apply Alembic migration | Now | ✅ Complete |
| **P0** | Live broker E2E verification | Q2 2026 | 🚧 In Progress |
| **P1** | Kelly Criterion (AI) | Q2 2026 | ✅ Bug fixed, wired |
| **P1** | OpenAPI spec + docs | Q2 2026 | ✅ Generated (243 paths) |
| **P1** | Workflow Redesign (hooks) | Q1 2026 | ✅ Complete (Mar 20) |
| **P1** | Credential Architecture Overhaul | Q1 2026 | ✅ Complete (Mar 20) |
| **P2** | Backtesting | Q3 2026 | 💡 Design |
| **P2** | Risk Management Enhancements | Q3 2026 | 💡 Planning |
| **P3** | Multi-Timeframe | Q4 2026 | 💡 Planning |
| **P3** | Social Trading | 2027 | 💡 Vision |
| **P3** | Mobile App | 2027 | 💡 Vision |

**Legend:** ✅ Complete | 🚧 In Progress / Blocked | 📋 Planned (ready to start) | 💡 Design/Vision phase

---

## Release Schedule

### v1.1 (Q1 2026) - Architecture — SHIPPED
- ✅ Multi-broker abstraction (Phases 1–6)
- ✅ 5-component ticker architecture
- ✅ All 6 broker adapters (market data + order execution + WebSocket)
- ✅ Frontend broker selection UI
- ✅ 714 broker tests passing
- ✅ Alembic migration applied (head: efdf0659b0ab)

### v1.2 (Q2 2026) - Hardening & AI
- Live broker verification (all 6 brokers)
- ✅ Kelly Criterion position sizing (bug fixed + wired)
- ✅ OpenAPI spec (243 paths generated)
- ✅ Workflow redesign (hook consolidation — complete Mar 20)
- ✅ Credential architecture overhaul (unified table, auto-refresh — complete Mar 20)

### v1.3 (Q3 2026) - Advanced Features
- Backtesting system (beta)
- Risk management enhancements
- AI model improvements

### v2.0 (Q4 2026) - Major Features
- Advanced analytics
- Multi-timeframe support
- Enhanced AI capabilities

---

## How to Track Progress

- **Active work:** This ROADMAP.md (updated weekly)
- **Daily tasks:** [docs/IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md)
- **Architecture decisions:** [docs/decisions/](decisions/)
- **Feature details:** [docs/features/{feature}/](features/)

---

## Contributing to Roadmap

When planning new features:
1. Create ADR in `docs/decisions/`
2. Update this ROADMAP.md with timeline
3. Add detailed plan to `docs/features/{feature}/`
4. Link from IMPLEMENTATION-CHECKLIST.md for active work
