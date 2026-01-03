# AngelOne SmartAPI Integration Plan

## Summary

Replace Kite API with AngelOne SmartAPI as the **default market data source** for live prices and historical OHLC. Orders/positions remain with Zerodha Kite.

## User Requirements (Confirmed)

| Requirement | Decision |
|-------------|----------|
| SmartAPI scope | Market data only (live + historical) |
| Default source | SmartAPI (user can switch to Kite in Settings) |
| Token mapping | Auto-lookup via tradingsymbol |
| UI location | Settings page toggle |
| Auth method | Stored credentials with auto-TOTP |
| Switch behavior | Seamless if Kite token valid |
| Historical data | AngelOne getCandleData API |

---

## AngelOne SmartAPI - 3 APIs Overview

AngelOne provides **3 distinct APIs** for market data:

### 1. WebSocket V2 (Real-Time Streaming)

**Purpose:** Tick-by-tick live price streaming

| Property | Value |
|----------|-------|
| **Endpoint** | `wss://smartapisocket.angelone.in/smart-stream` |
| **Max Connections** | 3 per client ID |
| **Token Limit** | 1000 per session |
| **Modes** | LTP(1), Quote(2), SnapQuote(3), Depth(4) |
| **Market Depth** | Best 20 Buy/Sell (Depth mode) |
| **Use Case** | Real-time price updates, Option Chain, Strategy P/L |

**Subscription Format:**
```python
token_list = [{"exchangeType": 2, "tokens": ["57920"]}]  # exchangeType: 1=NSE, 2=NFO
sws.subscribe(correlation_id, mode=2, token_list=token_list)
```

**Tick Data (Quote Mode):**
```python
{
    'token': '57920',
    'last_traded_price': 2350000,  # In paise, divide by 100
    'open_price_of_the_day': 2340000,
    'high_price_of_the_day': 2360000,
    'low_price_of_the_day': 2335000,
    'closed_price': 2345000,  # Previous close
    'exchange_timestamp': 1704067200000  # Unix ms
}
```

### 2. Market Data API (REST - On-Demand Quotes)

**Purpose:** Fetch current prices on demand (not streaming)

| Property | Value |
|----------|-------|
| **Endpoint** | `POST /rest/secure/angelbroking/market/v1/quote/` |
| **Modes** | LTP, OHLC, Full |
| **Market Depth** | Best 5 Buy/Sell (Full mode) |
| **Limit** | Single token per exchange per request |
| **Use Case** | One-time price checks, after-market snapshots |

**Request Format:**
```json
{
    "mode": "FULL",
    "exchangeTokens": {
        "NSE": ["3045"],
        "NFO": ["57920"]
    }
}
```

**Response (Full Mode):**
```json
{
    "ltp": 23500.50,
    "open": 23400.00,
    "high": 23600.00,
    "low": 23350.00,
    "close": 23450.00,
    "volume": 1500000,
    "oi": 2500000,
    "totBuyQuan": 50000,
    "totSellQuan": 45000,
    "52WeekHigh": 25000.00,
    "52WeekLow": 18000.00,
    "depth": { "buy": [...], "sell": [...] }
}
```

### 3. Historical Data API (REST - Candle Data)

**Purpose:** Fetch historical OHLCV candles

| Property | Value |
|----------|-------|
| **Endpoint** | `POST /rest/secure/angelbroking/historical/v1/getCandleData` |
| **Intervals** | ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY |
| **Max Candles** | 8000 per request |
| **1-Min Limit** | 30 days |
| **5-Min Limit** | 100 days |
| **Cost** | FREE |
| **Use Case** | Charts, backtesting, after-market OHLC |

**Request Format:**
```python
{
    "exchange": "NFO",
    "symboltoken": "57920",
    "interval": "ONE_DAY",
    "fromdate": "2024-01-01 09:15",
    "todate": "2024-01-31 15:30"
}
```

**Response:**
```python
# Returns: [[timestamp, open, high, low, close, volume], ...]
[
    ["2024-01-02T09:15:00+05:30", 23400.0, 23600.0, 23350.0, 23500.0, 1500000],
    ["2024-01-03T09:15:00+05:30", 23500.0, 23700.0, 23450.0, 23650.0, 1600000]
]
```

### API Selection Strategy

