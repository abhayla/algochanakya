"""Broker-agnostic failover for option chain quote fetches.

Iterates ``ORG_ACTIVE_BROKERS`` in order, creates an adapter for each, and
runs the 3-path quote-fetch flow (Upstox dedicated option chain / SmartAPI
WebSocket snap / generic REST get_quote). Stops at the first adapter that
returns a non-empty quote dict. Auth errors are escalated to
``HealthMonitor.record_auth_failure`` via the ``auth_tracking`` wrapper so
the pool-level ``FailoverController`` can react too.

Route callers use this to recover silently when the active broker's
credentials are expired — as happened on 2026-04-17 with platform SmartAPI.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Awaitable, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brokers.market_data.auth_tracking import (
    call_adapter_with_auth_tracking,
)
from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    BrokerAPIError,
)
from app.services.brokers.market_data.instrument_query import (
    get_nfo_instruments,
)
from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
)

logger = logging.getLogger(__name__)


# Maps ORG_ACTIVE_BROKERS DB names → factory broker_type strings.
# Kept here (in addition to websocket.py's copy) so that this module has a
# minimal import footprint — the route layer already imports this module.
_DB_NAME_TO_BROKER_TYPE: Dict[str, str] = {
    "angelone": "smartapi",
    "zerodha": "kite",
    "kite": "kite",
    "upstox": "upstox",
    "dhan": "dhan",
    "fyers": "fyers",
    "paytm": "paytm",
}


# Default adapter factory signature: `(broker_type, user_id, db) -> adapter`.
AdapterFactory = Callable[..., Awaitable[MarketDataBrokerAdapter]]


async def _default_adapter_factory(
    broker_type: str, user_id: Optional[UUID], db: AsyncSession
) -> MarketDataBrokerAdapter:
    # Deferred import to keep this module cheap when mocked in tests.
    from app.services.brokers.market_data.factory import get_market_data_adapter

    return await get_market_data_adapter(broker_type, user_id, db)


def _iter_active_broker_types() -> List[str]:
    """Read ORG_ACTIVE_BROKERS lazily so tests can monkeypatch it."""
    from app.constants.brokers import ORG_ACTIVE_BROKERS

    ordered: List[str] = []
    for db_name in ORG_ACTIVE_BROKERS:
        broker_type = _DB_NAME_TO_BROKER_TYPE.get(db_name)
        if broker_type and broker_type not in ordered:
            ordered.append(broker_type)
    return ordered


async def _build_token_to_symbol(
    adapter: MarketDataBrokerAdapter,
    underlying: str,
    expiry_date: date,
    db: AsyncSession,
) -> Tuple[Dict[str, str], List[str]]:
    """Look up the broker's preferred instruments and build the token-to-
    symbol dict expected by the 3 quote-fetch paths.

    Returns (token_to_symbol, canonical_symbols).
    """
    instruments = await get_nfo_instruments(
        db, underlying, expiry_date, broker_type=adapter.broker_type
    )
    token_to_symbol: Dict[str, str] = {}
    canonical_symbols: List[str] = []
    for inst in instruments:
        if inst.option_type not in ("CE", "PE"):
            continue
        if not inst.instrument_token:
            continue
        token_to_symbol[str(inst.instrument_token)] = inst.tradingsymbol
        canonical_symbols.append(inst.tradingsymbol)
    return token_to_symbol, canonical_symbols


async def _try_path1_upstox_option_chain(
    adapter: MarketDataBrokerAdapter,
    underlying: str,
    expiry_str: str,
    token_to_symbol: Dict[str, str],
    health_monitor,
) -> Dict[str, Dict]:
    if not hasattr(adapter, "get_option_chain_quotes"):
        return {}
    coro = adapter.get_option_chain_quotes(
        underlying, expiry_str, token_to_symbol=token_to_symbol
    )
    return await call_adapter_with_auth_tracking(
        adapter.broker_type, coro, health_monitor
    )


async def _try_path2_smartapi_snap(
    adapter: MarketDataBrokerAdapter,
    token_to_symbol: Dict[str, str],
    health_monitor,
) -> Dict[str, Dict]:
    if not hasattr(adapter, "get_option_chain_snap") or not token_to_symbol:
        return {}
    coro = adapter.get_option_chain_snap(
        canonical_symbols=[], timeout=7.0, token_to_symbol=token_to_symbol
    )
    ws_quotes = await call_adapter_with_auth_tracking(
        adapter.broker_type, coro, health_monitor
    )
    normalised: Dict[str, Dict] = {}
    for canonical_symbol, tick in (ws_quotes or {}).items():
        normalised[f"NFO:{canonical_symbol}"] = {
            "last_price": tick.get("ltp", 0),
            "oi": tick.get("oi", 0),
            "volume": tick.get("volume", 0),
            "ohlc": {
                "open": tick.get("open", 0),
                "high": tick.get("high", 0),
                "low": tick.get("low", 0),
                "close": tick.get("close", 0),
            },
            "depth": {"buy": [], "sell": []},
        }
    return normalised


async def _try_path3_rest_get_quote(
    adapter: MarketDataBrokerAdapter,
    canonical_symbols: List[str],
    health_monitor,
) -> Dict[str, Dict]:
    if not hasattr(adapter, "get_quote") or not canonical_symbols:
        return {}
    all_quotes: Dict[str, Dict] = {}
    # SmartAPI getMarketData caps at 50 symbols per request (AB4029 otherwise).
    # Other adapters tolerate the smaller batch, so use 50 uniformly.
    for i in range(0, len(canonical_symbols), 50):
        batch = canonical_symbols[i : i + 50]
        if not batch:
            continue
        try:
            coro = adapter.get_quote(batch)
            unified = await call_adapter_with_auth_tracking(
                adapter.broker_type, coro, health_monitor
            )
        except (AuthenticationError, BrokerAPIError):
            # Auth failures already recorded; propagate up so the caller can
            # failover to the next broker instead of issuing more batches.
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[failover_fetch] %s get_quote batch failed: %s",
                adapter.broker_type,
                exc,
            )
            continue
        for canonical_symbol, uq in (unified or {}).items():
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
                    "buy": (
                        [{"price": float(uq.bid_price), "quantity": uq.bid_quantity}]
                        if uq.bid_price
                        else []
                    ),
                    "sell": (
                        [{"price": float(uq.ask_price), "quantity": uq.ask_quantity}]
                        if uq.ask_price
                        else []
                    ),
                },
            }
    return all_quotes


async def _fetch_quotes_via_single_adapter(
    adapter: MarketDataBrokerAdapter,
    underlying: str,
    expiry_str: str,
    expiry_date: date,
    db: AsyncSession,
    health_monitor,
) -> Dict[str, Dict]:
    """Try the 3-path fetch flow against one adapter. Raises on auth error
    so the outer caller can move to the next broker."""
    token_to_symbol, canonical_symbols = await _build_token_to_symbol(
        adapter, underlying, expiry_date, db
    )
    if not token_to_symbol:
        return {}

    all_quotes = await _try_path1_upstox_option_chain(
        adapter, underlying, expiry_str, token_to_symbol, health_monitor
    )
    if all_quotes:
        return all_quotes

    all_quotes = await _try_path2_smartapi_snap(
        adapter, token_to_symbol, health_monitor
    )
    if all_quotes:
        return all_quotes

    return await _try_path3_rest_get_quote(
        adapter, canonical_symbols, health_monitor
    )


async def fetch_option_chain_quotes_with_failover(
    *,
    underlying: str,
    expiry_str: str,
    expiry_date: date,
    user_id: Optional[UUID],
    db: AsyncSession,
    health_monitor,
    adapter_factory: Optional[AdapterFactory] = None,
    skip_broker_types: Optional[List[str]] = None,
) -> Tuple[Optional[MarketDataBrokerAdapter], Dict[str, Dict]]:
    """Iterate ORG_ACTIVE_BROKERS and return quotes from the first healthy
    broker.

    Returns (adapter, all_quotes). If no broker produces quotes,
    returns (None, {}). Callers then decide whether to fall back to EOD.

    ``skip_broker_types``: brokers the caller already tried (e.g. the primary
    adapter from the hot path). Avoids duplicate work when the helper is
    used as a fallback.
    """
    factory: AdapterFactory = adapter_factory or _default_adapter_factory
    broker_types = _iter_active_broker_types()
    skip = set(skip_broker_types or [])

    for broker_type in broker_types:
        if broker_type in skip:
            continue
        # Step 1: create adapter. Auth errors here mean "credentials missing"
        # — record and move on.
        try:
            adapter = await factory(broker_type, user_id, db)
        except AuthenticationError as exc:
            logger.warning(
                "[failover_fetch] adapter %s not available: %s",
                broker_type,
                exc,
            )
            if health_monitor is not None:
                from app.services.brokers.market_data.auth_tracking import (
                    _extract_error_code,
                )

                code = _extract_error_code(str(exc)) or "CREDENTIALS_MISSING"
                try:
                    await health_monitor.record_auth_failure(
                        broker_type, code, str(exc)
                    )
                except Exception:  # noqa: BLE001
                    pass
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[failover_fetch] adapter %s creation failed: %s",
                broker_type,
                exc,
            )
            continue

        # Step 2: run the 3-path fetch flow.
        try:
            all_quotes = await _fetch_quotes_via_single_adapter(
                adapter, underlying, expiry_str, expiry_date, db, health_monitor
            )
        except (AuthenticationError, BrokerAPIError) as exc:
            logger.warning(
                "[failover_fetch] %s auth-class failure — failing over: %s",
                broker_type,
                exc,
            )
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[failover_fetch] %s unexpected failure — failing over: %s",
                broker_type,
                exc,
            )
            continue

        if all_quotes:
            logger.info(
                "[failover_fetch] %s returned %d quotes (stopping failover)",
                broker_type,
                len(all_quotes),
            )
            return adapter, all_quotes

        logger.info(
            "[failover_fetch] %s returned empty quotes — trying next broker",
            broker_type,
        )

    return None, {}
