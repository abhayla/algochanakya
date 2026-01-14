# Broker Abstraction Architecture

## Vision

AlgoChanakya is designed as a **broker-agnostic platform** where adding a new broker requires **zero code changes** - only configuration and adapter implementation. Users can mix-and-match brokers for cost optimization and reliability.

### Design Principles

1. **Separation of Concerns** - Market data and order execution are independent systems
2. **Abstraction via Interfaces** - All broker-specific logic encapsulated behind common interfaces
3. **Factory Pattern** - Runtime broker selection without conditional logic
4. **Unified Data Models** - Broker-agnostic data structures (UnifiedOrder, UnifiedQuote, etc.)

## Two Independent Broker Systems

The platform maintains **two separate broker abstractions** to allow maximum flexibility:

### 1. Market Data Brokers
**Purpose:** Live prices, historical OHLC, WebSocket ticks, instrument data

**Use Cases:**
- Real-time price streaming for watchlist, option chain, strategy builder
- Historical data for backtesting and charts
- Instrument token/symbol mapping

**Why Separate:** Many brokers offer free market data APIs but charge for trading APIs. Users may want to use a free data provider while executing orders through their funded broker account.

### 2. Order Execution Brokers
**Purpose:** Placing orders, managing positions, account margins

**Use Cases:**
- Order placement (market, limit, stop-loss)
- Order modification and cancellation
- Position tracking and P&L
- Account margin information

**Why Separate:** Order execution requires a funded broker account and may incur API fees. Separating allows users to optimize costs.

## Architecture Diagrams

The platform has **two independent broker systems** to allow maximum flexibility:

### Diagram 1: Market Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     MARKET DATA FLOW                        │
│         (Live Prices, Historical OHLC, WebSocket)           │
└─────────────────────────────────────────────────────────────┘

    Frontend (Watchlist, Option Chain, Strategy Builder)
                          │
                          ▼
              ┌───────────────────────┐
              │  MarketDataBroker     │
              │      Factory          │
              └───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  SmartAPI   │   │    Kite     │   │   Upstox    │
│  Adapter    │   │   Adapter   │   │   Adapter   │
│  (Default)  │   │             │   │  (Planned)  │
└─────────────┘   └─────────────┘   └─────────────┘
         │                │                │
         ▼                ▼                ▼
   Angel One API    Zerodha API      Upstox API
     (FREE)         (₹500/mo)          (FREE)
```

**Note:** Zerodha's "Connect" tier (₹500/month) provides live market data via WebSocket and historical data APIs.

### Diagram 2: Order Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   ORDER EXECUTION FLOW                      │
│       (Place Orders, Positions, Margins, P&L)               │
└─────────────────────────────────────────────────────────────┘

    Frontend (Strategy Deploy, Position Exit, AutoPilot)
                          │
                          ▼
              ┌───────────────────────┐
              │    OrderBroker        │
              │      Factory          │
              └───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│    Kite     │   │   Angel     │   │   Upstox    │
│   Adapter   │   │   Adapter   │   │   Adapter   │
│ (Implemented)│  │  (Planned)  │   │  (Planned)  │
└─────────────┘   └─────────────┘   └─────────────┘
         │                │                │
         ▼                ▼                ▼
   Zerodha API     Angel One API     Upstox API
     (FREE)           (FREE)           (FREE)

   Note: Order execution APIs are FREE for all brokers
         (uses user's funded broker account)
```

**Note:** All brokers provide free order execution APIs. Zerodha's "Personal" tier is completely free for orders, GTT, and portfolio management.

### Example: Completely FREE Setup

```
┌─────────────────────────────────────────────────────────────┐
│  EXAMPLE: User Configuration                                │
│                                                             │
│  market_data_broker: "smartapi"  ← FREE data from Angel One │
│  order_broker: "kite"            ← FREE orders via Zerodha  │
│                                                             │
│  Result: Completely FREE setup!                             │
│  (SmartAPI free data + Zerodha Personal API free orders)    │
└─────────────────────────────────────────────────────────────┘
```

## Supported Brokers

### Indian Brokers with Free APIs

