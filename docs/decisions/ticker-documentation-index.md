# Multi-Broker Ticker Documentation Index

**Last Updated:** 2026-02-16

This index consolidates all documentation for the multi-broker ticker architecture (WebSocket live price feeds).

---

## 📚 Current Documentation (Feb 14, 2026)

### 1. Primary Design Specification
**[TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md)** - **START HERE**
- **Status:** Current design (refined from ADR-003 v2)
- **Version:** 2.1.0
- **What it contains:**
  - 5-component architecture (TickerAdapter, TickerPool, TickerRouter, HealthMonitor, FailoverController)
  - NormalizedTick data model with `Decimal` types
  - Health scoring formula (latency 30%, tick_rate 30%, errors 20%, staleness 20%)
  - Make-before-break failover strategy
  - Thread→asyncio bridge for SmartAPI/Kite WebSocket libraries
- **Use this for:** Understanding the system architecture, design rationale, component interactions

### 2. Implementation Guide
**[../guides/TICKER-IMPLEMENTATION-GUIDE.md](../guides/TICKER-IMPLEMENTATION-GUIDE.md)** - **BUILD FROM THIS**
- **Status:** Current (Feb 16, 2026)
- **Length:** 3,868 lines with complete production-ready code
- **What it contains:**
  - 5 implementation phases (T1-T5) with full code
  - Phase T1: Core infrastructure (TickerAdapter, TickerPool, TickerRouter, HealthMonitor, FailoverController)
  - Phase T2: SmartAPI + Kite adapters, websocket.py refactoring (494→90 lines)
  - Phase T3: Health monitoring + failover integration
  - Phase T4: System credentials + adapter stubs (Upstox, Dhan, Fyers, Paytm)
  - Phase T5: Frontend updates + legacy cleanup
  - Testing strategy, migration guide, troubleshooting sections
- **Use this for:** Step-by-step implementation with copy-paste ready code

### 3. API Reference
**[../api/multi-broker-ticker-api.md](../api/multi-broker-ticker-api.md)** - **API CONTRACTS**
- **Status:** Current (v2.1.0)
- **What it contains:**
  - Complete interface definitions for all 5 components
  - NormalizedTick schema with `Decimal` types
  - Health score calculation formulas
  - WebSocket message protocol
  - Error handling patterns
  - Rate limiting specifications
- **Use this for:** Interface contracts, data models, protocol specifications

### 4. Broker Abstraction Overview
**[../architecture/broker-abstraction.md](../architecture/broker-abstraction.md)** - **CONTEXT**
- **Status:** Current (updated Feb 16, 2026)
- **What it contains:**
  - Phase 4 ticker architecture summary
  - Links to current design documentation
  - NormalizedTick definition with `Decimal` rationale
  - Broker comparison matrix
  - Symbol/token mapping patterns
- **Use this for:** High-level context, multi-broker strategy, design decisions

---

## 🚫 Superseded Documentation (Historical Reference Only)

### ADR-003 v2: Multi-Broker Ticker Architecture (SUPERSEDED)
**[003-multi-broker-ticker-architecture.md](003-multi-broker-ticker-architecture.md)**
- **Status:** ⚠️ SUPERSEDED by TICKER-DESIGN-SPEC.md
- **What changed:**
  - 6 components → **5 components** (SystemCredentialManager merged into TickerPool)
  - `float` prices → **`Decimal` prices** (precision critical for financial calculations)
  - Different health score formula (Connection 30%, Latency 20%, Errors 20%, Freshness 30%)
  - Less detailed implementation guidance
- **Do NOT use for implementation** - kept for historical context only

### Old Implementation Guide (SUPERSEDED)
**[../architecture/multi-broker-ticker-implementation.md](../architecture/multi-broker-ticker-implementation.md)**
- **Status:** ⚠️ SUPERSEDED by ../guides/TICKER-IMPLEMENTATION-GUIDE.md
- **What changed:**
  - New guide has 5-component design (not 6)
  - 3,868 lines vs ~500 lines (8x more detailed)
  - Complete code for all 5 phases (not just outlines)
  - Testing strategy, migration guide, troubleshooting sections
