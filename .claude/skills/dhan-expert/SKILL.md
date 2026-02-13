---
name: dhan-expert
description: Dhan API expert. Consult for authentication, endpoints, WebSocket,
  error codes, rate limits, symbol format, and adapter guidance for AlgoChanakya.
---

# Dhan API Expert

Dhan offers a modern REST API with unique features: **200-level market depth** (unique in India), **Little Endian binary WebSocket**, and **security_id-based** instrument identification (numeric IDs only). Dhan provides 25 free F&O trades/month or unlimited at ₹499/month. It's a planned broker for AlgoChanakya. Key differentiator: deepest market depth data and multi-tier rate limiting system.

## When to Use

- Implementing the Dhan market data or order execution adapter
- Debugging Dhan API errors or authentication issues
- Understanding Dhan's security_id format (numeric-only, no string symbols)
- Working with Little Endian binary WebSocket (unique `struct.unpack('<...')`)
- Understanding 20-depth and 200-depth market data
- Comparing Dhan capabilities with other brokers
- Auditing code that calls Dhan API for correctness

## API Overview

| Property | Value |
|----------|-------|
| **Official Docs** | https://dhanhq.co/docs/v2/ |
| **API Version** | v2 |
| **Python SDK** | `dhanhq` (`pip install dhanhq`) |
| **Pricing** | FREE (25 F&O trades/mo) or ₹499/mo unlimited |
| **REST Base URL** | `https://api.dhan.co/v2` |
| **WebSocket URL** | `wss://api-feed.dhan.co` |
| **Auth Method** | API access token (from web dashboard) |
| **Token Validity** | Until manually revoked or regenerated |

## Authentication Flow

Dhan uses a simple **API token** model - no OAuth redirect needed.

### Step-by-Step

```
1. Login to Dhan web dashboard (https://trade.dhan.co)
2. Navigate to API settings
3. Generate access_token (long-lived)
4. Use token in all API calls: access-token: {token}
```

### Auth Header

```
access-token: {access_token}
Content-Type: application/json
```

**Note:** Header name is `access-token` (hyphenated, lowercase), NOT `Authorization: Bearer`.

See [auth-flow.md](./references/auth-flow.md) for complete details.

## Key Endpoints Quick Reference

| Category | Method | Endpoint | Notes |
|----------|--------|----------|-------|
| **Profile** | GET | `/v2/clients/{client_id}` | User details |
| **Margins** | GET | `/v2/fundlimit` | Fund limits |
| **Quote** | POST | `/v2/marketfeed/ltp` | LTP for instruments |
| **OHLC** | POST | `/v2/marketfeed/ohlc` | OHLC data |
| **Depth (20)** | POST | `/v2/marketfeed/quote` | 20-level depth |
| **Historical** | GET | `/v2/charts/historical` | OHLCV candles |
| **Intraday** | GET | `/v2/charts/intraday` | Today's candles |
| **Place Order** | POST | `/v2/orders` | Place order |
| **Modify Order** | PUT | `/v2/orders/{order_id}` | Modify pending |
| **Cancel Order** | DELETE | `/v2/orders/{order_id}` | Cancel pending |
| **Orders** | GET | `/v2/orders` | All orders |
| **Positions** | GET | `/v2/positions` | Current positions |
| **Holdings** | GET | `/v2/holdings` | Portfolio holdings |
| **Instruments** | Download | CSV from Dhan website | Instrument master |

See [endpoints-catalog.md](./references/endpoints-catalog.md) for complete schemas.

## Symbol Format (security_id)

### Numeric IDs Only

Dhan uses **numeric security_id** values. There are NO string trading symbols in the API.

**Examples:**

| Instrument | security_id | exchange_segment |
|-----------|-------------|-----------------|
| NIFTY 50 | `13` | `IDX_I` |
| NIFTY BANK | `25` | `IDX_I` |
| NIFTY 25000 CE | `12345` | `NSE_FNO` |
| Reliance | `2885` | `NSE_EQ` |

### Exchange Segments

| Segment | Code | Description |
|---------|------|-------------|
| `NSE_EQ` | `NSE_EQ` | NSE Cash |
| `NSE_FNO` | `NSE_FNO` | NSE F&O |
| `BSE_EQ` | `BSE_EQ` | BSE Cash |
| `BSE_FNO` | `BSE_FNO` | BSE F&O |
| `MCX_COMM` | `MCX_COMM` | MCX Commodities |
| `IDX_I` | `IDX_I` | Indices |

### Canonical Conversion

Conversion is **high complexity** because Dhan uses only numeric IDs:

