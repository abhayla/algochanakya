# Phase 5 Test Suite - README

## Test Files Created

This directory contains comprehensive test coverage for Phase 5 "Advanced Adjustments & Option Chain Integration" features.

### Completed Test Files

1. **conftest.py** - Phase 5 fixtures added:
   - `test_position_leg` - Single position leg fixture
   - `test_position_legs_multiple` - Multi-leg strangle fixture
   - `test_suggestion` - Adjustment suggestion fixture
   - `mock_option_chain_service` - Mocked option chain service
   - `test_break_trade_scenario` - Break trade test scenario
   - `test_shift_leg_scenario` - Shift leg test scenario
   - Helper functions: `get_mock_option_chain_response()`, `get_sample_position_leg_data()`, etc.

2. **test_models_phase5.py** (25 tests):
   - AutoPilotPositionLeg CRUD and status transitions
   - AutoPilotAdjustmentSuggestion lifecycle
   - New columns on AutoPilotStrategy (net_delta, breakeven, DTE)
   - New columns on AutoPilotUserSettings (delta thresholds, preferences)

3. **test_services_option_chain.py** (10 tests):
   - Option chain fetching from Kite API
   - Cache hit/miss behavior
   - Greeks calculation
   - ATM strike identification
   - Error handling

4. **test_services_strike_finder.py** (12 tests):
   - Find strike by delta (exact, closest, round preference)
   - Find strike by premium
   - Find strikes in range (delta/premium)
   - ATM strike finding
   - Edge cases (no match, empty chain)

5. **test_api_option_chain.py** (20 tests):
   - GET option chain (full, filtered by CE/PE)
   - GET strikes list
   - POST find by delta
   - POST find by premium
   - GET ATM strike
   - GET strikes in range
   - GET expiries list

## Remaining Test Files Template

### To Create Next:

**test_schemas_phase5.py** - Should test:
- PositionLegBase, Create, Update, Response schemas
- OptionChainEntry, OptionChainResponse
- StrikeFindByDelta/Premium Request/Response
- ExitLegRequest, ShiftLegRequest, RollLegRequest, BreakTradeRequest
- Suggestion schemas
- WhatIf schemas
- Payoff schemas
- Validation rules (delta 0-1, premium > 0, etc.)

**test_services_position_leg.py** - Should test:
- create_leg(), get_leg(), get_all_strategy_legs()
- update_leg_greeks(), update_leg_pnl()
- close_leg() sets status and exit fields
- calculate_unrealized_pnl(), calculate_realized_pnl()
- link_rolled_legs()

**test_api_legs.py** - Should test:
- GET /legs/strategies/{id}/legs
- GET /legs/strategies/{id}/legs/{leg_id}
- POST /legs/strategies/{id}/legs/{leg_id}/exit
- POST /legs/strategies/{id}/legs/{leg_id}/shift
- POST /legs/strategies/{id}/legs/{leg_id}/roll
- POST /legs/strategies/{id}/legs/{leg_id}/break
- POST /legs/strategies/{id}/legs/{leg_id}/break/simulate
- POST /legs/strategies/{id}/legs/update-greeks

**test_services_leg_actions.py** - Should test:
- exit_leg() with market/limit orders
- shift_leg() by strike/delta/direction
- roll_leg() to new expiry with optional strike change
- Dry run mode
- Failure rollback

**test_services_break_trade.py** - Should test:
- calculate_exit_cost()
- calculate_recovery_premiums() (equal/weighted split)
- find_new_strikes() by premium with round preference
- execute_break_trade() full flow
- simulate_break_trade()
- Validation (invalid leg, closed leg)
- Partial failure rollback

**test_services_suggestion_engine.py** - Should test:
- generate_suggestions() for strategy
- Delta-based suggestions (high delta → break trade)
- P&L-based suggestions (profitable → shift)
- DTE-based suggestions (near expiry → exit)
- Risk-based suggestions
- Cooldown prevents duplicates
- One-click params generation

**test_api_suggestions.py** - Should test:
- GET /suggestions/strategies/{id}
- GET /suggestions/strategies/{id}/suggestions/{sid}
- POST /suggestions/{sid}/dismiss
- POST /suggestions/{sid}/execute
- POST /suggestions/refresh
- Filters (excludes dismissed/executed)

**test_services_whatif_simulator.py** - Should test:
- simulate_shift(), simulate_roll(), simulate_break(), simulate_exit()
- calculate_impact() metrics
- compare_scenarios() with ranking
- get_recommendation()

**test_api_simulation.py** - Should test:
- POST /simulate/{id}/shift
- POST /simulate/{id}/roll
- POST /simulate/{id}/break
- POST /simulate/{id}/exit
- POST /simulate/{id}/compare

**test_services_payoff_calculator.py** - Should test:
- calculate_payoff() single/multiple legs
- calculate_payoff_call_buy_sell(), calculate_payoff_put_buy_sell()
- calculate_breakevens()
- calculate_max_profit(), calculate_max_loss()
- greeks_heatmap()

**test_api_analytics_phase5.py** - Should test:
- GET /analytics/{id}/payoff
- GET /analytics/{id}/risk-metrics
- GET /analytics/{id}/breakevens
- POST /analytics/{id}/pnl-at-spot
- GET /analytics/{id}/profit-zones
- GET /analytics/{id}/greeks-heatmap

**test_integration_phase5.py** - Should test:
- Full break trade flow (identify → preview → execute)
- Full shift leg flow
- Full roll leg flow
- Suggestion to execution flow
- What-if to adjustment flow
- Delta alert to adjustment flow
- WebSocket leg updates
- Concurrent operations

## Running Tests

```bash
# All Phase 5 tests
pytest tests/backend/autopilot/test_*phase5*.py -v

# Specific service
pytest tests/backend/autopilot/test_services_option_chain.py -v

# With coverage
pytest tests/backend/autopilot/test_*phase5*.py -v --cov=app/services

# Integration tests only
pytest tests/backend/autopilot/test_integration_phase5.py -v
```

## Key Testing Patterns

1. **Use Fixtures**: Import from conftest.py, don't create duplicates
2. **Mock External APIs**: Always mock Kite API calls
3. **Test Success and Failure**: Happy path + error cases
4. **Async Tests**: Use `@pytest.mark.asyncio` decorator
5. **Assertions**: Use helper functions like `assert_position_leg_response()`
6. **Isolation**: Each test should be independent
7. **Naming**: `test_<feature>_<scenario>`

## Test Data

Mock data generators in conftest.py:
- `get_mock_option_chain_response()` - Full option chain with Greeks
- `get_sample_position_leg_data()` - Position leg data
- `get_sample_suggestion_data()` - Suggestion data  
- `get_mock_break_trade_scenario()` - Break trade scenario

## Coverage Goals

- Services: > 90%
- API endpoints: > 95%
- Models: > 85%
- Integration: > 80%

## Notes

- All tests use SQLite in-memory database
- Tests clean up after themselves (see db_session fixture)
- Phase 5 tables are cleaned before Phase 1-4 tables (FK dependencies)
- Use descriptive test names and docstrings
- Group related tests in classes
