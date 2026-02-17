# AlgoChanakya Roadmap

**Last Updated:** 2026-02-17

This document tracks active work, recently completed features, and planned development.

---

## 🔄 Active Work (February 2026)

### Workflow Redesign (In Progress)
**Goal:** Simplify and optimize automation workflows
**Status:** 🚧 Design complete, implementation in progress
**Details:** [.claude/WORKFLOW-DESIGN-SPEC.md](../.claude/WORKFLOW-DESIGN-SPEC.md)

**Improvements:**
- Hooks: 9 → 4 (consolidation)
- Total timeout: 395s → 110s (72% reduction)
- Total code: 3,100 → 1,200 lines (61% reduction)

**Timeline:** Q1 2026

---

---

## ✅ Recently Completed (February 2026)

### Ticker Architecture Redesign — COMPLETE (Feb 2026)
**Goal:** Multi-broker WebSocket architecture (5-component design)
**Status:** ✅ Complete
**Details:** [TICKER-DESIGN-SPEC.md](decisions/TICKER-DESIGN-SPEC.md) | [Implementation Guide](guides/TICKER-IMPLEMENTATION-GUIDE.md) | [API Reference](api/multi-broker-ticker-api.md)

**Results:**
- 5-component architecture: TickerAdapter, TickerPool, TickerRouter, HealthMonitor, FailoverController
- All 6 broker ticker adapters implemented (SmartAPI, Kite, Dhan, Fyers, Paytm, Upstox)
- `websocket.py` refactored from 494 → 292 lines (broker-agnostic)
- 714 broker tests passing (413 ticker adapter + 122 core component + 179 REST adapter)
- NormalizedTick uses `Decimal` for price precision

### Phase 6: Broker Abstraction E2E Tests — COMPLETE (Feb 2026)
- E2E tests for broker settings and abstraction layer
- Reset button visibility and interaction tests

---

## ✅ Recently Completed (January 2026)

### Multi-Broker Abstraction (Phase 1-3)
- ✅ BrokerAdapter interface and factory pattern
- ✅ MarketDataBrokerAdapter interface
- ✅ SmartAPI market data adapter (FREE data source)
- ✅ Kite market data adapter
- ✅ TokenManager for cross-broker symbol/token mapping
- ✅ RateLimiter for per-broker API limits
- ✅ SymbolConverter for canonical format
- ✅ All routes refactored to use broker factories
- ✅ `broker_instrument_tokens` database table

**Status:** Production-ready (Jan 2026)

### SmartAPI Integration
- ✅ Auto-TOTP authentication (no manual TOTP entry)
- ✅ Encrypted credentials storage
- ✅ WebSocket V2 ticker service
- ✅ Historical OHLC data service
- ✅ Frontend settings UI

**Status:** Production-ready (Jan 2026)

### E2E Test Suite Expansion
- ✅ Auto-login via SmartAPI
- ✅ Auth state reuse
- ✅ Allure reporting

**Status:** Production-ready (Jan 2026)

---

## 📋 Planned Features

### Q2 2026: Additional Broker Integrations

**Upstox Adapter**
- Market data adapter
- Order execution adapter
- Ticker WebSocket implementation
- Frontend broker selection

**Fyers Adapter**
- Market data adapter
- Order execution adapter
- Ticker WebSocket implementation

**Status:** Design phase, Q2 2026 target

---

### Q2-Q3 2026: More Broker Support

**Dhan Adapter** - Q3 2026
**Paytm Money Adapter** - Q3 2026

Each includes:
- Market data abstraction
- Order execution abstraction
- WebSocket ticker
- Frontend integration

---

### Q2 2026: AngelOne Order Execution

**Goal:** Support Angel One for order placement (currently only market data)

**Tasks:**
- Implement `AngelAdapter` extending `BrokerAdapter`
- Order placement API integration
- Position/margin fetching
- Register in factory
- Add E2E tests

**Benefit:** Fully FREE broker option (SmartAPI data + SmartAPI orders = Rs.0/month)

**Status:** Planned, Q2 2026

---

### Q3 2026: Advanced Features

**Backtesting System**
- Historical strategy backtesting
- Performance metrics
- Monte Carlo simulation
- Report generation

**Status:** Design phase

**Risk Management Enhancements**
- Portfolio-level risk limits
- Exposure tracking
- Margin utilization alerts
- Kill switch improvements

**Status:** Planning

**AI Improvements**
- Enhanced regime detection (more regimes)
- Better strategy recommendations
- Paper trading improvements
- Trust ladder refinements

**Status:** Continuous improvement

---

## 🎯 Long-Term Vision (2026+)

### Multi-Timeframe Analysis
- Intraday + swing trading support
- Multi-day position tracking
- Overnight risk management

### Social Trading
- Share strategies (anonymized)
- Leaderboards
- Community insights

### Mobile App
- React Native mobile client
- Push notifications
- Quick trade execution

### Advanced Analytics
- Machine learning for price prediction
- Sentiment analysis integration
- News impact analysis

---

## Implementation Priority

| Priority | Feature | Timeline | Status |
|----------|---------|----------|--------|
| **P0** | Workflow Redesign | Q1 2026 | 🚧 In Progress |
| **P0** | Ticker Architecture | Q1 2026 | ✅ Complete |
| **P1** | Upstox Integration | Q2 2026 | 📋 Planned |
| **P1** | Fyers Integration | Q2 2026 | 📋 Planned |
| **P1** | Angel Orders | Q2 2026 | 📋 Planned |
| **P2** | Dhan Integration | Q3 2026 | 📋 Planned |
| **P2** | Paytm Integration | Q3 2026 | 📋 Planned |
| **P2** | Backtesting | Q3 2026 | 💡 Design |
| **P3** | Multi-Timeframe | Q4 2026 | 💡 Planning |
| **P3** | Social Trading | 2027 | 💡 Vision |
| **P3** | Mobile App | 2027 | 💡 Vision |

**Legend:**
- ✅ Complete
- 🚧 In Progress
- 📋 Planned (ready to start)
- 💡 Design/Vision phase

---

## Release Schedule

### v1.1 (Q1 2026) - Architecture Improvements
- Workflow redesign complete
- Ticker architecture v2
- Performance optimizations

### v1.2 (Q2 2026) - Broker Expansion
- Upstox support
- Fyers support
- Angel One order execution

### v1.3 (Q3 2026) - More Brokers + Features
- Dhan support
- Paytm Money support
- Backtesting system (beta)

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

---

**Questions about roadmap?** Check [docs/README.md](README.md) or ask the development team.
