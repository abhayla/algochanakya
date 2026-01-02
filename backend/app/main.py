from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import select, func
import logging
import traceback

from app.config import settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.api.routes import health, auth, watchlist, instruments, websocket, options, strategy, orders, optionchain, positions, strategy_wizard, constants, user_preferences, ofo
from app.api.v1.autopilot import router as autopilot_router
from app.api.v1.ai import router as ai_router
from app.websocket.routes import router as autopilot_ws_router
from app.models import Instrument

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def check_and_download_instruments():
    """Check if instruments table is empty and download if needed."""
    try:
        async with AsyncSessionLocal() as db:
            # Check count
            result = await db.execute(select(func.count(Instrument.id)))
            count = result.scalar()

            if count == 0:
                print("[INFO] Instruments table is empty. Downloading from Kite...")
                from app.services.instruments import refresh_instrument_master
                await refresh_instrument_master(db)
                print("[SUCCESS] Instruments downloaded successfully")
            else:
                print(f"[INFO] Instruments table has {count} records")
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
    await check_and_download_instruments()

    # Note: Strategy Monitor requires a valid Kite session to start.
    # It will be initialized when a user with valid broker connection
    # activates a strategy. See app/services/strategy_monitor.py for details.
    # To start monitor globally with a service account:
    #
    # from kiteconnect import KiteConnect
    # from app.services.strategy_monitor import get_strategy_monitor
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

    yield

    # Shutdown
    from app.services.strategy_monitor import stop_strategy_monitor
    await stop_strategy_monitor()

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
app.include_router(autopilot_router, prefix="/api/v1/autopilot", tags=["AutoPilot"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI"])
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

