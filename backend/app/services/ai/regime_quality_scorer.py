"""
Regime Quality Scorer

Calculates regime-conditioned decision quality scores by normalizing
performance relative to historical regime-specific averages.

Priority 2.2: Regime-Conditioned Decision Quality
"""

import logging
from typing import Dict, List, Optional
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_regime_performance import AIRegimePerformance

logger = logging.getLogger(__name__)


class RegimeQualityScorer:
    """
    Normalizes decision quality scores based on market regime context.

    Example:
    - User's 70% win rate in VOLATILE might be better than their 75% in TRENDING_BULLISH
    - Normalized scores show relative performance within each regime
    """

    def __init__(self, lookback_days: int = 90):
        """
        Initialize regime quality scorer.

        Args:
            lookback_days: Number of days to look back for historical averages
        """
        self.lookback_days = lookback_days

    async def get_historical_regime_averages(
        self,
        user_id: UUID,
        regime_type: str,
        db: AsyncSession,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get historical average performance for a regime.

        Args:
            user_id: User ID
            regime_type: Regime type (e.g., 'TRENDING_BULLISH')
            db: Database session
            end_date: End date for lookback (defaults to today)

        Returns:
            Dict with avg_overall_score, avg_win_rate, avg_pnl_per_trade, etc.
        """
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=self.lookback_days)

        # Query historical performance
        stmt = select(
            func.avg(AIRegimePerformance.avg_overall_score).label('avg_overall_score'),
            func.avg(AIRegimePerformance.avg_pnl_score).label('avg_pnl_score'),
            func.avg(AIRegimePerformance.avg_risk_score).label('avg_risk_score'),
            func.avg(AIRegimePerformance.avg_entry_score).label('avg_entry_score'),
            func.avg(AIRegimePerformance.avg_adjustment_score).label('avg_adjustment_score'),
            func.avg(AIRegimePerformance.avg_exit_score).label('avg_exit_score'),
            func.avg(AIRegimePerformance.win_rate).label('avg_win_rate'),
            func.avg(AIRegimePerformance.avg_pnl_per_trade).label('avg_pnl_per_trade'),
            func.count(AIRegimePerformance.id).label('sample_size')
        ).where(
            AIRegimePerformance.user_id == user_id,
            AIRegimePerformance.regime_type == regime_type,
            AIRegimePerformance.report_date >= start_date,
            AIRegimePerformance.report_date < end_date
        )

        result = await db.execute(stmt)
        row = result.one_or_none()

        if not row or row.sample_size == 0:
            logger.info(f"No historical data for {regime_type} regime (user={user_id})")
            return None

        return {
            'avg_overall_score': float(row.avg_overall_score) if row.avg_overall_score else 50.0,
            'avg_pnl_score': float(row.avg_pnl_score) if row.avg_pnl_score else 50.0,
            'avg_risk_score': float(row.avg_risk_score) if row.avg_risk_score else 50.0,
            'avg_entry_score': float(row.avg_entry_score) if row.avg_entry_score else 50.0,
            'avg_adjustment_score': float(row.avg_adjustment_score) if row.avg_adjustment_score else 50.0,
            'avg_exit_score': float(row.avg_exit_score) if row.avg_exit_score else 50.0,
            'avg_win_rate': float(row.avg_win_rate) if row.avg_win_rate else 50.0,
            'avg_pnl_per_trade': float(row.avg_pnl_per_trade) if row.avg_pnl_per_trade else 0.0,
            'sample_size': row.sample_size
        }

    async def normalize_score(
        self,
        current_score: float,
        regime_type: str,
        user_id: UUID,
        db: AsyncSession,
        score_type: str = 'overall'
    ) -> Dict:
        """
        Normalize a score relative to historical regime-specific average.

        Args:
            current_score: Current score to normalize (0-100)
            regime_type: Current regime type
            user_id: User ID
            db: Database session
            score_type: Type of score ('overall', 'pnl', 'risk', etc.)

        Returns:
            Dict with normalized_score, percentile, and interpretation
        """
        # Get historical average for this regime
        historical_avg = await self.get_historical_regime_averages(
            user_id, regime_type, db
        )

        if not historical_avg:
            # No historical data - return neutral normalization
            return {
                'raw_score': current_score,
                'normalized_score': 50.0,
                'historical_avg': None,
                'diff_from_avg': 0.0,
                'percentile': 50.0,
                'interpretation': 'insufficient_data',
                'sample_size': 0
            }

        # Get the relevant historical average
        score_key = f'avg_{score_type}_score' if score_type != 'win_rate' else 'avg_win_rate'
        historical_score = historical_avg.get(score_key, 50.0)

        # Calculate difference from historical average
        diff_from_avg = current_score - historical_score

        # Normalize to 0-100 scale using standard deviation approximation
        # Assume stddev ~= 15 for quality scores (similar to IQ scoring)
        stddev = 15.0
        z_score = diff_from_avg / stddev

        # Convert z-score to percentile (using normal distribution approximation)
        # z_score of 0 = 50th percentile, +1 = 84th, -1 = 16th
        percentile = 50.0 + (z_score * 34.0)  # Approximation
        percentile = max(0.0, min(100.0, percentile))

        # Normalized score (50 = historical average, 100 = top performance)
        normalized_score = 50.0 + (z_score * 15.0)
        normalized_score = max(0.0, min(100.0, normalized_score))

        # Interpretation
        if diff_from_avg >= 10:
            interpretation = 'significantly_above_avg'
        elif diff_from_avg >= 5:
            interpretation = 'above_avg'
        elif diff_from_avg <= -10:
            interpretation = 'significantly_below_avg'
        elif diff_from_avg <= -5:
            interpretation = 'below_avg'
        else:
            interpretation = 'near_avg'

        return {
            'raw_score': current_score,
            'normalized_score': normalized_score,
            'historical_avg': historical_score,
            'diff_from_avg': diff_from_avg,
            'percentile': percentile,
            'interpretation': interpretation,
            'sample_size': historical_avg['sample_size']
        }

    async def get_regime_strengths_weaknesses(
        self,
        user_id: UUID,
        db: AsyncSession,
        lookback_days: Optional[int] = None
    ) -> Dict:
        """
        Identify which regimes user performs best/worst in.

        Args:
            user_id: User ID
            db: Database session
            lookback_days: Override default lookback period

        Returns:
            Dict with strongest_regimes, weakest_regimes, and insights
        """
        if lookback_days is None:
            lookback_days = self.lookback_days

        start_date = date.today() - timedelta(days=lookback_days)

        # Get average performance per regime
        stmt = select(
            AIRegimePerformance.regime_type,
            func.avg(AIRegimePerformance.avg_overall_score).label('avg_score'),
            func.avg(AIRegimePerformance.win_rate).label('avg_win_rate'),
            func.avg(AIRegimePerformance.avg_pnl_per_trade).label('avg_pnl'),
            func.sum(AIRegimePerformance.total_trades).label('total_trades'),
            func.count(AIRegimePerformance.id).label('days_traded')
        ).where(
            AIRegimePerformance.user_id == user_id,
            AIRegimePerformance.report_date >= start_date
        ).group_by(
            AIRegimePerformance.regime_type
        ).order_by(
            func.avg(AIRegimePerformance.avg_overall_score).desc()
        )

        result = await db.execute(stmt)
        regime_stats = result.all()

        if not regime_stats:
            return {
                'strongest_regimes': [],
                'weakest_regimes': [],
                'insights': ['Insufficient data for regime analysis']
            }

        # Convert to list of dicts
        regimes = [
            {
                'regime_type': r.regime_type,
                'avg_score': float(r.avg_score) if r.avg_score else 0.0,
                'avg_win_rate': float(r.avg_win_rate) if r.avg_win_rate else 0.0,
                'avg_pnl': float(r.avg_pnl) if r.avg_pnl else 0.0,
                'total_trades': r.total_trades,
                'days_traded': r.days_traded
            }
            for r in regime_stats
        ]

        # Identify strongest (top 2) and weakest (bottom 2)
        strongest = regimes[:2]
        weakest = regimes[-2:]

        # Generate insights
        insights = []

        if strongest:
            best = strongest[0]
            insights.append(
                f"Best performance in {best['regime_type']} regime "
                f"(avg score: {best['avg_score']:.1f}, win rate: {best['avg_win_rate']:.1f}%)"
            )

        if weakest:
            worst = weakest[-1]
            insights.append(
                f"Weakest performance in {worst['regime_type']} regime "
                f"(avg score: {worst['avg_score']:.1f}, win rate: {worst['avg_win_rate']:.1f}%)"
            )

        # Calculate regime adaptation score
        if len(regimes) >= 3:
            score_variance = sum((r['avg_score'] - 50.0) ** 2 for r in regimes) / len(regimes)
            if score_variance < 100:
                insights.append("Performance is consistent across regimes (good regime adaptation)")
            else:
                insights.append("Performance varies significantly by regime (consider regime-specific strategies)")

        return {
            'strongest_regimes': strongest,
            'weakest_regimes': weakest,
            'all_regimes': regimes,
            'insights': insights
        }


__all__ = ["RegimeQualityScorer"]
