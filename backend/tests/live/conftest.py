"""
Conftest for live broker integration tests.

Responsibilities:
- Load credentials from backend/.env
- Skip a broker's tests with a clear message if credentials are missing
- Provide authenticated adapter fixtures for each broker
- Provide a parametrized `broker_credentials` fixture used by all tests
"""

import os
import pytest
import pytest_asyncio
from pathlib import Path
from dotenv import load_dotenv

from tests.live.constants import BROKER_REQUIRED_ENV_KEYS

# ─────────────────────────────────────────────────────────────────────────────
# Load backend/.env once at import time
# ─────────────────────────────────────────────────────────────────────────────
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_env(key: str) -> str | None:
    return os.environ.get(key)


def _require_broker_env(broker: str) -> dict:
    """
    Return a dict of {env_key: value} for the broker.

    Calls pytest.skip() if any required key is missing or is a placeholder.
    """
    required = BROKER_REQUIRED_ENV_KEYS[broker]
    values = {}
    missing = []
    for key in required:
        val = _get_env(key)
        if not val or val.startswith("your-"):
            missing.append(key)
        else:
            values[key] = val

    if missing:
        pytest.skip(
            f"{broker.upper()} credentials not configured in backend/.env — "
            f"missing: {', '.join(missing)}"
        )
    return values


# ─────────────────────────────────────────────────────────────────────────────
# Per-broker credential fixtures
# Each fixture returns a dict of live credentials or skips the test.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def angelone_credentials() -> dict:
    """
    Live AngelOne/SmartAPI credentials from .env.

    AngelOne uses 3 separate API keys for 3 different data domains:
    - ANGEL_API_KEY      — market data (WebSocket ticks, live quotes)
    - ANGEL_HIST_API_KEY — historical candle data (getCandleData endpoint)
    - ANGEL_TRADE_API_KEY — order execution (placeOrder, cancelOrder, etc.)

    All 3 are exposed here so individual fixtures can pick the right key.
    """
    env = _require_broker_env("angelone")
    return {
        "broker": "angelone",
        "client_id": env["ANGEL_CLIENT_ID"],
        "pin": env["ANGEL_PIN"],
        "totp_secret": env["ANGEL_TOTP_SECRET"],
        "api_key": env["ANGEL_API_KEY"],
        # Optional: dedicated keys for historical and order execution APIs.
        # If absent, tests fall back to ANGEL_API_KEY (may get AG8001 on historical/order endpoints).
        "hist_api_key": _get_env("ANGEL_HIST_API_KEY") or env["ANGEL_API_KEY"],
        "trade_api_key": _get_env("ANGEL_TRADE_API_KEY") or env["ANGEL_API_KEY"],
    }


@pytest.fixture(scope="session")
def kite_credentials() -> dict:
    """Live Zerodha/Kite credentials from .env."""
    env = _require_broker_env("kite")
    return {
        "broker": "kite",
        "api_key": env["KITE_API_KEY"],
        "api_secret": env["KITE_API_SECRET"],
        # access_token is obtained via OAuth and cannot be auto-generated here.
        # Tests requiring a live Kite session will skip if KITE_ACCESS_TOKEN is absent.
        "access_token": _get_env("KITE_ACCESS_TOKEN") or "",
    }


@pytest.fixture(scope="session")
def upstox_credentials() -> dict:
    """Live Upstox credentials from .env."""
    env = _require_broker_env("upstox")
    return {
        "broker": "upstox",
        "api_key": env["UPSTOX_API_KEY"],
        "api_secret": env["UPSTOX_API_SECRET"],
        "access_token": _get_env("UPSTOX_ACCESS_TOKEN") or "",
    }


@pytest.fixture(scope="session")
def dhan_credentials() -> dict:
    """Live Dhan credentials from .env."""
    env = _require_broker_env("dhan")
    return {
        "broker": "dhan",
        "client_id": env["DHAN_CLIENT_ID"],
        "access_token": env["DHAN_ACCESS_TOKEN"],
    }


@pytest.fixture(scope="session")
def fyers_credentials() -> dict:
    """Live Fyers credentials from .env."""
    env = _require_broker_env("fyers")
    return {
        "broker": "fyers",
        "app_id": env["FYERS_APP_ID"],
        "secret_key": env["FYERS_SECRET_KEY"],
        "access_token": _get_env("FYERS_ACCESS_TOKEN") or "",
    }


