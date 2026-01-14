# Broker Abstraction Layer

This directory contains the broker abstraction layer for AlgoChanakya's multi-broker architecture.

## ⚠️ IMPORTANT: Read Before Modifying

**Before making any changes to this directory:**
1. **Read:** [docs/architecture/broker-abstraction.md](../../../../docs/architecture/broker-abstraction.md)
2. **Check:** [docs/IMPLEMENTATION-CHECKLIST.md](../../../../docs/IMPLEMENTATION-CHECKLIST.md) for current Phase
3. **Review:** [ADR-002: Multi-Broker Abstraction](../../../../docs/decisions/002-broker-abstraction.md) for rationale

## Architecture Overview

AlgoChanakya uses a **dual broker system**:
- **Market Data Brokers** - Live prices, historical OHLC, WebSocket ticks
- **Order Execution Brokers** - Placing orders, managing positions

Users can mix and match (e.g., Angel One for FREE data + Zerodha for order execution).

## Files in This Directory

| File | Purpose |
|------|---------|
| `base.py` | `BrokerAdapter` abstract interface + unified data models |
| `factory.py` | Factory function `get_broker_adapter()` |
| `kite_adapter.py` | Zerodha Kite Connect implementation |
| `__init__.py` | Public API exports |

## Current Implementation Status

**✅ Complete:**
- BrokerAdapter interface
- UnifiedOrder, UnifiedPosition, UnifiedQuote models
- KiteAdapter implementation
- Factory pattern

**🚧 In Progress:**
- Market data abstraction (separate from order execution)
- Refactoring API routes to use factory
- AngelAdapter for Angel One order execution
- Ticker service abstraction

**See:** [Implementation Checklist](../../../../docs/IMPLEMENTATION-CHECKLIST.md) for detailed tasks

## Usage

### ✅ Correct (Use This)

```python
from app.services.brokers.factory import get_broker_adapter

# Get broker adapter for user
adapter = get_broker_adapter(
    broker_type=user.order_broker_type,
    credentials=broker_credentials
)

# Place order - returns UnifiedOrder
order = await adapter.place_order(
    tradingsymbol="NIFTY2540125000CE",
    exchange="NFO",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    product=ProductType.NRML,
    quantity=25
)
```

### ❌ Wrong (Don't Do This)

```python
# NEVER use broker-specific APIs directly
from kiteconnect import KiteConnect  # ❌ Wrong
kite = KiteConnect(api_key=...)
kite.place_order(...)  # ❌ Bypasses abstraction

from app.services.kite_orders import KiteOrderService  # ❌ Wrong (legacy)
service = KiteOrderService()
service.place_order(...)  # ❌ Doesn't use abstraction
```

## Adding a New Broker

**Example: Adding Upstox support**

1. Create adapter file: `upstox_adapter.py`
   ```python
   from .base import BrokerAdapter, UnifiedOrder

   class UpstoxAdapter(BrokerAdapter):
       async def place_order(self, ...) -> UnifiedOrder:
           # Convert to Upstox API format
           upstox_response = await self.client.place_order(...)
           # Convert to UnifiedOrder
           return UnifiedOrder(...)
   ```

2. Register in factory: `factory.py`
   ```python
   _BROKER_ADAPTERS = {
       BrokerType.KITE: KiteAdapter,
       BrokerType.UPSTOX: UpstoxAdapter,  # Add here
   }
   ```

3. Add credentials table (if needed)
   ```python
   # backend/app/models/upstox_credentials.py
   class UpstoxCredentials(Base):
       __tablename__ = "upstox_credentials"
       ...
   ```

4. Create migration
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add Upstox credentials table"
   alembic upgrade head
   ```

**That's it!** No changes to routes or business logic needed.

## Unified Data Models

All broker adapters convert to/from these broker-agnostic models:

- **UnifiedOrder** - Normalized order (order_id, tradingsymbol, side, status, etc.)
- **UnifiedPosition** - Normalized position (quantity, pnl, average_price, etc.)
- **UnifiedQuote** - Normalized quote (last_price, ohlc, volume, bid/ask, etc.)

See `base.py` for complete definitions.

## Common Pitfalls

❌ **Direct broker API usage in routes**
- NEVER import `KiteConnect`, `SmartAPI`, or `KiteOrderService` in route files
- ALWAYS use `get_broker_adapter()` factory

❌ **Hardcoded broker assumptions**
- Code should work with ANY broker, not just Kite or SmartAPI
- Don't assume Kite-specific fields or behavior

❌ **Mixing concerns**
- Keep market data separate from order execution (dual system)
- Don't put market data logic in order execution adapters

## Testing

```bash
# Unit tests for adapters
cd backend
pytest tests/unit/test_broker_adapters.py -v

# E2E tests for order flow
cd ../..
npm run test:specs:positions
```

## Documentation

- **Architecture:** [docs/architecture/broker-abstraction.md](../../../../docs/architecture/broker-abstraction.md)
- **Decision Record:** [ADR-002](../../../../docs/decisions/002-broker-abstraction.md)
- **Implementation Tasks:** [docs/IMPLEMENTATION-CHECKLIST.md](../../../../docs/IMPLEMENTATION-CHECKLIST.md)
- **Quick Reference:** [docs/DEVELOPER-QUICK-REFERENCE.md](../../../../docs/DEVELOPER-QUICK-REFERENCE.md)

---

**Questions?** Check [CLAUDE.md](../../../../CLAUDE.md) for common patterns and pitfalls.