| Broker | API Name | Market Data | Order Execution | Status |
|--------|----------|-------------|-----------------|--------|
| **Angel One** | SmartAPI | FREE | FREE | In Progress (Default data) |
| **Zerodha** | Kite Connect | ₹500/mo | FREE | Implemented |
| **Upstox** | Upstox API | FREE | FREE | Planned |
| **Fyers** | Fyers API | FREE | FREE | Planned |
| **Alice Blue** | ANT API | FREE | FREE | Planned |
| **Kotak** | Neo API | FREE | FREE | Planned |
| **Dhan** | DhanHQ API | FREE or ₹499/mo* | FREE | Planned |
| **Paytm Money** | Open API | FREE | FREE | Planned |
| **Samco** | Samco API | FREE | FREE | Planned |
| **Shoonya** (Finvasia) | Shoonya API | FREE | FREE | Planned (Zero brokerage) |
| **Pocketful** | Pocketful API | FREE | FREE | Planned |
| **TradeSmart** | TradeSmart API | FREE | FREE | Planned |
| **ICICI Direct** | Breeze API | FREE (Rate limited) | FREE | Planned |

**Note:**
- **Zerodha** offers two tiers: "Connect" (₹500/month for market data + orders) and "Personal" (FREE for orders only, no market data)
- **Dhan** Data APIs are FREE if you execute 25 F&O trades/month, otherwise ₹499/month + taxes
- **Paytm Money** requires a KYC-ready equity trading account; all APIs are free
- **Upstox** has rate limits of 50 requests/sec for OHLC data & quotes
- All other brokers listed offer free API access for both market data and order execution
- Order execution requires a funded broker account for all brokers

## Current Implementation Status

### ✅ Implemented

#### Order Execution Abstraction
- **File:** `backend/app/services/brokers/base.py`
- **Interface:** `BrokerAdapter` (abstract base class)
- **Data Models:** `UnifiedOrder`, `UnifiedPosition`, `UnifiedQuote`, `BrokerCapabilities`
- **Factory:** `backend/app/services/brokers/factory.py` - `get_broker_adapter()`
- **Implementation:** `KiteAdapter` in `backend/app/services/brokers/kite_adapter.py`

#### Market Data (Partial)
- **SmartAPI Services:**
  - `backend/app/services/smartapi_auth.py` - Authentication with auto-TOTP
  - `backend/app/services/smartapi_ticker.py` - WebSocket V2 for live prices
  - `backend/app/services/smartapi_market_data.py` - REST API quotes
  - `backend/app/services/smartapi_historical.py` - Historical OHLCV data
  - `backend/app/services/smartapi_instruments.py` - Instrument lookup
- **Kite Services:**
  - `backend/app/services/kite_ticker.py` - WebSocket ticker (singleton)
  - `backend/app/services/kite_orders.py` - Direct Kite service (legacy)

**⚠️ Implementation Note:** While `BrokerAdapter` and `KiteAdapter` exist, the API routes (`auth.py`, `orders.py`, `positions.py`, `ofo.py`, `optionchain.py`, `strategy_wizard.py`) still use `KiteOrderService`, `KiteConnect`, and `SmartAPIMarketData` directly. Route refactoring to use `get_broker_adapter()` factory is pending.

### 🚧 To Be Implemented

#### Market Data Abstraction
- [ ] Create `MarketDataBrokerAdapter` interface in `backend/app/services/brokers/market_data/base.py`
- [ ] Define abstract methods:
  - `get_live_quote(symbol)` - Get real-time quote
  - `get_historical_data(symbol, from_date, to_date, interval)` - OHLCV data
  - `subscribe_ticks(symbols, callback)` - WebSocket subscription
  - `unsubscribe_ticks(symbols)` - WebSocket unsubscription
  - `search_instruments(query)` - Instrument search
- [ ] Create `SmartAPIMarketDataAdapter` implementing the interface
- [ ] Create `KiteMarketDataAdapter` implementing the interface
- [ ] Create factory: `get_market_data_adapter(broker_type, credentials)`

#### Order Execution Completion
- [ ] Create `AngelAdapter` (Angel One for orders) in `backend/app/services/brokers/angel_adapter.py`
- [ ] Refactor API routes to use `get_broker_adapter()` instead of hardcoded `KiteOrderService` and `KiteConnect`:
  - `backend/app/api/routes/auth.py` - 7 instances of direct `KiteConnect` instantiation
  - `backend/app/api/routes/orders.py` - Uses `KiteOrderService` directly
  - `backend/app/api/routes/positions.py` - Uses `KiteOrderService` directly
  - `backend/app/api/routes/ofo.py` - Uses `KiteOrderService` and `SmartAPIMarketData` directly
  - `backend/app/api/routes/optionchain.py` - Uses `KiteOrderService` and direct `KiteConnect`
  - `backend/app/api/routes/strategy_wizard.py` - Direct `KiteConnect` for LTP calls
