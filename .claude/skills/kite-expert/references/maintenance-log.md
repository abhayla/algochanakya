# Kite Connect Expert Maintenance Log

> This file tracks API changes, community-reported issues, and skill updates.
> Updated by: reflect deep mode (automated) or manual review sessions.

## API Change Tracker

### Active Changes (Affecting Current Implementation)

| Date | Change | Impact | Skill Updated |
|------|--------|--------|---------------|
| 2025-03-01 | Personal API: FREE for individuals | No cost for personal trading automation | Yes (v2.5) |
| 2025-02-01 | Historical data bundled with Connect ₹500/mo | No separate historical data charge | Yes (v2.5) |
| 2024-01-01 | WebSocket tokens increased 1000→3000/connection | Can subscribe more instruments | Yes |
| 2023-01-01 | Historical data 10 years intraday | Extended historical period | Documented |

### Rate Limit Correction

**IMPORTANT:** SKILL.md v2.0 incorrectly stated rate limit as 3/sec. Correct value is **10 req/sec**. The `rate_limiter.py` may need updating from `"kite": 3` to `"kite": 10`.

### Known Issues

| Issue | Status | Workaround | Last Checked |
|-------|--------|------------|--------------|
| Daily re-auth required (~6 AM) | By design | SmartAPI used for market data instead | 2026-02-25 |
| No auto-refresh token | By design | User completes OAuth daily | 2026-02-25 |
| Instruments CSV 80MB | Active | Cache once per day | 2026-02-25 |
| No Greeks in quote API | By design | Use SmartAPI for option chain | 2026-02-25 |
| BSE instruments separate CSV | Active | Download both NSE + BSE CSVs | 2026-02-25 |

### Pending Features

| Feature | Status | Notes |
|---------|--------|-------|
| Basket orders (iceberg) | Available | Implemented via /orders/iceberg |
| SL-M orders | Available | order_type=SL-M |
| After-Market Orders (AMO) | Available | variety=amo |

## Review History

| Date | Reviewer | Scope | Changes Made |
|------|----------|-------|--------------|
| 2026-02-25 | Claude | Full overhaul v2.0→v2.5 | Rate limit fix (3→10), GTT, option chain (N/A), webhook (N/A), maintenance log |
| 2026-02-25 | Claude | Initial v2.0 | Implementation status corrections, ticker adapter added |
| 2026-02-16 | Claude | Initial v1.0 | File created |

## Quarterly Review Checklist (Next: May 2026)

- [ ] Check Kite Connect docs for API changes: https://kite.trade/docs/connect/v3/
- [ ] Verify rate limits (current: 10/sec general)
- [ ] Check SDK version: `pip show kiteconnect`
- [ ] Verify Personal API still free
- [ ] Check historical data limits (60 days max for minute data)
- [ ] Test GTT endpoints
- [ ] Check WebSocket token limits (currently 3000)
- [ ] Verify auth flow unchanged (checksum SHA-256)
