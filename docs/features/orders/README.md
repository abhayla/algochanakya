# Order Management

## Overview

Order placement and management functionality for executing trades via Zerodha Kite Connect API.

## Features

- **Basket Orders**: Multi-leg order execution
- **Position Import**: Import existing broker positions as strategies
- **LTP Fetching**: Get Last Traded Price for instruments
- **Order Types**: Market and Limit orders
- **Transaction Types**: Buy and Sell

## Used By Features

- Strategy Builder - Execute basket orders for multi-leg strategies
- Positions - Exit and add to positions
- AutoPilot - Automated order execution

## Technical Implementation

### Backend

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orders/basket` | Place basket order via Kite |
| GET | `/api/orders/positions` | Get positions from broker |
| POST | `/api/orders/import-positions` | Import positions as strategy |
| GET | `/api/orders/ltp` | Get LTP for instruments |

**Basket Order Request:**
```json
{
  "legs": [
    {
      "tradingsymbol": "NIFTY24DEC24500CE",
      "exchange": "NFO",
      "transaction_type": "BUY",
      "quantity": 75,
      "order_type": "LIMIT",
      "price": 150.50
    }
  ]
}
```

**Position Import:**
- Fetches current positions from Kite
- Creates strategy with existing positions
- Populates entry prices and quantities

### Integration

**Strategy Builder:**
```javascript
// Execute basket order
const response = await api.post('/api/orders/basket', {
  legs: strategyLegs
})
```

**Positions:**
```javascript
// Exit position
await api.post('/api/positions/exit', {
  tradingsymbol: 'NIFTY24DEC24500CE',
  exchange: 'NFO',
  quantity: 75,
  order_type: 'MARKET'
})
```

## Order Execution Flow

```
Strategy Builder
      ↓
Basket Order API
      ↓
Kite Connect API
      ↓
Order Placement
      ↓
Confirmation
```

## Error Handling

- Insufficient margin
- Invalid instrument token
- Market closed
- Order rejection

## Testing

```bash
# Test order endpoints
curl -X POST http://localhost:8000/api/orders/basket \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"legs": [...]}'
```

## Related

- [Strategy Builder](../strategy-builder/) - Multi-leg strategies
- [Positions](../positions/) - Position management
- [AutoPilot](../autopilot/) - Automated execution