| Use Case | API to Use |
|----------|------------|
| Live price streaming (Watchlist, Positions, OptionChain) | **WebSocket V2** |
| Strategy P/L calculation (real-time) | **WebSocket V2** |
| After-market price check | **Market Data API** (quote) |
| Historical charts / backtesting | **Historical Data API** |
| OHLC fallback when WebSocket unavailable | **Historical Data API** |

### Kite API vs SmartAPI Comparison

| Feature | Kite API | SmartAPI |
|---------|----------|----------|
| **WebSocket Connections** | 1 | 3 |
| **Token Limit** | Unlimited (practical) | 1000 per session |
| **Price Format** | Rupees | Paise (÷100) |
| **Instrument Tokens** | Kite format | SmartAPI format |
| **Auth Method** | OAuth (request_token) | Client ID + PIN + TOTP |
| **Historical Data** | Paid add-on | FREE |
| **Market Depth** | 5 levels | 20 levels (Depth mode) |

### Exchange Type Mapping

| Exchange | Kite | SmartAPI exchangeType |
|----------|------|----------------------|
| NSE Cash | NSE | 1 (NSE_CM) |
| NSE F&O | NFO | 2 (NSE_FO) |
| BSE Cash | BSE | 3 (BSE_CM) |
| BSE F&O | BFO | 4 (BSE_FO) |
| MCX | MCX | 5 (MCX_FO) |

---

## Architecture

```
Frontend → /ws/ticks → MarketDataRouter → SmartAPI Ticker (default)
                                       → Kite Ticker (fallback)

Frontend → /api/orders/quote → MarketDataRouter → SmartAPI REST
                                                → Kite REST

Orders/Positions → /api/orders/basket → KiteOrderService (unchanged)
```

---

## Phase 1: Backend - Core Services

### New Files

| File | Purpose | API Used |
|------|---------|----------|
| `backend/app/models/smartapi_credentials.py` | Encrypted credentials storage (client_id, pin, totp_secret) | Auth |
| `backend/app/services/smartapi_auth.py` | Authentication with auto-TOTP generation | generateSession |
| `backend/app/services/smartapi_ticker.py` | **WebSocket V2** for live prices (mirrors KiteTickerService) | WebSocket V2 |
| `backend/app/services/smartapi_market_data.py` | **Market Data API** for on-demand quotes (LTP/OHLC/Full) | Market Data API |
| `backend/app/services/smartapi_historical.py` | **Historical Data API** for candle data (getCandleData) | Historical API |
| `backend/app/services/smartapi_instruments.py` | Instrument master download and token lookup | Instrument Master |
| `backend/app/services/brokers/smartapi_adapter.py` | BrokerAdapter wrapping all 3 APIs | All |
| `backend/app/api/routes/smartapi.py` | Credential management endpoints | - |
| `backend/app/utils/encryption.py` | Fernet encryption for stored credentials | - |

### Service Architecture (3 APIs)

```
SmartAPIAdapter (broker adapter interface)
    │
    ├── SmartAPIAuth (authentication)
    │   └── generateSession() → jwt_token + feed_token
    │
    ├── SmartAPITicker (WebSocket V2)
    │   └── Real-time streaming (Watchlist, Positions, OptionChain)
    │
    ├── SmartAPIMarketData (Market Data API)
    │   └── On-demand quotes (after-market prices)
    │
    └── SmartAPIHistorical (Historical Data API)
        └── Candle data (OHLC fallback, charts)
```

### Modify Files

| File | Changes |
|------|---------|
| `backend/app/models/user_preferences.py` | Add `market_data_source` field (default: "smartapi") |
| `backend/app/api/routes/websocket.py` | Route to SmartAPI or Kite based on user preference |
| `backend/app/api/routes/orders.py` | Route `/ltp`, `/quote`, `/ohlc` based on preference |
| `backend/app/services/brokers/factory.py` | Register SmartAPIAdapter |
| `backend/app/main.py` | Include smartapi router |
| `backend/requirements.txt` | Add `smartapi-python`, `pyotp` |

---

## Phase 2: Database Migration

**File:** `backend/alembic/versions/XXX_add_smartapi_support.py`

