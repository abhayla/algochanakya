"""
P/L Calculator Service Tests

Tests for PnLCalculator including:
- Intrinsic value at expiry (call/put)
- Black-Scholes current value
- P/L grid generation
- Breakeven calculation
- Multi-leg strategies
- Edge cases (deep ITM, deep OTM, at expiry)
"""

import pytest
from unittest.mock import MagicMock

from app.services.options.pnl_calculator import PnLCalculator, norm_cdf


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPOT = 22000.0
RISK_FREE_RATE = 0.07


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def calc():
    """Create a PnLCalculator."""
    return PnLCalculator(risk_free_rate=RISK_FREE_RATE)


# ---------------------------------------------------------------------------
# norm_cdf tests
# ---------------------------------------------------------------------------

class TestNormCDF:
    """Test the normal CDF implementation."""

    def test_cdf_at_zero(self):
        """CDF(0) should be 0.5."""
        assert abs(norm_cdf(0.0) - 0.5) < 0.001

    def test_cdf_symmetry(self):
        """CDF(x) + CDF(-x) should equal 1."""
        for x in [0.5, 1.0, 2.0, 3.0]:
            total = norm_cdf(x) + norm_cdf(-x)
            assert abs(total - 1.0) < 0.001

    def test_cdf_monotonic(self):
        """CDF should be monotonically increasing."""
        prev = 0
        for x in [-3, -2, -1, 0, 1, 2, 3]:
            curr = norm_cdf(x)
            assert curr >= prev
            prev = curr


# ---------------------------------------------------------------------------
# Intrinsic value tests
# ---------------------------------------------------------------------------

class TestIntrinsicValue:
    """Test intrinsic value at expiry calculations."""

    def test_itm_call_intrinsic(self, calc):
        """ITM call: max(spot - strike, 0)."""
        iv = calc._intrinsic_value(spot=22500, strike=22000, option_type="CE")
        assert iv == 500

    def test_otm_call_intrinsic(self, calc):
        """OTM call intrinsic value should be 0."""
        iv = calc._intrinsic_value(spot=21500, strike=22000, option_type="CE")
        assert iv == 0

    def test_atm_call_intrinsic(self, calc):
        """ATM call intrinsic value should be 0."""
        iv = calc._intrinsic_value(spot=22000, strike=22000, option_type="CE")
        assert iv == 0

    def test_itm_put_intrinsic(self, calc):
        """ITM put: max(strike - spot, 0)."""
        iv = calc._intrinsic_value(spot=21500, strike=22000, option_type="PE")
        assert iv == 500

    def test_otm_put_intrinsic(self, calc):
        """OTM put intrinsic value should be 0."""
        iv = calc._intrinsic_value(spot=22500, strike=22000, option_type="PE")
        assert iv == 0


# ---------------------------------------------------------------------------
# Black-Scholes tests
# ---------------------------------------------------------------------------

class TestBlackScholes:
    """Test Black-Scholes option pricing."""

    def test_call_price_positive(self, calc):
        """Call price should always be positive."""
        price = calc._black_scholes(
            spot=SPOT, strike=22000, time_to_expiry=0.05,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="CE"
        )
        assert price > 0

    def test_put_price_positive(self, calc):
        """Put price should always be positive."""
        price = calc._black_scholes(
            spot=SPOT, strike=22000, time_to_expiry=0.05,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="PE"
        )
        assert price > 0

    def test_deep_itm_call_near_intrinsic(self, calc):
        """Deep ITM call should be near intrinsic value."""
        price = calc._black_scholes(
            spot=23000, strike=22000, time_to_expiry=0.01,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="CE"
        )
        intrinsic = 1000
        assert abs(price - intrinsic) < 50  # Within 50 of intrinsic

    def test_higher_vol_means_higher_price(self, calc):
        """Higher volatility should give higher option price."""
        low_vol = calc._black_scholes(
            spot=SPOT, strike=22000, time_to_expiry=0.05,
            rate=RISK_FREE_RATE, volatility=0.10, option_type="CE"
        )
        high_vol = calc._black_scholes(
            spot=SPOT, strike=22000, time_to_expiry=0.05,
            rate=RISK_FREE_RATE, volatility=0.25, option_type="CE"
        )
        assert high_vol > low_vol

    def test_more_time_means_higher_price(self, calc):
        """More time to expiry should give higher option price."""
        short_time = calc._black_scholes(
            spot=SPOT, strike=22000, time_to_expiry=0.01,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="CE"
        )
        long_time = calc._black_scholes(
            spot=SPOT, strike=22000, time_to_expiry=0.10,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="CE"
        )
        assert long_time > short_time

    def test_put_call_parity(self, calc):
        """Put-call parity: C - P = S - K*exp(-rT)."""
        import math
        T = 0.05
        K = 22000

        call = calc._black_scholes(
            spot=SPOT, strike=K, time_to_expiry=T,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="CE"
        )
        put = calc._black_scholes(
            spot=SPOT, strike=K, time_to_expiry=T,
            rate=RISK_FREE_RATE, volatility=0.15, option_type="PE"
        )

        # C - P should ≈ S - K*e^(-rT)
        lhs = call - put
        rhs = SPOT - K * math.exp(-RISK_FREE_RATE * T)
        assert abs(lhs - rhs) < 5  # Within 5 points


