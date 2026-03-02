# Positions

## Overview

Real-time F&O positions display with MTM P/L, exit/add functionality, and portfolio summary.

## Screenshots

![Positions](../assets/screenshots/positions-pnl.png)

## Features

- **Day/Net Toggle**: View day or net positions
- **Live P/L**: Real-time MTM calculation
- **Auto Refresh**: 5-second auto-refresh toggle
- **Position Details**: Symbol, Qty, Avg Price, LTP, P/L, Change%
- **Color Coding**: Green for profit, Red for loss
- **Total P/L Box**: Prominent display of total P/L
- **Summary Bar**: Positions count, quantity, realized/unrealized P/L
- **Exit Modal**: Market/Limit exit with quantity selection
- **Add Modal**: Buy/Sell more at limit price
- **Exit All**: One-click exit all positions with confirmation
- **Empty State**: Link to Option Chain when no positions

## User Flow

1. View open F&O positions
2. Toggle between Day and Net positions
3. Monitor live P/L changes
4. Click Exit to close a position (select Market/Limit)
5. Click Add to increase position size
6. Use Exit All for emergency close (with confirmation)

## Technical Implementation

### Backend

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/positions/` | Get all positions with live P/L |
| POST | `/api/positions/exit` | Exit a position |
| POST | `/api/positions/add` | Add to existing position |
| POST | `/api/positions/exit-all` | Exit all open positions |
| GET | `/api/positions/grouped` | Positions grouped by underlying |

**Query Parameters for GET:**
- `type` - `day` or `net` (default: day)

**Exit Request Body:**
```json
{
  "tradingsymbol": "NIFTY24DEC24500CE",
  "exchange": "NFO",
  "quantity": 75,
  "order_type": "MARKET",
  "price": null
}
```

### Frontend

**Components:**
- `PositionsView.vue` - Main view with table and modals

**Store:**
- `stores/positions.js` - Positions state, modal state, auto-refresh

**data-testid attributes:**
- `positions-page`
- `positions-day-button`
- `positions-net-button`
- `positions-pnl-box`
- `positions-table`
- `positions-exit-modal`
- `positions-empty-state`

## Testing

```bash
npm run test:specs:positions
```

## Related

- [Strategy Builder](./strategy-builder.md) - Create strategies
- [Option Chain](./option-chain.md) - View option chain
- [API Reference](../api/README.md) - Endpoint details
