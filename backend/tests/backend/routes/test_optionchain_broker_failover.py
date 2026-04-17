"""Tests for route-level broker failover — Phase 3 (TDD Red).

Covers the broker-agnostic helper
``app.services.brokers.market_data.failover_fetch.fetch_option_chain_quotes_with_failover``
that iterates ORG_ACTIVE_BROKERS, tries the 3-path quote fetch per broker,
and stops at the first adapter that returns non-empty quotes.

This is what unblocks the option chain when the active broker's credentials
are expired but a secondary broker (per ORG_ACTIVE_BROKERS) has valid creds.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    BrokerAPIError,
)


# ─── Fixtures ───────────────────────────────────────────────────────────────


def _make_adapter(broker_type: str, *, option_chain_result=None, snap_result=None,
                  quote_result=None, oc_raises=None, snap_raises=None, quote_raises=None):
    """Build a mock MarketDataBrokerAdapter with configurable behaviours.

    Uses ``spec=[...]`` so ``hasattr()`` only returns True for the methods
    actually configured — mirroring real adapters that either implement a
    path or don't.
    """
    spec = ["broker_type"]
    if oc_raises is not None or option_chain_result is not None:
        spec.append("get_option_chain_quotes")
    if snap_raises is not None or snap_result is not None:
        spec.append("get_option_chain_snap")
    if quote_raises is not None or quote_result is not None:
        spec.append("get_quote")

    adapter = MagicMock(spec=spec)
    adapter.broker_type = broker_type

    if oc_raises is not None:
        adapter.get_option_chain_quotes = AsyncMock(side_effect=oc_raises)
    elif option_chain_result is not None:
        adapter.get_option_chain_quotes = AsyncMock(return_value=option_chain_result)

    if snap_raises is not None:
        adapter.get_option_chain_snap = AsyncMock(side_effect=snap_raises)
    elif snap_result is not None:
        adapter.get_option_chain_snap = AsyncMock(return_value=snap_result)

    if quote_raises is not None:
        adapter.get_quote = AsyncMock(side_effect=quote_raises)
    elif quote_result is not None:
        adapter.get_quote = AsyncMock(return_value=quote_result)

    return adapter


def _fake_instrument(strike: float, option_type: str, expiry: date, token: int):
    """Emulate a row from the instruments table (what get_nfo_instruments returns)."""
    inst = MagicMock()
    inst.instrument_token = token
    inst.exchange_token = token
    inst.tradingsymbol = f"NIFTY2642120{int(strike)}{option_type}"
    inst.strike = Decimal(str(strike))
    inst.option_type = option_type
    inst.instrument_type = option_type
    inst.expiry = expiry
    inst.lot_size = 75
    return inst


@pytest.fixture
def fake_instruments():
    """5 strikes × 2 types = 10 NIFTY options for 2026-04-21."""
    exp = date(2026, 4, 21)
    out = []
    for i, strike in enumerate([24000, 24100, 24200, 24300, 24400]):
        out.append(_fake_instrument(strike, "CE", exp, 60000 + i * 2))
        out.append(_fake_instrument(strike, "PE", exp, 60001 + i * 2))
    return out


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_health_monitor():
    m = AsyncMock()
    m.record_auth_failure = AsyncMock()
    return m


@pytest.fixture(autouse=True)
def patch_org_active_brokers(monkeypatch):
    """Pin ORG_ACTIVE_BROKERS to a deterministic order across tests."""
    monkeypatch.setattr(
        "app.constants.brokers.ORG_ACTIVE_BROKERS",
        ["angelone", "upstox"],
    )


@pytest.fixture(autouse=True)
def patch_get_nfo_instruments(fake_instruments):
    """Return the same fake instruments regardless of broker_type."""
    with patch(
        "app.services.brokers.market_data.failover_fetch.get_nfo_instruments",
        new=AsyncMock(return_value=fake_instruments),
    ):
        yield


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestFailoverHappyPath:
    @pytest.mark.asyncio
    async def test_primary_success_returns_primary_quotes(
        self, mock_db, mock_health_monitor
    ):
        """Primary (smartapi) returns quotes → helper returns those, never
        tries secondary."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        primary = _make_adapter(
            "smartapi",
            snap_result={
                "NIFTY2642124200CE": {
                    "ltp": 123.45, "oi": 1000, "volume": 50,
                    "open": 120, "high": 125, "low": 118, "close": 122,
                }
            },
        )
        secondary_factory = AsyncMock()  # Should NOT be called

        async def factory(broker_type, *_args, **_kwargs):
            if broker_type == "smartapi":
                return primary
            return await secondary_factory(broker_type)

        adapter, quotes = await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert adapter is primary
        assert len(quotes) > 0
        secondary_factory.assert_not_awaited()
        mock_health_monitor.record_auth_failure.assert_not_awaited()


