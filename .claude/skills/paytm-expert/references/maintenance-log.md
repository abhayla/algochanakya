# Paytm Money Expert Maintenance Log

> This file tracks API changes, community-reported issues, and skill updates.
> High priority for monitoring — Paytm Money API has frequent undocumented breaking changes.

## API Change Tracker

### Active Changes

| Date | Change | Impact | Skill Updated |
|------|--------|--------|---------------|
| 2025-01-01 | BSE F&O instruments added | BSE options now available | Yes (v2.5) |
| 2024-07-01 | pyPMClient last updated (v?) | SDK maintenance low priority | Yes (v2.5) |
| 2024-01-01 | Breaking change (unknown) | Monitor for response format changes | Monitor |

### Known Issues / Limitations

| Issue | Status | Workaround | Last Checked |
|-------|--------|------------|--------------|
| No webhooks | Permanent | REST polling only | 2026-02-25 |
| No order update WebSocket | Permanent | REST polling | 2026-02-25 |
| Least mature API | Ongoing | Defensive error handling | 2026-02-25 |
| SDK pyPMClient low maintenance | Ongoing | May need custom HTTP calls | 2026-02-25 |
| Breaking changes without notice | Ongoing | Pin SDK version, monitor | 2026-02-25 |
| Limited F&O coverage | Ongoing | Verify each instrument before use | 2026-02-25 |
| 3-token system complexity | By design | Map each token to correct endpoint | 2026-02-25 |
| WebSocket uses query param auth | By design | Use `?x_jwt_token={public_access_token}` | 2026-02-25 |

### Historical Breaking Changes (Known)

| Date (Approx) | Change | Note |
|---------------|--------|------|
| 2023-2024 | Various endpoint paths changed | API v1 paths not stable |
| Unknown | Response format changes | No deprecation notices given |

## Maturity Warning

Paytm Money is the **least mature** of all 6 supported brokers:
- Sporadic SDK maintenance
- Limited community support
- Occasional undocumented breaking changes
- Less complete instrument coverage vs NSE/BSE full coverage

**Recommendation:** Always implement Paytm adapter with extra try/except blocks and extensive logging.

## Review History

| Date | Reviewer | Changes |
|------|----------|---------|
| 2026-02-25 | Claude | v2.5: GTT, option chain (Heckyl), webhook (no webhooks), BSE F&O 2025, maintenance log |
| 2026-02-25 | Claude | v2.0: Implementation status corrections |
| 2026-02-16 | Claude | v1.0: Initial creation |

## Quarterly Review Checklist (Next: May 2026)

- [ ] Check for any Paytm Money API breaking changes: https://developer.paytmmoney.com/docs/
- [ ] Verify SDK: `pip show pyPMClient`
- [ ] Test 3-token authentication flow
- [ ] Verify endpoint paths haven't changed (common with Paytm)
- [ ] Check BSE F&O coverage completeness
- [ ] Test GTT endpoints (if implementing)
- [ ] Monitor for webhook/order WS addition (unlikely but check)
- [ ] Community check: Look for user reports of API issues
