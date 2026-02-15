# Session: SmartAPI Market Data Fix
**Saved:** 2026-01-23
**Auto-generated:** false

## Summary
Debugging and fixing live market data issues with AngelOne SmartAPI integration. The session involved fixing multiple issues preventing the Option Chain screen from loading market data:
1. WebSocket URL was malformed (double protocol prefix)
2. SmartAPI token had expired and needed re-authentication
3. SmartAPI adapter was using wrong API key (`broker_type` instead of `settings.ANGEL_API_KEY`)
4. SmartAPI adapter's `get_ltp` method didn't handle index symbols (NIFTY, BANKNIFTY, etc.)
5. Adapter was incorrectly dividing REST API prices by 100 (only WebSocket uses PAISE)

Also made minor documentation improvements to CLAUDE.md.

## Working Files
- `frontend/.env.local` (modified) - Fixed WebSocket URL, removed protocol prefix
- `backend/app/services/brokers/market_data/smartapi_adapter.py` (modified) - Multiple fixes for API key and index symbol handling
- `CLAUDE.md` (modified) - Added stale docs warning and browser-testing skill
- `docs/DEVELOPER-QUICK-REFERENCE.md` (modified) - Fixed typo in dev path
- `backend/app/services/smartapi_market_data.py` (read) - Analyzed get_index_quote method
- `backend/app/services/brokers/market_data/factory.py` (read) - Analyzed adapter creation
- `backend/app/api/routes/optionchain.py` (read) - Analyzed how spot price is fetched

## Recent Changes
```diff
# frontend/.env.local
- VITE_WS_URL=ws://localhost:8001
+ VITE_WS_URL=localhost:8001

# backend/app/services/brokers/market_data/smartapi_adapter.py
- api_key=credentials.broker_type  # WRONG
+ api_key = getattr(settings, 'ANGEL_API_KEY', None)  # CORRECT

# Added INDEX_SYMBOLS handling in get_ltp method
# Fixed PAISE/RUPEES conversion (REST API returns RUPEES, not PAISE)

# CLAUDE.md
+ Added stale docs warning for IMPLEMENTATION-CHECKLIST.md
+ Added browser-testing skill to skills table

# docs/DEVELOPER-QUICK-REFERENCE.md
- C:\Abhay\VideCoding (typo)
+ D:\Abhay\VibeCoding (correct)
```

## Todo State
No active todo list.

## Key Decisions
1. **WebSocket URL format**: Frontend code adds `ws://` prefix automatically, so `.env.local` should only contain host:port (e.g., `localhost:8001`)
2. **Index symbol handling**: Added `INDEX_SYMBOLS` set to adapter to route index queries (NIFTY, BANKNIFTY, etc.) through `get_index_quote()` instead of token manager lookup
3. **Price normalization**: REST API returns prices in RUPEES (already normalized), only WebSocket returns PAISE (needs /100 conversion)

## Relevant Docs
- [Broker Abstraction Architecture](../../docs/architecture/broker-abstraction.md) - Core multi-broker design being implemented
- [CLAUDE.md](../../CLAUDE.md) - Contains environment variable docs and important patterns

## Where I Left Off

### Completed
- ✅ Fixed WebSocket URL malformation in `frontend/.env.local`
- ✅ Re-authenticated SmartAPI (token was expired)
- ✅ Fixed SmartAPI adapter to use `settings.ANGEL_API_KEY` instead of `broker_type`
- ✅ Added index symbol handling to `get_ltp` method
- ✅ Fixed PAISE/RUPEES conversion (removed incorrect /100 division)
- ✅ Minor CLAUDE.md documentation improvements

### Still Failing
- ❌ Option Chain still shows "Could not get spot price" error (500)
- ❌ Header NIFTY/BANKNIFTY prices still showing "--"

### Investigation Status
The SmartAPI `get_index_quote` method is being called but may be returning None or failing silently. Possible causes:
1. SmartAPI REST API call failing (need to check backend console logs)
2. JWT token format issue
3. Market might be closed (though should still return last price)

### Next Steps
1. **Check backend console** - Look for error messages from SmartAPI calls
2. **Add debug logging** - Add more logging to `smartapi_market_data.py` get_index_quote and get_quote methods
3. **Test SmartAPI directly** - Create a simple test script to verify SmartAPI credentials work:
   ```python
   from SmartApi import SmartConnect
   api = SmartConnect(api_key="hGio9H2H")
   api.setAccessToken("<jwt_token_from_db>")
   result = api.getMarketData("LTP", {"NSE": ["99926000"]})
   print(result)
   ```
4. **Check if market is open** - Verify if issue is time-related

### Open Questions
- Is the SmartAPI JWT token format correct? (should not have "Bearer " prefix)
- Is the SmartAPI returning an error that's being swallowed?
- Could Redis being disconnected (seen in health check) affect anything?

## Resume Prompt
```
Continue debugging SmartAPI market data issue.

Status: Option chain still fails with "Could not get spot price" after multiple fixes.

Completed fixes:
- WebSocket URL in .env.local
- SmartAPI adapter API key (now uses settings.ANGEL_API_KEY)
- Index symbol handling in get_ltp (uses get_index_quote for NIFTY/BANKNIFTY)
- Removed incorrect /100 division for REST API prices

Next: Check backend console logs for SmartAPI errors, add debug logging to smartapi_market_data.py, or create test script to verify SmartAPI credentials directly.

Key files:
- backend/app/services/smartapi_market_data.py (get_index_quote method)
- backend/app/services/brokers/market_data/smartapi_adapter.py (get_ltp method)
```
