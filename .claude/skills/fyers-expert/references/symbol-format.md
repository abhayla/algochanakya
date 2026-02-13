# Fyers Symbol Format

Complete symbol format reference for Fyers API v3 with canonical conversion rules.

## Symbol Format: Exchange-Prefixed

All Fyers symbols use `{EXCHANGE}:{SYMBOL}` format. The prefix is **mandatory** for all API calls.

### Format by Instrument Type

| Type | Pattern | Example |
|------|---------|---------|
| **Index** | `{EXCH}:{NAME}-INDEX` | `NSE:NIFTY50-INDEX` |
| **Index Option (weekly)** | `{EXCH}:{INDEX}{YYMDD}{STRIKE}{CE\|PE}` | `NSE:NIFTY2522725000CE` |
| **Index Option (monthly)** | `{EXCH}:{INDEX}{YYMON}{STRIKE}{CE\|PE}` | `NSE:NIFTY25FEB25000CE` |
| **Index Future** | `{EXCH}:{INDEX}{YYMON}FUT` | `NSE:NIFTY25FEBFUT` |
| **Stock Option** | `{EXCH}:{STOCK}{DDMONYY}{STRIKE}{CE\|PE}` | `NSE:RELIANCE27FEB252500CE` |
| **Equity** | `{EXCH}:{STOCK}-EQ` | `NSE:RELIANCE-EQ` |

### Special Suffixes (MANDATORY)

| Suffix | When Required | Example |
|--------|---------------|---------|
| `-INDEX` | ALL index instruments | `NSE:NIFTY50-INDEX`, `BSE:SENSEX-INDEX` |
| `-EQ` | ALL equity/stock quotes | `NSE:RELIANCE-EQ`, `NSE:TCS-EQ` |

Omitting suffixes causes error code `-310`.

### Index Symbol Mapping

| Index | Fyers Symbol | Note |
|-------|-------------|------|
| NIFTY 50 | `NSE:NIFTY50-INDEX` | `NIFTY50` not `NIFTY` |
| NIFTY BANK | `NSE:NIFTYBANK-INDEX` | |
| NIFTY FIN SERVICE | `NSE:FINNIFTY-INDEX` | |
| SENSEX | `BSE:SENSEX-INDEX` | BSE exchange |
| BANKEX | `BSE:BANKEX-INDEX` | BSE exchange |
| INDIA VIX | `NSE:INDIAVIX-INDEX` | |

### Exchange Codes

| Code | Description | Notes |
|------|-------------|-------|
| `NSE` | NSE Cash + F&O | Single code for both segments |
| `BSE` | BSE Cash + F&O | Single code for both segments |
| `MCX` | Commodities | MCX F&O |

**Note:** Unlike SmartAPI (`NSE`/`NFO`/`BSE`/`BFO`), Fyers uses one code per exchange.

---

## Canonical Conversion (Fyers <-> Kite)

### Complexity: LOW

Fyers derivative symbols are essentially Kite symbols with an exchange prefix. Core symbol format is identical.

### Conversion Rules

| Direction | Rule | Example |
|-----------|------|---------|
| Fyers -> Canonical | Strip `{EXCH}:` prefix | `NSE:NIFTY2522725000CE` -> `NIFTY2522725000CE` |
| Canonical -> Fyers | Add `{EXCH}:` prefix | `NIFTY2522725000CE` -> `NSE:NIFTY2522725000CE` |
| Fyers Index -> Canonical | Strip prefix + `-INDEX`, map name | `NSE:NIFTY50-INDEX` -> `NIFTY 50` |
| Canonical Index -> Fyers | Map name, add prefix + `-INDEX` | `NIFTY 50` -> `NSE:NIFTY50-INDEX` |
| Fyers Equity -> Canonical | Strip prefix + `-EQ` | `NSE:RELIANCE-EQ` -> `RELIANCE` |
| Canonical Equity -> Fyers | Add prefix + `-EQ` | `RELIANCE` -> `NSE:RELIANCE-EQ` |

### Python Conversion Functions

```python
def fyers_to_canonical(fyers_symbol: str) -> str:
    """Convert Fyers symbol to canonical (Kite) format."""
    if ":" not in fyers_symbol:
        return fyers_symbol
    _, symbol = fyers_symbol.split(":", 1)

    if symbol.endswith("-INDEX"):
        bare = symbol.replace("-INDEX", "")
        return INDEX_FYERS_TO_CANONICAL.get(bare, bare)
    if symbol.endswith("-EQ"):
        return symbol.replace("-EQ", "")
    return symbol  # Derivatives: same as Kite after prefix

def canonical_to_fyers(canonical: str, instrument_type: str = "option") -> str:
    """Convert canonical (Kite) to Fyers format."""
    if instrument_type == "index":
        name = INDEX_CANONICAL_TO_FYERS.get(canonical, canonical)
        exch = "BSE" if canonical in BSE_INDICES else "NSE"
        return f"{exch}:{name}-INDEX"
    if instrument_type == "equity":
        return f"NSE:{canonical}-EQ"
    return f"NSE:{canonical}"  # Options/futures: add prefix

# Index name mappings
INDEX_FYERS_TO_CANONICAL = {
    "NIFTY50": "NIFTY 50", "NIFTYBANK": "NIFTY BANK",
    "FINNIFTY": "NIFTY FIN SERVICE", "SENSEX": "SENSEX",
    "BANKEX": "BANKEX", "INDIAVIX": "INDIA VIX",
    "MIDCPNIFTY": "NIFTY MID SELECT",
}
INDEX_CANONICAL_TO_FYERS = {v: k for k, v in INDEX_FYERS_TO_CANONICAL.items()}
BSE_INDICES = {"SENSEX", "BANKEX"}
```

