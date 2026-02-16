---
name: upstox-expert
description: Use when implementing Upstox adapter, debugging Upstox API errors, understanding Upstox instrument_key format, or auditing code calling Upstox API. Upstox API expert for AlgoChanakya.
metadata:
  author: AlgoChanakya
  version: "1.0"
---

# Upstox API Expert

Upstox offers a modern API with OAuth 2.0 authentication, Protobuf-based WebSocket (MarketDataFeedV3), and a well-maintained Python SDK. API access costs **₹499/month** (₹499 + GST). It's a popular alternative to Kite Connect for both market data and order execution. Upstox is a planned broker for AlgoChanakya (adapter not yet implemented). Key differentiator: **extended token** for long-lived read-only access and **Protocol Buffers** for efficient WebSocket messaging.

## When to Use

- Implementing the Upstox market data or order execution adapter
- Debugging Upstox API errors or OAuth flow issues
- Understanding Upstox instrument_key format (`NSE_FO|12345`)
- Working with Protobuf-based WebSocket (MarketDataFeedV3)
- Comparing Upstox capabilities with other brokers
- Auditing code that calls Upstox API for correctness
- Writing tests that mock Upstox API responses

## When NOT to Use

- General broker abstraction questions (read docs/architecture/broker-abstraction.md instead)
- Cross-broker comparison (use broker-shared/comparison-matrix.md instead)
- SmartAPI/Kite issues (use smartapi-expert or kite-expert)
- Dhan/Fyers/Paytm issues (use their respective expert skills)

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://upstox.com/developer/api-documentation/ |
| **API Version** | v2 |
| **Python SDK** | `upstox-python-sdk` (`pip install upstox-python-sdk`) |
| **Pricing** | **₹499/month** (₹499 + GST) for API access (market data + orders) |
| **REST Base URL** | `https://api.upstox.com/v2` |
| **WebSocket URL** | Authorized URL via REST endpoint |
| **Auth Method** | OAuth 2.0 (authorization_code grant) |
| **Token Validity** | access_token: until ~6:30 AM next day |

## Authentication Flow

Upstox uses standard **OAuth 2.0 authorization_code** flow with an optional **extended token** for long-lived access.

### Step-by-Step Authentication

```
1. Redirect user → https://api.upstox.com/v2/login/authorization/dialog
   ?client_id={api_key}&redirect_uri={redirect_url}&response_type=code
2. User logs in on Upstox website
3. Upstox redirects → {redirect_url}?code={authorization_code}
4. POST /v2/login/authorization/token with code, client_id, client_secret, redirect_uri, grant_type
5. Response: { access_token, extended_token (if requested) }
6. Use access_token: Authorization: Bearer {access_token}
```

### Token Types

| Token | Purpose | Validity | Notes |
|-------|---------|----------|-------|
| `access_token` | Full API access | Until ~6:30 AM next day | Standard OAuth token |
| `extended_token` | Read-only access | 1 year (renewable) | For multi-client apps, market data only |

### Extended Token (Unique Feature)

The extended token allows **long-lived read-only access** without daily re-authentication:
- Valid for 1 year
- Read-only: market data, instruments, portfolio viewing
- Cannot place/modify/cancel orders
- Ideal for market data adapter (no daily login needed)

### Auth Header

```
Authorization: Bearer {access_token}
```

