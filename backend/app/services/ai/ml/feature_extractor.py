"""
Feature Extractor for ML Strategy Scorer

Extracts features from market data for ML model training and prediction.
Features include market state, technical indicators, options data, and time features.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, time

from app.services.ai.market_regime import RegimeType

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse, IndicatorsSnapshotResponse


# Feature list (30 features total)
FEATURE_NAMES = [
    # Market State (7 features)
    "regime_TRENDING_BULLISH",
    "regime_TRENDING_BEARISH",
    "regime_RANGEBOUND",
    "regime_VOLATILE",
    "regime_PRE_EVENT",
    "regime_EVENT_DAY",
    "vix_level",

    # Technical Indicators (8 features)
    "rsi_14",
    "adx_14",
    "atr_14_pct",
    "bb_width_pct",
    "spot_distance_from_ema50_pct",
    "ema_9_21_cross",  # 1 if EMA9 > EMA21, else 0
    "ema_21_50_cross",  # 1 if EMA21 > EMA50, else 0
    "regime_confidence",

    # Options Data (4 features - would be calculated from real data)
    "iv_rank",  # Placeholder
    "iv_percentile",  # Placeholder
    "oi_pcr",  # Placeholder
    "max_pain_distance_pct",  # Placeholder

    # Time Features (6 features)
    "day_of_week",  # 0=Monday, 4=Friday
    "hour_of_day",
    "minutes_since_open",
    "is_first_hour",  # 1 if within first hour, else 0
    "is_last_hour",  # 1 if within last hour, else 0
    "dte",  # Days to expiry (for weekly: 0-4, for monthly: 0-30)

    # Strategy Features (5 features - added during scoring)
    "strategy_iron_condor",
    "strategy_spread",
    "strategy_straddle",
    "strategy_other",
    "expected_premium_pct",  # Placeholder
]


class FeatureExtractor:
    """
    Extracts ML features from market data and regime information.

    Features are normalized and one-hot encoded where appropriate.
    """

    def __init__(self):
        self.feature_count = len(FEATURE_NAMES)

    def extract_features(
        self,
        regime: "RegimeResponse",
        strategy_name: str,
        current_time: Optional[datetime] = None
    ) -> np.ndarray:
        """
        Extract feature vector from regime data and strategy.

        Args:
            regime: Current market regime classification
            strategy_name: Name of strategy being scored
            current_time: Current timestamp (defaults to now)

        Returns:
            NumPy array of shape (30,) with normalized features
        """
        if current_time is None:
            current_time = datetime.now()

        features = np.zeros(self.feature_count)

        # Market State Features (regime one-hot encoding)
        regime_idx = self._get_regime_index(regime.regime_type)
        if regime_idx < 6:
            features[regime_idx] = 1.0

        # VIX level (normalized to 0-1 range, assuming VIX 10-50)
        vix = regime.indicators.vix or 15.0
        features[6] = self._normalize(vix, min_val=10, max_val=50)

        # Technical Indicators
        features[7] = self._normalize(regime.indicators.rsi_14 or 50, min_val=0, max_val=100)
        features[8] = self._normalize(regime.indicators.adx_14 or 20, min_val=0, max_val=60)

        # ATR as percentage of spot
        atr_pct = ((regime.indicators.atr_14 or 0) / regime.indicators.spot_price) * 100 if regime.indicators.spot_price else 0
        features[9] = self._normalize(atr_pct, min_val=0, max_val=5)

        # BB width percentage
        features[10] = self._normalize(regime.indicators.bb_width_pct or 2, min_val=0, max_val=10)

        # Distance from EMA50
        distance_pct = ((regime.indicators.spot_price - regime.indicators.ema_50) / regime.indicators.ema_50 * 100) if regime.indicators.ema_50 else 0
        features[11] = self._normalize(distance_pct, min_val=-10, max_val=10)

        # EMA crosses
        features[12] = 1.0 if (regime.indicators.ema_9 or 0) > (regime.indicators.ema_21 or 0) else 0.0
        features[13] = 1.0 if (regime.indicators.ema_21 or 0) > (regime.indicators.ema_50 or 0) else 0.0

        # Regime confidence (already 0-100)
        features[14] = self._normalize(regime.confidence, min_val=0, max_val=100)

        # Options Data (placeholders - would be calculated from real data)
        features[15] = 0.5  # iv_rank
        features[16] = 0.5  # iv_percentile
        features[17] = 1.0  # oi_pcr
        features[18] = 0.0  # max_pain_distance_pct

        # Time Features
        features[19] = current_time.weekday() / 4.0  # 0-4 normalized to 0-1
        features[20] = current_time.hour / 23.0  # 0-23 normalized to 0-1

        # Minutes since market open (9:15 AM)
        market_open = time(9, 15)
        if current_time.time() >= market_open:
            open_dt = current_time.replace(hour=9, minute=15, second=0)
            minutes_since_open = (current_time - open_dt).total_seconds() / 60
            features[21] = self._normalize(minutes_since_open, min_val=0, max_val=375)  # 6.25 hours
        else:
            features[21] = 0.0

        # Is first hour (9:15-10:15)
        features[22] = 1.0 if 9 <= current_time.hour < 11 else 0.0

        # Is last hour (14:30-15:30)
        features[23] = 1.0 if 14 <= current_time.hour < 16 else 0.0

        # DTE (placeholder - would calculate from expiry date)
        features[24] = 0.5  # Normalized DTE

        # Strategy Features (one-hot encoding)
        strategy_idx = self._get_strategy_index(strategy_name)
        if strategy_idx < 4:
            features[25 + strategy_idx] = 1.0

        # Expected premium percentage (placeholder)
        features[29] = 0.5

        return features

    def extract_features_batch(
        self,
        regimes: List["RegimeResponse"],
        strategy_names: List[str],
        timestamps: Optional[List[datetime]] = None
    ) -> np.ndarray:
        """
        Extract features for a batch of samples.

        Args:
            regimes: List of regime responses
            strategy_names: List of strategy names
            timestamps: List of timestamps (optional)

        Returns:
            NumPy array of shape (N, 30) with features for each sample
        """
        if timestamps is None:
            timestamps = [datetime.now()] * len(regimes)

        features_list = []
        for regime, strategy, timestamp in zip(regimes, strategy_names, timestamps):
            features = self.extract_features(regime, strategy, timestamp)
            features_list.append(features)

        return np.array(features_list)

    def get_feature_names(self) -> List[str]:
        """Get list of feature names."""
        return FEATURE_NAMES.copy()

    # Helper methods

    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range."""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return np.clip(normalized, 0.0, 1.0)

    def _get_regime_index(self, regime_type) -> int:
        """Get index for regime one-hot encoding."""
        regime_map = {
            RegimeType.TRENDING_BULLISH: 0,
            RegimeType.TRENDING_BEARISH: 1,
            RegimeType.RANGEBOUND: 2,
            RegimeType.VOLATILE: 3,
            RegimeType.PRE_EVENT: 4,
            RegimeType.EVENT_DAY: 5,
        }

        # Handle both enum and string
        if isinstance(regime_type, str):
            try:
                regime_type = RegimeType[regime_type]
            except (KeyError, AttributeError):
                return 6  # Unknown

        return regime_map.get(regime_type, 6)

    def _get_strategy_index(self, strategy_name: str) -> int:
        """Get index for strategy one-hot encoding."""
        if "condor" in strategy_name.lower():
            return 0  # iron_condor
        elif "spread" in strategy_name.lower():
            return 1  # spread
        elif "straddle" in strategy_name.lower() or "strangle" in strategy_name.lower():
            return 2  # straddle
        else:
            return 3  # other


__all__ = ["FeatureExtractor", "FEATURE_NAMES"]
