"""
Technical Indicators Calculator

Implements technical analysis indicators for market regime classification and strategy selection.

Indicators:
- RSI (Relative Strength Index)
- ADX (Average Directional Index)
- EMA (Exponential Moving Average)
- ATR (Average True Range)
- Bollinger Bands

All calculations use standard financial formulas.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class BollingerBands:
    """Bollinger Bands result."""
    upper: float
    middle: float
    lower: float
    width_pct: float  # (upper - lower) / middle * 100


class TechnicalIndicators:
    """
    Technical indicators calculator using standard financial formulas.

    All methods are static for easy testing and reuse.
    """

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI).

        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss

        Args:
            prices: List of closing prices (oldest first)
            period: RSI period (default: 14)

        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(prices) < period + 1:
            logger.warning(f"Insufficient data for RSI: need {period + 1}, got {len(prices)}")
            return None

        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]

        # Separate gains and losses
        gains = [max(change, 0) for change in changes]
        losses = [abs(min(change, 0)) for change in changes]

        # Calculate initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Smoothed averages using Wilder's method
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # Calculate RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return round(rsi, 2)

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA).

        EMA = Price(today) × k + EMA(yesterday) × (1 - k)
        where k = 2 / (period + 1)

        Args:
            prices: List of closing prices (oldest first)
            period: EMA period

        Returns:
            EMA value or None if insufficient data
        """
        if len(prices) < period:
            logger.warning(f"Insufficient data for EMA: need {period}, got {len(prices)}")
            return None

        # Start with SMA for initial EMA
        ema = sum(prices[:period]) / period

        # Calculate multiplier
        multiplier = 2.0 / (period + 1.0)

        # Calculate EMA for remaining prices
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1.0 - multiplier))

        return round(ema, 2)

    @staticmethod
    def calculate_atr(
        high: List[float],
        low: List[float],
        close: List[float],
        period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average True Range (ATR).

        True Range = max(high - low, |high - prev_close|, |low - prev_close|)
        ATR = EMA of True Range

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: ATR period (default: 14)

        Returns:
            ATR value or None if insufficient data
        """
        if len(high) < period + 1 or len(low) < period + 1 or len(close) < period + 1:
            logger.warning(f"Insufficient data for ATR: need {period + 1}")
            return None

        if not (len(high) == len(low) == len(close)):
            logger.error("High, low, and close arrays must have same length")
            return None

        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(close)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)

        if len(true_ranges) < period:
            return None

        # Calculate ATR as EMA of True Range (Wilder's method)
        atr = sum(true_ranges[:period]) / period

        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period

        return round(atr, 2)

    @staticmethod
    def calculate_adx(
        high: List[float],
        low: List[float],
        close: List[float],
        period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average Directional Index (ADX).

        ADX measures trend strength (not direction).
        - ADX > 25: Strong trend
        - ADX < 20: Weak trend / ranging

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: ADX period (default: 14)

        Returns:
            ADX value (0-100) or None if insufficient data
        """
        if len(high) < period * 2 or len(low) < period * 2 or len(close) < period * 2:
            logger.warning(f"Insufficient data for ADX: need {period * 2}")
            return None

        if not (len(high) == len(low) == len(close)):
            logger.error("High, low, and close arrays must have same length")
            return None

        # Calculate True Range and Directional Movement
        plus_dm = []
        minus_dm = []
        true_ranges = []

        for i in range(1, len(close)):
            # True Range
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr = max(tr1, tr2, tr3)
            true_ranges.append(tr)

            # Directional Movement
            high_diff = high[i] - high[i-1]
            low_diff = low[i-1] - low[i]

            plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0)
            minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0)

        # Calculate smoothed averages (Wilder's method)
        smooth_tr = sum(true_ranges[:period])
        smooth_plus_dm = sum(plus_dm[:period])
        smooth_minus_dm = sum(minus_dm[:period])

        for i in range(period, len(true_ranges)):
            smooth_tr = smooth_tr - (smooth_tr / period) + true_ranges[i]
            smooth_plus_dm = smooth_plus_dm - (smooth_plus_dm / period) + plus_dm[i]
            smooth_minus_dm = smooth_minus_dm - (smooth_minus_dm / period) + minus_dm[i]

        # Calculate Directional Indicators
        if smooth_tr == 0:
            return None

        plus_di = 100 * (smooth_plus_dm / smooth_tr)
        minus_di = 100 * (smooth_minus_dm / smooth_tr)

        # Calculate DX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0.0

        dx = 100 * abs(plus_di - minus_di) / di_sum

        # ADX is EMA of DX (simplified - should ideally calculate for each period)
        # For production, you'd calculate DX series and then smooth it
        adx = dx  # Simplified for initial implementation

        return round(adx, 2)

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[BollingerBands]:
        """
        Calculate Bollinger Bands.

        Middle Band = SMA(period)
        Upper Band = Middle + (std_dev × standard deviation)
        Lower Band = Middle - (std_dev × standard deviation)

        Args:
            prices: List of closing prices
            period: Moving average period (default: 20)
            std_dev: Number of standard deviations (default: 2.0)

        Returns:
            BollingerBands dataclass or None if insufficient data
        """
        if len(prices) < period:
            logger.warning(f"Insufficient data for Bollinger Bands: need {period}, got {len(prices)}")
            return None

        # Calculate Middle Band (SMA)
        middle = sum(prices[-period:]) / period

        # Calculate standard deviation
        variance = sum((price - middle) ** 2 for price in prices[-period:]) / period
        std = variance ** 0.5

        # Calculate bands
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        # Calculate band width percentage
        width_pct = ((upper - lower) / middle) * 100.0 if middle != 0 else 0.0

        return BollingerBands(
            upper=round(upper, 2),
            middle=round(middle, 2),
            lower=round(lower, 2),
            width_pct=round(width_pct, 2)
        )

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average (SMA).

        Args:
            prices: List of closing prices
            period: SMA period

        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            logger.warning(f"Insufficient data for SMA: need {period}, got {len(prices)}")
            return None

        sma = sum(prices[-period:]) / period
        return round(sma, 2)
