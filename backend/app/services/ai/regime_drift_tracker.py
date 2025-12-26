"""
Regime Drift Tracker Service

Tracks market regime stability and detects drift (frequent regime changes).
Implements Priority 1.3: Regime Drift Detection.

Features:
- Regime history tracking
- Stability score calculation (0-100)
- Drift detection (rapid regime changes)
- Confidence decay during unstable periods
- Auto-tightening of thresholds during drift
"""

import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.ai import AIUserConfig
from app.models.ai_regime_history import AIRegimeHistory
from app.services.ai.market_regime import RegimeType, RegimeResult

logger = logging.getLogger(__name__)


class DriftSeverity:
    """Drift severity levels"""
    STABLE = "STABLE"           # No drift detected
    MINOR = "MINOR"             # Small amount of drift
    MODERATE = "MODERATE"       # Moderate drift
    SEVERE = "SEVERE"           # Severe drift - high instability


class RegimeDriftTracker:
    """
    Tracks regime classification history and detects drift.

    Drift occurs when:
    - Regime changes frequently (high change rate)
    - Regime confidence is declining
    - Predictions don't match realized regimes
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_regime(
        self,
        regime_result: RegimeResult,
        underlying: str = "NIFTY"
    ) -> AIRegimeHistory:
        """
        Record a regime classification to history.

        Args:
            regime_result: RegimeResult from MarketRegimeClassifier
            underlying: Underlying symbol

        Returns:
            AIRegimeHistory record
        """
        # Check if regime changed from previous
        prev_regime = await self._get_latest_regime(underlying)
        regime_changed = "N"

        if prev_regime and prev_regime.regime_type != regime_result.regime_type.value:
            regime_changed = "Y"
            logger.info(
                f"Regime change detected for {underlying}: "
                f"{prev_regime.regime_type} → {regime_result.regime_type.value}"
            )

        # Create history record
        history_record = AIRegimeHistory(
            underlying=underlying,
            regime_type=regime_result.regime_type.value,
            confidence=Decimal(str(regime_result.confidence)),
            indicators={
                "spot_price": regime_result.indicators.spot_price,
                "vix": regime_result.indicators.vix,
                "rsi_14": regime_result.indicators.rsi_14,
                "adx_14": regime_result.indicators.adx_14,
                "ema_50": regime_result.indicators.ema_50,
                "bb_width_pct": regime_result.indicators.bb_width_pct,
            },
            reasoning=regime_result.reasoning[:500] if regime_result.reasoning else None,
            regime_changed=regime_changed
        )

        self.db.add(history_record)
        await self.db.commit()
        await self.db.refresh(history_record)

        logger.info(
            f"Recorded regime for {underlying}: {regime_result.regime_type.value} "
            f"(confidence={regime_result.confidence:.1f}%)"
        )

        return history_record

    async def calculate_stability_score(
        self,
        underlying: str = "NIFTY",
        lookback_periods: Optional[int] = None
    ) -> Dict:
        """
        Calculate regime stability score (0-100).

        Higher score = more stable (fewer regime changes).
        Lower score = unstable (frequent regime changes).

        Formula:
            Stability = 100 - (Change Rate × 100)
            Change Rate = # of regime changes / total periods

        Args:
            underlying: Underlying symbol
            lookback_periods: Number of periods to analyze (from config if None)

        Returns:
            {
                "stability_score": float (0-100),
                "total_periods": int,
                "regime_changes": int,
                "change_rate": float (0-1),
                "current_regime": str,
                "drift_severity": str
            }
        """
        # Get user config for lookback periods
        if lookback_periods is None:
            config = await self._get_any_user_config()
            lookback_periods = config.drift_lookback_periods if config else 20

        # Get recent history
        history = await self._get_recent_history(underlying, limit=lookback_periods)

        if len(history) < 2:
            logger.warning(f"Insufficient history for stability calculation: {len(history)} periods")
            return {
                "stability_score": 100.0,  # Assume stable if no data
                "total_periods": len(history),
                "regime_changes": 0,
                "change_rate": 0.0,
                "current_regime": history[0].regime_type if history else "UNKNOWN",
                "drift_severity": DriftSeverity.STABLE
            }

        # Count regime changes
        changes = sum(1 for h in history if h.regime_changed == "Y")
        total_periods = len(history)
        change_rate = changes / total_periods if total_periods > 0 else 0.0

        # Calculate stability score (inverse of change rate)
        stability_score = 100.0 - (change_rate * 100.0)

        # Determine drift severity
        if change_rate < 0.2:  # < 20% change rate
            drift_severity = DriftSeverity.STABLE
        elif change_rate < 0.4:  # 20-40% change rate
            drift_severity = DriftSeverity.MINOR
        elif change_rate < 0.6:  # 40-60% change rate
            drift_severity = DriftSeverity.MODERATE
        else:  # > 60% change rate
            drift_severity = DriftSeverity.SEVERE

        logger.info(
            f"Stability for {underlying}: {stability_score:.1f}% "
            f"(changes={changes}/{total_periods}, severity={drift_severity})"
        )

        return {
            "stability_score": stability_score,
            "total_periods": total_periods,
            "regime_changes": changes,
            "change_rate": change_rate,
            "current_regime": history[0].regime_type,
            "drift_severity": drift_severity
        }

    async def detect_drift(
        self,
        underlying: str = "NIFTY",
        lookback_periods: Optional[int] = None
    ) -> Tuple[bool, str, Dict]:
        """
        Detect if regime drift is occurring.

        Drift is detected when:
        1. Stability score below threshold
        2. Recent regime changes are frequent
        3. Confidence is declining

        Returns:
            (is_drifting: bool, reason: str, metrics: Dict)
        """
        stability_metrics = await self.calculate_stability_score(
            underlying=underlying,
            lookback_periods=lookback_periods
        )

        # Get drift threshold from config
        config = await self._get_any_user_config()
        drift_threshold = float(config.drift_threshold) if config else 30.0

        # Check if drift detected
        is_drifting = stability_metrics["stability_score"] < drift_threshold

        if is_drifting:
            reason = (
                f"Regime drift detected: stability {stability_metrics['stability_score']:.1f}% "
                f"below threshold {drift_threshold}% "
                f"({stability_metrics['regime_changes']} changes in {stability_metrics['total_periods']} periods)"
            )
            logger.warning(f"Drift alert for {underlying}: {reason}")
        else:
            reason = (
                f"Regime stable: {stability_metrics['stability_score']:.1f}% "
                f"(threshold: {drift_threshold}%)"
            )

        return is_drifting, reason, stability_metrics

    async def get_confidence_adjustment(
        self,
        base_confidence: float,
        underlying: str = "NIFTY"
    ) -> Dict:
        """
        Calculate confidence adjustment based on regime drift.

        During drift, confidence is reduced to be more conservative.

        Args:
            base_confidence: Original confidence score (0-100)
            underlying: Underlying symbol

        Returns:
            {
                "adjusted_confidence": float,
                "confidence_penalty": float,
                "drift_detected": bool,
                "stability_score": float
            }
        """
        is_drifting, reason, metrics = await self.detect_drift(underlying)

        if not is_drifting:
            return {
                "adjusted_confidence": base_confidence,
                "confidence_penalty": 0.0,
                "drift_detected": False,
                "stability_score": metrics["stability_score"]
            }

        # Get penalty from config
        config = await self._get_any_user_config()
        penalty_pct = float(config.drift_confidence_penalty) if config else 10.0

        # Apply penalty
        adjusted_confidence = max(0.0, base_confidence - penalty_pct)

        logger.info(
            f"Confidence adjustment for {underlying}: "
            f"{base_confidence:.1f}% → {adjusted_confidence:.1f}% "
            f"(penalty={penalty_pct}% due to drift)"
        )

        return {
            "adjusted_confidence": adjusted_confidence,
            "confidence_penalty": penalty_pct,
            "drift_detected": True,
            "stability_score": metrics["stability_score"]
        }

    async def update_user_stability_score(self, user_id, underlying: str = "NIFTY") -> None:
        """
        Update user's current_regime_stability field.

        This is called periodically by AI monitor to keep stability score current.
        """
        metrics = await self.calculate_stability_score(underlying)

        # Update user config
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if config and config.enable_drift_detection:
            config.current_regime_stability = Decimal(str(metrics["stability_score"]))
            config.last_drift_check_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                f"Updated stability score for user {user_id}: "
                f"{metrics['stability_score']:.1f}%"
            )

    async def should_pause_due_to_drift(
        self,
        user_id,
        underlying: str = "NIFTY"
    ) -> Tuple[bool, str]:
        """
        Determine if trading should be paused due to excessive drift.

        Returns:
            (should_pause: bool, reason: str)
        """
        # Get user config
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config or not config.enable_drift_detection:
            return False, ""

        # Check stability score
        stability_metrics = await self.calculate_stability_score(underlying)

        if stability_metrics["stability_score"] < config.min_regime_stability_score:
            reason = (
                f"Regime instability detected: stability {stability_metrics['stability_score']:.1f}% "
                f"below minimum {config.min_regime_stability_score}% "
                f"(drift severity: {stability_metrics['drift_severity']})"
            )
            logger.warning(f"Trading paused for user {user_id}: {reason}")
            return True, reason

        return False, ""

    async def get_regime_history(
        self,
        underlying: str = "NIFTY",
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent regime history.

        Returns list of regime snapshots for charting/analysis.
        """
        history = await self._get_recent_history(underlying, limit=limit)

        return [
            {
                "id": h.id,
                "regime_type": h.regime_type,
                "confidence": float(h.confidence),
                "classified_at": h.classified_at.isoformat(),
                "regime_changed": h.regime_changed == "Y",
                "indicators": h.indicators
            }
            for h in history
        ]

    async def clear_old_history(
        self,
        underlying: str = "NIFTY",
        days_to_keep: int = 90
    ) -> int:
        """
        Clear regime history older than specified days (admin/maintenance).

        Returns number of records deleted.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        query = select(AIRegimeHistory).where(
            and_(
                AIRegimeHistory.underlying == underlying,
                AIRegimeHistory.classified_at < cutoff_date
            )
        )
        result = await self.db.execute(query)
        old_records = result.scalars().all()

        count = len(old_records)

        for record in old_records:
            await self.db.delete(record)

        await self.db.commit()

        logger.info(f"Cleared {count} old regime history records for {underlying}")
        return count

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _get_latest_regime(self, underlying: str) -> Optional[AIRegimeHistory]:
        """Get most recent regime record for underlying"""
        query = select(AIRegimeHistory).where(
            AIRegimeHistory.underlying == underlying
        ).order_by(desc(AIRegimeHistory.classified_at)).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_recent_history(
        self,
        underlying: str,
        limit: int = 20
    ) -> List[AIRegimeHistory]:
        """Get recent regime history"""
        query = select(AIRegimeHistory).where(
            AIRegimeHistory.underlying == underlying
        ).order_by(desc(AIRegimeHistory.classified_at)).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_any_user_config(self) -> Optional[AIUserConfig]:
        """Get any user's config for default settings (used when user_id not available)"""
        query = select(AIUserConfig).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


__all__ = ["RegimeDriftTracker", "DriftSeverity"]
