# Plan: Align AutoPilot Tests with Global Test Fixtures

## Overview

The AutoPilot test suite I created needs to be audited and updated to properly use the existing global test fixtures instead of duplicating them. This ensures consistency across the codebase and reduces maintenance burden.

---

## Global Fixtures Analysis

### Backend Global Fixtures (`backend/tests/conftest.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `event_loop` | session | Async event loop for all tests |
| `test_engine` | session | SQLite in-memory engine with JSONB→JSON compilation |
| `db_session` | function | Clean database session with table cleanup |
| `client` | function | AsyncClient with dependency overrides |
| `test_user` | function | User with UUID and email |
| `test_broker_connection` | function | Zerodha broker connection |
| `mock_kite_client` | function | Mock Kite Connect client |
| `auth_headers` | function | Authorization headers |
| Allure hooks | N/A | Test reporting configuration |

### AutoPilot Fixtures (`backend/tests/backend/autopilot/conftest.py`)

| Fixture | Purpose | Currently Used In Tests |
|---------|---------|------------------------|
| `test_user` | Primary test user | ✅ |
| `another_user` | Isolation tests | ❌ Need to use |
| `test_settings` | User settings | ❌ Need to use |
| `test_strategy` | Draft strategy | ✅ |
| `test_strategy_waiting` | Waiting strategy | ❌ Need to use |
| `test_strategy_active` | Active strategy | ❌ Need to use |
| `test_strategy_paused` | Paused strategy | ❌ Need to use |
| `test_strategy_completed` | Completed strategy | ❌ Need to use |
| `test_order` | Order fixture | ❌ Need to use |
| `test_log` | Log fixture | ❌ Need to use |
| `test_template` | Template fixture | ❌ Need to use |
| `mock_kite` | Kite mock | ❌ Need to use |
| `mock_market_data` | MarketDataService mock | ❌ Need to use |
| `mock_ws_manager` | WebSocket manager mock | ❌ Need to use |
| `mock_condition_engine` | ConditionEngine mock | ❌ Need to use |
| `mock_order_executor` | OrderExecutor mock | ❌ Need to use |
| `client` | Authenticated HTTP client | ✅ |
| `unauthenticated_client` | No-auth HTTP client | ❌ Need to use |

### Helper Functions to Use

```python
# From conftest.py - use these instead of inline assertions
create_strategy_request()      # Build strategy POST payloads
assert_strategy_response()     # Validate strategy response
assert_settings_response()     # Validate settings response
assert_dashboard_response()    # Validate dashboard summary
get_sample_legs_config()       # Standard Iron Condor legs
get_sample_entry_conditions()  # Time and VIX conditions
get_sample_risk_settings()     # Max loss, trailing stops
get_sample_order_settings()    # Execution style, slippage
get_sample_schedule_config()   # Trading hours and days
```

### E2E Test Fixtures

| Fixture | Source | Must Use |
|---------|--------|----------|
| `test` | `auth.fixture.js` | Yes - NOT `@playwright/test` |
| `authenticatedPage` | `auth.fixture.js` | Yes - for all auth tests |
| `auditablePage` | `auth.fixture.js` | Yes - for audit tests |
| `BasePage` | `pages/BasePage.js` | Yes - extend for POMs |

### E2E Browser & Login Requirements (`playwright.config.js`)

| Requirement | Configuration | Why |
|-------------|---------------|-----|
| **Single browser window** | `workers: 1, fullyParallel: false` | No auth flickering, shared session |
| **Full screen browser** | `viewport: null, args: ['--start-maximized']` | Consistent visual tests |
| **Reuse auth state** | `storageState: './tests/config/.auth-state.json'` | Login once for all tests |
| **3-minute timeout** | `timeout: 180000` | Allow manual TOTP entry |

### E2E Login Flow (`tests/e2e/global-setup.js`)

The login happens ONCE before all tests:

