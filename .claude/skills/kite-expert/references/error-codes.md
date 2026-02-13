# Kite Connect Error Codes

Complete error reference for Zerodha Kite Connect v3.

## Error Response Format

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error_type": "ExceptionClassName"
}
```

## Exception Classes

Kite Connect uses typed exceptions. The `error_type` field maps directly to Python SDK exception classes.

### TokenException (HTTP 403)

Authentication and token-related errors.

| Message | Cause | Resolution |
|---------|-------|------------|
| `Incorrect api_key or access_token` | Invalid/expired token | Re-authenticate via OAuth |
| `Invalid checksum` | Wrong SHA-256 in session exchange | Verify api_key + request_token + api_secret |
| `Token is invalid or has expired` | access_token expired (~6 AM) | Re-do OAuth flow |
| `Invalid api_key` | API key wrong or deactivated | Check KITE_API_KEY in .env |

### InputException (HTTP 400)

Invalid request parameters.

| Message | Cause | Resolution |
|---------|-------|------------|
| `Invalid instrument_token` | Token not found | Verify token from instruments list |
| `Missing required parameter: {param}` | Required field missing | Add missing field |
| `Invalid order_type` | Wrong order type value | Use MARKET, LIMIT, SL, SL-M |
| `Invalid product` | Wrong product type | Use CNC, NRML, MIS |
| `Invalid variety` | Wrong variety in URL | Use regular, amo, co, iceberg |
| `Quantity must be a multiple of lot_size` | Wrong lot size | Check lot size for instrument |
| `Invalid exchange` | Exchange code wrong | Use NSE, BSE, NFO, BFO, MCX |

### OrderException (HTTP 400/500)

Order placement and modification errors.

| Message | Cause | Resolution |
|---------|-------|------------|
| `Insufficient funds` | Not enough margin | Add funds or reduce quantity |
| `Order rejected by exchange` | Exchange-level rejection | Check rejection reason |
| `Market is closed` | Outside trading hours | Use AMO variety |
| `Price out of circuit range` | Limit price beyond circuit | Adjust price |
| `Scrip is suspended` | Trading halted | Wait for resume |
| `Order not found` | Invalid order_id | Verify order exists |
| `Cannot modify completed order` | Order already filled | N/A |
| `Cannot cancel completed order` | Order already filled | N/A |

### NetworkException (HTTP 429, 502, 503)

Network and rate limit errors.

| HTTP Status | Message | Cause | Resolution |
|-------------|---------|-------|------------|
| `429` | `Too many requests` | Rate limit exceeded | Wait, implement backoff |
| `502` | `Bad Gateway` | Server gateway error | Retry after 1-2 seconds |
| `503` | `Service Unavailable` | Server overloaded | Retry with exponential backoff |

### GeneralException (HTTP 500)

Server-side errors.

| Message | Cause | Resolution |
|---------|-------|------------|
| `Internal server error` | Kite server issue | Retry after delay |
| `Something went wrong` | Unspecified error | Check Kite status page |

### PermissionException (HTTP 403)

Authorization errors.

| Message | Cause | Resolution |
|---------|-------|------------|
| `Insufficient permission` | API plan doesn't include feature | Upgrade plan |
| `Exchange not enabled` | User not registered for exchange | Enable in Zerodha console |

### DataException (HTTP 400)

Data retrieval errors.

| Message | Cause | Resolution |
|---------|-------|------------|
| `No data available` | No candles for date range | Check date range validity |
| `Invalid date range` | from > to or too wide | Adjust dates |

## HTTP Status Code Summary

| Status | Exception | Retryable |
|--------|-----------|-----------|
| `200` | None (success) | - |
| `400` | `InputException`, `OrderException`, `DataException` | No - fix request |
| `403` | `TokenException`, `PermissionException` | No - re-auth or upgrade |
| `429` | `NetworkException` | Yes - exponential backoff |
| `500` | `GeneralException`, `OrderException` | Yes - retry after delay |
| `502` | `NetworkException` | Yes - retry after 1-2s |
| `503` | `NetworkException` | Yes - retry with backoff |

## Mapping to AlgoChanakya Exceptions

| Kite Exception | AlgoChanakya Exception | Notes |
|---------------|----------------------|-------|
| `TokenException` | `AuthenticationError` | Trigger re-auth flow |
| `InputException` | `InvalidSymbolError` or `BrokerAPIError` | Depends on message |
| `OrderException` | `BrokerAPIError` | Log rejection reason |
| `NetworkException` (429) | `RateLimitError` | Auto-handled by rate_limiter |
| `NetworkException` (502/503) | `BrokerAPIError` | Retry with backoff |
| `GeneralException` | `BrokerAPIError` | Log and retry |
| `DataException` | `DataNotAvailableError` | Check parameters |

## Python SDK Exception Handling

```python
from kiteconnect import exceptions as kite_exc

try:
    order = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NFO,
        tradingsymbol="NIFTY2522725000CE",
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=25,
        order_type=kite.ORDER_TYPE_MARKET,
        product=kite.PRODUCT_NRML
    )
except kite_exc.TokenException as e:
    # Re-authenticate
    logger.error(f"Auth error: {e.message}")
except kite_exc.InputException as e:
    # Fix parameters
    logger.error(f"Input error: {e.message}")
except kite_exc.OrderException as e:
    # Handle rejection
    logger.error(f"Order error: {e.message}")
except kite_exc.NetworkException as e:
    # Retry with backoff
    logger.error(f"Network error: {e.message}")
except kite_exc.GeneralException as e:
    # Generic server error
    logger.error(f"Server error: {e.message}")
```

## Retry Strategy

| Error Type | Strategy |
|-----------|----------|
| `TokenException` | Don't retry - re-authenticate |
| `InputException` | Don't retry - fix input |
| `OrderException` | Don't retry (usually) - check reason |
| `NetworkException` (429) | Retry after 1s, 2s, 4s (max 3 retries) |
| `NetworkException` (502/503) | Retry after 2s, 4s, 8s (max 3 retries) |
| `GeneralException` | Retry after 5s (max 2 retries) |

## Common Debugging Tips

1. **"Incorrect api_key or access_token"** - Most common error. Token expires daily ~6 AM. Must re-do OAuth.
2. **Check auth header format** - Must be `token api_key:access_token` (not `Bearer`)
3. **Order rejections** have detailed reasons in `message` - always log full response
4. **Rate limit errors** indicate code is not using rate_limiter - fix the calling code
5. **During market close** - Order and position endpoints may return empty data or errors