```sql
-- 1. Add to user_preferences
ALTER TABLE user_preferences
ADD COLUMN market_data_source VARCHAR(20) NOT NULL DEFAULT 'smartapi';

-- 2. Create smartapi_credentials table
CREATE TABLE smartapi_credentials (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    client_id VARCHAR(20) NOT NULL,
    encrypted_pin TEXT NOT NULL,
    encrypted_totp_secret TEXT NOT NULL,
    jwt_token TEXT,
    feed_token TEXT,
    token_expiry TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 3. Add constraint
ALTER TABLE user_preferences
ADD CONSTRAINT check_market_data_source
CHECK (market_data_source IN ('smartapi', 'kite'));
```

---

## Phase 3: Frontend Changes

### New Components

| File | Purpose |
|------|---------|
| `frontend/src/components/settings/SmartAPISettings.vue` | Credential input form with test connection |
| `frontend/src/components/settings/MarketDataSourceToggle.vue` | Radio toggle: SmartAPI / Kite |

### Modify Files

| File | Changes |
|------|---------|
| `frontend/src/stores/userPreferences.js` | Add `marketDataSource` getter and updater |
| `frontend/src/views/SettingsView.vue` | Add Market Data Settings section |

---

## Phase 4: SmartAPI Implementation Details (3 APIs)

### API 1: Authentication (generateSession)

**File:** `backend/app/services/smartapi_auth.py`

```python
from SmartApi import SmartConnect
import pyotp

class SmartAPIAuth:
    def __init__(self, api_key: str):
        self.api = SmartConnect(api_key=api_key)

    async def authenticate(self, client_id: str, pin: str, totp_secret: str):
        """Generate session with auto-TOTP"""
        totp = pyotp.TOTP(totp_secret).now()
        data = self.api.generateSession(client_id, pin, totp)
        return {
            'jwt_token': data['data']['jwtToken'],
            'refresh_token': data['data']['refreshToken'],
            'feed_token': self.api.getfeedToken()
        }

    async def refresh_session(self, refresh_token: str):
        """Refresh expired session"""
        return self.api.generateToken(refresh_token)
```

### API 2: WebSocket V2 (Real-Time Streaming)

**File:** `backend/app/services/smartapi_ticker.py`

```python
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

class SmartAPITicker:
    """Singleton WebSocket service mirroring KiteTickerService"""

    MODES = {
        'ltp': 1,      # Last Traded Price only
        'quote': 2,    # OHLC + Volume + OI
        'snap': 3,     # Snapshot quote
        'depth': 4     # Best 20 Buy/Sell
    }

    EXCHANGE_TYPES = {
        'NSE': 1,  # NSE Cash
        'NFO': 2,  # NSE F&O
        'BSE': 3,  # BSE Cash
        'BFO': 4,  # BSE F&O
        'MCX': 5   # MCX
    }

    async def connect(self, jwt_token, api_key, client_id, feed_token):
        self.sws = SmartWebSocketV2(jwt_token, api_key, client_id, feed_token)
        self.sws.on_data = self._on_ticks
        self.sws.on_error = self._on_error
        self.sws.connect()

    async def subscribe(self, tokens: List[str], exchange: str, mode: str = 'quote'):
        token_list = [{
            "exchangeType": self.EXCHANGE_TYPES[exchange],
            "tokens": tokens
        }]
        self.sws.subscribe("algochanakya", self.MODES[mode], token_list)

    def _on_ticks(self, wsapp, message):
        # Normalize to Kite format (prices in rupees)
        normalized = {
            'instrument_token': message['token'],
            'last_price': message['last_traded_price'] / 100,
            'ohlc': {
                'open': message['open_price_of_the_day'] / 100,
                'high': message['high_price_of_the_day'] / 100,
                'low': message['low_price_of_the_day'] / 100,
                'close': message['closed_price'] / 100
            },
            'volume': message.get('volume_trade_for_the_day', 0),
            'oi': message.get('open_interest', 0)
        }
        self._broadcast_ticks([normalized])
```

### API 3a: Market Data API (On-Demand Quotes)

**File:** `backend/app/services/smartapi_market_data.py`

