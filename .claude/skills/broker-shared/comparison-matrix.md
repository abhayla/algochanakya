# Cross-Broker Comparison Matrix

Comprehensive comparison of all 6 brokers supported by AlgoChanakya.

**Last Updated:** February 2026

---

## 1. Pricing

| Broker | Market Data Cost | Order Execution Cost | Total Monthly Cost | Notes |
|--------|-----------------|---------------------|-------------------|-------|
| **SmartAPI** (Angel One) | **FREE** | **FREE** | **₹0** | Default data source |
| **Kite Connect** (Zerodha) | ₹500/mo | **FREE** | **₹500** | Personal API free |
| **Upstox** | **FREE** | **FREE** | **₹0** | Extended token free |
| **Dhan** | **FREE** | **FREE** (25 F&O/mo) | **₹0-499** | ₹499/mo unlimited |
| **Fyers** | **FREE** | **FREE** | **₹0** | Virtual trading free |
| **Paytm Money** | **FREE** | **FREE** | **₹0** | Least mature |

**AlgoChanakya Default:** SmartAPI (data) + Kite (orders) = ₹0/month (using personal Kite API)

---

## 2. Authentication

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Auth Type** | Client+PIN+TOTP | OAuth redirect | OAuth redirect | API token | OAuth redirect | OAuth redirect |
| **Auto-Login** | **Yes** (auto-TOTP) | No (manual) | No (manual) | **Yes** (static token) | No (manual) | No (manual) |
| **Token Validity** | ~24h | ~24h (until 6AM) | ~24h (until 6:30AM) | Until revoked | Until midnight | ~24h |
| **Auto-Refresh** | **Yes** (refresh token) | **No** | Extended token (1yr) | N/A (long-lived) | **No** | **No** |
| **TOTP Required** | Yes (auto-generated) | Yes (manual on Zerodha) | Yes (manual) | No | Yes (manual) | Yes (manual) |
| **Token Types** | 3 (jwt, feed, refresh) | 2 (access, public) | 2 (access, extended) | 1 (access) | 1 (access) | 3 (access, public, read) |
| **Header Format** | `Bearer {jwt}` | `token api:access` | `Bearer {token}` | `access-token: {t}` | `{appid}:{token}` | `x-jwt-token: {t}` |

**Best for auto-login:** SmartAPI (auto-TOTP) or Dhan (static token)

---

## 3. REST Rate Limits

| Broker | General API | Order Placement | Historical Data | Quote API |
|--------|-------------|-----------------|-----------------|-----------|
| **SmartAPI** | **1/sec** | 10/sec | 1/sec | 1/sec |
| **Kite** | 3/sec | 10/sec | 3/sec | 1/sec |
| **Upstox** | **25/sec** | 25/sec | 6/sec | 25/sec |
| **Dhan** | 10/sec | 25/sec (multi-tier) | 10/sec | 10/sec |
| **Fyers** | 10/sec | 10/sec | **1/sec** | 10/sec |
| **Paytm** | 10/sec | 10/sec | 5/sec | 10/sec |

**Fastest:** Upstox (25/sec) | **Slowest:** SmartAPI (1/sec)

### AlgoChanakya rate_limiter.py Configuration

```python
BROKER_LIMITS = {
    "smartapi": 1,   # 1 req/sec
    "kite": 3,       # 3 req/sec
    "upstox": 25,    # 25 req/sec
    "dhan": 10,      # 10 req/sec
    "fyers": 10,     # 10 req/sec
    "paytm": 10,     # 10 req/sec
}
```

---

## 4. WebSocket Capabilities

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Max Tokens/Conn** | 3000 | 3000 | Plan-dependent | 100 (Ticker) | 200 | 200 |
| **Max Connections** | 3 | 3 | 1 | 5 | 1 | 1 |
| **Message Format** | Custom binary | Custom binary | **Protobuf** | Little Endian binary | **JSON** | JSON |
| **Price Unit** | **PAISE** | **PAISE** | RUPEES | RUPEES | RUPEES | RUPEES |
| **Auth Method** | feed_token + query | access_token + query | REST → URL | Header | SDK managed | public_access_token |
| **5-Level Depth** | Yes (Snap mode) | Yes (Full mode) | Yes (Full mode) | Yes (Quote mode) | Yes (DepthUpdate) | Yes (Full mode) |
| **20-Level Depth** | No | No | No | **Yes** | No | No |
| **200-Level Depth** | No | No | No | **Yes** (1 inst/conn) | No | No |
| **Option Greeks** | No | No | **Yes** | No | No | No |
| **Order Updates WS** | No | No | No | No | **Yes** (separate) | No |
| **Dual WS System** | No | No | No | No | **Yes** (Data+Order) | No |

