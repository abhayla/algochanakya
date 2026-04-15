"""
Wire #4: LearningPipeline → DailyScheduler Postmarket Integration Tests

Tests that _postmarket_review calls LearningPipeline.run_daily_learning
for each AI-enabled user after generating the Claude review.
TDD RED phase — these tests should FAIL until daily_scheduler.py is wired.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime


class TestPostmarketLearningPipelineIntegration:
    """Verify _postmarket_review calls LearningPipeline."""

    @pytest.mark.asyncio
    async def test_postmarket_calls_learning_pipeline(self):
        """Learning pipeline must be called for each user with trades."""
        user_id = uuid4()

        # Mock AI config
        mock_config = MagicMock()
        mock_config.user_id = user_id
        mock_config.ai_enabled = True
        mock_config.claude_api_key_encrypted = "encrypted_key"

        # Mock trade
        mock_trade = MagicMock()
        mock_trade.total_pnl = 500
        mock_trade.strategy_type = "iron_condor"
        mock_trade.entry_time = datetime.now()
        mock_trade.exit_time = datetime.now()

        # Mock DB query results
        mock_db = AsyncMock()
        mock_configs_result = MagicMock()
        mock_configs_result.scalars.return_value.all.return_value = [mock_config]
        mock_trades_result = MagicMock()
        mock_trades_result.scalars.return_value.all.return_value = [mock_trade]
        mock_db.execute = AsyncMock(side_effect=[mock_configs_result, mock_trades_result])

        async def mock_get_db():
            yield mock_db

        with patch("app.services.ai.daily_scheduler.get_db", mock_get_db), \
             patch("app.services.ai.daily_scheduler.ClaudeAdvisor") as MockClaudeAdvisor, \
             patch("app.services.ai.daily_scheduler.LearningPipeline") as MockLearningPipeline:

            mock_claude = MockClaudeAdvisor.return_value
            mock_claude.get_postmarket_review = AsyncMock(return_value={"review": "good"})

            mock_learning = MockLearningPipeline.return_value
            mock_learning.run_daily_learning = AsyncMock(return_value={
                "total_trades": 1,
                "win_rate": 100.0
            })

            from app.services.ai.daily_scheduler import DailyScheduler
            scheduler = DailyScheduler()
            await scheduler._postmarket_review()

            # LearningPipeline must be instantiated with db
            MockLearningPipeline.assert_called_once_with(mock_db)

            # run_daily_learning must be called with the user_id
            mock_learning.run_daily_learning.assert_called_once()
            call_args = mock_learning.run_daily_learning.call_args
            assert call_args.kwargs.get("user_id") == user_id or call_args[0][0] == user_id

    @pytest.mark.asyncio
    async def test_postmarket_learning_error_does_not_crash_review(self):
        """If learning pipeline fails, postmarket review must continue for other users."""
        user_id_1 = uuid4()
        user_id_2 = uuid4()

        configs = []
        for uid in [user_id_1, user_id_2]:
            c = MagicMock()
            c.user_id = uid
            c.ai_enabled = True
            c.claude_api_key_encrypted = "key"
            configs.append(c)

        mock_trade = MagicMock()
        mock_trade.total_pnl = 200
        mock_trade.strategy_type = "straddle"
        mock_trade.entry_time = datetime.now()
        mock_trade.exit_time = datetime.now()

        mock_db = AsyncMock()
        # First call returns configs, subsequent calls return trades
        mock_configs_result = MagicMock()
        mock_configs_result.scalars.return_value.all.return_value = configs
        mock_trades_result = MagicMock()
        mock_trades_result.scalars.return_value.all.return_value = [mock_trade]
        mock_db.execute = AsyncMock(side_effect=[
            mock_configs_result,
            mock_trades_result,  # user 1 trades
            mock_trades_result,  # user 2 trades
        ])

        async def mock_get_db():
            yield mock_db

        with patch("app.services.ai.daily_scheduler.get_db", mock_get_db), \
             patch("app.services.ai.daily_scheduler.ClaudeAdvisor") as MockClaudeAdvisor, \
             patch("app.services.ai.daily_scheduler.LearningPipeline") as MockLearningPipeline:

            mock_claude = MockClaudeAdvisor.return_value
            mock_claude.get_postmarket_review = AsyncMock(return_value={})

            mock_learning = MockLearningPipeline.return_value
            # First call raises, second should still proceed
            mock_learning.run_daily_learning = AsyncMock(
                side_effect=[Exception("ML training failed"), {"total_trades": 1}]
            )

            from app.services.ai.daily_scheduler import DailyScheduler
            scheduler = DailyScheduler()

            # Should not raise despite first user's learning failure
            await scheduler._postmarket_review()

            # Learning pipeline should have been called for both users
            assert mock_learning.run_daily_learning.call_count == 2

    @pytest.mark.asyncio
    async def test_postmarket_skips_learning_when_no_trades(self):
        """Learning pipeline must NOT be called if user has no trades today."""
        user_id = uuid4()

        mock_config = MagicMock()
        mock_config.user_id = user_id
        mock_config.ai_enabled = True
        mock_config.claude_api_key_encrypted = "key"

        mock_db = AsyncMock()
        mock_configs_result = MagicMock()
        mock_configs_result.scalars.return_value.all.return_value = [mock_config]
        mock_trades_result = MagicMock()
        mock_trades_result.scalars.return_value.all.return_value = []  # No trades
        mock_db.execute = AsyncMock(side_effect=[mock_configs_result, mock_trades_result])

        async def mock_get_db():
            yield mock_db

        with patch("app.services.ai.daily_scheduler.get_db", mock_get_db), \
             patch("app.services.ai.daily_scheduler.LearningPipeline") as MockLearningPipeline:

            from app.services.ai.daily_scheduler import DailyScheduler
            scheduler = DailyScheduler()
            await scheduler._postmarket_review()

            # No trades = no learning pipeline call
            MockLearningPipeline.assert_not_called()
