"""
Instruments API Routes

Endpoints for searching and managing instruments.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.schemas import InstrumentSearchResponse
from app.services.instruments import InstrumentService
from app.utils.dependencies import get_current_user
from app.models import User

router = APIRouter()


@router.get("/search", response_model=List[InstrumentSearchResponse])
async def search_instruments(
    q: str = Query(..., min_length=1, description="Search query"),
    exchange: Optional[str] = Query(None, description="Filter by exchange (NSE, BSE, NFO, etc.)"),
    segment: Optional[str] = Query(None, description="Filter by segment"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search instruments by symbol or name.

    Args:
        q: Search query
        exchange: Optional exchange filter
        segment: Optional segment filter
        limit: Maximum results

    Returns:
        List of matching instruments
    """
    try:
        instruments = await InstrumentService.search_instruments(
            db=db,
            query=q,
            exchange=exchange,
            segment=segment,
            limit=limit
        )

        return instruments

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search instruments: {str(e)}"
        )


@router.get("/indices")
async def get_indices(user: User = Depends(get_current_user)):
    """
    Get major index instruments (NIFTY 50, NIFTY BANK).

    Returns:
        List of index instruments with tokens
    """
    try:
        indices = await InstrumentService.get_indices()
        return indices

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get indices: {str(e)}"
        )


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_instrument_master(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger instrument master refresh (admin only in production).

    Returns:
        Status message
    """
    try:
        from app.services.instruments import refresh_instrument_master

        # In production, check if user is admin
        # For now, allow all authenticated users

        # Check if refresh is needed
        should_refresh = await InstrumentService.should_refresh_instruments()

        if should_refresh:
            # Trigger background refresh
            # In production, use background tasks or celery
            await refresh_instrument_master(db)
            return {"message": "Instrument master refresh started", "status": "success"}
        else:
            return {"message": "Instrument master is up to date", "status": "skipped"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh instruments: {str(e)}"
        )
