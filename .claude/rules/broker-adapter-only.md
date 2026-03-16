---
description: >
  All broker interactions MUST go through factory adapters (get_broker_adapter, get_market_data_adapter),
  never direct SDK imports like KiteConnect or SmartAPI client.
globs: ["backend/**/*.py"]
synthesized: true
private: false
---

# Broker Adapter Only

## MUST Use Factory Pattern

All broker interactions in routes, services, and background tasks MUST use the factory functions:

```python
# Order execution
from app.services.brokers.factory import get_broker_adapter
adapter = await get_broker_adapter(broker_type, access_token, api_key)
order = await adapter.place_order(...)  # Returns UnifiedOrder

# Market data
from app.services.brokers.market_data.factory import get_market_data_adapter
data_adapter = get_market_data_adapter(broker_type, credentials)
quote = await data_adapter.get_live_quote(symbol)  # Returns UnifiedQuote
```

## MUST NOT Import Broker SDKs Directly

```python
# NEVER do this in routes or services:
from kiteconnect import KiteConnect
from smartapi import SmartConnect
from dhanhq import DhanHQ
```

The only files permitted to import broker SDKs are the adapter implementations themselves
(e.g., `kite_adapter.py`, `smartapi_adapter.py`).

## Why This Matters

- Adding a new broker requires ZERO changes to routes or business logic
- All broker responses are normalized to `UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`
- Rate limiting, error handling, and credential management are encapsulated in adapters
- Direct SDK usage bypasses the dual-broker architecture (market data vs order execution)

## Unified Data Models

All adapters convert to/from these broker-agnostic models defined in `app/services/brokers/base.py`:
- `UnifiedOrder` — normalized order (order_id, tradingsymbol, side, status)
- `UnifiedPosition` — normalized position (quantity, pnl, average_price)
- `UnifiedQuote` — normalized quote (last_price, ohlc, volume, bid/ask)

## Dual Broker System

Market data and order execution are independent systems:
- `BrokerAdapter` (order execution): `app/services/brokers/base.py`
- `MarketDataBrokerAdapter` (market data): `app/services/brokers/market_data/market_data_base.py`

A user can use SmartAPI for market data and Kite for order execution simultaneously.
NEVER cross concerns between these two adapter hierarchies.

