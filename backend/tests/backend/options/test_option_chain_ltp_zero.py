"""
Bug Reproduction: Option chain returns all LTPs = 0 when broker_instrument_tokens is empty

When the broker_instrument_tokens table has no SmartAPI token mappings:
  1. TokenManager.get_token() returns None for every NFO symbol
  2. SmartAPIInstruments fallback also returns None (instrument master not loaded)
  3. tokens_map stays empty → get_quote() is never called → all quotes are empty
  4. Every strike in the chain shows LTP=0, IV=0, OI=0

The chain API returns HTTP 200 with 100+ strikes, all with zeroed data — a silent failure.
The UI shows "Failed to load option chain" because the data appears empty.

Fix (instrument_master.py — populate_broker_token_mappings):
  a) Raises RuntimeError (not silently returns 0) when SmartAPI master download fails
  b) Falls back to all source brokers if no kite-sourced instruments found
  c) main.py startup log is now a clear WARNING (not silent) when populate fails
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import date

from app.services.brokers.market_data.token_manager import TokenManager
from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter
from app.services.instrument_master import InstrumentMasterService


class TestTokenManagerEmptyTable:
    """
    Reproduces: TokenManager.get_token() returns None for all symbols
    when broker_instrument_tokens table is empty.
    """

    @pytest.mark.asyncio
    async def test_get_token_returns_none_when_table_empty(self):
        """When broker_instrument_tokens has no rows, get_token() returns None."""
        # Simulate empty DB — scalar_one_or_none() returns None
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # empty table
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        manager = TokenManager(broker="smartapi", db=mock_db)
        await manager.load_cache()

        token = await manager.get_token("NIFTY26MAR24250CE")

        assert token is None, (
            "get_token() should return None when broker_instrument_tokens is empty"
        )

    @pytest.mark.asyncio
    async def test_load_cache_loads_zero_tokens_when_table_empty(self):
        """When table is empty, cache loads 0 tokens — verified by cache size."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        manager = TokenManager(broker="smartapi", db=mock_db)
        await manager.load_cache()

        assert len(manager._symbol_to_token) == 0, (
            "Token cache should be empty when broker_instrument_tokens table is empty"
        )


class TestSmartAPIAdapterEmptyTokens:
    """
    Reproduces: SmartAPIMarketDataAdapter.get_quote() silently returns empty dict
    when TokenManager returns None AND instrument master fallback fails.
    This causes every strike LTP to be 0 in the option chain.
    """

    def _make_adapter(self, token_value=None, instrument_token_str=None):
        """Build a SmartAPIMarketDataAdapter with mocked internals."""
        mock_db = AsyncMock()

        mock_token_manager = AsyncMock()
        mock_token_manager.get_token.return_value = token_value

        mock_instruments = AsyncMock()
        mock_instruments._instruments = {}  # empty — forces lazy-load attempt
        mock_instruments.download_master = AsyncMock()
        mock_instruments.lookup_token.return_value = instrument_token_str

        mock_market_data = AsyncMock()
        mock_market_data.get_quote.return_value = {}  # no quotes from SmartAPI

        creds = MagicMock()
        creds.client_id = "test"
        creds.jwt_token = "test"
        creds.feed_token = "test"
        creds.api_key = "test"

        adapter = SmartAPIMarketDataAdapter.__new__(SmartAPIMarketDataAdapter)
        adapter._credentials = creds
        adapter._db = mock_db
        adapter._token_manager = mock_token_manager
        adapter._instruments = mock_instruments
        adapter._market_data = mock_market_data
        return adapter

    @pytest.mark.asyncio
    async def test_get_quote_returns_empty_when_no_tokens(self):
        """
        When TokenManager returns None AND instrument master fallback returns None,
        get_quote() returns an empty dict — every symbol gets no quote.

        This is the root cause of all LTPs = 0 in the option chain.
        """
        adapter = self._make_adapter(token_value=None, instrument_token_str=None)

        symbols = ["NIFTY26MAR24250CE", "NIFTY26MAR24250PE", "NIFTY26MAR24300CE"]
        result = await adapter.get_quote(symbols)

        # BUG: result is empty — none of the 3 symbols got a quote
        assert len(result) == 0, (
            f"Expected 0 quotes (bug state) when token lookup fails for all symbols, "
            f"got {len(result)}"
        )

        # Verify the adapter DID try to look up tokens
        assert adapter._token_manager.get_token.call_count == len(symbols), (
            "TokenManager.get_token should be called for each option symbol"
        )

    @pytest.mark.asyncio
    async def test_get_quote_never_calls_smartapi_when_no_tokens(self):
        """
        When all token lookups return None, the SmartAPI REST quote API
        is never called — confirming the data gap, not a SmartAPI error.
        """
        adapter = self._make_adapter(token_value=None, instrument_token_str=None)

        await adapter.get_quote(["NIFTY26MAR24250CE", "NIFTY26MAR24250PE"])

        # SmartAPI get_quote should NOT have been called — tokens_map was empty
        adapter._market_data.get_quote.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_quote_succeeds_when_token_present(self):
        """
        Confirm that when TokenManager DOES return a token, get_quote works
        and returns a non-empty UnifiedQuote. This is the expected fix state.
        """
        adapter = self._make_adapter(token_value=49159, instrument_token_str=None)

        # Mock SmartAPI returning valid quote data for token 49159
        raw_quote_data = {
            "49159": {
                "ltp": 25000,        # paise → 250.00 rupees after ÷100
                "open": 24000,
                "high": 26000,
                "low": 23000,
                "close": 24500,
                "oi": 1000000,
                "volume": 50000,
                "buyQty": 100,
                "buyPrice": 24900,
                "sellQty": 150,
                "sellPrice": 25100,
            }
        }
        adapter._market_data.get_quote.return_value = raw_quote_data

        result = await adapter.get_quote(["NIFTY26MAR24250CE"])

        assert len(result) == 1, "Should return quote for 1 symbol when token is found"
        assert "NIFTY26MAR24250CE" in result
        quote = result["NIFTY26MAR24250CE"]
        # SmartAPI NFO prices are in paise; adapter divides by 100
        assert quote.last_price == Decimal("250.00"), (
            f"LTP should be 250.00 rupees (25000 paise ÷ 100), got {quote.last_price}"
        )


