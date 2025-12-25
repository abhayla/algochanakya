"""
Technical Indicators Service Tests

Tests for TechnicalIndicators including:
- RSI (Relative Strength Index)
- ADX (Average Directional Index)
- EMA (Exponential Moving Average)
- ATR (Average True Range)
- Bollinger Bands
- SMA (Simple Moving Average)
"""

import pytest
from app.services.ai.indicators import TechnicalIndicators, BollingerBands


class TestRSICalculation:
    """Test RSI (Relative Strength Index) calculations."""

    def test_rsi_basic(self):
        """Test basic RSI calculation with known values."""
        # Sample prices that should produce predictable RSI
        prices = [
            44.0, 44.25, 44.50, 43.75, 44.00,
            44.50, 44.75, 45.00, 45.25, 45.50,
            45.75, 46.00, 45.50, 45.25, 45.00,
            44.75, 44.50, 44.25, 44.00, 43.75
        ]

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 0 <= rsi <= 100, f"RSI {rsi} should be between 0 and 100"

    def test_rsi_overbought(self):
        """Test RSI with strong uptrend (should be > 70)."""
        # Strong uptrend
        prices = [100 + i for i in range(20)]

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert rsi > 70, f"RSI {rsi} should be > 70 in strong uptrend"

    def test_rsi_oversold(self):
        """Test RSI with strong downtrend (should be < 30)."""
        # Strong downtrend
        prices = [100 - i for i in range(20)]

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert rsi < 30, f"RSI {rsi} should be < 30 in strong downtrend"

    def test_rsi_insufficient_data(self):
        """Test RSI returns None with insufficient data."""
        prices = [100, 101, 102]  # Only 3 prices, need 15 for period 14

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is None

    def test_rsi_neutral(self):
        """Test RSI around 50 for neutral/ranging market."""
        # Sideways market
        prices = [100, 101, 100, 101, 100, 101, 100, 101, 100, 101,
                  100, 101, 100, 101, 100, 101, 100, 101, 100, 101]

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 40 <= rsi <= 60, f"RSI {rsi} should be near 50 for ranging market"


class TestEMACalculation:
    """Test EMA (Exponential Moving Average) calculations."""

    def test_ema_basic(self):
        """Test basic EMA calculation."""
        prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109]

        ema = TechnicalIndicators.calculate_ema(prices, period=5)

        assert ema is not None
        assert ema > 0

    def test_ema_uptrend(self):
        """Test EMA follows uptrend."""
        prices = [100 + i for i in range(20)]

        ema_short = TechnicalIndicators.calculate_ema(prices, period=5)
        ema_long = TechnicalIndicators.calculate_ema(prices, period=10)

        assert ema_short is not None
        assert ema_long is not None
        assert ema_short > ema_long, "Short EMA should be > long EMA in uptrend"

    def test_ema_downtrend(self):
        """Test EMA follows downtrend."""
        prices = [100 - i for i in range(20)]

        ema_short = TechnicalIndicators.calculate_ema(prices, period=5)
        ema_long = TechnicalIndicators.calculate_ema(prices, period=10)

        assert ema_short is not None
        assert ema_long is not None
        assert ema_short < ema_long, "Short EMA should be < long EMA in downtrend"

    def test_ema_insufficient_data(self):
        """Test EMA returns None with insufficient data."""
        prices = [100, 101, 102]

        ema = TechnicalIndicators.calculate_ema(prices, period=10)

        assert ema is None


