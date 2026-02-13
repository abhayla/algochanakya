# Upstox Error Codes

Complete error reference for Upstox API v2.

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

## Authentication Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100010` | 401 | Invalid token | Re-authenticate |
| `UDAPI100011` | 401 | Token expired | Re-do OAuth flow |
| `UDAPI100012` | 403 | Insufficient permissions | Check token scope (extended vs access) |
| `UDAPI100013` | 400 | Invalid authorization code | Get new auth code |
| `UDAPI100014` | 400 | Invalid client credentials | Verify api_key and secret |

## Input Validation Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100050` | 400 | Invalid instrument key | Check instrument_key format |
| `UDAPI100051` | 400 | Invalid order type | Use MARKET, LIMIT, SL, SL-M |
| `UDAPI100052` | 400 | Invalid product type | Use D, I, CO, OC |
| `UDAPI100053` | 400 | Invalid quantity | Check lot size |
| `UDAPI100054` | 400 | Missing required parameter | Add missing field |

## Order Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100020` | 400 | Order rejected | Check rejection reason |
| `UDAPI100021` | 400 | Insufficient margin | Add funds |
| `UDAPI100022` | 400 | Market closed | Use AMO |
| `UDAPI100023` | 400 | Order not found | Verify order_id |
| `UDAPI100024` | 400 | Cannot modify/cancel | Order already completed |

## Rate Limit Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100030` | 429 | Rate limit exceeded | Wait and retry with backoff |

## Server Errors

| Code | HTTP | Message | Resolution |
|------|------|---------|------------|
| `UDAPI100040` | 500 | Internal server error | Retry after delay |
| `UDAPI100041` | 503 | Service unavailable | Retry with backoff |

## Mapping to AlgoChanakya Exceptions

| Upstox Error | AlgoChanakya Exception |
|-------------|----------------------|
| `UDAPI10001x` (auth) | `AuthenticationError` |
| `UDAPI10005x` (input) | `InvalidSymbolError` / `BrokerAPIError` |
| `UDAPI10002x` (order) | `BrokerAPIError` |
| `UDAPI100030` (rate) | `RateLimitError` |
| `UDAPI10004x` (server) | `BrokerAPIError` |

## Retry Strategy

| HTTP Status | Retryable | Strategy |
|-------------|-----------|----------|
| 400 | No | Fix request |
| 401 | No | Re-authenticate |
| 403 | No | Check permissions |
| 429 | Yes | Exponential backoff (1s, 2s, 4s) |
| 500 | Yes | Retry after 2-5s |
| 503 | Yes | Retry with backoff |
