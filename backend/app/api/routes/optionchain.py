"""
Option Chain API Routes

Endpoints for full option chain with OI, IV, Greeks, and live prices.
Uses SmartAPI for market data (default) or Kite as fallback.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
import math
import logging
from kiteconnect.exceptions import TokenException

from app.database import get_db
from app.models import User, BrokerConnection, Instrument
from app.services.kite_orders import KiteOrderService
from app.services.smartapi_market_data import SmartAPIMarketData, SmartAPIMarketDataError
from app.services.smartapi_instruments import get_smartapi_instruments
from app.services.strike_finder_service import StrikeFinderService
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.schemas.autopilot import (
    StrikeFindByDeltaRequest,
    StrikeFindByPremiumRequest,
    StrikeFindResponse
)
from app.constants import LOT_SIZES, INDEX_TOKENS, INDEX_SYMBOLS
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Constants
RISK_FREE_RATE = 0.07  # 7% for India


def calculate_iv(option_price: float, spot: float, strike: float,
                 days_to_expiry: int, is_call: bool) -> float:
    """Calculate Implied Volatility using Newton-Raphson method"""
    if days_to_expiry <= 0 or option_price <= 0 or spot <= 0 or strike <= 0:
        return 0.0

    T = days_to_expiry / 365.0
    r = RISK_FREE_RATE

    # Initial guess
    sigma = 0.3

    for _ in range(100):  # Max iterations
        try:
            d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            # Normal CDF approximation
            def norm_cdf(x):
                return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

            def norm_pdf(x):
                return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)

            if is_call:
                price = spot * norm_cdf(d1) - strike * math.exp(-r * T) * norm_cdf(d2)
            else:
                price = strike * math.exp(-r * T) * norm_cdf(-d2) - spot * norm_cdf(-d1)

            vega = spot * math.sqrt(T) * norm_pdf(d1)

            if vega < 1e-10:
                break

            diff = option_price - price
            if abs(diff) < 0.01:
                break

            sigma += diff / vega
            sigma = max(0.01, min(sigma, 5.0))  # Bound sigma
        except (ValueError, ZeroDivisionError):
            break

    return round(sigma * 100, 2)  # Return as percentage


def calculate_greeks(spot: float, strike: float, days_to_expiry: int,
                     iv: float, is_call: bool) -> dict:
    """Calculate Option Greeks"""
    if days_to_expiry <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    try:
        T = days_to_expiry / 365.0
        r = RISK_FREE_RATE
        sigma = iv / 100.0

        d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        def norm_cdf(x):
            return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

        def norm_pdf(x):
            return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)

        # Delta
        if is_call:
            delta = norm_cdf(d1)
        else:
            delta = norm_cdf(d1) - 1

        # Gamma
        gamma = norm_pdf(d1) / (spot * sigma * math.sqrt(T))

        # Theta (per day)
        theta_part1 = -(spot * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
        if is_call:
            theta = (theta_part1 - r * strike * math.exp(-r * T) * norm_cdf(d2)) / 365
        else:
            theta = (theta_part1 + r * strike * math.exp(-r * T) * norm_cdf(-d2)) / 365

        # Vega (per 1% move in IV)
        vega = spot * math.sqrt(T) * norm_pdf(d1) / 100

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 2),
            "vega": round(vega, 2)
        }
    except (ValueError, ZeroDivisionError):
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}


def calculate_max_pain(oi_data: dict, spot: float) -> float:
    """Calculate Max Pain strike"""
    if not oi_data:
        return spot

    min_pain = float('inf')
    max_pain_strike = spot

    strikes = sorted(oi_data.keys())

    for test_strike in strikes:
        total_pain = 0

        for strike, data in oi_data.items():
            # CE pain: If spot > strike, CE is ITM
            if test_strike > strike:
                ce_pain = (test_strike - strike) * data["ce_oi"]
            else:
                ce_pain = 0

            # PE pain: If spot < strike, PE is ITM
            if test_strike < strike:
                pe_pain = (strike - test_strike) * data["pe_oi"]
            else:
                pe_pain = 0

            total_pain += ce_pain + pe_pain

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike

    return max_pain_strike


@router.get("/chain")
async def get_option_chain(
    underlying: str = Query(..., description="NIFTY, BANKNIFTY, or FINNIFTY"),
    expiry: str = Query(..., description="Expiry date in YYYY-MM-DD format"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete option chain with OI, IV, Greeks.

    Returns all strikes with CE and PE data including:
    - LTP, change, bid/ask
    - OI and OI change
    - Volume
    - Implied Volatility
    - Greeks (Delta, Gamma, Theta, Vega)
    - Summary (PCR, Max Pain, ATM)
    """
    underlying = underlying.upper()
    if underlying not in LOT_SIZES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid underlying. Must be one of: {list(LOT_SIZES.keys())}"
        )

    try:
        # Parse expiry date
        try:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        except ValueError:
            try:
                expiry_date = datetime.strptime(expiry, "%d-%b-%Y").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD or DD-MMM-YYYY"
                )

        # Determine which market data service to use based on broker type
        use_smartapi = broker.broker == "angelone"

        if use_smartapi:
            # Use SmartAPI for market data
            logger.info(f"[OptionChain] Using SmartAPI for market data")
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
        else:
            # Use Kite for market data (legacy/fallback)
            logger.info(f"[OptionChain] Using Kite for market data")
            kite_service = KiteOrderService(broker.access_token)
            spot_symbol = INDEX_SYMBOLS.get(underlying)
            spot_quote = await kite_service.get_quote([spot_symbol])
            spot_price = spot_quote.get(spot_symbol, {}).get("last_price", 0)

        if not spot_price:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not get spot price"
            )

        # Get instruments for this expiry
        strikes_data = {}
        instrument_map = {}  # token -> instrument
        all_quotes = {}
        lot_size = LOT_SIZES.get(underlying, 1)

        if use_smartapi:
            # Use SmartAPI instruments directly (different format than Kite)
            smartapi_instruments = get_smartapi_instruments()

            # Format expiry for SmartAPI: "2026-01-27" -> "27JAN2026"
            expiry_str = expiry_date.strftime("%d%b%Y").upper()
            logger.info(f"[OptionChain] Fetching SmartAPI instruments for {underlying} expiry {expiry_str}")

            # Get options from SmartAPI master
            smartapi_options = await smartapi_instruments.get_option_chain_tokens(underlying, expiry_str, "NFO")

            if not smartapi_options:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No instruments found for {underlying} expiry {expiry_str}"
                )

            logger.info(f"[OptionChain] Found {len(smartapi_options)} SmartAPI instruments")

            # Organize by strike and collect tokens for quote fetch
            nfo_tokens = []
            token_to_symbol = {}

            for opt in smartapi_options:
                symbol = opt.get('symbol', '')
                token = opt.get('token')
                strike_raw = opt.get('strike', 0)
                inst_type = opt.get('instrumenttype', '')

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

            logger.info(f"[OptionChain] Organized {len(strikes_data)} strikes, fetching quotes for {len(nfo_tokens)} instruments")

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
                                    "volume": quote.get("volume", 0),
                                    "ohlc": {
                                        "open": float(quote.get("open", 0)),
                                        "high": float(quote.get("high", 0)),
                                        "low": float(quote.get("low", 0)),
                                        "close": float(quote.get("close", 0))
                                    },
                                    "depth": quote.get("depth", {"buy": [], "sell": []})
                                }
                    except SmartAPIMarketDataError as e:
                        logger.warning(f"[OptionChain] SmartAPI quote batch failed: {e}")
                        continue

        else:
            # Use Kite instruments table (legacy/fallback)
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

                instrument_map[inst.instrument_token] = inst

            # Get quotes from Kite
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

        # Calculate days to expiry
        today = date.today()
        days_to_expiry = (expiry_date - today).days

        # Build option chain
        option_chain = []
        total_ce_oi = 0
        total_pe_oi = 0
        max_pain_data = {}

        # Determine ATM strike (nearest to spot)
        sorted_strikes = sorted(strikes_data.keys())
        atm_strike = min(sorted_strikes, key=lambda x: abs(x - spot_price)) if sorted_strikes else spot_price

        for strike in sorted_strikes:
            data = strikes_data[strike]
            row = {
                "strike": strike,
                "is_atm": strike == atm_strike,
                "is_itm_ce": strike < spot_price,
                "is_itm_pe": strike > spot_price,
                "ce": None,
                "pe": None
            }

            # Process CE
            if data["ce"]:
                ce_symbol = f"NFO:{data['ce']['tradingsymbol']}"
                ce_quote = all_quotes.get(ce_symbol, {})

                ce_ltp = ce_quote.get("last_price", 0)
                ce_oi = ce_quote.get("oi", 0)
                ce_volume = ce_quote.get("volume", 0)
                ce_ohlc = ce_quote.get("ohlc", {})
                ce_close = ce_ohlc.get("close", 0)
                ce_change = ce_ltp - ce_close if ce_close else 0
                ce_change_pct = (ce_change / ce_close * 100) if ce_close else 0

                # Bid/Ask from depth
                ce_depth = ce_quote.get("depth", {})
                ce_bid = ce_depth.get("buy", [{}])[0].get("price", 0) if ce_depth.get("buy") else 0
                ce_ask = ce_depth.get("sell", [{}])[0].get("price", 0) if ce_depth.get("sell") else 0

                # Calculate IV and Greeks
                ce_iv = calculate_iv(ce_ltp, spot_price, strike, days_to_expiry, True)
                ce_greeks = calculate_greeks(spot_price, strike, days_to_expiry, ce_iv, True)

                row["ce"] = {
                    "instrument_token": data["ce"]["instrument_token"],
                    "tradingsymbol": data["ce"]["tradingsymbol"],
                    "ltp": ce_ltp,
                    "change": round(ce_change, 2),
                    "change_pct": round(ce_change_pct, 2),
                    "bid": ce_bid,
                    "ask": ce_ask,
                    "oi": ce_oi,
                    "volume": ce_volume,
                    "iv": ce_iv,
                    **ce_greeks
                }
                total_ce_oi += ce_oi

            # Process PE
            if data["pe"]:
                pe_symbol = f"NFO:{data['pe']['tradingsymbol']}"
                pe_quote = all_quotes.get(pe_symbol, {})

                pe_ltp = pe_quote.get("last_price", 0)
                pe_oi = pe_quote.get("oi", 0)
                pe_volume = pe_quote.get("volume", 0)
                pe_ohlc = pe_quote.get("ohlc", {})
                pe_close = pe_ohlc.get("close", 0)
                pe_change = pe_ltp - pe_close if pe_close else 0
                pe_change_pct = (pe_change / pe_close * 100) if pe_close else 0

                # Bid/Ask from depth
                pe_depth = pe_quote.get("depth", {})
                pe_bid = pe_depth.get("buy", [{}])[0].get("price", 0) if pe_depth.get("buy") else 0
                pe_ask = pe_depth.get("sell", [{}])[0].get("price", 0) if pe_depth.get("sell") else 0

                # Calculate IV and Greeks
                pe_iv = calculate_iv(pe_ltp, spot_price, strike, days_to_expiry, False)
                pe_greeks = calculate_greeks(spot_price, strike, days_to_expiry, pe_iv, False)

                row["pe"] = {
                    "instrument_token": data["pe"]["instrument_token"],
                    "tradingsymbol": data["pe"]["tradingsymbol"],
                    "ltp": pe_ltp,
                    "change": round(pe_change, 2),
                    "change_pct": round(pe_change_pct, 2),
                    "bid": pe_bid,
                    "ask": pe_ask,
                    "oi": pe_oi,
                    "volume": pe_volume,
                    "iv": pe_iv,
                    **pe_greeks
                }
                total_pe_oi += pe_oi

            # Max Pain calculation data
            max_pain_data[strike] = {
                "ce_oi": row["ce"]["oi"] if row["ce"] else 0,
                "pe_oi": row["pe"]["oi"] if row["pe"] else 0
            }

            option_chain.append(row)

        # Calculate Max Pain
        max_pain = calculate_max_pain(max_pain_data, spot_price)

        # Calculate PCR
        pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0

        return {
            "underlying": underlying,
            "expiry": expiry,
            "spot_price": spot_price,
            "days_to_expiry": days_to_expiry,
            "lot_size": LOT_SIZES.get(underlying, 75),
            "chain": option_chain,
            "summary": {
                "total_ce_oi": total_ce_oi,
                "total_pe_oi": total_pe_oi,
                "pcr": pcr,
                "max_pain": max_pain,
                "atm_strike": atm_strike
            }
        }

    except HTTPException:
        raise
    except TokenException as e:
        # Kite access token is invalid or expired - return 401 to trigger frontend redirect
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except SmartAPIMarketDataError as e:
        # SmartAPI error - could be token issue or API error
        error_msg = str(e).lower()
        if "token" in error_msg or "auth" in error_msg or "session" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"SmartAPI session expired. Please login again. ({str(e)})"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SmartAPI error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch option chain: {str(e)}"
        )


