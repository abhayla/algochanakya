# Dhan API Error Codes and Rate Limits

## Overview

Dhan API returns standard HTTP status codes with JSON error bodies. The platform has a
**multi-tier rate limiting** system that is stricter than most other Indian brokers, especially
for order placement.

---

## HTTP Status Codes

| Status Code | Meaning                | Description                                         |
|-------------|------------------------|-----------------------------------------------------|
| 200         | OK                     | Request succeeded                                   |
| 201         | Created                | Resource created (e.g., order placed)                |
| 400         | Bad Request            | Invalid parameters, missing fields, validation error |
| 401         | Unauthorized           | Invalid or expired access token                      |
| 403         | Forbidden              | Token lacks required permissions / account restricted |
| 404         | Not Found              | Resource does not exist (order, position)            |
| 429         | Too Many Requests      | Rate limit exceeded                                  |
| 500         | Internal Server Error  | Dhan server error                                    |
| 502         | Bad Gateway            | Upstream exchange/gateway error                      |
| 503         | Service Unavailable    | Dhan service temporarily down                        |

---

## Error Response Format

All error responses follow this structure:

```json
{
    "status": "failure",
    "remarks": {
        "error_code": "DH-901",
        "error_type": "Invalid_Value",
        "error_message": "Invalid security ID provided"
    },
    "data": null
}
```

**Fields:**

| Field                    | Type   | Description                          |
|--------------------------|--------|--------------------------------------|
| `status`                 | string | `"success"` or `"failure"`           |
| `remarks.error_code`     | string | Dhan-specific error code             |
| `remarks.error_type`     | string | Category of error                    |
| `remarks.error_message`  | string | Human-readable error description     |
| `data`                   | any    | `null` on error, response on success |

---

## Dhan Error Codes by Category

### Authentication Errors (DH-1xx)

| Error Code | Error Type        | Message                              | Resolution                        |
|------------|-------------------|--------------------------------------|-----------------------------------|
| DH-100     | Invalid_Token     | Invalid access token                 | Regenerate token from dashboard   |
| DH-101     | Expired_Token     | Access token has expired             | Regenerate token from dashboard   |
| DH-102     | Missing_Token     | Access token not provided            | Add `access-token` header         |
| DH-103     | Invalid_Client    | Client ID mismatch                   | Verify client ID in request body  |
| DH-104     | Account_Blocked   | Trading account is blocked           | Contact Dhan support              |
| DH-105     | API_Disabled      | API access is disabled               | Enable API from Dhan dashboard    |

### Validation Errors (DH-9xx)

| Error Code | Error Type        | Message                              | Resolution                        |
|------------|-------------------|--------------------------------------|-----------------------------------|
| DH-901     | Invalid_Value     | Invalid security ID                  | Check security_id from instruments CSV |
| DH-902     | Invalid_Value     | Invalid exchange segment             | Use valid segment (NSE_EQ, etc.)  |
| DH-903     | Invalid_Value     | Invalid order type                   | Use LIMIT/MARKET/STOP_LOSS/SL_MARKET |
| DH-904     | Invalid_Value     | Invalid product type                 | Use CNC/INTRADAY/MARGIN/CO/BO    |
| DH-905     | Invalid_Value     | Invalid transaction type             | Use BUY or SELL                   |
| DH-906     | Invalid_Quantity  | Quantity not in lot size multiple    | Adjust quantity to lot size       |
| DH-907     | Invalid_Price     | Price out of circuit limits          | Adjust price within circuit range |
| DH-908     | Invalid_Value     | Invalid validity type                | Use DAY or IOC                    |
| DH-909     | Missing_Field     | Required field missing               | Check request body for all fields |
| DH-910     | Invalid_Value     | Invalid instrument for segment       | Verify security_id + segment combo |

### Order Errors (DH-2xx)

| Error Code | Error Type          | Message                            | Resolution                          |
|------------|---------------------|------------------------------------|-------------------------------------|
| DH-200     | Order_Failed        | Order rejected by exchange         | Check RMS limits, margin, circuit   |
| DH-201     | Order_Not_Found     | Order does not exist               | Verify order ID                     |
| DH-202     | Order_Not_Modifiable| Order cannot be modified           | Order already executed/cancelled    |
| DH-203     | Order_Not_Cancellable| Order cannot be cancelled         | Order already executed              |
| DH-204     | Insufficient_Margin | Insufficient margin for order      | Add funds or reduce quantity        |
| DH-205     | Freeze_Qty_Exceeded | Quantity exceeds freeze limit      | Use /orders/slicing endpoint        |
| DH-206     | Price_Band_Exceeded | Price outside allowed band         | Adjust price within limits          |
| DH-207     | Market_Closed       | Market is closed                   | Place AMO or wait for market hours  |
| DH-208     | Scrip_Suspended     | Instrument is suspended            | Cannot trade suspended instruments  |
| DH-209     | Max_Orders_Reached  | Maximum open orders limit reached  | Cancel some pending orders first    |

