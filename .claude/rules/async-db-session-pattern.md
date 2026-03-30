---
description: >
  All database operations use async SQLAlchemy with AsyncSession, dependency injection via
  Depends(get_db), and expire_on_commit=False. Services accept db:AsyncSession parameter.
globs: ["backend/app/**/*.py"]
synthesized: true
private: false
---

# Async Database Session Pattern

## Session Configuration

The async session is configured in `app/database.py` with `expire_on_commit=False`:

```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # CRITICAL — prevents DetachedInstanceError on access after commit
)
```

`expire_on_commit=False` MUST remain set. Without it, accessing any model attribute
after `session.commit()` raises `DetachedInstanceError` because async sessions cannot
lazy-load expired attributes.

## Dependency Injection

Routes get database sessions via FastAPI's `Depends(get_db)`:

```python
from app.database import get_db

@router.get("/strategies")
async def list_strategies(db: AsyncSession = Depends(get_db)):
    result = await strategy_service.get_all(db)
    return result
```

The `get_db` generator yields a session and handles cleanup:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

## Service Layer: Accept db Parameter

Services MUST accept `db: AsyncSession` as a parameter — never create their own sessions:

```python
# CORRECT — service receives session:
class StrategyService:
    async def get_all(self, db: AsyncSession) -> list[Strategy]:
        result = await db.execute(select(Strategy))
        return result.scalars().all()

# WRONG — service creates own session:
class StrategyService:
    async def get_all(self) -> list[Strategy]:
        async with AsyncSessionLocal() as db:  # NEVER — breaks transaction boundaries
            result = await db.execute(select(Strategy))
            return result.scalars().all()
```

## Eager Loading: selectinload()

For relationships, use `selectinload()` instead of `joinedload()` with async sessions:

```python
# CORRECT — async-compatible:
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(Strategy).options(selectinload(Strategy.legs))
)

# WRONG — causes greenlet errors with async:
from sqlalchemy.orm import joinedload
result = await db.execute(
    select(Strategy).options(joinedload(Strategy.legs))  # AVOID
)
```

`joinedload()` can cause greenlet spawn errors in async contexts. `selectinload()`
issues a separate SELECT query, which is async-safe.

## Transaction Boundaries

Routes own the transaction boundary. Services operate within the session but
MUST NOT call `session.commit()` — let the route or dependency manage commits:

```python
@router.post("/strategies")
async def create_strategy(data: StrategyCreate, db: AsyncSession = Depends(get_db)):
    strategy = await strategy_service.create(db, data)
    await db.commit()  # Route commits
    await db.refresh(strategy)
    return strategy
```

## MUST NOT

- MUST NOT remove `expire_on_commit=False` — causes DetachedInstanceError in async flows
- MUST NOT create sessions inside services — accept `db: AsyncSession` parameter
- MUST NOT use `joinedload()` — use `selectinload()` for async-safe eager loading
- MUST NOT use synchronous SQLAlchemy APIs — all DB operations must be `await`-ed
