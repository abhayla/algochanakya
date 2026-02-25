# Fyers Expert Maintenance Log

> This file tracks API changes, community-reported issues, and skill updates.

## API Change Tracker

### Active Changes

| Date | Change | Impact | Skill Updated |
|------|--------|--------|---------------|
| 2023-11-01 | API v3.0.0 released | New SDK fyers-apiv3, 5 socket types, 5K symbols/WS | Yes (v2.5) |
| 2024-01-01 | WebSocket upgraded: 200->5000 symbols | Massive capacity increase | Yes (v2.5) |
| 2024-06-01 | Option Chain API added (v3) | GET /v3/optionchain with Greeks + Charm/Vanna/Rho | Yes (v2.5) |
| 2024-06-01 | Position Socket added | Real-time P&L via FyersPositionSocket | Yes (v2.5) |
| 2024-06-01 | Trade Socket added | Trade execution via FyersTradeSocket | Yes (v2.5) |
| 2022-01-01 | API v2 (legacy) | Deprecated after v3 released | N/A |

### Known Issues

| Issue | Status | Workaround | Last Checked |
|-------|--------|------------|--------------|
| GTT WebSocket events broken | Active (Feb 2026) | Use REST polling for GTT status | 2026-02-25 |
| GTT API underdocumented | Active | Use app for reliable GTT | 2026-02-25 |
| Exchange prefix mandatory | Active (by design) | Always add NSE:/BSE:/MCX: prefix | 2026-02-25 |
| -EQ suffix for equities | Active (by design) | Add -EQ to equity symbols | 2026-02-25 |
| Token expires midnight IST | Active (by design) | Schedule refresh before midnight | 2026-02-25 |
| Historical: 1 req/sec limit | Active (by design) | Queue historical requests | 2026-02-25 |

### Corrections Made in v2.5

- **v3.0.0 release date**: SKILL.md incorrectly stated "Feb 3, 2026". Correct date: **November 2023**
- **WebSocket capacity**: Was "200 symbols" in websocket-protocol.md, corrected to **5,000 symbols**

## Review History

| Date | Reviewer | Changes |
|------|----------|---------|
| 2026-02-25 | Claude | v2.5: v3 release date fix, 5 socket types, option chain, GTT warning, maintenance log |
| 2026-02-25 | Claude | v2.0: Implementation status corrections |
| 2026-02-16 | Claude | v1.0: Initial creation |

## Quarterly Review Checklist (Next: May 2026)

- [ ] Check Fyers API version: `pip show fyers-apiv3`
- [ ] Verify option chain API still returns Greeks
- [ ] Test GTT API endpoints (broken per Feb 2026 community reports)
- [ ] Verify WebSocket symbol capacity (currently 5,000)
- [ ] Check daily 100K request limit
- [ ] Verify appIdHash still SHA-256 of app_id:app_secret
- [ ] Check token expiry time (currently midnight IST)
- [ ] Review community for new issues: https://myapi.fyers.in/docs/
