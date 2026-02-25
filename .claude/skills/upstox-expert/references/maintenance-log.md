# Upstox Expert Maintenance Log

> This file tracks API changes, community-reported issues, and skill updates.
> Updated by: `reflect deep` mode (automated) or manual review sessions.
> Source: [Upstox Announcements](https://upstox.com/developer/api-documentation/announcements/) + [Developer Forum](https://community.upstox.com/c/developer-api/15)

---

## API Change Tracker

### Active Changes (Affecting Current Implementation)

| Date | Change | Impact | Skill Updated |
|------|--------|--------|---------------|
| 2025-08-22 | V2 WebSocket discontinued | Must use V3 only; code using V2 URL will fail | Yes (v2.0) |
| 2025-07-19 | Fund API response changed | `equity` object now includes commodity data; `commodity` returns `null` | Yes (v2.0) |
| 2025-06-30 | V2 APIs deprecated (migration period) | Migrate to v3 endpoints (orders, historical, quotes) | Yes (v2.0) |
| 2025-06-30 | Trailing Stop Loss (Beta) | New GTT feature — `trailing_stop_loss` field in GTT rules | Yes (v2.0) |
| 2025-05-13 | Expired Instruments APIs (Plus) | New endpoint for Upstox Plus subscribers | Yes (v2.0) |
| 2025-05-13 | WebSocket Plus (5 connections, D30) | Plus subscribers get 5 connections + 30-level depth | Yes (v2.0) |
| 2025-04-17 | Historical Candle V3 | Custom time units (3min, 5min, 10min, 15min, 1hr, 2hr, 4hr); v2 limited | Yes (v2.0) |
| 2025-02-28 | GTT Order API launched | 4 new endpoints — place, modify, cancel, get | Yes (v2.0) |
| 2025-01-16 | Sandbox launched | Testing environment with 30-day token, order APIs only | Yes (v2.0) |
| 2025-01-16 | Access Token Flow for Users (Beta) | Multi-client app token generation without individual OAuth | Yes (v2.0) |
| 2025-01-03 | MarketDataFeedV3 launched | V3 WS with Protobuf; V2 put on deprecation track | Yes (v2.0) |
| 2024-08-31 | Zero brokerage program ended | New users get 90-day free; then standard rates | Yes (v2.0) |
| 2024-04-25 | CSV instruments deprecated | Only JSON format via REST API; CSV download removed | Yes (v2.0) |

### Pricing Changes

| Date | Change | Impact |
|------|--------|--------|
| 2025 | API access changed from ₹499/month to **FREE** | All AlgoChanakya users can use Upstox API at no cost |
| 2026-03 (expected) | API brokerage ₹10/order promotional rate ends | Standard ₹20/order resumes after Mar 2026 |

---

## Known Community Issues

> Source: [Developer API Forum](https://community.upstox.com/c/developer-api/15) | Last checked: 2026-02-25

| Issue | Status | Workaround | Forum Link |
|-------|--------|------------|------------|
| 401 UDAPI100050 on order placement (post-reauth) | Active (Feb 2026) | Re-authenticate fully; check IP whitelist | community.upstox.com |
| Portfolio WS NXDOMAIN errors | Active (Feb 2026) | Retry with exponential backoff; check DNS | community.upstox.com |
| IP whitelisting 403 errors on production | Active (Feb 2026) | Whitelist server IP in My Apps → Settings | community.upstox.com |
| Java SDK CVE vulnerabilities | Reported (Feb 2026) | Use Python SDK; Java SDK dependencies have unpatched CVEs | community.upstox.com |
| WebSocket disconnect on market volatility | Periodic | Implement auto-reconnect with backoff | community.upstox.com |

---

## Pending API Changes (Announced, Not Yet Fully Documented in Skill)

| Announced | Feature | Expected |
|-----------|---------|----------|
| TBD | MCP read-only integration (Claude Desktop, VS Code) | Available at mcp.upstox.com/mcp |
| TBD | GTT Trailing Stop Loss GA (out of Beta) | Q2 2026 estimate |

---

## Skill Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 2.0 | 2026-02-25 | reflect deep | Comprehensive overhaul: FREE pricing, v3 API, GTT/Option Chain/Webhook/Sandbox/MCP, implementation status corrected, rate limits updated, auto-improvement system, 3 new reference files |
| 1.0 | 2026-02-16 | AlgoChanakya | Initial creation with broker skills batch |

---

## Next Review: May 2026

**Checklist for quarterly review:**
- [ ] Check [Upstox API Announcements](https://upstox.com/developer/api-documentation/announcements/) for new/deprecated endpoints
- [ ] Check [Developer API Forum](https://community.upstox.com/c/developer-api/15) for recurring issues (sort by Latest)
- [ ] Run `pip show upstox-python-sdk` for version bumps
- [ ] Verify rate limits haven't changed (test with actual API if possible)
- [ ] Check pricing at [upstox.com/trading-api/](https://upstox.com/trading-api/) for changes
- [ ] Verify Trailing Stop Loss GTT has graduated from Beta
- [ ] Update `last_verified` dates in skill.md Freshness Tracking table
- [ ] Update this maintenance log with any new changes found
