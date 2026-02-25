# Upstox Symbol Format

> Source: [Upstox API Docs](https://upstox.com/developer/api-documentation/open-api) | Last verified: 2026-02-25

## instrument_key Format

Upstox uses `instrument_key` in the format: `{EXCHANGE}_{SEGMENT}|{identifier}`

### Format Pattern

```
{EXCHANGE}_{SEGMENT}|{instrument_token_or_name}
```

### Examples

| Instrument | instrument_key | Notes |
|-----------|---------------|-------|
| NIFTY 50 Index | `NSE_INDEX\|Nifty 50` | Indices use name |
| NIFTY BANK Index | `NSE_INDEX\|Nifty Bank` | Note capitalization |
| NIFTY 25000 CE | `NSE_FO\|56789` | F&O uses numeric token |
| Reliance Equity | `NSE_EQ\|2885` | Equity uses token |
| NIFTY Feb Future | `NSE_FO\|12345` | Futures use token |
| BSE Equity | `BSE_EQ\|500325` | BSE token |
| MCX Gold | `MCX_FO\|34567` | MCX token |

### Exchange Segments

| Segment | Description | Identifier Type |
|---------|-------------|-----------------|
| `NSE_EQ` | NSE Cash | Numeric token |
| `NSE_FO` | NSE F&O | Numeric token |
| `NSE_INDEX` | NSE Indices | Name string |
| `BSE_EQ` | BSE Cash | Numeric token |
| `BSE_FO` | BSE F&O | Numeric token |
| `BSE_INDEX` | BSE Indices | Name string |
| `MCX_FO` | MCX Commodities | Numeric token |

---

## Instrument Master

### Download (JSON only — CSV deprecated Apr 2024)

```
GET https://api.upstox.com/v2/market-quote/instruments?exchange=NSE
```

> **Note:** The CSV instrument file download (previously at `assets.upstox.com`) was deprecated in April 2024. Use the JSON REST API endpoint instead.

### Key Fields

| Field | Description |
|-------|-------------|
| `instrument_key` | Upstox unique key (used in all APIs) |
| `trading_symbol` | Readable symbol (e.g., NIFTY2522725000CE) |
| `name` | Instrument name |
| `exchange` | NSE, BSE, MCX |
| `lot_size` | Contract lot size |
| `instrument_type` | EQUITY, FUTIDX, OPTIDX, FUTSTK, OPTSTK, etc. |
| `expiry` | Expiry date (ISO format: YYYY-MM-DD) |
| `strike` | Strike price in RUPEES |
| `option_type` | CE, PE |
| `weekly` | Boolean — `true` for weekly expiry options |

---

## Canonical Conversion

### instrument_key → Canonical (Kite)

Requires instrument master lookup:

```python
# Must look up the trading_symbol from instrument master
# then convert to Kite canonical format
from app.services.brokers.market_data.token_manager import token_manager

# Upstox token → Canonical
canonical = await token_manager.get_canonical_symbol("56789", "upstox")
# → "NIFTY2522725000CE"

# Canonical → Upstox instrument_key
upstox_key = await token_manager.get_broker_token("NIFTY2522725000CE", "upstox")
# → "NSE_FO|56789"
```

### Conversion Complexity

Upstox → Canonical conversion is **moderate complexity** because:
1. instrument_key uses numeric tokens (not readable symbols)
2. Must maintain mapping table (`broker_instrument_tokens`)
3. Index instrument_keys use names, not tokens
4. Exchange segment encoding differs from Kite

---

## Common Gotchas

1. **Pipe separator** — `|` in instrument_key must be URL-encoded as `%7C` in query parameters
2. **Index names have spaces** — `NSE_INDEX|Nifty 50` (with space — also URL-encode the space as `%20`)
3. **Indices use names, instruments use tokens** — Don't mix them up
4. **Token is string in API** — Even though numeric, pass as string in JSON
5. **Strike in rupees** — Instrument master stores strikes in RUPEES (not paise)
6. **CSV deprecated** — Do not use the old CSV download URL; it no longer exists
7. **`weekly` field** — Boolean in instrument master; use to distinguish weekly vs monthly options