See [auth-flow.md](./references/auth-flow.md) for complete request/response examples.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Auth** | POST | `/v2/login/authorization/token` | Exchange auth code |
| **Profile** | GET | `/v2/user/profile` | User details |
| **Margins** | GET | `/v2/user/get-funds-and-margin` | Fund details |
| **Quote** | GET | `/v2/market-quote/quotes?instrument_key=` | Full quote |
| **LTP** | GET | `/v2/market-quote/ltp?instrument_key=` | LTP only |
| **OHLC** | GET | `/v2/market-quote/ohlc?instrument_key=` | OHLC data |
| **Historical** | GET | `/v2/historical-candle/{instrument_key}/{interval}/{to_date}` | OHLCV |
| **Intraday** | GET | `/v2/historical-candle/intraday/{instrument_key}/{interval}` | Today's candles |
| **Instruments** | GET | `/v2/market-quote/instruments` | Instrument master |
| **Place Order** | POST | `/v2/order/place` | Place order |
| **Modify Order** | PUT | `/v2/order/modify` | Modify pending |
| **Cancel Order** | DELETE | `/v2/order/cancel?order_id=` | Cancel pending |
| **Orders** | GET | `/v2/order/retrieve-all` | All orders |
| **Positions** | GET | `/v2/portfolio/short-term-positions` | Positions |
| **Holdings** | GET | `/v2/portfolio/long-term-holdings` | Holdings |
| **WS Auth** | GET | `/v2/feed/market-data-feed/authorize` | Get authorized WS URL |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

## Symbol Format

### instrument_key Format

Upstox uses `instrument_key` in the format: `{EXCHANGE}_{SEGMENT}|{instrument_token}`

**Examples:**

| Instrument | instrument_key | Notes |
|-----------|---------------|-------|
| NIFTY 50 Index | `NSE_INDEX\|Nifty 50` | Index uses name |
| NIFTY 25000 CE | `NSE_FO\|12345` | F&O uses token |
| Reliance Equity | `NSE_EQ\|2885` | Equity uses token |
| NIFTY Future | `NSE_FO\|67890` | Future uses token |

### Exchange Segments

| Segment | Description |
|---------|-------------|
| `NSE_EQ` | NSE Equity |
| `NSE_FO` | NSE F&O |
| `NSE_INDEX` | NSE Indices |
| `BSE_EQ` | BSE Equity |
| `BSE_FO` | BSE F&O |
| `BSE_INDEX` | BSE Indices |
| `MCX_FO` | MCX Commodities |

### Canonical Conversion

```python
# Upstox instrument_key → Canonical (Kite)
# Requires instrument master lookup (token-based)
from app.services.brokers.market_data.token_manager import token_manager
canonical = await token_manager.get_canonical_symbol(12345, "upstox")
```

See [symbol-format.md](./references/symbol-format.md) for complete format details.

## WebSocket Protocol (Protobuf)

### MarketDataFeedV3

Upstox uses **Protocol Buffers** for WebSocket messages - unique among Indian brokers.

### Connection Flow

1. Get authorized WS URL: `GET /v2/feed/market-data-feed/authorize`
2. Connect to the returned URL
3. Subscribe via binary Protobuf message

### Subscription Request (Protobuf)

```python
import upstox_client
from google.protobuf import json_format

# Create subscription request
request = {
    "guid": "unique-id",
    "method": "sub",
    "data": {
        "mode": "full",  # "ltpc", "full", or "option_greeks"
        "instrumentKeys": ["NSE_FO|12345", "NSE_INDEX|Nifty 50"]
    }
}
```

### Modes

| Mode | Description | Data Included |
|------|-------------|---------------|
| `ltpc` | LTP + Change | LTP, close, change, change% |
| `full` | Full quote | OHLC, volume, OI, depth, bid/ask |
| `option_greeks` | Greeks + quote | Full + delta, gamma, theta, vega, IV |

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max instruments per connection | **Varies by plan** |
| Max connections | **1 per access_token** |
| Message format | **Protocol Buffers (binary)** |
| Heartbeat | Automatic |

See [websocket-protocol.md](./references/websocket-protocol.md) for Protobuf schema and parsing.

## Rate Limits

