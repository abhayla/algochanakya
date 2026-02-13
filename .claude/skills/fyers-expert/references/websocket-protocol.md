# Fyers WebSocket Protocol

Complete WebSocket reference for Fyers API v3 dual WebSocket system.

## Dual WebSocket Architecture

Fyers uses **two independent WebSocket connections** -- unique among Indian brokers:

| Socket | SDK Class | Purpose | Data Format |
|--------|-----------|---------|-------------|
| **FyersDataSocket** | `data_ws.FyersDataSocket` | Market data ticks | JSON |
| **FyersOrderSocket** | `order_ws.FyersOrderSocket` | Order status updates | JSON |

## Connection Limits

| Limit | Value | Comparison |
|-------|-------|------------|
| Max symbols | **200** per connection | SmartAPI: 3000, Kite: 3000 |
| Max connections | **1** per socket type | SmartAPI: 3, Kite: 3 |
| Message format | **JSON** (not binary) | SmartAPI/Kite: binary |
| Price unit | **RUPEES** | SmartAPI/Kite: PAISE |
| Data types | SymbolUpdate, DepthUpdate | |

---

## FyersDataSocket (Market Data)

### Full Connection Example

```python
from fyers_apiv3.FyersWebsocket import data_ws

def on_message(message):
    """Tick callback - message is a dict (JSON parsed by SDK)."""
    print(f"Symbol: {message['symbol']}, LTP: {message['ltp']}")

def on_error(message):
    print(f"Data WS Error: {message}")

def on_close(message):
    print(f"Data WS Closed: {message}")

def on_open():
    print("Data WS Connected")
    symbols = ["NSE:NIFTY2522725000CE", "NSE:NIFTY50-INDEX"]
    data_socket.subscribe(symbols=symbols, data_type="SymbolUpdate")

data_socket = data_ws.FyersDataSocket(
    access_token=f"{app_id}:{access_token}",  # Colon-separated!
    log_path="",
    litemode=False,       # False=full data, True=LTP only
    write_to_file=False,
    reconnect=True,       # Auto-reconnect on disconnect
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open
)
data_socket.keep_running()  # Blocking call - run in thread
```

### Subscribe / Unsubscribe

```python
data_socket.subscribe(symbols=["NSE:NIFTY2522725000CE"], data_type="SymbolUpdate")
data_socket.subscribe(symbols=["NSE:NIFTY2522725000CE"], data_type="DepthUpdate")
data_socket.unsubscribe(symbols=["NSE:NIFTY2522725000CE"], data_type="SymbolUpdate")
data_socket.close_connection()
```

### SymbolUpdate Message (type="sf")

```json
{
  "symbol": "NSE:NIFTY2522725000CE",
  "fyToken": "101010000012345",
  "timestamp": 1709119800,
  "ltp": 150.25,
  "open_price": 145.00,
  "high_price": 155.50,
  "low_price": 142.00,
  "prev_close_price": 148.75,
  "ch": 1.50,
  "chp": 1.01,
  "vol_traded_today": 1250000,
  "last_traded_qty": 50,
  "last_traded_time": 1709119790,
  "bid_price": 150.20,
  "bid_size": 500,
  "ask_price": 150.30,
  "ask_size": 400,
  "oi": 500000,
  "pdoi": 480000,
  "oipercent": 4.17,
  "type": "sf"
}
```

### DepthUpdate Message (type="dp")

Extends SymbolUpdate with 5-level market depth:

```json
{
  "...": "all SymbolUpdate fields",
  "type": "dp",
  "bids": [
    {"price": 150.20, "volume": 500, "ord": 3},
    {"price": 150.15, "volume": 750, "ord": 5}
  ],
  "asks": [
    {"price": 150.30, "volume": 400, "ord": 2},
    {"price": 150.35, "volume": 600, "ord": 4}
  ]
}
```

### Lite Mode (litemode=True)

Sends only LTP data (reduced bandwidth): `{ "symbol": "...", "ltp": 150.25, "timestamp": ..., "type": "sf" }`

---

## FyersOrderSocket (Order Updates)

### Connection Example