@pytest.mark.unit
class TestFailoverOnAuthError:
    @pytest.mark.asyncio
    async def test_primary_auth_error_skips_to_secondary(
        self, mock_db, mock_health_monitor
    ):
        """Primary raises AuthenticationError → record failure, try
        secondary; secondary returns non-empty → helper returns secondary's
        result."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        primary = _make_adapter(
            "smartapi",
            snap_raises=AuthenticationError("smartapi", "AG8001 Invalid Token"),
            quote_raises=AuthenticationError("smartapi", "AG8001 Invalid Token"),
        )
        secondary = _make_adapter(
            "upstox",
            option_chain_result={
                "NFO:NIFTY2642124200CE": {
                    "last_price": 99.99, "oi": 200, "volume": 10,
                    "ohlc": {"open": 100, "high": 102, "low": 98, "close": 101},
                    "depth": {"buy": [], "sell": []},
                }
            },
        )

        async def factory(broker_type, *_args, **_kwargs):
            return {"smartapi": primary, "upstox": secondary}[broker_type]

        adapter, quotes = await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert adapter is secondary
        assert len(quotes) > 0
        mock_health_monitor.record_auth_failure.assert_awaited()  # primary auth recorded

    @pytest.mark.asyncio
    async def test_broker_api_error_with_ag8001_escalates_and_failovers(
        self, mock_db, mock_health_monitor
    ):
        """SmartAPI logs show AG8001 wrapped in BrokerAPIError — helper must
        still treat it as an auth issue (via auth_tracking) and failover."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        primary = _make_adapter(
            "smartapi",
            snap_raises=BrokerAPIError("smartapi", "AG8001 Invalid Token"),
            quote_raises=BrokerAPIError("smartapi", "AG8001 Invalid Token"),
        )
        secondary = _make_adapter(
            "upstox",
            option_chain_result={
                "NFO:NIFTY2642124200CE": {
                    "last_price": 42.0, "oi": 100, "volume": 5,
                    "ohlc": {"open": 40, "high": 43, "low": 39, "close": 41},
                    "depth": {"buy": [], "sell": []},
                }
            },
        )

        async def factory(broker_type, *_args, **_kwargs):
            return {"smartapi": primary, "upstox": secondary}[broker_type]

        adapter, quotes = await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert adapter is secondary
        assert len(quotes) > 0
        mock_health_monitor.record_auth_failure.assert_awaited()


