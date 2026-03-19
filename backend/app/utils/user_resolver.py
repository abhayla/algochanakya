"""
Unified user resolution for multi-broker authentication.

All broker auth routes MUST use resolve_or_create_user() instead of
inline user lookup logic. This prevents duplicate user creation when
the same person logs in via multiple brokers.

See: docs/architecture/authentication.md#three-tier-credential-architecture
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, BrokerConnection

import logging

logger = logging.getLogger(__name__)


async def resolve_or_create_user(
    db: AsyncSession,
    broker: str,
    broker_user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> User:
    """
    Resolve an existing user or create a new one for broker authentication.

    Resolution priority:
    1. Look up by broker + broker_user_id (returning user on same broker)
    2. Look up by email if available (same person, different broker)
    3. Create new user if no match found

    Args:
        db: Database session
        broker: Broker name as stored in DB ('zerodha', 'angelone', 'upstox', etc.)
        broker_user_id: Broker-specific user identifier
        email: User's email from broker profile (optional)
        name: User's name from broker profile (optional)

    Returns:
        User object (existing or newly created)
    """
    # 1. Check if user already has a connection for this broker
    result = await db.execute(
        select(User).join(BrokerConnection).where(
            BrokerConnection.broker == broker,
            BrokerConnection.broker_user_id == broker_user_id,
        )
    )
    users = result.scalars().all()

    if len(users) == 1:
        user = users[0]
        logger.info(f"[UserResolver] Found existing user {user.id} via {broker}/{broker_user_id}")
        _update_user_profile(user, email, name)
        return user

    if len(users) > 1:
        # Multiple users found — merge to the oldest one
        user = min(users, key=lambda u: u.created_at)
        logger.warning(f"[UserResolver] Multiple users for {broker}/{broker_user_id}, using oldest {user.id}")
        _update_user_profile(user, email, name)
        return user

    # 2. No existing connection — try email-based lookup (links across brokers)
    if email:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        email_users = result.scalars().all()

        if len(email_users) == 1:
            user = email_users[0]
            logger.info(f"[UserResolver] Linked {broker}/{broker_user_id} to existing user {user.id} via email")
            _update_user_profile(user, email, name)
            return user

        if len(email_users) > 1:
            # Multiple users with same email — use the oldest
            user = min(email_users, key=lambda u: u.created_at)
            logger.warning(f"[UserResolver] Multiple users with email {email}, using oldest {user.id}")
            _update_user_profile(user, email, name)
            return user

    # 3. No match — create new user
    user = User(email=email)
    if name:
        user.first_name = name.split()[0].capitalize()
    db.add(user)
    await db.flush()
    logger.info(f"[UserResolver] Created new user {user.id} for {broker}/{broker_user_id}")
    return user


def _update_user_profile(user: User, email: Optional[str], name: Optional[str]):
    """Update user profile fields if we have new information."""
    if email and not user.email:
        user.email = email
    if name and not user.first_name:
        user.first_name = name.split()[0].capitalize()