**Best for depth:** Dhan (200-level) | **Best for Greeks:** Upstox | **Best capacity:** SmartAPI/Kite (3000 tokens)

---

## 5. Symbol Format

| Broker | Format | Options Example | Conversion to Canonical |
|--------|--------|----------------|------------------------|
| **SmartAPI** | `{SYM}{DDMONYY}{STRIKE}{CE\|PE}` | `NIFTY27FEB2525000CE` | Moderate (reformat date) |
| **Kite** | `{SYM}{YY}{M}{DD}{STRIKE}{CE\|PE}` | `NIFTY2522725000CE` | **Identity** (IS canonical) |
| **Upstox** | `{EXCH}_{SEG}\|{token}` | `NSE_FO\|12345` | High (token lookup) |
| **Dhan** | `{security_id}` (numeric) | `12345` | High (full ID lookup) |
| **Fyers** | `{EXCH}:{SYMBOL}` | `NSE:NIFTY2522725000CE` | **Low** (strip prefix) |
| **Paytm** | `{security_id}` + exchange | `12345` + `NSE` | High (full ID lookup) |

**Easiest conversion:** Fyers (strip prefix) → Kite (identity) | **Hardest:** Dhan/Upstox/Paytm (numeric IDs)

---

## 6. Price Units (PAISE vs RUPEES)

| Data Source | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|------------|---------|------|--------|------|-------|-------|
| **REST Quotes** | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES |
| **REST Historical** | **PAISE** | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES |
| **WebSocket** | **PAISE** | **PAISE** | RUPEES | RUPEES | RUPEES | RUPEES |
| **Instrument Master** | **PAISE** (strikes) | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES |

**Require paise→rupees conversion:** SmartAPI (WS, historical, strikes), Kite (WS only)
**No conversion needed:** Upstox, Dhan, Fyers, Paytm (all RUPEES everywhere)

---

## 7. Historical Data

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Min Interval** | 1 min | 1 min | 1 min | 1 min | 1 min | 1 min |
| **Max Interval** | Daily | Daily | Monthly | Daily | Daily | Daily |
| **Max Candles/Req** | ~2000 | ~2000 | ~2000 | ~2000 | ~2000 | ~1000 |
| **Max Date Range** | Varies by interval | Varies | Varies | Varies | Varies | Limited |
| **OI Included** | Yes | Yes (optional) | Yes | Yes | Yes | Limited |
| **Sort Order** | Ascending | Ascending | **Descending** | Ascending | Ascending | Ascending |

**Note:** Upstox returns candles in **descending** order (newest first). All others ascending.

---

## 8. Feature Support

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **GTT Orders** | Yes | Yes | No | Yes | Yes | No |
| **Basket Orders** | No | Yes (Iceberg) | No | No | Yes | No |
| **AMO Orders** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Bracket Orders** | Yes (ROBO) | Yes (CO) | Yes (CO/OC) | Yes | Yes | No |
| **Cover Orders** | No | Yes | Yes | Yes | Yes | No |
| **Margin Calculator** | Yes | Yes (separate API) | Yes | Yes | Yes | Limited |
| **Paper Trading** | No | No | No | No | **Yes** | No |
| **Extended Token** | No | No | **Yes** (1yr) | N/A | No | No |
| **Auto-TOTP** | **Yes** | No | No | N/A | No | No |
| **Option Greeks WS** | No | No | **Yes** | No | No | No |
| **200-Depth** | No | No | No | **Yes** | No | No |
| **Order Update WS** | No | No | No | No | **Yes** | No |

---

## 9. Python SDK

| Broker | Package | Install | Quality | Maintenance |
|--------|---------|---------|---------|-------------|
| **SmartAPI** | `smartapi-python` | `pip install smartapi-python` | Good | Active |
| **Kite** | `kiteconnect` | `pip install kiteconnect` | **Excellent** | Active |
| **Upstox** | `upstox-python-sdk` | `pip install upstox-python-sdk` | Good | Active |
| **Dhan** | `dhanhq` | `pip install dhanhq` | Good | Active |
| **Fyers** | `fyers-apiv3` | `pip install fyers-apiv3` | Good | Active |
| **Paytm** | `pyPMClient` | `pip install pyPMClient` | **Low** | Sporadic |

