# Session: NIFTY Closing Prices Fix
**Saved:** 2026-01-25
**Auto-generated:** false

## Summary
Fixed the issue where NIFTY 50 and NIFTY BANK values showed "--" in the header when the market is closed. The root cause was a timezone comparison bug in the SmartAPI token expiry check, combined with a logic flow issue that prevented proper token refresh after the 5 AM IST daily flush.

## Working Files
- `backend/app/utils/smartapi_utils.py` (lines 75-99) - **KEY FIX**: Fixed timezone comparison and logic flow for 5 AM token refresh
- `backend/app/services/smartapi_auth.py` (lines 110-123) - Updated token expiry calculation to use 5 AM IST instead of 8 hours
- `backend/app/api/routes/websocket.py` (lines 160-238) - Added `fetch_initial_index_quotes()` to fetch REST quotes on subscribe
- `backend/app/services/brokers/market_data/smartapi_adapter.py` - Added lazy loading for instrument master
- `backend/app/services/brokers/market_data/factory.py` (lines 86-112) - Integrated auto-refresh with `get_valid_smartapi_credentials()`

## Recent Changes
16 files modified with ~565 additions. Key changes:
1. **smartapi_utils.py** - Fixed timezone-aware vs naive datetime comparison, added `needs_refresh` flag to prevent returning stale credentials
2. **smartapi_auth.py** - Changed token expiry from "8 hours from now" to "next 5 AM IST"
3. **websocket.py** - Added `KITE_TO_SMARTAPI_INDEX` mapping and `fetch_initial_index_quotes()` function
4. **smartapi_adapter.py** - Added `skip_instrument_download` parameter for fast index-only queries
5. **factory.py** - Uses `auto_refresh=True` and skips instrument download on adapter creation

## Todo State
No active todos - fix is complete and verified.

## Key Decisions
- **5 AM IST Token Flush**: SmartAPI tokens are flushed at 5 AM IST daily (per SmartAPI forum), not 8 hours from login
- **Lazy Loading**: Instrument master (~50MB, 185k instruments) is only downloaded when needed for option symbols, not for index quotes
- **Initial REST Quotes**: When WebSocket subscribes, also fetch REST API quotes to ensure UI shows values even when market is closed
- **Timezone Handling**: Assume DB datetime without tzinfo is UTC (standard practice), then convert to UTC-aware for comparison

## Relevant Docs
- [Broker Abstraction Architecture](../../docs/architecture/broker-abstraction.md) - Multi-broker design, adapter pattern
- [SmartAPI Token Validity](https://smartapi.angelone.in/smartapi/forum/topic/468/token-s-validity-period) - External: 5 AM flush confirmation

## Where I Left Off
### Completed:
- Fixed timezone comparison bug in `smartapi_utils.py`
- Verified fix works: NIFTY 50 and NIFTY BANK values now display in header
- Dashboard E2E tests pass (9/9)
- Screenshot captured: `screenshots/verification/nifty-values-showing-2026-01-25.png`

### Next Steps (if continuing):
1. **Commit the changes** - All changes are uncommitted
2. **Add unit tests** for the timezone comparison logic in `smartapi_utils.py`
3. **Test edge cases**: Token refresh when user logs in just before 5 AM, multiple users, etc.

### Open Questions:
- None - fix is verified working

## Resume Prompt
```
Continue from the NIFTY closing prices fix session. The timezone comparison bug in smartapi_utils.py has been fixed and verified. Next steps are to commit the changes with a proper commit message. The key files modified are:
- backend/app/utils/smartapi_utils.py (main fix)
- backend/app/services/smartapi_auth.py (5 AM expiry)
- backend/app/api/routes/websocket.py (initial quotes)
```
