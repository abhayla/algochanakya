---
name: add-new-broker
description: >
  Add a new broker integration to AlgoChanakya. Walks through creating adapter classes,
  factory registration, database migration, and frontend settings. Zero route changes required.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<broker-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add New Broker Integration

## STEP 1: Create Order Execution Adapter

Create `backend/app/services/brokers/<broker>_adapter.py`:

```python
from app.services.brokers.base import BrokerAdapter, BrokerType, UnifiedOrder, UnifiedPosition, UnifiedQuote

class <Broker>Adapter(BrokerAdapter):
    """<Broker> order execution adapter."""
    
    def __init__(self, access_token: str, client_id: str = None):
        self.access_token = access_token
        self.client_id = client_id
        self._client = None
    
    async def initialize(self) -> bool:
        # Initialize SDK client
        ...
        return True
    
    async def place_order(self, **kwargs) -> UnifiedOrder:
        # Convert to broker format, place, convert response to UnifiedOrder
        ...
    
    async def get_positions(self) -> list[UnifiedPosition]:
        # Fetch and convert to UnifiedPosition list
        ...
    
    async def get_orders(self) -> list[UnifiedOrder]:
        ...
    
    async def cancel_order(self, order_id: str) -> bool:
        ...
```

Key: ALL responses MUST be converted to Unified* models. Use `Decimal` for prices.

## STEP 2: Create Market Data Adapter

Create `backend/app/services/brokers/market_data/<broker>_adapter.py`:

```python
from app.services.brokers.market_data.market_data_base import MarketDataBrokerAdapter

class <Broker>MarketDataAdapter(MarketDataBrokerAdapter):
    # Implement: get_live_quote, get_historical_data, get_instruments
    # All symbols MUST use canonical (Kite) format internally
    # Use SymbolConverter for broker-specific symbols
```

## STEP 3: Create Ticker Adapter

Create `backend/app/services/brokers/market_data/ticker/adapters/<broker>.py`:

```python
from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.models import NormalizedTick

class <Broker>TickerAdapter(TickerAdapter):
    # WebSocket connection to broker
    # Convert native ticks to NormalizedTick (Decimal prices, canonical tokens)
    # Handle reconnection and heartbeat
```

## STEP 4: Register in Factories

1. Order execution factory (`backend/app/services/brokers/factory.py`):
   ```python
   from app.services.brokers.<broker>_adapter import <Broker>Adapter
   _BROKER_ADAPTERS[BrokerType.<BROKER>] = <Broker>Adapter
   ```

2. Market data factory (`backend/app/services/brokers/market_data/factory.py`):
   ```python
   # Add to market data adapter registry
   ```

3. Ticker pool registration in `backend/app/main.py` lifespan:
   ```python
   pool.register_adapter("<broker>", <Broker>TickerAdapter)
   ```

## STEP 5: Add BrokerType Enum (if new)

In `backend/app/services/brokers/base.py`:
```python
class BrokerType(str, Enum):
    ...
    <BROKER> = "<broker>"
```

## STEP 6: Database Migration (if credentials needed)

1. Create credentials model (e.g., `backend/app/models/<broker>_credentials.py`)
2. Import in `models/__init__.py` AND `alembic/env.py`
3. Generate migration: `alembic revision --autogenerate -m "add <broker> credentials table"`
4. Apply: `alembic upgrade head`

## STEP 7: Update Frontend Settings

Add broker option to `frontend/src/components/settings/BrokerSettings.vue`:
- Add to broker dropdown list
- Create `<Broker>Settings.vue` component for broker-specific credentials form

## STEP 8: Write Tests

1. Order adapter tests: `backend/tests/backend/brokers/test_<broker>_order_adapter.py`
2. Market data tests: `backend/tests/backend/brokers/test_<broker>_market_data_adapter.py`
3. Ticker adapter tests: `backend/tests/backend/brokers/test_<broker>_ticker_adapter.py`

## STEP 9: Update Broker Name Mapping

If the DB name differs from enum value, add to the broker name mapping in relevant utilities.

## STEP 10: Token Policy Integration

When adding a new broker adapter, you MUST also:

1. **Add error classification** in `backend/app/services/brokers/market_data/ticker/token_policy.py`:
   - Add broker's error codes to `_BROKER_ERRORS` dict
   - Classify each error as RETRYABLE, RETRYABLE_ONCE, NOT_RETRYABLE, or NOT_REFRESHABLE
   - If broker supports auto-refresh, add to `_AUTO_REFRESHABLE_BROKERS` set
   - Add frontend notification message in `get_frontend_notification()` if NOT_REFRESHABLE

2. **Register in health monitor** in `backend/app/main.py` lifespan:
   - Add `ticker_health.register_adapter("new_broker")` in startup sequence

3. **Wire error reporting** in the adapter:
   - Call `self._report_error()` in error handlers
   - Call `self._report_auth_error()` for authentication failures with the broker's error code

## CRITICAL RULES

- ZERO changes to routes or business logic — all broker specifics are encapsulated in adapters
- ALL prices in Decimal, ALL symbols in canonical (Kite) format
- Adapter MUST handle rate limiting internally
- Ticker adapter MUST produce NormalizedTick with Decimal prices
- Test with mock responses first, then live integration tests with `@pytest.mark.live`