```python
class SmartAPIMarketData:
    """REST API for on-demand quotes (after-market, one-time checks)"""

    ENDPOINT = "/rest/secure/angelbroking/market/v1/quote/"

    async def get_quote(self, exchange: str, tokens: List[str], mode: str = "FULL"):
        """
        Get current quote for instruments
        mode: LTP | OHLC | FULL
        """
        payload = {
            "mode": mode,
            "exchangeTokens": {exchange: tokens}
        }
        response = await self._post(self.ENDPOINT, payload)
        return self._normalize_quote(response['data']['fetched'])

    async def get_ltp(self, instruments: List[str]) -> Dict[str, float]:
        """Get LTP for multiple instruments"""
        # Parse "NFO:NIFTY24DEC26000CE" format
        by_exchange = self._group_by_exchange(instruments)
        result = {}
        for exchange, tokens in by_exchange.items():
            quotes = await self.get_quote(exchange, tokens, mode="LTP")
            result.update(quotes)
        return result
```

### API 3b: Historical Data API (Candle Data)

**File:** `backend/app/services/smartapi_historical.py`

```python
class SmartAPIHistorical:
    """REST API for historical OHLC candle data"""

    ENDPOINT = "/rest/secure/angelbroking/historical/v1/getCandleData"

    INTERVALS = {
        '1m': 'ONE_MINUTE',
        '3m': 'THREE_MINUTE',
        '5m': 'FIVE_MINUTE',
        '10m': 'TEN_MINUTE',
        '15m': 'FIFTEEN_MINUTE',
        '30m': 'THIRTY_MINUTE',
        '1h': 'ONE_HOUR',
        '1d': 'ONE_DAY'
    }

    async def get_candles(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,  # "YYYY-MM-DD HH:MM"
        to_date: str
    ) -> List[Dict]:
        """Fetch historical OHLCV candles (max 8000 per request)"""
        payload = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": self.INTERVALS.get(interval, interval),
            "fromdate": from_date,
            "todate": to_date
        }
        response = await self._post(self.ENDPOINT, payload)
        return self._parse_candles(response['data'])

    async def get_ohlc(self, instruments: List[str]) -> Dict:
        """Get today's OHLC (for after-market fallback)"""
        # Use ONE_DAY interval, today's date
        today = datetime.now().strftime("%Y-%m-%d 09:15")
        result = {}
        for inst in instruments:
            exchange, symbol = inst.split(":")
            token = await self.instruments.lookup_token(symbol, exchange)
            candles = await self.get_candles(exchange, token, '1d', today, today)
            if candles:
                result[inst] = candles[-1]  # Latest candle
        return result
```

### Token Lookup

**File:** `backend/app/services/smartapi_instruments.py`

```python
class SmartAPIInstruments:
    """Instrument master for token lookup"""

    MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    async def download_master(self):
        """Download instrument master (run daily via cron)"""
        response = await httpx.get(self.MASTER_URL)
        instruments = response.json()
        # Index by symbol and exchange for O(1) lookup
        await self._cache_instruments(instruments)

    async def lookup_token(self, tradingsymbol: str, exchange: str) -> Optional[str]:
        """Lookup SmartAPI token from tradingsymbol"""
        cache_key = f"smartapi:instrument:{exchange}:{tradingsymbol}"
        token = await redis.get(cache_key)
        if not token:
            # Search in master
            token = self._search_master(tradingsymbol, exchange)
            if token:
                await redis.setex(cache_key, 86400, token)  # 24h TTL
        return token
```

---

## Phase 5: API Endpoints

### SmartAPI Credential Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/smartapi/credentials` | Store encrypted credentials |
| GET | `/api/smartapi/credentials` | Check if credentials exist |
| DELETE | `/api/smartapi/credentials` | Remove credentials |
| POST | `/api/smartapi/test-connection` | Test with generateSession |

### Modified Endpoints (route based on preference)

| Endpoint | SmartAPI | Kite |
|----------|----------|------|
| `/ws/ticks` | SmartWebSocketV2 | KiteTickerService |
| `/api/orders/ltp` | getLTPData | kite.ltp() |
| `/api/orders/quote` | getMarketData | kite.quote() |
| `/api/orders/ohlc` | getCandleData | kite.ohlc() |

---

## Phase 6: Critical Files to Modify

### Backend (Priority Order)

