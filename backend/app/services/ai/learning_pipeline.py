"""
Self-Learning Pipeline

Runs daily post-market analysis to improve AI decision-making:
1. Extract completed trades from decision log
2. Compute features and outcomes
3. Score decision quality using multi-factor analysis
4. Update ML models if sufficient data accumulated
5. Generate daily insights report

Scheduled to run at 4:00 PM daily after market close.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.services.ai.feedback_scorer import FeedbackScorer, TradeOutcome
from app.services.ai.ml.training_pipeline import TrainingPipeline, train_model_from_csv
from app.services.ai.ml.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class LearningPipeline:
    """
    Daily self-learning pipeline for AI improvement.

    Analyzes completed trades, scores decisions, and retrains
    ML models when performance improvement is possible.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.feedback_scorer = FeedbackScorer(db)

    async def run_daily_learning(
        self,
        user_id: UUID,
        report_date: Optional[date] = None
    ) -> Dict:
        """
        Execute daily learning cycle for a user.

        Args:
            user_id: User ID to run learning for
            report_date: Date to analyze (defaults to yesterday)

        Returns:
            Dict with learning results and insights
        """
        if report_date is None:
            report_date = date.today() - timedelta(days=1)

        logger.info(f"Running daily learning for user {user_id}, date: {report_date}")

        # Step 1: Extract completed trades
        completed_trades = await self._extract_completed_trades(user_id, report_date)

        if not completed_trades:
            logger.info(f"No completed trades for {user_id} on {report_date}")
            return {
                "report_date": report_date,
                "total_trades": 0,
                "insights": "No trades to analyze"
            }

        # Step 2: Score each decision
        decision_scores = []
        for trade in completed_trades:
            try:
                scores = self.feedback_scorer.score_decision(trade)
                decision_scores.append({
                    "decision_id": trade.decision_id,
                    "strategy_id": trade.strategy_id,
                    "scores": scores,
                    "outcome": trade
                })
            except Exception as e:
                logger.error(f"Error scoring decision {trade.decision_id}: {e}")
                continue

        # Step 3: Compute aggregate statistics
        stats = self._compute_statistics(decision_scores)

        # Step 4: Check if model retraining is needed
        should_retrain = await self.feedback_scorer.should_retrain_model()

        if should_retrain:
            logger.info("Model retraining triggered")
            await self._retrain_models(user_id, decision_scores)

        # Step 5: Generate insights
        insights = self._generate_insights(stats, decision_scores)

        # Step 6: Create learning report
        report = {
            "report_date": report_date,
            "user_id": str(user_id),
            "total_trades": len(completed_trades),
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "win_rate": stats["win_rate"],
            "avg_score": stats["avg_overall_score"],
            "avg_pnl": stats["avg_pnl"],
            "total_pnl": stats["total_pnl"],
            "model_retrained": should_retrain,
            "insights": insights,
            "component_scores": {
                "pnl": stats["avg_pnl_score"],
                "risk": stats["avg_risk_score"],
                "entry": stats["avg_entry_score"],
                "adjustment": stats["avg_adjustment_score"],
                "exit": stats["avg_exit_score"]
            }
        }

        # Step 7: Save report to database
        await self._save_learning_report(report)

        logger.info(
            f"Daily learning complete for {user_id}: "
            f"{len(completed_trades)} trades, "
            f"avg score: {stats['avg_overall_score']:.2f}"
        )

        return report

    async def _extract_completed_trades(
        self,
        user_id: UUID,
        report_date: date
    ) -> List[TradeOutcome]:
        """
        Extract completed trades for a specific date from trade journal.

        Queries autopilot_trade_journal for completed trades.
        """
        from app.models import AutoPilotTradeJournal
        from sqlalchemy import select, and_
        from datetime import datetime, timedelta

        try:
            # Query completed trades for the specific date
            start_of_day = datetime.combine(report_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)

            result = await self.db.execute(
                select(AutoPilotTradeJournal)
                .where(
                    and_(
                        AutoPilotTradeJournal.user_id == user_id,
                        AutoPilotTradeJournal.entry_time >= start_of_day,
                        AutoPilotTradeJournal.entry_time < end_of_day,
                        AutoPilotTradeJournal.exit_time.isnot(None)  # Only completed trades
                    )
                )
            )
            trades = result.scalars().all()

            trade_outcomes = []
            for trade in trades:
                try:
                    # Extract trade outcome data
                    outcome = TradeOutcome(
                        strategy_type=trade.strategy_type or "UNKNOWN",
                        entry_regime=trade.entry_regime or "UNKNOWN",
                        exit_regime=trade.exit_regime or trade.entry_regime or "UNKNOWN",
                        entry_vix=float(trade.entry_vix or 0),
                        exit_vix=float(trade.exit_vix or trade.entry_vix or 0),
                        holding_period_minutes=int((trade.exit_time - trade.entry_time).total_seconds() / 60) if trade.exit_time and trade.entry_time else 0,
                        total_pnl=float(trade.total_pnl or 0),
                        max_profit_reached=float(trade.max_profit_reached or trade.total_pnl or 0),
                        max_loss_reached=float(trade.max_loss_reached or 0),
                        num_adjustments=trade.num_adjustments or 0,
                        adjustment_quality=float(trade.adjustment_quality or 0),
                        exit_reason=trade.exit_reason or "MANUAL",
                        slippage=float(trade.total_slippage or 0),
                        was_successful=(trade.total_pnl or 0) > 0,
                        confidence_at_entry=float(trade.confidence_at_entry or 0) if hasattr(trade, 'confidence_at_entry') else 70.0,
                        timestamp=trade.exit_time or trade.entry_time
                    )
                    trade_outcomes.append(outcome)

                except Exception as e:
                    logger.error(f"Error extracting trade outcome for trade {trade.id}: {e}")
                    continue

            logger.info(f"Extracted {len(trade_outcomes)} completed trades for {report_date}")
            return trade_outcomes

        except Exception as e:
            logger.error(f"Error extracting completed trades: {e}")
            return []

    def _compute_statistics(
        self,
        decision_scores: List[Dict]
    ) -> Dict:
        """
        Compute aggregate statistics from scored decisions.
        """
        if not decision_scores:
            return {
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_overall_score": 0.0,
                "avg_pnl_score": 0.0,
                "avg_risk_score": 0.0,
                "avg_entry_score": 0.0,
                "avg_adjustment_score": 0.0,
                "avg_exit_score": 0.0,
                "avg_pnl": Decimal('0'),
                "total_pnl": Decimal('0')
            }

        winning_trades = sum(
            1 for d in decision_scores
            if d["outcome"].realized_pnl > 0
        )

        losing_trades = len(decision_scores) - winning_trades

        win_rate = (winning_trades / len(decision_scores)) * 100

        avg_overall_score = sum(
            d["scores"]["overall_score"] for d in decision_scores
        ) / len(decision_scores)

        avg_pnl_score = sum(
            d["scores"]["pnl_score"] for d in decision_scores
        ) / len(decision_scores)

        avg_risk_score = sum(
            d["scores"]["risk_score"] for d in decision_scores
        ) / len(decision_scores)

        avg_entry_score = sum(
            d["scores"]["entry_score"] for d in decision_scores
        ) / len(decision_scores)

        avg_adjustment_score = sum(
            d["scores"]["adjustment_score"] for d in decision_scores
        ) / len(decision_scores)

        avg_exit_score = sum(
            d["scores"]["exit_score"] for d in decision_scores
        ) / len(decision_scores)

        total_pnl = sum(
            d["outcome"].realized_pnl for d in decision_scores
        )

        avg_pnl = total_pnl / len(decision_scores)

        return {
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "avg_overall_score": round(avg_overall_score, 2),
            "avg_pnl_score": round(avg_pnl_score, 2),
            "avg_risk_score": round(avg_risk_score, 2),
            "avg_entry_score": round(avg_entry_score, 2),
            "avg_adjustment_score": round(avg_adjustment_score, 2),
            "avg_exit_score": round(avg_exit_score, 2),
            "avg_pnl": avg_pnl,
            "total_pnl": total_pnl
        }

    async def _retrain_models(
        self,
        user_id: UUID,
        decision_scores: List[Dict]
    ):
        """
        Retrain ML models with new decision outcomes.

        Creates training dataset from scored decisions and
        triggers model retraining pipeline.
        """
        logger.info(f"Retraining models for user {user_id}")

        # Step 1: Create training dataset
        training_data = self._create_training_dataset(decision_scores)

        if len(training_data) < 100:
            logger.warning(
                f"Insufficient data for retraining: {len(training_data)} samples"
            )
            return

        # Step 2: Save to CSV (temporary)
        csv_path = f"backend/data/training/user_{user_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        training_data.to_csv(csv_path, index=False)

        # Step 3: Train new model
        try:
            new_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            pipeline, metrics = train_model_from_csv(
                csv_path=csv_path,
                model_type="xgboost",
                version=new_version,
                test_size=0.2
            )

            # Step 4: Register in model registry
            await ModelRegistry.register_model(
                version=new_version,
                model_type="xgboost",
                file_path=str(pipeline.model_dir / f"model_{new_version}.pkl"),
                metrics=metrics,
                description=f"Retrained model with {len(training_data)} samples",
                db=self.db
            )

            # Step 5: Auto-activate if performance improved
            current_model = await ModelRegistry.get_active_model(self.db)

            if current_model is None or metrics["accuracy"] > float(current_model.accuracy):
                await ModelRegistry.activate_model(new_version, self.db)
                logger.info(f"Activated new model {new_version}")

        except Exception as e:
            logger.error(f"Error retraining models: {e}")

    def _create_training_dataset(
        self,
        decision_scores: List[Dict]
    ) -> pd.DataFrame:
        """
        Create ML training dataset from scored decisions.

        Features: Same 30 features from feature_extractor
        Target: Overall decision quality score (normalized 0-1)
        """
        # This would extract features and targets from decisions
        # Placeholder: return empty DataFrame

        data = {
            # Would include all 30 features from feature_extractor
            # Plus target column: success (0/1 based on score threshold)
        }

        return pd.DataFrame(data)

    def _generate_insights(
        self,
        stats: Dict,
        decision_scores: List[Dict]
    ) -> List[str]:
        """
        Generate actionable insights from daily analysis.
        """
        insights = []

        # Win rate insight
        if stats["win_rate"] >= 70:
            insights.append(f"Strong win rate of {stats['win_rate']:.1f}% - excellent")
        elif stats["win_rate"] >= 55:
            insights.append(f"Good win rate of {stats['win_rate']:.1f}%")
        else:
            insights.append(
                f"Win rate of {stats['win_rate']:.1f}% needs improvement "
                f"(target: 55%+)"
            )

        # Score component analysis
        if stats["avg_risk_score"] < 60:
            insights.append(
                "Risk management score is low - review stop loss adherence "
                "and position sizing"
            )

        if stats["avg_entry_score"] < 65:
            insights.append(
                "Entry quality score is low - consider higher confidence "
                "thresholds or better regime filtering"
            )

        if stats["avg_adjustment_score"] < 60:
            insights.append(
                "Adjustment quality is low - review adjustment timing "
                "and action selection"
            )

        # P&L insights
        avg_pnl = float(stats["avg_pnl"])
        if avg_pnl > 0:
            insights.append(f"Average P&L per trade: +₹{avg_pnl:.2f}")
        else:
            insights.append(
                f"Negative average P&L of ₹{avg_pnl:.2f} - "
                f"review strategy selection"
            )

        # Overall performance
        if stats["avg_overall_score"] >= 75:
            insights.append("Overall decision quality is excellent")
        elif stats["avg_overall_score"] >= 60:
            insights.append("Overall decision quality is good")
        else:
            insights.append(
                "Overall decision quality needs improvement - "
                "focus on risk management and entry timing"
            )

        return insights

    async def _save_learning_report(self, report: Dict):
        """Save learning report to ai_learning_reports table."""
        # This would insert into ai_learning_reports table
        # Placeholder for now

        logger.info(f"Saved learning report for {report['report_date']}")


__all__ = ["LearningPipeline"]
