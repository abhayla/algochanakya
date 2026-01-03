# SmartAPI Integration - Continuation Prompt

Use this prompt to continue the AngelOne SmartAPI integration in a new Claude Code session.

---

## Prompt for New Session

```
I want to continue implementing AngelOne SmartAPI integration for AlgoChanakya.

## Context
The plan has been created and approved. Read the full plan at:
- `docs/plans/smartapi-integration-plan.md`

## Summary of What We're Doing
Replace Kite API with AngelOne SmartAPI as the DEFAULT market data source for:
1. **Live prices** - via WebSocket V2 (real-time streaming)
2. **Historical OHLC** - via Historical Data API (getCandleData)
3. **On-demand quotes** - via Market Data API (after-market prices)

Orders/positions will REMAIN with Zerodha Kite - only market data is switching.

## Key Decisions Made
- SmartAPI scope: Market data only (not orders)
- Default source: SmartAPI (user can switch to Kite in Settings)
- Token mapping: Auto-lookup via tradingsymbol (no pre-built mapping)
- UI location: Settings page toggle
- Auth method: Stored credentials with auto-TOTP (pyotp)
- Switch behavior: Seamless if Kite token valid

## AngelOne SmartAPI - 3 APIs to Implement
1. **WebSocket V2** - `wss://smartapisocket.angelone.in/smart-stream` (live streaming)
2. **Market Data API** - `POST /rest/secure/angelbroking/market/v1/quote/` (on-demand)
3. **Historical Data API** - `POST /rest/secure/angelbroking/historical/v1/getCandleData`

## Files to Create (Priority Order)
1. `backend/app/models/smartapi_credentials.py` - Encrypted credentials storage
2. `backend/app/utils/encryption.py` - Fernet encryption for credentials
3. `backend/app/services/smartapi_auth.py` - Auth with auto-TOTP
4. `backend/app/services/smartapi_instruments.py` - Token lookup from instrument master
5. `backend/app/services/smartapi_ticker.py` - WebSocket V2 (mirrors KiteTickerService)
6. `backend/app/services/smartapi_market_data.py` - REST quotes
7. `backend/app/services/smartapi_historical.py` - Historical candles
8. `backend/app/api/routes/smartapi.py` - Credential management endpoints
9. `backend/alembic/versions/XXX_add_smartapi_support.py` - Migration

## Files to Modify
- `backend/app/models/user_preferences.py` - Add `market_data_source` field
- `backend/app/api/routes/websocket.py` - Route to SmartAPI or Kite
- `backend/app/api/routes/orders.py` - Route `/ltp`, `/quote`, `/ohlc`
- `backend/app/services/brokers/factory.py` - Register SmartAPIAdapter
- `backend/app/main.py` - Include smartapi router
- `backend/requirements.txt` - Add `smartapi-python`, `pyotp`

## Frontend Files
- `frontend/src/components/settings/SmartAPISettings.vue` - NEW
- `frontend/src/components/settings/MarketDataSourceToggle.vue` - NEW
- `frontend/src/stores/userPreferences.js` - Add marketDataSource
- `frontend/src/views/SettingsView.vue` - Add settings section

## Key Reference Files (Existing Patterns)
- `backend/app/services/kite_ticker.py` - Pattern to follow for SmartAPI ticker
- `backend/app/services/brokers/base.py` - BrokerAdapter interface
- `backend/app/services/brokers/kite_adapter.py` - Reference implementation

## Important Notes
- Prices from SmartAPI are in PAISE (divide by 100 for rupees)
- SmartAPI uses different instrument tokens than Kite
- Instrument master URL: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
- Max 1000 tokens per WebSocket session, 3 connections max

## Prerequisites (User Action)
I need to create an AngelOne SmartAPI account first:
1. https://smartapi.angelbroking.com/
2. Generate API Key
3. Enable TOTP

Please start implementing from the first file in the priority order. Use the plan document for detailed implementation specs.
```

---

## Quick Reference

### SmartAPI Python SDK
```bash
pip install smartapi-python pyotp
```

### Authentication Example
```python
from SmartApi import SmartConnect
import pyotp

api = SmartConnect(api_key="YOUR_API_KEY")
totp = pyotp.TOTP("YOUR_TOTP_SECRET").now()
data = api.generateSession("CLIENT_ID", "PIN", totp)
jwt_token = data['data']['jwtToken']
feed_token = api.getfeedToken()
```

### WebSocket V2 Example
```python
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

sws = SmartWebSocketV2(jwt_token, api_key, client_id, feed_token)
token_list = [{"exchangeType": 2, "tokens": ["57920"]}]  # NFO
sws.subscribe("correlation_id", mode=2, token_list=token_list)
# Prices in paise - divide by 100
```

### Historical Data Example
```python
params = {
    "exchange": "NFO",
    "symboltoken": "57920",
    "interval": "ONE_DAY",
    "fromdate": "2024-01-01 09:15",
    "todate": "2024-01-31 15:30"
}
data = api.getCandleData(params)
```

---

## Sources
- [SmartAPI Docs](https://smartapi.angelbroking.com/docs)
- [SmartAPI Python GitHub](https://github.com/angel-one/smartapi-python)
- [Market Data API Forum](https://smartapi.angelone.in/smartapi/forum/topic/3661)