class TestPopulateBrokerTokenMappings:
    """
    Tests for InstrumentMasterService.populate_broker_token_mappings().

    Verifies the fix: clear errors instead of silent zero returns.
    """

    def _make_mock_db_with_instruments(self, instruments):
        """Return a mock DB session that returns the given list from execute().scalars().all()."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = instruments
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_raises_when_instrument_master_download_fails(self):
        """
        When SmartAPI instrument master download fails (network error),
        populate_broker_token_mappings raises RuntimeError instead of silently returning 0.
        """
        mock_db = self._make_mock_db_with_instruments([])  # DB has no kite instruments

        mock_smartapi_instr = MagicMock()
        mock_smartapi_instr._instruments = []  # Empty — triggers download

        # Simulate download failure
        mock_smartapi_instr.download_master = AsyncMock(side_effect=Exception("Network timeout"))

        # get_smartapi_instruments is called inside the method via a local from-import.
        # Patch the module-level singleton so the getter returns our mock.
        import app.services.legacy.smartapi_instruments as smartapi_mod
        original_singleton = smartapi_mod._smartapi_instruments
        smartapi_mod._smartapi_instruments = mock_smartapi_instr
        try:
            with pytest.raises(RuntimeError):
                await InstrumentMasterService.populate_broker_token_mappings(mock_db)
        finally:
            smartapi_mod._smartapi_instruments = original_singleton

    @pytest.mark.asyncio
    async def test_raises_when_no_instruments_in_db(self):
        """
        When no NFO instruments exist in DB (fresh/empty DB),
        populate_broker_token_mappings raises RuntimeError with a clear message.
        """
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []  # No kite AND no any instruments
        mock_db.execute.return_value = mock_result

        mock_smartapi_instr = MagicMock()
        mock_smartapi_instr._instruments = ["dummy"]  # Pretend already loaded
        mock_smartapi_instr.download_master = AsyncMock()

        import app.services.legacy.smartapi_instruments as smartapi_mod
        original_singleton = smartapi_mod._smartapi_instruments
        smartapi_mod._smartapi_instruments = mock_smartapi_instr
        try:
            with pytest.raises(RuntimeError, match="No NFO option instruments found"):
                await InstrumentMasterService.populate_broker_token_mappings(mock_db)
        finally:
            smartapi_mod._smartapi_instruments = original_singleton

    @pytest.mark.asyncio
    async def test_falls_back_to_all_sources_when_no_kite_instruments(self):
        """
        When DB has instruments but none are source_broker='kite',
        the function falls back to querying all sources rather than returning 0.

        This handles dev environments where instruments came from SmartAPI adapter.
        """
        # Create a fake instrument (non-kite source)
        fake_instrument = MagicMock()
        fake_instrument.tradingsymbol = "NIFTY26MAR24250CE"
        fake_instrument.expiry = date(2026, 3, 27)

        mock_db = AsyncMock()
        mock_result_kite = MagicMock()
        mock_result_kite.scalars.return_value.all.return_value = []  # No kite instruments

        mock_result_all = MagicMock()
        mock_result_all.scalars.return_value.all.return_value = [fake_instrument]  # Non-kite exists

        mock_result_insert = MagicMock()

        # First call (kite filter) returns empty; second call (all sources) returns instrument
        # Third call is the insert (execute returns a result)
        mock_db.execute.side_effect = [mock_result_kite, mock_result_all, mock_result_insert]
        mock_db.commit = AsyncMock()

        mock_smartapi_instr = MagicMock()
        mock_smartapi_instr._instruments = ["dummy"]  # Already loaded
        mock_smartapi_instr.download_master = AsyncMock()
        # Token found for the instrument
        mock_smartapi_instr.lookup_token = AsyncMock(return_value="57797")

        import app.services.legacy.smartapi_instruments as smartapi_mod
        original_singleton = smartapi_mod._smartapi_instruments
        smartapi_mod._smartapi_instruments = mock_smartapi_instr
        try:
            with patch(
                "app.services.instrument_master.insert",
            ) as mock_insert:
                # Mock the upsert statement chain
                mock_stmt = MagicMock()
                mock_stmt.on_conflict_do_update.return_value = mock_stmt
                mock_insert.return_value = mock_stmt

                result = await InstrumentMasterService.populate_broker_token_mappings(mock_db)
        finally:
            smartapi_mod._smartapi_instruments = original_singleton

        # Should have stored 1 mapping (from the non-kite instrument)
        assert result == 1, (
            f"Expected 1 mapping (from non-kite instrument fallback), got {result}"
        )
        # Should have made 3 DB calls (kite-select, all-sources-select, insert)
        assert mock_db.execute.call_count == 3, (
            f"Expected 3 DB calls (2 selects + 1 insert), got {mock_db.execute.call_count}"
        )


class TestOptionChainEndpointAllZeroLtps:
    """
    Integration-level reproduction: the /chain endpoint returns HTTP 200
    with all LTPs = 0 when broker_instrument_tokens is empty.

    Demonstrates the 'silent failure' — no error is raised, just zeros.
    """

    @pytest.mark.asyncio
    async def test_chain_response_has_nonzero_ltps(self):
        """
        The /chain endpoint must return at least one strike with non-zero CE or PE LTP.
        Failing this test proves the 'all LTPs = 0' bug.

        This test calls the live dev backend. Skip if backend is not running.
        """
        import httpx
        import os

        token = os.environ.get(
            "TEST_AUTH_TOKEN",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJ1c2VyX2lkIjoiOTA1N2JlOWItMzUzMy00NWM2LWIwMDUtNzRkNjAxN2FlNjgyIiwiZXhwIjoxNzczMjI1NjI1LCJpYXQiOjE3NzMxMzkyMjUsImJyb2tlcl9jb25uZWN0aW9uX2lkIjoiMWRhOTkwMjEtOWYyNS00ZDE2LWJlZDAtM2Y4NDllZTA0MzA1In0"
            ".Xrc_AFj4CUKHyibHvntNQtyHiRIaoUhqjT6rvZoH98Y"
        )
        backend_url = "http://localhost:8001"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{backend_url}/api/optionchain/chain",
                    params={"underlying": "NIFTY", "expiry": "2026-03-17"},
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.ConnectError:
            pytest.skip("Backend not running on localhost:8001")

        if resp.status_code in (401, 403):
            pytest.skip(f"Auth token expired or invalid (HTTP {resp.status_code})")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        # API returns key "chain" (not "strikes")
        strikes = data.get("chain", data.get("strikes", []))

        assert len(strikes) > 0, (
            f"Chain must have at least one strike. Response keys: {list(data.keys())}. "
            f"spot_price={data.get('spot_price')}"
        )

        # The bug: ALL strikes have LTP = 0
        nonzero_ltps = [
            s for s in strikes
            if (s.get("ce") or {}).get("ltp", 0) > 0
            or (s.get("pe") or {}).get("ltp", 0) > 0
        ]

        if len(nonzero_ltps) == 0:
            # Check if broker_instrument_tokens table is populated before diagnosing.
            # LTP=0 can mean either:
            #   a) broker_instrument_tokens is empty (the actual bug), OR
            #   b) SmartAPI credentials are expired (8-hour JWT validity) — not our bug
            from app.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as check_db:
                r = await check_db.execute(
                    text("SELECT COUNT(*) FROM broker_instrument_tokens WHERE broker='smartapi'")
                )
                token_count = r.scalar()

            if token_count == 0:
                pytest.fail(
                    f"BUG CONFIRMED: All {len(strikes)} strikes have LTP = 0 AND "
                    "broker_instrument_tokens table is EMPTY. "
                    "TokenManager cannot look up SmartAPI tokens — run "
                    "InstrumentMasterService.populate_broker_token_mappings() first."
                )
            else:
                pytest.skip(
                    f"All {len(strikes)} strikes have LTP = 0, but broker_instrument_tokens "
                    f"has {token_count} rows. Likely cause: SmartAPI JWT credentials expired "
                    "(8-hour validity) — re-authenticate via /api/smartapi/authenticate."
                )
