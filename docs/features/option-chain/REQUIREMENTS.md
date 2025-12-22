# Option Chain Requirements

## Core Requirements
- [x] Display full option chain for NIFTY, BANKNIFTY, FINNIFTY, SENSEX
- [x] Select underlying via tabs
- [x] Select expiry from dropdown
- [x] Show all strikes for selected expiry
- [x] Display CE (Call) and PE (Put) data side-by-side

## Data Display Requirements
- [x] Open Interest (OI)
- [x] OI Change
- [x] Volume
- [x] Implied Volatility (IV)
- [x] Last Traded Price (LTP)
- [x] Change percentage
- [x] Greeks (Delta - toggleable)
- [x] Bid/Ask prices
- [x] Bid/Ask quantities

## Visual Features
- [x] OI visualization bars (red for CE, green for PE)
- [x] ATM strike highlighting (yellow background)
- [x] ITM strikes color coding (green for CE ITM, red for PE ITM)
- [x] OTM strikes regular display
- [x] Strike price column in center

## Summary Metrics
- [x] PCR (Put-Call Ratio) calculation
- [x] Max Pain calculation
- [x] Total CE OI
- [x] Total PE OI
- [x] Live spot price with DTE (Days to Expiry)

## Strike Selection
- [x] Click + button to select strike
- [x] Multi-strike selection
- [x] Selected strikes badge count
- [x] "Add to Strategy Builder" button
- [x] Transfer selected legs to Strategy Builder

## Strike Finder (Advanced)
- [x] ATM-based selection
- [x] Delta-based selection
- [x] Find strikes by target delta value
- [x] Quick add to Strategy Builder

## Greeks Calculations
- [x] Calculate Delta using Black-Scholes
- [x] Calculate Gamma using Black-Scholes
- [x] Calculate Theta using Black-Scholes
- [x] Calculate Vega using Black-Scholes
- [x] Toggle Greeks display on/off

## API Requirements
- [x] GET /api/optionchain/chain - Full option chain
- [x] GET /api/optionchain/oi-analysis - OI data for charts
- [x] GET /api/options/expiries - Available expiries
- [x] GET /api/options/strikes - Strike prices for expiry
- [x] GET /api/options/instrument - Get instrument by params

## UI Requirements
- [x] Underlying tabs (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)
- [x] Expiry dropdown
- [x] Greeks toggle button
- [x] Strike range filter (±10 strikes around ATM)
- [x] Responsive table design
- [x] Sticky header for scrolling

## Performance Requirements
- [x] Load option chain within 1 second
- [x] Calculate Greeks within 500ms
- [x] Real-time price updates via WebSocket
- [x] Handle 50+ strikes efficiently

## Integration Requirements
- [x] Live prices via WebSocket
- [x] Integration with Strategy Builder
- [x] Kite API for instrument data

---
Last updated: 2025-12-22
