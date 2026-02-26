# Market Data Adapter Rules

> Applies to all files in `brokers/market_data/`. Read before modifying any adapter.

## Symbol Format: Bare Index Names (No "NSE:" Prefix)

`SmartAPIMarketDataAdapter.INDEX_SYMBOLS` contains bare names — **no exchange prefix**:

```python
# ✅ Correct
adapter.get_quote(["NIFTY 50", "NIFTY BANK"])

# ❌ Wrong — SmartAPI adapter will not recognize these
adapter.get_quote(["NSE:NIFTY 50", "NSE:NIFTY BANK"])
```

Other adapters (Kite, Upstox, Fyers) use broker-specific formats. Use `SymbolConverter`
to translate between canonical and broker formats.

## Prices: Always Decimal (NEVER float)

All price fields in `UnifiedQuote`, `OHLCBar`, and `NormalizedTick` must be `Decimal`,
not `float`. This is enforced at the adapter layer.

```python
# ✅ Correct
from decimal import Decimal
quote.last_price = Decimal(str(raw_price))

# ❌ Wrong
quote.last_price = float(raw_price)
```

## Historical Data: SmartAPI

- `SmartAPIHistorical.get_candles()` (not `get_historical()`)
- Dates must be strings in `"YYYY-MM-DD HH:MM"` format
- NSE exchange prices are in **rupees** (divisor = 1)
- NFO exchange prices are in **paise** (divisor = 100)

Index tokens are in `SmartAPIMarketDataAdapter._INDEX_HISTORICAL_MAP`:
```python
"NIFTY":     {"exchange": "NSE", "token": "99926000"}
"NIFTY BANK": {"exchange": "NSE", "token": "99926009"}
```

## AngelOne API Keys (3 separate keys!)

AngelOne uses 3 different API keys configured in `backend/.env`:

| Key | Purpose |
|-----|---------|
| `ANGEL_API_KEY` | Live market data (WebSocket, quotes) |
| `ANGEL_HIST_API_KEY` | Historical candle data (`getCandleData`) |
| `ANGEL_TRADE_API_KEY` | Order execution (`placeOrder`, etc.) |

`SmartAPIMarketDataAdapter` uses:
- `ANGEL_API_KEY` → `SmartAPIMarketData` (live quotes)
- `ANGEL_HIST_API_KEY` (falls back to `ANGEL_API_KEY`) → `SmartAPIHistorical`

Using the wrong key for an endpoint returns **AG8001 Invalid Token**.

## Access Errors: Skip, Don't Fail

AngelOne historical API returns `AG8001 Invalid Token` when:
- JWT is expired (8h expiry)
- API key lacks historical data permissions

Tests should convert these to `pytest.skip()` via `_get_historical_or_skip()`.
Do not fail tests on access/permission errors — they are config issues.

## Rate Limits

All adapters are wrapped by `RateLimiter`. Never bypass it. Per-broker limits:
- SmartAPI: 1 req/s
- Kite: 10 req/s
- Upstox: 50 req/s
- Dhan/Fyers/Paytm: 10 req/s
