# SmartAPI Symbol Format

Complete symbol format reference for Angel One SmartAPI, including instrument master details and canonical conversion.

## Symbol Format Specification

### General Pattern

```
{UNDERLYING}{EXPIRY}{STRIKE}{OPTION_TYPE}
```

Where:
- `UNDERLYING`: Index/stock name (e.g., `NIFTY`, `BANKNIFTY`, `RELIANCE`)
- `EXPIRY`: Date in `DDMONYY` format (e.g., `27FEB25`, `27MAR25`)
- `STRIKE`: Strike price as integer (no decimal)
- `OPTION_TYPE`: `CE` (Call) or `PE` (Put)

### Format by Instrument Type

| Type | Pattern | Example |
|------|---------|---------|
| **Index Option** | `{INDEX}{DDMONYY}{STRIKE}{CE\|PE}` | `NIFTY27FEB2525000CE` |
| **Stock Option** | `{STOCK}{DDMONYY}{STRIKE}{CE\|PE}` | `RELIANCE27FEB252500CE` |
| **Index Future** | `{INDEX}{DDMONYY}FUT` | `NIFTY27FEBFUT` |
| **Stock Future** | `{STOCK}{DDMONYY}FUT` | `RELIANCE27FEBFUT` |
| **Equity** | `{STOCK}-EQ` | `RELIANCE-EQ` |
| **Index** | `{INDEX}` | `NIFTY` (with specific tokens) |

### Expiry Format

```
DD  = Day of month (2 digits, zero-padded)
MON = 3-letter month abbreviation (JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC)
YY  = 2-digit year
```

**Examples:**
- `27FEB25` = February 27, 2025
- `06MAR25` = March 6, 2025
- `24APR25` = April 24, 2025

### Weekly vs Monthly Expiry

SmartAPI does NOT distinguish weekly from monthly in the symbol format. Both use `DDMONYY`. The expiry date itself determines if it's weekly or monthly:

- **Weekly:** Thursday expiry (current week)
- **Monthly:** Last Thursday of the month

### Strike Price Format

- Stored as **integer** in the symbol (no decimals)
- In the instrument master file, `strike` is in **PAISE** (divide by 100)
- Example: Strike 25000 → symbol has `25000`, master has `2500000` (paise)

## Instrument Master File

### Download URL

```
https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
```

### File Details

| Property | Value |
|----------|-------|
| Format | JSON array |
| Size | ~50 MB |
| Update Frequency | Daily (before market open) |
| Cache Duration (AlgoChanakya) | 12 hours |

### JSON Object Schema

```json
{
  "token": "12345",
  "symbol": "NIFTY27FEB2525000CE",
  "name": "NIFTY",
  "expiry": "27FEB2025",
  "strike": "2500000.000000",
  "lotsize": "25",
  "instrumenttype": "OPTIDX",
  "exch_seg": "NFO",
  "tick_size": "5.000000"
}
```

### Field Reference

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `token` | string | SmartAPI instrument token | Unique per exchange |
| `symbol` | string | Trading symbol | SmartAPI format |
| `name` | string | Underlying name | `NIFTY`, `BANKNIFTY`, etc. |
| `expiry` | string | Expiry date | `DDMONYYYY` (4-digit year) |
| `strike` | string | Strike price | **In PAISE** (divide by 100) |
| `lotsize` | string | Lot size | e.g., `"25"` for NIFTY |
| `instrumenttype` | string | Instrument category | See table below |
| `exch_seg` | string | Exchange segment | `NSE`, `NFO`, `BSE`, `BFO`, `MCX` |
| `tick_size` | string | Minimum price movement | In paise |

### Instrument Types

| Value | Description |
|-------|-------------|
| `OPTIDX` | Index Option (NIFTY, BANKNIFTY CE/PE) |
| `OPTSTK` | Stock Option (RELIANCE CE/PE) |
| `FUTIDX` | Index Future |
| `FUTSTK` | Stock Future |
| `EQ` | Equity |
| `AMXIDX` | AMX Index |

## Token to Symbol Mapping

### Key Index Tokens

| Index | SmartAPI Token | Exchange |
|-------|---------------|----------|
| NIFTY 50 | `99926000` | NSE |
| NIFTY BANK | `99926009` | NSE |
| NIFTY FIN SERVICE | `99926037` | NSE |
| SENSEX | `99919000` | BSE |
| BANKEX | `99919005` | BSE |

