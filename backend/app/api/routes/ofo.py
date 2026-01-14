"""
OFO (Options For Options) API Routes

Endpoints for finding and ranking the best option strategy combinations.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, date
from kiteconnect.exceptions import TokenException as KiteTokenException
from SmartApi.smartExceptions import TokenException as SmartAPITokenException

from app.database import get_db
from app.models import User, BrokerConnection, Instrument
from app.services.kite_orders import KiteOrderService
from app.services.ofo_calculator import ofo_calculator
from app.services.smartapi_market_data import SmartAPIMarketData, SmartAPIMarketDataError
from app.services.smartapi_instruments import get_smartapi_instruments
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.schemas.ofo import (
    OFOCalculateRequest,
    OFOCalculateResponse,
    OFOStrategyResult,
    OFOLegResult,
    OFO_AVAILABLE_STRATEGIES
)
from app.constants import LOT_SIZES, INDEX_SYMBOLS
from app.config import settings

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

    try:
        # Parse expiry date
        try:
            expiry_date = datetime.strptime(request.expiry, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        # Determine which market data service to use based on broker type
        use_smartapi = broker.broker == "angelone"
        lot_size = LOT_SIZES.get(underlying, 1)
        strikes_data = {}
        all_quotes = {}

        if use_smartapi:
            # Use SmartAPI for market data
            logger.info(f"[OFO] Using SmartAPI for market data")
            smartapi_service = SmartAPIMarketData(
                api_key=settings.ANGEL_API_KEY,
                jwt_token=broker.access_token
            )

            # Get spot price using SmartAPI
            spot_quote = await smartapi_service.get_index_quote(underlying)
            if spot_quote:
                spot_price = float(spot_quote.get("ltp", 0))
            else:
                spot_price = 0

            if not spot_price:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not get spot price"
                )

            # Use SmartAPI instruments directly
            smartapi_instruments = get_smartapi_instruments()

            # Format expiry for SmartAPI: "2026-01-27" -> "27JAN2026"
            expiry_str = expiry_date.strftime("%d%b%Y").upper()
            logger.info(f"[OFO] Fetching SmartAPI instruments for {underlying} expiry {expiry_str}")

            # Get options from SmartAPI master
            smartapi_options = await smartapi_instruments.get_option_chain_tokens(underlying, expiry_str, "NFO")

            if not smartapi_options:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No instruments found for {underlying} expiry {expiry_str}"
                )

            logger.info(f"[OFO] Found {len(smartapi_options)} SmartAPI instruments")

            # Organize by strike and collect tokens for quote fetch
            nfo_tokens = []
            token_to_symbol = {}

            for opt in smartapi_options:
                symbol = opt.get('symbol', '')
                token = opt.get('token')
                strike_raw = opt.get('strike', 0)

                # Skip futures
                if 'FUT' in symbol:
                    continue

                # SmartAPI strike is in paise (e.g., 2560000 = 25600)
                # Convert to rupees
                try:
                    strike = float(strike_raw) / 100.0
                except (ValueError, TypeError):
                    continue

                if strike <= 0:
                    continue

                # Determine option type from symbol (ends with CE or PE)
                if symbol.endswith('CE'):
                    opt_type = 'CE'
                elif symbol.endswith('PE'):
                    opt_type = 'PE'
                else:
                    continue

                if strike not in strikes_data:
                    strikes_data[strike] = {"strike": strike, "ce": None, "pe": None}

                inst_data = {
                    "instrument_token": token,
                    "tradingsymbol": symbol,
                    "lot_size": int(opt.get('lotsize', lot_size))
                }

                if opt_type == "CE":
                    strikes_data[strike]["ce"] = inst_data
                else:
                    strikes_data[strike]["pe"] = inst_data

                # Collect token for quote fetch
                if token:
                    nfo_tokens.append(token)
                    token_to_symbol[token] = f"NFO:{symbol}"

            logger.info(f"[OFO] Organized {len(strikes_data)} strikes, fetching quotes for {len(nfo_tokens)} instruments")

            # Fetch quotes in batches of 50
            for i in range(0, len(nfo_tokens), 50):
                batch = nfo_tokens[i:i+50]
                if batch:
                    try:
                        quotes = await smartapi_service.get_quote("NFO", batch, mode="FULL")
                        for token, quote in quotes.items():
                            symbol_key = token_to_symbol.get(token)
                            if symbol_key:
                                all_quotes[symbol_key] = {
                                    "last_price": float(quote.get("ltp", 0)),
                                    "oi": quote.get("oi", 0),
                                    "volume": quote.get("volume", 0)
                                }
                    except SmartAPIMarketDataError as e:
                        logger.warning(f"[OFO] SmartAPI quote batch failed: {e}")
                        continue

        else:
            # Use Kite for market data (legacy/fallback)
            logger.info(f"[OFO] Using Kite for market data")
            kite_service = KiteOrderService(broker.access_token)

            # Get spot price
            spot_symbol = INDEX_SYMBOLS.get(underlying)
            spot_quote = await kite_service.get_quote([spot_symbol])
            spot_price = spot_quote.get(spot_symbol, {}).get("last_price", 0)

            if not spot_price:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not get spot price"
                )

            # Get instruments for this expiry from DB
            query = select(Instrument).where(
                and_(
                    Instrument.name == underlying,
                    Instrument.expiry == expiry_date,
                    Instrument.instrument_type.in_(["CE", "PE"]),
                    Instrument.exchange == "NFO"
                )
            ).order_by(Instrument.strike)

            result = await db.execute(query)
            instruments = result.scalars().all()

            if not instruments:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No instruments found for this expiry"
                )

            # Organize by strike
            for inst in instruments:
                strike = float(inst.strike)
                if strike not in strikes_data:
                    strikes_data[strike] = {"strike": strike, "ce": None, "pe": None}

                inst_data = {
                    "instrument_token": inst.instrument_token,
                    "tradingsymbol": inst.tradingsymbol,
                    "lot_size": inst.lot_size
                }

                if inst.instrument_type == "CE":
                    strikes_data[strike]["ce"] = inst_data
                else:
                    strikes_data[strike]["pe"] = inst_data

            # Get live quotes for all instruments (batch in groups of 500)
            instrument_list = [f"NFO:{inst.tradingsymbol}" for inst in instruments]

            for i in range(0, len(instrument_list), 500):
                batch = instrument_list[i:i+500]
                if batch:
                    quotes = await kite_service.get_quote(batch)
                    all_quotes.update(quotes)

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
    except (KiteTokenException, SmartAPITokenException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Broker session expired. Please re-login."
        )
    except SmartAPIMarketDataError as e:
        logger.error(f"[OFO] SmartAPI error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[OFO] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating OFO strategies: {str(e)}"
        )
