# WebSocket Requirements

## Core Requirements
- [x] Real-time price streaming via WebSocket
- [x] Kite Connect WebSocket integration
- [x] Per-user subscription management
- [x] Multi-client support
- [x] JWT authentication for connections

## Connection Management
- [x] WebSocket endpoint at ws://localhost:8000/ws/ticks
- [x] JWT authentication on connect
- [x] Per-user connection tracking
- [x] Graceful disconnect handling
- [x] Connection status messages

## Subscription Management
- [x] Subscribe to instrument tokens
- [x] Unsubscribe from tokens
- [x] Subscribe to multiple tokens simultaneously
- [x] Per-user subscription isolation
- [x] Subscription confirmation messages

## Tick Broadcasting
- [x] Receive ticks from Kite WebSocket
- [x] Broadcast to subscribed users only
- [x] Filter ticks by user subscriptions
- [x] Thread-safe async broadcasting
- [x] Tick caching for instant delivery

## Message Types
- [x] `connected` - Connection established
- [x] `subscribe` - Subscribe to tokens
- [x] `subscribed` - Subscription confirmed
- [x] `unsubscribe` - Unsubscribe from tokens
- [x] `ticks` - Live price data
- [x] `ping` - Client keepalive
- [x] `pong` - Server keepalive response
- [x] `error` - Error messages

## Kite Ticker Service
- [x] Singleton service instance
- [x] Connect to Kite WebSocket
- [x] Handle Kite connection lifecycle
- [x] Auto-reconnect on disconnect
- [x] Manage global subscriptions
- [x] Broadcast to all platform connections

## Tick Data Format
- [x] Instrument token
- [x] Last Traded Price (LTP)
- [x] Change amount
- [x] Change percentage
- [x] Volume
- [x] Open Interest (for options/futures)
- [x] Bid/Ask prices
- [x] Timestamp

## Subscription Modes
- [x] `ltp` - LTP only
- [x] `quote` - LTP + Volume + OI + Change
- [x] `full` - Complete market depth

## Performance Requirements
- [x] Handle 100+ concurrent connections
- [x] Support 3000 token subscriptions (Kite limit)
- [x] Deliver ticks within 500ms
- [x] Efficient memory usage for tick caching

## Error Handling
- [x] Invalid JWT handling
- [x] Connection timeout handling
- [x] Kite WebSocket errors
- [x] Graceful degradation on Kite disconnect
- [x] Error messages to clients

## Integration Requirements
- [x] Used by Watchlist feature
- [x] Used by Positions feature
- [x] Used by Option Chain feature
- [x] Used by Strategy Builder feature
- [x] Used by AutoPilot feature

## Index Token Support
- [x] NIFTY 50 (256265)
- [x] NIFTY BANK (260105)
- [x] FINNIFTY (257801)
- [x] SENSEX (265)

---
Last updated: 2025-12-22
