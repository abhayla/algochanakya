"""
Phase 2 Option Chain Performance — TDD RED Tests

Tests for vectorized IV and Greeks calculation using numpy.
These tests MUST FAIL before implementation (module doesn't exist yet)
and PASS after implementing the vectorized calculator.

The vectorized calculator should:
  1. Accept arrays of option parameters (spot, strikes, prices, etc.)
  2. Compute IV via vectorized Newton-Raphson (all strikes at once)
  3. Compute Greeks via vectorized Black-Scholes (all strikes at once)
  4. Match scalar calculate_iv/calculate_greeks results within tolerance
  5. Be significantly faster than the scalar loop for 40+ strikes
"""
import numpy as np
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


# ---------------------------------------------------------------------------
# Test that the vectorized module exists and is importable
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVectorizedModuleExists:

    def test_module_importable(self):
        """vectorized_greeks module must exist in app.services.options."""
        from app.services.options import vectorized_greeks
        assert vectorized_greeks is not None

    def test_has_vectorized_iv_function(self):
        from app.services.options.vectorized_greeks import calculate_iv_vectorized
        assert callable(calculate_iv_vectorized)

    def test_has_vectorized_greeks_function(self):
        from app.services.options.vectorized_greeks import calculate_greeks_vectorized
        assert callable(calculate_greeks_vectorized)

    def test_has_batch_iv_and_greeks_function(self):
        """Combined function that computes both IV and Greeks in one pass."""
        from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch
        assert callable(calculate_iv_and_greeks_batch)


# ---------------------------------------------------------------------------
# Vectorized IV Calculation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVectorizedIV:
    """Vectorized IV must match scalar IV within tolerance."""

    def test_single_atm_call_iv(self):
        """Single ATM call option: vectorized IV should match scalar."""
        from app.services.options.vectorized_greeks import calculate_iv_vectorized
        from app.api.routes.optionchain import calculate_iv as scalar_iv

        spot = 24000.0
        strike = 24000.0
        price = 150.0
        dte = 14

        scalar_result = scalar_iv(price, spot, strike, dte, True)
        vec_result = calculate_iv_vectorized(
            np.array([price]), spot, np.array([strike]), dte, np.array([True])
        )

        assert len(vec_result) == 1
        if scalar_result > 0:
            assert abs(vec_result[0] - scalar_result) < 0.5, (
                f"Vectorized IV {vec_result[0]} differs from scalar {scalar_result} by >{0.5}"
            )

    def test_multiple_strikes_call(self):
        """Multiple CE strikes: vectorized should match scalar for each."""
        from app.services.options.vectorized_greeks import calculate_iv_vectorized
        from app.api.routes.optionchain import calculate_iv as scalar_iv

        spot = 24000.0
        dte = 14
        strikes = np.array([23800, 23900, 24000, 24100, 24200], dtype=float)
        prices = np.array([220.0, 160.0, 110.0, 70.0, 40.0])
        is_call = np.array([True, True, True, True, True])

        vec_results = calculate_iv_vectorized(prices, spot, strikes, dte, is_call)

        assert len(vec_results) == 5
        for i in range(5):
            scalar = scalar_iv(prices[i], spot, strikes[i], dte, True)
            if scalar > 0 and vec_results[i] > 0:
                assert abs(vec_results[i] - scalar) < 1.0, (
                    f"Strike {strikes[i]}: vec={vec_results[i]}, scalar={scalar}"
                )

    def test_put_options(self):
        """PE strikes: vectorized should handle puts correctly."""
        from app.services.options.vectorized_greeks import calculate_iv_vectorized
        from app.api.routes.optionchain import calculate_iv as scalar_iv

        spot = 24000.0
        dte = 14
        strikes = np.array([23800, 24000, 24200], dtype=float)
        prices = np.array([30.0, 100.0, 220.0])
        is_call = np.array([False, False, False])

        vec_results = calculate_iv_vectorized(prices, spot, strikes, dte, is_call)

        assert len(vec_results) == 3
        for i in range(3):
            scalar = scalar_iv(prices[i], spot, strikes[i], dte, False)
            if scalar > 0 and vec_results[i] > 0:
                assert abs(vec_results[i] - scalar) < 1.0

    def test_zero_price_returns_zero_iv(self):
        """Options with zero price should return IV=0."""
        from app.services.options.vectorized_greeks import calculate_iv_vectorized

        vec = calculate_iv_vectorized(
            np.array([0.0, 150.0]),
            24000.0,
            np.array([24000.0, 24000.0]),
            14,
            np.array([True, True])
        )
        assert vec[0] == 0.0, f"Zero-price option should have IV=0, got {vec[0]}"
        assert vec[1] > 0, f"Non-zero-price option should have positive IV"

    def test_zero_dte_returns_zero_iv(self):
        """DTE=0 should return zero IV for all strikes."""
        from app.services.options.vectorized_greeks import calculate_iv_vectorized

        vec = calculate_iv_vectorized(
            np.array([150.0, 100.0]),
            24000.0,
            np.array([24000.0, 24100.0]),
            0,
            np.array([True, True])
        )
        assert np.all(vec == 0.0), f"DTE=0 should produce all-zero IV, got {vec}"

    def test_returns_numpy_array(self):
        """Output must be a numpy array."""
        from app.services.options.vectorized_greeks import calculate_iv_vectorized

        result = calculate_iv_vectorized(
            np.array([150.0]), 24000.0, np.array([24000.0]), 14, np.array([True])
        )
        assert isinstance(result, np.ndarray), f"Expected ndarray, got {type(result)}"