- **Do NOT use for implementation** - kept for historical context only

---

## 🗺️ Navigation Guide

**I want to...**

### Understand the Architecture
1. Read **[TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md)** (design overview)
2. Read **[../architecture/broker-abstraction.md](../architecture/broker-abstraction.md)** (Phase 4 context)
3. Refer to **[../api/multi-broker-ticker-api.md](../api/multi-broker-ticker-api.md)** (interface contracts)

### Implement the System
1. Follow **[../guides/TICKER-IMPLEMENTATION-GUIDE.md](../guides/TICKER-IMPLEMENTATION-GUIDE.md)** phase by phase
2. Refer to **[../api/multi-broker-ticker-api.md](../api/multi-broker-ticker-api.md)** for interface details
3. Cross-reference **[TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md)** for design decisions

### Add a New Broker Adapter
1. Read **[../guides/TICKER-IMPLEMENTATION-GUIDE.md](../guides/TICKER-IMPLEMENTATION-GUIDE.md)** Phase T2 (SmartAPI/Kite examples)
2. Refer to **[../api/multi-broker-ticker-api.md](../api/multi-broker-ticker-api.md)** (TickerAdapter interface)
3. Review **[../architecture/broker-abstraction.md](../architecture/broker-abstraction.md)** (broker comparison matrix)

| Key Source File | Purpose |
|-----------------|---------|
| `token_policy.py` | Auth error classification per broker — 4 categories (RETRYABLE, RETRYABLE_ONCE, NOT_RETRYABLE, NOT_REFRESHABLE). Drives instant failover vs gradual decay in HealthMonitor. |

### Troubleshoot Issues
1. Check **[../guides/TICKER-IMPLEMENTATION-GUIDE.md](../guides/TICKER-IMPLEMENTATION-GUIDE.md)** troubleshooting section
2. Review **[TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md)** design constraints
3. Verify against **[../api/multi-broker-ticker-api.md](../api/multi-broker-ticker-api.md)** contracts

### Understand Design Decisions
1. Read **[TICKER-DESIGN-SPEC.md](TICKER-DESIGN-SPEC.md)** Section 11 (Design Decisions)
2. Compare with **[003-multi-broker-ticker-architecture.md](003-multi-broker-ticker-architecture.md)** (what changed and why)
3. Review **[../architecture/broker-abstraction.md](../architecture/broker-abstraction.md)** (Decimal vs float rationale)

---

## 📊 Key Design Differences (v2.0.0 → v2.1.0)

| Aspect | ADR-003 v2 (Old) | TICKER-DESIGN-SPEC (Current) |
|--------|------------------|------------------------------|
| **Components** | 6 (includes SystemCredentialManager) | **5** (merged into TickerPool) |
| **NormalizedTick prices** | `float` | **`Decimal`** (precision critical) |
| **Health formula** | Connection 30%, Latency 20%, Errors 20%, Freshness 30% | **Latency 30%, Tick_Rate 30%, Errors 20%, Staleness 20%** |
| **Implementation detail** | High-level outline | **3,868 lines with complete code** |
| **Testing strategy** | Minimal | **Comprehensive with unit/integration/E2E** |
| **Migration guide** | Not included | **Included with rollback plan** |

---

## 🔗 External References

- **SmartAPI WebSocket V2:** https://smartapi.angelbroking.com/docs/WebSocket2
- **Kite Ticker:** https://kite.trade/docs/connect/v3/websocket/
- **Upstox WebSocket (Protobuf):** https://upstox.com/developer/api-documentation/websocket-market-data-api
- **Dhan WebSocket:** https://dhanhq.co/docs/v2/market-feed/
- **Fyers WebSocket:** https://api-docs.fyers.in/v2/websocket/

---

## 📝 Maintenance Notes

**When to Update This Index:**
- New design documents are created
- Existing design documents are superseded
- Implementation phases are completed
- Breaking changes to architecture

**Last Review:** 2026-02-16 (Task #5 completion)

**Next Review Due:** When Phase T1 implementation begins
