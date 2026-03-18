# Cross-Broker Comparison Matrix

Comprehensive comparison of all 6 brokers supported by AlgoChanakya.

**Last Updated:** 2026-02-25 (updated to match all broker skill v2.5 overhauls)

> **Broker Expert Skills:** For API-specific guidance (auth flows, error codes, WebSocket protocols, symbol formats), consult the dedicated broker expert skills:
> - `/angelone-expert` — Angel One SmartAPI (default market data, auto-TOTP, binary WS, paise pricing, static IP required Aug 2025)
> - `/zerodha-expert` — Zerodha Kite Connect (default orders, OAuth, canonical symbol format, 10/sec rate limit)
> - `/upstox-expert` — Upstox (FREE, Protobuf WS, extended token, Option Greeks via WS, GTT, v3 API)
> - `/dhan-expert` — Dhan (static token, 200-level depth, Little Endian binary WS, Forever Orders, `availabelBalance` typo)
> - `/fyers-expert` — Fyers (FREE, 5-socket WS system, 5K symbols/conn, v3 SDK Nov 2023, daily 100K limit)
> - `/paytm-expert` — Paytm Money (FREE, 3-token OAuth, JSON WS, least mature API, BSE F&O added 2025)

---

## 1. Pricing

| Broker | Market Data Cost | Order Execution Cost | Total Monthly Cost | Notes |
|--------|-----------------|---------------------|-------------------|-------|
| **SmartAPI** (Angel One) | **FREE** | **FREE** | **₹0** | Default data source |
| **Kite Connect** (Zerodha) | ₹500/mo* | **FREE** | **₹0–500** | *Personal API free (orders only, no data) |
| **Upstox** | **FREE** | **FREE** | **₹0** | Changed to FREE in 2025. ₹10/order API brokerage till Mar 2026. |
| **Dhan** | **FREE**† | **FREE** | **₹0–499** | †25 F&O trades/mo OR ₹499/mo for Data API |
| **Fyers** | **FREE** | **FREE** | **₹0** | v3 SDK (Nov 2023), 5K symbols/conn |
| **Paytm Money** | **FREE** | **FREE** | **₹0** | Least mature. BSE F&O added 2025. |

**AlgoChanakya Default:** SmartAPI (data) + Kite Personal API (orders) = ₹0/month

**Corrections from previous version:**
- **Upstox:** Was incorrectly listed as ₹499/month. API is now **FREE** (changed in 2025).
- All 6 brokers are effectively ₹0 for API access.

**Notes:**
- **Kite Connect:** ₹500/month includes live market data + historical data (bundled since Feb 2025). Personal API is free but provides order execution only.
- **Upstox:** ₹10/order promotional API brokerage until Mar 2026, then standard ₹20/order applies. Plus plan (₹30/order) offers 5 WS connections + D30 depth.
- **Dhan:** Two-tier model — Trading APIs free, Data APIs require 25 F&O trades/month OR ₹499/month subscription.

---

## 2. Authentication

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Auth Type** | Client+PIN+TOTP | OAuth redirect | OAuth redirect | API token | OAuth redirect | OAuth redirect |
| **Auto-Login** | **Yes** (auto-TOTP) | No (manual) | **Yes** (auto-TOTP) | **Yes** (static token) | No (manual) | No (manual) |
| **Token Validity** | ~24h | ~24h (until 6AM) | ~24h (until ~6:30AM) or 1yr (extended) | Until revoked | Until **midnight IST** | ~24h |
| **Auto-Refresh** | **Yes** (refresh token, 15d) | **No** | Extended token (1yr, read-only) | N/A (long-lived) | **No** | **No** |
| **TOTP Required** | Yes (auto-generated) | Yes (manual on Zerodha) | Yes (auto-generated) | No | Yes (manual) | Yes (manual) |
| **Token Types** | 3 (jwt, feed, refresh) | 2 (access, public) | 2 (access, extended) | 1 (access) | 1 (access) | 3 (access, public_access, read_access) |
| **Header Format** | `Bearer {jwt}` | `token api:access` | `Bearer {token}` | `access-token: {t}` | `{appid}:{token}` | `x-jwt-token: {t}` |
| **IP Whitelist** | **Yes** (since Aug 2025) | No | **Yes** (app settings) | No | No | No |

**Best for auto-login:** SmartAPI (auto-TOTP), Upstox (auto-TOTP), or Dhan (static token)

**Key gotchas:**
- **SmartAPI:** Static IP registration required since Aug 2025 — 403 if not registered (up to 5 IPv4s)
- **Upstox:** IP whitelisting in My Apps dashboard — 403 Forbidden if not configured
- **Fyers:** `appIdHash` = SHA-256 of `app_id:app_secret` required for token exchange
- **Kite:** No refresh token — user must re-OAuth daily after ~6 AM expiry

