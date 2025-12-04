from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import redis.asyncio as aioredis
from app.config import settings


# PostgreSQL AsyncEngine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# Redis connection pool
redis_pool = None


async def get_redis():
    """Get Redis connection from pool."""
    global redis_pool
    if redis_pool is None:
        redis_pool = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_pool


async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {str(e)}")
        print(f"[INFO] Please check database connection settings in .env file")
        print(f"[INFO] Current DATABASE_URL host: {settings.DATABASE_URL.split('@')[1].split(':')[0] if '@' in settings.DATABASE_URL else 'unknown'}")
        raise


async def close_db():
    """Close database connections."""
    global redis_pool
    if redis_pool:
        await redis_pool.close()
    await engine.dispose()
