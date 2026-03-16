# SmartAPI Expert Maintenance Log

> This file tracks API changes, community-reported issues, and skill updates.
> Updated by: reflect deep mode (automated) or manual review sessions.

## API Change Tracker

### Active Changes (Affecting Current Implementation)

| Date | Change | Impact | Skill Updated |
|------|--------|--------|---------------|
| 2025-08-01 | Static IP registration required | HTTP 403 / AG8008 if IP not registered — must whitelist server IPs in Angel One dashboard | Yes (v2.5) |
| 2025-02-01 | Order rate limit increased 10/sec → 20/sec | Rate limiter config may need update if per-order throttling is implemented | Yes (v2.5) |
| 2025-02-01 | SDK v1.5.5 released | New GTT endpoints exposed, stability fixes | Yes (v2.5) |
| 2025-01-01 | Order Update WebSocket added | Real-time order notifications available at `wss://tns.angelone.in/smart-order-update` | Yes (v2.5) |
| 2024-06-01 | Historical data returns PAISE (confirmed behavior) | Divide by 100 required for historical candle data | Documented |
| 2024-01-01 | Instrument master migrated from CSV to JSON | Old CSV endpoint deprecated — use JSON endpoint only | Documented |

| 2026-03-12 | REST `get_quote` returns 0 LTP for illiquid option strikes — community confirmed | Use WebSocket V2 Snap Quote (Mode 3) for complete option chain data; dedicated `/optionChain` endpoint is an alternative to test | Yes — option-chain.md, websocket-protocol.md |

### Known Issues

| Issue | Status | Workaround | Last Checked |
|-------|--------|------------|--------------|
| REST rate limit 1 req/sec | Active (by design) | Use WebSocket for live data; batch REST calls where possible | 2026-02-25 |
| PAISE in WebSocket vs RUPEES in REST | Active (by design, not a bug) | Always divide WebSocket prices by 100; never divide REST quote prices | 2026-02-25 |
| Static IP 403 (AG8008) | Active since Aug 2025 | Register server IPv4 in Angel One developer dashboard | 2026-02-25 |
| Instrument master ~50MB | Active | Cache for 12+ hours; use singleton in `smartapi_instruments.py` | 2026-02-25 |
| TOTP timing issues | Active | Use `pyotp` library; ensure NTP sync; do not manually calculate TOTP | 2026-02-25 |
| Login takes 20-25 seconds | Active (SmartAPI server-side) | Set HTTP timeout to 35+ seconds; do not timeout early | 2026-02-25 |
| Greeks accuracy varies | Under review | SmartAPI calculates Greeks server-side; consider independent calculation for critical decisions | 2026-02-25 |

### Pending API Changes (Not Yet in Skill)

| Announced | Feature | Status |
|-----------|---------|--------|
| 2025 | OAuth preview (instead of PIN+TOTP) | Beta — not yet stable for production |
| 2025 | Options Greeks in WebSocket (binary) | Under testing by Angel One |
| 2025 | BSE F&O added to instrument master | Available — tokens present in master file |

## Review History

| Date | Reviewer | Scope | Changes Made |
|------|----------|-------|--------------|
| 2026-02-25 | Claude (manual) | Full overhaul v2.0 → v2.5 | Static IP requirement (Aug 2025), rate limit 20/sec, Order Update WebSocket, GTT orders, option chain, webhook, AG8008 error code, 4 new reference files, maintenance log |
| 2026-02-25 | Claude (manual) | v2.0 creation | Implementation status corrections, AngelOneAdapter added, ticker adapter row, maintenance section added |
| 2026-02-16 | Claude (manual) | v1.0 creation | Initial file created |

## Quarterly Review Checklist (Next: May 2026)

- [ ] Check Angel One developer portal for new API features or deprecation notices
- [ ] Verify rate limits unchanged (REST: 1 req/sec, orders: 20/sec)
- [ ] Check SDK version: `pip show smartapi-python` — currently v1.5.5
- [ ] Review community issues on GitHub: https://github.com/angel-one/smartapi-python
- [ ] Verify static IP registration process unchanged (currently: max 5 IPs, IPv4 only)
- [ ] Test GTT endpoints still work (may be affected by SEBI regulatory changes)
- [ ] Verify option chain endpoint still returns Greeks
- [ ] Confirm Order Update WebSocket URL (`wss://tns.angelone.in/smart-order-update`) unchanged
- [ ] Check if OAuth (non-TOTP) auth has moved from beta to stable
- [ ] Verify WebSocket V2 binary protocol byte offsets unchanged
- [ ] Update `last_verified` dates across all reference files

## SDK Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.5.5 | 2025-02-01 | GTT endpoints, stability improvements |
| v1.4.x | 2024 | Market data improvements |
| v1.3.x | 2023 | WebSocket V2 support added |
| v1.0.x | 2022 | Initial release |

**Check current version:** `pip show smartapi-python`

## Known Documentation Gaps

These items are not fully documented in the skill and should be researched in future reviews:

| Item | Gap | Priority |
|------|-----|----------|
| OCO GTT orders | Create/Modify request body for OCO type | Medium |
| Order Update WS complete message schema | All possible fields in order update messages | Medium |
| BSE F&O support | Which BSE options are available via SmartAPI | Low |
| Paper trading limitations | Which endpoints work in paper trading mode | Low |
| WebSocket reconnect behavior | Does server send missed ticks on reconnect? | Low |
