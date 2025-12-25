"""
Daily Scheduler Service

Manages scheduled AI tasks including:
- Market data prefetching at market open
- Daily regime classification caching
- End-of-day summaries and cleanup
- Scheduled AutoPilot strategy checks
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.ai.market_regime import MarketRegimeClassifier
from app.services.ai.claude_advisor import ClaudeAdvisor
from app.services.ai.deployment_executor import DeploymentExecutor
from app.constants.trading import UNDERLYINGS
from app.models.ai import AIUserConfig
from sqlalchemy import select

logger = logging.getLogger(__name__)


class DailyScheduler:
    """
    Scheduler for AI-related daily tasks.

    Runs tasks at specific times:
    - 9:00 AM: Market open tasks (prefetch data, classify regimes)
    - 3:30 PM: Market close tasks (EOD summaries, cleanup)
    - Every hour: Regime reclassification during market hours
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting AI Daily Scheduler")

        # Pre-market analysis (8:45 AM IST) - Claude API market analysis
        self.scheduler.add_job(
            self._premarket_analysis,
            CronTrigger(hour=8, minute=45, timezone="Asia/Kolkata"),
            id="premarket_analysis",
            name="Pre-Market Analysis",
            replace_existing=True
        )

        # Market open tasks (9:00 AM IST)
        self.scheduler.add_job(
            self._market_open_tasks,
            CronTrigger(hour=9, minute=0, timezone="Asia/Kolkata"),
            id="market_open",
            name="Market Open Tasks",
            replace_existing=True
        )

        # Auto-deployment check (9:20 AM IST) - Deploy AI strategies
        self.scheduler.add_job(
            self._check_and_deploy,
            CronTrigger(hour=9, minute=20, timezone="Asia/Kolkata"),
            id="auto_deploy",
            name="Auto-Deploy AI Strategies",
            replace_existing=True
        )

        # Market close tasks (3:30 PM IST)
        self.scheduler.add_job(
            self._market_close_tasks,
            CronTrigger(hour=15, minute=30, timezone="Asia/Kolkata"),
            id="market_close",
            name="Market Close Tasks",
            replace_existing=True
        )

        # Post-market review (4:00 PM IST) - Claude API daily review
        self.scheduler.add_job(
            self._postmarket_review,
            CronTrigger(hour=16, minute=0, timezone="Asia/Kolkata"),
            id="postmarket_review",
            name="Post-Market Review",
            replace_existing=True
        )

        # Hourly regime refresh (during market hours: 9 AM - 3:30 PM)
        for hour in range(9, 16):  # 9 AM to 3 PM
            self.scheduler.add_job(
                self._refresh_regimes,
                CronTrigger(hour=hour, minute=0, timezone="Asia/Kolkata"),
                id=f"refresh_regimes_{hour}",
                name=f"Refresh Regimes {hour}:00",
                replace_existing=True
            )

        # Daily cleanup (11:00 PM IST)
        self.scheduler.add_job(
            self._daily_cleanup,
            CronTrigger(hour=23, minute=0, timezone="Asia/Kolkata"),
            id="daily_cleanup",
            name="Daily Cleanup",
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("AI Daily Scheduler started successfully")

    async def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping AI Daily Scheduler")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("AI Daily Scheduler stopped")

    # Scheduled Task Methods

    async def _premarket_analysis(self):
        """
        Pre-market analysis using Claude API (8:45 AM).

        - Analyze global cues, SGX Nifty, overnight news
        - Generate market outlook for the day
        - Store analysis for all enabled AI users
        """
        logger.info("Running pre-market analysis")

        try:
            async for db in get_db():
                # Get all users with AI enabled
                result = await db.execute(
                    select(AIUserConfig).where(AIUserConfig.ai_enabled == True)
                )
                ai_configs = result.scalars().all()

                if not ai_configs:
                    logger.info("No AI-enabled users found")
                    return

                # Get market data for analysis
                from app.services.ai.market_regime import MarketRegimeClassifier
                regime_classifier = MarketRegimeClassifier()

                market_data = {}
                for underlying in UNDERLYINGS:
                    try:
                        regime = await regime_classifier.classify(underlying)
                        indicators = await regime_classifier.get_indicators_snapshot(underlying)
                        market_data[underlying] = {
                            "regime": regime.dict(),
                            "indicators": indicators.dict()
                        }
                    except Exception as e:
                        logger.error(f"Error getting data for {underlying}: {e}")

                # Generate Claude analysis for each user with valid API key
                claude_advisor = ClaudeAdvisor()
                for config in ai_configs:
                    if not config.claude_api_key_encrypted:
                        logger.debug(f"Skipping user {config.user_id} - no Claude API key")
                        continue

                    try:
                        analysis = await claude_advisor.get_premarket_analysis(market_data)
                        logger.info(f"Pre-market analysis generated for user {config.user_id}")
                        # TODO: Store analysis in database or send notification
                    except Exception as e:
                        logger.error(f"Error generating analysis for user {config.user_id}: {e}")

                logger.info("Pre-market analysis completed")

        except Exception as e:
            logger.error(f"Error in pre-market analysis: {e}")

    async def _check_and_deploy(self):
        """
        Check deployment conditions and auto-deploy strategies (9:20 AM).

        - Check each AI-enabled user's configuration
        - Evaluate market conditions
        - Deploy strategies if conditions met
        """
        logger.info("Running auto-deployment check")

        try:
            async for db in get_db():
                # Get users with auto-deploy enabled
                result = await db.execute(
                    select(AIUserConfig).where(
                        AIUserConfig.ai_enabled == True,
                        AIUserConfig.auto_deploy_enabled == True
                    )
                )
                ai_configs = result.scalars().all()

                if not ai_configs:
                    logger.info("No users with auto-deploy enabled")
                    return

                deployment_executor = DeploymentExecutor()

                for config in ai_configs:
                    try:
                        # Check if today is a deploy day
                        from datetime import datetime
                        today = datetime.now()
                        day_name = today.strftime("%a").upper()[:3]  # MON, TUE, etc.

                        if day_name not in (config.deploy_days or []):
                            logger.debug(f"Skipping user {config.user_id} - not a deploy day")
                            continue

                        # Check if should skip event days
                        if config.skip_event_days:
                            from app.services.ai.market_regime import MarketRegimeClassifier
                            regime_classifier = MarketRegimeClassifier()
                            is_event, event_type = regime_classifier.is_event_day(today.date())
                            if is_event:
                                logger.info(f"Skipping user {config.user_id} - event day: {event_type}")
                                continue

                        # Execute deployment
                        result = await deployment_executor.execute_deployment(
                            user_id=config.user_id,
                            config=config,
                            db=db
                        )
                        logger.info(f"Deployment result for user {config.user_id}: {result}")

                    except Exception as e:
                        logger.error(f"Error deploying for user {config.user_id}: {e}")

                logger.info("Auto-deployment check completed")

        except Exception as e:
            logger.error(f"Error in auto-deployment check: {e}")

    async def _postmarket_review(self):
        """
        Post-market review using Claude API (4:00 PM).

        - Analyze day's trades for all AI users
        - Generate lessons learned
        - Identify what went right/wrong
        - Store review for user access
        """
        logger.info("Running post-market review")

        try:
            async for db in get_db():
                # Get all users with AI enabled
                result = await db.execute(
                    select(AIUserConfig).where(AIUserConfig.ai_enabled == True)
                )
                ai_configs = result.scalars().all()

                if not ai_configs:
                    logger.info("No AI-enabled users found")
                    return

                claude_advisor = ClaudeAdvisor()

                for config in ai_configs:
                    if not config.claude_api_key_encrypted:
                        logger.debug(f"Skipping user {config.user_id} - no Claude API key")
                        continue

                    try:
                        # Get today's trades from trade journal
                        from app.models import AutoPilotTradeJournal
                        from datetime import datetime, timedelta
                        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                        trades_result = await db.execute(
                            select(AutoPilotTradeJournal)
                            .where(
                                AutoPilotTradeJournal.user_id == config.user_id,
                                AutoPilotTradeJournal.entry_time >= today_start
                            )
                        )
                        trades = trades_result.scalars().all()

                        if not trades:
                            logger.debug(f"No trades today for user {config.user_id}")
                            continue

                        # Calculate performance metrics
                        total_pnl = sum(trade.total_pnl or 0 for trade in trades)
                        winning_trades = sum(1 for trade in trades if (trade.total_pnl or 0) > 0)
                        win_rate = (winning_trades / len(trades) * 100) if trades else 0

                        performance = {
                            "total_trades": len(trades),
                            "total_pnl": total_pnl,
                            "win_rate": win_rate,
                            "trades": [
                                {
                                    "strategy_type": trade.strategy_type,
                                    "entry_time": trade.entry_time.isoformat(),
                                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                                    "pnl": trade.total_pnl,
                                }
                                for trade in trades
                            ]
                        }

                        # Generate Claude review
                        review = await claude_advisor.get_postmarket_review(
                            trades=[t for t in trades],
                            performance=performance
                        )
                        logger.info(f"Post-market review generated for user {config.user_id}")
                        # TODO: Store review in ai_learning_reports table

                    except Exception as e:
                        logger.error(f"Error generating review for user {config.user_id}: {e}")

                logger.info("Post-market review completed")

        except Exception as e:
            logger.error(f"Error in post-market review: {e}")

    async def _market_open_tasks(self):
        """
        Tasks to run at market open (9:00 AM).

        - Classify market regimes for all indices
        - Cache initial market data
        - Log market open event
        """
        logger.info("Running market open tasks")

        try:
            async for db in get_db():
                # Classify regimes for all underlyings
                for underlying in UNDERLYINGS:
                    try:
                        # This will be implemented when we have the full classifier with caching
                        logger.info(f"Would classify regime for {underlying}")
                        # await self._classify_and_cache_regime(underlying, db)
                    except Exception as e:
                        logger.error(f"Error classifying {underlying}: {e}")

                logger.info("Market open tasks completed")

        except Exception as e:
            logger.error(f"Error in market open tasks: {e}")

    async def _market_close_tasks(self):
        """
        Tasks to run at market close (3:30 PM).

        - Generate end-of-day regime summary
        - Cache final market data
        - Prepare for next trading day
        """
        logger.info("Running market close tasks")

        try:
            async for db in get_db():
                # Generate EOD summaries
                logger.info("Generating end-of-day summaries")

                # Cache final regime classifications
                for underlying in UNDERLYINGS:
                    try:
                        logger.info(f"Caching EOD regime for {underlying}")
                        # await self._cache_eod_regime(underlying, db)
                    except Exception as e:
                        logger.error(f"Error caching EOD regime for {underlying}: {e}")

                logger.info("Market close tasks completed")

        except Exception as e:
            logger.error(f"Error in market close tasks: {e}")

    async def _refresh_regimes(self):
        """
        Refresh regime classifications during market hours.

        Runs every hour to keep regime data fresh.
        """
        logger.info("Refreshing market regimes")

        try:
            async for db in get_db():
                for underlying in UNDERLYINGS:
                    try:
                        logger.info(f"Refreshing regime for {underlying}")
                        # await self._classify_and_cache_regime(underlying, db)
                    except Exception as e:
                        logger.error(f"Error refreshing regime for {underlying}: {e}")

                logger.info("Regime refresh completed")

        except Exception as e:
            logger.error(f"Error in regime refresh: {e}")

    async def _daily_cleanup(self):
        """
        Daily cleanup tasks (11:00 PM).

        - Clear old cache entries
        - Archive old logs
        - Clean up expired sessions
        """
        logger.info("Running daily cleanup tasks")

        try:
            # Clean up old Redis cache entries (if needed)
            logger.info("Cleaning up old cache entries")

            # Archive old logs (placeholder)
            logger.info("Archiving old logs")

            # Any other cleanup tasks
            logger.info("Daily cleanup completed")

        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")

    # Helper Methods

    async def _classify_and_cache_regime(self, underlying: str, db: AsyncSession):
        """
        Classify market regime and cache the result.

        Args:
            underlying: Index name
            db: Database session
        """
        # This will be implemented when we integrate with regime classifier
        # For now, just a placeholder
        logger.debug(f"Classifying regime for {underlying}")

    async def _cache_eod_regime(self, underlying: str, db: AsyncSession):
        """
        Cache end-of-day regime classification.

        Args:
            underlying: Index name
            db: Database session
        """
        # Placeholder for EOD caching logic
        logger.debug(f"Caching EOD regime for {underlying}")

    def get_next_run_times(self) -> dict:
        """
        Get next run times for all scheduled jobs.

        Returns:
            Dictionary of job IDs to next run times
        """
        if not self.is_running:
            return {}

        jobs = self.scheduler.get_jobs()
        return {
            job.id: job.next_run_time
            for job in jobs
        }

    def get_job_status(self) -> dict:
        """
        Get status of all scheduled jobs.

        Returns:
            Dictionary with scheduler status and job details
        """
        if not self.is_running:
            return {"running": False, "jobs": []}

        jobs = self.scheduler.get_jobs()
        return {
            "running": True,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs
            ]
        }


# Global scheduler instance
_scheduler_instance: Optional[DailyScheduler] = None


def get_scheduler() -> DailyScheduler:
    """
    Get or create the global scheduler instance.

    Returns:
        Global DailyScheduler instance
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DailyScheduler()
    return _scheduler_instance


async def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


__all__ = [
    "DailyScheduler",
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler"
]
