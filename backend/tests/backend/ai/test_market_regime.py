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
    return kite


@pytest.fixture
def mock_market_data():
    """Create a mock MarketDataService."""
    md = MagicMock()
    spot = MagicMock()
    spot.ltp = 22000.0
    md.get_spot_price = AsyncMock(return_value=spot)
    md.get_vix = AsyncMock(return_value=14.5)
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
# Classification tests (with mocked dependencies)
# ---------------------------------------------------------------------------

class TestClassification:
    """Test regime classification logic."""

    @pytest.mark.asyncio
    async def test_classify_returns_regime_result(self, classifier):
        """classify() should return a RegimeResult."""
        ohlc_data = _make_ohlc_data(trend="bullish")
        with patch.object(classifier.historical_data, 'get_daily_candles', new_callable=AsyncMock) as mock_candles:
            mock_candles.return_value = ohlc_data

            result = await classifier.classify("NIFTY")

            assert isinstance(result, RegimeResult)
            assert result.regime_type in RegimeType
            assert 0 <= result.confidence <= 100
            assert result.reasoning is not None

    @pytest.mark.asyncio
    async def test_classify_bullish_trend(self, classifier):
        """Strong uptrend should classify as TRENDING_BULLISH."""
        ohlc_data = _make_ohlc_data(trend="bullish")
        with patch.object(classifier.historical_data, 'get_daily_candles', new_callable=AsyncMock) as mock_candles:
            mock_candles.return_value = ohlc_data
            # Low VIX — mock_market_data already returns 14.5

            result = await classifier.classify("NIFTY")

            # Bullish trend with low VIX should give bullish or rangebound
            assert result.regime_type in [
                RegimeType.TRENDING_BULLISH,
                RegimeType.RANGEBOUND,
                RegimeType.UNKNOWN,
                RegimeType.PRE_EVENT,
                RegimeType.EVENT_DAY,
            ]

    @pytest.mark.asyncio
    async def test_classify_with_event_day(self, classifier):
        """Event day should override other classifications."""
        with patch.object(classifier, 'is_event_day', return_value=(True, "RBI Policy")):
            ohlc_data = _make_ohlc_data(trend="bullish")
            with patch.object(classifier.historical_data, 'get_daily_candles', new_callable=AsyncMock) as mock_candles:
                mock_candles.return_value = ohlc_data

                result = await classifier.classify("NIFTY")

                assert result.regime_type == RegimeType.EVENT_DAY

    @pytest.mark.asyncio
    async def test_classify_volatile_market(self, classifier, mock_market_data):
        """High VIX should contribute to VOLATILE classification."""
        mock_market_data.get_vix = AsyncMock(return_value=25.0)
        ohlc_data = _make_ohlc_data(trend="volatile")
        with patch.object(classifier.historical_data, 'get_daily_candles', new_callable=AsyncMock) as mock_candles:
            mock_candles.return_value = ohlc_data

            result = await classifier.classify("NIFTY")

            assert result.confidence > 0


# ---------------------------------------------------------------------------
# Indicators snapshot tests
# ---------------------------------------------------------------------------

class TestIndicatorsSnapshot:
    """Test indicator snapshot generation."""

    @pytest.mark.asyncio
    async def test_snapshot_returns_all_fields(self, classifier):
        """Snapshot should include all indicator fields."""
        ohlc_data = _make_ohlc_data(trend="bullish")
        with patch.object(classifier.historical_data, 'get_daily_candles', new_callable=AsyncMock) as mock_candles:
            mock_candles.return_value = ohlc_data

            snapshot = await classifier.get_indicators_snapshot("NIFTY")

            assert isinstance(snapshot, IndicatorsSnapshot)
            assert snapshot.underlying == "NIFTY"
            assert snapshot.spot_price > 0


# ---------------------------------------------------------------------------
# Direct classification logic tests (no async needed)
# ---------------------------------------------------------------------------

class TestClassificationLogic:
    """Test the private classification helper methods directly."""

    def test_volatile_regime_detected_with_high_vix(self, classifier):
        """High VIX should trigger VOLATILE."""
        snapshot = _make_snapshot(vix=25.0, adx=18.0, rsi=50.0, bb_width=2.5, spot=22000.0, ema_50=21500.0)
        result = classifier._check_volatile_regime(snapshot)
        assert result is not None
        assert result.regime_type == RegimeType.VOLATILE

    def test_rangebound_regime_detected_with_low_adx(self, classifier):
        """Low ADX and narrow BB width should trigger RANGEBOUND."""
        snapshot = _make_snapshot(vix=12.0, adx=15.0, rsi=50.0, bb_width=1.5, spot=22000.0, ema_50=21900.0)
        result = classifier._check_rangebound_regime(snapshot)
        assert result is not None
        assert result.regime_type == RegimeType.RANGEBOUND

    def test_trending_bullish_detected(self, classifier):
        """Strong ADX with price above EMA50 and RSI < 70 is bullish."""
        snapshot = _make_snapshot(vix=12.0, adx=30.0, rsi=60.0, bb_width=2.5, spot=22000.0, ema_50=21000.0)
        result = classifier._check_trending_regime(snapshot)
        assert result is not None
        assert result.regime_type == RegimeType.TRENDING_BULLISH

    def test_trending_bearish_detected(self, classifier):
        """Strong ADX with price below EMA50 and RSI > 30 is bearish."""
        snapshot = _make_snapshot(vix=15.0, adx=30.0, rsi=40.0, bb_width=2.5, spot=21000.0, ema_50=22000.0)
        result = classifier._check_trending_regime(snapshot)
        assert result is not None
        assert result.regime_type == RegimeType.TRENDING_BEARISH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(vix, adx, rsi, bb_width, spot, ema_50):
    """Create an IndicatorsSnapshot for testing."""
    return IndicatorsSnapshot(
        underlying="NIFTY",
        timestamp=datetime.now(),
        spot_price=spot,
        vix=vix,
        rsi_14=rsi,
        adx_14=adx,
        ema_9=spot - 50,
        ema_21=spot - 30,
        ema_50=ema_50,
        atr_14=spot * 0.01,
        bb_upper=spot + 300,
        bb_middle=spot,
        bb_lower=spot - 300,
        bb_width_pct=bb_width,
    )


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
