"""
Options Data API Routes

Endpoints for options expiries, strikes, and chain data.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, and_
from typing import List, Optional
from datetime import date
from decimal import Decimal

from app.database import get_db
from app.models import User, Instrument
from app.schemas.strategies import ExpiryResponse, StrikeResponse, OptionChainItem, OptionChainResponse
from app.utils.dependencies import get_current_user
from app.constants import LOT_SIZES, INDEX_TOKENS

router = APIRouter()

# Underlying to instrument name mapping
UNDERLYING_MAP = {
    "NIFTY": "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "FINNIFTY": "FINNIFTY",
}


@router.get("/expiries", response_model=ExpiryResponse)
async def get_expiries(
    underlying: str = Query(..., description="Underlying (NIFTY, BANKNIFTY, FINNIFTY)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available expiry dates for an underlying.

    Args:
        underlying: NIFTY, BANKNIFTY, or FINNIFTY

    Returns:
        List of expiry dates sorted ascending
    """
    underlying = underlying.upper()
    if underlying not in UNDERLYING_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid underlying. Must be one of: {list(UNDERLYING_MAP.keys())}"
        )

    try:
        # Query distinct expiry dates for the underlying
        query = select(distinct(Instrument.expiry)).where(
            and_(
                Instrument.name == UNDERLYING_MAP[underlying],
                Instrument.exchange == "NFO",
                Instrument.instrument_type.in_(["CE", "PE"]),
                Instrument.expiry >= date.today()
            )
        ).order_by(Instrument.expiry)

        result = await db.execute(query)
        expiries = [row[0] for row in result.fetchall() if row[0] is not None]

        return ExpiryResponse(expiries=expiries)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get expiries: {str(e)}"
        )


@router.get("/strikes", response_model=StrikeResponse)
async def get_strikes(
    underlying: str = Query(..., description="Underlying (NIFTY, BANKNIFTY, FINNIFTY)"),
    expiry: date = Query(..., description="Expiry date"),
    contract_type: Optional[str] = Query(None, description="CE or PE (optional)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available strike prices for an underlying and expiry.

    Args:
        underlying: NIFTY, BANKNIFTY, or FINNIFTY
        expiry: Expiry date
        contract_type: Optional filter for CE or PE

    Returns:
        List of strike prices sorted ascending
    """
    underlying = underlying.upper()
    if underlying not in UNDERLYING_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid underlying. Must be one of: {list(UNDERLYING_MAP.keys())}"
        )

    try:
        # Build query conditions
        conditions = [
            Instrument.name == UNDERLYING_MAP[underlying],
            Instrument.exchange == "NFO",
            Instrument.expiry == expiry,
            Instrument.strike.isnot(None)
        ]

        if contract_type:
            contract_type = contract_type.upper()
            if contract_type in ["CE", "PE"]:
                conditions.append(Instrument.instrument_type == contract_type)

        # Query distinct strikes
        query = select(distinct(Instrument.strike)).where(
            and_(*conditions)
        ).order_by(Instrument.strike)

        result = await db.execute(query)
        strikes = [row[0] for row in result.fetchall() if row[0] is not None]

        return StrikeResponse(strikes=strikes)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strikes: {str(e)}"
        )


@router.get("/chain", response_model=OptionChainResponse)
async def get_option_chain(
    underlying: str = Query(..., description="Underlying (NIFTY, BANKNIFTY, FINNIFTY)"),
    expiry: date = Query(..., description="Expiry date"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get option chain for an underlying and expiry.

    Args:
        underlying: NIFTY, BANKNIFTY, or FINNIFTY
        expiry: Expiry date

    Returns:
        Option chain with all CE and PE options
    """
    underlying = underlying.upper()
    if underlying not in UNDERLYING_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid underlying. Must be one of: {list(UNDERLYING_MAP.keys())}"
        )

    try:
        # Query all options for the underlying and expiry
        query = select(Instrument).where(
            and_(
                Instrument.name == UNDERLYING_MAP[underlying],
                Instrument.exchange == "NFO",
                Instrument.expiry == expiry,
                Instrument.instrument_type.in_(["CE", "PE"]),
                Instrument.strike.isnot(None)
            )
        ).order_by(Instrument.strike, Instrument.instrument_type)

        result = await db.execute(query)
        instruments = result.scalars().all()

        options = [
            OptionChainItem(
                instrument_token=inst.instrument_token,
                tradingsymbol=inst.tradingsymbol,
                strike=inst.strike,
                contract_type=inst.instrument_type,
                expiry=inst.expiry
            )
            for inst in instruments
        ]

        return OptionChainResponse(
            underlying=underlying,
            expiry=expiry,
            spot_price=None,  # Will be populated from WebSocket
            options=options
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get option chain: {str(e)}"
        )


@router.get("/instrument")
async def get_instrument_by_params(
    underlying: str = Query(..., description="Underlying (NIFTY, BANKNIFTY, FINNIFTY)"),
    expiry: date = Query(..., description="Expiry date"),
    strike: Decimal = Query(..., description="Strike price"),
    contract_type: str = Query(..., description="CE or PE"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific instrument by parameters.

    Args:
        underlying: NIFTY, BANKNIFTY, or FINNIFTY
        expiry: Expiry date
        strike: Strike price
        contract_type: CE or PE

    Returns:
        Instrument details with token
    """
    underlying = underlying.upper()
    contract_type = contract_type.upper()

    if underlying not in UNDERLYING_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid underlying. Must be one of: {list(UNDERLYING_MAP.keys())}"
        )

    if contract_type not in ["CE", "PE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract type must be CE or PE"
        )

    try:
        query = select(Instrument).where(
            and_(
                Instrument.name == UNDERLYING_MAP[underlying],
                Instrument.exchange == "NFO",
                Instrument.expiry == expiry,
                Instrument.strike == strike,
                Instrument.instrument_type == contract_type
            )
        )

        result = await db.execute(query)
        instrument = result.scalar_one_or_none()

        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instrument not found"
            )

        return {
            "instrument_token": instrument.instrument_token,
            "tradingsymbol": instrument.tradingsymbol,
            "name": instrument.name,
            "exchange": instrument.exchange,
            "strike": float(instrument.strike),
            "expiry": instrument.expiry.isoformat(),
            "contract_type": instrument.instrument_type,
            "lot_size": instrument.lot_size
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get instrument: {str(e)}"
        )


@router.get("/lot-sizes")
async def get_lot_sizes(user: User = Depends(get_current_user)):
    """
    Get lot sizes for all underlyings.

    Returns:
        Dictionary of underlying to lot size
    """
    return LOT_SIZES


@router.get("/index-tokens")
async def get_index_tokens(user: User = Depends(get_current_user)):
    """
    Get index tokens for underlyings.

    Returns:
        Dictionary of underlying to index token
    """
    return INDEX_TOKENS
