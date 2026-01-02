# Orders Requirements

## Core Requirements
- [x] Place basket orders (multi-leg)
- [x] Get positions from broker
- [x] Import positions as strategy
- [x] Get LTP for instruments
- [x] Support Market and Limit orders
- [x] Support Buy and Sell transactions

## Basket Order
- [x] Accept multiple legs in single request
- [x] Execute all legs sequentially or simultaneously
- [x] Return order IDs for all legs
- [x] Handle partial fills
- [x] Error handling for failed legs

## Position Import
- [x] Fetch current positions from Kite
- [x] Filter F&O positions
- [x] Create strategy from positions
- [x] Set entry prices from average price
- [x] Calculate current P&L

## LTP Fetching
- [x] Get LTP for single instrument
- [x] Get LTP for multiple instruments
- [x] Fallback when WebSocket unavailable
- [x] Return LTP with timestamp

## OHLC & Quote Fetching
- [x] Get OHLC (Open/High/Low/Close) for instruments
- [x] Get full quote with OHLC and bid/ask spread
- [x] Frontend fallback to OHLC when quote fails (market closed)
- [x] Return last_price with OHLC data

## API Requirements
- [x] POST /api/orders/basket - Place basket order
- [x] GET /api/orders/positions - Get broker positions
- [x] POST /api/orders/import-positions - Import as strategy
- [x] GET /api/orders/ltp - Get LTP for instruments
- [x] GET /api/orders/ohlc - Get OHLC data for instruments (market-closed fallback)
- [x] GET /api/orders/quote - Get full quote with OHLC and bid/ask

## Order Request Schema
- [x] tradingsymbol (e.g., "NIFTY24DEC24500CE")
- [x] exchange (NFO, NSE, BSE, CDS, BCD)
- [x] transaction_type (BUY, SELL)
- [x] quantity (in lots)
- [x] order_type (MARKET, LIMIT)
- [x] price (for LIMIT orders)
- [x] product (MIS, NRML, CNC)

## Integration Requirements
- [x] Kite Connect order placement API
- [x] Kite Connect positions API
- [x] Kite Connect LTP API
- [x] Kite Connect OHLC API
- [x] Kite Connect Quote API
- [x] Used by Strategy Builder
- [x] Used by Positions feature
- [x] Used by AutoPilot
- [x] Used by P/L Grid (index prices fallback)

## Error Handling
- [x] Insufficient margin errors
- [x] Invalid instrument errors
- [x] Market closed errors
- [x] Order rejection errors
- [x] Network errors

## Response Format
- [x] Order IDs for successful orders
- [x] Error messages for failures
- [x] Partial success indicators
- [x] Order status tracking

---
Last updated: 2026-01-02