@router.get("/oi-analysis")
async def get_oi_analysis(
    underlying: str = Query(..., description="NIFTY, BANKNIFTY, or FINNIFTY"),
    expiry: str = Query(..., description="Expiry date"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Get OI analysis data for charts.

    Returns simplified OI data for visualization.
    """
    chain_data = await get_option_chain(underlying, expiry, user, broker, db)

    oi_data = []
    for row in chain_data["chain"]:
        oi_data.append({
            "strike": row["strike"],
            "ce_oi": row["ce"]["oi"] if row["ce"] else 0,
            "pe_oi": row["pe"]["oi"] if row["pe"] else 0,
            "ce_volume": row["ce"]["volume"] if row["ce"] else 0,
            "pe_volume": row["pe"]["volume"] if row["pe"] else 0,
            "ce_iv": row["ce"]["iv"] if row["ce"] else 0,
            "pe_iv": row["pe"]["iv"] if row["pe"] else 0,
        })

    return {
        "underlying": underlying,
        "expiry": expiry,
        "spot_price": chain_data["spot_price"],
        "data": oi_data,
        "summary": chain_data["summary"]
    }


@router.post("/find-by-delta", response_model=StrikeFindResponse)
async def find_strike_by_delta(
    request: StrikeFindByDeltaRequest,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Find option strike by target delta.

    Searches for the strike with delta closest to the target value.
    Optionally prefers round strikes (divisible by 100).
    """
    try:
        from kiteconnect import KiteConnect

        # Initialize Kite client
        kite = KiteConnect(api_key="placeholder")
        kite.set_access_token(broker.access_token)

        # Initialize Strike Finder service
        strike_finder = StrikeFinderService(kite, db)

        # Find strike by delta
        result = await strike_finder.find_strike_by_delta(
            underlying=request.underlying,
            expiry=request.expiry,
            option_type=request.option_type,
            target_delta=request.target_delta,
            tolerance=request.tolerance if hasattr(request, 'tolerance') else 0.02,
            prefer_round_strike=request.prefer_round_strike
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No strike found matching the criteria"
            )

        return result

    except HTTPException:
        raise
    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find strike by delta: {str(e)}"
        )


@router.post("/find-by-premium", response_model=StrikeFindResponse)
async def find_strike_by_premium(
    request: StrikeFindByPremiumRequest,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Find option strike by target premium (LTP).

    Searches for the strike with premium closest to the target value.
    Optionally prefers round strikes (divisible by 100).
    """
    try:
        from kiteconnect import KiteConnect

        # Initialize Kite client
        kite = KiteConnect(api_key="placeholder")
        kite.set_access_token(broker.access_token)

        # Initialize Strike Finder service
        strike_finder = StrikeFinderService(kite, db)

        # Find strike by premium
        result = await strike_finder.find_strike_by_premium(
            underlying=request.underlying,
            expiry=request.expiry,
            option_type=request.option_type,
            target_premium=request.target_premium,
            tolerance=request.tolerance if hasattr(request, 'tolerance') else 10,
            prefer_round_strike=request.prefer_round_strike
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No strike found matching the criteria"
            )

        return result

    except HTTPException:
        raise
    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find strike by premium: {str(e)}"
        )
