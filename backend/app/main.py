from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import select, func
import logging
import traceback

from app.config import settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.api.routes import health, auth, watchlist, instruments, websocket, options, strategy, orders, optionchain, positions, strategy_wizard, constants, user_preferences, ofo, smartapi, ticker
from app.api.routes import dhan_auth, upstox_auth, fyers_auth, paytm_auth
from app.api.routes import zerodha_credentials as zerodha_creds_router
from app.api.routes import upstox_credentials as upstox_creds_router
from app.api.routes import dhan_credentials as dhan_creds_router
from app.api.routes import settings_credentials as settings_creds_router
from app.api.v1.autopilot import router as autopilot_router
from app.api.v1.ai import router as ai_router
from app.services.ai.daily_scheduler import start_scheduler, stop_scheduler
from app.websocket.routes import router as autopilot_ws_router
from app.models import Instrument

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def refresh_instrument_master_startup():
    """Download instruments from platform broker and populate DB."""
    try:
        async with AsyncSessionLocal() as db:
            from app.services.instrument_master import InstrumentMasterService

            if not await InstrumentMasterService.should_refresh(db):
                result = await db.execute(select(func.count(Instrument.id)))
                count = result.scalar()
                print(f"[INFO] Instruments table up-to-date ({count} records)")
                return

            # Try broker-agnostic refresh
            try:
                from app.services.brokers.market_data.factory import get_platform_market_data_adapter
                adapter = await get_platform_market_data_adapter(db)
                broker_name = adapter.broker_type
                count = await InstrumentMasterService.refresh_from_adapter(
                    adapter, broker_name, db, exchanges=["NFO"]
                )
                print(f"[SUCCESS] Instruments refreshed from {broker_name}: {count}")
            except Exception as e:
                # Fallback to Kite CSV download
                print(f"[WARNING] Platform adapter failed ({e}), falling back to Kite CSV...")
                from app.services.instruments import refresh_instrument_master as kite_refresh
                await kite_refresh(db)
                print("[SUCCESS] Instruments downloaded from Kite CSV (fallback)")

    except Exception as e:
        print(f"[WARNING] Could not check/download instruments: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    print(f"[SUCCESS] {settings.APP_NAME} backend started")
    print(f"[SUCCESS] Database: Connected to PostgreSQL")
    print(f"[SUCCESS] Redis: Connected")
    print(f"[SUCCESS] AutoPilot WebSocket: /ws/autopilot")

    # Auto-download instruments if needed
    await refresh_instrument_master_startup()

    # Pre-warm SmartAPI instrument cache
    # Downloads 185k instruments (~20-30s) ONCE on startup
    # Eliminates cold-start penalty for first API request
    try:
        from app.services.legacy.smartapi_instruments import get_smartapi_instruments
        print("[INFO] Pre-warming SmartAPI instrument cache...")
        smartapi_instruments = get_smartapi_instruments()
        count = await smartapi_instruments.download_master()
        print(f"[SUCCESS] SmartAPI instruments cached: {count} instruments")
    except Exception as e:
        print(f"[WARNING] SmartAPI pre-warm failed (will retry on first request): {e}")

    # Populate broker_instrument_tokens table for SmartAPI
    # Maps canonical symbols (kite format) → SmartAPI tokens so
    # TokenManager and WebSocket ticker adapters can resolve tokens.
    # CRITICAL: if this step fails or returns 0, all option chain LTPs will be 0.
    try:
        from app.services.instrument_master import InstrumentMasterService
        async with AsyncSessionLocal() as db:
            print("[INFO] Populating SmartAPI token mappings...")
            token_count = await InstrumentMasterService.populate_broker_token_mappings(db)
            if token_count == 0:
                print("[WARNING] SmartAPI token mappings: 0 rows stored — option chain LTPs will be 0!")
                print("[WARNING] Fix: ensure NFO instruments are in DB and ANGEL_API_KEY is set.")
            else:
                print(f"[SUCCESS] SmartAPI token mappings: {token_count} rows")
    except RuntimeError as e:
        print(f"[WARNING] SmartAPI token mapping failed — option chain LTPs will be 0: {e}")
        print("[WARNING] Fix: check ANGEL_API_KEY in backend/.env and network connectivity.")
    except Exception as e:
        print(f"[WARNING] SmartAPI token mapping failed (unexpected error): {e}")

    # Refresh expired platform broker tokens (Upstox, AngelOne)
    try:
        from app.services.brokers.platform_token_refresh import refresh_platform_tokens
        results = await refresh_platform_tokens()
        for broker, status in results.items():
            if status == "refreshed":
                print(f"[SUCCESS] {broker} platform token refreshed")
            elif status == "failed":
                print(f"[WARNING] {broker} platform token refresh failed")
            elif status == "skipped":
                print(f"[INFO] {broker} platform token still valid")
    except Exception as e:
        print(f"[WARNING] Platform token refresh failed: {e}")

    # Note: Strategy Monitor requires a valid Kite session to start.
    # It will be initialized when a user with valid broker connection
    # activates a strategy. See app/services/strategy_monitor.py for details.
    # To start monitor globally with a service account:
    #
    # from kiteconnect import KiteConnect
    # from app.services.autopilot.strategy_monitor import get_strategy_monitor
    # kite = KiteConnect(api_key=settings.KITE_API_KEY)
    # kite.set_access_token(service_account_token)
    # monitor = await get_strategy_monitor(kite)
    # await monitor.start()

    # Initialize WebSocket Health Monitor for circuit breaker protection
    try:
        from app.services.ai.websocket_health_monitor import initialize_health_monitor
        health_monitor = await initialize_health_monitor()
        print("[SUCCESS] WebSocket Health Monitor: Started")
    except Exception as e:
        print(f"[WARNING] WebSocket Health Monitor failed to start: {e}")

    # Initialize Multi-Broker Ticker System (Phase 4 architecture)
    try:
        from app.services.brokers.market_data.ticker import (
            TickerPool, TickerRouter, HealthMonitor as TickerHealthMonitor,
            FailoverController, SmartAPITickerAdapter, KiteTickerAdapter,
            DhanTickerAdapter, FyersTickerAdapter,
            UpstoxTickerAdapter, PaytmTickerAdapter,
        )

        pool = TickerPool.get_instance()
        router = TickerRouter.get_instance()

        # Register available broker adapters (implemented)
        pool.register_adapter("smartapi", SmartAPITickerAdapter)
        pool.register_adapter("kite", KiteTickerAdapter)

        # Register stub adapters (will raise NotImplementedError if used)
        pool.register_adapter("dhan", DhanTickerAdapter)
        pool.register_adapter("fyers", FyersTickerAdapter)
        pool.register_adapter("upstox", UpstoxTickerAdapter)
        pool.register_adapter("paytm", PaytmTickerAdapter)

        # Create health monitor and register ALL broker adapters
        # Depends on: nothing. Must happen BEFORE pool.initialize() so pool can forward events.
        ticker_health = TickerHealthMonitor()
        ticker_health.register_adapter("smartapi")
        ticker_health.register_adapter("kite")
        ticker_health.register_adapter("dhan")
        ticker_health.register_adapter("fyers")
        ticker_health.register_adapter("upstox")
        ticker_health.register_adapter("paytm")

        # Wire pool → router dispatch + health monitor
        router.set_pool(pool)
        await pool.initialize(on_tick_callback=router.dispatch, health_monitor=ticker_health)

        # Create failover controller and wire dependencies
        failover = FailoverController(
            primary_broker="smartapi",
            secondary_broker="kite",
        )
        failover.set_dependencies(pool, router, ticker_health)

        # Store references on app state for API access and shutdown
        app.state.ticker_health_monitor = ticker_health
        app.state.failover_controller = failover

        # Start health monitoring
        await ticker_health.start()

        print("[SUCCESS] Ticker system initialized with health monitoring + failover")
    except Exception as e:
        print(f"[WARNING] Ticker system failed to initialize: {e}")
        logger.error("Ticker system init failed: %s", e, exc_info=True)

    # Start AI Daily Scheduler (cron-based: premarket 8:45, deploy 9:20, postmarket 4:00 PM)
    # Depends on: init_db (needs DB for AI configs)
    try:
        await start_scheduler()
        print("[SUCCESS] AI Daily Scheduler: Started")
    except Exception as e:
        print(f"[WARNING] AI Daily Scheduler failed to start: {e}")
        logger.error("AI Daily Scheduler init failed: %s", e, exc_info=True)

    yield

    # Shutdown
    # Stop AI Daily Scheduler
    try:
        await stop_scheduler()
    except Exception:
        pass

    from app.services.autopilot.strategy_monitor import stop_strategy_monitor
    await stop_strategy_monitor()

    # Shutdown ticker system (health monitor + failover + pool)
    try:
        ticker_health = getattr(app.state, "ticker_health_monitor", None)
        if ticker_health:
            await ticker_health.stop()
        failover = getattr(app.state, "failover_controller", None)
        if failover:
            await failover.stop()
        from app.services.brokers.market_data.ticker import TickerPool
        pool = TickerPool.get_instance()
        await pool.shutdown()
        print("[INFO] Ticker system shut down")
    except Exception:
        pass

    # Stop health monitor
    try:
        from app.services.ai.websocket_health_monitor import get_health_monitor
        health_monitor = get_health_monitor()
        if health_monitor:
            await health_monitor.stop()
    except Exception:
        pass

    await close_db()
    print("[INFO] Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Options Trading Platform API",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}")
    logger.error(f"Exception: {type(exc).__name__}: {str(exc)}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "error_type": type(exc).__name__
        }
    )

