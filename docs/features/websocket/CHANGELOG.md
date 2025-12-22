# WebSocket Changelog

All notable changes to the WebSocket feature will be documented in this file.

## [Unreleased]

## [1.0.0] - 2024-12-04

### Added
- WebSocket endpoint for real-time tick streaming (file: backend/app/api/routes/websocket.py)
- Kite Ticker Service singleton for WebSocket management (file: backend/app/services/kite_ticker.py)
- JWT authentication for WebSocket connections (file: backend/app/api/routes/websocket.py)
- Per-user subscription management (file: backend/app/services/kite_ticker.py)
- Thread-safe async tick broadcasting (file: backend/app/services/kite_ticker.py)
- Tick caching for instant delivery on subscribe (file: backend/app/services/kite_ticker.py)
- Auto-reconnect on disconnect (file: backend/app/services/kite_ticker.py)
- Message types: connected, subscribe, subscribed, ticks, ping, pong, error (file: backend/app/api/routes/websocket.py)
- Support for ltp, quote, and full subscription modes (file: backend/app/services/kite_ticker.py)
- Index token support (NIFTY 50, NIFTY BANK, FINNIFTY, SENSEX) (file: backend/app/constants/trading.py)
