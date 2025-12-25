"""
Market Regime Classifier

Rule-based market regime classification using technical indicators.

Regime Types:
- TRENDING_BULLISH: ADX > 25, Price > EMA50, RSI < 70
- TRENDING_BEARISH: ADX > 25, Price < EMA50, RSI > 30
- RANGEBOUND: ADX < 20, BB Width < 2%
- VOLATILE: VIX > 20 OR ATR > 1.5x average
- PRE_EVENT: 1-2 days before major events (Budget, RBI, Expiry)
- EVENT_DAY: Budget day, RBI policy, major earnings
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional, List, Tuple
from decimal import Decimal

from kiteconnect import KiteConnect
import redis.asyncio as redis

from app.services.ai.indicators import TechnicalIndicators
from app.services.ai.historical_data import HistoricalDataService, OHLC
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class RegimeType(str, Enum):
    """Market regime types."""
    TRENDING_BULLISH = "TRENDING_BULLISH"
    TRENDING_BEARISH = "TRENDING_BEARISH"
    RANGEBOUND = "RANGEBOUND"
    VOLATILE = "VOLATILE"
    PRE_EVENT = "PRE_EVENT"
    EVENT_DAY = "EVENT_DAY"
    UNKNOWN = "UNKNOWN"


@dataclass
class IndicatorsSnapshot:
    """
    Snapshot of all calculated indicators at a point in time.
    """
    underlying: str
    timestamp: datetime

    # Price Data
    spot_price: float
    vix: Optional[float]

    # Trend Indicators
    rsi_14: Optional[float]
    adx_14: Optional[float]
    ema_9: Optional[float]
    ema_21: Optional[float]
    ema_50: Optional[float]

    # Volatility Indicators
    atr_14: Optional[float]
    bb_upper: Optional[float]
    bb_middle: Optional[float]
    bb_lower: Optional[float]
    bb_width_pct: Optional[float]


@dataclass
class RegimeResult:
    """Market regime classification result."""
    regime_type: RegimeType
    confidence: float  # 0-100
    indicators: IndicatorsSnapshot
    reasoning: str  # Why this regime was selected


class MarketRegimeClassifier:
    """
    Classifies market regime using rule-based technical analysis.

    Uses historical data to calculate indicators and determine current regime.
    """

    # Event calendar (simplified - in production, fetch from external API)
    EVENT_DATES = {
        # Budget days (usually Feb 1)
        date(2025, 2, 1): "Budget",
        # RBI Policy (usually every 2 months)
        date(2025, 2, 7): "RBI Policy",
        date(2025, 4, 9): "RBI Policy",
        date(2025, 6, 6): "RBI Policy",
        # Weekly expiry (Thursdays)
        # Monthly expiry (last Thursday)
    }

    def __init__(
        self,
        kite: KiteConnect,
        market_data: MarketDataService,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize Market Regime Classifier.

        Args:
            kite: KiteConnect instance
            market_data: MarketDataService for current prices
            redis_client: Optional Redis client for historical data caching
        """
        self.kite = kite
        self.market_data = market_data
        self.historical_data = HistoricalDataService(kite, redis_client)
        self.indicators = TechnicalIndicators()

    async def classify(self, underlying: str) -> RegimeResult:
        """
        Classify current market regime for underlying.

        Args:
            underlying: Index name (NIFTY, BANKNIFTY, etc.)

        Returns:
            RegimeResult with regime type, confidence, and reasoning
        """
        try:
            # Step 1: Get indicators snapshot
            snapshot = await self.get_indicators_snapshot(underlying)

            # Step 2: Check for event days first (highest priority)
            is_event, event_name = self.is_event_day(date.today())
            if is_event:
                return RegimeResult(
                    regime_type=RegimeType.EVENT_DAY,
                    confidence=100.0,
                    indicators=snapshot,
                    reasoning=f"Event Day: {event_name}"
                )

            # Step 3: Check for pre-event (1-2 days before)
            is_pre_event, days_to_event, event_name = self.is_pre_event(date.today())
            if is_pre_event:
                return RegimeResult(
                    regime_type=RegimeType.PRE_EVENT,
                    confidence=80.0 + (10.0 if days_to_event == 1 else 0),
                    indicators=snapshot,
                    reasoning=f"Pre-Event: {days_to_event} day(s) before {event_name}"
                )

            # Step 4: Check for volatile regime (VIX or ATR based)
            volatile_result = self._check_volatile_regime(snapshot)
            if volatile_result:
                return volatile_result

            # Step 5: Check for trending regime (ADX based)
            trending_result = self._check_trending_regime(snapshot)
            if trending_result:
                return trending_result

            # Step 6: Check for rangebound regime
            rangebound_result = self._check_rangebound_regime(snapshot)
            if rangebound_result:
                return rangebound_result

            # Default: Unknown
            return RegimeResult(
                regime_type=RegimeType.UNKNOWN,
                confidence=0.0,
                indicators=snapshot,
                reasoning="Insufficient data or mixed signals"
            )

        except Exception as e:
            logger.error(f"Error classifying regime for {underlying}: {e}")
            raise

    async def get_indicators_snapshot(self, underlying: str) -> IndicatorsSnapshot:
        """
        Calculate all indicators for the current market state.

        Args:
            underlying: Index name

        Returns:
            IndicatorsSnapshot with all calculated values
        """
        try:
            # Get current spot price and VIX
            spot_data = await self.market_data.get_spot_price(underlying)
            spot_price = float(spot_data.ltp)

            vix_data = await self.market_data.get_vix()
            vix = float(vix_data) if vix_data else None

            # Get historical daily data for indicators (50 days)
            daily_candles = await self.historical_data.get_daily_candles(underlying, days=50)

            if len(daily_candles) < 20:
                logger.warning(f"Insufficient historical data for {underlying}: {len(daily_candles)} candles")

            # Extract price arrays
            closes = [candle.close for candle in daily_candles]
            highs = [candle.high for candle in daily_candles]
            lows = [candle.low for candle in daily_candles]

            # Calculate trend indicators
            rsi_14 = self.indicators.calculate_rsi(closes, period=14)
            adx_14 = self.indicators.calculate_adx(highs, lows, closes, period=14)
            ema_9 = self.indicators.calculate_ema(closes, period=9)
            ema_21 = self.indicators.calculate_ema(closes, period=21)
            ema_50 = self.indicators.calculate_ema(closes, period=50)

            # Calculate volatility indicators
            atr_14 = self.indicators.calculate_atr(highs, lows, closes, period=14)
            bb = self.indicators.calculate_bollinger_bands(closes, period=20, std_dev=2.0)

            return IndicatorsSnapshot(
                underlying=underlying,
                timestamp=datetime.now(),
                spot_price=spot_price,
                vix=vix,
                rsi_14=rsi_14,
                adx_14=adx_14,
                ema_9=ema_9,
                ema_21=ema_21,
                ema_50=ema_50,
                atr_14=atr_14,
                bb_upper=bb.upper if bb else None,
                bb_middle=bb.middle if bb else None,
                bb_lower=bb.lower if bb else None,
                bb_width_pct=bb.width_pct if bb else None
            )

        except Exception as e:
            logger.error(f"Error getting indicators snapshot: {e}")
            raise

    def _check_volatile_regime(self, snapshot: IndicatorsSnapshot) -> Optional[RegimeResult]:
        """Check if market is in volatile regime."""
        reasons = []
        confidence = 0.0

        # VIX > 20
        if snapshot.vix and snapshot.vix > 20:
            reasons.append(f"VIX {snapshot.vix:.2f} > 20")
            confidence += 50.0

        # ATR > 1.5x average (simplified: just check if ATR is high relative to price)
        if snapshot.atr_14 and snapshot.spot_price:
            atr_pct = (snapshot.atr_14 / snapshot.spot_price) * 100
            if atr_pct > 1.5:
                reasons.append(f"ATR {atr_pct:.2f}% > 1.5%")
                confidence += 40.0

        # Bollinger Band width > 3% indicates high volatility
        if snapshot.bb_width_pct and snapshot.bb_width_pct > 3.0:
            reasons.append(f"BB Width {snapshot.bb_width_pct:.2f}% > 3%")
            confidence += 30.0

        if confidence >= 50.0:
            return RegimeResult(
                regime_type=RegimeType.VOLATILE,
                confidence=min(confidence, 100.0),
                indicators=snapshot,
                reasoning=f"Volatile regime: {', '.join(reasons)}"
            )

        return None

    def _check_trending_regime(self, snapshot: IndicatorsSnapshot) -> Optional[RegimeResult]:
        """Check if market is in trending regime (bullish or bearish)."""
        if not snapshot.adx_14 or snapshot.adx_14 < 25:
            return None  # Not trending

        if not snapshot.ema_50 or not snapshot.rsi_14:
            return None  # Insufficient data

        # ADX > 25 indicates trend
        confidence = min((snapshot.adx_14 - 25) * 2, 40.0)  # Max 40 from ADX

        # Check direction
        if snapshot.spot_price > snapshot.ema_50:
            # Bullish trend
            if snapshot.rsi_14 < 70:  # Not overbought
                confidence += 30.0
                reasons = [
                    f"ADX {snapshot.adx_14:.2f} > 25 (trending)",
                    f"Price {snapshot.spot_price:.2f} > EMA50 {snapshot.ema_50:.2f}",
                    f"RSI {snapshot.rsi_14:.2f} < 70 (not overbought)"
                ]
                return RegimeResult(
                    regime_type=RegimeType.TRENDING_BULLISH,
                    confidence=min(confidence, 100.0),
                    indicators=snapshot,
                    reasoning=f"Bullish trend: {', '.join(reasons)}"
                )
        else:
            # Bearish trend
            if snapshot.rsi_14 > 30:  # Not oversold
                confidence += 30.0
                reasons = [
                    f"ADX {snapshot.adx_14:.2f} > 25 (trending)",
                    f"Price {snapshot.spot_price:.2f} < EMA50 {snapshot.ema_50:.2f}",
                    f"RSI {snapshot.rsi_14:.2f} > 30 (not oversold)"
                ]
                return RegimeResult(
                    regime_type=RegimeType.TRENDING_BEARISH,
                    confidence=min(confidence, 100.0),
                    indicators=snapshot,
                    reasoning=f"Bearish trend: {', '.join(reasons)}"
                )

        return None

    def _check_rangebound_regime(self, snapshot: IndicatorsSnapshot) -> Optional[RegimeResult]:
        """Check if market is in rangebound regime."""
        reasons = []
        confidence = 0.0

        # ADX < 20 (weak trend)
        if snapshot.adx_14 and snapshot.adx_14 < 20:
            reasons.append(f"ADX {snapshot.adx_14:.2f} < 20 (no trend)")
            confidence += 40.0

        # Bollinger Band width < 2% (low volatility)
        if snapshot.bb_width_pct and snapshot.bb_width_pct < 2.0:
            reasons.append(f"BB Width {snapshot.bb_width_pct:.2f}% < 2% (low volatility)")
            confidence += 40.0

        # RSI between 40-60 (neutral)
        if snapshot.rsi_14 and 40 <= snapshot.rsi_14 <= 60:
            reasons.append(f"RSI {snapshot.rsi_14:.2f} neutral (40-60)")
            confidence += 20.0

        if confidence >= 60.0:
            return RegimeResult(
                regime_type=RegimeType.RANGEBOUND,
                confidence=min(confidence, 100.0),
                indicators=snapshot,
                reasoning=f"Rangebound regime: {', '.join(reasons)}"
            )

        return None

    def is_event_day(self, check_date: date) -> Tuple[bool, str]:
        """
        Check if date is a known event day.

        Args:
            check_date: Date to check

        Returns:
            (is_event, event_name)
        """
        # Check weekly expiry (Thursday)
        if check_date.weekday() == 3:  # Thursday
            # Check if it's the last Thursday (monthly expiry)
            next_week = check_date + timedelta(days=7)
            if next_week.month != check_date.month:
                return (True, "Monthly Expiry")
            return (True, "Weekly Expiry")

        # Check predefined events
        if check_date in self.EVENT_DATES:
            return (True, self.EVENT_DATES[check_date])

        return (False, "")

    def is_pre_event(self, check_date: date) -> Tuple[bool, int, str]:
        """
        Check if date is 1-2 days before an event.

        Args:
            check_date: Date to check

        Returns:
            (is_pre_event, days_to_event, event_name)
        """
        for days_ahead in [1, 2]:
            future_date = check_date + timedelta(days=days_ahead)
            is_event, event_name = self.is_event_day(future_date)
            if is_event:
                return (True, days_ahead, event_name)

        return (False, 0, "")

    async def classify_historical(
        self,
        underlying: str,
        historical_date: datetime,
        ohlc_data: List[OHLC]
    ) -> RegimeResult:
        """
        Classify market regime for historical date using historical OHLC data.

        Args:
            underlying: Index symbol
            historical_date: Date to classify
            ohlc_data: Historical OHLC data (should include enough history for indicators)

        Returns:
            RegimeResult for the historical date
        """
        try:
            # Calculate indicators from historical OHLC data
            indicators_service = TechnicalIndicators()

            # Extract close prices for indicator calculation
            close_prices = [float(ohlc.close) for ohlc in ohlc_data]
            high_prices = [float(ohlc.high) for ohlc in ohlc_data]
            low_prices = [float(ohlc.low) for ohlc in ohlc_data]

            # Calculate indicators
            rsi = indicators_service.calculate_rsi(close_prices, period=14)
            adx = indicators_service.calculate_adx(high_prices, low_prices, close_prices, period=14)
            ema_50 = indicators_service.calculate_ema(close_prices, period=50)
            atr = indicators_service.calculate_atr(high_prices, low_prices, close_prices, period=14)
            bb_bands = indicators_service.calculate_bollinger_bands(close_prices, period=20, std_dev=2)

            # Get spot price from last OHLC
            spot_price = float(ohlc_data[-1].close)

            # Create indicators snapshot
            indicators = IndicatorsSnapshot(
                underlying=underlying,
                timestamp=historical_date,
                spot_price=spot_price,
                vix=None,  # VIX not available for historical backtest
                rsi_14=rsi[-1] if rsi else None,
                adx_14=adx[-1] if adx else None,
                ema_9=None,
                ema_21=None,
                ema_50=ema_50[-1] if ema_50 else None,
                atr_14=atr[-1] if atr else None,
                bb_upper=bb_bands['upper'][-1] if bb_bands and bb_bands['upper'] else None,
                bb_middle=bb_bands['middle'][-1] if bb_bands and bb_bands['middle'] else None,
                bb_lower=bb_bands['lower'][-1] if bb_bands and bb_bands['lower'] else None,
                bb_width_pct=bb_bands['width_pct'][-1] if bb_bands and bb_bands['width_pct'] else None
            )

            # Use same classification logic as live classify
            regime_type, confidence, reasoning = self._classify_regime(indicators)

            return RegimeResult(
                regime_type=regime_type,
                confidence=confidence,
                indicators=indicators,
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"Error classifying historical regime for {underlying} on {historical_date}: {e}")
            # Return UNKNOWN regime on error
            return RegimeResult(
                regime_type=RegimeType.UNKNOWN,
                confidence=0.0,
                indicators=IndicatorsSnapshot(
                    underlying=underlying,
                    timestamp=historical_date,
                    spot_price=0.0,
                    vix=None,
                    rsi_14=None,
                    adx_14=None,
                    ema_9=None,
                    ema_21=None,
                    ema_50=None,
                    atr_14=None,
                    bb_upper=None,
                    bb_middle=None,
                    bb_lower=None,
                    bb_width_pct=None
                ),
                reasoning=f"Error: {str(e)}"
            )