### Position/Holdings Errors (DH-3xx)

| Error Code | Error Type          | Message                            | Resolution                          |
|------------|---------------------|------------------------------------|-------------------------------------|
| DH-300     | No_Position         | No position found for conversion   | Check security_id and product type  |
| DH-301     | Convert_Failed      | Position conversion failed         | Check target product type validity  |
| DH-302     | Insufficient_Qty    | Quantity exceeds available position | Reduce conversion quantity          |

### Rate Limit Errors (DH-4xx)

| Error Code | Error Type          | Message                            | Resolution                          |
|------------|---------------------|------------------------------------|-------------------------------------|
| DH-400     | Rate_Limit          | Per-second rate limit exceeded     | Wait 1 second, retry               |
| DH-401     | Rate_Limit          | Per-minute rate limit exceeded     | Wait and spread requests            |
| DH-402     | Rate_Limit          | Per-hour rate limit exceeded       | Reduce order frequency              |
| DH-403     | Rate_Limit          | Daily rate limit exceeded          | Cannot place more orders today      |
| DH-404     | Rate_Limit          | API rate limit exceeded            | General API throttling, backoff     |

---

## Rate Limits

### Order Rate Limits (Multi-Tier)

Dhan enforces **four tiers** of order rate limits. Exceeding any tier returns HTTP 429.

| Tier      | Limit            | Window    | Reset                          |
|-----------|------------------|-----------|--------------------------------|
| Per-second| 25 orders/sec    | 1 second  | Rolling window                 |
| Per-minute| 250 orders/min   | 1 minute  | Rolling window                 |
| Per-hour  | 500 orders/hr    | 1 hour    | Rolling window                 |
| Per-day   | 5000 orders/day  | 1 day     | Midnight IST reset             |

**These limits include:** Place + Modify + Cancel. Each operation counts toward all tiers.

### API Rate Limits (General)

| Endpoint Category     | Rate Limit                     | Notes                           |
|-----------------------|--------------------------------|---------------------------------|
| Market Data (LTP)     | 10 requests/second             | Per access token                |
| Market Data (Quote)   | 5 requests/second              | Heavier payload                 |
| Historical Data       | 5 requests/second              | Per access token                |
| Orders (Place/Modify) | See multi-tier above           | Strictest limits                |
| Orders (Query)        | 10 requests/second             | Read-only, more lenient         |
| Positions/Holdings    | 10 requests/second             | Read-only                       |
| Profile/Margins       | 5 requests/second              | Lightweight                     |

### Rate Limit Headers

Dhan may include rate limit information in response headers:

```
X-RateLimit-Limit: 25
X-RateLimit-Remaining: 22
X-RateLimit-Reset: 1707820800
```

---

## AlgoChanakya Exception Mapping

### Exception Classes

Map Dhan errors to AlgoChanakya's unified exception hierarchy:

```python
from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
    InvalidRequestError,
    BrokerUnavailableError,
    InstrumentNotFoundError,
)

# Additional order-specific exceptions
from app.services.brokers.exceptions import (
    OrderRejectedError,
    InsufficientMarginError,
    OrderNotFoundError,
    MarketClosedError,
)
```

### Error Handler Implementation