```python
from app.services.brokers.market_data.token_manager import token_manager

# security_id → Canonical
canonical = await token_manager.get_canonical_symbol(12345, "dhan")

# Canonical → security_id
security_id = await token_manager.get_broker_token("NIFTY2522725000CE", "dhan")
```

See [symbol-format.md](./references/symbol-format.md) for instrument CSV format.

## WebSocket Protocol (Little Endian Binary)

### Unique: Little Endian

Dhan is the **only Indian broker** using Little Endian byte order (`struct.unpack('<...')`). All others use Big Endian.

### Connection

```python
import websocket
ws = websocket.WebSocketApp(
    "wss://api-feed.dhan.co",
    header={"access-token": access_token},
    on_message=on_message
)
```

### Subscription Modes

| Mode | Description | Data |
|------|-------------|------|
| **Ticker** | LTP + change | ~20 bytes |
| **Quote** | OHLC + volume + OI + 20-depth | ~500 bytes |
| **Full** | All quote data + timestamps | ~700 bytes |
| **20-Depth** | 20-level market depth | Default for Quote mode |
| **200-Depth** | 200-level depth | **1 instrument/connection** (unique in India) |

### WebSocket Limits

| Limit | Value |
|-------|-------|
| Max instruments per connection | **100** (Ticker), **50** (Quote), **1** (200-Depth) |
| Max connections | **5** |
| Message format | Little Endian binary |
| 200-Depth limit | **1 instrument per connection** |

See [websocket-protocol.md](./references/websocket-protocol.md) for byte offsets and parsing.

## Rate Limits (Multi-Tier)

| Resource | Limit | Window |
|----------|-------|--------|
| Order placement | **25/second** | Per second |
| Order placement | **250/minute** | Per minute |
| Order placement | **500/hour** | Per hour |
| Order placement | **5000/day** | Per day |
| REST API (general) | **10/second** | Per second |
| WebSocket | Unlimited ticks | After subscription |
| Historical data | **10/second** | Per second |

**AlgoChanakya Configuration:** `rate_limiter.py` sets `"dhan": 10` (10 req/sec).

## Price Normalization

| Data Source | Price Unit | Action Required |
|------------|------------|-----------------|
| **REST API** | **RUPEES** | No conversion |
| **WebSocket** | **RUPEES** | No conversion (prices as float) |
| **Historical** | **RUPEES** | No conversion |

Dhan returns all prices in RUPEES. No paise conversion needed.

## AlgoChanakya Integration

### Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Market Data Adapter | **🚧 Planned** | Not yet created |
| Order Execution Adapter | **🚧 Planned** | Not yet created |
| Credentials Dataclass | **✅ Defined** | `market_data_base.py` (`DhanMarketDataCredentials`) |
| Enum Registration | **✅ Defined** | `MarketDataBrokerType.DHAN` |
| Rate Limiter Config | **✅ Set** | `rate_limiter.py`: `"dhan": 10` |

## Common Gotchas

1. **Little Endian binary** - Use `struct.unpack('<...')` NOT `'>'`. This is unique among Indian brokers.

2. **Numeric IDs only** - No string trading symbols. Must maintain instrument mapping table.

3. **Auth header format** - `access-token: {token}` (hyphenated, lowercase). Not `Authorization: Bearer`.

4. **200-Depth limit** - Only 1 instrument per connection. Need 5 connections for 5 instruments.

5. **Multi-tier order limits** - Check all 4 limits (sec/min/hour/day). Can hit daily limit even within rate limit.

6. **Free tier limit** - 25 F&O trades/month free. After that, orders fail unless subscribed.

7. **Instrument CSV download** - Must download from Dhan website manually or via undocumented URL.

8. **Exchange segment format** - Uses `NSE_FNO` not `NFO`. Different from Kite/SmartAPI naming.

## Error Codes Quick Reference

| HTTP Status | Error | Cause | Retryable |
|-------------|-------|-------|-----------|
| `400` | Bad Request | Invalid parameters | No |
| `401` | Unauthorized | Invalid/expired token | No |
| `403` | Forbidden | Permissions issue | No |
| `429` | Rate Limited | Exceeded rate limit | Yes - backoff |
| `500` | Server Error | Dhan server issue | Yes - retry |

See [error-codes.md](./references/error-codes.md) for complete error catalog.

## References

- [Authentication Flow](./references/auth-flow.md) - API token setup
- [Endpoints Catalog](./references/endpoints-catalog.md) - All REST endpoints
- [WebSocket Protocol](./references/websocket-protocol.md) - Little Endian binary protocol
- [Error Codes](./references/error-codes.md) - Error code reference
- [Symbol Format](./references/symbol-format.md) - security_id format
- [Comparison Matrix](../broker-shared/comparison-matrix.md) - Cross-broker comparison
