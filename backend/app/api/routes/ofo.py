"""
OFO (Options For Options) API Routes

Endpoints for finding and ranking the best option strategy combinations.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

from app.database import get_db
from app.models import User, BrokerConnection
from app.services.ofo_calculator import ofo_calculator
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.schemas.ofo import (
    OFOCalculateRequest,
    OFOCalculateResponse,
    OFOStrategyResult,
    OFOLegResult,
    OFO_AVAILABLE_STRATEGIES
)
from app.constants import LOT_SIZES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/strategies")
async def get_available_strategies():
    """
    Get list of available strategies for OFO calculation.

    Returns the 9 popular strategies that can be used for finding
    optimal combinations.
    """
    return {
        "strategies": OFO_AVAILABLE_STRATEGIES
    }


@router.post("/calculate", response_model=OFOCalculateResponse)
async def calculate_ofo_strategies(
    request: OFOCalculateRequest,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate top 3 most profitable combinations for each selected strategy type.

    This endpoint:
    1. Fetches live option chain data for the selected underlying/expiry
    2. Generates all valid combinations for each strategy type
    3. Filters out invalid options (CMP=0/0.5/null, OI<=0, premium<1)
    4. Calculates max profit at expiry for each combination
    5. Returns top 3 combinations per strategy, ranked by max profit

    Performance: Calculation time is returned in the response for benchmarking.
    """
    underlying = request.underlying.upper()
    if underlying not in LOT_SIZES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid underlying. Must be one of: {list(LOT_SIZES.keys())}"
        )

    # Validate strategy types
    valid_strategy_keys = [s["key"] for s in OFO_AVAILABLE_STRATEGIES]
    for strategy_type in request.strategy_types:
        if strategy_type not in valid_strategy_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy type: {strategy_type}. Valid types: {valid_strategy_keys}"
            )

    from app.services.brokers.market_data import get_user_market_data_adapter

    try:
        # Parse expiry date
        try:
            expiry_date = datetime.strptime(request.expiry, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        # Get market data adapter (automatically uses user's preferred broker)
        logger.info(f"[OFO] Fetching market data via adapter for {underlying}")
        adapter = await get_user_market_data_adapter(user.id, db)

        lot_size = LOT_SIZES.get(underlying, 1)

        # Get spot price via adapter
        ltp_map = await adapter.get_ltp([underlying])
        spot_price = float(ltp_map.get(underlying, 0))

        if not spot_price:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not get spot price"
            )

        # Get instruments for this expiry from adapter
        all_instruments = await adapter.get_instruments("NFO")

        # Filter for our underlying and expiry
        instruments = [
            inst for inst in all_instruments
            if inst.name == underlying and
               inst.instrument_type in ["CE", "PE"] and
               hasattr(inst, 'expiry') and inst.expiry == expiry_date
        ]

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No instruments found for {underlying} expiry {expiry_date}"
            )

        logger.info(f"[OFO] Found {len(instruments)} instruments for {underlying}")

        # Organize by strike
        strikes_data = {}
        canonical_symbols = []

        for inst in instruments:
            strike = float(inst.strike) if hasattr(inst, 'strike') else 0
            if strike <= 0:
                continue

            if strike not in strikes_data:
                strikes_data[strike] = {"strike": strike, "ce": None, "pe": None}

            inst_data = {
                "instrument_token": inst.instrument_token,
                "tradingsymbol": inst.canonical_symbol,
                "lot_size": inst.lot_size
            }

            if inst.instrument_type == "CE":
                strikes_data[strike]["ce"] = inst_data
            else:
                strikes_data[strike]["pe"] = inst_data

            # Collect canonical symbols for quote fetch
            canonical_symbols.append(inst.canonical_symbol)

        logger.info(f"[OFO] Organized {len(strikes_data)} strikes, fetching quotes for {len(canonical_symbols)} instruments")

        # Fetch quotes in batches of 50
        all_quotes = {}
        for i in range(0, len(canonical_symbols), 50):
            batch = canonical_symbols[i:i+50]
            if batch:
                try:
                    quotes = await adapter.get_quote(batch)
                    for symbol, unified_quote in quotes.items():
                        # Store with NFO: prefix for compatibility
                        symbol_key = f"NFO:{symbol}"
                        all_quotes[symbol_key] = {
                            "last_price": float(unified_quote.last_price),
                            "oi": unified_quote.oi,
                            "volume": unified_quote.volume
                        }
                except Exception as e:
                    logger.warning(f"[OFO] Quote batch failed: {e}")
                    continue

        if not strikes_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No option strikes found for this expiry"
            )

        # Build chain data for OFO calculator
        chain_data = []
        for strike in sorted(strikes_data.keys()):
            data = strikes_data[strike]
            row = {"strike": strike, "ce": None, "pe": None}

            # Process CE
            if data["ce"]:
                ce_symbol = f"NFO:{data['ce']['tradingsymbol']}"
                ce_quote = all_quotes.get(ce_symbol, {})
                row["ce"] = {
                    "instrument_token": data["ce"]["instrument_token"],
                    "tradingsymbol": data["ce"]["tradingsymbol"],
                    "ltp": ce_quote.get("last_price", 0),
                    "oi": ce_quote.get("oi", 0),
                    "volume": ce_quote.get("volume", 0)
                }

            # Process PE
            if data["pe"]:
                pe_symbol = f"NFO:{data['pe']['tradingsymbol']}"
                pe_quote = all_quotes.get(pe_symbol, {})
                row["pe"] = {
                    "instrument_token": data["pe"]["instrument_token"],
                    "tradingsymbol": data["pe"]["tradingsymbol"],
                    "ltp": pe_quote.get("last_price", 0),
                    "oi": pe_quote.get("oi", 0),
                    "volume": pe_quote.get("volume", 0)
                }

            chain_data.append(row)

        # Calculate best strategies using OFO calculator
        calculation_result = ofo_calculator.calculate_best_strategies(
            chain_data=chain_data,
            spot_price=spot_price,
            expiry=request.expiry,
            underlying=underlying,
            strategy_types=request.strategy_types,
            strike_range=request.strike_range,
            lots=request.lots,
            top_n=3
        )

        # Convert results to response schema
        formatted_results = {}
        for strategy_type, combinations in calculation_result["results"].items():
            formatted_results[strategy_type] = [
                OFOStrategyResult(
                    strategy_type=combo["strategy_type"],
                    strategy_name=combo["strategy_name"],
                    max_profit=combo["max_profit"],
                    max_loss=combo["max_loss"],
                    breakevens=combo["breakevens"],
                    net_premium=combo["net_premium"],
                    risk_reward_ratio=combo["risk_reward_ratio"],
                    legs=[
                        OFOLegResult(
                            expiry=leg["expiry"],
                            contract_type=leg["contract_type"],
                            transaction_type=leg["transaction_type"],
                            strike=leg["strike"],
                            cmp=leg["cmp"],
                            lots=leg["lots"],
                            qty=leg["qty"],
                            instrument_token=leg["instrument_token"],
                            tradingsymbol=leg["tradingsymbol"]
                        )
                        for leg in combo["legs"]
                    ]
                )
                for combo in combinations
            ]

        return OFOCalculateResponse(
            underlying=calculation_result["underlying"],
            expiry=calculation_result["expiry"],
            spot_price=calculation_result["spot_price"],
            atm_strike=calculation_result["atm_strike"],
            lot_size=calculation_result["lot_size"],
            calculated_at=calculation_result["calculated_at"],
            calculation_time_ms=calculation_result["calculation_time_ms"],
            total_combinations_evaluated=calculation_result["total_combinations_evaluated"],
            results=formatted_results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OFO] Error calculating OFO strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating OFO strategies: {str(e)}"
        )
