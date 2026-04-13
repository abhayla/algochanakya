"""
NSE Market Hours Utility

Determines whether the NSE market is currently open.
Mirrors the logic in tests/e2e/helpers/market-status.helper.js.
"""
from datetime import datetime, date, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# NSE regular session: Mon–Fri, 9:15–15:30 IST (excluding holidays)
_MARKET_OPEN = (9, 15)
_MARKET_CLOSE = (15, 30)

# NSE 2026 trading holidays
_NSE_HOLIDAYS_2026 = {
    "2026-01-26", "2026-02-18", "2026-03-02", "2026-03-31",
    "2026-04-02", "2026-04-03", "2026-04-14", "2026-04-21",
    "2026-05-01", "2026-07-16", "2026-08-15", "2026-09-07",
    "2026-10-02", "2026-10-21", "2026-10-28", "2026-11-04",
    "2026-11-05", "2026-11-19", "2026-12-25",
}


def _ist_now() -> datetime:
    return datetime.now(tz=IST)


def is_market_open() -> bool:
    """Returns True if NSE regular session is currently active."""
    now = _ist_now()
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if now.strftime("%Y-%m-%d") in _NSE_HOLIDAYS_2026:
        return False
    minutes = now.hour * 60 + now.minute
    open_minutes = _MARKET_OPEN[0] * 60 + _MARKET_OPEN[1]   # 555
    close_minutes = _MARKET_CLOSE[0] * 60 + _MARKET_CLOSE[1]  # 930
    return open_minutes <= minutes < close_minutes


def _is_trading_day(d: date) -> bool:
    """Check if a given date is a trading day (weekday, not an NSE holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if d.strftime("%Y-%m-%d") in _NSE_HOLIDAYS_2026:
        return False
    return True


# 15:35 IST — 5 minutes after market close for OI settlement buffer
_SNAPSHOT_CLOSE = (15, 35)


def get_last_trading_close(now: datetime = None) -> datetime:
    """
    Returns datetime of the most recent 15:35 IST on a trading day.

    Used to determine if an EOD snapshot is fresh. A snapshot captured
    after this time is from the latest trading session.

    Examples:
        - Friday 20:00 → Friday 15:35
        - Saturday 10:00 → Friday 15:35
        - Monday 08:00 → Friday 15:35
        - Holiday → previous trading day 15:35
        - Wednesday 11:00 (market open) → Tuesday 15:35
    """
    if now is None:
        now = _ist_now()

    candidate = now.date()

    # If today is a trading day and we're past the snapshot time, today qualifies
    snapshot_minutes = _SNAPSHOT_CLOSE[0] * 60 + _SNAPSHOT_CLOSE[1]
    now_minutes = now.hour * 60 + now.minute
    if _is_trading_day(candidate) and now_minutes >= snapshot_minutes:
        return datetime(
            candidate.year, candidate.month, candidate.day,
            _SNAPSHOT_CLOSE[0], _SNAPSHOT_CLOSE[1], tzinfo=IST,
        )

    # Walk backward to find the previous trading day
    candidate -= timedelta(days=1)
    while not _is_trading_day(candidate):
        candidate -= timedelta(days=1)

    return datetime(
        candidate.year, candidate.month, candidate.day,
        _SNAPSHOT_CLOSE[0], _SNAPSHOT_CLOSE[1], tzinfo=IST,
    )


def get_data_freshness() -> str:
    """
    Returns 'LIVE' when market is open, 'LAST_KNOWN' otherwise.

    Use this in API responses so the frontend can show a market-closed banner.
    'LAST_KNOWN' means prices reflect the previous session's close.
    """
    return "LIVE" if is_market_open() else "LAST_KNOWN"
