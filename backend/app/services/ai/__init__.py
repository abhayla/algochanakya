"""
AI Services Module

Autonomous AI trading system services including:
- Historical data fetching with caching
- Technical indicators calculation (RSI, ADX, EMA, ATR, Bollinger Bands)
- Market regime classification
- Strategy recommendation engine
- Dynamic strike selection
- Claude AI advisor for explanations
- Daily task scheduling
- Auto-deployment execution
- Real-time position synchronization
- AI-powered adjustment advisor with what-if analysis
- Kelly Criterion position sizing
- Historical strategy backtesting
- Multi-strategy portfolio management
"""

from app.services.ai.indicators import TechnicalIndicators
from app.services.ai.historical_data import HistoricalDataService
from app.services.ai.market_regime import MarketRegimeClassifier, RegimeType, RegimeResult
from app.services.ai.strategy_recommender import StrategyRecommender, StrategyRecommendation
from app.services.ai.strike_selector import StrikeSelector, StrikeSelection, StrategyStrikes
from app.services.ai.claude_advisor import ClaudeAdvisor
from app.services.ai.daily_scheduler import DailyScheduler, get_scheduler, start_scheduler, stop_scheduler
from app.services.ai.deployment_executor import DeploymentExecutor, DeploymentStatus
from app.services.ai.position_sync import PositionSyncService, PositionAnalysis, PositionChange
from app.services.ai.ai_monitor import AIMonitor, AIDecision
from app.services.ai.ai_adjustment_advisor import AIAdjustmentAdvisor, AdjustmentRecommendation, AdjustmentSimulation
from app.services.ai.feedback_scorer import FeedbackScorer, TradeOutcome
from app.services.ai.learning_pipeline import LearningPipeline
from app.services.ai.kelly_calculator import KellyCalculator
from app.services.ai.backtester import Backtester, BacktestResult, BacktestTrade, BacktestStatus
from app.services.ai.portfolio_manager import (
    PortfolioManager,
    PortfolioSummary,
    PortfolioGreeks,
    StrategyCorrelation,
    PortfolioRebalance
)

__all__ = [
    "TechnicalIndicators",
    "HistoricalDataService",
    "MarketRegimeClassifier",
    "RegimeType",
    "RegimeResult",
    "StrategyRecommender",
    "StrategyRecommendation",
    "StrikeSelector",
    "StrikeSelection",
    "StrategyStrikes",
    "ClaudeAdvisor",
    "DailyScheduler",
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler",
    "DeploymentExecutor",
    "DeploymentStatus",
    "PositionSyncService",
    "PositionAnalysis",
    "PositionChange",
    "AIMonitor",
    "AIDecision",
    "AIAdjustmentAdvisor",
    "AdjustmentRecommendation",
    "AdjustmentSimulation",
    "FeedbackScorer",
    "TradeOutcome",
    "LearningPipeline",
    "KellyCalculator",
    "Backtester",
    "BacktestResult",
    "BacktestTrade",
    "BacktestStatus",
    "PortfolioManager",
    "PortfolioSummary",
    "PortfolioGreeks",
    "StrategyCorrelation",
    "PortfolioRebalance",
]