# CORS middleware - use allow_origin_regex for more flexible matching
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",  # Allow any localhost port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dhan_auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upstox_auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(fyers_auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(paytm_auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(watchlist.router, prefix="/api/watchlists", tags=["Watchlists"])
app.include_router(instruments.router, prefix="/api/instruments", tags=["Instruments"])
app.include_router(options.router, prefix="/api/options", tags=["Options"])
app.include_router(strategy.router, prefix="/api/strategies", tags=["Strategies"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(optionchain.router, prefix="/api/optionchain", tags=["OptionChain"])
app.include_router(ofo.router, prefix="/api/ofo", tags=["OFO"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(strategy_wizard.router, prefix="/api/strategy-library", tags=["Strategy Library"])
app.include_router(constants.router, prefix="/api/constants", tags=["Constants"])
app.include_router(user_preferences.router, prefix="/api/user/preferences", tags=["User Preferences"])
app.include_router(smartapi.router, prefix="/api/smartapi", tags=["SmartAPI"])
app.include_router(zerodha_creds_router.router, prefix="/api/zerodha-credentials", tags=["Zerodha Credentials"])
app.include_router(upstox_creds_router.router, prefix="/api/upstox-credentials", tags=["Upstox Credentials"])
app.include_router(dhan_creds_router.router, prefix="/api/dhan-credentials", tags=["Dhan Credentials"])
app.include_router(settings_creds_router.router, prefix="/api/settings", tags=["Settings Credentials"])
app.include_router(autopilot_router, prefix="/api/v1/autopilot", tags=["AutoPilot"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(ticker.router, prefix="/api", tags=["Ticker"])
app.include_router(autopilot_ws_router, tags=["AutoPilot WebSocket"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": "1.0.0",
        "docs": "/docs"
    }
