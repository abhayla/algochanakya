# Fyers GTT Orders Reference

> Source: Fyers API v3 Docs (https://myapi.fyers.in/docs/) | Last verified: 2026-02-25
> Warning: GTT WebSocket events are reportedly broken per community reports (Feb 2026).

## Overview

Fyers provides GTT (Good Till Triggered) order functionality through the Fyers app/web interface. The API documentation for GTT is incomplete and community reports indicate WebSocket GTT events may not work correctly.

## Available GTT Functionality

### Via App/Web Interface (Stable)
- Create GTT orders
- View/modify/cancel GTT orders
- Single trigger and OCO (target + stop-loss)

### Via API (Status Unclear)
The Fyers v3 API may support GTT endpoints, but:
- Documentation is incomplete
- Community reports of WebSocket GTT events being broken (Feb 2026)
- Reliability is uncertain

## Potential Endpoints (Community Research)

Based on community research, Fyers may support:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v3/gtt/orders` | Create GTT |
| GET | `/api/v3/gtt/orders` | List GTT |
| PUT | `/api/v3/gtt/orders/{id}` | Modify GTT |
| DELETE | `/api/v3/gtt/orders/{id}` | Cancel GTT |

Caution: These endpoints are not fully documented. Test in sandbox before production use.

## Community-Reported Issues (Feb 2026)

1. **WebSocket GTT events broken**: FyersOrderSocket may not send GTT trigger notifications correctly
2. **Documentation gaps**: GTT API not fully documented in official v3 docs
3. **Use App Instead**: For reliable GTT, use the Fyers mobile app directly

## Alternative: Fyers App GTT

For reliable GTT placement:
1. Use Fyers mobile app or web platform
2. Set GTT via "GTT Alerts" feature
3. Orders execute automatically regardless of app state

## AlgoChanakya Integration

- GTT is **NOT implemented** in AlgoChanakya's Fyers adapter
- Fyers adapter supports standard orders only
- Given community issues with GTT API, recommend testing thoroughly before implementing
- File: `backend/app/services/brokers/fyers_order_adapter.py`
