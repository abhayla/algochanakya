"""
Record RAW HTTP responses from broker APIs.

Unlike record_broker_responses.py (which records adapter output),
this captures the exact JSON that _make_request() returns — the
shape that unit tests mock with patch.object(adapter, "_make_request").

Usage:
    cd backend
    source venv/Scripts/activate
    PYTHONPATH=. python -m tests.fixtures.record_raw_responses --broker upstox
    PYTHONPATH=. python -m tests.fixtures.record_raw_responses --broker angelone

Saves to: tests/fixtures/recorded/{broker}/raw_{method}.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "recorded"


def save_raw(broker: str, name: str, data: dict):
    broker_dir = FIXTURES_DIR / broker
    broker_dir.mkdir(parents=True, exist_ok=True)
    filepath = broker_dir / f"raw_{name}.json"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"  Saved {filepath.relative_to(FIXTURES_DIR)}")


# ─────────────────────────────────────────────────────────────────────
# Upstox: Direct HTTP calls to capture raw API JSON
# ─────────────────────────────────────────────────────────────────────

async def record_upstox_raw():
    """Record raw Upstox API responses via direct HTTP calls."""
    import httpx

    logger.info("=" * 60)
    logger.info("Recording RAW Upstox API responses")
    logger.info("=" * 60)

    access_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    if not access_token:
        logger.info("No UPSTOX_ACCESS_TOKEN — attempting auto-login...")
        try:
            from app.services.legacy.upstox_auth import UpstoxAuth, save_token_to_env
            auth = UpstoxAuth()
            access_token = auth.authenticate()
            save_token_to_env(access_token)
        except Exception as e:
            logger.error(f"  Auto-login failed: {e}")
            return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # v2 quote (full)
        logger.info("Recording v2 market-quote/quotes...")
        try:
            r = await client.get(
                "https://api.upstox.com/v2/market-quote/quotes",
                headers=headers,
                params={"instrument_key": "NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank"},
            )
            save_raw("upstox", "v2_quote", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # v3 LTP
        logger.info("Recording v3 market-quote/ltp...")
        try:
            r = await client.get(
                "https://api.upstox.com/v3/market-quote/ltp",
                headers=headers,
                params={"instrument_key": "NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank"},
            )
            save_raw("upstox", "v3_ltp", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # v2 LTP (fallback)
        logger.info("Recording v2 market-quote/ltp...")
        try:
            r = await client.get(
                "https://api.upstox.com/v2/market-quote/ltp",
                headers=headers,
                params={"instrument_key": "NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank"},
            )
            save_raw("upstox", "v2_ltp", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Historical candle (5 days of NIFTY)
        logger.info("Recording v2 historical-candle...")
        to_date = date.today().isoformat()
        from_date = (date.today() - timedelta(days=5)).isoformat()
        try:
            r = await client.get(
                f"https://api.upstox.com/v2/historical-candle/NSE_INDEX%7CNifty%2050/day/{to_date}/{from_date}",
                headers=headers,
            )
            save_raw("upstox", "v2_historical", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Profile
        logger.info("Recording v2 user/profile...")
        try:
            r = await client.get("https://api.upstox.com/v2/user/profile", headers=headers)
            save_raw("upstox", "v2_profile", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Funds/margin
        logger.info("Recording v2 user/get-funds-and-margin...")
        try:
            r = await client.get("https://api.upstox.com/v2/user/get-funds-and-margin", headers=headers)
            save_raw("upstox", "v2_margins", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Positions
        logger.info("Recording v2 portfolio/short-term-positions...")
        try:
            r = await client.get("https://api.upstox.com/v2/portfolio/short-term-positions", headers=headers)
            save_raw("upstox", "v2_positions", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Orders
        logger.info("Recording v2 order/retrieve-all...")
        try:
            r = await client.get("https://api.upstox.com/v2/order/retrieve-all", headers=headers)
            save_raw("upstox", "v2_orders", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Option chain
        logger.info("Recording v2 option/chain...")
        try:
            r = await client.get(
                "https://api.upstox.com/v2/option/chain",
                headers=headers,
                params={"instrument_key": "NSE_INDEX|Nifty 50", "expiry_date": "2026-04-17"},
            )
            save_raw("upstox", "v2_option_chain", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

    logger.info("Upstox raw recording complete.")


# ─────────────────────────────────────────────────────────────────────
# AngelOne: Direct HTTP calls to capture raw SmartAPI JSON
# ─────────────────────────────────────────────────────────────────────

async def record_angelone_raw():
    """Record raw AngelOne SmartAPI responses."""
    logger.info("=" * 60)
    logger.info("Recording RAW AngelOne (SmartAPI) API responses")
    logger.info("=" * 60)

    required = ["ANGEL_CLIENT_ID", "ANGEL_PIN", "ANGEL_TOTP_SECRET", "ANGEL_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error(f"Missing .env keys: {missing}")
        return

    # Authenticate
    from app.services.legacy.smartapi_auth import SmartAPIAuth
    auth = SmartAPIAuth(api_key=os.environ["ANGEL_API_KEY"])
    session = auth.authenticate(
        client_id=os.environ["ANGEL_CLIENT_ID"],
        pin=os.environ["ANGEL_PIN"],
        totp_secret=os.environ["ANGEL_TOTP_SECRET"],
    )
    if not session or not session.get("jwt_token"):
        logger.error("Authentication failed")
        return

    jwt_token = session["jwt_token"]
    # Strip "Bearer " prefix if present
    if jwt_token.startswith("Bearer "):
        jwt_token = jwt_token[7:]

    save_raw("angelone", "authenticate", {
        "jwt_token_prefix": jwt_token[:20] + "...",
        "feed_token": session.get("feed_token", ""),
        "refresh_token": session.get("refresh_token", "")[:20] + "..." if session.get("refresh_token") else "",
        "response_keys": list(session.keys()),
    })

    import httpx
    api_base = "https://apiconnect.angelone.in"
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
        "X-PrivateKey": os.environ["ANGEL_API_KEY"],
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "0.0.0.0",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Market data quote (FULL mode)
        logger.info("Recording marketData (FULL)...")
        try:
            r = await client.post(
                f"{api_base}/rest/secure/angelbroking/market/v1/quote/",
                headers=headers,
                json={
                    "mode": "FULL",
                    "exchangeTokens": {"NSE": ["99926000", "99926009"]},
                },
            )
            save_raw("angelone", "market_quote_full", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # LTP mode
        logger.info("Recording marketData (LTP)...")
        try:
            r = await client.post(
                f"{api_base}/rest/secure/angelbroking/market/v1/quote/",
                headers=headers,
                json={
                    "mode": "LTP",
                    "exchangeTokens": {"NSE": ["99926000", "99926009"]},
                },
            )
            save_raw("angelone", "market_quote_ltp", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

        # Historical candles
        logger.info("Recording historical candles...")
        try:
            r = await client.post(
                f"{api_base}/rest/secure/angelbroking/historical/v1/getCandleData",
                headers=headers,
                json={
                    "exchange": "NSE",
                    "symboltoken": "99926000",
                    "interval": "ONE_DAY",
                    "fromdate": f"{(date.today() - timedelta(days=5)).isoformat()} 09:15",
                    "todate": f"{date.today().isoformat()} 15:30",
                },
            )
            save_raw("angelone", "historical_candles", r.json())
        except Exception as e:
            logger.warning(f"  Failed: {e}")

    logger.info("AngelOne raw recording complete.")


async def main():
    parser = argparse.ArgumentParser(description="Record raw broker API HTTP responses")
    parser.add_argument("--broker", choices=["angelone", "upstox", "all"], default="all")
    args = parser.parse_args()

    if args.broker in ("angelone", "all"):
        await record_angelone_raw()
    if args.broker in ("upstox", "all"):
        await record_upstox_raw()

    # Summary
    print("\n" + "=" * 60)
    print("RAW RECORDING SUMMARY")
    print("=" * 60)
    for broker_dir in sorted(FIXTURES_DIR.iterdir()):
        if broker_dir.is_dir():
            raw_files = sorted(broker_dir.glob("raw_*.json"))
            if raw_files:
                print(f"\n{broker_dir.name}:")
                for f in raw_files:
                    size = f.stat().st_size
                    print(f"  {f.name} ({size:,} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
