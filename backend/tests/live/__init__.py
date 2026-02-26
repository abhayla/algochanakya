"""
Live integration tests for AlgoChanakya broker adapters.

These tests call REAL broker APIs with live credentials from backend/.env.
They will FAIL if:
- A broker's credentials are missing from .env (test is skipped with message)
- A broker's API is unreachable or returns errors
- Response data does not meet expected shape/value constraints

Run all live tests:
    pytest tests/live/ -v

Run for a single broker:
    pytest tests/live/ -v -k "angelone"

Run a single test file:
    pytest tests/live/test_live_websocket_ticker.py -v

IMPORTANT: These tests use real market APIs. Run during market hours for
live tick tests, or off-hours for REST/historical tests.
"""