```python
class DhanErrorHandler:
    """Map Dhan API errors to AlgoChanakya exceptions."""

    # HTTP status -> exception mapping
    STATUS_MAP = {
        401: AuthenticationError,
        403: PermissionDeniedError,
        429: RateLimitError,
        500: BrokerUnavailableError,
        502: BrokerUnavailableError,
        503: BrokerUnavailableError,
    }

    # Dhan error code -> (exception_class, retry_eligible)
    ERROR_CODE_MAP = {
        # Auth
        "DH-100": (AuthenticationError, False),
        "DH-101": (AuthenticationError, False),
        "DH-102": (AuthenticationError, False),
        "DH-103": (AuthenticationError, False),
        "DH-104": (PermissionDeniedError, False),
        "DH-105": (PermissionDeniedError, False),

        # Validation
        "DH-901": (InvalidRequestError, False),
        "DH-902": (InvalidRequestError, False),
        "DH-903": (InvalidRequestError, False),
        "DH-906": (InvalidRequestError, False),
        "DH-907": (InvalidRequestError, False),
        "DH-910": (InstrumentNotFoundError, False),

        # Orders
        "DH-200": (OrderRejectedError, False),
        "DH-201": (OrderNotFoundError, False),
        "DH-204": (InsufficientMarginError, False),
        "DH-205": (InvalidRequestError, False),  # Use /orders/slicing
        "DH-207": (MarketClosedError, False),

        # Rate limits (all retry-eligible)
        "DH-400": (RateLimitError, True),
        "DH-401": (RateLimitError, True),
        "DH-402": (RateLimitError, True),
        "DH-403": (RateLimitError, False),  # Daily limit -- no retry today
        "DH-404": (RateLimitError, True),
    }

    @classmethod
    def handle(cls, status_code: int, response_body: dict) -> None:
        """Raise appropriate AlgoChanakya exception for Dhan error."""
        remarks = response_body.get("remarks", {})
        error_code = remarks.get("error_code", "")
        error_message = remarks.get("error_message", "Unknown Dhan error")

        # Try error code first (more specific)
        if error_code in cls.ERROR_CODE_MAP:
            exc_class, retryable = cls.ERROR_CODE_MAP[error_code]
            raise exc_class(
                broker="dhan",
                message=f"[{error_code}] {error_message}",
                retryable=retryable,
            )

        # Fall back to HTTP status
        if status_code in cls.STATUS_MAP:
            raise cls.STATUS_MAP[status_code](
                broker="dhan",
                message=error_message,
            )

        # Generic error
        raise BrokerUnavailableError(
            broker="dhan",
            message=f"Unexpected error ({status_code}): {error_message}",
        )
```

---

## Rate Limiter Configuration

### Integration with AlgoChanakya RateLimiter

Configure the Dhan rate limiter in the market data adapter:

```python
from app.services.brokers.market_data.rate_limiter import RateLimiter

# Dhan rate limiter configuration
DHAN_RATE_LIMITS = {
    "market_data_ltp": {"requests": 10, "period": 1},      # 10/sec
    "market_data_quote": {"requests": 5, "period": 1},     # 5/sec
    "historical": {"requests": 5, "period": 1},            # 5/sec
    "orders_read": {"requests": 10, "period": 1},          # 10/sec
    "orders_write_sec": {"requests": 25, "period": 1},     # 25/sec
    "orders_write_min": {"requests": 250, "period": 60},   # 250/min
    "orders_write_hr": {"requests": 500, "period": 3600},  # 500/hr
    "orders_write_day": {"requests": 5000, "period": 86400},# 5000/day
}

rate_limiter = RateLimiter(broker="dhan", limits=DHAN_RATE_LIMITS)
```

### Retry Strategy for Rate Limits

```python
import asyncio
from typing import Callable, Any

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """Retry a Dhan API call with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError as e:
            if not e.retryable or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
    raise RateLimitError(broker="dhan", message="Max retries exceeded")
```

---

## Comparison: Rate Limits Across Brokers

| Broker        | Order Limit (per sec) | Order Limit (per day) | Data Limit (per sec) |
|---------------|----------------------|----------------------|---------------------|
| **Dhan**      | 25                   | 5,000                | 10                  |
| Zerodha Kite  | 10                   | 1,000 (modify/cancel)| 10                  |
| Angel SmartAPI| 1                    | Not specified        | 1                   |
| Upstox        | 10                   | 10,000               | 30                  |

**Key takeaway:** Dhan has generous per-second limits (25/sec) but a moderate daily cap (5000/day).
The multi-tier system (sec/min/hr/day) is unique to Dhan.

---

## WebSocket Error Handling

WebSocket disconnections have specific codes:

| Disconnect Code | Meaning                              | Action                          |
|-----------------|--------------------------------------|---------------------------------|
| 805             | Access token expired/invalid         | Re-authenticate, reconnect      |
| 806             | Maximum connections exceeded (5)     | Close unused connections first   |
| 807             | Maximum subscriptions exceeded       | Unsubscribe from some instruments|
| 808             | Server maintenance                   | Wait and retry with backoff     |
| 809             | Invalid subscription request         | Fix subscription message format |

These are sent as a binary frame with response code 50 (disconnect message) before the connection
is closed by the server.

```python
def handle_ws_disconnect(data: bytes) -> None:
    """Handle Dhan WebSocket disconnect message."""
    response_code = struct.unpack('<H', data[0:2])[0]
    if response_code == 50:
        disconnect_code = struct.unpack('<H', data[2:4])[0]
        if disconnect_code == 805:
            raise AuthenticationError(broker="dhan", message="WS token expired")
        elif disconnect_code == 806:
            raise ConnectionError("Max WS connections exceeded (5)")
        elif disconnect_code == 807:
            raise ConnectionError("Max WS subscriptions exceeded")
```
