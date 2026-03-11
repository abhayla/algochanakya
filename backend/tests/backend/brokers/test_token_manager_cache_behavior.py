"""
Test: TokenManager cache behavior — reproduces sequential DB query bug.

Bug: When TokenManager._loaded is False (fresh per-request instance),
each get_token() call for a cache-miss fires a separate DB query.
With 126 option symbols this produces 126 sequential DB round-trips,
causing the /api/optionchain/chain endpoint to take 7+ seconds —
exceeding the Axios 10s timeout and resulting in ERR_ABORTED in the browser.

Fix: Call await token_manager.load_cache() once before the per-symbol
loop in SmartAPIMarketDataAdapter.get_quote(). load_cache() does a
single bulk SELECT and populates the in-memory cache. Subsequent
get_token() calls hit only memory — zero extra DB queries.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.services.brokers.market_data.token_manager import TokenManager


class TestTokenManagerCacheBehavior:
    """Reproduces Bug 1: sequential DB queries when cache is not preloaded."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_token_without_preload_fires_one_db_query_per_symbol(self):
        """
        REPRODUCES BUG: Without load_cache(), each get_token() for an uncached symbol
        fires a separate DB query. 50 symbols = 50 DB queries per batch.

        Root cause: SmartAPIMarketDataAdapter.get_quote() uses a per-request
        TokenManager and never calls load_cache() before the symbol loop.
        """
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        manager = TokenManager(broker="smartapi", db=mock_db)
        # Deliberately NOT calling load_cache() — simulating current broken behavior

        symbols = [f"NIFTY26MAR{20000 + i}CE" for i in range(50)]
        for symbol in symbols:
            await manager.get_token(symbol)

        # Bug demonstrated: 50 separate DB queries were fired (one per symbol)
        assert mock_db.execute.call_count == 50, (
            f"Bug confirmed: {mock_db.execute.call_count} sequential DB queries fired "
            f"for 50 symbols. After fix, load_cache() should reduce this to 1."
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_load_cache_fires_exactly_one_db_query_for_all_tokens(self):
        """
        After fix: load_cache() preloads all tokens in a single bulk DB query.
        This is the correct initialization pattern.
        """
        mock_db = AsyncMock()

        # Simulate 50 tokens in DB
        mock_tokens = []
        for i in range(50):
            tok = MagicMock()
            tok.canonical_symbol = f"NIFTY26MAR{20000 + i}CE"
            tok.broker_token = 50000 + i
            tok.broker_symbol = f"NIFTY26MAR{20000 + i}CE"
            mock_tokens.append(tok)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tokens
        mock_db.execute = AsyncMock(return_value=mock_result)

        manager = TokenManager(broker="smartapi", db=mock_db)
        await manager.load_cache()  # Should fire exactly 1 DB query

        assert mock_db.execute.call_count == 1, (
            f"load_cache() must fire exactly 1 DB query, got {mock_db.execute.call_count}"
        )
        assert manager._loaded is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_token_after_load_cache_fires_zero_extra_db_queries(self):
        """
        After fix: Once load_cache() has run, all get_token() calls hit memory only.
        Zero additional DB queries for 50 symbol lookups.
        """
        mock_db = AsyncMock()

        # Simulate 50 tokens in DB
        mock_tokens = []
        for i in range(50):
            tok = MagicMock()
            tok.canonical_symbol = f"NIFTY26MAR{20000 + i}CE"
            tok.broker_token = 50000 + i
            tok.broker_symbol = f"NIFTY26MAR{20000 + i}CE"
            mock_tokens.append(tok)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tokens
        mock_db.execute = AsyncMock(return_value=mock_result)

        manager = TokenManager(broker="smartapi", db=mock_db)
        await manager.load_cache()

        db_calls_after_load = mock_db.execute.call_count  # Should be 1

        # Look up all 50 symbols — should all hit memory cache
        for i in range(50):
            token = await manager.get_token(f"NIFTY26MAR{20000 + i}CE")
            assert token == 50000 + i, f"Cache miss for symbol {i}"

        assert mock_db.execute.call_count == db_calls_after_load, (
            f"After load_cache(), get_token() must not fire extra DB queries. "
            f"Expected {db_calls_after_load} total calls, got {mock_db.execute.call_count}."
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_load_cache_is_idempotent_second_call_is_noop(self):
        """
        load_cache() checks _loaded flag and skips on subsequent calls.
        Safe to call before every get_quote() invocation.
        """
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        manager = TokenManager(broker="smartapi", db=mock_db)
        await manager.load_cache()  # First call — 1 DB query
        await manager.load_cache()  # Second call — should be no-op
        await manager.load_cache()  # Third call — should be no-op

        assert mock_db.execute.call_count == 1, (
            f"load_cache() should be idempotent (1 DB query total), "
            f"but fired {mock_db.execute.call_count} queries."
        )


class TestSmartAPIAdapterGetQuotePreloadsCache:
    """
    Reproduces Bug 1 at the adapter level: get_quote() must call load_cache()
    before the per-symbol token loop.
    """

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_quote_calls_load_cache_before_token_loop(self):
        """
        EXPECTED FIX: SmartAPIMarketDataAdapter.get_quote() must call
        self._token_manager.load_cache() once before iterating over option_symbols.

        Without this, each of the 50+ symbols in a batch triggers a sequential DB query.
        """
        from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter

        # Build adapter with mocked internals (bypass __init__)
        adapter = SmartAPIMarketDataAdapter.__new__(SmartAPIMarketDataAdapter)

        mock_token_manager = AsyncMock()
        mock_token_manager._loaded = False
        mock_token_manager.load_cache = AsyncMock()
        # Return a valid token for every symbol lookup
        mock_token_manager.get_token = AsyncMock(return_value=99999)

        mock_instruments = MagicMock()
        mock_instruments._instruments = ["dummy_instrument"]  # Non-empty = already loaded

        mock_market_data = AsyncMock()
        mock_market_data.get_quote = AsyncMock(return_value={})  # Empty quote response

        adapter._token_manager = mock_token_manager
        adapter._instruments = mock_instruments
        adapter._market_data = mock_market_data

        symbols = [f"NIFTY26MAR{20000 + i}CE" for i in range(10)]
        await adapter.get_quote(symbols)

        # After fix: load_cache() must have been called exactly once
        mock_token_manager.load_cache.assert_called_once()  # BUG: currently called 0 times

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_ltp_calls_load_cache_before_token_loop(self):
        """
        Same fix needed in get_ltp() — also does sequential per-symbol token lookups.
        """
        from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter

        adapter = SmartAPIMarketDataAdapter.__new__(SmartAPIMarketDataAdapter)

        mock_token_manager = AsyncMock()
        mock_token_manager._loaded = False
        mock_token_manager.load_cache = AsyncMock()
        mock_token_manager.get_token = AsyncMock(return_value=99999)

        mock_instruments = MagicMock()
        mock_instruments._instruments = ["dummy_instrument"]

        mock_market_data = AsyncMock()
        mock_market_data.get_quote = AsyncMock(return_value={})

        adapter._token_manager = mock_token_manager
        adapter._instruments = mock_instruments
        adapter._market_data = mock_market_data

        symbols = [f"NIFTY26MAR{20000 + i}CE" for i in range(10)]
        await adapter.get_ltp(symbols)

        mock_token_manager.load_cache.assert_called_once()  # BUG: currently called 0 times
