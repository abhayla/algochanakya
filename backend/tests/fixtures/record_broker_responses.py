"""
Record real broker API responses for use as test fixtures.

Authenticates with live brokers and saves raw API responses as JSON files.
These recordings replace hand-crafted mock responses in unit tests,
ensuring tests validate against real API shapes.

Usage:
    cd backend
    source venv/Scripts/activate
    python -m tests.fixtures.record_broker_responses --broker angelone
    python -m tests.fixtures.record_broker_responses --broker upstox
    python -m tests.fixtures.record_broker_responses --broker all

Responses saved to: tests/fixtures/recorded/{broker}/

Re-record when:
    - Broker API version changes
    - New test scenarios need real response shapes
    - Monthly refresh (tokens/formats may drift)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "recorded"


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and datetime."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return {"__decimal__": str(obj)}
        if isinstance(obj, (datetime, date)):
            return {"__datetime__": obj.isoformat()}
        return super().default(obj)


def save_response(broker: str, method: str, response, metadata: dict | None = None):
    """Save a broker API response as a JSON fixture."""
    broker_dir = FIXTURES_DIR / broker
    broker_dir.mkdir(parents=True, exist_ok=True)

    fixture = {
        "broker": broker,
        "method": method,
        "recorded_at": datetime.now().isoformat(),
        "market_open": _is_market_open(),
        "metadata": metadata or {},
        "response": _serialize(response),
    }

    filepath = broker_dir / f"{method}.json"
    with open(filepath, "w") as f:
        json.dump(fixture, f, indent=2, cls=DecimalEncoder)

    logger.info(f"  Saved {filepath.relative_to(FIXTURES_DIR)}")


def _serialize(obj):
    """Convert broker response objects to serializable dicts."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, Decimal):
        return {"__decimal__": str(obj)}
    if isinstance(obj, (datetime, date)):
        return {"__datetime__": obj.isoformat()}
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        # Pydantic model or dataclass
        d = {}
        for k, v in obj.__dict__.items():
            if not k.startswith("_"):
                d[k] = _serialize(v)
        # Also try model_dump for pydantic v2
        if hasattr(obj, "model_dump"):
            try:
                d = _serialize(obj.model_dump())
            except Exception:
                pass
        d["__type__"] = type(obj).__name__
        return d
    return obj


def _is_market_open() -> bool:
    """Check if Indian market is currently open (9:15-15:30 IST, Mon-Fri)."""
    from datetime import timezone, timedelta as td

    ist = timezone(td(hours=5, minutes=30))
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close


# ─────────────────────────────────────────────────────────────────────
# AngelOne (SmartAPI) Recorder
# ─────────────────────────────────────────────────────────────────────

