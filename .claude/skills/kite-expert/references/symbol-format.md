# Kite Connect Symbol Format (CANONICAL)

Kite Connect's symbol format is the **canonical format** used throughout AlgoChanakya. All other brokers' symbols are converted to/from this format.

## Why Kite = Canonical

AlgoChanakya chose Kite format as canonical because:
1. Most well-documented and standardized
2. Already used by the initial order execution system
3. All internal references (instrument tokens, option chain) use Kite format
4. `SymbolConverter.to_canonical(symbol, "kite")` is an identity operation

## Symbol Format Specification

### Options

**Monthly Expiry:**
```
{UNDERLYING}{YY}{MON}{STRIKE}{CE|PE}
```

**Weekly Expiry:**
```
{UNDERLYING}{YY}{M}{DD}{STRIKE}{CE|PE}
```

Where:
- `UNDERLYING`: Index or stock (NIFTY, BANKNIFTY, RELIANCE, etc.)
- `YY`: 2-digit year (25, 26, etc.)
- `MON`: 3-letter month (JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC)
- `M`: Single-char month code (see table below)
- `DD`: 2-digit day of month
- `STRIKE`: Strike price (integer, no decimals)
- `CE|PE`: Call or Put

### Month Codes (Weekly Expiry)

| Month | Code | Month | Code |
|-------|------|-------|------|
| January | `1` | July | `7` |
| February | `2` | August | `8` |
| March | `3` | September | `9` |
| April | `4` | October | `O` |
| May | `5` | November | `N` |
| June | `6` | December | `D` |

### Examples by Instrument Type

| Instrument | Symbol | Type |
|-----------|--------|------|
| NIFTY 25000 CE (Feb 27 weekly) | `NIFTY2522725000CE` | Weekly option |
| NIFTY 25000 CE (Feb monthly) | `NIFTY25FEB25000CE` | Monthly option |
| NIFTY 25000 PE (Mar 6 weekly) | `NIFTY2530625000PE` | Weekly option |
| BANKNIFTY 52000 CE (Mar monthly) | `BANKNIFTY25MAR52000CE` | Monthly option |
| NIFTY Future (Feb) | `NIFTY25FEBFUT` | Monthly future |
| NIFTY Future (Mar) | `NIFTY25MARFUT` | Monthly future |
| Reliance Equity | `RELIANCE` | Equity |
| Reliance 2500 CE (Feb monthly) | `RELIANCE25FEB2500CE` | Stock option |
| NIFTY 50 Index | `NIFTY 50` | Index (with space) |
| NIFTY BANK Index | `NIFTY BANK` | Index (with space) |

### Breaking Down a Symbol

Example: `NIFTY2522725000CE`

```
NIFTY  = Underlying (NIFTY)
25     = Year (2025)
2      = Month code for February
27     = Day (27th)
25000  = Strike price (₹25,000)
CE     = Call option
```

Example: `NIFTY25FEB25000CE`

```
NIFTY  = Underlying (NIFTY)
25     = Year (2025)
FEB    = Month (February, monthly expiry)
25000  = Strike price (₹25,000)
CE     = Call option
```

## Futures Format

```
{UNDERLYING}{YY}{MON}FUT
```

**Examples:**
- `NIFTY25FEBFUT` - NIFTY Feb 2025 Future
- `BANKNIFTY25MARFUT` - BANKNIFTY Mar 2025 Future
- `RELIANCE25FEBFUT` - Reliance Feb 2025 Future

## Equity Format

Just the stock symbol, no suffix:
- `RELIANCE` (not `RELIANCE-EQ` like SmartAPI)
- `TCS`
- `INFY`
- `HDFCBANK`

## Index Format

Indices use full names with spaces:
- `NIFTY 50` (not just `NIFTY`)
- `NIFTY BANK`
- `NIFTY FIN SERVICE`
- `SENSEX`

**Note:** In URL parameters, spaces must be URL-encoded: `NIFTY%2050`

## Instrument Tokens

### Key Tokens

