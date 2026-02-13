# SmartAPI Error Codes

Complete error code reference for Angel One SmartAPI.

## Error Response Format

All SmartAPI errors follow the standard envelope:

```json
{
  "status": false,
  "message": "Error description",
  "errorcode": "AG8001",
  "data": null
}
```

## Authentication Errors

| Code | Message | Cause | Retryable | Resolution |
|------|---------|-------|-----------|------------|
| `AG8001` | Invalid Token | JWT expired or malformed | No | Re-authenticate (login) |
| `AG8002` | Invalid Client Code | Wrong client ID | No | Verify client_id in credentials |
| `AG8003` | Invalid TOTP | TOTP expired or wrong | Yes | Regenerate TOTP, check clock sync |
| `AG8004` | Invalid Password | Wrong PIN | No | Verify password |
| `AG8005` | Account Locked | Too many failed attempts | No | Wait 30 min or contact Angel One |
| `AG8006` | Invalid API Key | Wrong or deactivated API key | No | Check ANGEL_API_KEY in .env |
| `AG8007` | API Key Expired | API key subscription ended | No | Renew API subscription |
| `AB1012` | Session Expired | Token validity ended | No | Re-authenticate |
| `AB1013` | Duplicate Session | Another session active | No | Logout other session first |

## Rate Limiting Errors

| Code | Message | Cause | Retryable | Resolution |
|------|---------|-------|-----------|------------|
| `AB1010` | Rate Limit Exceeded | Too many requests/second | Yes | Wait 1 second, retry |
| `AB1011` | Too Many Requests | Burst limit hit | Yes | Implement backoff |

## Market Data Errors

| Code | Message | Cause | Retryable | Resolution |
|------|---------|-------|-----------|------------|
| `AB1004` | Invalid Exchange or Token | Wrong exchange/token combo | No | Verify token belongs to exchange |
| `AB8050` | Data Not Found | Symbol/date range invalid | No | Check symbol exists, valid dates |
| `AB8051` | Exchange Closed | Market hours over | No | Wait for market open |
| `AB1005` | Invalid Symbol | Symbol not in master | No | Re-download instrument master |
| `AB1006` | Invalid Interval | Wrong historical interval | No | Use valid interval values |

## Order Errors

| Code | Message | Cause | Retryable | Resolution |
|------|---------|-------|-----------|------------|
| `AB2000` | Order Rejected | Various order issues | Depends | Check rejection reason |
| `AB2001` | Insufficient Margin | Not enough funds | No | Add funds or reduce quantity |
| `AB2002` | Invalid Quantity | Wrong lot size | No | Use correct lot size |
| `AB2003` | Order Not Found | Invalid order ID | No | Verify order ID |
| `AB2004` | Cannot Modify | Order already executed | No | Place new order |
| `AB2005` | Cannot Cancel | Order already completed | No | N/A |
| `AB2006` | Market Closed | Order placed after hours | No | Use AMO variety |
| `AB2007` | Price Out of Range | Limit price invalid | No | Adjust price within circuit |
| `AB2008` | Scrip Suspended | Trading halted | No | Wait for trading to resume |
| `AB2009` | Maximum Order Value Exceeded | Order too large | No | Reduce quantity/lots |

## Connection Errors

| Code | Message | Cause | Retryable | Resolution |
|------|---------|-------|-----------|------------|
| `-1` | Connection Timeout | Network issue | Yes | Check network, retry |
| `-2` | Server Error | SmartAPI server down | Yes | Wait and retry |
| `AB1000` | General Error | Unspecified error | Depends | Check message details |
| `AB1001` | Internal Server Error | Server-side issue | Yes | Wait and retry |

## WebSocket Errors

| Scenario | Error Type | Cause | Resolution |
|----------|-----------|-------|------------|
| Connection refused | TCP error | Invalid URL or server down | Check URL, retry |
| Immediate disconnect | Auth error | Invalid feed_token or API key | Re-authenticate |
| No data received | Subscription error | Wrong exchange type for token | Verify exchange segment code |
| Partial data | Mode mismatch | Parsing wrong mode format | Check mode byte in header |
| Reconnect loop | Token expired | Feed token expired (24h) | Get new feed token |

## Mapping to AlgoChanakya Exceptions

SmartAPI errors map to unified exceptions in `market_data/exceptions.py`:

| SmartAPI Error | AlgoChanakya Exception | Notes |
|---------------|----------------------|-------|
| `AG8001`, `AG8003`, `AB1012` | `AuthenticationError` | Trigger re-auth |
| `AB1010`, `AB1011` | `RateLimitError` | Auto-handled by rate_limiter |
| `AB1004`, `AB1005`, `AB8050` | `InvalidSymbolError` | Check symbol conversion |
| `AB8050`, `AB8051` | `DataNotAvailableError` | Market closed or no data |
| All others | `BrokerAPIError` | Generic broker error |

```python
# Exception mapping in smartapi_adapter.py
from app.services.brokers.market_data.exceptions import (
    AuthenticationError,     # Auth failures
    BrokerAPIError,          # General API errors
    InvalidSymbolError,      # Symbol/token not found
    DataNotAvailableError,   # No data for request
    RateLimitError,          # Rate limit exceeded
)
```

## HTTP Status Codes

SmartAPI uses standard HTTP codes alongside error codes:

| HTTP Status | Meaning | Common Error Codes |
|-------------|---------|-------------------|
| `200` | Success (check `status` field) | May have `errorcode` even with 200 |
| `400` | Bad Request | `AB1004`, `AB1005` |
| `401` | Unauthorized | `AG8001`, `AB1012` |
| `403` | Forbidden | `AG8006`, `AG8007` |
| `429` | Too Many Requests | `AB1010` |
| `500` | Internal Server Error | `AB1001` |

**Important:** SmartAPI sometimes returns HTTP 200 with `"status": false` and an error code. Always check both HTTP status AND the `status` field in the response body.

## Debugging Tips

1. **Always log the full response** including `errorcode` and `message`
2. **Check `status` field** even on HTTP 200 responses
3. **Token-related errors** (AG8001, AB1012) require re-authentication, not retry
4. **Rate limit errors** should trigger exponential backoff (1s, 2s, 4s)
5. **Market data errors** during off-hours are expected (AB8051)
6. **Order rejections** (AB2000) contain detailed reason in `message` field