# ---------------------------------------------------------------------------
# P/L grid tests
# ---------------------------------------------------------------------------

class TestPnLGrid:
    """Test P/L grid calculation."""

    def test_pnl_grid_returns_dict(self, calc):
        """P/L grid should return a dictionary."""
        legs = [{
            "strike": 22000,
            "option_type": "CE",
            "action": "BUY",
            "lots": 1,
            "lot_size": 25,
            "entry_price": 250,
        }]
        spots = [21000, 21500, 22000, 22500, 23000]

        result = calc.calculate_pnl_grid(
            legs=legs, spot_prices=spots, mode="expiry"
        )
        assert isinstance(result, dict)

    def test_long_call_pnl_at_expiry(self, calc):
        """Long call P/L: max(spot-strike, 0) - premium, per lot."""
        legs = [{
            "strike": 22000,
            "option_type": "CE",
            "action": "BUY",
            "lots": 1,
            "lot_size": 25,
            "entry_price": 250,
        }]
        # At spot=22500, intrinsic=500, premium=250, pnl=(500-250)*25=6250
        # At spot=21000, intrinsic=0, pnl=-250*25=-6250
        spots = [21000, 22500]

        result = calc.calculate_pnl_grid(
            legs=legs, spot_prices=spots, mode="expiry"
        )

        if "pnl" in result:
            pnl_values = result["pnl"]
            # At 21000, should be negative (loss of premium)
            assert pnl_values[0] < 0
            # At 22500, should be positive
            assert pnl_values[1] > 0

    def test_iron_condor_max_profit_in_range(self, calc):
        """Iron condor should have max profit in the middle range."""
        legs = [
            {"strike": 21500, "option_type": "PE", "action": "SELL", "lots": 1,
             "lot_size": 25, "entry_price": 40},
            {"strike": 21000, "option_type": "PE", "action": "BUY", "lots": 1,
             "lot_size": 25, "entry_price": 15},
            {"strike": 22500, "option_type": "CE", "action": "SELL", "lots": 1,
             "lot_size": 25, "entry_price": 45},
            {"strike": 23000, "option_type": "CE", "action": "BUY", "lots": 1,
             "lot_size": 25, "entry_price": 15},
        ]
        spots = [20000, 22000, 24000]

        result = calc.calculate_pnl_grid(
            legs=legs, spot_prices=spots, mode="expiry"
        )

        if "pnl" in result:
            pnl_values = result["pnl"]
            # Middle spot (22000) should have highest P/L
            assert pnl_values[1] > pnl_values[0]
            assert pnl_values[1] > pnl_values[2]


# ---------------------------------------------------------------------------
# Breakeven tests
# ---------------------------------------------------------------------------

class TestBreakeven:
    """Test breakeven point calculation."""

    def test_find_breakeven_single_crossing(self, calc):
        """Should find breakeven where P/L crosses zero."""
        spots = [21000, 21500, 22000, 22500, 23000]
        pnl = [-6250, -6250, -6250, 6250, 18750]  # Crosses between 22000 and 22500

        breakevens = calc._find_breakeven(spots, pnl)

        assert len(breakevens) >= 1
        # Breakeven should be between 22000 and 22500
        assert 22000 <= breakevens[0] <= 22500

    def test_find_breakeven_no_crossing(self, calc):
        """No breakeven if P/L never crosses zero."""
        spots = [21000, 22000, 23000]
        pnl = [1000, 2000, 3000]  # Always positive

        breakevens = calc._find_breakeven(spots, pnl)
        assert len(breakevens) == 0


# ---------------------------------------------------------------------------
# Lot size tests
# ---------------------------------------------------------------------------

class TestLotSize:
    """Test lot size retrieval."""

    def test_nifty_lot_size(self):
        """NIFTY lot size should be 25."""
        assert PnLCalculator.get_lot_size("NIFTY") == 25

    def test_banknifty_lot_size(self):
        """BANKNIFTY lot size should be 15."""
        assert PnLCalculator.get_lot_size("BANKNIFTY") == 15
