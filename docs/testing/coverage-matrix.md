# AlgoChanakya Test Coverage Matrix

Last Updated: 2026-02-26

## Legend
- Implemented and passing
- Partially implemented
- Not implemented
- In progress
- N/A Not applicable

## Backend API Tests

| Endpoint | Unit | API | Integration | Edge Cases | Auth |
|----------|------|-----|-------------|------------|------|
| **Authentication** |
| POST /auth/login | Yes | Yes | Yes | Yes | N/A |
| GET /auth/callback | Yes | Yes | Yes | Yes | N/A |
| POST /auth/logout | Yes | Yes | Yes | Yes | Yes |
| GET /auth/me | Yes | Yes | Yes | Yes | Yes |
| **Watchlist** |
| GET /watchlist | Yes | Yes | Yes | Yes | Yes |
| POST /watchlist | Yes | Yes | Yes | Yes | Yes |
| DELETE /watchlist/{id} | Yes | Yes | Yes | Yes | Yes |
| **Option Chain** |
| GET /optionchain | Yes | Yes | Yes | Yes | Yes |
| GET /optionchain/expiries | Yes | Yes | Yes | Yes | Yes |
| **Strategy Builder** |
| POST /strategy/calculate | Yes | Yes | Yes | Yes | Yes |
| GET /strategy/payoff | Yes | Yes | Yes | Yes | Yes |
| **Positions** |
| GET /positions | Yes | Yes | Partial | Yes | Yes |
| POST /positions/exit | Yes | Yes | Partial | Yes | Yes |
| POST /positions/add | Yes | Yes | Partial | Yes | Yes |
| POST /positions/exit-all | Yes | Yes | Partial | Yes | Yes |
| **Strategy Wizard** |
| GET /strategy-wizard/templates | Yes | Yes | Pending | Pending | Yes |
| GET /strategy-wizard/templates/{name} | Yes | Yes | Pending | Pending | Yes |
| POST /strategy-wizard/wizard | Yes | Yes | Pending | Pending | Yes |
| POST /strategy-wizard/deploy | Yes | Yes | Pending | Pending | Yes |
| GET /strategy-wizard/popular | Yes | Yes | Pending | Pending | Yes |

## Frontend E2E Tests

| Feature | Happy Path | Edge Cases | Visual | API Mock | Accessibility |
|---------|------------|------------|--------|----------|---------------|
| **Authentication** |
| Login page | Yes | Yes | Yes | Yes | Partial |
| OAuth callback | Yes | Yes | N/A | Yes | N/A |
| Session management | Yes | Yes | N/A | Yes | N/A |
| **Dashboard** |
| Market overview | Yes | Partial | Yes | Yes | Partial |
| Quick actions | Yes | Yes | Yes | Yes | Partial |
| **Watchlist** |
| View watchlist | Yes | Yes | Yes | Yes | Partial |
| Add symbol | Yes | Yes | Yes | Yes | Partial |
| Remove symbol | Yes | Yes | Yes | Yes | Partial |
| Live prices | Yes | Partial | Yes | Yes | N/A |
| **Option Chain** |
| View chain | Yes | Yes | Yes | Yes | Partial |
| Change expiry | Yes | Yes | Yes | Yes | Partial |
| Greeks display | Yes | Yes | Yes | Yes | Partial |
| OI analysis | Yes | Yes | Yes | Yes | Partial |
| **Strategy Builder** |
| Add legs | Yes | Yes | Yes | Yes | Partial |
| P&L calculation | Yes | Yes | Yes | Yes | N/A |
| Payoff chart | Yes | Yes | Yes | Yes | N/A |
| Place orders | Yes | Yes | Yes | Yes | Partial |
| **Positions** |
| View positions | Yes | Yes | Yes | Yes | Partial |
| Exit position | Yes | Yes | Yes | Yes | Partial |
| Add to position | Yes | Yes | Yes | Yes | Partial |
| Exit all | Yes | Yes | Yes | Yes | Partial |
| **Strategy Library** |
| Browse strategies | Yes | Yes | Yes | Yes | Partial |
| Strategy wizard | Yes | Yes | Yes | Yes | Partial |
| Deploy strategy | Yes | Yes | Yes | Yes | Partial |
| Compare strategies | Pending | Pending | Pending | Pending | Pending |

## Live Broker Tests (real broker APIs, `@live` marker)

| Test Area | Brokers Covered | Skip Behavior |
|-----------|----------------|---------------|
| WebSocket ticker | Zerodha, AngelOne, Upstox, Dhan, Fyers, Paytm | Skip if credentials absent |
| Market data (quote/LTP/historical) | All 6 | Skip if credentials absent |
| Authentication flows | All 6 | Skip if credentials absent |
| Order execution | All 6 | Skip if credentials absent |
| Option chain | All 6 | Skip if credentials absent |
| Instrument search | All 6 | Skip if credentials absent |
| Screens API | All 6 | Skip if credentials absent |

Run with: `pytest tests/live/ -m live -v` (from `backend/`). See `docs/testing/README.md` for full details.

## Test Statistics

> **Note:** Test counts change frequently. Run the commands in `docs/testing/README.md` for current numbers.

| Category | Total | Passing | Failing | Skipped | Coverage |
|----------|-------|---------|---------|---------|----------|
| Backend Unit | 16 | 16 | 0 | 0 | 85% |
| Backend API | 42 | 42 | 0 | 0 | 88% |
| Backend Integration | 15 | 15 | 0 | 0 | 75% |
| Backend Live (`@live`) | 7 files (parameterized x6 brokers) | Varies by credentials | 0 | Varies | N/A (real APIs) |
| Frontend E2E | 240+ | 240+ | 0 | 0 | 85% |
| **Total (excl. live)** | **313+** | **313+** | **0** | **0** | **85%** |

## Priority Test Gaps

### High Priority (Must implement)
1. Strategy Library Compare - E2E tests missing
2. Integration tests for deploy flow
3. Accessibility tests - Mostly partial

### Medium Priority
1. Visual regression tests expansion
2. Performance tests
3. Load tests for WebSocket

### Low Priority
1. Cross-browser testing (Firefox, Safari)
2. Mobile responsive tests
3. Offline mode tests

## Test File Locations

### Backend
```
backend/tests/
  test_strategy_templates.py    # 16 tests - Model tests
  test_strategy_wizard_api.py   # 42 tests - API tests (with Allure)
  test_strategy_validation.py   # 15 tests - Validation tests
  test_strategy_integration.py  # 5 tests - Integration tests
  conftest.py                   # Fixtures and Allure hooks

backend/tests/live/             # Live broker tests (@live marker)
  test_live_websocket_ticker.py
  test_live_market_data.py
  test_live_authentication.py
  test_live_order_execution.py
  test_live_option_chain.py
  test_live_instrument_search.py
  test_live_screens_api.py

backend/tests/factories/        # Shared test data builders
  ticks.py
  strategies.py
  broker.py
```

### Frontend Unit Helpers
```
frontend/tests/helpers/
  test-setup.js   # Pinia/localStorage/env setup
  factories.js    # Mock data factories
```

### Frontend E2E
```
tests/e2e/specs/
  login/           # 5 spec files
  dashboard/       # 4 spec files
  positions/       # 5 spec files
  watchlist/       # 5 spec files
  optionchain/     # 5 spec files
  strategy/        # 5 spec files
  strategylibrary/ # 5 spec files (160+ tests)
  live/            # Live broker E2E tests
  integration/     # Integration specs


tests/e2e/helpers/
  assertions.js   # Shared Playwright assertion utilities
```
