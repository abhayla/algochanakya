# Instrument & Token Architecture — Cross-Broker Reference

## The NSE Exchange Token Discovery

NSE assigns its own token numbers for every F&O instrument. These flow through to some brokers unchanged:

| Broker | Token Field | F&O Options Token Source | Index Token Source |
|--------|------------|--------------------------|-------------------|
| **Kite/Zerodha** | `instrument_token` | Kite-internal (NOT NSE) — large numbers like 14032898 | Kite-internal (256265 for NIFTY) |
| **Kite/Zerodha** | `exchange_token` | NSE-assigned — smaller numbers like 54816 | Broker-assigned (1001) |
| **SmartAPI/AngelOne** | `symboltoken` | NSE-assigned — same as Kite's exchange_token | Broker-assigned (26000) |
| **Upstox** | `exchange_token` (in instrument_key) | NSE-assigned — same as SmartAPI | String for indices ("Nifty 50") |

**Key rule:** For F&O options, `Upstox exchange_token == SmartAPI symboltoken == Kite exchange_token`. But Kite's `instrument_token` is completely different (Kite-internal). For indices, all three brokers use different IDs.

**Confirmed with live testing:** NIFTY 24050 CE 13-Apr-2026 — Upstox instrument_key `NSE_FO|54816`, SmartAPI token `54816`, Kite instrument_token `14032898`. SmartAPI and Upstox match; Kite does not.

## Instrument Master Comparison

| Aspect | Zerodha (Kite) | AngelOne (SmartAPI) | Upstox |
|--------|---------------|---------------------|--------|
| **Format** | CSV (gzipped) | JSON (~50MB) | JSON or CSV (gzipped) |
| **URL** | `api.kite.trade/instruments/NFO` | `margincalculator.angelbroking.com/.../OpenAPIScripMaster.json` | `assets.upstox.com/.../NSE.json.gz` |
| **Auth required** | Yes (API key) | No (public) | No (public) |
| **Refresh time** | 8:30 AM IST | 8:30 AM IST | 6:00 AM IST |
| **Token stability** | Tokens recycled after expiry | Stable during contract life | instrument_key never reused; exchange_token recycled |
| **Recommended primary key** | `exchange + tradingsymbol` | `exch_seg + symbol` | `instrument_key` |
| **Prices** | Rupees | **Paise** (divide by 100) | Rupees |
| **Option chain API** | None (batch quote) | None (WebSocket snap or batch REST) | **Yes** — `/v2/option/chain` |
| **Greeks in API** | No | No | **Yes** (IV, delta, gamma, theta, vega, PoP) |

## tradingsymbol Format

For NIFTY 24000 CE expiring 17 Apr 2026 (weekly):

| Broker | Format Pattern | Result |
|--------|---------------|--------|
| **Kite** (weekly) | `{NAME}{YY}{M}{DD}{STRIKE}{TYPE}` | `NIFTY2641724000CE` |
| **Kite** (monthly) | `{NAME}{YY}{MMM}{STRIKE}{TYPE}` | `NIFTY26APR24000CE` |
| **SmartAPI** | `{NAME}{DD}{MMM}{YYYY}{STRIKE}{TYPE}` | `NIFTY17APR202624000CE` |
| **Upstox** (instrument master) | Same as Kite format | `NIFTY2641724000CE` |
| **Upstox** (option chain API) | Not returned — only `instrument_key` | `NSE_FO|54816` |

Kite weekly month codes: 1=JAN, 2=FEB, 3=MAR, 4=APR, 5=MAY, 6=JUN, 7=JUL, 8=AUG, 9=SEP, O=OCT, N=NOV, D=DEC.

Last Thursday of month = monthly expiry (3-letter month code). All other Thursdays = weekly (single-char month code).

## Rate Limits

| Broker | REST Rate Limit | WebSocket Token Limit |
|--------|----------------|----------------------|
| SmartAPI | 1 req/sec (50 tokens/batch) | 1,000 tokens/session |
| Kite | 10 req/sec (500 tokens/quote, 1000/ltp) | 3,000 tokens x 3 connections |
| Upstox | 25 req/sec | ~1,500 basic, ~5,000 pro |

## Option Chain Data Sources

| Broker | Method | Market-Closed Behavior |
|--------|--------|----------------------|
| **Upstox** | `/v2/option/chain` — returns all strikes with `close_price` + pre-calculated Greeks | `close_price` always non-zero; `ltp=0` falls back to `close_price` |
| **SmartAPI** | WebSocket V2 snap (Mode 3) — bulk ticks for subscribed tokens | Returns 0 for `last_traded_price`; `closed_price` has previous close |
| **Kite** | Batch `GET /quote` — up to 500 instruments per call | `last_price=0`; `ohlc.close` has previous close |

## AlgoChanakya Implications

### The Duplicate Row Problem

The `instruments` table has unique constraint on `(instrument_token, source_broker)`. When both Kite and SmartAPI instruments are loaded, each strike gets TWO rows with different tokens. Queries without `source_broker` filter return duplicates — causing token mismatches in option chain, orders, and strategy builders.

### Correct Token Usage Per Adapter

| Active Adapter | Which token to use from DB | Why |
|---------------|--------------------------|-----|
| **SmartAPI** | SmartAPI rows (`source_broker='smartapi'`) | SmartAPI tokens = NSE exchange tokens |
| **Upstox** | SmartAPI rows (`source_broker='smartapi'`) | Upstox tokens = NSE exchange tokens = SmartAPI tokens |
| **Kite** | Kite rows (`source_broker='kite'`) | Kite uses its own internal instrument_token |

### Best Practice Pattern

```
1. CANONICAL SYMBOL as universal key — "NIFTY2641724000CE" (Kite format)
2. Single instruments table — one row per (underlying, strike, expiry, type)
3. broker_instrument_tokens table — maps canonical_symbol -> each broker's token
4. Daily refresh at startup — download from active broker's instrument master
```

## Sources

- Kite Connect v3 docs: market-data-and-instruments, market-quotes
- Kite forum: token reuse warnings, weekly format spec, exchange_token discussion
- SmartAPI docs: OpenAPIScripMaster.json fields, symboltoken format
- SmartAPI forum: instrument master refresh, token stability, no option chain REST API
- Upstox API docs: instrument_key format, option chain endpoint, instrument master URLs
- Upstox community: instrument_key stability, daily refresh at 6 AM
- AlgoChanakya live testing (April 2026): confirmed SmartAPI==Upstox token equivalence