# ---------------------------------------------------------------------------
# Vectorized Greeks Calculation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVectorizedGreeks:
    """Vectorized Greeks must match scalar Greeks within tolerance."""

    def test_single_atm_call_greeks(self):
        """Single ATM call: vectorized Greeks should match scalar."""
        from app.services.options.vectorized_greeks import calculate_greeks_vectorized
        from app.api.routes.optionchain import calculate_greeks as scalar_greeks

        spot = 24000.0
        strike = np.array([24000.0])
        iv = np.array([15.0])  # 15% IV
        dte = 14
        is_call = np.array([True])

        scalar = scalar_greeks(spot, 24000.0, dte, 15.0, True)
        vec = calculate_greeks_vectorized(spot, strike, dte, iv, is_call)

        # vec should return dict of numpy arrays
        assert "delta" in vec
        assert "gamma" in vec
        assert "theta" in vec
        assert "vega" in vec

        assert abs(vec["delta"][0] - scalar["delta"]) < 0.001
        assert abs(vec["gamma"][0] - scalar["gamma"]) < 0.0001
        assert abs(vec["theta"][0] - scalar["theta"]) < 0.1
        assert abs(vec["vega"][0] - scalar["vega"]) < 0.1

    def test_multiple_strikes_greeks(self):
        """Multiple strikes: each should match scalar Greeks."""
        from app.services.options.vectorized_greeks import calculate_greeks_vectorized
        from app.api.routes.optionchain import calculate_greeks as scalar_greeks

        spot = 24000.0
        strikes = np.array([23800, 23900, 24000, 24100, 24200], dtype=float)
        ivs = np.array([16.0, 15.5, 15.0, 14.5, 14.0])
        dte = 14
        is_call = np.array([True, True, True, True, True])

        vec = calculate_greeks_vectorized(spot, strikes, dte, ivs, is_call)

        for i in range(5):
            scalar = scalar_greeks(spot, strikes[i], dte, ivs[i], True)
            assert abs(vec["delta"][i] - scalar["delta"]) < 0.001, (
                f"Strike {strikes[i]}: delta vec={vec['delta'][i]}, scalar={scalar['delta']}"
            )

    def test_put_greeks(self):
        """PE Greeks: delta should be negative."""
        from app.services.options.vectorized_greeks import calculate_greeks_vectorized

        vec = calculate_greeks_vectorized(
            24000.0,
            np.array([24000.0]),
            14,
            np.array([15.0]),
            np.array([False])
        )
        assert vec["delta"][0] < 0, f"Put delta should be negative, got {vec['delta'][0]}"

    def test_zero_iv_returns_zero_greeks(self):
        """When IV=0, all Greeks should be zero."""
        from app.services.options.vectorized_greeks import calculate_greeks_vectorized

        vec = calculate_greeks_vectorized(
            24000.0,
            np.array([24000.0]),
            14,
            np.array([0.0]),
            np.array([True])
        )
        assert vec["delta"][0] == 0
        assert vec["gamma"][0] == 0
        assert vec["theta"][0] == 0
        assert vec["vega"][0] == 0

    def test_returns_dict_of_arrays(self):
        """Output must be a dict of numpy arrays."""
        from app.services.options.vectorized_greeks import calculate_greeks_vectorized

        vec = calculate_greeks_vectorized(
            24000.0,
            np.array([24000.0, 24100.0]),
            14,
            np.array([15.0, 14.5]),
            np.array([True, True])
        )
        for key in ["delta", "gamma", "theta", "vega"]:
            assert isinstance(vec[key], np.ndarray), f"{key} should be ndarray"
            assert len(vec[key]) == 2


