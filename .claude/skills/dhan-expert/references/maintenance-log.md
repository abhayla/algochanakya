# Dhan Expert Maintenance Log

> This file tracks API changes, community-reported issues, and skill updates.

## API Change Tracker

### Active Changes

| Date | Change | Impact | Skill Updated |
|------|--------|--------|---------------|
| 2024-01-01 | v2 API released | New base URL /v2, new endpoints | Yes |
| 2024-06-01 | Option Chain API added | POST /v2/optionchain with Greeks | Yes (v2.5) |
| 2024-06-01 | Expiry list API added | GET /v2/expirylist | Yes (v2.5) |
| 2024-09-01 | Live Order Update WebSocket | wss://api-order-update.dhan.co | Yes (v2.5) |
| 2024-01-01 | Forever Orders (GTT) added | /v2/forever/orders | Yes (v2.5) |
| 2024-01-01 | Super Orders added | /v2/super/orders (entry+target+SL in one call) | Yes (v2.6) |
| 2024-01-01 | Trader's Control added | /v2/killswitch + /v2/pnlExit risk management APIs | Yes (v2.6) |

### Known Bugs/Issues

| Issue | Status | Workaround | Last Checked |
|-------|--------|------------|--------------|
| `availabelBalance` typo | Active (by design) | Use exact field name with typo in code | 2026-02-25 |
| Data API unlock requirement | Active | 25 F&O trades/mo or ₹499/mo subscription | 2026-02-25 |
| Little Endian binary WS | Active (by design) | Use `struct.unpack('<...')` | 2026-02-25 |
| 200-depth: 1 instrument limit | Active (by design) | Separate connection per 200-depth instrument | 2026-02-25 |

### Rate Limits (Multi-tier)

| Type | Per Second | Per Minute | Per Hour | Per Day |
|------|-----------|-----------|---------|---------|
| Order Placement | 10 | 250 | 1000 | 7000 |
| REST API (general) | 10 | - | - | - |

## Review History

| Date | Reviewer | Changes |
|------|----------|---------|
| 2026-02-26 | Claude | v2.6: Added Super Order (new reference), Trader's Control (new reference), corrected WS auth to MsgCode:42, fixed forever GET to /forever/all, added IP whitelist indicators, corrected WS URL to query-param auth, fixed heartbeat details (10s/40s), expanded rate limits to 5 categories, 9 new gotchas |
| 2026-02-25 | Claude | v2.5: Forever Orders, Option Chain, Postback/WebSocket, availabelBalance typo, corrected rate limits |
| 2026-02-25 | Claude | v2.0: Implementation status corrections |
| 2026-02-16 | Claude | v1.0: Initial creation |

## Quarterly Review Checklist (Next: May 2026)

- [ ] Verify dhanhq SDK version: `pip show dhanhq`
- [ ] Check Dhan API docs for new endpoints: https://dhanhq.co/docs/v2/
- [ ] Verify Forever Orders API still works
- [ ] Check option chain API for new fields (new Greeks?)
- [ ] Test 200-depth WebSocket (1 instrument per connection still?)
- [ ] Verify Data API unlock criteria unchanged
- [ ] Check for `availabelBalance` typo fix (or confirm it's still a typo)
