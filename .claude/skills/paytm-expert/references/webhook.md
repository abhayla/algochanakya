# Paytm Money Webhook Reference

> Source: Paytm Money API Docs (https://developer.paytmmoney.com/docs/) | Last verified: 2026-02-25

## Overview

Paytm Money does **NOT support webhooks or push notifications** for order/trade events.

There is no mechanism for Paytm to call your URL when orders execute.

## Available Alternatives

### 1. REST Polling (Only Option)

Poll the order book to check order status:

```python
import time

def poll_paytm_order(client, order_no, max_polls=30, interval=2):
    """
    Poll Paytm Money order status.

    Note: Uses access_token, not read_access_token.
    """
    for _ in range(max_polls):
        response = client.get_order_book()
        orders = response.get("data", {}).get("order_book", [])

        for order in orders:
            if order.get("order_no") == order_no:
                status = order.get("order_status")
                if status in ["complete", "rejected", "cancelled"]:
                    return order

        time.sleep(interval)

    return None  # Timeout

# Usage
order_book_resp = paytm_client.get_order_book()
# Headers: x-jwt-token: {access_token}
# GET /orders/v1/order-book
```

### 2. AlgoChanakya AutoPilot Polling

AlgoChanakya's AutoPilot service polls order status for all active orders at configurable intervals.

## No Order Update WebSocket

Unlike Dhan (postback + WebSocket) and SmartAPI (order WS) and Fyers (order socket), Paytm Money provides:
- No HTTP webhooks
- No order update WebSocket
- REST polling only

This is a significant limitation compared to other brokers.

## Comparison: Order Update Mechanisms

| Broker | HTTP Webhook | Order WS | REST Polling |
|--------|-------------|----------|-------------|
| Paytm Money | No | No | Yes |
| Upstox | Yes | No | Yes |
| Dhan | Yes (Postback) | Yes | Yes |
| Fyers | No | Yes (Order Socket) | Yes |
| SmartAPI | No | Yes | Yes |
| Kite | No | No | Yes |

## AlgoChanakya Implementation

AlgoChanakya handles Paytm order tracking via REST polling:
- AutoPilot polls at 2-second intervals for active orders
- Order status updates propagated to frontend via WebSocket
- File: `backend/app/services/brokers/paytm_order_adapter.py`
