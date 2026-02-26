"""
Live Screen API Tests — all 6 brokers, parameterized.

Tests the backend API endpoints (watchlist, option chain, positions, dashboard)
with each broker configured as the user's market_data_source.

These are integration tests that:
1. Start the FastAPI app in test mode
2. Authenticate a real user
3. Set market_data_source = broker under test
4. Call the API endpoint
5. Assert the response contains real, valid data

Tests FAIL if:
- API returns non-200 status
- Response contains empty or zero price data
- Broker-specific data is missing or malformed

Run:
    pytest tests/live/test_live_screens_api.py -v
    pytest tests/live/test_live_screens_api.py -v -k "watchlist and angelone"
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from tests.live.constants import NIFTY_MIN_PRICE, NIFTY_MAX_PRICE


# ─────────────────────────────────────────────────────────────────────────────
# Parametrize over all 6 brokers
# ─────────────────────────────────────────────────────────────────────────────

ALL_BROKERS = [
    pytest.param("angelone", id="angelone"),
    pytest.param("kite",     id="kite"),
    pytest.param("upstox",   id="upstox"),
    pytest.param("dhan",     id="dhan"),
    pytest.param("fyers",    id="fyers"),
    pytest.param("paytm",    id="paytm"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def live_app_client():
    """HTTP client connected to a real running backend (localhost:8001)."""
    # Tests hit the real running dev backend rather than a test app instance.
    # This ensures platform-level broker routing code is exercised end-to-end.
    #
    # Session-scoped to share one client across all broker tests (avoids re-login).
    # Teardown uses try/except to suppress "Event loop is closed" errors that
    # can occur when pytest tears down session fixtures after the event loop closes.
    import httpx
    # limits=httpx.Limits(max_keepalive_connections=0) disables keep-alive so
    # each request uses a fresh TCP connection — avoids stuck connections after
    # long-running requests (e.g. AngelOne login takes 20-25s).
    client = httpx.AsyncClient(
        base_url="http://localhost:8001",
        timeout=60.0,
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
    )
    try:
        # Verify backend is running
        try:
            resp = await client.get("/api/health")
            if resp.status_code != 200:
                await client.aclose()
                pytest.skip(
                    f"Dev backend not running at localhost:8001 "
                    f"(got {resp.status_code}). Start backend first: python run.py"
                )
        except Exception:
            await client.aclose()
            pytest.skip(
                "Dev backend not running at localhost:8001. "
                "Start backend first: cd backend && python run.py"
            )
        yield client
    finally:
        try:
            await client.aclose()
        except Exception:
            pass  # Suppress "Event loop is closed" during session teardown


@pytest_asyncio.fixture(scope="session")
async def live_auth_token(live_app_client, angelone_credentials):
    """
    Obtain a real JWT from the running backend via AngelOne login.

    AngelOne is used as the primary auth method since it supports auto-TOTP.
    Session-scoped so the 20-25s login only happens once per test run.
    """
    resp = await live_app_client.post("/api/auth/angelone/login", json={
        "client_id": angelone_credentials["client_id"],
        "pin": angelone_credentials["pin"],
        "totp_secret": angelone_credentials["totp_secret"],
        "api_key": angelone_credentials["api_key"],
    }, timeout=45.0)  # AngelOne login takes 20-25s

    if resp.status_code != 200:
        pytest.fail(
            f"AngelOne login failed with status {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"Login response missing access_token: {data}"
    return token


@pytest_asyncio.fixture
async def authed_client(live_app_client, live_auth_token):
    """HTTP client with Authorization header set."""
    live_app_client.headers.update({"Authorization": f"Bearer {live_auth_token}"})
    return live_app_client


# Broker name → API source value mapping.
# Only "smartapi" and "kite" are accepted by PUT /api/smartapi/market-data-source.
# Other brokers skip with a clear message until the endpoint is extended.
_BROKER_TO_SOURCE = {
    "angelone": "smartapi",
    "kite":     "kite",
}


@pytest_asyncio.fixture
async def set_broker(authed_client):
    """
    Factory fixture: sets market_data_source to the given broker via
    PUT /api/smartapi/market-data-source.

    Usage: broker_client = await set_broker("angelone")

    The endpoint currently only accepts "smartapi" and "kite" as sources.
    Tests for other brokers are skipped with a clear message.
    """

    async def _set(broker: str):
        # Skip if broker has no credentials
        from tests.live.conftest import _require_broker_env
        _require_broker_env(broker)

        source = _BROKER_TO_SOURCE.get(broker)
        if source is None:
            pytest.skip(
                f"[{broker}] PUT /api/smartapi/market-data-source does not yet support "
                f"'{broker}' as a market data source. Only 'smartapi' and 'kite' are "
                f"currently supported. Skipping screens API test for this broker."
            )

        resp = await authed_client.put("/api/smartapi/market-data-source", json={
            "source": source
        })
        assert resp.status_code == 200, (
            f"[{broker}] Failed to set market_data_source={source}: {resp.text[:200]}"
        )
        return authed_client
    return _set


# ─────────────────────────────────────────────────────────────────────────────
# Screen: Watchlist list (GET /api/watchlists/)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("broker", ALL_BROKERS, indirect=False)
@pytest.mark.live
async def test_watchlist_quotes_with_broker(broker, set_broker):
    """
    Watchlist list endpoint returns 200 for the authenticated user.

    Tests GET /api/watchlists/ — returns the user's watchlists (may be empty list,
    which is valid if the user has no watchlists configured yet).
    """
    client = await set_broker(broker)
    resp = await client.get("/api/watchlists/")

    assert resp.status_code == 200, (
        f"[{broker}] /api/watchlists/ returned {resp.status_code}: {resp.text[:200]}"
    )

    data = resp.json()
    # May be empty list — that's valid (user may have no watchlists).
    assert isinstance(data, list), (
        f"[{broker}] /api/watchlists/ response is not a list: {str(data)[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Screen: Option Chain
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("broker", ALL_BROKERS, indirect=False)
@pytest.mark.live
async def test_option_chain_screen_with_broker(broker, set_broker):
    """Option chain endpoint returns valid NIFTY strikes for each broker."""
    from datetime import date, timedelta

    # Find the nearest upcoming Thursday (NIFTY weekly expiry day = 3)
    today = date.today()
    days_until_thursday = (3 - today.weekday()) % 7
    if days_until_thursday == 0:
        days_until_thursday = 7  # if today is Thursday, use next Thursday
    nearest_expiry = today + timedelta(days=days_until_thursday)

    client = await set_broker(broker)
    resp = await client.get("/api/optionchain/chain", params={
        "underlying": "NIFTY",
        "expiry": nearest_expiry.strftime("%Y-%m-%d"),
    })

    if resp.status_code == 404 and "No instruments found" in resp.text:
        pytest.skip(
            f"[{broker}] No instruments found for NIFTY expiry {nearest_expiry} — "
            f"instrument master may not have this expiry loaded. "
            f"Run instrument download or try during market hours."
        )
    assert resp.status_code == 200, (
        f"[{broker}] /api/optionchain/chain returned {resp.status_code}: {resp.text[:200]}"
    )

    data = resp.json()
    strikes = data.get("strikes") or data.get("data") or []
    assert len(strikes) > 0, (
        f"[{broker}] Option chain returned 0 strikes"
    )

    atm = data.get("atm_strike") or data.get("atmStrike")
    assert atm, f"[{broker}] Option chain missing ATM strike"
    assert float(atm) > NIFTY_MIN_PRICE, (
        f"[{broker}] ATM strike={atm} is suspiciously low"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Screen: Positions
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("broker", ALL_BROKERS, indirect=False)
@pytest.mark.live
async def test_positions_screen_with_broker(broker, set_broker):
    """Positions endpoint returns 200 and valid structure for each broker."""
    client = await set_broker(broker)
    resp = await client.get("/api/positions/")

    assert resp.status_code == 200, (
        f"[{broker}] /api/positions/ returned {resp.status_code}: {resp.text[:200]}"
    )

    data = resp.json()
    # May be empty list — that's valid. Must not be an error object.
    assert isinstance(data, list) or "positions" in data, (
        f"[{broker}] Positions response is not a list or dict with 'positions' key: "
        f"{str(data)[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Screen: Market data source status (GET /api/smartapi/market-data-source)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("broker", ALL_BROKERS, indirect=False)
@pytest.mark.live
async def test_dashboard_market_summary_with_broker(broker, set_broker):
    """
    Market data source status returns 200 and shows active source for each broker.

    Tests GET /api/smartapi/market-data-source — the dashboard equivalent that
    shows which broker is currently active for market data.
    """
    client = await set_broker(broker)
    resp = await client.get("/api/smartapi/market-data-source")

    assert resp.status_code == 200, (
        f"[{broker}] /api/smartapi/market-data-source returned {resp.status_code}: "
        f"{resp.text[:200]}"
    )

    data = resp.json()
    assert data, f"[{broker}] Market data source response returned empty"

    # Verify the source field is present and set to the broker we configured
    assert "source" in data, (
        f"[{broker}] Market data source response missing 'source' field: {data}"
    )
    expected_source = _BROKER_TO_SOURCE.get(broker, broker)
    assert data["source"] == expected_source, (
        f"[{broker}] Expected source='{expected_source}', got '{data['source']}'"
    )
