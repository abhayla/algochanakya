# Positions Requirements

## Core Requirements
- [x] Display all F&O positions from broker
- [x] Toggle between Day and Net positions
- [x] Show live P&L calculations
- [x] Exit individual positions
- [x] Add to existing positions
- [x] Exit all positions at once

## Position Data Display
- [x] Instrument tradingsymbol
- [x] Quantity (with color: blue for buy, red for sell)
- [x] Average price
- [x] Last Traded Price (LTP)
- [x] Day change percentage
- [x] Profit/Loss per position
- [x] Color coding (green profit, red loss)

## Summary Features
- [x] Total P/L box with prominent display
- [x] Positions count
- [x] Total quantity
- [x] Realized P&L
- [x] Unrealized P&L
- [x] Margin used (if available)

## Exit Modal
- [x] Select quantity to exit
- [x] Market order type
- [x] Limit order type with price input
- [x] Confirmation before exit
- [x] Success/error messaging

## Add Modal
- [x] Select Buy or Sell
- [x] Enter quantity
- [x] Limit price input
- [x] Confirmation before add
- [x] Success/error messaging

## Exit All Feature
- [x] Exit all button
- [x] Confirmation dialog
- [x] Execute all exits at market price
- [x] Show success count

## Auto Refresh
- [x] Toggle auto-refresh on/off
- [x] 5-second refresh interval
- [x] Manual refresh button
- [x] Loading indicators during refresh

## API Requirements
- [x] GET /api/positions/ - Get positions with P/L
- [x] POST /api/positions/exit - Exit position
- [x] POST /api/positions/add - Add to position
- [x] POST /api/positions/exit-all - Exit all positions
- [x] GET /api/positions/grouped - Grouped positions

## UI Requirements
- [x] Day/Net toggle buttons
- [x] Auto-refresh toggle
- [x] Positions table
- [x] Exit modal dialog
- [x] Add modal dialog
- [x] Empty state with link to Option Chain
- [x] Responsive design for mobile/desktop

## Data Requirements
- [x] Fetch positions from Kite API
- [x] Calculate day P&L
- [x] Calculate net P&L
- [x] Handle futures and options positions
- [x] Support multiple exchanges (NFO, CDS, BCD)

## Integration Requirements
- [x] Kite Connect positions API
- [x] Live price updates via WebSocket
- [x] Order placement via Kite

---
Last updated: 2025-12-22