---

## 3. REST Rate Limits

| Broker | General API | Order Placement | Historical Data | Notes |
|--------|-------------|-----------------|-----------------|-------|
| **SmartAPI** | **1/sec** | **20/sec** | 1/sec | Strictest REST; order limit increased from 10 in Feb 2025 |
| **Kite** | **10/sec** | 10/sec | 10/sec (max 60 days/req for minute) | Was incorrectly 3/sec in old docs |
| **Upstox** | **50/sec**, 500/min, 2000/30min | 50/sec | 50/sec | Multi-tier; multi-order APIs: 4/sec |
| **Dhan** | 10/sec | 10/sec, **250/min**, **1000/hr**, **7000/day** | 10/sec | Multi-tier order limits — check all 4 |
| **Fyers** | 10/sec | 10/sec | **1/sec** | Daily limit: **100,000 req/day** |
| **Paytm** | 10/sec | 10/sec | 5/sec | - |

**Fastest:** Upstox (50/sec) | **Slowest REST:** SmartAPI (1/sec)

### AlgoChanakya rate_limiter.py — Current vs Correct

```python
# CURRENT (some values incorrect):
BROKER_LIMITS = {
    "smartapi": 1,   # ✅ correct
    "kite": 3,       # ❌ WRONG — should be 10
    "upstox": 25,    # ❌ WRONG — should be 50
    "dhan": 10,      # ✅ correct
    "fyers": 10,     # ✅ correct
    "paytm": 10,     # ✅ correct
}

# CORRECTED:
BROKER_LIMITS = {
    "smartapi": 1,   # 1 req/sec
    "kite": 10,      # 10 req/sec (was 3 — incorrect)
    "upstox": 50,    # 50 req/sec (was 25 — incorrect)
    "dhan": 10,      # 10 req/sec
    "fyers": 10,     # 10 req/sec
    "paytm": 10,     # 10 req/sec
}
```

---

## 4. WebSocket Capabilities

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Max Tokens/Conn** | 3000 | 3000 | Basic:~1500, Plus:more | 100 (Ticker), 50 (Quote) | **5,000** | 200 |
| **Max Connections** | 3 | 3 | Basic:2, Plus:5 | **5** | 1 per socket type | 1 |
| **Message Format** | Custom binary | Custom binary | **Protobuf** | **Little Endian** binary | **JSON** | JSON |
| **Price Unit** | **PAISE** | **PAISE** | RUPEES | RUPEES | RUPEES | RUPEES |
| **5-Level Depth** | Yes (Snap mode) | Yes (Full mode) | Yes (Full mode) | Yes (Quote mode) | Yes (DepthUpdate) | Yes (Full mode) |
| **20-Level Depth** | No | No | No | **Yes** | No | No |
| **200-Level Depth** | No | No | No | **Yes** (1 inst/conn) | No | No |
| **D30 Depth** | No | No | **Yes** (Plus, 50/conn) | No | No | No |
| **Option Greeks** | No | No | **Yes** (option_greeks mode) | No | No | No |
| **Order Updates WS** | **Yes** (separate URL) | No | No | **Yes** (separate URL) | **Yes** (FyersOrderSocket) | No |
| **Position Updates WS** | No | No | **Yes** (Portfolio WS) | No | **Yes** (FyersPositionSocket) | No |
| **Trade Updates WS** | No | No | No | No | **Yes** (FyersTradeSocket) | No |
| **WS Socket Types** | 2 (data + order) | 1 | 2 (market + portfolio) | 2 (market + order) | **5** | 1 |

**Best for depth:** Dhan (200-level, unique in India)
**Best for Greeks:** Upstox (option_greeks WS mode)
**Best capacity:** Fyers (5,000 tokens/conn)
**Best WS ecosystem:** Fyers (5 socket types)
**Unique binary format:** Dhan — only Little Endian broker (use `struct.unpack('<...')`)

---

## 5. Symbol Format

| Broker | Format | Options Example | Conversion Complexity |
|--------|--------|----------------|----------------------|
| **SmartAPI** | `{SYM}{DDMONYY}{STRIKE}{CE\|PE}` | `NIFTY27FEB2525000CE` | Moderate (reformat date) |
| **Kite** | `{SYM}{YY}{M}{DD}{STRIKE}{CE\|PE}` | `NIFTY2522725000CE` | **Identity** (IS canonical) |
| **Upstox** | `{EXCH}_{SEG}\|{token}` | `NSE_FO\|12345` | High (token lookup, `\|` URL-encode as `%7C`) |
| **Dhan** | `{security_id}` (numeric only) | `12345` + segment `NSE_FNO` | High (full ID lookup) |
| **Fyers** | `{EXCH}:{SYMBOL}` | `NSE:NIFTY2522725000CE` | **Low** (strip prefix) |
| **Paytm** | `{security_id}` + exchange | `12345` + `NSE` | High (full ID lookup) |