1. **Check existing auth**: Validates stored token via `/api/auth/me`
2. **If valid**: Reuses saved auth state (skips login)
3. **If invalid**:
   - Opens browser (non-headless)
   - **Auto-fills credentials** from `tests/config/credentials.js`:
     - User ID (kite.userId)
     - Password (kite.password)
   - **Only TOTP is manual** - waits 60 seconds for entry
   - Extracts token after OAuth callback
   - Saves to `.auth-token` and `.auth-state.json`
4. **All tests reuse**: Auth state loaded automatically

### Credentials File (`tests/config/credentials.js`)

```javascript
// Copy from credentials.example.js - GITIGNORED
export const credentials = {
  kite: {
    userId: 'YOUR_KITE_USER_ID',    // Auto-filled
    password: 'YOUR_KITE_PASSWORD',  // Auto-filled
    // TOTP is entered manually (unique per login)
  }
};
```

---

## Files Requiring Updates

### 1. Backend API Tests

| File | Issues | Fix |
|------|--------|-----|
| `test_api_settings.py` | Missing use of `test_settings` fixture | Use existing fixture |
| `test_api_strategies.py` | Creates inline strategies | Use `test_strategy_*` fixtures |
| `test_api_lifecycle.py` | Creates inline strategies | Use state fixtures |
| `test_api_dashboard.py` | Creates inline data | Use existing fixtures |

### 2. Backend Service Tests

| File | Issues | Fix |
|------|--------|-----|
| `test_services_market_data.py` | Creates own mocks | Use `mock_market_data` |
| `test_services_condition_engine.py` | Creates own mocks | Use `mock_condition_engine` |
| `test_services_order_executor.py` | Creates own mocks | Use `mock_order_executor` |
| `test_services_strategy_monitor.py` | Creates own mocks | Use all mock fixtures |

### 3. Backend WebSocket Tests

| File | Issues | Fix |
|------|--------|-----|
| `test_websocket_manager.py` | Creates own manager | Use `mock_ws_manager` patterns |
| `test_websocket_routes.py` | Creates own fixtures | Use `client` and mocks |

### 4. Frontend Tests

| File | Issues | Fix |
|------|--------|-----|
| `frontend/tests/setup.js` | Good - already correct | No changes |
| `stores/autopilot.test.js` | Good - uses vi.mock | Minor cleanup |
| `composables/useWebSocket.test.js` | Good - mocks stores | Minor cleanup |

### 5. E2E Tests

| File | Issues | Fix |
|------|--------|-----|
| `autopilot.happy.spec.js` | Must import from `auth.fixture.js` | ✅ Already correct |
| `autopilot.edge.spec.js` | Must import from `auth.fixture.js` | ✅ Already correct |
| `autopilot.api.spec.js` | Must import from `auth.fixture.js` | ✅ Already correct |
| `AutoPilotDashboardPage.js` | Must extend `BasePage` | ✅ Already correct |

---

## Detailed Changes Required

### Change 1: Use Existing Strategy State Fixtures

**Before (inline creation):**
```python
@pytest.fixture
async def draft_strategy(db_session, test_user):
    strategy = AutoPilotStrategy(...)  # Duplicate code
    db_session.add(strategy)
    return strategy
```

**After (use existing):**
```python
# Just use the fixture from conftest.py
async def test_activate_draft(client, test_strategy):
    response = await client.post(f"/api/v1/autopilot/strategies/{test_strategy.id}/activate")
```

### Change 2: Use Mock Service Fixtures

**Before (inline mocks):**
```python
@pytest.fixture
def mock_market_data():
    mock = AsyncMock()
    mock.get_ltp.return_value = {...}  # Duplicate setup
    return mock
```

**After (use existing):**
```python
# The fixture is already in conftest.py
async def test_condition_evaluation(mock_market_data, mock_condition_engine):
    # Use directly - no need to create
```

### Change 3: Use Helper Functions for Requests