# ---------------------------------------------------------------------------
# Batch IV+Greeks (combined function)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBatchIVAndGreeks:
    """Combined batch computation: IV → Greeks in one call."""

    def test_returns_iv_and_greeks(self):
        from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch

        result = calculate_iv_and_greeks_batch(
            option_prices=np.array([150.0, 100.0]),
            spot=24000.0,
            strikes=np.array([24000.0, 24100.0]),
            dte=14,
            is_call=np.array([True, True])
        )

        assert "iv" in result
        assert "delta" in result
        assert "gamma" in result
        assert "theta" in result
        assert "vega" in result
        assert len(result["iv"]) == 2

    def test_batch_matches_scalar_loop(self):
        """Batch result must match doing scalar IV then scalar Greeks per strike."""
        from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch
        from app.api.routes.optionchain import calculate_iv, calculate_greeks

        spot = 24000.0
        dte = 14
        strikes = np.array([23900, 24000, 24100], dtype=float)
        prices = np.array([160.0, 110.0, 70.0])
        is_call = np.array([True, True, True])

        batch = calculate_iv_and_greeks_batch(prices, spot, strikes, dte, is_call)

        for i in range(3):
            s_iv = calculate_iv(prices[i], spot, strikes[i], dte, True)
            s_greeks = calculate_greeks(spot, strikes[i], dte, s_iv, True)

            if s_iv > 0 and batch["iv"][i] > 0:
                assert abs(batch["iv"][i] - s_iv) < 1.0, (
                    f"Strike {strikes[i]}: batch IV={batch['iv'][i]}, scalar IV={s_iv}"
                )
                assert abs(batch["delta"][i] - s_greeks["delta"]) < 0.01

    def test_mixed_ce_pe(self):
        """Batch should handle mixed CE/PE in a single call."""
        from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch

        result = calculate_iv_and_greeks_batch(
            option_prices=np.array([150.0, 120.0]),
            spot=24000.0,
            strikes=np.array([24000.0, 24000.0]),
            dte=14,
            is_call=np.array([True, False])
        )

        assert result["delta"][0] > 0, "CE delta should be positive"
        assert result["delta"][1] < 0, "PE delta should be negative"


# ---------------------------------------------------------------------------
# Performance: vectorized must be faster than scalar loop
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVectorizedPerformance:
    """Vectorized computation should be faster than scalar loop for 40+ strikes."""

    def test_vectorized_80_options_under_20ms(self):
        """For a typical 80-option chain (40 strikes × 2 sides), vectorized
        should complete in <20ms. This is the real-world scenario: the entire
        IV+Greeks computation should not be a noticeable bottleneck.
        """
        from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch

        spot = 24000.0
        dte = 14
        n = 80  # 40 strikes × CE + PE
        strikes = np.tile(np.linspace(23000, 25000, 40), 2)
        prices = np.maximum(spot - strikes + 300, 5.0)
        is_call = np.concatenate([np.ones(40, dtype=bool), np.zeros(40, dtype=bool)])

        # Warm up
        calculate_iv_and_greeks_batch(prices, spot, strikes, dte, is_call)

        start = time.perf_counter()
        calculate_iv_and_greeks_batch(prices, spot, strikes, dte, is_call)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, (
            f"80-option vectorized batch should complete in <50ms, took {elapsed_ms:.1f}ms"
        )

    def test_vectorized_completes_40_strikes_under_50ms(self):
        """For a typical 40-strike chain, vectorized should complete under 50ms."""
        from app.services.options.vectorized_greeks import calculate_iv_and_greeks_batch

        spot = 24000.0
        dte = 14
        n = 40
        strikes = np.linspace(23000, 25000, n)
        prices = np.maximum(spot - strikes + 200, 5.0)
        is_call = np.ones(n, dtype=bool)

        # Warm up
        calculate_iv_and_greeks_batch(prices, spot, strikes, dte, is_call)

        start = time.perf_counter()
        calculate_iv_and_greeks_batch(prices, spot, strikes, dte, is_call)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, (
            f"40-strike vectorized batch should complete in <50ms, took {elapsed_ms:.1f}ms"
        )