class TestATRCalculation:
    """Test ATR (Average True Range) calculations."""

    def test_atr_basic(self):
        """Test basic ATR calculation."""
        high = [102, 104, 106, 105, 107, 109, 108, 110, 112, 111,
                113, 115, 114, 116, 118]
        low = [98, 100, 102, 101, 103, 105, 104, 106, 108, 107,
               109, 111, 110, 112, 114]
        close = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
                 111, 113, 112, 114, 116]

        atr = TechnicalIndicators.calculate_atr(high, low, close, period=14)

        assert atr is not None
        assert atr > 0

    def test_atr_high_volatility(self):
        """Test ATR is higher with increased volatility."""
        # Low volatility
        high_low_vol = [102, 103, 104, 103, 104, 105, 104, 105, 106, 105,
                        106, 107, 106, 107, 108]
        low_low_vol = [98, 99, 100, 99, 100, 101, 100, 101, 102, 101,
                       102, 103, 102, 103, 104]
        close_low_vol = [100, 101, 102, 101, 102, 103, 102, 103, 104, 103,
                         104, 105, 104, 105, 106]

        # High volatility
        high_high_vol = [105, 108, 111, 108, 112, 115, 112, 116, 119, 116,
                         120, 123, 120, 124, 127]
        low_high_vol = [95, 92, 89, 92, 88, 85, 88, 84, 81, 84,
                        80, 77, 80, 76, 73]
        close_high_vol = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
                          100, 100, 100, 100, 100]

        atr_low = TechnicalIndicators.calculate_atr(high_low_vol, low_low_vol, close_low_vol, period=14)
        atr_high = TechnicalIndicators.calculate_atr(high_high_vol, low_high_vol, close_high_vol, period=14)

        assert atr_low is not None
        assert atr_high is not None
        assert atr_high > atr_low, "ATR should be higher with increased volatility"

    def test_atr_insufficient_data(self):
        """Test ATR returns None with insufficient data."""
        high = [102, 104, 106]
        low = [98, 100, 102]
        close = [100, 102, 104]

        atr = TechnicalIndicators.calculate_atr(high, low, close, period=14)

        assert atr is None

    def test_atr_mismatched_arrays(self):
        """Test ATR returns None with mismatched array lengths."""
        high = [102, 104, 106, 105, 107]
        low = [98, 100, 102]
        close = [100, 102, 104, 103]

        atr = TechnicalIndicators.calculate_atr(high, low, close, period=14)

        assert atr is None


class TestADXCalculation:
    """Test ADX (Average Directional Index) calculations."""

    def test_adx_basic(self):
        """Test basic ADX calculation."""
        high = [102, 104, 106, 105, 107, 109, 108, 110, 112, 111,
                113, 115, 114, 116, 118, 117, 119, 121, 120, 122,
                124, 123, 125, 127, 126, 128, 130, 129, 131]
        low = [98, 100, 102, 101, 103, 105, 104, 106, 108, 107,
               109, 111, 110, 112, 114, 113, 115, 117, 116, 118,
               120, 119, 121, 123, 122, 124, 126, 125, 127]
        close = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
                 111, 113, 112, 114, 116, 115, 117, 119, 118, 120,
                 122, 121, 123, 125, 124, 126, 128, 127, 129]

        adx = TechnicalIndicators.calculate_adx(high, low, close, period=14)

        assert adx is not None
        assert 0 <= adx <= 100, f"ADX {adx} should be between 0 and 100"

    def test_adx_insufficient_data(self):
        """Test ADX returns None with insufficient data."""
        high = [102, 104, 106]
        low = [98, 100, 102]
        close = [100, 102, 104]

        adx = TechnicalIndicators.calculate_adx(high, low, close, period=14)

        assert adx is None


class TestBollingerBands:
    """Test Bollinger Bands calculations."""

    def test_bollinger_bands_basic(self):
        """Test basic Bollinger Bands calculation."""
        prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
                  111, 113, 112, 114, 116, 115, 117, 119, 118, 120]

        bb = TechnicalIndicators.calculate_bollinger_bands(prices, period=20, std_dev=2.0)

        assert bb is not None
        assert isinstance(bb, BollingerBands)
        assert bb.upper > bb.middle > bb.lower
        assert bb.width_pct > 0

    def test_bollinger_bands_narrow_range(self):
        """Test Bollinger Bands with narrow range (low volatility)."""
        # Low volatility - prices stay close to 100
        prices = [100, 100.1, 99.9, 100, 100.1, 99.9, 100, 100.1, 99.9, 100,
                  100, 100.1, 99.9, 100, 100.1, 99.9, 100, 100.1, 99.9, 100]

        bb = TechnicalIndicators.calculate_bollinger_bands(prices, period=20, std_dev=2.0)

        assert bb is not None
        assert bb.width_pct < 2.0, f"BB width {bb.width_pct}% should be < 2% for low volatility"

    def test_bollinger_bands_wide_range(self):
        """Test Bollinger Bands with wide range (high volatility)."""
        # High volatility
        prices = [100, 110, 90, 105, 95, 112, 88, 107, 93, 115,
                  85, 110, 90, 113, 87, 108, 92, 111, 89, 114]

        bb = TechnicalIndicators.calculate_bollinger_bands(prices, period=20, std_dev=2.0)

        assert bb is not None
        assert bb.width_pct > 5.0, f"BB width {bb.width_pct}% should be > 5% for high volatility"

    def test_bollinger_bands_insufficient_data(self):
        """Test Bollinger Bands returns None with insufficient data."""
        prices = [100, 101, 102]

        bb = TechnicalIndicators.calculate_bollinger_bands(prices, period=20, std_dev=2.0)

        assert bb is None


