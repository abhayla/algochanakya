"""Auth-aware adapter call wrapper — broker-agnostic.

Routes wrap adapter coroutines with ``call_adapter_with_auth_tracking`` so
that broker auth failures (expired tokens, invalid API keys) are recorded on
the shared ``HealthMonitor``. This lets ``FailoverController`` react to
adapter failures that originate from HTTP routes (not just the ticker pool).

Used by ``optionchain.py`` (Path 1/2/3 quote fetches) and, in follow-up
phases, by ``orders.py`` and ``positions.py`` on the same HTTP boundary.
"""

from __future__ import annotations

import re
from typing import Any, Awaitable, Optional, TYPE_CHECKING

from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    BrokerAPIError,
)
from app.services.brokers.market_data.ticker.token_policy import (
    _BROKER_ERROR_TABLES,
)

if TYPE_CHECKING:
    from app.services.brokers.market_data.ticker.health import HealthMonitor


# Broker auth error codes use varied prefixes; extract the first token-like
# identifier from the message. Ordered most-specific → least so the first
# successful match wins.
_ERROR_CODE_PATTERNS = [
    re.compile(r"\b(UDAPI\d{6,})\b"),                # Upstox e.g. UDAPI100050
    re.compile(r"\b(AG\d{4,})\b"),                   # SmartAPI production e.g. AG8001
    re.compile(r"\b(AB\d{4,})\b"),                   # SmartAPI SDK e.g. AB1010
    re.compile(r"\b(DH-\d{3,})\b"),                  # Dhan e.g. DH-901
    re.compile(r"\b(TokenException|NetworkException|GeneralException)\b"),  # Kite
    re.compile(r"\b(ACCESS_TOKEN_EXPIRED|SESSION_EXPIRED)\b"),               # Paytm
    re.compile(r"\b(invalid_token)\b", re.IGNORECASE),                        # Fyers
]


def _extract_error_code(message: str) -> Optional[str]:
    """Extract a broker error code from a free-text error message.

    Returns ``None`` if no recognised pattern is present.
    """
    if not message:
        return None
    for pattern in _ERROR_CODE_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1)
    return None


def _is_known_auth_error_code(broker: str, error_code: str) -> bool:
    """Check if a code is listed in ``token_policy`` for this broker.

    Any code we've classified (retryable, not-retryable, not-refreshable) is
    considered an auth error — we want HealthMonitor to see it.
    """
    if not error_code:
        return False
    table = _BROKER_ERROR_TABLES.get(broker, {})
    return error_code in table


async def call_adapter_with_auth_tracking(
    broker_name: str,
    coro: Awaitable[Any],
    health_monitor: Optional["HealthMonitor"],
) -> Any:
    """Execute an adapter coroutine with auth-failure escalation.

    - ``AuthenticationError``: always escalate (already classified as auth by
      the adapter layer).
    - ``BrokerAPIError`` carrying a known broker-specific auth code in its
      message: escalate.
    - Any other exception (generic ``BrokerAPIError``, ``ValueError`` …):
      pass through without recording.

    The original exception is always re-raised. ``health_monitor=None`` is
    tolerated (e.g. during app startup races) — the coroutine is still
    awaited and its exception propagates.
    """
    try:
        return await coro
    except AuthenticationError as exc:
        if health_monitor is not None:
            code = _extract_error_code(str(exc)) or "UNKNOWN"
            await health_monitor.record_auth_failure(broker_name, code, str(exc))
        raise
    except BrokerAPIError as exc:
        code = _extract_error_code(str(exc))
        if (
            code is not None
            and health_monitor is not None
            and _is_known_auth_error_code(broker_name, code)
        ):
            await health_monitor.record_auth_failure(broker_name, code, str(exc))
        raise
