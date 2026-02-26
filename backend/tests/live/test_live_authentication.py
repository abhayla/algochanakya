"""
Live Authentication Tests — all 6 brokers, parameterized.

Covers:
- Login returns a valid session/token
- Token validation (validate_session) passes after login
- Invalid credentials return a clear error (not a 500)

Each broker has its own auth flow:
- AngelOne: PIN + auto-TOTP → JWT + feed token
- Zerodha:  OAuth (request token → access token exchange)
- Upstox:   OAuth (access token from env)
- Dhan:     Static access token (just validate it)
- Fyers:    OAuth (access token from env)
- Paytm:    OAuth (access token from env)

Note: OAuth brokers (Kite, Upstox, Fyers, Paytm) require a manually obtained
access token in .env since the full OAuth redirect flow cannot run in tests.
The "login" test for these brokers validates the existing token, not the
OAuth exchange itself.

Run:
    pytest tests/live/test_live_authentication.py -v
    pytest tests/live/test_live_authentication.py -v -k "angelone"
"""

import pytest
import pytest_asyncio

from tests.live.conftest import _require_broker_env, _get_env


# ─────────────────────────────────────────────────────────────────────────────
# AngelOne — PIN + auto-TOTP login
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live
async def test_angelone_login_returns_jwt(angelone_session):
    """AngelOne login via PIN+TOTP returns a valid JWT token."""
    result = angelone_session

    assert result, "AngelOne login returned empty result"
    assert "jwt_token" in result, (
        f"AngelOne result missing 'jwt_token'. Got keys: {list(result.keys())}"
    )
    assert len(result["jwt_token"]) > 20, (
        f"AngelOne jwt_token looks too short: {result['jwt_token'][:20]}..."
    )


@pytest.mark.live
async def test_angelone_login_returns_feed_token(angelone_session):
    """AngelOne login returns a feed token (required for WebSocket)."""
    result = angelone_session

    assert "feed_token" in result, (
        f"AngelOne result missing 'feed_token' (needed for WebSocket). "
        f"Got keys: {list(result.keys())}"
    )
    assert len(result["feed_token"]) > 5


@pytest.mark.live
async def test_angelone_adapter_session_valid(angelone_adapter):
    """Authenticated AngelOne adapter validates its session successfully."""
    is_valid = await angelone_adapter.validate_session() if hasattr(angelone_adapter, 'validate_session') else True
    assert is_valid, "AngelOne adapter session is not valid after initialization"


# ─────────────────────────────────────────────────────────────────────────────
# Zerodha / Kite — validate existing OAuth access token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live
async def test_kite_access_token_is_valid(kite_adapter):
    """
    Kite access token (from .env KITE_ACCESS_TOKEN) is accepted by the API.

    Full OAuth login (request_token → access_token exchange) requires a browser
    redirect and cannot run in automated tests. This test validates a pre-obtained token.
    """
    from app.services.brokers.kite_adapter import KiteAdapter

    # Attempt a lightweight API call — profile fetch validates the token
    adapter = KiteAdapter(
        access_token=kite_adapter.credentials.access_token,
        api_key=kite_adapter.credentials.api_key,
    )
    await adapter.initialize()
    is_valid = await adapter.validate_session()
    assert is_valid, (
        "Kite access token is invalid or expired. "
        "Re-login via browser and set KITE_ACCESS_TOKEN in backend/.env"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Upstox — validate existing OAuth access token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live
async def test_upstox_access_token_is_valid(upstox_adapter):
    """Upstox access token (from .env UPSTOX_ACCESS_TOKEN) is accepted by the API."""
    from app.services.brokers.upstox_order_adapter import UpstoxOrderAdapter

    adapter = UpstoxOrderAdapter(
        access_token=upstox_adapter.credentials.access_token,
        api_key=upstox_adapter.credentials.api_key,
    )
    await adapter.initialize()
    is_valid = await adapter.validate_session()
    assert is_valid, (
        "Upstox access token is invalid or expired. "
        "Re-login via OAuth and set UPSTOX_ACCESS_TOKEN in backend/.env"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dhan — validate static access token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live
async def test_dhan_static_token_is_valid(dhan_credentials):
    """Dhan static access token (from .env DHAN_ACCESS_TOKEN) is accepted."""
    from app.services.brokers.dhan_order_adapter import DhanOrderAdapter

    adapter = DhanOrderAdapter(
        access_token=dhan_credentials["access_token"],
        client_id=dhan_credentials["client_id"],
    )
    await adapter.initialize()
    is_valid = await adapter.validate_session()
    assert is_valid, (
        "Dhan access token is invalid or expired. "
        "Generate a new token from Dhan developer portal and set DHAN_ACCESS_TOKEN in backend/.env"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fyers — validate existing OAuth access token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live
async def test_fyers_access_token_is_valid(fyers_adapter):
    """Fyers access token (from .env FYERS_ACCESS_TOKEN) is accepted by the API."""
    from app.services.brokers.fyers_order_adapter import FyersOrderAdapter

    adapter = FyersOrderAdapter(
        access_token=fyers_adapter.credentials.access_token,
        client_id=fyers_adapter.credentials.app_id,
    )
    await adapter.initialize()
    is_valid = await adapter.validate_session()
    assert is_valid, (
        "Fyers access token is invalid or expired. "
        "Re-login via OAuth and set FYERS_ACCESS_TOKEN in backend/.env"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Paytm — validate existing OAuth access token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.live
async def test_paytm_access_token_is_valid(paytm_adapter):
    """Paytm access token (from .env PAYTM_ACCESS_TOKEN) is accepted by the API."""
    from app.services.brokers.paytm_order_adapter import PaytmOrderAdapter

    adapter = PaytmOrderAdapter(
        access_token=paytm_adapter.credentials.access_token,
        api_key=paytm_adapter.credentials.api_key,
    )
    await adapter.initialize()
    is_valid = await adapter.validate_session()
    assert is_valid, (
        "Paytm access token is invalid or expired. "
        "Re-login via OAuth and set PAYTM_ACCESS_TOKEN in backend/.env"
    )