**Easiest conversion:** Fyers (strip `:` prefix) → Kite (identity)
**Hardest:** Dhan, Upstox, Paytm (numeric IDs requiring instrument master lookup)

**Special format notes:**
- **Fyers equities:** Need `-EQ` suffix (`NSE:RELIANCE-EQ`). Indices need `-INDEX` suffix (`NSE:NIFTY50-INDEX`).
- **Upstox indices:** Use name string, not token (`NSE_INDEX|Nifty 50`).
- **Dhan segment codes:** `NSE_FNO` (not `NFO`), `IDX_I` for indices.

---

## 6. Price Units (PAISE vs RUPEES)

| Data Source | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|------------|---------|------|--------|------|-------|-------|
| **REST Quotes** | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES |
| **REST Historical** | **PAISE** | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES |
| **WebSocket** | **PAISE** | **PAISE** | RUPEES | RUPEES | RUPEES | RUPEES |
| **Instrument Master** | **PAISE** (strikes) | RUPEES | RUPEES | RUPEES | RUPEES | RUPEES |
| **Option Chain** | RUPEES | N/A | RUPEES | RUPEES | RUPEES | RUPEES |

**Require paise→rupees conversion:** SmartAPI (WS, historical, instrument strikes), Kite (WS only)
**No conversion needed:** Upstox, Dhan, Fyers, Paytm (all RUPEES everywhere)

---

## 7. Historical Data

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **Min Interval** | 1 min | 1 min | 1 min | 1 min | 1 min | 1 min |
| **Max Interval** | Daily | Daily | Monthly | Daily | Daily | Daily |
| **Max Range (minute)** | Varies | **60 days/req** | Varies | Varies | Varies | Limited |
| **Years Available** | Varies | **10 years** (bundled Feb 2025) | Varies | Varies | Varies | Limited |
| **Rate Limit** | 1/sec | 10/sec | 50/sec | 10/sec | **1/sec** | 5/sec |
| **OI Included** | Yes | Yes (optional) | Yes | Yes | Yes | Limited |
| **Sort Order** | Ascending | Ascending | **Descending** | Ascending | Ascending | Ascending |

**Note:** Upstox returns candles in **descending** order (newest first). All others ascending. Reverse before processing.

---

## 8. Feature Support

| Feature | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|---------|---------|------|--------|------|-------|-------|
| **GTT Orders** | Yes (API) | Yes (API) | Yes (API, v3) | Yes ("Forever Orders") | Partial (API unclear, WS broken) | Yes (API, sparse docs) |
| **Option Chain API** | Yes (with Greeks) | No (batch quotes only, no Greeks) | Yes (with Greeks + PoP) | Yes (with Greeks) | Yes (with Greeks incl. Rho/Vanna/Charm) | Yes (Heckyl Greeks) |
| **Basket/Iceberg Orders** | No | Yes (Iceberg) | No | No | Yes | No |
| **AMO Orders** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Bracket Orders** | Yes (ROBO) | Yes (CO) | Yes (CO/OC) | Yes | Yes | No |
| **Cover Orders** | No | Yes | Yes | Yes | Yes | No |
| **Margin Calculator** | Yes | Yes | Yes | Yes | Yes | Limited |
| **Paper/Virtual Trading** | No | No | **Yes** (Sandbox, Jan 2025) | No | **Yes** (built-in) | No |
| **Extended/Long Token** | No | No | **Yes** (1yr, read-only) | N/A (permanent) | No | No |
| **Auto-TOTP Login** | **Yes** | No | **Yes** | N/A | No | No |
| **Option Greeks WS** | No | No | **Yes** | No | No | No |
| **200-Level Depth** | No | No | No | **Yes** | No | No |
| **HTTP Webhooks** | No | No | **Yes** (order POST) | **Yes** (Postback) | No | No |
| **Order Update WS** | **Yes** | No | No | **Yes** | **Yes** (OrderSocket) | No |
| **MCP Integration** | No | No | **Yes** (read-only) | No | No | No |
| **BSE F&O** | Yes | Yes | Yes | Yes | Yes | **Added 2025** |

**GTT implementations in AlgoChanakya:** None yet (all 6 adapters use standard orders only)
**Option chain in AlgoChanakya:** SmartAPI only (platform default)