**Before (inline payloads):**
```python
payload = {
    "name": "Test",
    "underlying": "NIFTY",
    "legs_config": [...]  # Repeated everywhere
}
```

**After (use helpers):**
```python
from conftest import create_strategy_request, get_sample_legs_config

payload = create_strategy_request(
    name="Test",
    legs_config=get_sample_legs_config()
)
```

### Change 4: Use Assertion Helpers

**Before (inline assertions):**
```python
assert "id" in response_data
assert "name" in response_data
assert "status" in response_data
# ... repeated validation
```

**After (use helpers):**
```python
from conftest import assert_strategy_response

assert_strategy_response(response_data, expected_status="active")
```

---

## Implementation Checklist

### Phase 1: Update Backend API Tests
- [ ] `test_api_settings.py` - Use `test_settings`, `assert_settings_response()`
- [ ] `test_api_strategies.py` - Use `test_strategy_*`, `create_strategy_request()`, `assert_strategy_response()`
- [ ] `test_api_lifecycle.py` - Use all strategy state fixtures
- [ ] `test_api_dashboard.py` - Use `assert_dashboard_response()`

### Phase 2: Update Backend Service Tests
- [ ] `test_services_market_data.py` - Use `mock_kite` from conftest
- [ ] `test_services_condition_engine.py` - Use `mock_market_data`, sample configs
- [ ] `test_services_order_executor.py` - Use `mock_kite`, `mock_market_data`
- [ ] `test_services_strategy_monitor.py` - Use all mock fixtures

### Phase 3: Update Backend WebSocket Tests
- [ ] `test_websocket_manager.py` - Align with `mock_ws_manager` patterns
- [ ] `test_websocket_routes.py` - Use `client`, proper JWT fixtures

### Phase 4: Frontend & E2E (Already Correct)
- [x] `frontend/tests/setup.js` - Correct
- [x] E2E tests import from `auth.fixture.js` - Correct
- [x] Page objects extend `BasePage` - Correct

---

## Files to Modify

1. `backend/tests/backend/autopilot/test_api_settings.py`
2. `backend/tests/backend/autopilot/test_api_strategies.py`
3. `backend/tests/backend/autopilot/test_api_lifecycle.py`
4. `backend/tests/backend/autopilot/test_api_dashboard.py`
5. `backend/tests/backend/autopilot/test_services_market_data.py`
6. `backend/tests/backend/autopilot/test_services_condition_engine.py`
7. `backend/tests/backend/autopilot/test_services_order_executor.py`
8. `backend/tests/backend/autopilot/test_services_strategy_monitor.py`
9. `backend/tests/backend/autopilot/test_websocket_manager.py`
10. `backend/tests/backend/autopilot/test_websocket_routes.py`

---

## Key Rules Summary

### Backend Tests Must:
1. Import from `conftest.py` fixtures - don't duplicate
2. Use `@pytest_asyncio.fixture` for async operations
3. Use existing mock fixtures (`mock_kite`, `mock_market_data`, etc.)
4. Use helper functions (`create_strategy_request()`, `assert_*_response()`)
5. Use state fixtures (`test_strategy_waiting`, `test_strategy_active`, etc.)
6. Override dependencies via `app.dependency_overrides`
7. Clear overrides after test: `app.dependency_overrides.clear()`

### E2E Tests Must:
1. Import `test` from `auth.fixture.js` (NOT `@playwright/test`)
2. Use `authenticatedPage` fixture for all authenticated tests
3. All selectors via `data-testid` and POM `getByTestId()`
4. Page objects must extend `BasePage`
5. No inline selectors or CSS class selectors
6. **Browser**: Single window, full screen (`workers: 1`, `--start-maximized`)
7. **Login**: Auto-fills credentials, only TOTP is manual
8. **Auth reuse**: All tests share auth from `global-setup.js`
9. **Credentials**: Store in `tests/config/credentials.js` (gitignored)
