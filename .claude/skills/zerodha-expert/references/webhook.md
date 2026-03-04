# Kite Connect Webhook Reference

> Source: Kite Connect v3 Official Docs | Last verified: 2026-02-25

## Overview

Kite Connect does **NOT support HTTP webhooks** for order or trade notifications.

There is no mechanism to register a URL that Zerodha will call when orders execute.

## Available Alternatives

### 1. KiteTicker WebSocket (Market Data)

Use the KiteTicker WebSocket for live market data updates. This is for **price/tick data**, not order updates.

See [websocket-protocol.md](./websocket-protocol.md) for full details.

### 2. REST Polling for Order Updates

Poll the order book periodically to check order status:

```python
import asyncio

async def poll_order_status(kite, order_id, interval_seconds=2):
    """Poll order status until filled, rejected, or cancelled."""
    terminal_statuses = {"COMPLETE", "REJECTED", "CANCELLED"}

    while True:
        orders = kite.orders()
        for order in orders:
            if order["order_id"] == order_id:
                status = order["status"]
                if status in terminal_statuses:
                    return order
        await asyncio.sleep(interval_seconds)
```

### 3. AlgoChanakya Order Tracking

AlgoChanakya's AutoPilot module handles order tracking:
- Polls order status at configurable intervals
- Updates order status in database
- Emits WebSocket events to frontend for real-time UI updates

## Why No Webhooks?

Zerodha's design philosophy is to keep the API simple and stateless:
- Webhooks require maintaining a server with public URL
- Many retail traders don't have server infrastructure
- KiteTicker + polling covers 99% of use cases

## Comparison with Other Brokers

| Broker | Webhooks | Order WS | Polling |
|--------|----------|----------|---------|
| Kite | No | No | Yes |
| Upstox | Yes (HTTP POST) | No | Yes |
| SmartAPI | No | Yes (WS) | Yes |
| Dhan | Yes (Postback) | Yes | Yes |
| Fyers | No | Yes (Order Socket) | Yes |
| Paytm | No | No | Yes |
