# Watchlist Changelog

All notable changes to the Watchlist feature will be documented in this file.

## [Unreleased]

## [1.0.0] - 2024-12-04

### Added
- Watchlist feature with real-time prices (file: frontend/src/views/WatchlistView.vue)
- WebSocket integration for live tick data (file: backend/app/api/routes/websocket.py)
- Kite Ticker Service for WebSocket management (file: backend/app/services/kite_ticker.py)
- Instrument search functionality (file: backend/app/api/routes/instruments.py)
- Multiple watchlist support (file: backend/app/api/routes/watchlist.py)
- Index headers for NIFTY 50, NIFTY BANK, FINNIFTY (file: frontend/src/components/watchlist/IndexHeader.vue)
- Instrument row component with expandable actions (file: frontend/src/components/watchlist/InstrumentRow.vue)
- Instrument search modal with debounced search (file: frontend/src/components/watchlist/InstrumentSearch.vue)
- Watchlist and Instruments database models (files: backend/app/models/watchlists.py, instruments.py)
- Instrument master download service (file: backend/app/services/instruments.py)
- Watchlist store for state management (file: frontend/src/stores/watchlist.js)