```python
from fyers_apiv3.FyersWebsocket import order_ws

def on_order_update(message):
    print(f"Order {message['id']}: status={message['status']}, "
          f"symbol={message['symbol']}, filled={message['filledQty']}")

def on_error(message):
    print(f"Order WS Error: {message}")

order_socket = order_ws.FyersOrderSocket(
    access_token=f"{app_id}:{access_token}",
    write_to_file=False,
    on_order_update=on_order_update,
    on_error=on_error,
    on_close=lambda m: print(f"Closed: {m}"),
    on_open=lambda: print("Order WS Connected")
)
order_socket.connect()  # Blocking call - run in thread
```

### Order Update Message

```json
{
  "id": "808058117761",
  "symbol": "NSE:NIFTY2522725000CE",
  "qty": 25, "filledQty": 25,
  "type": 2, "side": 1,
  "productType": "INTRADAY",
  "status": 2, "tradedPrice": 150.25,
  "orderTag": "algochanakya"
}
```

**Status values:** `1`=Cancelled, `2`=Traded, `4`=Transit, `5`=Rejected, `6`=Pending

---

## AlgoChanakya Integration

### Adapter Pattern (TickerServiceBase)

```python
from app.services.brokers.market_data.ticker_base import TickerServiceBase
import threading

class FyersTickerAdapter(TickerServiceBase):
    """Wraps FyersDataSocket to implement TickerServiceBase."""

    def __init__(self, app_id: str, access_token: str):
        self._access_token = f"{app_id}:{access_token}"
        self._data_socket = None

    async def connect(self):
        from fyers_apiv3.FyersWebsocket import data_ws
        self._data_socket = data_ws.FyersDataSocket(
            access_token=self._access_token,
            litemode=False, reconnect=True, log_path="",
            write_to_file=False, on_message=self._on_tick,
        )
        # SDK blocks - run in daemon thread
        self._thread = threading.Thread(
            target=self._data_socket.keep_running, daemon=True
        )
        self._thread.start()

    async def subscribe(self, symbols: list[str], mode: str = "quote"):
        from app.services.brokers.market_data.symbol_converter import SymbolConverter
        fyers_syms = [SymbolConverter().from_canonical(s, "fyers") for s in symbols]
        data_type = "DepthUpdate" if mode == "full" else "SymbolUpdate"
        self._data_socket.subscribe(symbols=fyers_syms, data_type=data_type)

    async def unsubscribe(self, symbols: list[str]):
        from app.services.brokers.market_data.symbol_converter import SymbolConverter
        fyers_syms = [SymbolConverter().from_canonical(s, "fyers") for s in symbols]
        self._data_socket.unsubscribe(symbols=fyers_syms, data_type="SymbolUpdate")

    async def disconnect(self):
        if self._data_socket:
            self._data_socket.close_connection()

    def _on_tick(self, message: dict):
        """Convert Fyers tick to unified format."""
        unified = {
            "symbol": message["symbol"].split(":")[1],  # Strip prefix
            "ltp": message["ltp"],       # Already rupees
            "open": message.get("open_price", 0),
            "high": message.get("high_price", 0),
            "low": message.get("low_price", 0),
            "close": message.get("prev_close_price", 0),
            "volume": message.get("vol_traded_today", 0),
            "oi": message.get("oi", 0),
            "timestamp": message.get("timestamp", 0),
        }
        for callback in self._callbacks.values():
            callback(unified)
```

## Error Handling

| Scenario | Cause | Resolution |
|----------|-------|------------|
| Connection refused | Invalid `{app_id}:{access_token}` | Re-authenticate |
| Disconnect at midnight | Token expiry (midnight IST) | Get new token |
| No data after subscribe | Invalid symbol / missing prefix | Verify `NSE:` prefix |
| Silent subscription fail | >200 symbols | Stay under 200 limit |
| SDK crash | Wrong version | Use `fyers-apiv3` not v2 |
| Thread deadlock | `keep_running()` blocks | Run in daemon thread |

## Broker Comparison

| Feature | Fyers | SmartAPI | Kite |
|---------|-------|---------|------|
| Protocol | JSON (SDK) | Binary (raw WS) | Binary (raw WS) |
| Max symbols | 200 | 3000 | 3000 |
| Price unit | RUPEES | PAISE | PAISE |
| Order updates | Dedicated WS | REST polling | Postback URL |
| Depth levels | 5 (DepthUpdate) | 5 (Snap mode) | 5 (Full mode) |
