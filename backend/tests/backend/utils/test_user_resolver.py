"""Unit tests for resolve_or_create_user() in app/utils/user_resolver.py."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger
from sqlalchemy.ext.compiler import compiles

from app.database import Base
from app.models import User
from app.models.broker_connections import BrokerConnection
from app.utils.user_resolver import resolve_or_create_user
