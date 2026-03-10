# Common Broker Integration Gotchas

Shared pitfalls across all 6 supported brokers. Each entry references the relevant broker expert skill for details.

## 1. Token Expiry & Refresh

All brokers require periodic re-authentication, but patterns vary significantly.

| Broker | Token Lifetime | Refresh Method | Expert Skill |
|--------|---------------|----------------|--------------|
| Zerodha | ~6-8 hours | OAuth re-login (no refresh token) | `/zerodha-expert` |
| AngelOne | ~24 hours | Refresh token endpoint | `/angelone-expert` |
| Upstox | ~1 year | OAuth refresh token | `/upstox-expert` |
| Dhan | No expiry | Static token (manual rotation) | `/dhan-expert` |
| Fyers | ~24 hours | OAuth refresh token | `/fyers-expert` |
| Paytm | Varies (3 JWTs) | Each JWT has own refresh | `/paytm-expert` |

**Common mistake:** Assuming all brokers have refresh tokens. Zerodha requires full OAuth re-login.

## 2. Symbol Format Conversion

Each broker uses a different symbol format. The platform uses a canonical format internally.

| Broker | Format Example (NIFTY 25000 CE) | Notes |
|--------|-------------------------------|-------|
| Zerodha | `NIFTY2530625000CE` (exchange token) | Numeric instrument token for WebSocket |
| AngelOne | `NIFTY25MAR25000CE` (symbol token) | Different date format from Zerodha |
| Upstox | `NSE_FO|12345` (numeric instrument key) | Exchange prefix + pipe + numeric token (NOT symbol name) |
| Dhan | Security ID (numeric) | Separate security ID lookup required |
| Fyers | `NSE:NIFTY2530625000CE` | Exchange prefix with colon |
| Paytm | Script ID (numeric) | Similar to Dhan — numeric ID lookup |

**Common mistake:** Using one broker's symbol format with another's API. Always convert through `app.services.brokers.symbol_converter`.

## 3. Rate Limiting

Rate limits vary widely. Exceeding them can cause temporary bans.

| Broker | Order API | Data API | WebSocket | Expert Skill |
|--------|-----------|----------|-----------|--------------|
| Zerodha | 10 req/s | 10 req/s | 3000 tokens | `/zerodha-expert` |
| AngelOne | 10 req/s | 1 req/s (historical) | 9000 tokens | `/angelone-expert` |
| Upstox | 50 req/s | 50 req/s | 4096 tokens | `/upstox-expert` |
| Dhan | 25 req/s | 5 req/s | 100 instruments | `/dhan-expert` |
| Fyers | 10 req/s | 1 req/s (historical) | 200 symbols | `/fyers-expert` |
| Paytm | 10 req/s | 5 req/s | 200 instruments | `/paytm-expert` |

**Common mistake:** Not implementing per-broker rate limiting. Use `app.services.brokers.rate_limiter` which has broker-specific configurations.

## 4. WebSocket Reconnection

All brokers drop WebSocket connections periodically. Handling varies.

**Shared pattern:**
1. Detect disconnect (heartbeat timeout or explicit close frame)
2. Wait with exponential backoff (1s, 2s, 4s, max 30s)
3. Re-authenticate (some brokers require new auth token)
4. Re-subscribe to all instruments

**Broker-specific notes:**
- **Zerodha:** Sends explicit `close` frame. Auto-reconnect built into KiteTicker SDK.
- **AngelOne:** May silently stop sending ticks. Monitor heartbeat interval.
- **Upstox:** Binary protobuf format. Reconnect requires new auth token.
- **Dhan:** HTTP-based streaming (not true WebSocket for some endpoints).
- **Fyers:** Auto-reconnect in SDK. Check `on_error` callback for auth failures.
- **Paytm:** Least documented. Monitor for stale connections aggressively.

## 5. Price Unit Differences

**Critical:** Some brokers return prices in paisa (×100), others in rupees.

| Broker | Price Unit | Conversion |
|--------|-----------|------------|
| Zerodha | Rupees (decimal) | None needed |
| AngelOne | Rupees (decimal) | None needed |
| Upstox | Rupees (decimal) | None needed |
| Dhan | Rupees (decimal) | None needed |
| Fyers | Rupees (decimal) | None needed |
| Paytm | **Paisa (×100)** for some endpoints | Divide by 100 for display |

**Common mistake:** Displaying Paytm prices without conversion, showing ₹250000 instead of ₹2500.

## 6. Order Status Mapping

Each broker uses different status strings. Map to platform canonical statuses.

**Platform canonical statuses:** `PENDING`, `OPEN`, `COMPLETE`, `CANCELLED`, `REJECTED`, `TRIGGER_PENDING`

| Status | Zerodha | AngelOne | Upstox | Dhan | Fyers | Paytm |
|--------|---------|----------|--------|------|-------|-------|
| PENDING | `OPEN PENDING` | `pending` | `open pending` | `PENDING` | `6` | `PENDING` |
| COMPLETE | `COMPLETE` | `complete` | `complete` | `TRADED` | `2` | `EXECUTED` |
| CANCELLED | `CANCELLED` | `cancelled` | `cancelled` | `CANCELLED` | `1` | `CANCELLED` |
| REJECTED | `REJECTED` | `rejected` | `rejected` | `REJECTED` | `5` | `REJECTED` |

**Common mistake:** Comparing raw status strings across brokers. Always map through the order adapter's `normalize_status()`.

## 7. Market Hours & Session Handling

| Session | Timing | Notes |
|---------|--------|-------|
| Pre-open | 9:00-9:08 | Limited order types. Not all brokers support pre-open orders. |
| Normal | 9:15-15:30 | All brokers active |
| Post-close | 15:40-16:00 | AMO orders only for some brokers |
| After-hours | After 16:00 | AMO placement. Zerodha allows, others vary. |

**Common mistake:** Sending regular orders during pre-open/post-close sessions. Check `market_status` before order placement.

## 8. AngelOne Multi-Key Confusion (AG8001)

AngelOne uses 3 separate API keys, each for a different purpose. Using the wrong key returns `AG8001 Invalid Token`.

| `.env` Key | Purpose | Wrong usage symptom |
|-----------|---------|-------------------|
| `ANGEL_API_KEY` | Live market data (WebSocket, quotes) | AG8001 on historical data calls |
| `ANGEL_HIST_API_KEY` | Historical candle data only | AG8001 on live data calls |
| `ANGEL_TRADE_API_KEY` | Order execution only | AG8001 on data calls |

**This is the #1 AngelOne support issue.** See `/angelone-expert` for full details.

## Quick Debugging Checklist

When a broker integration fails:

1. **Check token expiry** — Is the auth token still valid?
2. **Check rate limits** — Are we exceeding the broker's limits?
3. **Check symbol format** — Is the symbol in the correct broker-specific format?
4. **Check market hours** — Is the market open for this order type?
5. **Check API key** — (AngelOne) Are we using the right key for this endpoint?
6. **Check price units** — (Paytm) Are prices in paisa or rupees?
7. **Check order status mapping** — Are we comparing canonical statuses?

## References

- Each gotcha links to the relevant broker expert skill for deep-dive details
- Architecture: `docs/architecture/broker-abstraction.md`
- Symbol converter: `backend/app/services/brokers/symbol_converter.py`
- Rate limiter: `backend/app/services/brokers/rate_limiter.py`
- Order adapter base: `backend/app/services/brokers/order/base_adapter.py`
