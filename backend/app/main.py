from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select, func

from app.config import settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.api.routes import health, auth, watchlist, instruments, websocket, options, strategy, orders, optionchain, positions, strategy_wizard
from app.api.v1.autopilot import router as autopilot_router
from app.models import Instrument


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

    # Auto-download instruments if needed
    await check_and_download_instruments()

    yield
    # Shutdown
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(strategy_wizard.router, prefix="/api/strategy-library", tags=["Strategy Library"])
app.include_router(autopilot_router, prefix="/api/v1", tags=["AutoPilot"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": "1.0.0",
        "docs": "/docs"
    }
