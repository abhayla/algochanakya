---
description: >
  Financial prices MUST use Decimal (not float) to prevent floating-point precision errors.
  Enforced in NormalizedTick, UnifiedQuote, and position P&L calculations.
globs: ["backend/**/*.py"]
synthesized: true
private: false
---

# Decimal Not Float for Prices

## Rule

All financial price values MUST use `Decimal` from the `decimal` module, not `float`.

## Where This Applies

- `NormalizedTick` — all price fields (`ltp`, `open`, `high`, `low`, `close`, `change`) are `Decimal`
- `UnifiedQuote` — `last_price`, `bid_price`, `ask_price` are `Decimal`
- `UnifiedPosition` — `average_price`, `pnl`, `buy_value`, `sell_value` are `Decimal`
- Position P&L calculations in autopilot services
- Kelly Criterion calculations in `kelly_calculator.py`
- Risk state thresholds (`DRAWDOWN_DEGRADED_THRESHOLD = Decimal("10.00")`)

## Why This Matters

Options trading involves small price differences that compound across lots. A `float` rounding
error of ₹0.05 on NIFTY with 75 lots = ₹3.75 per trade, which accumulates to significant
P&L drift over hundreds of trades.

## Conversion Rules

- When receiving data from broker APIs (which return float), convert immediately:
  ```python
  ltp = Decimal(str(raw_tick["ltp"]))  # NOT Decimal(raw_tick["ltp"])
  ```
- When serializing to JSON for WebSocket/API responses, convert to float at the boundary:
  ```python
  def to_dict(self):
      return {"ltp": float(self.ltp), ...}
  ```
- Use `Decimal(str(value))` instead of `Decimal(value)` to avoid float representation artifacts

## Exception

`float` is acceptable in:
- Black-Scholes/Newton-Raphson calculations in `greeks_calculator.py` (math library requires float)
- Technical indicator calculations in `indicators.py` (numpy/scipy require float)
- Display-only formatting

