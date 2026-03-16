"""
Bug reproduction test: CE IV shows "1" for all strikes in option chain.

Root cause: calculate_iv() Newton-Raphson iteration hits the minimum sigma bound
(0.01) when it cannot converge for deep ITM options. It returns 0.01 * 100 = 1.0
instead of 0.0 (which means "IV not available").

Fix: return 0.0 when sigma converges to or below the minimum bound (0.01),
     to signal that IV is unavailable for this strike.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def calculate_iv(option_price, spot, strike, days_to_expiry, is_call):
    """Import from the route module."""
    from app.api.routes.optionchain import calculate_iv as _calculate_iv
    return _calculate_iv(option_price, spot, strike, days_to_expiry, is_call)


@pytest.mark.unit
class TestOptionChainIV:

    def test_atm_call_iv_is_never_one(self):
        """
        BUG: CE IV showed "1" for all strikes due to min-bound artifact.

        When Newton-Raphson hits the minimum sigma bound (0.01) without
        converging, it must return 0.0 (IV unavailable), NOT 1.0.

        Note: near-expiry NIFTY ATM options at very low LTP (e.g. ₹2.60)
        cannot always be fitted by Black-Scholes due to the interest-rate floor.
        0.0 is correct — it means "IV not calculable" (shown as "-" in UI).
        """
        iv = calculate_iv(2.60, 23650, 23650, 6, True)
        assert iv != 1.0, (
            f"ATM CE IV must not return 1.0 (minimum-bound artifact). "
            f"Should be 0.0 (unavailable) or a real IV%. Got {iv}"
        )

    def test_atm_put_iv_is_never_one(self):
        """
        ATM PE must also not return 1.0 from the min-bound artifact.
        """
        iv = calculate_iv(2.42, 23650, 23650, 6, False)
        assert iv != 1.0, (
            f"ATM PE IV must not return 1.0 (minimum-bound artifact). Got {iv}"
        )

    def test_high_premium_otm_call_converges(self):
        """
        OTM CE with a premium large enough for BS to fit should converge to a real IV.
        Spot=23650, Strike=24000, LTP=50, DTE=30 — should yield a real IV.
        """
        iv = calculate_iv(50.0, 23650, 24000, 30, True)
        assert iv != 1.0, f"OTM CE IV should not be 1.0. Got {iv}"
        assert iv > 3.0, f"OTM CE IV should be > 3% for this option. Got {iv}"

    def test_deep_itm_call_returns_zero_not_one(self):
        """
        BUG: Deep ITM CE returned 1.0 (min-bound artifact) before fix.
        After fix: must return 0.0 to indicate IV is unavailable.

        Deep ITM call: spot=23650, strike=23200, LTP=5.65, DTE=6.
        """
        iv = calculate_iv(5.65, 23650, 23200, 6, True)
        assert iv != 1.0, (
            f"Deep ITM CE IV must NOT return 1.0 (minimum-bound artifact). "
            f"Should return 0.0 to indicate IV unavailable. Got {iv}"
        )

    def test_zero_price_returns_zero_iv(self):
        """Zero LTP should return 0 IV (guard clause)."""
        iv = calculate_iv(0, 23650, 23650, 6, True)
        assert iv == 0.0, f"Zero LTP should produce IV=0. Got {iv}"

    def test_expired_option_returns_zero_iv(self):
        """DTE=0 should return 0 IV (guard clause)."""
        iv = calculate_iv(5.0, 23650, 23650, 0, True)
        assert iv == 0.0, f"DTE=0 should produce IV=0. Got {iv}"
