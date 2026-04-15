"""
Record live WebSocket tick samples from broker APIs.

Captures a few seconds of real tick data for use in tests.
Must be run during market hours (9:15 AM - 3:30 PM IST).

Usage:
    cd backend
    source venv/Scripts/activate
    PYTHONPATH=. python -m tests.fixtures.record_websocket_ticks --broker smartapi
    PYTHONPATH=. python -m tests.fixtures.record_websocket_ticks --broker upstox
    PYTHONPATH=. python -m tests.fixtures.record_websocket_ticks --broker all

Saves to: tests/fixtures/recorded/{broker}/ws_ticks.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "recorded"

# NIFTY 50 token for SmartAPI
SMARTAPI_NIFTY_TOKEN = "99926000"
# NIFTY 50 for Upstox WebSocket
UPSTOX_NIFTY_KEY = "NSE_INDEX|Nifty 50"


def save_ticks(broker: str, ticks: list):
    broker_dir = FIXTURES_DIR / broker
    broker_dir.mkdir(parents=True, exist_ok=True)
    filepath = broker_dir / "ws_ticks.json"
    with open(filepath, "w") as f:
        json.dump({"ticks": ticks, "count": len(ticks)}, f, indent=2, default=str)
    logger.info(f"Saved {len(ticks)} ticks to {filepath.relative_to(FIXTURES_DIR)}")


async def record_smartapi_ticks(duration: int = 10):
    """Connect to SmartAPI WebSocket and capture ticks for `duration` seconds."""
    logger.info("=" * 60)
    logger.info("Recording SmartAPI WebSocket ticks")
    logger.info("=" * 60)

    required = ["ANGEL_CLIENT_ID", "ANGEL_PIN", "ANGEL_TOTP_SECRET", "ANGEL_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error(f"Missing .env keys: {missing}")
        return

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
    if jwt_token.startswith("Bearer "):
        jwt_token = jwt_token[7:]
    feed_token = session.get("feed_token", "")
    client_id = os.environ["ANGEL_CLIENT_ID"]

    ticks = []

    try:
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2

        sws = SmartWebSocketV2(
            auth_token=jwt_token,
            api_key=os.environ["ANGEL_API_KEY"],
            client_code=client_id,
            feed_token=feed_token,
        )

        def on_data(wsapp, message):
            logger.info(f"  Tick received: {type(message).__name__}, keys={list(message.keys()) if isinstance(message, dict) else 'N/A'}")
            ticks.append(message)

        def on_open(wsapp):
            logger.info("  WebSocket connected, subscribing to NIFTY...")
            # mode 2 = quote, exchange_type 1 = NSE
            sws.subscribe(
                correlation_id="nifty_recording",
                mode=2,
                token_list=[{"exchangeType": 1, "tokens": [SMARTAPI_NIFTY_TOKEN]}],
            )

        def on_error(wsapp, error):
            logger.warning(f"  WebSocket error: {error}")

        def on_close(wsapp):
            logger.info("  WebSocket closed")

        sws.on_data = on_data
        sws.on_open = on_open
        sws.on_error = on_error
        sws.on_close = on_close

        # Run in background thread (SmartWebSocketV2 uses threading)
        import threading
        ws_thread = threading.Thread(target=sws.connect, daemon=True)
        ws_thread.start()

        # Wait for ticks
        logger.info(f"  Collecting ticks for {duration} seconds...")
        await asyncio.sleep(duration)

        # Disconnect
        try:
            sws.close_connection()
        except Exception:
            pass

    except ImportError:
        logger.warning("SmartApi package not installed, trying raw websocket...")
    except Exception as e:
        logger.error(f"  Error: {e}")

    if ticks:
        save_ticks("angelone", ticks)
    else:
        logger.warning("  No ticks captured from SmartAPI")


async def record_upstox_ticks(duration: int = 10):
    """Connect to Upstox WebSocket and capture ticks for `duration` seconds."""
    logger.info("=" * 60)
    logger.info("Recording Upstox WebSocket ticks")
    logger.info("=" * 60)

    access_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
    if not access_token:
        logger.info("No UPSTOX_ACCESS_TOKEN, attempting auto-login...")
        try:
            from app.services.legacy.upstox_auth import UpstoxAuth, save_token_to_env
            auth = UpstoxAuth()
            access_token = auth.authenticate()
            save_token_to_env(access_token)
        except Exception as e:
            logger.error(f"  Auto-login failed: {e}")
            return

    ticks = []

    try:
        import websockets
        import httpx

        # Get authorized WebSocket URL from Upstox (v3 endpoint)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                "https://api.upstox.com/v3/feed/market-data-feed/authorize",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            ws_data = r.json()
            ws_url = ws_data.get("data", {}).get("authorizedRedirectUri", "")

        if not ws_url:
            logger.error(f"  Failed to get WebSocket URL: {ws_data}")
            return

        logger.info(f"  WebSocket URL obtained, connecting...")

        # Connect and subscribe
        async with websockets.connect(ws_url) as ws:
            # Subscribe to NIFTY
            import struct

            # Upstox binary protocol subscribe
            # Method: subscribe, mode: ltpc (1), keys: [NSE_INDEX|Nifty 50]
            subscribe_msg = json.dumps({
                "guid": "recording",
                "method": "sub",
                "data": {
                    "mode": "ltpc",
                    "instrumentKeys": [UPSTOX_NIFTY_KEY],
                },
            })
            await ws.send(subscribe_msg.encode())
            logger.info(f"  Subscribed, collecting ticks for {duration} seconds...")

            # Collect ticks
            try:
                end_time = asyncio.get_event_loop().time() + duration
                while asyncio.get_event_loop().time() < end_time:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        if isinstance(msg, bytes):
                            # Upstox sends protobuf binary — try to decode
                            try:
                                from upstox_client.feeder.MarketDataFeed_pb2 import FeedResponse
                                feed = FeedResponse()
                                feed.ParseFromString(msg)
                                # Convert to dict
                                tick_data = {}
                                for key, ff in feed.feeds.items():
                                    ltpc = ff.ltpc
                                    tick_data[key] = {
                                        "ltp": ltpc.ltp,
                                        "close": ltpc.cp,
                                        "timestamp": str(ltpc.ltt),
                                    }
                                if tick_data:
                                    ticks.append(tick_data)
                                    logger.info(f"  Tick: {tick_data}")
                            except ImportError:
                                # No protobuf — save raw hex
                                ticks.append({"raw_hex": msg.hex(), "length": len(msg)})
                                logger.info(f"  Raw binary tick: {len(msg)} bytes")
                            except Exception as e:
                                ticks.append({"raw_hex": msg.hex(), "length": len(msg), "error": str(e)})
                        else:
                            # JSON text frame
                            parsed = json.loads(msg) if isinstance(msg, str) else msg
                            ticks.append(parsed)
                            logger.info(f"  JSON tick: {str(parsed)[:100]}")
                    except asyncio.TimeoutError:
                        continue
            except websockets.ConnectionClosed:
                logger.info("  WebSocket connection closed")

    except ImportError as e:
        logger.error(f"  Missing dependency: {e}")
    except Exception as e:
        logger.error(f"  Error: {e}")

    if ticks:
        save_ticks("upstox", ticks)
    else:
        logger.warning("  No ticks captured from Upstox")


async def main():
    parser = argparse.ArgumentParser(description="Record WebSocket tick samples")
    parser.add_argument("--broker", choices=["smartapi", "upstox", "all"], default="all")
    parser.add_argument("--duration", type=int, default=10, help="Seconds to collect ticks")
    args = parser.parse_args()

    if args.broker in ("smartapi", "all"):
        await record_smartapi_ticks(args.duration)
    if args.broker in ("upstox", "all"):
        await record_upstox_ticks(args.duration)


if __name__ == "__main__":
    asyncio.run(main())
