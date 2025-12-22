# Strategy Builder Requirements

## Core Requirements
- [x] Create multi-leg option strategies
- [x] Add unlimited legs
- [x] Edit leg parameters (strike, expiry, type, quantity, prices)
- [x] Delete legs
- [x] Save strategies to database
- [x] Load saved strategies
- [x] Share strategies via public links

## Leg Configuration
- [x] Select underlying (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)
- [x] Select expiry date
- [x] Select strike price
- [x] Select option type (CE/PE)
- [x] Select position (BUY/SELL)
- [x] Enter number of lots
- [x] Enter entry price
- [x] Use Current Market Price (CMP)

## P/L Calculation
- [x] Calculate P/L at expiry (intrinsic value)
- [x] Calculate current P/L (Black-Scholes pricing)
- [x] Toggle between "At Expiry" and "Current" modes
- [x] Generate P/L grid across spot prices
- [x] Include ATM column in grid
- [x] Include breakeven columns in grid
- [x] Include strike price columns in grid
- [x] Linear interpolation for breakeven/strike P&L values
- [x] Color gradient (green for profit zones, red for loss zones)

## Summary Metrics
- [x] Max Profit calculation
- [x] Max Loss calculation
- [x] Breakeven points
- [x] Risk/Reward ratio
- [x] Net premium (debit/credit)
- [x] Total margin requirement

## Live Data Features
- [x] Current Market Price (CMP) via WebSocket
- [x] Exit P/L calculation per leg
- [x] Manual override for Exit P/L
- [x] Real-time updates when market moves

## Payoff Chart
- [x] Visual payoff diagram
- [x] X-axis: Spot prices
- [x] Y-axis: Profit/Loss
- [x] Breakeven markers
- [x] Max profit/loss annotations
- [x] Current spot indicator

## Strategy Templates
- [x] Iron Condor template
- [x] Straddle template
- [x] Strangle template
- [x] Bull Call Spread
- [x] Bear Put Spread
- [x] Quick load template with one click

## Order Execution
- [x] Place basket order via Kite
- [x] Review order before execution
- [x] Order confirmation modal
- [x] Success/failure messaging

## Import/Export
- [x] Import existing positions from broker
- [x] Convert positions to strategy
- [x] Export strategy as JSON
- [x] Share strategy with public link

## API Requirements
- [x] GET /api/strategies - List saved strategies
- [x] GET /api/strategies/{id} - Get strategy details
- [x] POST /api/strategies - Save new strategy
- [x] PUT /api/strategies/{id} - Update strategy
- [x] DELETE /api/strategies/{id} - Delete strategy
- [x] POST /api/strategies/calculate - Calculate P/L grid
- [x] POST /api/strategies/{id}/share - Generate share code
- [x] GET /api/strategies/shared/{code} - Get shared strategy (public)
- [x] POST /api/orders/basket - Place basket order
- [x] POST /api/orders/import-positions - Import positions
- [x] GET /api/orders/ltp - Get LTP fallback

## UI Requirements
- [x] Full-width layout
- [x] Underlying selector dropdown
- [x] P/L mode toggle (At Expiry / Current)
- [x] "+ Add Row" button
- [x] Legs table with inline editing
- [x] "ReCalculate" button
- [x] P/L grid with dynamic columns
- [x] Payoff chart visualization
- [x] Summary cards row
- [x] Action buttons (Save, Share, Buy)
- [x] Modals (Save, Share, Basket Order)

## Data Requirements
- [x] `strategies` table - Strategy metadata
- [x] `strategy_legs` table - Individual legs
- [x] Store share_code for public access
- [x] Track created_at, updated_at timestamps

## Performance Requirements
- [x] P/L calculation within 1 second
- [x] Handle up to 10 legs efficiently
- [x] Real-time CMP updates within 500ms
- [x] Smooth chart rendering

## Integration Requirements
- [x] Option Chain integration for adding legs
- [x] WebSocket for live CMP
- [x] Kite API for order placement
- [x] Trading constants for lot sizes

---
Last updated: 2025-12-22
