from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.database import get_redis, engine

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint that tests:
    - PostgreSQL connection
    - Redis connection
    """
    status = {
        "status": "healthy",
        "database": "disconnected",
        "redis": "disconnected"
    }

    # Test PostgreSQL connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            status["database"] = "connected"
    except Exception as e:
        status["status"] = "unhealthy"
        status["database_error"] = str(e)

    # Test Redis connection
    try:
        redis = await get_redis()
        await redis.ping()
        status["redis"] = "connected"
    except Exception as e:
        status["status"] = "unhealthy"
        status["redis_error"] = str(e)

    # Return appropriate status code
    if status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=status)

    return status