1. `backend/app/models/user_preferences.py` - Add market_data_source
2. `backend/app/models/smartapi_credentials.py` - NEW: Credentials model
3. `backend/app/utils/encryption.py` - NEW: Fernet encryption
4. `backend/app/services/smartapi_service.py` - NEW: Core service
5. `backend/app/services/smartapi_instruments.py` - NEW: Token lookup
6. `backend/app/services/smartapi_ticker.py` - NEW: WebSocket ticker
7. `backend/app/api/routes/smartapi.py` - NEW: API routes
8. `backend/app/api/routes/websocket.py` - Route to correct ticker
9. `backend/app/api/routes/orders.py` - Route LTP/Quote/OHLC
10. `backend/alembic/versions/XXX_*.py` - Migration

### Frontend (Priority Order)

1. `frontend/src/stores/userPreferences.js` - Add marketDataSource
2. `frontend/src/components/settings/SmartAPISettings.vue` - NEW
3. `frontend/src/components/settings/MarketDataSourceToggle.vue` - NEW
4. `frontend/src/views/SettingsView.vue` - Add settings section

---

## Phase 7: Testing Checklist

- [ ] SmartAPI authentication with auto-TOTP
- [ ] WebSocket connection and tick reception
- [ ] Price conversion (paise → rupees)
- [ ] Token lookup via tradingsymbol
- [ ] Historical data fetching (getCandleData)
- [ ] Data source switch (SmartAPI ↔ Kite)
- [ ] Kite session validation before switch
- [ ] Credential encryption/decryption
- [ ] All existing features work with SmartAPI
- [ ] Fallback to Kite on SmartAPI failure

### TOTP Generation Utility

To generate a TOTP code for testing (after credentials are saved):

```bash
cd backend
venv\Scripts\activate
python generate_totp.py
```

This script:
1. Fetches stored credentials from `smartapi_credentials` table
2. Decrypts the TOTP secret using Fernet
3. Generates the current 6-digit code (valid for 30 seconds)
4. Prints the TOTP and Client ID

---

## Environment Variables

Add to `backend/.env`:
```
# AngelOne SmartAPI
ANGEL_API_KEY=your_api_key_here
```

---

## Prerequisites (User Action Required)

1. Create AngelOne SmartAPI account at https://smartapi.angelbroking.com/
2. Generate API Key from SmartAPI dashboard
3. Enable TOTP (get TOTP secret for auto-generation)
4. Note: Client ID = Angel One trading account ID

---

## Rollout Strategy

1. **Dev Testing** - Test with dev AngelOne account
2. **Feature Flag** - `SMARTAPI_ENABLED=false` initially
3. **Gradual Rollout** - Enable for users who set up credentials
4. **Default Switch** - Make SmartAPI default after validation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SmartAPI downtime | Automatic fallback to Kite if configured |
| Token lookup failure | Cache instrument master, retry logic |
| Session expiry | Auto-refresh before expiry |
| Credential security | Fernet encryption with JWT_SECRET derived key |

---

## Success Criteria

1. Live prices stream via SmartAPI WebSocket V2
2. On-demand quotes work via Market Data API
3. Historical OHLC data fetched from Historical Data API
4. User can switch between SmartAPI and Kite seamlessly
5. All existing features (OptionChain, Strategy, Positions) work unchanged
6. Orders continue to work via Zerodha Kite

---

## Sources

- [AngelOne SmartAPI Documentation](https://smartapi.angelbroking.com/docs)
- [SmartAPI Python SDK (GitHub)](https://github.com/angel-one/smartapi-python)
- [SmartAPI Python on PyPI](https://pypi.org/project/smartapi-python/)
- [Market Data API Announcement](https://smartapi.angelone.in/smartapi/forum/topic/3661/new-feature-announcement-enhanced-real-time-market-data-with-our-market-data-api)
- [Historical Data Tutorial](https://www.marketcalls.in/python/how-to-fetch-historical-stock-market-data-using-smartapi-python-library-angelone-trading-account.html)
- [Real-Time Quotes Tutorial](https://www.marketcalls.in/python/how-to-fetch-realtime-stock-market-quotes-using-smartapi-python-library-angelone-trading-account.html)
- [SmartAPI Introduction](https://www.angelone.in/knowledge-center/smartapi/making-sense-of-the-smartapi-documentation)

---

*Plan created: 2026-01-03*
