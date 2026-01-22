from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import jwt as pyjwt

from app.database import get_db
from app.models import User, BrokerConnection
from app.utils.jwt import verify_access_token


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from request header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        # Verify and decode token
        payload = verify_access_token(token)
        user_id = UUID(payload.get("user_id"))

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except (pyjwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


async def get_current_broker_connection(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BrokerConnection:
    """
    Dependency to get current user's active broker connection.

    Args:
        credentials: HTTP Bearer token
        user: Current authenticated user
        db: Database session

    Returns:
        BrokerConnection object

    Raises:
        HTTPException: If no active broker connection found
    """
    token = credentials.credentials

    try:
        payload = verify_access_token(token)
        broker_connection_id = payload.get("broker_connection_id")

        if broker_connection_id:
            broker_connection_id = UUID(broker_connection_id)
    except (pyjwt.InvalidTokenError, ValueError):
        broker_connection_id = None

    # Query for active broker connection
    query = select(BrokerConnection).where(
        BrokerConnection.user_id == user.id,
        BrokerConnection.is_active == True
    )

    if broker_connection_id:
        query = query.where(BrokerConnection.id == broker_connection_id)

    result = await db.execute(query)
    broker_connection = result.scalar_one_or_none()

    if not broker_connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active broker connection found"
        )

    return broker_connection


def get_kite_client(
    broker_connection: BrokerConnection = Depends(get_current_broker_connection)
):
    """
    Dependency to get KiteConnect client for current user's broker connection.

    DEPRECATED: Use get_broker_adapter_dep() instead for broker-agnostic code.

    Args:
        broker_connection: Current user's active broker connection

    Returns:
        KiteConnect client instance with access token set
    """
    from kiteconnect import KiteConnect
    from app.config import settings

    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(broker_connection.access_token)
    return kite


async def get_broker_adapter_dep(
    broker: BrokerConnection = Depends(get_current_broker_connection)
):
    """
    FastAPI dependency for broker adapter.

    Returns an initialized BrokerAdapter based on the broker connection.
    Currently defaults to Kite adapter as it's the only order execution broker.

    Args:
        broker: Current user's active broker connection

    Returns:
        Initialized BrokerAdapter instance

    Usage:
        @router.get("/positions")
        async def get_positions(adapter: BrokerAdapter = Depends(get_broker_adapter_dep)):
            positions = await adapter.get_positions()
            return positions
    """
    from app.services.brokers.factory import get_broker_adapter
    from app.services.brokers.base import BrokerType, BrokerAdapter

    adapter = await get_broker_adapter(BrokerType.KITE, broker.access_token)
    return adapter
