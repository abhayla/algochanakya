# Paytm Money Symbol Format and Instrument Mapping

> **MATURITY WARNING:** Paytm Money has limited F&O coverage compared to Kite/SmartAPI.
> Not all derivatives may be available. Verify against the daily script master before
> assuming a security_id exists. Gaps remain for commodity derivatives and some far-OTM
> index options series.

## Core Identifier: security_id

Paytm uses `security_id` (string) corresponding to BSE/NSE security codes.

| Broker | Identifier | Example (Reliance) |
|--------|-----------|-------------------|
| **Paytm Money** | `security_id` (string) | `"500325"` |
| **Kite (Zerodha)** | `instrument_token` (int) | `738561` |
| **SmartAPI (Angel)** | `symboltoken` (string) | `"2885"` |

**Exchanges:** `NSE` (Equity, Derivatives, Index), `BSE` (Equity only)

## Script Master (Instrument Master)

Daily CSV download: `GET /data/v1/scrip/download/csv` (requires `read_access_token`)

| Column | Type | Example |
|--------|------|---------|
| `security_id` | string | `500325` |
| `exchange` | string | `NSE` |
| `segment` | string | `E` (equity), `D` (derivative) |
| `symbol` | string | `RELIANCE` |
| `series` | string | `EQ`, `BE`, `INDEX` |
| `expiry` | string | `2024-01-25` |
| `strike_price` | float | `21500.00` |
| `option_type` | string | `CE`, `PE` |
| `lot_size` | int | `50` |
| `tick_size` | float | `0.05` |

```csv
security_id,exchange,segment,symbol,series,expiry,strike_price,option_type,lot_size,tick_size
500325,NSE,E,RELIANCE,EQ,,,,1,0.05
999920000,NSE,E,NIFTY 50,INDEX,,,,1,0.05
46512,NSE,D,NIFTY,OPT,2024-01-25,21500.00,CE,50,0.05
```

## Canonical Symbol Conversion

AlgoChanakya uses **Kite format** as canonical symbol. Conversion requires the script master.

### Conversion Table

| Canonical (Kite) | Paytm Fields |
|-------------------|-------------|
| `RELIANCE` | symbol=`RELIANCE`, segment=`E` |
| `NIFTY24JAN21500CE` | symbol=`NIFTY`, expiry=`2024-01-25`, strike=`21500`, type=`CE` |
| `BANKNIFTY24JAN48000PE` | symbol=`BANKNIFTY`, expiry=`2024-01-25`, strike=`48000`, type=`PE` |
| `NIFTY24JANFUT` | symbol=`NIFTY`, expiry=`2024-01-25`, segment=`D` (FUT) |

### Conversion Functions

```python
from datetime import datetime

MONTH_CODES = {1:"JAN",2:"FEB",3:"MAR",4:"APR",5:"MAY",6:"JUN",
               7:"JUL",8:"AUG",9:"SEP",10:"OCT",11:"NOV",12:"DEC"}

def paytm_to_canonical(row: dict) -> str:
    """Convert Paytm script master row to canonical (Kite) symbol."""
    symbol, segment = row["symbol"], row["segment"]
    if segment == "E" or row.get("series") == "INDEX":
        return symbol
    expiry = datetime.strptime(row["expiry"], "%Y-%m-%d")
    ym = f"{expiry.strftime('%y')}{MONTH_CODES[expiry.month]}"
    if row.get("option_type") in ("CE", "PE"):
        return f"{symbol}{ym}{int(float(row['strike_price']))}{row['option_type']}"
    return f"{symbol}{ym}FUT"

def canonical_to_paytm_query(canonical: str) -> dict:
    """Parse canonical symbol into Paytm search fields (heuristic)."""
    import re
    m = re.match(r'^([A-Z]+)(\d{2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
                 r'(?:(\d+)(CE|PE)|(FUT))$', canonical)
    if m:
        result = {"symbol": m.group(1), "expiry_year": int(m.group(2))+2000, "expiry_month": m.group(3)}
        if m.group(6): result["segment"] = "FUT"
        else: result["strike_price"] = float(m.group(4)); result["option_type"] = m.group(5)
        return result
    return {"symbol": canonical, "segment": "E"}
```

## TokenManager Integration

Uses `broker_instrument_tokens` table for cross-broker mapping:

```python
# Load script master into TokenManager
async def load_paytm_instruments(adapter, token_manager):
    csv_content = await adapter.download_script_master()
    reader = csv.DictReader(io.StringIO(csv_content))
    instruments = [{"canonical_symbol": paytm_to_canonical(row), "broker": "paytm",
        "broker_symbol": row["symbol"], "broker_token": row["security_id"],
        "exchange": row["exchange"], "expiry": row.get("expiry"),
        "strike": row.get("strike_price"), "option_type": row.get("option_type"),
        "lot_size": row.get("lot_size", 1)} for row in reader]
    await token_manager.bulk_upsert("paytm", instruments)

# Usage in adapters
security_id = await token_manager.get_broker_token("RELIANCE", "paytm")    # "500325"
paytm_id = await token_manager.get_broker_token(256265, "paytm")           # "999920000"
canonical = await token_manager.get_canonical_symbol("500325", "paytm")    # "RELIANCE"
```

## Index Identifiers

| Index | Kite Token | Paytm security_id |
|-------|-----------|-------------------|
| NIFTY 50 | 256265 | `999920000` |
| BANK NIFTY | 260105 | `999920005` |
| FINNIFTY | 257801 | `999920019` |

> Index security_ids follow a `9999xxxxx` pattern (synthetic, not BSE/NSE codes).

## Known Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Limited F&O coverage | Far-OTM strikes missing | Check script master first |
| No weekly expiry identifiers | Hard to differentiate weekly/monthly | Parse expiry dates |
| security_id changes on rollover | Derivative IDs change after expiry | Re-download daily |
| No commodity segment | MCX unavailable | Not supported |
| BSE derivatives sparse | Limited BSE F&O | Use NSE for derivatives |

## Daily Refresh Requirement

Script master must be refreshed daily (new contracts listed, expired removed, security_ids
change on rollover). Schedule download at 8:00 AM IST before market open.

> **MATURITY WARNING:** The Paytm script master CSV format and column names have changed
> in the past. Use defensive parsing; log warnings for unexpected changes rather than crashing.
