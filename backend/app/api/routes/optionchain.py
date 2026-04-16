"""
Option Chain API Routes

Endpoints for full option chain with OI, IV, Greeks, and live prices.
Uses unified market data adapter for broker-agnostic data access.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
import asyncio
import math
import logging
import numpy as np

from app.database import get_db
from app.models import User
from app.services.brokers.market_data import get_user_market_data_adapter
from app.services.brokers.market_data.factory import get_platform_market_data_adapter
from app.services.autopilot.strike_finder_service import StrikeFinderService
from app.utils.market_hours import get_data_freshness, is_market_open
from app.services.options.option_chain_cache import (
    get_or_compute, get_cached_platform_adapter,
)
from app.services.options.eod_snapshot_service import EODSnapshotService
from app.utils.dependencies import get_current_user
from app.schemas.autopilot import (
    StrikeFindByDeltaRequest,
    StrikeFindByPremiumRequest,
    StrikeFindResponse
)
from app.constants import LOT_SIZES
from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch
from app.services.options.option_chain_live_engine import OptionChainLiveEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Constants
RISK_FREE_RATE = 0.07  # 7% for India
# Skip IV/Greeks for strikes >10% OTM — Newton-Raphson diverges and IV is meaningless
FAR_OTM_MONEYNESS_THRESHOLD = 0.10


def _should_use_eod_snapshot(all_quotes: dict) -> bool:
    """Check if broker OI is mostly zeros (typical closed-market response).

    Uses a 90% threshold — if >=90% of strikes have zero OI, snapshot is needed.
    Upstox OC API sometimes returns OI for 1-2 ATM strikes even when closed.
    """
    if not all_quotes:
        return True
    total = len(all_quotes)
    zero_count = sum(1 for q in all_quotes.values() if q.get("oi", 0) == 0)
    return zero_count >= total * 0.9


def _apply_eod_fallback(
    all_quotes: dict,
    eod_snapshot: dict | None,
    strikes_data: dict,
) -> dict:
    """Apply EOD snapshot OI/volume/LTP to broker quotes.

    Two modes:
    1. all_quotes is populated (broker returned data with zero OI) — fill OI/volume from snapshot
    2. all_quotes is empty (broker returned nothing) — create quote entries from strikes_data + snapshot

    Mutates and returns all_quotes for convenience.
    """
    if not eod_snapshot:
        return all_quotes

    filled = 0

    # Mode 2: all_quotes is empty — create entries from strikes_data + snapshot
    if not all_quotes:
        for strike_val, data in strikes_data.items():
            snap_strike = Decimal(str(int(strike_val)))
            # Try exact match, then with .00
            snap = eod_snapshot.get(snap_strike)
            if not snap:
                snap_strike_dec = Decimal(f"{int(strike_val)}.00")
                snap = eod_snapshot.get(snap_strike_dec)
            if not snap:
                continue

            for side in ("ce", "pe"):
                inst = data.get(side)
                if not inst:
                    continue
                symbol_key = f"NFO:{inst['tradingsymbol']}"
                ltp = float(snap.get(f"{side}_ltp", 0))
                all_quotes[symbol_key] = {
                    "last_price": ltp,
                    "oi": snap.get(f"{side}_oi", 0),
                    "volume": snap.get(f"{side}_volume", 0),
                    "ohlc": {"open": 0, "high": 0, "low": 0, "close": ltp},
                    "depth": {"buy": [], "sell": []},
                }
                filled += 1
        logger.info(f"[EOD] Created {filled} quote entries from snapshot (all_quotes was empty)")
        return all_quotes

    # Mode 1: all_quotes has entries — fill zero-OI entries from snapshot
    for key, quote in all_quotes.items():
        if quote.get("oi", 0) != 0:
            continue

        symbol = key.split(":")[-1] if ":" in key else key
        opt_type = symbol[-2:].upper()
        if opt_type not in ("CE", "PE"):
            continue

        matched_strike = None
        for snap_strike in eod_snapshot:
            strike_int = int(snap_strike)
            if symbol.endswith(f"{strike_int}{opt_type}"):
                matched_strike = snap_strike
                break

        if matched_strike is None:
            continue

        snap = eod_snapshot[matched_strike]
        if opt_type == "CE":
            quote["oi"] = snap.get("ce_oi", 0)
            quote["volume"] = snap.get("ce_volume", 0)
        elif opt_type == "PE":
            quote["oi"] = snap.get("pe_oi", 0)
            quote["volume"] = snap.get("pe_volume", 0)
        filled += 1

    logger.info(f"[EOD] Filled {filled}/{len(all_quotes)} quote entries from snapshot")
    return all_quotes


def calculate_iv(option_price: float, spot: float, strike: float,
                 days_to_expiry: int, is_call: bool) -> float:
    """Calculate Implied Volatility using Newton-Raphson method"""
    if days_to_expiry <= 0 or option_price <= 0 or spot <= 0 or strike <= 0:
        return 0.0

    T = days_to_expiry / 365.0
    r = RISK_FREE_RATE

    # Initial guess
    sigma = 0.3
    converged = False

    def norm_cdf(x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def norm_pdf(x):
        return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)

    for _ in range(100):  # Max iterations
        try:
            d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            if is_call:
                price = spot * norm_cdf(d1) - strike * math.exp(-r * T) * norm_cdf(d2)
            else:
                price = strike * math.exp(-r * T) * norm_cdf(-d2) - spot * norm_cdf(-d1)

            vega = spot * math.sqrt(T) * norm_pdf(d1)

            if vega < 1e-10:
                break

            diff = option_price - price
            if abs(diff) < 0.01:
                converged = True
                break

            sigma += diff / vega
            sigma = max(0.01, min(sigma, 5.0))  # Bound sigma
        except (ValueError, ZeroDivisionError):
            break

    # If the algorithm never converged (e.g. deep ITM where IV is meaningless),
    # return 0.0 to indicate IV is unavailable rather than the min-bound artifact (1.0).
    if not converged:
        return 0.0

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


def _build_chain_from_live_snapshot(
    snap: dict,
    underlying: str,
    expiry: str,
    expiry_date: date,
    spot_price: float,
) -> dict:
    """Build an option chain response from a live engine snapshot.

    Skips all broker API calls — uses in-memory LTP/OI/volume from ticker feed.
    Still computes IV/Greeks via vectorized batch (fast, ~1-5ms for 50 strikes).
    """
    today = date.today()
    days_to_expiry = (expiry_date - today).days

    # Group snapshot tokens by strike
    strikes_data: dict[float, dict] = {}
    for _tok, entry in snap["tokens"].items():
        strike = float(entry["strike"])
        if strike not in strikes_data:
            strikes_data[strike] = {"strike": strike, "ce": None, "pe": None}

        side = entry["side"].lower()
        ltp = float(entry["ltp"]) if entry["ltp"] else 0
        strikes_data[strike][side] = {
            "instrument_token": _tok,
            "tradingsymbol": entry["tradingsymbol"],
            "ltp": ltp,
            "oi": entry["oi"],
            "volume": entry["volume"],
        }

    sorted_strikes = sorted(strikes_data.keys())
    atm_strike = min(sorted_strikes, key=lambda x: abs(x - spot_price)) if sorted_strikes else spot_price

    # Vectorized IV/Greeks
    _vec_entries = []
    for _s in sorted_strikes:
        _d = strikes_data[_s]
        for _side, _is_call in [("ce", True), ("pe", False)]:
            if _d[_side] and _d[_side]["ltp"] > 0:
                if spot_price and abs(spot_price - _s) / spot_price > FAR_OTM_MONEYNESS_THRESHOLD:
                    continue
                _vec_entries.append((_s, _side, _d[_side]["ltp"], _is_call))

    _vec_results = {}
    if _vec_entries and days_to_expiry > 0:
        _prices = np.array([e[2] for e in _vec_entries])
        _strikes_arr = np.array([e[0] for e in _vec_entries], dtype=float)
        _is_call_arr = np.array([e[3] for e in _vec_entries])
        _batch = calculate_iv_and_greeks_batch(_prices, spot_price, _strikes_arr, days_to_expiry, _is_call_arr)
        for i, (_s, _side, _ltp, _is_call) in enumerate(_vec_entries):
            _vec_results[(_s, _side)] = {
                "iv": float(_batch["iv"][i]),
                "delta": float(_batch["delta"][i]),
                "gamma": float(_batch["gamma"][i]),
                "theta": float(_batch["theta"][i]),
                "vega": float(_batch["vega"][i]),
            }

    # Build response rows
    option_chain = []
    total_ce_oi = 0
    total_pe_oi = 0
    max_pain_data = {}

    for strike in sorted_strikes:
        data = strikes_data[strike]
        row = {
            "strike": strike,
            "is_atm": strike == atm_strike,
            "is_itm_ce": strike < spot_price,
            "is_itm_pe": strike > spot_price,
            "ce": None,
            "pe": None,
        }

        for side, is_call, field in [("ce", True, "ce"), ("pe", False, "pe")]:
            sd = data[side]
            if not sd:
                continue
            ltp = sd["ltp"]
            oi = sd["oi"]
            volume = sd["volume"]

            vr = _vec_results.get((strike, side))
            if vr:
                greeks = {"iv": vr["iv"], "delta": vr["delta"], "gamma": vr["gamma"], "theta": vr["theta"], "vega": vr["vega"]}
            else:
                greeks = {"iv": 0.0, "delta": 0, "gamma": 0, "theta": 0, "vega": 0}

            row[field] = {
                "instrument_token": sd["instrument_token"],
                "tradingsymbol": sd["tradingsymbol"],
                "ltp": ltp,
                "change": 0,
                "change_pct": 0,
                "bid": 0,
                "ask": 0,
                "oi": oi,
                "volume": volume,
                **greeks,
            }

            if side == "ce":
                total_ce_oi += oi
            else:
                total_pe_oi += oi

        max_pain_data[strike] = {
            "ce_oi": row["ce"]["oi"] if row["ce"] else 0,
            "pe_oi": row["pe"]["oi"] if row["pe"] else 0,
        }
        option_chain.append(row)

    max_pain = calculate_max_pain(max_pain_data, spot_price)
    pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0

    return {
        "underlying": underlying,
        "expiry": expiry,
        "spot_price": spot_price,
        "days_to_expiry": days_to_expiry,
        "lot_size": LOT_SIZES.get(underlying, 75),
        "data_freshness": "LIVE_ENGINE",
        "chain": option_chain,
        "summary": {
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "pcr": pcr,
            "max_pain": max_pain,
            "atm_strike": atm_strike,
        },
    }


async def _compute_option_chain(
    underlying: str,
    expiry: str,
    expiry_date: date,
    user: Optional[User],
    db: AsyncSession,
) -> dict:
    """Core option chain computation — extracted for cacheability.

    Called directly by the route handler (with user) and by the background
    prefetch service (user=None, uses platform adapter only).
    """
    # ── FAST PATH: Live Engine snapshot (market hours only) ───────────────
    # If WebSocket ticks are flowing and the engine has a fresh snapshot,
    # skip all broker API calls and serve from memory.
    if is_market_open():
        try:
            engine = OptionChainLiveEngine.get_instance()
            live_snap = engine.get_fresh_snapshot(underlying, expiry)
            if live_snap:
                # Still need spot price — try quick platform adapter call
                spot = 0.0
                try:
                    pa = await get_cached_platform_adapter(db)
                    if pa:
                        prices = await pa.get_best_price([underlying])
                        spot = float(prices.get(underlying, 0))
                except Exception:
                    pass
                if spot > 0:
                    logger.info(
                        "[OptionChain] LIVE ENGINE HIT — %s:%s (%d ticks, %.1fs old)",
                        underlying, expiry, live_snap["tick_count"],
                        __import__("time").monotonic() - live_snap["last_tick_at"],
                    )
                    return _build_chain_from_live_snapshot(
                        live_snap, underlying, expiry, expiry_date, spot,
                    )
        except Exception as e:
            logger.debug("[OptionChain] Live engine check failed: %s", e)

    # ── STANDARD PATH: Broker API calls ──────────────────────────────────
    # Get market data adapter
    adapter = None
    if not is_market_open():
        # After hours: use cached platform singleton (no per-user adapter needed)
        try:
            adapter = await get_cached_platform_adapter(db)
        except Exception as e:
            logger.warning(f"[OptionChain] Platform adapter failed: {e}")
    else:
        # During market: try user adapter, fall back to platform singleton
        if user:
            try:
                adapter = await get_user_market_data_adapter(user.id, db)
            except Exception as user_adapter_err:
                logger.warning(
                    f"[OptionChain] User adapter init failed ({user_adapter_err}), "
                    "falling back to platform adapter"
                )
        if adapter is None:
            try:
                adapter = await get_cached_platform_adapter(db)
            except Exception:
                pass

    lot_size = LOT_SIZES.get(underlying, 1)

    spot_price = 0.0

    # When market is closed, try NSE EOD snapshot first — brokers may have expired tokens
    if not is_market_open():
        try:
            snapshot_svc = EODSnapshotService()
            _eod_spot = await snapshot_svc.get_snapshot(underlying, expiry_date, db)
            if _eod_spot:
                first_row = await snapshot_svc._load_from_db(underlying, expiry_date, db)
                if first_row and first_row[0].spot_price:
                    spot_price = float(first_row[0].spot_price)
                    logger.info(f"[OptionChain] Got spot price from EOD snapshot: {spot_price}")
        except Exception as eod_err:
            logger.warning(f"[OptionChain] EOD snapshot spot price failed: {eod_err}")

    # If no EOD spot, try broker adapters in parallel for speed
    if not spot_price:
        spot_tasks = {}
        if adapter:
            spot_tasks["user"] = adapter.get_best_price([underlying])
        try:
            platform_adapter = await get_cached_platform_adapter(db)
            if platform_adapter and platform_adapter is not adapter:
                spot_tasks["platform"] = platform_adapter.get_best_price([underlying])
        except Exception:
            pass

        if spot_tasks:
            labels = list(spot_tasks.keys())
            results = await asyncio.gather(*spot_tasks.values(), return_exceptions=True)
            for label, result in zip(labels, results):
                if isinstance(result, Exception):
                    logger.warning(f"[OptionChain] {label} adapter get_best_price failed: {result}")
                    continue
                price = float(result.get(underlying, 0))
                if price > 0:
                    spot_price = price
                    if label == "platform":
                        adapter = platform_adapter
                    logger.info(f"[OptionChain] Got spot from {label} adapter: {spot_price}")
                    break

    # Last resort: fetch from NSE directly if no cached snapshot exists
    if not spot_price and not is_market_open():
        try:
            from app.services.options.nse_fetcher import NSEFetcher
            fetcher = NSEFetcher()
            nse_data = await fetcher.fetch_option_chain(underlying, expiry_date)
            spot_price = float(nse_data["spot_price"])
            snapshot_svc = EODSnapshotService()
            await snapshot_svc._store_snapshot(underlying, expiry_date, nse_data, db)
            logger.info(f"[OptionChain] Got spot price from live NSE fetch: {spot_price}")
        except Exception as nse_err:
            logger.warning(f"[OptionChain] NSE live fetch for spot price failed: {nse_err}")

    if not spot_price:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not get spot price for {underlying} — market data unavailable",
        )

    # Get instruments for this expiry from DB
    from app.services.brokers.market_data.instrument_query import get_nfo_instruments
    broker_type = adapter.broker_type if adapter else "smartapi"
    db_instruments = await get_nfo_instruments(db, underlying, expiry_date, broker_type=broker_type)

    logger.info(f"[OptionChain] DB query returned {len(db_instruments)} instruments for {underlying} expiry {expiry_date}")

    if not db_instruments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No instruments found for {underlying} expiry {expiry_date}"
        )

    class _Inst:
        __slots__ = ("instrument_token", "canonical_symbol", "lot_size", "strike", "option_type")
        def __init__(self, token, symbol, lot, strike, opt_type):
            self.instrument_token = token
            self.canonical_symbol = symbol
            self.lot_size = lot
            self.strike = strike
            self.option_type = opt_type

    instruments = [
        _Inst(
            token=inst.instrument_token,
            symbol=inst.tradingsymbol,
            lot=inst.lot_size,
            strike=inst.strike,
            opt_type=inst.instrument_type,
        )
        for inst in db_instruments
    ]

    logger.info(f"[OptionChain] Found {len(instruments)} instruments for {underlying}")

    # --- PERFORMANCE FIX: filter to ATM ± range before fetching quotes ---
    QUOTE_FETCH_RANGE = 25

    all_strikes_sorted = sorted(set(float(inst.strike) for inst in instruments if hasattr(inst, 'strike') and inst.strike))
    if all_strikes_sorted and spot_price:
        atm_for_filter = min(all_strikes_sorted, key=lambda x: abs(x - spot_price))
        atm_idx_for_filter = all_strikes_sorted.index(atm_for_filter)
        start_idx = max(0, atm_idx_for_filter - QUOTE_FETCH_RANGE)
        end_idx = min(len(all_strikes_sorted), atm_idx_for_filter + QUOTE_FETCH_RANGE + 1)
        strikes_to_fetch = set(all_strikes_sorted[start_idx:end_idx])
        instruments_for_quotes = [inst for inst in instruments if float(inst.strike) in strikes_to_fetch]
        logger.info(f"[OptionChain] Filtered {len(instruments)} instruments to {len(instruments_for_quotes)} near ATM {atm_for_filter} for quote fetch")
    else:
        instruments_for_quotes = instruments

    # Organize by strike and collect tokens for quote fetch
    strikes_data = {}
    token_to_symbol = {}

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

        if inst.option_type == "CE":
            strikes_data[strike]["ce"] = inst_data
        else:
            strikes_data[strike]["pe"] = inst_data

    for inst in instruments_for_quotes:
        if inst.instrument_token:
            token_to_symbol[str(inst.instrument_token)] = inst.canonical_symbol

    logger.info(f"[OptionChain] Organized {len(strikes_data)} strikes, fetching quotes for {len(token_to_symbol)} instruments")

    # ── PRIMARY PATH: adapter-specific option chain fetch ─────────────────
    all_quotes = {}
    canonical_symbols = list(token_to_symbol.values())

    # PATH 1: Upstox dedicated option chain endpoint
    if adapter and hasattr(adapter, 'get_option_chain_quotes'):
        try:
            import time as _time
            oc_start = _time.time()
            all_quotes = await adapter.get_option_chain_quotes(underlying, expiry, token_to_symbol=token_to_symbol)
            logger.info(
                f"[OptionChain] Upstox option chain: {len(all_quotes)} contracts "
                f"in {_time.time()-oc_start:.1f}s"
            )
        except Exception as e:
            logger.warning(f"[OptionChain] Upstox option chain failed, falling back: {e}")
            all_quotes = {}

    # PATH 2: SmartAPI WebSocket V2 snap
    ws_quotes = {}
    if not all_quotes and adapter and hasattr(adapter, 'get_option_chain_snap') and token_to_symbol:
        try:
            import time as _time
            ws_start = _time.time()
            ws_quotes = await adapter.get_option_chain_snap(
                canonical_symbols=[],
                timeout=7.0,
                token_to_symbol=token_to_symbol,
            )
            logger.info(
                f"[OptionChain] WebSocket snap: {len(ws_quotes)}/{len(token_to_symbol)} "
                f"in {_time.time()-ws_start:.1f}s"
            )
        except Exception as e:
            logger.warning(f"[OptionChain] WebSocket snap failed, falling back to REST: {e}")

    if ws_quotes:
        for canonical_symbol, tick in ws_quotes.items():
            symbol_key = f"NFO:{canonical_symbol}"
            all_quotes[symbol_key] = {
                "last_price": tick["ltp"],
                "oi": tick["oi"],
                "volume": tick["volume"],
                "ohlc": {
                    "open": tick["open"],
                    "high": tick["high"],
                    "low": tick["low"],
                    "close": tick["close"],
                },
                "depth": {"buy": [], "sell": []},
            }

    # PATH 3: Batched REST get_quote() fallback
    if not all_quotes and adapter:
        for i in range(0, len(canonical_symbols), 100):
            batch_symbols = canonical_symbols[i:i+100]
            if not batch_symbols:
                continue
            try:
                unified_quotes = await adapter.get_quote(batch_symbols)
                for canonical_symbol, uq in unified_quotes.items():
                    symbol_key = f"NFO:{canonical_symbol}"
                    all_quotes[symbol_key] = {
                        "last_price": float(uq.last_price),
                        "oi": uq.oi,
                        "volume": uq.volume,
                        "ohlc": {
                            "open": float(uq.open),
                            "high": float(uq.high),
                            "low": float(uq.low),
                            "close": float(uq.close),
                        },
                        "depth": {
                            "buy": [{"price": float(uq.bid_price), "quantity": uq.bid_quantity}] if uq.bid_price else [],
                            "sell": [{"price": float(uq.ask_price), "quantity": uq.ask_quantity}] if uq.ask_price else [],
                        },
                    }
            except Exception as e:
                logger.warning(f"[OptionChain] Quote batch failed: {e}")
                continue

    logger.info(f"[OptionChain] Fetched quotes for {len(all_quotes)}/{len(list(token_to_symbol.values()))} instruments")

    # EOD Snapshot fallback: when market is closed and broker OI is all zeros
    eod_snapshot = None
    use_eod = False
    if not is_market_open() and _should_use_eod_snapshot(all_quotes):
        try:
            snapshot_svc = EODSnapshotService()
            eod_snapshot = await snapshot_svc.get_snapshot(underlying, expiry_date, db)
            if eod_snapshot:
                all_quotes = _apply_eod_fallback(
                    all_quotes, eod_snapshot, strikes_data,
                )
                use_eod = True
                logger.info(f"[OptionChain] Applied EOD snapshot fallback ({len(eod_snapshot)} strikes)")
        except Exception as e:
            logger.warning(f"[OptionChain] EOD snapshot failed: {e}")

    if not strikes_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No option strikes found for this expiry"
        )

    today = date.today()
    days_to_expiry = (expiry_date - today).days

    option_chain = []
    total_ce_oi = 0
    total_pe_oi = 0
    max_pain_data = {}

    sorted_strikes = sorted(strikes_data.keys())
    atm_strike = min(sorted_strikes, key=lambda x: abs(x - spot_price)) if sorted_strikes else spot_price

    # --- Vectorized IV+Greeks pre-compute for strikes needing local calculation ---
    # Collect all options that need local IV (not Upstox-provided, not far-OTM)
    _vec_entries = []  # (strike, side, ltp) for vectorized batch
    for _s in sorted_strikes:
        _d = strikes_data[_s]
        for _side, _is_call in [("ce", True), ("pe", False)]:
            if _d[_side]:
                _sym = f"NFO:{_d[_side]['tradingsymbol']}"
                _q = all_quotes.get(_sym, {})
                _ltp = _q.get("last_price", 0) or _q.get("ohlc", {}).get("close", 0)
                _upstox_g = _q.get("greeks")
                # Skip if Upstox provides Greeks, or far OTM, or zero LTP
                if _upstox_g and _upstox_g.get("iv"):
                    continue
                if spot_price and abs(spot_price - _s) / spot_price > FAR_OTM_MONEYNESS_THRESHOLD:
                    continue
                if _ltp > 0:
                    _vec_entries.append((_s, _side, _ltp, _is_call))

    _vec_results = {}  # key: (strike, side) -> {"iv": float, "delta": ..., ...}
    if _vec_entries and days_to_expiry > 0:
        _prices = np.array([e[2] for e in _vec_entries])
        _strikes_arr = np.array([e[0] for e in _vec_entries], dtype=float)
        _is_call_arr = np.array([e[3] for e in _vec_entries])
        _batch = calculate_iv_and_greeks_batch(_prices, spot_price, _strikes_arr, days_to_expiry, _is_call_arr)
        for i, (_s, _side, _ltp, _is_call) in enumerate(_vec_entries):
            _vec_results[(_s, _side)] = {
                "iv": float(_batch["iv"][i]),
                "delta": float(_batch["delta"][i]),
                "gamma": float(_batch["gamma"][i]),
                "theta": float(_batch["theta"][i]),
                "vega": float(_batch["vega"][i]),
            }
    # --- End vectorized pre-compute ---

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
            if not ce_ltp and ce_close:
                ce_ltp = ce_close
            ce_change = ce_ltp - ce_close if ce_close else 0
            ce_change_pct = (ce_change / ce_close * 100) if ce_close else 0

            ce_depth = ce_quote.get("depth", {})
            ce_bid = ce_depth.get("buy", [{}])[0].get("price", 0) if ce_depth.get("buy") else 0
            ce_ask = ce_depth.get("sell", [{}])[0].get("price", 0) if ce_depth.get("sell") else 0

            ce_upstox_greeks = ce_quote.get("greeks")
            if ce_upstox_greeks and ce_upstox_greeks.get("iv"):
                ce_iv = ce_upstox_greeks["iv"]
                ce_greeks = {
                    "delta": round(ce_upstox_greeks.get("delta", 0), 4),
                    "gamma": round(ce_upstox_greeks.get("gamma", 0), 6),
                    "theta": round(ce_upstox_greeks.get("theta", 0), 2),
                    "vega": round(ce_upstox_greeks.get("vega", 0), 2),
                }
            elif spot_price and abs(spot_price - strike) / spot_price > FAR_OTM_MONEYNESS_THRESHOLD:
                ce_iv = 0.0
                ce_greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
            elif (strike, "ce") in _vec_results:
                _vr = _vec_results[(strike, "ce")]
                ce_iv = _vr["iv"]
                ce_greeks = {"delta": _vr["delta"], "gamma": _vr["gamma"], "theta": _vr["theta"], "vega": _vr["vega"]}
            else:
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
            if not pe_ltp and pe_close:
                pe_ltp = pe_close
            pe_change = pe_ltp - pe_close if pe_close else 0
            pe_change_pct = (pe_change / pe_close * 100) if pe_close else 0

            pe_depth = pe_quote.get("depth", {})
            pe_bid = pe_depth.get("buy", [{}])[0].get("price", 0) if pe_depth.get("buy") else 0
            pe_ask = pe_depth.get("sell", [{}])[0].get("price", 0) if pe_depth.get("sell") else 0

            pe_upstox_greeks = pe_quote.get("greeks")
            if pe_upstox_greeks and pe_upstox_greeks.get("iv"):
                pe_iv = pe_upstox_greeks["iv"]
                pe_greeks = {
                    "delta": round(pe_upstox_greeks.get("delta", 0), 4),
                    "gamma": round(pe_upstox_greeks.get("gamma", 0), 6),
                    "theta": round(pe_upstox_greeks.get("theta", 0), 2),
                    "vega": round(pe_upstox_greeks.get("vega", 0), 2),
                }
            elif spot_price and abs(spot_price - strike) / spot_price > FAR_OTM_MONEYNESS_THRESHOLD:
                pe_iv = 0.0
                pe_greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
            elif (strike, "pe") in _vec_results:
                _vr = _vec_results[(strike, "pe")]
                pe_iv = _vr["iv"]
                pe_greeks = {"delta": _vr["delta"], "gamma": _vr["gamma"], "theta": _vr["theta"], "vega": _vr["vega"]}
            else:
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

        max_pain_data[strike] = {
            "ce_oi": row["ce"]["oi"] if row["ce"] else 0,
            "pe_oi": row["pe"]["oi"] if row["pe"] else 0
        }

        option_chain.append(row)

    max_pain = calculate_max_pain(max_pain_data, spot_price)
    pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0

    # ── Register with Live Engine for future fast-path hits ──────────────
    if is_market_open() and instruments_for_quotes:
        try:
            engine = OptionChainLiveEngine.get_instance()
            engine_tokens = [
                {
                    "token": int(inst.instrument_token),
                    "strike": float(inst.strike),
                    "side": inst.option_type,
                    "tradingsymbol": inst.canonical_symbol,
                }
                for inst in instruments_for_quotes
                if inst.instrument_token
            ]
            if engine_tokens:
                engine.register_chain(underlying, expiry, engine_tokens)
                engine.cleanup_idle()
        except Exception as e:
            logger.debug("[OptionChain] Live engine registration failed: %s", e)

    return {
        "underlying": underlying,
        "expiry": expiry,
        "spot_price": spot_price,
        "days_to_expiry": days_to_expiry,
        "lot_size": LOT_SIZES.get(underlying, 75),
        "data_freshness": "EOD_SNAPSHOT" if use_eod else get_data_freshness(),
        "chain": option_chain,
        "summary": {
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "pcr": pcr,
            "max_pain": max_pain,
            "atm_strike": atm_strike
        }
    }


@router.get("/chain")
async def get_option_chain(
    underlying: str = Query(..., description="NIFTY, BANKNIFTY, or FINNIFTY"),
    expiry: str = Query(..., description="Expiry date in YYYY-MM-DD format"),
    user: User = Depends(get_current_user),
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

        async def compute():
            return await _compute_option_chain(underlying, expiry, expiry_date, user, db)

        result = await get_or_compute(underlying, expiry, compute)

        # Trigger background prefetch on first after-hours request
        if not is_market_open():
            from app.services.options.option_chain_prefetch import trigger_prefetch_if_needed
            asyncio.create_task(trigger_prefetch_if_needed())

        return result

    except HTTPException:
        raise
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
    db: AsyncSession = Depends(get_db)
):
    """
    Get OI analysis data for charts.

    Returns simplified OI data for visualization.
    """
    chain_data = await get_option_chain(underlying, expiry, user, db)

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
    db: AsyncSession = Depends(get_db)
):
    """
    Find option strike by target delta.

    Searches for the strike with delta closest to the target value.
    Optionally prefers round strikes (divisible by 100).
    """
    try:
        adapter = await get_user_market_data_adapter(user.id, db)
        strike_finder = StrikeFinderService(adapter, db)

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find strike by delta: {str(e)}"
        )


@router.post("/find-by-premium", response_model=StrikeFindResponse)
async def find_strike_by_premium(
    request: StrikeFindByPremiumRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Find option strike by target premium (LTP).

    Searches for the strike with premium closest to the target value.
    Optionally prefers round strikes (divisible by 100).
    """
    try:
        adapter = await get_user_market_data_adapter(user.id, db)
        strike_finder = StrikeFinderService(adapter, db)

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find strike by premium: {str(e)}"
        )