### Using SymbolConverter / TokenManager

```python
from app.services.brokers.market_data.symbol_converter import SymbolConverter
from app.services.brokers.market_data.token_manager import token_manager

converter = SymbolConverter()
canonical = converter.to_canonical("NSE:NIFTY2522725000CE", "fyers")  # -> "NIFTY2522725000CE"
fyers = converter.from_canonical("NIFTY2522725000CE", "fyers")        # -> "NSE:NIFTY2522725000CE"

fyers_token = await token_manager.get_broker_token("NIFTY2522725000CE", "fyers")
canonical = await token_manager.get_canonical_symbol("101010000012345", "fyers")
```

---

## Regex Patterns

### Full Symbol (with exchange prefix)
```regex
^(NSE|BSE|MCX):(.+)$
```

### Index
```regex
^(NSE|BSE):([A-Z0-9]+)-INDEX$
```

### Option
```regex
^(NSE|BSE):([A-Z]+)(\d{2}[A-Z]{3}\d{2}|\d{5})(\d+)(CE|PE)$
```

### Future
```regex
^(NSE|BSE|MCX):([A-Z]+)(\d{2}[A-Z]{3}\d{2}|\d{2}[A-Z]{3})FUT$
```

### Equity
```regex
^(NSE|BSE):([A-Z0-9&]+)-EQ$
```

### Validation Function

```python
import re

FYERS_PATTERNS = {
    "index": re.compile(r"^(NSE|BSE):([A-Z0-9]+)-INDEX$"),
    "equity": re.compile(r"^(NSE|BSE):([A-Z0-9&]+)-EQ$"),
    "option": re.compile(r"^(NSE|BSE):([A-Z]+)(\d{2}[A-Z]{3}\d{2}|\d{5})(\d+)(CE|PE)$"),
    "future": re.compile(r"^(NSE|BSE|MCX):([A-Z]+)(\d{2}[A-Z]{3}\d{2}|\d{2}[A-Z]{3})FUT$"),
}

def identify_fyers_symbol_type(symbol: str) -> str:
    """Returns: 'index', 'equity', 'option', 'future', or 'unknown'."""
    for sym_type, pattern in FYERS_PATTERNS.items():
        if pattern.match(symbol):
            return sym_type
    return "unknown"

def validate_fyers_symbol(symbol: str) -> bool:
    if ":" not in symbol:
        return False
    return identify_fyers_symbol_type(symbol) != "unknown"
```

---

## Instrument Master (CSV)

| Segment | URL |
|---------|-----|
| NSE Cash | `https://public.fyers.in/sym_details/NSE_CM.csv` |
| NSE F&O | `https://public.fyers.in/sym_details/NSE_FO.csv` |
| BSE Cash/F&O | `BSE_CM.csv` / `BSE_FO.csv` |
| MCX | `https://public.fyers.in/sym_details/MCX_COM.csv` |

**Key differences from SmartAPI:** CSV format (not JSON), strike prices in **rupees** (not paise), ~5-15MB per segment.

---

## Common Gotchas

1. **Exchange prefix mandatory** -- Every API call needs `NSE:`, `BSE:`, or `MCX:`. Error `-310` without it.
2. **`-INDEX` for all indices** -- `NSE:NIFTY50-INDEX`, not `NSE:NIFTY50`.
3. **`-EQ` for all equities** -- `NSE:RELIANCE-EQ`, not `NSE:RELIANCE`.
4. **NIFTY50 vs NIFTY** -- Index name is `NIFTY50`, but derivatives use `NIFTY` (e.g., `NIFTY2522725000CE`).
5. **Single exchange code** -- `NSE` for both cash and F&O (not `NSE`/`NFO` like SmartAPI).
6. **Strikes in rupees** -- Instrument master has strikes in rupees (SmartAPI uses paise).
7. **Low conversion complexity** -- After stripping prefix, Fyers derivative symbols match Kite format.
8. **Case sensitive** -- Must be UPPERCASE. `nse:nifty50-index` fails.
9. **Fytoken format** -- Long numeric strings (e.g., `101010000012345`), different from SmartAPI tokens.
10. **CSV instrument master** -- Not JSON like SmartAPI. Requires different parsing logic.

## AlgoChanakya Files

| File | Purpose |
|------|---------|
| `backend/app/services/brokers/market_data/symbol_converter.py` | Fyers <-> Canonical conversion |
| `backend/app/services/brokers/market_data/token_manager.py` | Token <-> Symbol mapping |
| `backend/app/services/brokers/market_data/fyers_adapter.py` | Market data adapter (planned) |