@pytest.mark.unit
class TestFailoverOnEmptyQuotes:
    @pytest.mark.asyncio
    async def test_primary_returns_empty_tries_secondary(
        self, mock_db, mock_health_monitor
    ):
        """Primary succeeds but returns empty dict (no auth error) → try
        secondary. This is the 'silent broker' case."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        primary = _make_adapter(
            "smartapi",
            snap_result={},       # empty
            quote_result={},      # empty REST fallback too
        )
        secondary = _make_adapter(
            "upstox",
            option_chain_result={
                "NFO:NIFTY2642124200CE": {
                    "last_price": 50, "oi": 1, "volume": 1,
                    "ohlc": {"close": 50},
                    "depth": {"buy": [], "sell": []},
                }
            },
        )

        async def factory(broker_type, *_args, **_kwargs):
            return {"smartapi": primary, "upstox": secondary}[broker_type]

        adapter, quotes = await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert adapter is secondary
        assert len(quotes) > 0
        # No auth error → record_auth_failure not called
        mock_health_monitor.record_auth_failure.assert_not_awaited()


@pytest.mark.unit
class TestFailoverAllBrokersFail:
    @pytest.mark.asyncio
    async def test_all_brokers_fail_returns_none_and_empty(
        self, mock_db, mock_health_monitor
    ):
        """Every broker in ORG_ACTIVE_BROKERS exhausts its paths → return
        (None, {}). The route layer decides whether to fall back to EOD."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        primary = _make_adapter(
            "smartapi",
            snap_raises=AuthenticationError("smartapi", "AG8001"),
            quote_raises=AuthenticationError("smartapi", "AG8001"),
        )
        secondary = _make_adapter(
            "upstox",
            oc_raises=AuthenticationError("upstox", "UDAPI100050 invalid token"),
        )

        async def factory(broker_type, *_args, **_kwargs):
            return {"smartapi": primary, "upstox": secondary}[broker_type]

        adapter, quotes = await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert adapter is None
        assert quotes == {}
        # Both brokers should have been reported
        assert mock_health_monitor.record_auth_failure.await_count == 2

    @pytest.mark.asyncio
    async def test_adapter_factory_auth_error_skips_to_next_broker(
        self, mock_db, mock_health_monitor
    ):
        """If adapter creation itself raises AuthenticationError
        (e.g. credentials row missing), helper records the failure and moves
        on without crashing."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        secondary = _make_adapter(
            "upstox",
            option_chain_result={
                "NFO:NIFTY2642124200CE": {
                    "last_price": 7, "oi": 1, "volume": 1,
                    "ohlc": {"close": 7}, "depth": {"buy": [], "sell": []},
                }
            },
        )

        async def factory(broker_type, *_args, **_kwargs):
            if broker_type == "smartapi":
                raise AuthenticationError("smartapi", "credentials not found")
            return secondary

        adapter, quotes = await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert adapter is secondary


@pytest.mark.unit
class TestFailoverRespectsBrokerOrder:
    @pytest.mark.asyncio
    async def test_primary_tried_before_secondary(
        self, mock_db, mock_health_monitor
    ):
        """The order must match ORG_ACTIVE_BROKERS (angelone → upstox)."""
        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        call_order: list[str] = []

        primary = _make_adapter(
            "smartapi",
            snap_raises=AuthenticationError("smartapi", "AG8001"),
            quote_raises=AuthenticationError("smartapi", "AG8001"),
        )
        secondary = _make_adapter(
            "upstox",
            option_chain_result={
                "NFO:NIFTY2642124200CE": {
                    "last_price": 1, "oi": 1, "volume": 1,
                    "ohlc": {"close": 1}, "depth": {"buy": [], "sell": []},
                }
            },
        )

        async def factory(broker_type, *_args, **_kwargs):
            call_order.append(broker_type)
            return {"smartapi": primary, "upstox": secondary}[broker_type]

        await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert call_order == ["smartapi", "upstox"]


@pytest.mark.unit
class TestFailoverStopsAtFirstHealthy:
    @pytest.mark.asyncio
    async def test_tertiary_never_attempted_when_secondary_succeeds(
        self, mock_db, mock_health_monitor, monkeypatch
    ):
        """If a 3rd broker were configured, it must NOT be tried after
        secondary returns quotes."""
        monkeypatch.setattr(
            "app.constants.brokers.ORG_ACTIVE_BROKERS",
            ["angelone", "upstox", "dhan"],  # hypothetical 3-broker chain
        )

        from app.services.brokers.market_data.failover_fetch import (
            fetch_option_chain_quotes_with_failover,
        )

        call_order: list[str] = []
        primary = _make_adapter(
            "smartapi",
            snap_raises=AuthenticationError("smartapi", "AG8001"),
        )
        secondary = _make_adapter(
            "upstox",
            option_chain_result={
                "NFO:NIFTY2642124200CE": {
                    "last_price": 1, "oi": 1, "volume": 1,
                    "ohlc": {"close": 1}, "depth": {"buy": [], "sell": []},
                }
            },
        )
        tertiary_factory = AsyncMock()  # should NEVER be called

        async def factory(broker_type, *_args, **_kwargs):
            call_order.append(broker_type)
            if broker_type == "smartapi":
                return primary
            if broker_type == "upstox":
                return secondary
            await tertiary_factory(broker_type)
            return None

        await fetch_option_chain_quotes_with_failover(
            underlying="NIFTY",
            expiry_str="2026-04-21",
            expiry_date=date(2026, 4, 21),
            user_id=uuid4(),
            db=mock_db,
            health_monitor=mock_health_monitor,
            adapter_factory=factory,
        )

        assert "dhan" not in call_order
        tertiary_factory.assert_not_awaited()
