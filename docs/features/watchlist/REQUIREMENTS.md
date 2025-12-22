# Watchlist Requirements

## Core Requirements
- [x] Create up to 5 watchlists per user
- [x] Add up to 100 instruments per watchlist
- [x] Remove instruments from watchlist
- [x] Rename watchlist
- [x] Delete watchlist
- [x] Search instruments by name/symbol
- [x] Filter instruments by Cash/F&O

## Live Data Requirements
- [x] WebSocket connection for real-time prices
- [x] Display LTP (Last Traded Price)
- [x] Show change amount and change percentage
- [x] Color coding (green for positive, red for negative)
- [x] Connection status indicator
- [x] Auto-reconnect on disconnect

## Index Headers
- [x] Display NIFTY 50 live price
- [x] Display NIFTY BANK live price
- [x] Show change for indices
- [x] Update indices in real-time

## Instrument Row Features
- [x] Expandable row for actions
- [x] Buy button (placeholder)
- [x] Sell button (placeholder)
- [x] Chart button (placeholder)
- [x] Option Chain navigation
- [x] Delete instrument action

## API Requirements
- [x] GET /api/watchlists - Get all user watchlists
- [x] POST /api/watchlists - Create new watchlist
- [x] PUT /api/watchlists/{id} - Update watchlist
- [x] DELETE /api/watchlists/{id} - Delete watchlist
- [x] POST /api/watchlists/{id}/instruments - Add instrument
- [x] DELETE /api/watchlists/{id}/instruments/{token} - Remove instrument
- [x] GET /api/instruments/search - Search instruments
- [x] GET /api/instruments/indices - Get index tokens
- [x] POST /api/instruments/refresh - Refresh instrument master

## UI Requirements
- [x] Tabbed interface for multiple watchlists
- [x] "+ Add Watchlist" button
- [x] "+ Add Instrument" button with search modal
- [x] Empty state with CTA
- [x] Debounced search (300ms)
- [x] "Already Added" badge in search results

## Data Requirements
- [x] `watchlists` table with JSONB instruments array
- [x] `instruments` table with Kite master data
- [x] Index on instrument_token
- [x] Index on tradingsymbol and exchange

## Integration Requirements
- [x] WebSocket at ws://localhost:8000/ws/ticks
- [x] JWT authentication for WebSocket
- [x] Kite WebSocket integration
- [x] Instrument master download from Kite API
- [x] Redis caching for instrument data

## Performance Requirements
- [x] Handle up to 100 instruments per watchlist
- [x] Real-time updates within 500ms
- [x] Search results within 200ms
- [x] Support ~200,000 instruments in database

---
Last updated: 2025-12-22
