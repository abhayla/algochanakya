# Fyers Error Codes

Complete error code reference for Fyers API v3.

## Error Response Format

```json
{
  "s": "error",
  "code": -1,
  "message": "Descriptive error message"
}
```

**Note:** Fyers uses **numeric** error codes (e.g., `-16`), unlike SmartAPI's alphanumeric codes (e.g., `AG8001`). Fyers may return HTTP 200 with a negative code in the body -- always check the `code` field.

---

## Error Code Reference

### Authentication Errors (code: -16)

| Code | HTTP | Cause | Retryable | Resolution |
|------|------|-------|-----------|------------|
| `-16` | 401 | access_token expired or malformed | No | Re-authenticate via OAuth |
| `-16` | 401 | Wrong app_id in auth header | No | Verify app_id matches dashboard |
| `-16` | 401 | Midnight IST token expiry | No | Re-authenticate (tokens reset daily) |

**Most common `-16` cause:** Using `Bearer` prefix instead of `{app_id}:{access_token}`.

```python
# WRONG: headers = {"Authorization": f"Bearer {access_token}"}  -> code -16
# WRONG: headers = {"Authorization": access_token}               -> code -16
# CORRECT:
headers = {"Authorization": f"{app_id}:{access_token}"}
```

### Bad Request Errors (code: -1)

| Code | HTTP | Cause | Retryable | Resolution |
|------|------|-------|-----------|------------|
| `-1` | 400 | Malformed JSON or missing fields | No | Validate request body |
| `-1` | 400 | Invalid parameter value | No | Check API docs for valid values |
| `-1` | 400 | Invalid/expired auth code | No | Request new auth code via OAuth |
| `-1` | 400 | Wrong appIdHash | No | Verify `SHA256(app_id:app_secret)` |
| `-1` | 400 | Redirect URI mismatch | No | Fix URI to match Fyers app settings |
| `-1` | 400 | Invalid order type/product | No | Use valid type (1-4) / product values |
| `-1` | 400 | Order not found for modify/cancel | No | Verify order ID from order book |

### Rate Limit Errors (code: -300)

| Code | HTTP | Cause | Retryable | Resolution |
|------|------|-------|-----------|------------|
| `-300` | 429 | Too many requests per second | Yes | Wait 1s, retry with backoff |
| `-300` | 429 | Daily/hourly API limit reached | Yes | Wait for limit reset |

**Rate limits:** General 10 req/s, Historical 1 req/s, Orders 10/s.

### Symbol Errors (code: -310)

| Code | HTTP | Cause | Retryable | Resolution |
|------|------|-------|-----------|------------|
| `-310` | 400 | Missing exchange prefix | No | Add `NSE:`, `BSE:`, or `MCX:` prefix |
| `-310` | 400 | Symbol not in instrument master | No | Re-download instrument master CSV |
| `-310` | 400 | Missing `-INDEX` or `-EQ` suffix | No | Add required suffix |
| `-310` | 400 | Expired derivative contract | No | Use current contract |

```python
# Common -310 mistakes:
"NIFTY2522725000CE"        # Missing prefix -> -310
"NSE:NIFTY50"              # Missing -INDEX suffix -> -310
"NSE:RELIANCE"             # Missing -EQ suffix -> -310
# Correct:
"NSE:NIFTY2522725000CE"
"NSE:NIFTY50-INDEX"
"NSE:RELIANCE-EQ"
```

### Order Rejection Errors (code: -320)

| Code | HTTP | Cause | Retryable | Resolution |
|------|------|-------|-----------|------------|
| `-320` | 400 | Exchange rejected the order | No | Check `message` for reason |
| `-320` | 400 | Insufficient margin | No | Add funds or reduce quantity |
| `-320` | 400 | Invalid quantity / wrong lot size | No | Use correct lot size from constants |
| `-320` | 400 | Price beyond circuit limits | No | Adjust price within circuit range |
| `-320` | 400 | Market closed | No | Use `offlineOrder: true` or wait |
| `-320` | 400 | Scrip suspended | No | Wait for trading to resume |

**Note:** `side` must be integer (`1`=Buy, `-1`=Sell), NOT string.

### Server Errors (code: -99)

| Code | HTTP | Cause | Retryable | Resolution |
|------|------|-------|-----------|------------|
| `-99` | 500 | Internal server error | Yes | Retry with exponential backoff |
| `-99` | 503 | Service unavailable | Yes | Wait and retry |
| `-99` | 504 | Gateway timeout | Yes | Retry after 5 seconds |

---

## Mapping to AlgoChanakya Exceptions

| Fyers Code | AlgoChanakya Exception | Action |
|------------|----------------------|--------|
| `-16` | `AuthenticationError` | Re-authenticate via OAuth |
| `-300` | `RateLimitError` | Auto-handled by rate_limiter.py |
| `-310` | `InvalidSymbolError` | Check symbol_converter.py |
| `-320` | `BrokerAPIError` (order rejected) | Return rejection details to user |
| `-99` | `BrokerAPIError` (retryable) | Retry with backoff (1s, 2s, 4s) |
| `-1` | `BrokerAPIError` | Log and return error |

### Exception Mapping Code

```python
from app.services.brokers.market_data.exceptions import (
    AuthenticationError, BrokerAPIError, InvalidSymbolError, RateLimitError,
)

def map_fyers_error(response: dict) -> Exception:
    """Map Fyers error response to AlgoChanakya exception."""
    code = response.get("code", 0)
    message = response.get("message", "Unknown error")
    mapping = {
        -16: AuthenticationError(broker="fyers", message=f"Auth error: {message}"),
        -300: RateLimitError(broker="fyers", message=message, retry_after=1.0),
        -310: InvalidSymbolError(broker="fyers", message=f"Invalid symbol: {message}"),
        -320: BrokerAPIError(broker="fyers", message=f"Order rejected: {message}"),
        -99: BrokerAPIError(broker="fyers", message=f"Server error: {message}", retryable=True),
    }
    return mapping.get(code, BrokerAPIError(broker="fyers", message=f"Error ({code}): {message}"))
```

### Usage in Adapter

```python
class FyersMarketDataAdapter:
    async def _make_request(self, method, endpoint, **kwargs):
        response = await self._client.request(method, endpoint, **kwargs)
        data = response.json()
        if data.get("s") == "error" or data.get("code", 200) < 0:
            raise map_fyers_error(data)
        return data
```

---

## WebSocket Errors

| Scenario | Cause | Resolution |
|----------|-------|------------|
| Connection refused | Invalid `{app_id}:{access_token}` | Re-authenticate |
| Disconnect at midnight | Token expired | Get new token |
| No data after subscribe | Invalid/missing exchange prefix | Verify symbol format |
| Subscription silently fails | >200 symbols | Stay under limit |
| SDK crash | Using `fyers-apiv2` | Upgrade to `fyers-apiv3` |

---

## Debugging Tips

1. **Always check `s` field** -- HTTP 200 can still have `"s": "error"`
2. **`-16` errors** are always auth format issues or token expiry -- never retry
3. **`-300` rate limits** -- wait 1s minimum, then retry with backoff
4. **`-310` symbol errors** -- 99% of the time it's a missing prefix or suffix
5. **`-320` rejections** -- pass the `message` to the user, it has the specific reason
6. **`-99` server errors** -- exponential backoff (1s, 2s, 4s), max 3 retries
7. **Test with virtual trading** first using Fyers paper trading mode
