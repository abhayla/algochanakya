# Orders Changelog

All notable changes to the Orders feature will be documented in this file.

## [Unreleased]

### Added
- OHLC endpoint for market-closed price fallback (file: backend/app/api/routes/orders.py)
- Quote endpoint for full market data including OHLC and bid/ask (file: backend/app/api/routes/orders.py)
- get_ohlc() method in KiteOrderService (file: backend/app/services/kite_orders.py)
- get_quote() method in KiteOrderService (file: backend/app/services/kite_orders.py)
- Frontend OHLC fallback when quote API fails outside market hours (file: frontend/src/composables/usePriceFallback.js)

## [1.0.0] - 2024-12-05

### Added
- Basket order execution API (file: backend/app/api/routes/orders.py)
- Position import from broker (file: backend/app/api/routes/orders.py)
- LTP fetching endpoint (file: backend/app/api/routes/orders.py)
- Support for Market and Limit orders (file: backend/app/api/routes/orders.py)
- Support for Buy and Sell transactions (file: backend/app/api/routes/orders.py)
- Multi-leg order execution (file: backend/app/api/routes/orders.py)
- Kite Connect integration for order placement (file: backend/app/api/routes/orders.py)
- Error handling for order failures (file: backend/app/api/routes/orders.py)
