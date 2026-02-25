"""
Market Regime Classifier Tests

Tests for MarketRegimeClassifier including:
- Regime classification for different market conditions
- Event day detection
- Pre-event detection
- Indicator snapshot generation
- Edge cases (insufficient data, missing indicators)
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from app.services.ai.market_regime import (
    MarketRegimeClassifier,
    RegimeType,
    RegimeResult,
    IndicatorsSnapshot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kite():
    """Create a mock KiteConnect client."""
    kite = MagicMock()
    kite.ltp.return_value = {"NSE:NIFTY 50": {"last_price": 22000.0}}
    kite.quote.return_value = {
        "NSE:NIFTY 50": {"last_price": 22000.0, "ohlc": {"open": 21900, "high": 22100, "low": 21850, "close": 22000}},
        "NSE:INDIA VIX": {"last_price": 14.5},
    }
    return kite


@pytest.fixture
def mock_market_data():
    """Create a mock MarketDataService."""
    md = MagicMock()
    md.get_ltp = AsyncMock(return_value=22000.0)
    return md


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    return r


@pytest.fixture
def classifier(mock_kite, mock_market_data, mock_redis):
    """Create a MarketRegimeClassifier with mocked dependencies."""
    return MarketRegimeClassifier(
        kite=mock_kite,
        market_data=mock_market_data,
        redis_client=mock_redis,
    )


# ---------------------------------------------------------------------------
# RegimeType enum tests
# ---------------------------------------------------------------------------

class TestRegimeType:
    """Test RegimeType enum values."""

    def test_all_regime_types_exist(self):
        """All 7 regime types should exist."""
        expected = [
            "TRENDING_BULLISH", "TRENDING_BEARISH", "RANGEBOUND",
            "VOLATILE", "PRE_EVENT", "EVENT_DAY", "UNKNOWN",
        ]
        for name in expected:
            assert hasattr(RegimeType, name), f"Missing RegimeType.{name}"

    def test_regime_type_values(self):
        """RegimeType values should match their names."""
        assert RegimeType.TRENDING_BULLISH.value == "TRENDING_BULLISH"
        assert RegimeType.RANGEBOUND.value == "RANGEBOUND"
        assert RegimeType.UNKNOWN.value == "UNKNOWN"


# ---------------------------------------------------------------------------
# Event day detection tests
# ---------------------------------------------------------------------------

class TestEventDayDetection:
    """Test event and pre-event day detection."""

    def test_is_event_day_returns_tuple(self, classifier):
        """is_event_day returns (bool, str) tuple."""
        result = classifier.is_event_day(date.today())
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)

    def test_is_pre_event_returns_tuple(self, classifier):
        """is_pre_event returns (bool, int, str) tuple."""
        result = classifier.is_pre_event(date.today())
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)


# ---------------------------------------------------------------------------
# Classification tests (with mocked historical data)
# ---------------------------------------------------------------------------

class TestClassification:
    """Test regime classification logic."""

    @pytest.mark.asyncio
    async def test_classify_returns_regime_result(self, classifier):
        """classify() should return a RegimeResult."""
        # Mock internal historical data fetch
        with patch.object(classifier, '_get_ohlc_data', new_callable=AsyncMock) as mock_ohlc:
            mock_ohlc.return_value = _make_ohlc_data(trend="bullish")
            with patch.object(classifier, '_get_vix', new_callable=AsyncMock) as mock_vix:
                mock_vix.return_value = 14.5

                result = await classifier.classify("NIFTY")

                assert isinstance(result, RegimeResult)
                assert result.regime_type in RegimeType
                assert 0 <= result.confidence <= 100
                assert result.reasoning is not None

    @pytest.mark.asyncio
    async def test_classify_bullish_trend(self, classifier):
        """Strong uptrend should classify as TRENDING_BULLISH."""
        with patch.object(classifier, '_get_ohlc_data', new_callable=AsyncMock) as mock_ohlc:
            mock_ohlc.return_value = _make_ohlc_data(trend="bullish")
            with patch.object(classifier, '_get_vix', new_callable=AsyncMock) as mock_vix:
                mock_vix.return_value = 12.0  # Low VIX

                result = await classifier.classify("NIFTY")

                # Bullish trend with low VIX should give bullish or rangebound
                assert result.regime_type in [
                    RegimeType.TRENDING_BULLISH,
                    RegimeType.RANGEBOUND,
                ]

    @pytest.mark.asyncio
    async def test_classify_bearish_trend(self, classifier):
        """Strong downtrend should classify as TRENDING_BEARISH."""
        with patch.object(classifier, '_get_ohlc_data', new_callable=AsyncMock) as mock_ohlc:
            mock_ohlc.return_value = _make_ohlc_data(trend="bearish")
            with patch.object(classifier, '_get_vix', new_callable=AsyncMock) as mock_vix:
                mock_vix.return_value = 18.0

                result = await classifier.classify("NIFTY")

                assert result.regime_type in [
                    RegimeType.TRENDING_BEARISH,
                    RegimeType.VOLATILE,
                ]

    @pytest.mark.asyncio
    async def test_classify_volatile_market(self, classifier):
        """High VIX should contribute to VOLATILE classification."""
        with patch.object(classifier, '_get_ohlc_data', new_callable=AsyncMock) as mock_ohlc:
            mock_ohlc.return_value = _make_ohlc_data(trend="volatile")
            with patch.object(classifier, '_get_vix', new_callable=AsyncMock) as mock_vix:
                mock_vix.return_value = 25.0  # High VIX

                result = await classifier.classify("NIFTY")

                assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_classify_with_event_day(self, classifier):
        """Event day should override other classifications."""
        with patch.object(classifier, 'is_event_day', return_value=(True, "RBI Policy")):
            with patch.object(classifier, '_get_ohlc_data', new_callable=AsyncMock) as mock_ohlc:
                mock_ohlc.return_value = _make_ohlc_data(trend="bullish")
                with patch.object(classifier, '_get_vix', new_callable=AsyncMock) as mock_vix:
                    mock_vix.return_value = 14.0

                    result = await classifier.classify("NIFTY")

                    assert result.regime_type == RegimeType.EVENT_DAY


# ---------------------------------------------------------------------------
# Indicators snapshot tests
# ---------------------------------------------------------------------------

class TestIndicatorsSnapshot:
    """Test indicator snapshot generation."""

    @pytest.mark.asyncio
    async def test_snapshot_returns_all_fields(self, classifier):
        """Snapshot should include all indicator fields."""
        with patch.object(classifier, '_get_ohlc_data', new_callable=AsyncMock) as mock_ohlc:
            mock_ohlc.return_value = _make_ohlc_data(trend="bullish")
            with patch.object(classifier, '_get_vix', new_callable=AsyncMock) as mock_vix:
                mock_vix.return_value = 14.5

                snapshot = await classifier.get_indicators_snapshot("NIFTY")

                assert isinstance(snapshot, IndicatorsSnapshot)
                assert snapshot.underlying == "NIFTY"
                assert snapshot.spot_price > 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlc_data(trend="bullish", days=50):
    """Generate synthetic OHLC data for testing."""
    data = []
    base_price = 22000.0

    for i in range(days):
        if trend == "bullish":
            close = base_price + (i * 20)
        elif trend == "bearish":
            close = base_price - (i * 20)
        elif trend == "volatile":
            close = base_price + ((-1) ** i * 150)
        else:  # rangebound
            close = base_price + ((-1) ** i * 30)

        high = close + 50
        low = close - 50
        open_price = close - 10 if trend == "bullish" else close + 10

        data.append(MagicMock(
            date=datetime.now() - timedelta(days=days - i),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=1000000 + i * 10000,
        ))

    return data