---

## 9. Python SDK

| Broker | Package | Version | Quality | Maintenance | Notes |
|--------|---------|---------|---------|-------------|-------|
| **SmartAPI** | `smartapi-python` | v1.5.5 | Good | Active | Feb 2025 update |
| **Kite** | `kiteconnect` | v5.0.1 | **Excellent** | Active | Most mature, typed exceptions |
| **Upstox** | `upstox-python-sdk` | Latest | Good | Active | 6 SDKs (Python/JS/.NET/Java/C#/PHP) |
| **Dhan** | `dhanhq` | v2.1.0 | Good | Active | - |
| **Fyers** | `fyers-apiv3` | v3.1.7 | Good | Active | Released Nov 2023 |
| **Paytm** | `pyPMClient` | Unknown | **Low** | **Sporadic** (last Jul 2024) | May need raw HTTP calls |

**Best SDK:** Kite (`kiteconnect`) — most mature, best documented, typed exceptions
**Worst SDK:** Paytm (`pyPMClient`) — low maintenance, may need workarounds

---

## 10. Exchange Support

| Exchange | SmartAPI | Kite | Upstox | Dhan | Fyers | Paytm |
|----------|---------|------|--------|------|-------|-------|
| **NSE** (Cash) | Yes | Yes | Yes | Yes | Yes | Yes |
| **BSE** (Cash) | Yes | Yes | Yes | Yes | Yes | Yes |
| **NFO** (NSE F&O) | Yes | Yes | Yes | Yes | Yes | Yes |
| **BFO** (BSE F&O) | Yes | Yes | Yes | Yes | Yes | **Yes (added 2025)** |
| **MCX** (Commodity) | Yes | Yes | Yes | Yes | Yes | No |
| **CDS** (Currency) | Yes | Yes | Yes | Yes | Yes | No |

**Full exchange support:** SmartAPI, Kite, Upstox, Dhan, Fyers
**Limited:** Paytm (NSE/BSE/NFO/BFO, no MCX/CDS; limited F&O coverage)

---

## 11. AlgoChanakya Implementation Status

| Broker | Market Data | Order Adapter | Ticker (WS) | Auth Route | Frontend | Tests |
|--------|------------|---------------|-------------|------------|----------|-------|
| **SmartAPI** | ✅ 584 lines | ✅ 428 lines | ✅ 353 lines | ✅ 410 lines | ✅ | ✅ 510 lines |
| **Kite** | ✅ 422 lines | ✅ kite_adapter | ✅ 313 lines | ✅ auth.py | ✅ | ✅ 598 lines |
| **Upstox** | ✅ 568 lines | ✅ 494 lines | ✅ 821 lines | ✅ 190 lines | ✅ | ✅ 1,738 lines |
| **Dhan** | ✅ 813 lines | ✅ 446 lines | ✅ 575 lines | ✅ 173 lines | ✅ | ✅ 1,435 lines |
| **Fyers** | ✅ 695 lines | ✅ 467 lines | ✅ 410 lines | ✅ 201 lines | ✅ | ✅ 1,424 lines |
| **Paytm** | ✅ 581 lines | ✅ 437 lines | ✅ 618 lines | ✅ 246 lines | ✅ | ✅ 1,423 lines |

**All 6 brokers are fully implemented.** (Previous version incorrectly showed Upstox/Dhan/Fyers/Paytm as "Planned".)

### Key Codebase Files

| File | Contents |
|------|----------|
| `backend/app/services/brokers/base.py` | BrokerAdapter interface, UnifiedOrder/Position/Quote |
| `backend/app/services/brokers/factory.py` | Order execution factory |
| `backend/app/services/brokers/kite_adapter.py` | Kite order execution |
| `backend/app/services/brokers/market_data/market_data_base.py` | MarketDataBrokerAdapter, credentials, enums |
| `backend/app/services/brokers/market_data/factory.py` | Market data factory |
| `backend/app/services/brokers/market_data/smartapi_adapter.py` | SmartAPI market data (584 lines) |
| `backend/app/services/brokers/market_data/rate_limiter.py` | Rate limits (all 6 brokers) |
| `backend/app/services/brokers/market_data/symbol_converter.py` | Symbol conversion |
| `backend/app/services/brokers/market_data/token_manager.py` | Token mapping |
| `backend/app/services/brokers/market_data/exceptions.py` | Unified exceptions |

### Broker Expert Skill Quick Reference

| Broker | Expert Skill | Top Gotchas |
|--------|-------------|-------------|
| **SmartAPI** | `/angelone-expert` | Static IP required (Aug 2025); paise conversion (WS + historical); auto-TOTP; 1 req/sec |
| **Kite** | `/zerodha-expert` | Rate limit is **10/sec** (not 3); symbol IS canonical; no webhooks; no option chain API |
| **Upstox** | `/upstox-expert` | IP whitelist required; V2 WS discontinued Aug 2025; Protobuf; UDAPI100050 dual meaning |
| **Dhan** | `/dhan-expert` | `availabelBalance` typo (exact spelling required); Little Endian WS; numeric security_ids |
| **Fyers** | `/fyers-expert` | v3 SDK Nov 2023; 5 socket types; GTT WS events broken (Feb 2026); midnight token expiry |
| **Paytm** | `/paytm-expert` | 3 token types (wrong token = silent fail); least mature; no webhooks; BSE F&O added 2025 |

---

## 12. Recommendation Matrix

### Use Case → Best Broker

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| **Free market data** | Any (all free) | SmartAPI, Upstox, Fyers, Paytm, Dhan* all ₹0 |
| **Free orders** | Any (all free) | SmartAPI + Kite Personal API default |
| **Highest REST rate limit** | Upstox | 50/sec (vs Kite 10, others 10) |
| **Best documentation** | Kite | Most mature API, best SDK |
| **Auto-login (no interaction)** | SmartAPI, Upstox, or Dhan | Auto-TOTP (SmartAPI/Upstox) / static token (Dhan) |
| **Deep market depth** | Dhan | 200-level depth (unique in India) |
| **Real-time Greeks via WS** | Upstox | `option_greeks` WS mode |
| **Highest WS symbol capacity** | Fyers | 5,000 symbols/conn |
| **Order update stream** | Fyers or Dhan | FyersOrderSocket / Dhan order WS |
| **Most WS socket types** | Fyers | 5 types (Data/Order/Position/Trade/General) |
| **Multi-client/server apps** | Upstox | Extended token (1yr read-only) |
| **Paper/virtual trading** | Fyers or Upstox | Fyers built-in, Upstox sandbox (Jan 2025) |
| **Widest exchange support** | SmartAPI/Kite/Upstox/Dhan/Fyers | 6 exchanges each |

### AlgoChanakya Default Setup

```
Market Data:  SmartAPI (FREE, auto-TOTP, no daily login, platform default)
Orders:       Kite Personal API (FREE, orders only since March 2025)
Total Cost:   ₹0/month

Failover chain (market data): SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite
```

---

## 13. Corrections from Previous Version (Feb 16, 2026 → Feb 25, 2026)

| Section | Old (Wrong) | New (Correct) |
|---------|-------------|---------------|
| Upstox pricing | ₹499/month | **FREE (₹0)** |
| Kite rate limit | 3/sec | **10/sec** |
| Upstox rate limit | 25/sec | **50/sec, 500/min, 2000/30min** |
| Dhan order rate limits | 25/sec | **10/sec, 250/min, 1000/hr, 7000/day** |
| SmartAPI order rate | 10/sec | **20/sec** (Feb 2025) |
| Fyers WS symbols | 200 | **5,000** |
| Fyers WS sockets | 2 (dual) | **5** (Data/Order/Position/Trade/General) |
| Fyers v3 release | Feb 3, 2026 | **November 2023** |
| Implementation status | Upstox/Dhan/Fyers/Paytm = Planned | **All 6 fully implemented** |
| SmartAPI static IP | Not mentioned | **Required since Aug 2025** |
| Dhan `availabelBalance` | Not mentioned | **Known typo — use exact spelling** |
| Paytm BSE F&O | No | **Added 2025** |
| GTT support | Incomplete | **Updated per broker** |
| Option chain | Incomplete | **Updated per broker** |
| Webhooks | Incomplete | **Updated per broker** |

---

## 14. Architecture Documentation

| Document | Description |
|----------|-------------|
| [Broker Abstraction Architecture](../../../../docs/architecture/broker-abstraction.md) | Complete multi-broker technical design (dual system: market data + orders) |
| [ADR-002: Multi-Broker Abstraction](../../../../docs/decisions/002-broker-abstraction.md) | Decision rationale for broker abstraction pattern |
| [TICKER-DESIGN-SPEC.md](../../../../docs/decisions/TICKER-DESIGN-SPEC.md) | Multi-broker ticker architecture (5-component design) |
| [CLAUDE.md - Multi-Broker Architecture](../../../../CLAUDE.md#core-purpose-multi-broker-architecture) | Project-level broker architecture overview |
| [Implementation Checklist](../../../../docs/IMPLEMENTATION-CHECKLIST.md) | Current phase status and remaining tasks |