### Key Equity Tokens

| Stock | SmartAPI Token | Exchange |
|-------|---------------|----------|
| RELIANCE | `2885` | NSE |
| TCS | `11536` | NSE |
| INFY | `1594` | NSE |
| HDFC BANK | `1333` | NSE |

## Canonical Conversion (SmartAPI ↔ Kite)

AlgoChanakya uses **Kite format as canonical**. SmartAPI symbols must be converted.

### Conversion Rules

| Aspect | SmartAPI | Kite (Canonical) | Conversion |
|--------|---------|-------------------|------------|
| Expiry | `27FEB25` | `25FEB` or `25225` | Reformat date |
| Strike | `25000` | `25000` | Same |
| Option type | `CE`/`PE` | `CE`/`PE` | Same |
| Equity suffix | `-EQ` | (none or `-EQ`) | May differ |

### Example Conversions

| SmartAPI Symbol | Canonical (Kite) | Notes |
|----------------|-------------------|-------|
| `NIFTY27FEB2525000CE` | `NIFTY2522725000CE` | Date reformatted |
| `BANKNIFTY06MAR2552000PE` | `BANKNIFTY2530652000PE` | Monthly → YY + date |
| `RELIANCE-EQ` | `RELIANCE` | Suffix removed |
| `NIFTY27FEBFUT` | `NIFTY25FEBFUT` | Future format |

### Using SymbolConverter

```python
from app.services.brokers.market_data.symbol_converter import SymbolConverter

converter = SymbolConverter()

# SmartAPI → Canonical
canonical = converter.to_canonical("NIFTY27FEB2525000CE", "smartapi")
# → "NIFTY2522725000CE"

# Canonical → SmartAPI
smartapi = converter.from_canonical("NIFTY2522725000CE", "smartapi")
# → "NIFTY27FEB2525000CE"
```

### Using TokenManager

```python
from app.services.brokers.market_data.token_manager import token_manager

# Canonical symbol → SmartAPI token
smartapi_token = await token_manager.get_broker_token("NIFTY2522725000CE", "smartapi")
# → 12345

# SmartAPI token → Canonical symbol
canonical = await token_manager.get_canonical_symbol(12345, "smartapi")
# → "NIFTY2522725000CE"
```

## Common Symbol Gotchas

1. **Strike in paise in master** - Instrument master's `strike` field is in paise (`2500000` = ₹25000). Divide by 100.

2. **Expiry year format** - Master uses 4-digit year (`27FEB2025`), symbol uses 2-digit (`27FEB25`).

3. **Exchange mismatch** - NSE and BSE have different tokens for the same stock. Always include exchange context.

4. **Weekly expiry symbols** - Look identical to monthly. Differentiate by checking if the date is the last Thursday.

5. **Token recycling** - SmartAPI may reuse tokens after contract expiry. Always verify token-symbol mapping with current master.

6. **Name field** - The `name` field in master is the underlying (e.g., `NIFTY`), NOT the full symbol.

7. **50MB download** - Master is large. Always cache. AlgoChanakya caches in `smartapi_instruments.py` singleton for 12 hours.

## Regex Patterns

### SmartAPI Option Symbol
```regex
^([A-Z]+)(\d{2}[A-Z]{3}\d{2})(\d+)(CE|PE)$
```
Groups: `underlying`, `expiry`, `strike`, `option_type`

### SmartAPI Future Symbol
```regex
^([A-Z]+)(\d{2}[A-Z]{3}\d{2})?FUT$
```

### SmartAPI Equity Symbol
```regex
^([A-Z]+)-EQ$
```

## AlgoChanakya Codebase Files

| File | Purpose |
|------|---------|
| `backend/app/services/brokers/market_data/symbol_converter.py` | SmartAPI ↔ Canonical conversion |
| `backend/app/services/brokers/market_data/token_manager.py` | Token ↔ Symbol mapping |
| `backend/app/services/legacy/smartapi_instruments.py` | Instrument master download/cache |
| `backend/app/services/brokers/market_data/smartapi_adapter.py` | Uses SymbolConverter + TokenManager |
