"""
Watchlist API Routes

Endpoints for managing user watchlists.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import User, Watchlist, Instrument
from app.schemas import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    AddInstrumentRequest,
    InstrumentSearchResponse,
    WatchlistInstrument
)
from app.utils.dependencies import get_current_user
from app.services.instruments import InstrumentService

router = APIRouter()

MAX_WATCHLISTS_PER_USER = 5
MAX_INSTRUMENTS_PER_WATCHLIST = 100


@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all watchlists for current user.

    Returns:
        List of user's watchlists with instrument details
    """
    try:
        # Get user's watchlists
        result = await db.execute(
            select(Watchlist)
            .where(Watchlist.user_id == user.id)
            .order_by(Watchlist.order_index)
        )
        watchlists = result.scalars().all()

        # If no watchlists exist, create a default one
        if not watchlists:
            default_watchlist = Watchlist(
                user_id=user.id,
                name="Watchlist 1",
                instruments=[],
                order_index=0
            )
            db.add(default_watchlist)
            await db.commit()
            await db.refresh(default_watchlist)
            watchlists = [default_watchlist]

        return watchlists

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch watchlists: {str(e)}"
        )


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new watchlist.

    Args:
        watchlist_data: Watchlist creation data

    Returns:
        Created watchlist

    Raises:
        HTTPException: If user already has max watchlists
    """
    try:
        # Check watchlist count
        result = await db.execute(
            select(func.count(Watchlist.id)).where(Watchlist.user_id == user.id)
        )
        count = result.scalar()

        if count >= MAX_WATCHLISTS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_WATCHLISTS_PER_USER} watchlists allowed per user"
            )

        # Create watchlist
        watchlist = Watchlist(
            user_id=user.id,
            name=watchlist_data.name,
            instruments=[],
            order_index=count  # New watchlist at the end
        )

        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)

        return watchlist

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create watchlist: {str(e)}"
        )


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: UUID,
    watchlist_data: WatchlistUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a watchlist (rename, reorder instruments).

    Args:
        watchlist_id: Watchlist ID
        watchlist_data: Update data

    Returns:
        Updated watchlist
    """
    try:
        # Get watchlist
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user.id
            )
        )
        watchlist = result.scalar_one_or_none()

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        # Update fields
        if watchlist_data.name is not None:
            watchlist.name = watchlist_data.name

        if watchlist_data.instruments is not None:
            # Validate instrument limit
            if len(watchlist_data.instruments) > MAX_INSTRUMENTS_PER_WATCHLIST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum {MAX_INSTRUMENTS_PER_WATCHLIST} instruments allowed"
                )
            watchlist.instruments = [inst.dict() for inst in watchlist_data.instruments]

        if watchlist_data.order_index is not None:
            watchlist.order_index = watchlist_data.order_index

        await db.commit()
        await db.refresh(watchlist)

        return watchlist

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watchlist: {str(e)}"
        )


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a watchlist.

    Args:
        watchlist_id: Watchlist ID

    Raises:
        HTTPException: If it's the only watchlist
    """
    try:
        # Check if it's the only watchlist
        result = await db.execute(
            select(func.count(Watchlist.id)).where(Watchlist.user_id == user.id)
        )
        count = result.scalar()

        if count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only watchlist"
            )

        # Delete watchlist
        result = await db.execute(
            delete(Watchlist).where(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user.id
            )
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete watchlist: {str(e)}"
        )


@router.post("/{watchlist_id}/instruments", response_model=WatchlistResponse)
async def add_instrument_to_watchlist(
    watchlist_id: UUID,
    instrument_data: AddInstrumentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add instrument to watchlist.

    Args:
        watchlist_id: Watchlist ID
        instrument_data: Instrument to add

    Returns:
        Updated watchlist
    """
    try:
        # Get watchlist
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user.id
            )
        )
        watchlist = result.scalar_one_or_none()

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        # Check instrument limit
        if len(watchlist.instruments) >= MAX_INSTRUMENTS_PER_WATCHLIST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_INSTRUMENTS_PER_WATCHLIST} instruments allowed"
            )

        # Get instrument details
        instrument = await InstrumentService.get_instrument_by_token(db, instrument_data.instrument_token)

        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instrument not found"
            )

        # Check if already added
        existing_tokens = [inst["token"] for inst in watchlist.instruments]
        if instrument.instrument_token in existing_tokens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instrument already in watchlist"
            )

        # Add instrument
        watchlist.instruments.append({
            "token": instrument.instrument_token,
            "symbol": instrument.tradingsymbol,
            "exchange": instrument.exchange
        })

        # Mark as modified for JSONB update
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(watchlist, "instruments")

        await db.commit()
        await db.refresh(watchlist)

        return watchlist

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add instrument: {str(e)}"
        )


@router.delete("/{watchlist_id}/instruments/{instrument_token}", response_model=WatchlistResponse)
async def remove_instrument_from_watchlist(
    watchlist_id: UUID,
    instrument_token: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove instrument from watchlist.

    Args:
        watchlist_id: Watchlist ID
        instrument_token: Instrument token to remove

    Returns:
        Updated watchlist
    """
    try:
        # Get watchlist
        result = await db.execute(
            select(Watchlist).where(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user.id
            )
        )
        watchlist = result.scalar_one_or_none()

        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        # Remove instrument
        original_length = len(watchlist.instruments)
        watchlist.instruments = [
            inst for inst in watchlist.instruments
            if inst["token"] != instrument_token
        ]

        if len(watchlist.instruments) == original_length:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instrument not in watchlist"
            )

        # Mark as modified for JSONB update
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(watchlist, "instruments")

        await db.commit()
        await db.refresh(watchlist)

        return watchlist

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove instrument: {str(e)}"
        )
