---
description: >
  All internal symbol references MUST use Kite canonical format. Use SymbolConverter and TokenManager
  for broker-specific conversions. Never hardcode broker-specific symbol formats.
globs: ["backend/**/*.py"]
synthesized: true
private: false
---

# Canonical Symbol Format

## Kite Format Is the Internal Standard

All symbol references inside the codebase MUST use Kite canonical format:
- Monthly expiry: `NIFTY25APR25000CE`
- Weekly expiry: `NIFTY2541725000CE`

## Use SymbolConverter for Broker-Specific Formats

```python
from app.services.brokers.market_data.symbol_converter import CanonicalSymbol

# Parse from Kite format
symbol = CanonicalSymbol.from_kite_symbol("NIFTY25APR25000CE")

# Convert to broker-specific format
kite_str = symbol.to_kite_symbol()
```

## Use TokenManager for Token Lookups

```python
from app.services.brokers.market_data.token_manager import TokenManager

token_mgr = TokenManager(broker="smartapi", db=session)
await token_mgr.load_cache()

# Canonical symbol -> broker token
broker_token = await token_mgr.get_token("NIFTY25APR25000CE")

# Broker token -> canonical symbol
canonical = await token_mgr.get_symbol(256265)
```

## MUST NOT Hardcode Broker Symbol Formats

Different brokers use different formats:
- Kite: `NIFTY25APR25000CE`
- SmartAPI: `NIFTY24DEC24000CE` (different date encoding)
- Dhan/Fyers/Upstox: their own formats

Hardcoding any broker-specific format outside of adapter code will break when users switch brokers.

## Index Tokens Are Constants

Use `app.constants.trading.INDEX_TOKENS` for well-known index tokens:
```python
from app.constants.trading import INDEX_TOKENS
nifty_token = INDEX_TOKENS["NIFTY"]  # 256265
```