@pytest.fixture(scope="session")
def paytm_credentials() -> dict:
    """Live Paytm Money credentials from .env."""
    env = _require_broker_env("paytm")
    return {
        "broker": "paytm",
        "api_key": env["PAYTM_API_KEY"],
        "api_secret": env["PAYTM_API_SECRET"],
        "access_token": _get_env("PAYTM_ACCESS_TOKEN") or "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Shared AngelOne session — authenticate ONCE per test session.
# Both angelone_adapter and angelone_order_adapter depend on this fixture so
# that only a single login is performed (avoids rate-limit errors).
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def angelone_session(angelone_credentials) -> dict:
    """
    Authenticate once with AngelOne and cache the session for the whole run.

    Returns dict with jwt_token, feed_token, and trade_jwt_token (if trade key differs).
    All AngelOne fixtures must depend on this instead of calling auth.authenticate()
    directly, to avoid triggering AngelOne's per-minute login rate limit.

    If ANGEL_TRADE_API_KEY differs from ANGEL_API_KEY, we also authenticate with the
    trade key here (with a delay) so the order adapter can reuse the JWT without doing
    a second fresh login at fixture-setup time.
    """
    import time
    from app.services.legacy.smartapi_auth import SmartAPIAuth

    auth = SmartAPIAuth(api_key=angelone_credentials["api_key"])
    result = auth.authenticate(
        client_id=angelone_credentials["client_id"],
        pin=angelone_credentials["pin"],
        totp_secret=angelone_credentials["totp_secret"],
    )
    if not result or not result.get("jwt_token"):
        pytest.fail("AngelOne authentication failed — check credentials in .env")

    trade_api_key = angelone_credentials.get("trade_api_key", "")
    market_api_key = angelone_credentials.get("api_key", "")
    if trade_api_key and trade_api_key != market_api_key:
        # Trade key is different — authenticate separately for order execution.
        # Wait 65 seconds to avoid AngelOne's per-minute login rate limit.
        import logging
        logging.getLogger(__name__).info(
            "[AngelOne] Trade API key differs — waiting 65s before second login to avoid rate limit"
        )
        time.sleep(65)
        trade_auth = SmartAPIAuth(api_key=trade_api_key)
        trade_result = trade_auth.authenticate(
            client_id=angelone_credentials["client_id"],
            pin=angelone_credentials["pin"],
            totp_secret=angelone_credentials["totp_secret"],
        )
        if trade_result and trade_result.get("jwt_token"):
            result["trade_jwt_token"] = trade_result["jwt_token"]
            logging.getLogger(__name__).info("[AngelOne] Trade key login successful")
        else:
            logging.getLogger(__name__).warning(
                "[AngelOne] Trade key login failed — order tests will attempt fresh login "
                "in AngelOneAdapter.initialize() and may hit rate limit"
            )
    else:
        # Same key — reuse the same JWT for orders
        result["trade_jwt_token"] = result["jwt_token"]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated adapter fixtures
# Each returns a live, initialized adapter instance.
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def angelone_adapter(angelone_credentials, angelone_session):
    """
    Authenticated AngelOne SmartAPIMarketDataAdapter (session-scoped).

    Passes db=None because live tests don't need DB-backed token lookups —
    they use bare index names (e.g. "NIFTY 50") which SmartAPIMarketDataAdapter
    handles via get_index_quote() without any token resolution.
    """
    from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import SmartAPIMarketDataCredentials
    from uuid import uuid4

    creds = SmartAPIMarketDataCredentials(
        broker_type="smartapi",
        user_id=uuid4(),
        client_id=angelone_credentials["client_id"],
        jwt_token=angelone_session["jwt_token"],
        feed_token=angelone_session.get("feed_token", ""),
    )
    adapter = SmartAPIMarketDataAdapter(creds, db=None)
    yield adapter


@pytest.fixture(scope="session")
def angelone_ticker_adapter(angelone_credentials, angelone_session):
    """
    Authenticated AngelOne SmartAPITickerAdapter (session-scoped).

    This is a WebSocket (TickerAdapter) instance, NOT the REST MarketDataAdapter.
    Used by WebSocket/ticker tests only.

    The adapter requires token mappings pre-loaded so canonical Kite tokens
    (NIFTY=256265, BANKNIFTY=260105) are translated to SmartAPI tokens.
    """
    from app.services.brokers.market_data.ticker.adapters.smartapi import SmartAPITickerAdapter

    adapter = SmartAPITickerAdapter(broker_type="smartapi")

    # Pre-load well-known canonical → SmartAPI token mappings
    # Format: {canonical_kite_token: (smartapi_token_str, exchange_type_int)}
    # NSE exchange type = 1, NFO = 2
    adapter.load_token_map({
        256265: ("99926000", 1),   # NIFTY 50  (NSE)
        260105: ("99926009", 1),   # NIFTY BANK (NSE)
        257801: ("99919009", 1),   # NIFTY FIN SERVICE (NSE)
    })

    # Store credentials dict so connect() can use them
    adapter._live_credentials = {
        "jwt_token": angelone_session["jwt_token"],
        "api_key": angelone_credentials["api_key"],
        "client_id": angelone_credentials["client_id"],
        "feed_token": angelone_session.get("feed_token", ""),
    }
    yield adapter


@pytest_asyncio.fixture(scope="session")
async def kite_adapter(kite_credentials):
    """Authenticated Kite adapter (session-scoped). Skips if no access token."""
    if not kite_credentials["access_token"]:
        pytest.skip(
            "Kite access token not set — add KITE_ACCESS_TOKEN to backend/.env "
            "(obtained via OAuth login)"
        )

    from app.services.brokers.market_data.kite_adapter import KiteMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import KiteMarketDataCredentials
    from uuid import uuid4

    creds = KiteMarketDataCredentials(
        broker_type="kite",
        user_id=uuid4(),
        api_key=kite_credentials["api_key"],
        access_token=kite_credentials["access_token"],
    )
    adapter = KiteMarketDataAdapter(creds)
    yield adapter


@pytest_asyncio.fixture(scope="session")
async def upstox_adapter(upstox_credentials):
    """Authenticated Upstox adapter (session-scoped). Skips if no access token."""
    if not upstox_credentials["access_token"]:
        pytest.skip(
            "Upstox access token not set — add UPSTOX_ACCESS_TOKEN to backend/.env "
            "(obtained via OAuth login)"
        )

    from app.services.brokers.market_data.upstox_adapter import UpstoxMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import UpstoxMarketDataCredentials
    from uuid import uuid4

    creds = UpstoxMarketDataCredentials(
        broker_type="upstox",
        user_id=uuid4(),
        api_key=upstox_credentials["api_key"],
        access_token=upstox_credentials["access_token"],
    )
    adapter = UpstoxMarketDataAdapter(creds)
    yield adapter


@pytest_asyncio.fixture(scope="session")
async def dhan_adapter(dhan_credentials):
    """Authenticated Dhan adapter (session-scoped)."""
    from app.services.brokers.market_data.dhan_adapter import DhanMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import DhanMarketDataCredentials
    from uuid import uuid4

    creds = DhanMarketDataCredentials(
        broker_type="dhan",
        user_id=uuid4(),
        client_id=dhan_credentials["client_id"],
        access_token=dhan_credentials["access_token"],
    )
    adapter = DhanMarketDataAdapter(creds)
    yield adapter


@pytest_asyncio.fixture(scope="session")
async def fyers_adapter(fyers_credentials):
    """Authenticated Fyers adapter (session-scoped). Skips if no access token."""
    if not fyers_credentials["access_token"]:
        pytest.skip(
            "Fyers access token not set — add FYERS_ACCESS_TOKEN to backend/.env "
            "(obtained via OAuth login)"
        )

    from app.services.brokers.market_data.fyers_adapter import FyersMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import FyersMarketDataCredentials
    from uuid import uuid4

    creds = FyersMarketDataCredentials(
        broker_type="fyers",
        user_id=uuid4(),
        app_id=fyers_credentials["app_id"],
        access_token=fyers_credentials["access_token"],
    )
    adapter = FyersMarketDataAdapter(creds)
    yield adapter


@pytest_asyncio.fixture(scope="session")
async def paytm_adapter(paytm_credentials):
    """Authenticated Paytm adapter (session-scoped). Skips if no access token."""
    if not paytm_credentials["access_token"]:
        pytest.skip(
            "Paytm access token not set — add PAYTM_ACCESS_TOKEN to backend/.env "
            "(obtained via OAuth login)"
        )

    from app.services.brokers.market_data.paytm_adapter import PaytmMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import PaytmMarketDataCredentials
    from uuid import uuid4

    creds = PaytmMarketDataCredentials(
        broker_type="paytm",
        user_id=uuid4(),
        api_key=paytm_credentials["api_key"],
        access_token=paytm_credentials["access_token"],
    )
    adapter = PaytmMarketDataAdapter(creds)
    yield adapter


# ─────────────────────────────────────────────────────────────────────────────
# Broker → adapter mapping for parametrized tests
# ─────────────────────────────────────────────────────────────────────────────

BROKER_ADAPTER_FIXTURE_MAP = {
    "angelone": "angelone_adapter",
    "kite":     "kite_adapter",
    "upstox":   "upstox_adapter",
    "dhan":     "dhan_adapter",
    "fyers":    "fyers_adapter",
    "paytm":    "paytm_adapter",
}


# ─────────────────────────────────────────────────────────────────────────────
# Ticker (WebSocket) adapter fixtures
# These are separate from the REST market data adapters above.
# Each stores credentials in _live_credentials so tests can call
# adapter.connect(adapter._live_credentials) without importing creds.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def kite_ticker_adapter(kite_credentials):
    """
    Authenticated Kite KiteTickerAdapter (session-scoped).
    Kite tokens ARE canonical tokens — no token map pre-loading needed.
    """
    if not kite_credentials["access_token"]:
        pytest.skip("KITE_ACCESS_TOKEN not set in backend/.env")

    from app.services.brokers.market_data.ticker.adapters.kite import KiteTickerAdapter

    adapter = KiteTickerAdapter(broker_type="kite")
    adapter._live_credentials = {
        "api_key": kite_credentials["api_key"],
        "access_token": kite_credentials["access_token"],
    }
    yield adapter


@pytest.fixture(scope="session")
def upstox_ticker_adapter(upstox_credentials):
    """Authenticated Upstox UpstoxTickerAdapter (session-scoped)."""
    if not upstox_credentials["access_token"]:
        pytest.skip("UPSTOX_ACCESS_TOKEN not set in backend/.env")

    from app.services.brokers.market_data.ticker.adapters.upstox import UpstoxTickerAdapter

    adapter = UpstoxTickerAdapter(broker_type="upstox")
    adapter._live_credentials = {
        "access_token": upstox_credentials["access_token"],
    }
    yield adapter


@pytest.fixture(scope="session")
def dhan_ticker_adapter(dhan_credentials):
    """Authenticated Dhan DhanTickerAdapter (session-scoped)."""
    from app.services.brokers.market_data.ticker.adapters.dhan import DhanTickerAdapter

    adapter = DhanTickerAdapter(broker_type="dhan")
    # Dhan token map: canonical Kite token → (dhan_security_id_str, exchange_segment)
    # NSE_EQ=1, NSE_FO=2 — indices are NSE_INDEX=13
    adapter.load_token_map({
        256265: ("13",  13),   # NIFTY 50  (NSE_INDEX)
        260105: ("25",  13),   # NIFTY BANK (NSE_INDEX)
    })
    adapter._live_credentials = {
        "client_id": dhan_credentials["client_id"],
        "access_token": dhan_credentials["access_token"],
    }
    yield adapter


@pytest.fixture(scope="session")
def fyers_ticker_adapter(fyers_credentials):
    """Authenticated Fyers FyersTickerAdapter (session-scoped)."""
    if not fyers_credentials["access_token"]:
        pytest.skip("FYERS_ACCESS_TOKEN not set in backend/.env")

    from app.services.brokers.market_data.ticker.adapters.fyers import FyersTickerAdapter

    adapter = FyersTickerAdapter(broker_type="fyers")
    # Fyers symbol format: "NSE:NIFTY50-INDEX"
    adapter.load_token_map({
        256265: ("NSE:NIFTY50-INDEX",   0),
        260105: ("NSE:NIFTYBANK-INDEX", 0),
    })
    adapter._live_credentials = {
        "access_token": fyers_credentials["access_token"],
        "app_id": fyers_credentials["app_id"],
    }
    yield adapter


@pytest.fixture(scope="session")
def paytm_ticker_adapter(paytm_credentials):
    """Authenticated Paytm PaytmTickerAdapter (session-scoped)."""
    if not paytm_credentials["access_token"]:
        pytest.skip("PAYTM_ACCESS_TOKEN not set in backend/.env")

    from app.services.brokers.market_data.ticker.adapters.paytm import PaytmTickerAdapter

    adapter = PaytmTickerAdapter(broker_type="paytm")
    # Paytm uses NSE scrip codes; NIFTY=26000, BANKNIFTY=26009
    adapter.load_token_map({
        256265: ("26000", 0),
        260105: ("26009", 0),
    })
    adapter._live_credentials = {
        "access_token": paytm_credentials["access_token"],
        "api_key": paytm_credentials["api_key"],
    }
    yield adapter
