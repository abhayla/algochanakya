# Session: Hybrid Architecture - User API Coexistence with Platform-Level Data

**Saved:** 2026-02-16 (Session 3)
**Auto-generated:** false

---

## Summary

Completed comprehensive architecture design for **hybrid market data system** that allows users with their own broker API credentials to co-exist with the platform-level shared data architecture. This is Session 3 in the multi-broker architecture series, building on Session 1 (requirements) and Session 2 (platform-level implementation).

**Three major explorations completed:**

1. **Platform-level 1000+ user scaling architecture** - How 3-layer system (Broker WS → Redis Pub/Sub → User WS) handles 1000+ concurrent users with performance math proving it scales to 10K+

2. **Hybrid dual-path architecture** - How users with own API credentials (Kite Connect ₹500/mo or SmartAPI personal) can use dedicated connections while 99% of free users share platform credentials

3. **Complete working doc** - Comprehensive 1,600+ line architecture specification ready for implementation planning

**Key architectural decisions:**
- ✅ Dual-path routing via `MarketDataRouter` component
- ✅ User preference: `market_data_preference` ('platform' vs 'own_api')
- ✅ Graceful fallback: User API fails → Auto-switch to platform
- ✅ Cost isolation: Users pay their own API fees, no cross-subsidy
- ✅ Fair usage quotas: 10GB/month, 10M ticks/month per user
- ✅ No interference: User-level connections don't affect platform performance

---

## What Was Accomplished

### Phase 1: Deep Dive on 1000+ User Scaling
1. **Documented 3-layer architecture** in detail:
   - Layer 1: Broker WebSocket connections (1:N pattern, ref-counted)
   - Layer 2: Redis Pub/Sub distribution (O(1) fan-out, 2s cache)
   - Layer 3: Platform WebSocket server (per-user connections)

2. **Performance math** proving scalability:
   - Broker utilization: 3.3% (300 instruments / 9K capacity)
   - Redis load: 250 msg/sec (handles millions/sec)
   - Network: 33.6 Mbps (servers handle 1+ Gbps)
   - **Conclusion:** Scales to 10K+ users on single instance

3. **Optimization techniques** documented:
   - Request coalescing: 60-80% API call reduction
   - HTTP connection pooling: 60% latency reduction (300ms → 120ms)
   - Circuit breaker pattern: Auto-pause failing brokers
   - Multi-broker failover: SmartAPI → Upstox → Fyers

### Phase 2: Hybrid Architecture Design
4. **Explored edge case:** What if user has own Kite Connect API (₹500/mo)?
   - Initial assumption: Platform-only would force all users to free tier
   - Reality: Power traders willing to pay for premium features

5. **Designed dual-path architecture:**
   - Platform path: 99% of users, shared data (₹0/month)
   - User path: 1% power traders, dedicated connections (₹500/mo or free)
   - Router component decides path based on user preference

6. **Database schema changes:**
   - `user_preferences.market_data_preference` ('platform' or 'own_api')
   - `user_data_services` table to track user-level connections
   - `broker_connections.subscription_type` to distinguish Kite Connect vs Personal API

7. **Frontend UI mockup:**
   - Settings page with radio buttons: Platform Data (recommended) vs Own API
   - Warning if user selects Own API without valid credentials
   - Cost display: ₹0/month (platform) vs ₹500/month (Kite) or ₹0 (SmartAPI)

### Phase 3: Complete Working Doc
8. **Updated comprehensive architecture spec:**
   - Total: 1,600+ lines (from 575 original)
   - Added: 1000+ user scaling section (600 lines)
   - Added: Hybrid architecture section (400 lines)
   - Includes: Code examples, database schemas, performance math, UI mockups

9. **Ready for implementation planning:**
   - Phase 1 MVP: Platform-level only (4 weeks)
   - Phase 2: Add user-level path (2 weeks)
   - Clear migration path for existing users

---

## Working Files

### Created (This Session)
- None (all updates to existing working doc)

