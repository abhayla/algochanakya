# Ticker Adapter Rules

> Applies to all files in `ticker/adapters/`. Read before modifying any adapter.

## NormalizedTick Field Names (CRITICAL)

`NormalizedTick` fields are **not** named after Kite/REST conventions.
Always use these exact names:

| Field | ✅ Correct | ❌ Wrong (do not use) |
|-------|-----------|----------------------|
| Instrument token | `tick.token` | `tick.instrument_token`, `tick.instrument` |
| Last traded price | `tick.ltp` | `tick.last_price`, `tick.price`, `tick.ltp_price` |
| Broker source | `tick.broker_type` | `tick.broker`, `tick.source` |

```python
# ✅ Correct
assert isinstance(tick.ltp, Decimal)
received_tokens = {tick.token for tick in ticks}

# ❌ Wrong — will raise AttributeError
assert isinstance(tick.last_price, Decimal)
received_tokens = {tick.instrument_token for tick in ticks}
```

## Price Units: Always Rupees (NEVER Paise)

All prices in `NormalizedTick` MUST be in rupees. Adapters are responsible for
converting paise → rupees when the broker returns paise.

- SmartAPI: returns prices in paise — divide by 100
- Kite: returns prices in paise — divide by 100
- Dhan, Fyers, Upstox, Paytm: returns rupees — no division

## Token: Always Canonical (Kite) Token

`NormalizedTick.token` MUST be the canonical Kite instrument token (integer), not
a broker-specific token. Adapters must translate via `load_token_map()`.

```python
# SmartAPI → canonical mapping example
adapter.load_token_map({
    256265: ("99926000", 1),   # NIFTY 50: canonical 256265 ← SmartAPI "99926000"
    260105: ("99926009", 1),   # NIFTY BANK: canonical 260105 ← SmartAPI "99926009"
})
```

## Adapter Interface

Every adapter must implement `TickerAdapter` ABC from `ticker/adapter_base.py`:
- `connect(credentials: dict) -> None`
- `disconnect() -> None`
- `subscribe(tokens: List[int], mode: str) -> None`
- `unsubscribe(tokens: List[int]) -> None`
- `set_on_tick_callback(callback: Callable) -> None`
- `set_event_loop(loop: asyncio.AbstractEventLoop) -> None`
- `is_connected: bool` (property)
- `subscribed_tokens: Set[int]` (property)
- `broker_type: str` (property)
- `load_token_map(mapping: dict) -> None`