- [ ] Refactor `OrderExecutor` to accept `BrokerAdapter` instead of `KiteConnect`

#### Ticker Service Abstraction
- [ ] Create `TickerService` interface in `backend/app/services/brokers/ticker/base.py`
- [ ] Make `KiteTickerService` implement `TickerService`
- [ ] Make `SmartAPITickerService` implement `TickerService`
- [ ] Create factory/registry for ticker selection

#### User Configuration
- [ ] Add `market_data_broker` and `order_execution_broker` to `users` table
- [ ] Frontend settings UI for broker selection
- [ ] Store broker-specific credentials (encrypted)

## Unified Data Models

All broker adapters convert broker-specific responses to these unified models:

### UnifiedOrder
```python
@dataclass
class UnifiedOrder:
    order_id: str              # Broker's order ID
    tradingsymbol: str         # NFO symbol (e.g., "NIFTY2540125000CE")
    exchange: str              # "NFO", "NSE", etc.
    side: OrderSide            # BUY/SELL
    order_type: OrderType      # MARKET/LIMIT/SL/SL-M
    product: ProductType       # NRML/MIS
    quantity: int
    price: Optional[Decimal]
    status: OrderStatus        # PENDING/OPEN/COMPLETE/CANCELLED/REJECTED
    filled_quantity: int
    average_price: Optional[Decimal]
    # ... (see backend/app/services/brokers/base.py for full definition)
```

### UnifiedPosition
```python
@dataclass
class UnifiedPosition:
    tradingsymbol: str
    exchange: str
    product: ProductType
    quantity: int              # Net quantity (can be negative)
    average_price: Decimal
    last_price: Decimal
    pnl: Decimal              # Realized + Unrealized P&L
    # ... (see base.py for full definition)
```

### UnifiedQuote
```python
@dataclass
class UnifiedQuote:
    instrument_token: int
    tradingsymbol: str
    last_price: Decimal
    volume: int
    buy_quantity: int
    sell_quantity: int
    ohlc: Dict[str, Decimal]  # open, high, low, close
    # ... (see base.py for full definition)
```

## Adding a New Broker (Future State)

Once the abstraction is complete, adding a new broker will follow this process:

### For Market Data Broker

1. **Create Adapter** (`backend/app/services/brokers/market_data/<broker>_adapter.py`):
```python
from .base import MarketDataBrokerAdapter

class UpstoxMarketDataAdapter(MarketDataBrokerAdapter):
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = UpstoxClient(access_token)

    async def get_live_quote(self, symbol: str) -> UnifiedQuote:
        # Convert to broker-specific symbol format
        broker_symbol = self._map_symbol(symbol)
        # Fetch quote from broker API
        quote = await self.client.get_quote(broker_symbol)
        # Convert to UnifiedQuote
        return UnifiedQuote(
            tradingsymbol=symbol,
            last_price=Decimal(str(quote['ltp'])),
            # ... map other fields
        )

    # Implement other abstract methods...
```

2. **Register in Factory** (`backend/app/services/brokers/market_data/factory.py`):
```python
_MARKET_DATA_ADAPTERS = {
    BrokerType.SMARTAPI: SmartAPIMarketDataAdapter,
    BrokerType.KITE: KiteMarketDataAdapter,
    BrokerType.UPSTOX: UpstoxMarketDataAdapter,  # Add here
}
```

3. **Add Credentials Table** (if needed):
```python
# In backend/app/models/upstox_credentials.py
class UpstoxCredentials(Base):
    __tablename__ = "upstox_credentials"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token_encrypted = Column(String)
    # ... other fields
```

4. **Create Migration**:
```bash
cd backend
alembic revision --autogenerate -m "Add Upstox credentials table"
alembic upgrade head
```

5. **Update Frontend Settings** (`frontend/src/components/settings/BrokerSettings.vue`):
```vue
<select v-model="marketDataBroker">
  <option value="smartapi">Angel One (SmartAPI)</option>
  <option value="kite">Zerodha (Kite)</option>
  <option value="upstox">Upstox</option>  <!-- Add here -->
</select>
```

**That's it!** No changes to routes, services, or business logic.

### For Order Execution Broker

Same process, but implement `BrokerAdapter` interface from `backend/app/services/brokers/base.py`.

