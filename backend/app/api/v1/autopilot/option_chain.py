"""
AutoPilot Option Chain API Routes - Phase 5

Endpoints for accessing option chain data with Greeks and strike finding.
"""
from datetime import date
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_db
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models import User, BrokerConnection
from app.config import settings
from app.schemas.autopilot import (
    OptionChainResponse,
    StrikeFindByDeltaRequest,
    StrikeFindByPremiumRequest,
    StrikeFindResponse
)
from app.services.option_chain_service import OptionChainService
from app.services.strike_finder_service import StrikeFinderService

router = APIRouter()


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/{underlying}/{expiry}", response_model=OptionChainResponse)
async def get_option_chain(
    underlying: str,
    expiry: date,
    use_cache: bool = Query(True, description="Use cached data if available"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get full option chain for an underlying and expiry.

    Includes:
    - Strike prices
    - LTP, Bid, Ask
    - Volume, OI, OI Change
    - Greeks (Delta, Gamma, Theta, Vega)
    - Implied Volatility (IV)

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
        expiry: Expiry date (YYYY-MM-DD)
        use_cache: Use cached data (default: true)

    Returns:
        Option chain data with all strikes
    """
    try:
        # Validate underlying
        valid_underlyings = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]
        if underlying.upper() not in valid_underlyings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid underlying. Must be one of: {', '.join(valid_underlyings)}"
            )

        service = OptionChainService(kite, db)
        chain_data = await service.get_option_chain(
            underlying=underlying.upper(),
            expiry=expiry,
            use_cache=use_cache
        )

        return chain_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching option chain: {str(e)}"
        )


@router.get("/{underlying}/{expiry}/strikes", response_model=List[Decimal])
async def get_strikes_list(
    underlying: str,
    expiry: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get list of available strike prices.

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
        expiry: Expiry date

    Returns:
        List of strike prices
    """
    try:
        service = OptionChainService(kite, db)
        strikes = await service.get_strikes_list(
            underlying=underlying.upper(),
            expiry=expiry
        )

        return strikes

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching strikes: {str(e)}"
        )


@router.post("/find-by-delta", response_model=StrikeFindResponse)
async def find_strike_by_delta(
    request: StrikeFindByDeltaRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Find option strike by target delta.

    Example: Find "15 delta PUT" or "20 delta CALL"

    Args:
        request: Delta find request with:
            - underlying: NIFTY, BANKNIFTY, etc.
            - expiry: Expiry date
            - option_type: CE or PE
            - target_delta: Target delta value (0 to 1)
            - tolerance: Acceptable delta deviation (default: 0.02)
            - prefer_round_strike: Prefer strikes divisible by 100

    Returns:
        Strike with closest delta
    """
    try:
        service = StrikeFinderService(kite, db)
        result = await service.find_strike_by_delta(
            underlying=request.underlying.upper(),
            expiry=request.expiry,
            option_type=request.option_type.upper(),
            target_delta=request.target_delta,
            tolerance=request.tolerance,
            prefer_round_strike=request.prefer_round_strike
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No strike found for delta {request.target_delta}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding strike by delta: {str(e)}"
        )


@router.post("/find-by-premium", response_model=StrikeFindResponse)
async def find_strike_by_premium(
    request: StrikeFindByPremiumRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Find option strike by target premium.

    Example: Find strike with "₹180 premium" or "₹250 premium"

    Args:
        request: Premium find request with:
            - underlying: NIFTY, BANKNIFTY, etc.
            - expiry: Expiry date
            - option_type: CE or PE
            - target_premium: Target premium value
            - tolerance: Acceptable premium deviation (default: 10)
            - prefer_round_strike: Prefer strikes divisible by 100

    Returns:
        Strike with closest premium
    """
    try:
        service = StrikeFinderService(kite, db)
        result = await service.find_strike_by_premium(
            underlying=request.underlying.upper(),
            expiry=request.expiry,
            option_type=request.option_type.upper(),
            target_premium=request.target_premium,
            tolerance=request.tolerance,
            prefer_round_strike=request.prefer_round_strike
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No strike found for premium {request.target_premium}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding strike by premium: {str(e)}"
        )


@router.get("/find-atm/{underlying}/{expiry}")
async def find_atm_strike(
    underlying: str,
    expiry: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Find ATM (At The Money) strike.

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
        expiry: Expiry date

    Returns:
        ATM strike price
    """
    try:
        service = StrikeFinderService(kite, db)
        atm_strike = await service.find_atm_strike(
            underlying=underlying.upper(),
            expiry=expiry
        )

        if not atm_strike:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot determine ATM strike for {underlying} {expiry}"
            )

        return {
            "underlying": underlying.upper(),
            "expiry": expiry,
            "atm_strike": atm_strike
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding ATM strike: {str(e)}"
        )


@router.get("/strikes-in-range/{underlying}/{expiry}")
async def find_strikes_in_range(
    underlying: str,
    expiry: date,
    option_type: str = Query(..., regex="^(CE|PE)$"),
    min_value: Decimal = Query(...),
    max_value: Decimal = Query(...),
    range_type: str = Query("premium", regex="^(premium|delta)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Find all strikes within a value range.

    Args:
        underlying: NIFTY, BANKNIFTY, etc.
        expiry: Expiry date
        option_type: CE or PE
        min_value: Minimum value
        max_value: Maximum value
        range_type: 'premium' or 'delta'

    Returns:
        List of strikes within range
    """
    try:
        service = StrikeFinderService(kite, db)
        strikes = await service.find_strikes_in_range(
            underlying=underlying.upper(),
            expiry=expiry,
            option_type=option_type.upper(),
            min_value=min_value,
            max_value=max_value,
            range_type=range_type
        )

        return {
            "underlying": underlying.upper(),
            "expiry": expiry,
            "option_type": option_type.upper(),
            "range_type": range_type,
            "min_value": min_value,
            "max_value": max_value,
            "strikes": strikes
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding strikes in range: {str(e)}"
        )


@router.get("/strike-by-sd/{underlying}/{expiry}")
async def find_strike_by_sd(
    underlying: str,
    expiry: date,
    option_type: str = Query(..., regex="^(CE|PE)$"),
    sd_multiplier: float = Query(..., ge=0.5, le=3.0),
    prefer_round_strike: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Find strike at X standard deviations from ATM.

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
        expiry: Expiry date
        option_type: CE or PE
        sd_multiplier: Standard deviation multiplier (0.5 to 3.0)
        prefer_round_strike: Prefer strikes divisible by 100

    Returns:
        Strike details with price and Greeks
    """
    try:
        service = StrikeFinderService(kite, db)
        result = await service.find_strike_by_standard_deviation(
            underlying=underlying.upper(),
            expiry=expiry,
            option_type=option_type.upper(),
            standard_deviations=sd_multiplier,
            prefer_round_strike=prefer_round_strike
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No strike found for {sd_multiplier} SD"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding strike by SD: {str(e)}"
        )


@router.get("/strike-by-expected-move/{underlying}/{expiry}")
async def find_strike_by_expected_move(
    underlying: str,
    expiry: date,
    option_type: str = Query(..., regex="^(CE|PE)$"),
    position: str = Query(..., regex="^(above|below)$"),
    prefer_round_strike: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Find strike outside expected move range.

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
        expiry: Expiry date
        option_type: CE or PE
        position: 'above' or 'below' expected move
        prefer_round_strike: Prefer strikes divisible by 100

    Returns:
        Strike details outside expected move
    """
    try:
        service = StrikeFinderService(kite, db)
        result = await service.find_strike_by_expected_move(
            underlying=underlying.upper(),
            expiry=expiry,
            option_type=option_type.upper(),
            outside=True,
            outside_sd=1.0,
            prefer_round_strike=prefer_round_strike
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No strike found outside expected move"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding strike by expected move: {str(e)}"
        )


@router.get("/expected-move-range/{underlying}/{expiry}")
async def get_expected_move_range(
    underlying: str,
    expiry: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get expected move range for display.

    Calculates expected move using ATM straddle price or IV-based formula.

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX
        expiry: Expiry date

    Returns:
        Dict with spot, expected_move, upper_bound, lower_bound
    """
    try:
        from app.services.expected_move_service import ExpectedMoveService

        service = ExpectedMoveService(kite, db)
        expiry_str = expiry.strftime("%Y-%m-%d")
        result = await service.get_expected_move_range(underlying.upper(), expiry_str)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching expected move range: {str(e)}"
        )


@router.get("/expiries/{underlying}")
async def get_expiries(
    underlying: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get available expiry dates for an underlying.

    Args:
        underlying: NIFTY, BANKNIFTY, FINNIFTY, or SENSEX

    Returns:
        List of available expiry dates
    """
    try:
        import asyncio

        # Fetch instruments from Kite
        loop = asyncio.get_event_loop()
        all_instruments = await loop.run_in_executor(
            None,
            kite.instruments,
            "NFO"
        )

        # Filter for this underlying and get unique expiries
        expiries = sorted(set(
            inst['expiry']
            for inst in all_instruments
            if inst['name'] == underlying.upper()
            and inst['instrument_type'] in ['CE', 'PE']
        ))

        return {
            "underlying": underlying.upper(),
            "expiries": [exp.strftime("%Y-%m-%d") for exp in expiries]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching expiries: {str(e)}"
        )
