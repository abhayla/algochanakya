"""
Tests for get_last_trading_close() and _is_trading_day() in market_hours.py.

TDD: These tests are written FIRST, before the implementation.
"""
import pytest
from datetime import datetime, date, timezone, timedelta
from unittest.mock import patch

from app.utils.market_hours import IST

# Patch target for controlling time in tests
PATCH_TARGET = "app.utils.market_hours._ist_now"


def _ist(year, month, day, hour=0, minute=0):
    """Helper to create IST-aware datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=IST)


class TestIsTradingDay:
    """Tests for _is_trading_day()."""

    def test_regular_weekday_is_trading_day(self):
        from app.utils.market_hours import _is_trading_day
        # Wednesday April 8, 2026
        assert _is_trading_day(date(2026, 4, 8)) is True

    def test_saturday_is_not_trading_day(self):
        from app.utils.market_hours import _is_trading_day
        # Saturday April 11, 2026
        assert _is_trading_day(date(2026, 4, 11)) is False

    def test_sunday_is_not_trading_day(self):
        from app.utils.market_hours import _is_trading_day
        # Sunday April 12, 2026
        assert _is_trading_day(date(2026, 4, 12)) is False

    def test_holiday_is_not_trading_day(self):
        from app.utils.market_hours import _is_trading_day
        # April 14, 2026 — Dr. Ambedkar Jayanti (NSE holiday)
        assert _is_trading_day(date(2026, 4, 14)) is False

    def test_day_before_holiday_is_trading_day(self):
        from app.utils.market_hours import _is_trading_day
        # April 13, 2026 — Monday, not a holiday
        assert _is_trading_day(date(2026, 4, 13)) is True

    def test_republic_day_is_not_trading_day(self):
        from app.utils.market_hours import _is_trading_day
        # January 26, 2026 — Republic Day
        assert _is_trading_day(date(2026, 1, 26)) is False


class TestGetLastTradingClose:
    """Tests for get_last_trading_close()."""

    def test_weekday_after_close_returns_same_day(self):
        """Wednesday 20:00 IST → Wednesday 15:35 IST."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 8, 20, 0)  # Wed 20:00
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 8, 15, 35)

    def test_weekday_during_market_returns_previous_day(self):
        """Wednesday 11:00 IST (market open) → Tuesday 15:35 IST."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 8, 11, 0)  # Wed 11:00
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 7, 15, 35)

    def test_weekday_before_market_returns_previous_day(self):
        """Wednesday 08:00 IST (pre-market) → Tuesday 15:35 IST."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 8, 8, 0)  # Wed 08:00
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 7, 15, 35)

    def test_saturday_returns_friday(self):
        """Saturday 10:00 IST → Friday 15:35 IST."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 11, 10, 0)  # Sat
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 10, 15, 35)  # Fri

    def test_sunday_returns_friday(self):
        """Sunday 14:00 IST → Friday 15:35 IST."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 12, 14, 0)  # Sun
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 10, 15, 35)  # Fri

    def test_monday_premarket_returns_friday(self):
        """Monday 08:00 IST → Friday 15:35 IST."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 13, 8, 0)  # Mon 08:00
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 10, 15, 35)  # Fri

    def test_holiday_returns_previous_trading_day(self):
        """April 14 (holiday, Tuesday) evening → April 13 (Monday) 15:35."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 14, 18, 0)  # Tue holiday, 18:00
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 13, 15, 35)  # Mon

    def test_consecutive_holidays_skip_all(self):
        """April 3 (holiday, Friday) → April 1 (Wednesday) 15:35.
        April 2 (Thu) and April 3 (Fri) are both holidays."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 3, 18, 0)  # Fri holiday, 18:00
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 1, 15, 35)  # Wed

    def test_returns_tz_aware_datetime(self):
        """Result must have IST tzinfo."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 8, 20, 0)
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result.tzinfo is not None
        assert result.tzinfo == IST

    def test_accepts_now_parameter(self):
        """Can pass explicit `now` for testability without mocking."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 11, 10, 0)  # Saturday
        result = get_last_trading_close(now=now)
        assert result == _ist(2026, 4, 10, 15, 35)  # Friday

    def test_exactly_at_close_time_returns_previous_day(self):
        """Wednesday 15:30 IST (market still open) → Tuesday 15:35."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 8, 15, 30)  # Wed at market close
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 7, 15, 35)

    def test_just_after_close_returns_same_day(self):
        """Wednesday 15:35 IST (just after close buffer) → Wednesday 15:35."""
        from app.utils.market_hours import get_last_trading_close
        now = _ist(2026, 4, 8, 15, 35)  # Wed 15:35
        with patch(PATCH_TARGET, return_value=now):
            result = get_last_trading_close()
        assert result == _ist(2026, 4, 8, 15, 35)
