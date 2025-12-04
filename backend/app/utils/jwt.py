import jwt
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from app.config import settings


def create_access_token(user_id: UUID, broker_connection_id: Optional[UUID] = None) -> str:
    """
    Create JWT access token for authenticated user.

    Args:
        user_id: User's UUID
        broker_connection_id: Optional broker connection UUID

    Returns:
        JWT token string
    """
    expires_at = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)

    payload = {
        "user_id": str(user_id),
        "exp": expires_at,
        "iat": datetime.utcnow(),
    }

    if broker_connection_id:
        payload["broker_connection_id"] = str(broker_connection_id)

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token


def verify_access_token(token: str) -> dict:
    """
    Verify and decode JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("Invalid token")
