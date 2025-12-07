# Option Chain

## Overview

Displays real-time option chain data for NIFTY, BANKNIFTY, and FINNIFTY with OI, IV, Greeks, and click-to-add functionality.

## Screenshots

![Option Chain](../assets/screenshots/optionchain-nifty.png)

## Features

- **Underlying Selection**: NIFTY, BANKNIFTY, FINNIFTY tabs
- **Expiry Dropdown**: All available expiry dates
- **Live Spot Price**: Real-time underlying price with DTE
- **Strike Data**: OI, OI Change, Volume, IV, LTP, Change%
- **Greeks**: Delta (toggleable)
- **Visual OI Bars**: Red for CE, Green for PE
- **ATM Highlighting**: Yellow row for ATM strike
- **ITM/OTM Colors**: Color-coded backgrounds
- **Summary Bar**: PCR, Max Pain, Total CE/PE OI
- **Add to Strategy**: Click + button to select strikes
- **Strike Range Filter**: Show strikes around ATM

## User Flow

1. Select underlying (NIFTY/BANKNIFTY/FINNIFTY)
2. Select expiry date from dropdown
3. View option chain with live data
4. Click + to select strikes for strategy
5. Click "Add to Strategy Builder" to transfer selected legs

## Technical Implementation

### Backend

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/optionchain/chain` | Full option chain with OI, IV, Greeks |
| GET | `/api/optionchain/oi-analysis` | OI data for charts |

**Query Parameters:**
- `underlying` - NIFTY, BANKNIFTY, or FINNIFTY
- `expiry` - Expiry date (YYYY-MM-DD)

**Calculations:**
- IV: Newton-Raphson method
- Greeks: Black-Scholes model (Delta, Gamma, Theta, Vega)
- Max Pain: Calculated from cumulative OI data
- PCR: Put OI / Call OI

### Frontend

**Components:**
- `OptionChainView.vue` - Main view with table and controls

**Store:**
- `stores/optionchain.js` - Manages underlying, expiry, chain data

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Strike Range | ±10 | Number of strikes shown around ATM |
| Auto Refresh | On | Refresh data automatically |

## Testing

```bash
npm run test:optionchain
```

## Related

- [Strategy Builder](./strategy-builder.md) - Build strategies from selected strikes
- [WebSocket Architecture](../architecture/websocket.md) - Live price streaming