| Symbol | Token | Exchange |
|--------|-------|----------|
| `NIFTY 50` | `256265` | NSE |
| `NIFTY BANK` | `260105` | NSE |
| `NIFTY FIN SERVICE` | `257801` | NSE |
| `SENSEX` | `265` | BSE |
| `RELIANCE` | `738561` | NSE |
| `TCS` | `2953217` | NSE |
| `INFY` | `408065` | NSE |
| `HDFCBANK` | `341249` | NSE |

### Token Encoding

Kite instrument tokens encode the exchange:
- Tokens 0-999: BSE indices
- Tokens 256000-260000+: NSE indices
- Large tokens (7+ digits): Individual instruments

Tokens change daily for F&O instruments (expiry-specific). Always fetch fresh from instruments dump.

## Instruments CSV

### Download

```
GET https://api.kite.trade/instruments
GET https://api.kite.trade/instruments/{exchange}
```

### CSV Columns

```csv
instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange
```

| Column | Type | Description |
|--------|------|-------------|
| `instrument_token` | int | Unique token for WebSocket |
| `exchange_token` | int | Exchange-specific token |
| `tradingsymbol` | string | Trading symbol (= canonical) |
| `name` | string | Human-readable name |
| `last_price` | float | Last traded price |
| `expiry` | date | `YYYY-MM-DD` format |
| `strike` | float | Strike price in RUPEES |
| `tick_size` | float | Minimum price increment |
| `lot_size` | int | Lot size |
| `instrument_type` | string | CE, PE, FUT, EQ |
| `segment` | string | NSE, NFO-OPT, NFO-FUT, BSE |
| `exchange` | string | NSE, BSE, NFO, BFO, MCX |

**File Size:** ~80 MB for all exchanges. Cache for 24 hours.

## Regex Patterns

### Weekly Option
```regex
^([A-Z]+)(\d{2})([1-9OND])(\d{2})(\d+)(CE|PE)$
```
Groups: `underlying`, `year`, `month_code`, `day`, `strike`, `option_type`

### Monthly Option
```regex
^([A-Z]+)(\d{2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d+)(CE|PE)$
```
Groups: `underlying`, `year`, `month`, `strike`, `option_type`

### Future
```regex
^([A-Z]+)(\d{2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)FUT$
```

### Equity
```regex
^[A-Z]+$
```

## Canonical Conversion (Other Brokers → Kite)

Since Kite IS canonical, conversion is only needed from other brokers:

| Source | Example | Canonical (Kite) | Conversion |
|--------|---------|-------------------|------------|
| SmartAPI | `NIFTY27FEB2525000CE` | `NIFTY2522725000CE` | Reformat expiry |
| Upstox | `NSE_FO\|12345` | Look up tradingsymbol | Token-based lookup |
| Dhan | `12345` (security_id) | Look up tradingsymbol | ID-based lookup |
| Fyers | `NSE:NIFTY2522725000CE` | `NIFTY2522725000CE` | Strip exchange prefix |
| Paytm | Varies | Look up tradingsymbol | Instrument lookup |

### Using SymbolConverter

```python
from app.services.brokers.market_data.symbol_converter import SymbolConverter
converter = SymbolConverter()

# Kite → Canonical (identity)
canonical = converter.to_canonical("NIFTY2522725000CE", "kite")
# → "NIFTY2522725000CE" (unchanged)

# SmartAPI → Canonical
canonical = converter.to_canonical("NIFTY27FEB2525000CE", "smartapi")
# → "NIFTY2522725000CE"

# Canonical → SmartAPI
smartapi = converter.from_canonical("NIFTY2522725000CE", "smartapi")
# → "NIFTY27FEB2525000CE"
```

## AlgoChanakya Codebase Files

| File | Purpose |
|------|---------|
| `backend/app/services/brokers/market_data/symbol_converter.py` | All broker ↔ canonical conversion |
| `backend/app/services/brokers/market_data/token_manager.py` | Token ↔ symbol mapping |
| `backend/app/services/brokers/market_data/kite_adapter.py` | Uses canonical symbols directly |
| `backend/app/services/brokers/kite_adapter.py` | Order execution (canonical symbols) |