| Endpoint Type | Limit | Notes |
|---------------|-------|-------|
| REST API (general) | **25 requests/second** | Per access_token |
| Order placement | **25 orders/second** | Per user |
| Historical data | **6 requests/second** | Separate limit |
| WebSocket | **Unlimited ticks** | After subscription |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"upstox": 25` (25 req/sec).

## Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** (all endpoints) | **RUPEES** | No conversion |
| **WebSocket** (all modes) | **RUPEES** | No conversion |
| **Historical data** | **RUPEES** | No conversion |

**Upstox always returns prices in RUPEES.** No paise conversion needed (unlike SmartAPI and Kite WS).

## AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **🚧 Planned** | Not yet created |
| Order Execution Adapter | **🚧 Planned** | Not yet created |
| Credentials Dataclass | **✅ Defined** | `market_data_base.py` (`UpstoxMarketDataCredentials`) |
| Enum Registration | **✅ Defined** | `MarketDataBrokerType.UPSTOX` |
| Rate Limiter Config | **✅ Set** | `rate_limiter.py`: `"upstox": 25` |

### Planned Integration

```python
# Future: Market data via adapter
from app.services.brokers.market_data.factory import get_market_data_adapter
adapter = get_market_data_adapter("upstox", credentials, db)
quote = await adapter.get_quote(["NIFTY2522725000CE"])  # Returns UnifiedQuote
```

## Common Gotchas

1. **₹499/month subscription required** - Unlike SmartAPI (free) or Paytm (free), Upstox charges ₹499 + GST monthly for API access. Not free despite early marketing.

2. **Protobuf dependency** - WebSocket requires `protobuf` package and compiled .proto schemas. Different from JSON or raw binary used by other brokers.

3. **instrument_key format** - Not a simple symbol string. Includes exchange segment and uses `|` separator. Must look up in instrument master.

3. **Extended token is read-only** - Cannot place orders with extended token. Need full access_token for trading.

4. **WS URL from REST** - Must call REST endpoint to get authorized WebSocket URL. Cannot hardcode WS URL.

5. **One WS connection per token** - Unlike Kite/SmartAPI (3 connections), Upstox allows only 1 WebSocket connection per access_token.

6. **Prices always in RUPEES** - No paise conversion needed (simpler than SmartAPI/Kite). Don't accidentally divide by 100.

7. **Historical data structure** - Returns candles in descending order (newest first). Other brokers return ascending.

8. **OAuth redirect** - Like Kite, requires user interaction. Cannot be automated like SmartAPI auto-TOTP.

9. **Index instrument_key** - Indices use name string (`NSE_INDEX|Nifty 50`) not numeric token. Different from other instruments.

10. **Option Greeks mode** - Upstox is the only broker providing Greeks via WebSocket (delta, gamma, theta, vega). Useful for real-time Greek monitoring.

## Error Codes Quick Reference

| HTTP Status | Error Type | Cause | Retryable |
|-------------|-----------|-------|-----------|
| `400` | `UDAPI100` | Bad request / invalid params | No |
| `401` | `UDAPI100` | Invalid/expired token | No - re-auth |
| `403` | `UDAPI100` | Insufficient permissions | No |
| `429` | `UDAPI100` | Rate limit exceeded | Yes - backoff |
| `500` | `UDAPI100` | Server error | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

## Related Skills

For cross-broker work, consult these complementary skills:

| Skill | When to Use |
|-------|-------------|
| `/smartapi-expert` | Reference implementation — SmartAPI adapter is the model for new market data adapters |
| `/kite-expert` | Order execution reference — Kite adapter is the model for new order adapters |
| `/dhan-expert` | Compare unique WS features — Dhan has 200-depth, Upstox has Greeks via WS |
| `/auto-verify` | After any Upstox adapter change — run verification immediately |
| `/docs-maintainer` | After adapter changes — update feature registry, comparison matrix, CHANGELOG |

**Cross-Broker Comparison:** See [comparison-matrix.md](../broker-shared/comparison-matrix.md) for pricing, rate limits, WebSocket capabilities, and symbol format differences across all 6 brokers.

## References

- [Authentication Flow](./references/auth-flow.md) - OAuth 2.0 flow + extended token
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints with schemas
- [WebSocket Protocol](./references/websocket-protocol.md) - Protobuf-based MarketDataFeedV3
- [Error Codes](./references/error-codes.md) - Complete error code reference
- [Symbol Format](./references/symbol-format.md) - instrument_key format and conversion
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