async def record_angelone():
    """Record all available AngelOne API responses."""
    logger.info("=" * 60)
    logger.info("Recording AngelOne (SmartAPI) responses")
    logger.info("=" * 60)

    # Check credentials
    required = ["ANGEL_CLIENT_ID", "ANGEL_PIN", "ANGEL_TOTP_SECRET", "ANGEL_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error(f"Missing .env keys: {missing}")
        return

    # Authenticate
    logger.info("Authenticating with AngelOne...")
    from app.services.legacy.smartapi_auth import SmartAPIAuth

    auth = SmartAPIAuth(api_key=os.environ["ANGEL_API_KEY"])
    session = auth.authenticate(
        client_id=os.environ["ANGEL_CLIENT_ID"],
        pin=os.environ["ANGEL_PIN"],
        totp_secret=os.environ["ANGEL_TOTP_SECRET"],
    )
    if not session or not session.get("jwt_token"):
        logger.error("AngelOne authentication failed")
        return

    jwt_token = session["jwt_token"]
    feed_token = session.get("feed_token", "")
    logger.info(f"  Authenticated. JWT: {jwt_token[:20]}...")

    save_response("angelone", "authenticate", session, {
        "client_id": os.environ["ANGEL_CLIENT_ID"],
        "api_key_prefix": os.environ["ANGEL_API_KEY"][:8] + "...",
    })

    # Create market data adapter
    from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import SmartAPIMarketDataCredentials

    creds = SmartAPIMarketDataCredentials(
        broker_type="smartapi",
        user_id=uuid4(),
        client_id=os.environ["ANGEL_CLIENT_ID"],
        jwt_token=jwt_token,
        feed_token=feed_token,
    )
    adapter = SmartAPIMarketDataAdapter(creds, db=None)

    # Record each method
    symbols = ["NIFTY 50", "NIFTY BANK"]

    # get_quote
    logger.info("Recording get_quote...")
    try:
        result = await adapter.get_quote(symbols)
        save_response("angelone", "get_quote", result, {"symbols": symbols})
    except Exception as e:
        logger.warning(f"  get_quote failed: {e}")
        save_response("angelone", "get_quote__error", {"error": str(e), "type": type(e).__name__})

    # get_ltp
    logger.info("Recording get_ltp...")
    try:
        result = await adapter.get_ltp(symbols)
        save_response("angelone", "get_ltp", result, {"symbols": symbols})
    except Exception as e:
        logger.warning(f"  get_ltp failed: {e}")
        save_response("angelone", "get_ltp__error", {"error": str(e), "type": type(e).__name__})

    # get_historical
    logger.info("Recording get_historical...")
    hist_api_key = os.environ.get("ANGEL_HIST_API_KEY", os.environ["ANGEL_API_KEY"])
    try:
        # Historical may need a different adapter instance with hist key
        result = await adapter.get_historical(
            "NIFTY 50",
            from_date=date.today() - timedelta(days=5),
            to_date=date.today(),
            interval="day",
        )
        save_response("angelone", "get_historical", result, {
            "symbol": "NIFTY 50",
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
            "to_date": date.today().isoformat(),
            "interval": "day",
        })
    except Exception as e:
        logger.warning(f"  get_historical failed: {e}")
        save_response("angelone", "get_historical__error", {"error": str(e), "type": type(e).__name__})

    # Create order adapter for profile/margins/positions/orders
    logger.info("Recording order adapter methods...")
    try:
        from app.services.brokers.factory import get_broker_adapter
        from app.services.brokers.base import BrokerType

        trade_api_key = os.environ.get("ANGEL_TRADE_API_KEY", os.environ["ANGEL_API_KEY"])

        # If trade key differs, we need a separate session
        if trade_api_key != os.environ["ANGEL_API_KEY"]:
            logger.info("  Trade API key differs — authenticating with trade key...")
            import time
            time.sleep(65)  # AngelOne rate limit: 1 login/minute
            trade_auth = SmartAPIAuth(api_key=trade_api_key)
            trade_session = trade_auth.authenticate(
                client_id=os.environ["ANGEL_CLIENT_ID"],
                pin=os.environ["ANGEL_PIN"],
                totp_secret=os.environ["ANGEL_TOTP_SECRET"],
            )
            trade_jwt = trade_session["jwt_token"] if trade_session else jwt_token
        else:
            trade_jwt = jwt_token

        order_adapter = await get_broker_adapter(
            BrokerType.ANGEL,
            access_token=trade_jwt,
            api_key=trade_api_key,
            client_id=os.environ["ANGEL_CLIENT_ID"],
        )
        if hasattr(order_adapter, 'initialize'):
            init_result = order_adapter.initialize()
            if asyncio.iscoroutine(init_result):
                await init_result

        # get_profile
        logger.info("Recording get_profile...")
        try:
            profile = await order_adapter.get_profile()
            save_response("angelone", "get_profile", profile)
        except Exception as e:
            logger.warning(f"  get_profile failed: {e}")
            save_response("angelone", "get_profile__error", {"error": str(e), "type": type(e).__name__})

        # get_margins
        logger.info("Recording get_margins...")
        try:
            margins = await order_adapter.get_margins()
            save_response("angelone", "get_margins", margins)
        except Exception as e:
            logger.warning(f"  get_margins failed: {e}")
            save_response("angelone", "get_margins__error", {"error": str(e), "type": type(e).__name__})

        # get_positions
        logger.info("Recording get_positions...")
        try:
            positions = await order_adapter.get_positions()
            save_response("angelone", "get_positions", positions)
        except Exception as e:
            logger.warning(f"  get_positions failed: {e}")
            save_response("angelone", "get_positions__error", {"error": str(e), "type": type(e).__name__})

        # get_orders
        logger.info("Recording get_orders...")
        try:
            orders = await order_adapter.get_orders()
            save_response("angelone", "get_orders", orders)
        except Exception as e:
            logger.warning(f"  get_orders failed: {e}")
            save_response("angelone", "get_orders__error", {"error": str(e), "type": type(e).__name__})

    except Exception as e:
        logger.warning(f"  Order adapter setup failed: {e}")
        save_response("angelone", "order_adapter__error", {"error": str(e), "type": type(e).__name__})

    logger.info("AngelOne recording complete.")


# ─────────────────────────────────────────────────────────────────────
# Upstox Recorder
# ─────────────────────────────────────────────────────────────────────

async def record_upstox():
    """Record all available Upstox API responses."""
    logger.info("=" * 60)
    logger.info("Recording Upstox responses")
    logger.info("=" * 60)

    required = ["UPSTOX_API_KEY", "UPSTOX_API_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error(f"Missing .env keys: {missing}")
        return

    access_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    if not access_token:
        logger.info("No UPSTOX_ACCESS_TOKEN — attempting auto-login...")
        try:
            from app.services.legacy.upstox_auth import UpstoxAuth, save_token_to_env
            auth = UpstoxAuth()
            access_token = auth.authenticate()
            save_token_to_env(access_token)
            logger.info("  Auto-login successful")
        except Exception as e:
            logger.error(f"  Auto-login failed: {e}")
            return

    # Create market data adapter
    from app.services.brokers.market_data.upstox_adapter import UpstoxMarketDataAdapter
    from app.services.brokers.market_data.market_data_base import UpstoxMarketDataCredentials

    # Need a real DB session for token manager
    from app.database import AsyncSessionLocal
    db = AsyncSessionLocal()

    try:
        creds = UpstoxMarketDataCredentials(
            broker_type="upstox",
            user_id=uuid4(),
            api_key=os.environ["UPSTOX_API_KEY"],
            access_token=access_token,
        )
        adapter = UpstoxMarketDataAdapter(creds, db=db)

        symbols = ["NIFTY 50", "NIFTY BANK"]

        # get_quote
        logger.info("Recording get_quote...")
        try:
            result = await adapter.get_quote(symbols)
            save_response("upstox", "get_quote", result, {"symbols": symbols})
        except Exception as e:
            logger.warning(f"  get_quote failed: {e}")
            save_response("upstox", "get_quote__error", {"error": str(e), "type": type(e).__name__})

        # get_ltp
        logger.info("Recording get_ltp...")
        try:
            result = await adapter.get_ltp(symbols)
            save_response("upstox", "get_ltp", result, {"symbols": symbols})
        except Exception as e:
            logger.warning(f"  get_ltp failed: {e}")
            save_response("upstox", "get_ltp__error", {"error": str(e), "type": type(e).__name__})

        # get_historical
        logger.info("Recording get_historical...")
        try:
            result = await adapter.get_historical(
                "NIFTY 50",
                from_date=date.today() - timedelta(days=5),
                to_date=date.today(),
                interval="day",
            )
            save_response("upstox", "get_historical", result, {
                "symbol": "NIFTY 50",
                "from_date": (date.today() - timedelta(days=5)).isoformat(),
                "to_date": date.today().isoformat(),
                "interval": "day",
            })
        except Exception as e:
            logger.warning(f"  get_historical failed: {e}")
            save_response("upstox", "get_historical__error", {"error": str(e), "type": type(e).__name__})

        # Order adapter for profile/margins/positions/orders
        logger.info("Recording order adapter methods...")
        try:
            from app.services.brokers.factory import get_broker_adapter
            from app.services.brokers.base import BrokerType

            order_adapter = await get_broker_adapter(
                BrokerType.UPSTOX,
                access_token=access_token,
                api_key=os.environ["UPSTOX_API_KEY"],
            )
            if hasattr(order_adapter, 'initialize'):
                init_result = order_adapter.initialize()
                if asyncio.iscoroutine(init_result):
                    await init_result

            # get_profile
            logger.info("Recording get_profile...")
            try:
                profile = await order_adapter.get_profile()
                save_response("upstox", "get_profile", profile)
            except Exception as e:
                logger.warning(f"  get_profile failed: {e}")
                save_response("upstox", "get_profile__error", {"error": str(e), "type": type(e).__name__})

            # get_margins
            logger.info("Recording get_margins...")
            try:
                margins = await order_adapter.get_margins()
                save_response("upstox", "get_margins", margins)
            except Exception as e:
                logger.warning(f"  get_margins failed: {e}")
                save_response("upstox", "get_margins__error", {"error": str(e), "type": type(e).__name__})

            # get_positions
            logger.info("Recording get_positions...")
            try:
                positions = await order_adapter.get_positions()
                save_response("upstox", "get_positions", positions)
            except Exception as e:
                logger.warning(f"  get_positions failed: {e}")
                save_response("upstox", "get_positions__error", {"error": str(e), "type": type(e).__name__})

            # get_orders
            logger.info("Recording get_orders...")
            try:
                orders = await order_adapter.get_orders()
                save_response("upstox", "get_orders", orders)
            except Exception as e:
                logger.warning(f"  get_orders failed: {e}")
                save_response("upstox", "get_orders__error", {"error": str(e), "type": type(e).__name__})

        except Exception as e:
            logger.warning(f"  Order adapter setup failed: {e}")
            save_response("upstox", "order_adapter__error", {"error": str(e), "type": type(e).__name__})

    finally:
        try:
            await db.close()
        except Exception:
            pass

    logger.info("Upstox recording complete.")


# ─────────────────────────────────────────────────────────────────────
# Fixture Loader (for use in tests)
# ─────────────────────────────────────────────────────────────────────

def load_recorded_response(broker: str, method: str) -> dict:
    """Load a recorded fixture for use in tests.

    Usage in tests:
        from tests.fixtures.record_broker_responses import load_recorded_response
        fixture = load_recorded_response("angelone", "get_quote")
        # fixture["response"] contains the real API response shape
    """
    filepath = FIXTURES_DIR / broker / f"{method}.json"
    if not filepath.exists():
        raise FileNotFoundError(
            f"No recorded fixture: {filepath}. "
            f"Run: python -m tests.fixtures.record_broker_responses --broker {broker}"
        )
    with open(filepath) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Record real broker API responses")
    parser.add_argument(
        "--broker",
        choices=["angelone", "upstox", "all"],
        default="all",
        help="Which broker to record (default: all)",
    )
    args = parser.parse_args()

    if args.broker in ("angelone", "all"):
        await record_angelone()
    if args.broker in ("upstox", "all"):
        await record_upstox()

    # Summary
    print("\n" + "=" * 60)
    print("RECORDING SUMMARY")
    print("=" * 60)
    for broker_dir in sorted(FIXTURES_DIR.iterdir()):
        if broker_dir.is_dir():
            files = list(broker_dir.glob("*.json"))
            errors = [f for f in files if "__error" in f.name]
            successes = [f for f in files if "__error" not in f.name]
            print(f"\n{broker_dir.name}:")
            for f in successes:
                print(f"  OK {f.stem}")
            for f in errors:
                print(f"  FAIL {f.stem}")
            print(f"  Total: {len(successes)} recorded, {len(errors)} errors")


if __name__ == "__main__":
    asyncio.run(main())