**Best SDK:** Kite (kiteconnect) - most mature, best documented, typed exceptions

---

## 10. Exchange Support

| Exchange | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|----------|---------|------|--------|------|-------|-------|
| **NSE** (Cash) | Yes | Yes | Yes | Yes | Yes | Yes |
| **BSE** (Cash) | Yes | Yes | Yes | Yes | Yes | Yes |
| **NFO** (F&O) | Yes | Yes | Yes | Yes | Yes | Limited |
| **BFO** (BSE F&O) | Yes | Yes | Yes | Yes | Yes | No |
| **MCX** (Commodity) | Yes | Yes | Yes | Yes | Yes | No |
| **CDS** (Currency) | Yes | Yes | Yes | Yes | Yes | No |

**Full exchange support:** SmartAPI, Kite, Upstox, Dhan, Fyers
**Limited:** Paytm (NSE, BSE, NFO only, limited F&O coverage)

---

## 11. AlgoChanakya Implementation Status

| Broker | Market Data Adapter | Order Adapter | Ticker | Symbol Converter | Factory |
|--------|-------------------|---------------|--------|-----------------|---------|
| **SmartAPI** | **✅ Complete** | 🚧 Planned | ✅ Legacy | ✅ Complete | ✅ Registered |
| **Kite** | **✅ Complete** | **✅ Complete** | ✅ Legacy | ✅ Identity | ✅ Registered |
| **Upstox** | 🚧 Planned | 🚧 Planned | - | - | Enum defined |
| **Dhan** | 🚧 Planned | 🚧 Planned | - | - | Enum defined |
| **Fyers** | 🚧 Planned | 🚧 Planned | - | - | Enum defined |
| **Paytm** | 🚧 Planned | 🚧 Planned | - | - | Enum defined |

### Key Codebase Files

| File | Contents |
|------|----------|
| `backend/app/services/brokers/base.py` | BrokerAdapter interface, UnifiedOrder/Position/Quote |
| `backend/app/services/brokers/factory.py` | Order execution factory |
| `backend/app/services/brokers/kite_adapter.py` | Kite order execution |
| `backend/app/services/brokers/market_data/market_data_base.py` | MarketDataBrokerAdapter, credentials, enums |
| `backend/app/services/brokers/market_data/factory.py` | Market data factory |
| `backend/app/services/brokers/market_data/smartapi_adapter.py` | SmartAPI market data |
| `backend/app/services/brokers/market_data/kite_adapter.py` | Kite market data |
| `backend/app/services/brokers/market_data/rate_limiter.py` | Rate limits (all 6 brokers) |
| `backend/app/services/brokers/market_data/symbol_converter.py` | Symbol conversion |
| `backend/app/services/brokers/market_data/token_manager.py` | Token mapping |
| `backend/app/services/brokers/market_data/exceptions.py` | Unified exceptions |

---

## 12. Recommendation Matrix

### Use Case → Best Broker

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| **Free market data** | SmartAPI or Upstox | Both free, SmartAPI has auto-TOTP |
| **Free orders** | Any (all free) | SmartAPI + Kite personal API |
| **Lowest latency** | Kite or Upstox | Highest rate limits |
| **Best documentation** | Kite | Most mature API |
| **Auto-login (no interaction)** | SmartAPI or Dhan | Auto-TOTP / static token |
| **Deep market depth** | Dhan | 200-level depth (unique) |
| **Real-time Greeks** | Upstox | Option Greeks via WS |
| **Paper trading** | Fyers | Built-in virtual trading |
| **Order update stream** | Fyers | Dedicated order WebSocket |
| **Widest exchange support** | SmartAPI/Kite/Upstox/Dhan/Fyers | All support 6 exchanges |
| **Multi-client apps** | Upstox | Extended token (1yr, read-only) |

### AlgoChanakya Default Setup

```
Market Data:  SmartAPI (FREE, auto-TOTP, no daily login)
Orders:       Kite Connect (FREE personal API, well-documented)
Total Cost:   ₹0/month
```

---

## 13. Quick Decision Table

**"Which broker should I implement next?"**

| Priority | Broker | Rationale |
|----------|--------|-----------|
| 1 (done) | SmartAPI + Kite | Default setup, real adapters exist |
| 2 (next) | **Upstox** | Most popular free alternative, Protobuf WS, Greeks |
| 3 | **Dhan** | 200-depth unique feature, static token |
| 4 | **Fyers** | Dual WS, virtual trading, low conversion complexity |
| 5 (last) | **Paytm** | Least mature, limited features |
