# Upstox Error Codes

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) + [Developer API Forum](https://community.upstox.com/c/developer-api/15) | Last verified: 2026-02-25

Complete error reference for Upstox API v2 and v3.

## Error Response Format

```json
{
  "status": "error",
  "errors": [
    {
      "errorCode": "UDAPI100010",
      "message": "Human-readable error description",
      "propertyPath": null,
      "invalidValue": null,
      "error_type": "bad_request"
    }
  ]
}
```

---

## Authentication Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100010` | 401 | Invalid token | Re-authenticate |
| `UDAPI100011` | 401 | Token expired | Re-do OAuth flow |
| `UDAPI100012` | 403 | Insufficient permissions | Check token scope (extended vs access) |
| `UDAPI100013` | 400 | Invalid authorization code | Get new auth code |
| `UDAPI100014` | 400 | Invalid client credentials | Verify api_key and secret |

---

## Input Validation Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100050` | 400/401 | Invalid instrument key OR auth/order failure | See note below |
| `UDAPI100051` | 400 | Invalid order type | Use MARKET, LIMIT, SL, SL-M |
| `UDAPI100052` | 400 | Invalid product type | Use D, I, CO, OC, MTF |
| `UDAPI100053` | 400 | Invalid quantity | Check lot size |
| `UDAPI100054` | 400 | Missing required parameter | Add missing field |

> **UDAPI100050 — Dual meaning (community-confirmed):**
> 1. **Standard:** Invalid `instrument_key` format (check `NSE_FO|12345` format)
> 2. **Community-reported:** Also appears on valid orders after re-login or session reset — indicates auth/order placement failure unrelated to instrument key. If instrument key is correct, re-authenticate and retry.

---

## Order Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100020` | 400 | Order rejected | Check rejection reason in message |
| `UDAPI100021` | 400 | Insufficient margin | Add funds |
| `UDAPI100022` | 400 | Market closed | Use AMO (is_amo: true) |
| `UDAPI100023` | 400 | Order not found | Verify order_id |
| `UDAPI100024` | 400 | Cannot modify/cancel | Order already completed/cancelled |

---

## Option Chain Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100011` | 400 | Invalid expiry date | Use ISO format YYYY-MM-DD |
| `UDAPI1088` | 400 | Option Chain not available for MCX | Use NSE/BSE instruments only |

---

## GTT Order Error Codes (UDAPI1126–UDAPI1151)

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI1126` | 400 | Invalid GTT order type | Use SINGLE or MULTIPLE |
| `UDAPI1128` | 400 | Invalid number of rules | SINGLE: 1 rule, MULTIPLE: 2-3 rules |
| `UDAPI1130` | 400 | Invalid trigger type | Use ABOVE, BELOW, or IMMEDIATE |
| `UDAPI1132` | 400 | Invalid strategy type | Use ENTRY, TARGET, or STOPLOSS |
| `UDAPI1136` | 400 | GTT order not found | Verify GTT id |
| `UDAPI1137` | 400 | GTT order cannot be modified | Status is TRIGGERED or CANCELLED |
| `UDAPI1141` | 400 | Duplicate GTT order | Same instrument + direction exists |
| `UDAPI1143` | 400 | Trigger price invalid | Check ABOVE/BELOW vs current price |
| `UDAPI1151` | 400 | GTT trigger already fired | Order already executed |

> **GTT error mapping:** All `UDAPI112x`–`UDAPI115x` errors map to `BrokerAPIError` in AlgoChanakya.

---

## Rate Limit Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100030` | 429 | Rate limit exceeded | Wait and retry with exponential backoff |

**Rate limit details:** 50 req/sec general, 4 req/sec for multi-order APIs. Add `Retry-After` header check.

---

## Server Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100040` | 500 | Internal server error | Retry after 2–5s delay |
| `UDAPI100041` | 503 | Service unavailable | Retry with exponential backoff |

---

## IP Whitelisting Errors

| HTTP | Message | Resolution |
|------|---------|------------|
| `403 Forbidden` | Request from non-whitelisted IP | Add server IP to My Apps dashboard → IP Whitelist |

> **Production issue:** 403 errors on order placement often mean the server IP is not whitelisted, not a credential issue. Check My Apps → Settings → IP Whitelist first.

---

## Mapping to AlgoChanakya Exceptions

| Upstox Error | AlgoChanakya Exception |
|-------------|----------------------|
| `UDAPI10001x` (auth) | `AuthenticationError` |
| `UDAPI10005x` (input/invalid key) | `InvalidSymbolError` / `BrokerAPIError` |
| `UDAPI100050` (auth/order failure) | `BrokerAPIError` (re-auth required) |
| `UDAPI10002x` (order) | `BrokerAPIError` |
| `UDAPI100030` (rate) | `RateLimitError` |
| `UDAPI10004x` (server) | `BrokerAPIError` |
| `UDAPI112x`–`UDAPI115x` (GTT) | `BrokerAPIError` |
| `403 Forbidden` (IP) | `BrokerAPIError` (IP whitelist) |

---

## Retry Strategy

| HTTP Status | Retryable | Strategy |
|-------------|-----------|----------|
| 400 | No | Fix request |
| 401 | No | Re-authenticate |
| 403 | No | Check IP whitelist or permissions |
| 429 | Yes | Exponential backoff (1s, 2s, 4s), check Retry-After header |
| 500 | Yes | Retry after 2–5s |
| 503 | Yes | Retry with backoff |