### Modified
- **`docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md`** (MAJOR UPDATE)
  - Line 1-575: Original platform-level architecture (from Session 2)
  - Line 576-990: NEW - "Deep Dive: Handling 1000+ Concurrent Users" section
  - Line 991-1600: NEW - "Hybrid Architecture: User-Level API Coexistence" section
  - Version: 1.0 → 1.2
  - Status: Requirements Complete, Ready for Implementation Planning

### Read Extensively (Research Phase)
- `backend/app/models/smartapi_credentials.py` - Per-user SmartAPI credentials structure
- `backend/app/models/broker_connections.py` - Per-user OAuth tokens for order execution
- `backend/app/models/user_preferences.py` - User preferences (market_data_source field)
- `backend/app/api/routes/websocket.py` - Current WebSocket route (495 lines, legacy)
- `backend/app/services/brokers/market_data/factory.py` - Per-user adapter factory
- `backend/app/config.py` - App-level API keys configuration
- `.claude/sessions/2026-02-16-platform-level-multi-broker-architecture.md` - Session 2 summary

### Referenced Documentation
- `docs/decisions/TICKER-DESIGN-SPEC.md` - 5-component ticker design (needs update)
- `docs/guides/TICKER-IMPLEMENTATION-GUIDE.md` - 3,868-line implementation guide
- `docs/architecture/broker-abstraction.md` - Multi-broker design principles
- `docs/decisions/002-broker-abstraction.md` - Original abstraction decision
- `backend/CLAUDE.md` - Backend-specific patterns and broker adapter usage

---

## Recent Changes

**Git Status:**
- Modified: CLAUDE.md, backend/.env.example, backend/CLAUDE.md (11 files total, from earlier session)
- New: `docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md` (1,600+ lines)
- New: `.claude/sessions/2026-02-16-market-data-architecture-requirements.md` (Session 1)
- New: `.claude/sessions/2026-02-16-platform-level-multi-broker-architecture.md` (Session 2)
- New: `.claude/sessions/2026-02-16-hybrid-architecture-user-api-coexistence.md` (this session)

**No git commit yet** - All work is in working doc, ready for review and implementation planning.

---

## Key Decisions Made

### Architectural Decisions

| # | Decision | Rationale | Impact |
|---|----------|-----------|--------|
| 1 | **Dual-path architecture** (not platform-only) | Support power traders willing to pay ₹500/month for premium | Serves both free (99%) and premium (1%) users |
| 2 | **MarketDataRouter component** | Central routing logic with graceful fallback | Clean separation, easy to test, no duplication |
| 3 | **User-level service = isolated pool** | No Redis sharing, direct WebSocket | Prevents interference with platform performance |
| 4 | **Graceful fallback to platform** | User API fails → Auto-switch to free tier | Better UX, prevents complete data loss |
| 5 | **Fair usage quotas** | 10GB/month, 10M ticks/month per user | Prevent abuse of "own_api" mode (reselling) |
| 6 | **No cross-subsidy** | Users pay their own API fees | Platform cost remains ₹0, sustainable |
| 7 | **Phase 1 = platform-only** | MVP without user-level complexity | Faster launch, serves 99% of users |
| 8 | **Phase 2 = add user-level** | Premium feature for power traders | Incremental complexity, revenue opportunity |

### Technical Decisions

| Component | Technology | Reason |
|-----------|-----------|--------|
| **Data source routing** | Python conditional logic | Simple, no external dependencies |
| **User preference storage** | PostgreSQL column | Already have user_preferences table |
| **User service lifecycle** | Per-connection instantiation | Clean isolation, no global state |
| **Credential validation** | Try API call, catch 403 | Distinguishes Kite Connect (has data) vs Personal API (no data) |
| **Fallback mechanism** | Try-except with router switch | Automatic, no user intervention |
| **Usage tracking** | Database counters | Fair usage enforcement, analytics |

---

## Relevant Docs

### Created This Session
- [Working Doc: Platform-Level Multi-Broker Architecture](../../docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md) - **UPDATED to 1,600+ lines** with complete platform + hybrid architecture

