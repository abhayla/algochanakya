# Paytm Money Error Codes and Exception Mapping

> **MATURITY WARNING:** Paytm Money's error responses are not fully standardized.
> The same error may return different HTTP codes or message formats depending on the endpoint.
> Always handle unexpected error shapes gracefully.

## HTTP Status Codes

| Status | Meaning | Retry? |
|--------|---------|--------|
| 400 | Bad Request (invalid params) | No |
| 401 | Unauthorized (expired/invalid JWT) | No (re-auth) |
| 403 | Forbidden (wrong token type) | No (use correct token) |
| 429 | Rate limit exceeded | Yes (backoff) |
| 500/502/503 | Server error / maintenance | Yes (backoff) |

## Error Response Formats

> **WARNING:** Paytm returns two different error shapes. The adapter must handle both.

```json
// Format 1 (most endpoints)
{"message": "Error description", "code": "ERROR_CODE_STRING", "data": null}

// Format 2 (some endpoints)
{"error": true, "message": "Error description", "status_code": 400}
```

> **MATURITY WARNING:** Paytm has been observed returning HTTP 200 with error payloads
> in the body. Always validate response body fields, not just HTTP status.

## Error Code Tables

### Authentication (401) & Authorization (403)

| Code | Cause | Resolution |
|------|-------|------------|
| `TOKEN_EXPIRED` | JWT past validity (~24h) | Re-authenticate via OAuth |
| `INVALID_TOKEN` | Malformed or revoked JWT | Re-authenticate via OAuth |
| `SESSION_EXPIRED` | Server-side session invalidated | Re-authenticate via OAuth |
| `INVALID_API_KEY` | Wrong or deactivated API key | Verify API key in settings |
| `INSUFFICIENT_PERMISSION` | read_access_token used for write op | Use access_token |
| `WRONG_TOKEN_TYPE` | access_token used for WebSocket | Use public_access_token |
| `API_NOT_ENABLED` | Feature not activated | Contact Paytm support |

### Order Errors (400)

| Code | Cause | Resolution |
|------|-------|------------|
| `INVALID_ORDER` | Missing/wrong fields | Validate order payload |
| `INSUFFICIENT_FUNDS` | Not enough margin | Check margin before order |
| `INVALID_QUANTITY` | Wrong lot size or zero qty | Use correct lot size |
| `MARKET_CLOSED` | Outside trading hours | Queue for next session |
| `SCRIP_NOT_FOUND` | Invalid security_id | Verify against script master |
| `PRICE_OUT_OF_RANGE` | Beyond circuit limits | Adjust price |
| `ORDER_NOT_FOUND` | Invalid order_no | Verify order number |
| `ORDER_ALREADY_COMPLETE` | Modifying filled order | No action needed |
| `ORDER_ALREADY_CANCELLED` | Cancelling twice | No action needed |

### WebSocket Errors

| Code | Cause | Resolution |
|------|-------|------------|
| 4001 | Invalid security_id | Fix scripId |
| 4002 | Over 200 instruments | Unsubscribe unused first |
| 4003 | Invalid modeType | Use LTP or FULL |
| 4004 | Invalid public_access_token | Re-authenticate |
| 1000 | Server closing normally | Reconnect |
| 1006 | Abnormal closure (network/crash) | Reconnect with backoff |

## AlgoChanakya Exception Mapping

```python
from app.services.brokers.market_data.exceptions import (
    BrokerAuthError, BrokerAPIError, BrokerRateLimitError,
    BrokerDataError, BrokerConnectionError, BrokerOrderError,
)

def map_paytm_error(status_code: int, error_code: str, message: str) -> Exception:
    """Map Paytm Money error to AlgoChanakya exception."""
    if status_code == 401 or error_code in ("TOKEN_EXPIRED", "INVALID_TOKEN", "SESSION_EXPIRED"):
        return BrokerAuthError(broker="paytm", message=message, retriable=False)
    if status_code == 403:
        return BrokerAuthError(broker="paytm", message=f"Permission denied: {message}", retriable=False)
    if status_code == 429:
        return BrokerRateLimitError(broker="paytm", message=message, retry_after=1.0)
    if error_code in ("INVALID_ORDER", "INSUFFICIENT_FUNDS", "INVALID_QUANTITY",
                       "MARKET_CLOSED", "PRICE_OUT_OF_RANGE", "ORDER_NOT_FOUND"):
        return BrokerOrderError(broker="paytm", message=message, retriable=False)
    if error_code == "SCRIP_NOT_FOUND":
        return BrokerDataError(broker="paytm", message=message)
    if status_code in (500, 502, 503):
        return BrokerConnectionError(broker="paytm", message=message, retriable=True, retry_after=5.0)
    return BrokerAPIError(broker="paytm", message=message, status_code=status_code)
```

## Retry Strategy

| Error Category | Retry? | Strategy | Max Retries |
|---------------|--------|----------|-------------|
| Auth (401/403) | No | Re-authenticate user | 0 |
| Bad Request (400) | No | Fix request params | 0 |
| Rate Limit (429) | Yes | Exponential backoff from 1s | 3 |
| Server Error (500) | Yes | Exponential backoff from 2s | 3 |
| Bad Gateway (502) | Yes | Exponential backoff from 5s | 5 |
| Service Down (503) | Yes | Wait 30s then retry | 3 |
| WebSocket Disconnect | Yes | Reconnect backoff (1s-30s) | 10 |

```python
async def retry_with_backoff(func, max_retries=3, initial_delay=1.0):
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except (BrokerRateLimitError, BrokerConnectionError) as e:
            if attempt == max_retries or (hasattr(e, 'retriable') and not e.retriable):
                raise
            await asyncio.sleep(delay)
            delay *= 2
```