class TestSMACalculation:
    """Test SMA (Simple Moving Average) calculations."""

    def test_sma_basic(self):
        """Test basic SMA calculation."""
        prices = [100, 102, 104, 106, 108]

        sma = TechnicalIndicators.calculate_sma(prices, period=5)

        assert sma is not None
        expected_sma = sum(prices) / len(prices)
        assert abs(sma - expected_sma) < 0.01, f"SMA {sma} should be approximately {expected_sma}"

    def test_sma_known_values(self):
        """Test SMA with known values."""
        prices = [10, 20, 30, 40, 50]

        sma = TechnicalIndicators.calculate_sma(prices, period=5)

        assert sma == 30.0, f"SMA should be 30.0, got {sma}"

    def test_sma_insufficient_data(self):
        """Test SMA returns None with insufficient data."""
        prices = [100, 101, 102]

        sma = TechnicalIndicators.calculate_sma(prices, period=10)

        assert sma is None

    def test_sma_uses_last_n_values(self):
        """Test SMA only uses the last N values."""
        prices = [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100]

        sma = TechnicalIndicators.calculate_sma(prices, period=5)

        assert sma is not None
        expected_sma = (96 + 97 + 98 + 99 + 100) / 5
        assert abs(sma - expected_sma) < 0.01, f"SMA {sma} should use last 5 values"


class TestIndicatorsEdgeCases:
    """Test edge cases and error handling for all indicators."""

    def test_empty_price_list(self):
        """Test all indicators return None with empty price list."""
        prices = []

        assert TechnicalIndicators.calculate_rsi(prices, period=14) is None
        assert TechnicalIndicators.calculate_ema(prices, period=9) is None
        assert TechnicalIndicators.calculate_sma(prices, period=20) is None
        assert TechnicalIndicators.calculate_bollinger_bands(prices, period=20) is None

    def test_single_price(self):
        """Test all indicators handle single price gracefully."""
        prices = [100]

        assert TechnicalIndicators.calculate_rsi(prices, period=14) is None
        assert TechnicalIndicators.calculate_ema(prices, period=9) is None
        assert TechnicalIndicators.calculate_sma(prices, period=5) is None
        assert TechnicalIndicators.calculate_bollinger_bands(prices, period=20) is None

    def test_zero_prices(self):
        """Test indicators handle zero prices."""
        prices = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # RSI should be 0 or handle gracefully
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        if rsi is not None:
            assert 0 <= rsi <= 100

        # EMAs should be 0
        ema = TechnicalIndicators.calculate_ema(prices, period=9)
        assert ema == 0.0

        # SMA should be 0
        sma = TechnicalIndicators.calculate_sma(prices, period=20)
        assert sma == 0.0

    def test_negative_prices(self):
        """Test indicators handle negative prices (should still work mathematically)."""
        prices = [-100 + i for i in range(20)]

        # Indicators should still calculate (though not meaningful for real prices)
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        assert rsi is not None

        ema = TechnicalIndicators.calculate_ema(prices, period=9)
        assert ema is not None

        sma = TechnicalIndicators.calculate_sma(prices, period=10)
        assert sma is not None