### To Be Updated (Next Session)
- [TICKER-DESIGN-SPEC.md](../../docs/decisions/TICKER-DESIGN-SPEC.md) - Needs platform-level credentials section
- [TICKER-IMPLEMENTATION-GUIDE.md](../../docs/guides/TICKER-IMPLEMENTATION-GUIDE.md) - Needs dual-path routing implementation
- [Broker Abstraction Architecture](../../docs/architecture/broker-abstraction.md) - Add platform vs user-level distinction
- [ADR-002: Broker Abstraction](../../docs/decisions/002-broker-abstraction.md) - Document dual-path pattern

### Referenced During Research
- [DEVELOPER-QUICK-REFERENCE.md](../../docs/DEVELOPER-QUICK-REFERENCE.md) - Quick commands
- [backend/CLAUDE.md](../../backend/CLAUDE.md) - Broker adapter patterns
- [frontend/CLAUDE.md](../../frontend/CLAUDE.md) - Frontend patterns

### Session History
- [Session 1: Market Data Architecture Requirements](2026-02-16-market-data-architecture-requirements.md) - Initial research on app-level vs user-level
- [Session 2: Platform-Level Architecture](2026-02-16-platform-level-multi-broker-architecture.md) - Industry research, platform-level design
- [Session 3: Hybrid Architecture](2026-02-16-hybrid-architecture-user-api-coexistence.md) - This session, dual-path design

---

## Where I Left Off

### ✅ Completed (This Session)
1. **1000+ user scaling architecture** - Complete with performance math
2. **Redis Pub/Sub fan-out pattern** - Detailed implementation with code examples
3. **Request coalescing pattern** - Multi-user → single broker call optimization
4. **HTTP connection pooling** - 60% latency reduction technique
5. **Hybrid dual-path architecture** - Platform + user-level coexistence
6. **Data source router component** - Routing logic with graceful fallback
7. **User data service design** - Isolated per-user market data
8. **Database schema updates** - market_data_preference, user_data_services table
9. **Frontend UI mockup** - Settings page for data source selection
10. **Fair usage quotas** - Bandwidth and tick count limits
11. **Complete working doc** - 1,600+ lines, ready for implementation

### 📋 Next Immediate Actions

**Priority 1: Update Architecture Docs (2-3 hours)**
1. Update TICKER-DESIGN-SPEC.md with platform-level credentials section
   - Remove `system_broker_credentials` table references (wrong approach)
   - Add platform credentials in `.env` section
   - Add dual-path routing architecture
2. Update TICKER-IMPLEMENTATION-GUIDE.md with dual-path implementation
   - Add `MarketDataRouter` component code
   - Add `UserMarketDataService` component code
   - Update Phase 1-4 roadmap to reflect dual-path
3. Update broker-abstraction.md with platform vs user-level distinction
   - Add section: "Market Data: Two Modes"
   - Document when to use each mode
4. Update ADR-002 with dual-path pattern decision
   - Add "Decision: Hybrid Architecture" section
   - Document rationale and alternatives considered

**Priority 2: Database Schema Migration (1 hour)**
5. Create migration: Add `market_data_preference` column to `user_preferences`
6. Create migration: Add `user_data_services` table
7. Create migration: Add `subscription_type` column to `broker_connections`
8. Run migrations on dev database
9. Verify schema changes

**Priority 3: Implementation Planning (2 hours)**
10. Create Phase 1 task breakdown (platform-level only, 4 weeks)
    - Platform credentials setup
    - Redis Pub/Sub integration
    - Platform WebSocket to frontend
    - User OAuth for orders
11. Create Phase 2 task breakdown (user-level, 2 weeks)
    - MarketDataRouter component
    - UserMarketDataService component
    - Frontend settings page
    - Usage tracking and quotas

**Priority 4: Frontend Mockups (Optional, 1 hour)**
12. Create Figma/wireframe for data source settings page
13. Define UX flow for switching between platform/own API
14. Design warning messages for edge cases

---

## Blockers/Open Questions

