"""
Substance test for GreeksCalculatorService.calculate_iv_from_price.

The live option chain showed CE IV=17.15 vs PE IV=10.33 at the same ATM
strike, and later IV=0.00 for most strikes. The hypothesis is that the IV
solver is fine — the wide skew / zero IV is what happens when the solver
gets a 100x-off option price as input (the LTP-scale bug tracked in
test_smartapi_convert_unified_quote.py + task #29).

This test pins the solver's own correctness with a REALISTIC input:
NIFTY 24000 CE ATM at spot 24000 with 7 days to expiry and ~ATR-consistent
IV of 15% should round-trip cleanly. If the solver ever regresses, this
fails visibly.
"""

from app.services.options.greeks_calculator import GreeksCalculatorService


def _bs_price_for_iv(iv_pct):
    """Compute a synthetic ATM CE price for the given IV via the same B-S
    the solver uses — that guarantees the solver's inverse can round-trip."""
    calc = GreeksCalculatorService()
    spot = 24000.0
    strike = 24000.0
    tte_years = 7 / 365
    return calc.calculate_option_price(spot, strike, tte_years, iv_pct / 100, is_call=True)


def test_iv_solver_round_trips_atm_ce():
    """IV solver on an ATM CE with realistic 15% IV recovers ~15%."""
    calc = GreeksCalculatorService()
    target_iv_pct = 15.0
    px = _bs_price_for_iv(target_iv_pct)
    solved = calc.calculate_iv_from_price(
        option_price=px,
        spot=24000.0,
        strike=24000.0,
        time_to_expiry=7 / 365,
        is_call=True,
    )
    assert solved is not None, "Solver failed to converge on a well-conditioned input"
    # Solver returns IV as a decimal fraction (0.15 for 15%)
    assert 0.14 < solved < 0.16, f"Expected ~0.15, got {solved}"


def test_iv_solver_returns_none_or_low_on_100x_too_small_input():
    """This is the failure mode we see live — LTP=1.7 for an ATM CE where
    the true price is ~170. The solver either fails to converge (returns
    None) or returns a very small IV (which the chain renders as 0.00).
    Either way, the observed 'IV=0.00' downstream is EXPECTED behaviour
    given the broken LTP input — the bug is in the LTP, not the solver."""
    calc = GreeksCalculatorService()
    # Real ATM CE at spot=24000 with 7-day IV=15% would be ~₹170.
    # Feed the solver the 100x-too-small version.
    broken_px = 1.7
    solved = calc.calculate_iv_from_price(
        option_price=broken_px,
        spot=24000.0,
        strike=24000.0,
        time_to_expiry=7 / 365,
        is_call=True,
    )
    # Either None (didn't converge) or very small — both are "would render as 0.00"
    assert solved is None or solved < 0.01, (
        f"Solver should have failed or returned tiny IV for broken input, got {solved}"
    )
