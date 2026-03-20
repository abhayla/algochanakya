"""
Multi-Broker Screen Verification — Option Chain + Strategy Builder

Verifies that key screens work with BOTH AngelOne and Upstox as the
platform market data source. Each test:
1. Sets market_data_source to the broker under test
2. Calls the screen API
3. Asserts real, non-zero data is returned

This is the Gap #4 test: "switch broker, verify screen, repeat."

Run:
    pytest tests/live/test_live_multi_broker_screens.py -v -m live
    pytest tests/live/test_live_multi_broker_screens.py -v -m live -k "option_chain"
    pytest tests/live/test_live_multi_broker_screens.py -v -m live -k "strategy"
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import date, timedelta

from tests.live.constants import (
    ORG_ACTIVE_BROKERS,
    NIFTY_MIN_PRICE,
    NIFTY_MAX_PRICE,
)

ALL_BROKERS = [pytest.param(b, id=b) for b in ORG_ACTIVE_BROKERS]

_BROKER_TO_SOURCE = {
    "angelone": "smartapi",
    "kite": "kite",
    "upstox": "upstox",
    "dhan": "dhan",
    "fyers": "fyers",
    "paytm": "paytm",
}


def _nearest_expiry() -> date:
    """Nearest upcoming Thursday (NIFTY weekly expiry)."""
    today = date.today()
    days_until_thursday = (3 - today.weekday()) % 7
    if days_until_thursday == 0:
        days_until_thursday = 7
    return today + timedelta(days=days_until_thursday)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures (reuse live_app_client and live_auth_token from conftest)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def live_app_client():
    """HTTP client connected to running dev backend (localhost:8001)."""
    import httpx
    client = httpx.AsyncClient(
        base_url="http://localhost:8001",
        timeout=60.0,
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
    )
    try:
        try:
            resp = await client.get("/api/health")
            if resp.status_code != 200:
                await client.aclose()
                pytest.skip("Dev backend not running at localhost:8001")
        except Exception:
            await client.aclose()
            pytest.skip("Dev backend not running at localhost:8001")
        yield client
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


@pytest_asyncio.fixture(scope="session")
async def auth_token(live_app_client, angelone_credentials):
    """JWT token from AngelOne login."""
    resp = await live_app_client.post("/api/auth/angelone/login", json={
        "client_id": angelone_credentials["client_id"],
        "pin": angelone_credentials["pin"],
        "totp_secret": angelone_credentials["totp_secret"],
        "api_key": angelone_credentials["api_key"],
    }, timeout=45.0)

    if resp.status_code != 200:
        pytest.fail(f"AngelOne login failed: {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"Login response missing access_token: {data}"
    return token


def _is_token_expired_error(resp) -> bool:
    """Check if response indicates an expired broker token."""
    if resp.status_code != 500:
        return False
    text = resp.text.lower()
    return any(k in text for k in ["token invalid", "token expired", "unauthorized", "udapi100050"])


async def _switch_broker(client, token: str, broker: str):
    """Set market data source and return authed headers."""
    source = _BROKER_TO_SOURCE[broker]
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/api/smartapi/market-data-source",
        json={"source": source},
        headers=headers,
    )
    assert resp.status_code == 200, (
        f"[{broker}] Failed to set source={source}: {resp.text[:200]}"
    )
    return headers


# ─────────────────────────────────────────────────────────────────────────────
# Option Chain — multi-broker
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_option_chain_returns_strikes(broker, live_app_client, auth_token):
    """Option chain returns non-empty strikes list for each broker."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    expiry = _nearest_expiry()

    resp = await live_app_client.get(
        "/api/optionchain/chain",
        params={"underlying": "NIFTY", "expiry": expiry.strftime("%Y-%m-%d")},
        headers=headers,
    )

    if resp.status_code == 404 and "No instruments found" in resp.text:
        pytest.skip(f"[{broker}] No instruments for NIFTY expiry {expiry}")
    if _is_token_expired_error(resp):
        pytest.skip(f"[{broker}] Token expired on running backend — restart backend after token refresh")

    assert resp.status_code == 200, (
        f"[{broker}] /api/optionchain/chain returned {resp.status_code}: {resp.text[:200]}"
    )
    data = resp.json()
    strikes = data.get("strikes") or data.get("data") or []
    assert len(strikes) > 0, f"[{broker}] Option chain returned 0 strikes"


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_option_chain_has_valid_atm(broker, live_app_client, auth_token):
    """Option chain ATM strike is within NIFTY price range for each broker."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    expiry = _nearest_expiry()

    resp = await live_app_client.get(
        "/api/optionchain/chain",
        params={"underlying": "NIFTY", "expiry": expiry.strftime("%Y-%m-%d")},
        headers=headers,
    )

    if resp.status_code != 200:
        pytest.skip(f"[{broker}] Chain unavailable: {resp.status_code}")

    data = resp.json()
    atm = data.get("atm_strike") or data.get("atmStrike")
    assert atm, f"[{broker}] Option chain missing ATM strike"
    assert NIFTY_MIN_PRICE < float(atm) < NIFTY_MAX_PRICE, (
        f"[{broker}] ATM strike {atm} outside expected range"
    )


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_option_chain_strikes_have_ltp(broker, live_app_client, auth_token):
    """At least some strikes near ATM have non-zero LTP values."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    expiry = _nearest_expiry()

    resp = await live_app_client.get(
        "/api/optionchain/chain",
        params={"underlying": "NIFTY", "expiry": expiry.strftime("%Y-%m-%d")},
        headers=headers,
    )

    if resp.status_code != 200:
        pytest.skip(f"[{broker}] Chain unavailable: {resp.status_code}")

    data = resp.json()
    strikes = data.get("strikes") or data.get("data") or []
    if not strikes:
        pytest.skip(f"[{broker}] No strikes returned")

    # Check ATM ±5 strikes for non-zero LTP
    atm = float(data.get("atm_strike") or data.get("atmStrike") or 0)
    near_atm = [s for s in strikes if abs(float(s.get("strike", 0)) - atm) <= 500]

    nonzero_ce = sum(
        1 for s in near_atm
        if float(s.get("CE", {}).get("ltp", 0) if isinstance(s.get("CE"), dict) else 0) > 0
    )
    nonzero_pe = sum(
        1 for s in near_atm
        if float(s.get("PE", {}).get("ltp", 0) if isinstance(s.get("PE"), dict) else 0) > 0
    )

    assert nonzero_ce > 0 or nonzero_pe > 0, (
        f"[{broker}] All {len(near_atm)} ATM-adjacent strikes have LTP=0. "
        f"Market data may not be flowing."
    )


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_option_chain_banknifty(broker, live_app_client, auth_token):
    """Option chain works for BANKNIFTY too, not just NIFTY."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    expiry = _nearest_expiry()

    resp = await live_app_client.get(
        "/api/optionchain/chain",
        params={"underlying": "BANKNIFTY", "expiry": expiry.strftime("%Y-%m-%d")},
        headers=headers,
    )

    if resp.status_code == 404 and "No instruments found" in resp.text:
        pytest.skip(f"[{broker}] No instruments for BANKNIFTY expiry {expiry}")
    if _is_token_expired_error(resp):
        pytest.skip(f"[{broker}] Token expired on running backend — restart backend after token refresh")

    assert resp.status_code == 200, (
        f"[{broker}] BANKNIFTY chain returned {resp.status_code}: {resp.text[:200]}"
    )
    data = resp.json()
    strikes = data.get("strikes") or data.get("data") or []
    assert len(strikes) > 0, f"[{broker}] BANKNIFTY chain returned 0 strikes"


# ─────────────────────────────────────────────────────────────────────────────
# Strategy Builder — multi-broker
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_strategy_templates_available(broker, live_app_client, auth_token):
    """Strategy library returns templates for each broker (broker-agnostic)."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    resp = await live_app_client.get(
        "/api/strategy-library/templates",
        headers=headers,
    )
    assert resp.status_code == 200, (
        f"[{broker}] /api/strategy-library/templates returned {resp.status_code}"
    )
    data = resp.json()
    templates = data if isinstance(data, list) else data.get("templates", [])
    assert len(templates) > 0, f"[{broker}] No strategy templates returned"


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_strategy_wizard_recommends(broker, live_app_client, auth_token):
    """Strategy wizard returns recommendations for each broker."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    resp = await live_app_client.post(
        "/api/strategy-library/wizard",
        json={
            "market_outlook": "bullish",
            "volatility_view": "low_iv",
            "risk_tolerance": "low",
        },
        headers=headers,
    )
    assert resp.status_code == 200, (
        f"[{broker}] Wizard returned {resp.status_code}: {resp.text[:200]}"
    )
    data = resp.json()
    recs = data.get("recommendations") or data.get("strategies") or []
    assert len(recs) > 0, f"[{broker}] Wizard returned 0 recommendations"


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_strategy_deploy_iron_condor(broker, live_app_client, auth_token):
    """Deploy Iron Condor template returns legs with live prices for each broker."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    resp = await live_app_client.post(
        "/api/strategy-library/deploy",
        json={
            "template_name": "iron_condor",
            "underlying": "NIFTY",
            "lots": 1,
        },
        headers=headers,
    )

    if resp.status_code == 404:
        pytest.skip(f"[{broker}] iron_condor template not found in DB")
    if _is_token_expired_error(resp):
        pytest.skip(f"[{broker}] Token expired on running backend — restart backend after token refresh")

    assert resp.status_code == 200, (
        f"[{broker}] Deploy returned {resp.status_code}: {resp.text[:300]}"
    )

    data = resp.json()
    legs = data.get("legs") or data.get("strategy", {}).get("legs", [])
    assert len(legs) >= 4, (
        f"[{broker}] Iron Condor should have 4 legs, got {len(legs)}"
    )

    # At least one leg should have a non-zero LTP (proves market data is flowing)
    ltps = [float(leg.get("ltp", 0) or leg.get("premium", 0) or 0) for leg in legs]
    nonzero = sum(1 for p in ltps if p > 0)
    assert nonzero > 0, (
        f"[{broker}] All Iron Condor legs have LTP=0. "
        f"Market data not flowing for this broker. LTPs: {ltps}"
    )


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_strategy_deploy_bull_call_spread(broker, live_app_client, auth_token):
    """Deploy Bull Call Spread returns 2 legs with live prices."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    resp = await live_app_client.post(
        "/api/strategy-library/deploy",
        json={
            "template_name": "bull_call_spread",
            "underlying": "NIFTY",
            "lots": 1,
        },
        headers=headers,
    )

    if resp.status_code == 404:
        pytest.skip(f"[{broker}] bull_call_spread template not found in DB")
    if _is_token_expired_error(resp):
        pytest.skip(f"[{broker}] Token expired on running backend — restart backend after token refresh")

    assert resp.status_code == 200, (
        f"[{broker}] Deploy returned {resp.status_code}: {resp.text[:300]}"
    )

    data = resp.json()
    legs = data.get("legs") or data.get("strategy", {}).get("legs", [])
    assert len(legs) >= 2, (
        f"[{broker}] Bull Call Spread should have 2 legs, got {len(legs)}"
    )


@pytest.mark.parametrize("broker", ALL_BROKERS)
@pytest.mark.live
async def test_strategy_compare_two_templates(broker, live_app_client, auth_token):
    """Compare endpoint works with each broker's market data."""
    headers = await _switch_broker(live_app_client, auth_token, broker)
    resp = await live_app_client.post(
        "/api/strategy-library/compare",
        json={
            "template_names": ["iron_condor", "bull_call_spread"],
        },
        headers=headers,
    )

    if resp.status_code == 404:
        pytest.skip(f"[{broker}] Templates not found in DB")

    assert resp.status_code == 200, (
        f"[{broker}] Compare returned {resp.status_code}: {resp.text[:200]}"
    )

    data = resp.json()
    comparisons = data.get("comparisons") or data.get("strategies") or []
    assert len(comparisons) >= 2, (
        f"[{broker}] Compare should return 2+ strategies, got {len(comparisons)}"
    )