## Implementation Roadmap

### Phase 1: Complete SmartAPI Market Data (Current)
- ✅ SmartAPI authentication with auto-TOTP
- ✅ SmartAPI WebSocket ticker
- ✅ Historical data fetching
- ✅ Instrument lookup

### Phase 2: Market Data Abstraction
- Create `MarketDataBrokerAdapter` interface
- Wrap SmartAPI services in adapter
- Create KiteMarketDataAdapter
- Update routes to use factory

### Phase 3: Order Execution Completion
- Create `AngelAdapter` for Angel One orders
- Refactor routes to use broker factory
- Remove hardcoded `KiteOrderService` usage

### Phase 4: Additional Brokers
- Add Upstox, Fyers, Alice Blue, Dhan, etc.
- One broker per sprint
- Prioritize by user demand

### Phase 5: Ticker Abstraction
- Create `TickerService` interface
- Refactor existing ticker services
- Unified WebSocket management

## Key Design Decisions

### Why Two Separate Systems?

**Alternative 1:** Single unified broker interface handling both data and orders
- **Rejected:** Forces users to have same broker for both concerns, limiting cost optimization

**Alternative 2:** Each feature can use any broker
- **Rejected:** Too complex, no real use case for mixing brokers within same concern

**Chosen:** Two separate systems (data vs orders)
- **Rationale:** Most users want free data provider + their funded broker for orders
- **Benefit:** Clear separation of concerns, easier testing

### Why Factory Pattern?

**Alternative 1:** Dependency injection container
- **Rejected:** Overkill for Python/FastAPI, adds complexity

**Alternative 2:** Strategy pattern with manual instantiation
- **Rejected:** Requires conditional logic in every route

**Chosen:** Simple factory with broker type enum
- **Rationale:** Pythonic, easy to understand, minimal boilerplate
- **Benefit:** Centralized broker instantiation logic

### Why Unified Data Models?

**Alternative:** Use broker-specific models throughout app
- **Rejected:** Couples entire app to broker APIs

**Chosen:** Convert at adapter boundary
- **Rationale:** Business logic remains broker-agnostic
- **Benefit:** Easy to add new brokers without changing core logic

## Common Challenges

### Symbol/Token Mapping

Different brokers use different symbol formats and token IDs:
- Kite: `NIFTY2540125000CE`, token `12345678`
- Angel: `NIFTY 25 APR 25000 CE`, token `87654321`

**Solution:** Maintain symbol mapping table in database:
```python
class BrokerSymbolMapping(Base):
    __tablename__ = "broker_symbol_mappings"
    our_symbol = Column(String)        # "NIFTY2540125000CE"
    broker_type = Column(String)       # "kite", "smartapi"
    broker_symbol = Column(String)     # Broker-specific format
    broker_token = Column(Integer)     # Broker-specific token
```

### WebSocket Connection Limits

Brokers limit concurrent WebSocket connections per API key.

**Solution:**
- Use singleton ticker services
- Share WebSocket connections across users
- Implement connection pooling if needed

### Rate Limiting

Brokers enforce rate limits on API calls.

**Solution:**
- Implement caching for frequently accessed data (quotes, instruments)
- Use Redis for cross-process rate limiting
- Batch API calls where possible

## Testing Strategy

### Unit Tests
- Mock broker APIs
- Test adapter conversion logic
- Test factory instantiation

### Integration Tests
- Test against sandbox/test APIs provided by brokers
- Verify unified data models match expectations
- Test error handling for broker-specific errors

### E2E Tests
- Use auth fixtures to test with real broker credentials
- Test broker selection in UI
- Verify orders placed through abstraction layer

## Related Documentation

- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) - Decision rationale
- [ADR-001: Tech Stack Selection](../decisions/001-tech-stack.md) - Original tech choices
- [Authentication Architecture](./authentication.md) - Broker OAuth/credential storage
- [WebSocket Architecture](./websocket.md) - Live price streaming design
- [Database Schema](./database.md) - Broker-related tables

## References

- [Angel One SmartAPI Docs](https://smartapi.angelbroking.com/docs/)
- [Zerodha Kite Connect Docs](https://kite.trade/docs/connect/v3/)
- [Upstox API Docs](https://upstox.com/developer/api-documentation/)
- [Fyers API Docs](https://api-docs.fyers.in/)
- [Design Patterns: Factory Method](https://refactoring.guru/design-patterns/factory-method)