**None** - All architectural questions resolved for this phase.

**Decisions Deferred (Not Blockers):**
- User override UI design (exact layout, styling) - Can design during Phase 2 implementation
- Fair usage quota values (10GB? 5GB? 20GB?) - Can tune based on real usage data
- Kite Connect vs Personal API detection method - Current approach (try API call) is sufficient
- Enterprise/white-label pricing model - Future business decision
- Multi-tier premium offering (Bronze/Silver/Gold) - Future revenue model discussion

---

## Performance & Cost Summary

### Scalability Proof (1000+ Users)

**With 1000 concurrent users, each watching 10 instruments:**

| Metric | Value | Capacity | Utilization |
|--------|-------|----------|-------------|
| Unique instruments | 300 | 9,000 (SmartAPI) | **3.3%** ✅ |
| Redis messages/sec | 250 | Millions/sec | **0.025%** ✅ |
| Backend WS connections | 1,000 | 10,000+ | **10%** ✅ |
| Network bandwidth | 33.6 Mbps | 1+ Gbps | **3.36%** ✅ |

**Conclusion:** Easily scales to 10,000+ users on single backend instance.

### Cost Comparison

| User Type | Data Source | Broker API Cost | Platform Cost | User Cost | Latency |
|-----------|-------------|-----------------|---------------|-----------|---------|
| **Free User** | Platform shared | ₹0 (SmartAPI FREE) | ₹0 | **₹0/month** | ~50-200ms |
| **Premium User** | Own SmartAPI | ₹0 (user's SmartAPI) | ₹0 | **₹0/month** | ~20-50ms |
| **Premium User** | Own Kite Connect | ₹500/month (user pays) | ₹0 | **₹500/month** | ~20-50ms |

**Total Platform Cost:** ₹0/month (scales to ∞ users at zero cost)

---

## Resume Prompt

```
/start-session hybrid-architecture-user-api-coexistence

Resume the multi-broker architecture work from 2026-02-16 Session 3.

Context: Completed comprehensive architecture design for hybrid market data system. This allows users with own broker API credentials (Kite Connect ₹500/mo or SmartAPI personal) to use dedicated connections, while 99% of free users share platform credentials.

Working doc updated: docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md (1,600+ lines)

Key deliverables:
- 1000+ user scaling architecture with performance math
- Dual-path routing via MarketDataRouter component
- UserMarketDataService for isolated per-user connections
- Database schema updates (market_data_preference, user_data_services)
- Frontend UI mockup for data source selection
- Fair usage quotas (10GB/month, 10M ticks/month)

Next task: Update Ticker Design Spec and Implementation Guide to reflect dual-path architecture. Also update broker-abstraction.md and ADR-002 with platform vs user-level distinction.

Implementation roadmap:
- Phase 1 MVP: Platform-level only (4 weeks) - serves 99% of users
- Phase 2: Add user-level path (2 weeks) - premium feature for power traders

Architecture docs to update:
- docs/decisions/TICKER-DESIGN-SPEC.md
- docs/guides/TICKER-IMPLEMENTATION-GUIDE.md
- docs/architecture/broker-abstraction.md
- docs/decisions/002-broker-abstraction.md

Database migrations needed:
- ALTER TABLE user_preferences ADD COLUMN market_data_preference
- CREATE TABLE user_data_services
- ALTER TABLE broker_connections ADD COLUMN subscription_type

Session files:
- .claude/sessions/2026-02-16-market-data-architecture-requirements.md (Session 1)
- .claude/sessions/2026-02-16-platform-level-multi-broker-architecture.md (Session 2)
- .claude/sessions/2026-02-16-hybrid-architecture-user-api-coexistence.md (this session)
```

---

## Research Agent IDs (For Reference)

Research conducted via parallel agents:
- Initial session agents from Session 1-2 (see previous session files)
- No new agents spawned this session (used existing working doc + database models)

All research consolidated into Working Doc v1.2 (1,600+ lines).

---

**Session complete.** Ready to update architecture docs and start implementation planning.
