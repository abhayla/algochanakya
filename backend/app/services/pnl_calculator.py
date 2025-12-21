"""
P/L Calculator Service for Options Strategy Builder.

Provides intrinsic value (at expiry) and Black-Scholes (current) P/L calculations.
"""

import math
from typing import List, Dict, Optional, Tuple
from datetime import date
from decimal import Decimal

from app.constants import get_lot_size

# Try to import scipy, fallback to pure Python implementation if not available
try:
    from scipy.stats import norm
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    import warnings
    warnings.warn("scipy not installed. Using approximation for Black-Scholes.")


def _norm_cdf(x: float) -> float:
    """Approximation of standard normal CDF when scipy is not available."""
    # Abramowitz and Stegun approximation
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)

    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

    return 0.5 * (1.0 + sign * y)


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    if HAS_SCIPY:
        return norm.cdf(x)
    return _norm_cdf(x)


class PnLCalculator:
    """
    Service for calculating P/L at various spot prices for options strategies.

    Supports two modes:
    - 'expiry': Intrinsic value at expiry
    - 'current': Black-Scholes theoretical value before expiry
    """

    def __init__(self, risk_free_rate: float = 0.07):
        """
        Initialize P/L calculator.

        Args:
            risk_free_rate: Annual risk-free interest rate (default 7%)
        """
        self.risk_free_rate = risk_free_rate

    @staticmethod
    def get_lot_size(underlying: str) -> int:
        """Get lot size for underlying."""
        return get_lot_size(underlying)

    def calculate_pnl_grid(
        self,
        legs: List[dict],
        spot_prices: List[float],
        mode: str = "expiry",
        target_date: Optional[date] = None,
        volatility: float = 0.15
    ) -> Dict:
        """
        Calculate P/L at various spot prices for all legs.

        Args:
            legs: List of leg dictionaries with keys:
                - strike: Strike price
                - contract_type: 'CE' or 'PE'
                - transaction_type: 'BUY' or 'SELL'
                - lots: Number of lots
                - lot_size: Lot size
                - entry_price: Entry premium
                - expiry_date: Expiry date
            spot_prices: List of spot prices to calculate P/L for
            mode: 'expiry' for intrinsic value, 'current' for Black-Scholes
            target_date: Target date for 'current' mode (defaults to today)
            volatility: Implied volatility (default 15%)

        Returns:
            Dictionary with:
                - spot_prices: List of spot prices
                - leg_pnl: List of P/L arrays for each leg
                - total_pnl: Combined P/L at each spot price
                - max_profit: Maximum possible profit
                - max_loss: Maximum possible loss
                - breakeven: List of breakeven points
        """
        if target_date is None:
            target_date = date.today()

        leg_pnl = []

        for leg in legs:
            pnl_at_spots = []

            # Get leg parameters
            strike = float(leg.get("strike", 0))
            contract_type = leg.get("contract_type", "CE").upper()
            transaction_type = leg.get("transaction_type", "BUY").upper()
            lots = int(leg.get("lots", 1))
            lot_size = int(leg.get("lot_size", 75))
            entry_price = float(leg.get("entry_price", 0) or 0)
            expiry_date = leg.get("expiry_date")

            # Convert expiry_date to date object if string
            if isinstance(expiry_date, str):
                expiry_date = date.fromisoformat(expiry_date)

            qty = lots * lot_size
            multiplier = 1 if transaction_type == "BUY" else -1

            for spot in spot_prices:
                if mode == "expiry":
                    # Intrinsic value at expiry
                    option_value = self._intrinsic_value(spot, strike, contract_type)
                else:
                    # Black-Scholes value before expiry
                    if expiry_date:
                        days_to_expiry = (expiry_date - target_date).days
                    else:
                        days_to_expiry = 0

                    if days_to_expiry <= 0:
                        option_value = self._intrinsic_value(spot, strike, contract_type)
                    else:
                        option_value = self._black_scholes(
                            spot,
                            strike,
                            days_to_expiry / 365.0,
                            self.risk_free_rate,
                            volatility,
                            contract_type
                        )

                # P/L = (Current Value - Entry Price) * Qty * Multiplier
                pnl = (option_value - entry_price) * qty * multiplier
                pnl_at_spots.append(round(pnl, 2))

            leg_pnl.append(pnl_at_spots)

        # Calculate total P/L across all legs
        if leg_pnl:
            total_pnl = [
                round(sum(leg[i] for leg in leg_pnl), 2)
                for i in range(len(spot_prices))
            ]
        else:
            total_pnl = [0.0] * len(spot_prices)

        # Find max profit/loss
        max_profit = max(total_pnl) if total_pnl else 0
        max_loss = min(total_pnl) if total_pnl else 0

        # Find breakeven points
        breakevens = self._find_breakeven(spot_prices, total_pnl)

        return {
            "spot_prices": spot_prices,
            "leg_pnl": leg_pnl,
            "total_pnl": total_pnl,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakeven": breakevens
        }

    def _intrinsic_value(self, spot: float, strike: float, option_type: str) -> float:
        """
        Calculate intrinsic value at expiry.

        Args:
            spot: Spot price
            strike: Strike price
            option_type: 'CE' or 'PE'

        Returns:
            Intrinsic value (always >= 0)
        """
        if option_type == "CE":
            return max(0, spot - strike)
        else:  # PE
            return max(0, strike - spot)

    def _black_scholes(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str
    ) -> float:
        """
        Calculate option price using Black-Scholes model.

        Args:
            spot: Current spot price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate
            volatility: Implied volatility
            option_type: 'CE' or 'PE'

        Returns:
            Theoretical option price
        """
        if time_to_expiry <= 0:
            return self._intrinsic_value(spot, strike, option_type)

        if spot <= 0 or strike <= 0 or volatility <= 0:
            return 0.0

        try:
            sqrt_t = math.sqrt(time_to_expiry)
            d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (volatility * sqrt_t)
            d2 = d1 - volatility * sqrt_t

            if option_type == "CE":
                price = spot * norm_cdf(d1) - strike * math.exp(-risk_free_rate * time_to_expiry) * norm_cdf(d2)
            else:  # PE
                price = strike * math.exp(-risk_free_rate * time_to_expiry) * norm_cdf(-d2) - spot * norm_cdf(-d1)

            return max(0, price)
        except (ValueError, ZeroDivisionError):
            return self._intrinsic_value(spot, strike, option_type)

    def _find_breakeven(self, spots: List[float], pnl: List[float]) -> List[float]:
        """
        Find breakeven points where P/L crosses zero.

        Args:
            spots: List of spot prices
            pnl: List of P/L values at each spot

        Returns:
            List of breakeven points
        """
        breakevens = []

        for i in range(1, len(pnl)):
            # Check if P/L crosses zero between consecutive points
            if (pnl[i - 1] < 0 and pnl[i] >= 0) or (pnl[i - 1] >= 0 and pnl[i] < 0):
                # Linear interpolation to find exact breakeven
                try:
                    be = spots[i - 1] + (spots[i] - spots[i - 1]) * abs(pnl[i - 1]) / (abs(pnl[i - 1]) + abs(pnl[i]))
                    breakevens.append(round(be, 2))
                except ZeroDivisionError:
                    pass

        return breakevens

    def calculate_greeks(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str,
        risk_free_rate: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate option Greeks.

        Args:
            spot: Current spot price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: 'CE' or 'PE'
            risk_free_rate: Risk-free rate (uses instance default if None)

        Returns:
            Dictionary with delta, gamma, theta, vega, rho
        """
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        if time_to_expiry <= 0 or spot <= 0 or strike <= 0 or volatility <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}

        try:
            sqrt_t = math.sqrt(time_to_expiry)
            d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (volatility * sqrt_t)
            d2 = d1 - volatility * sqrt_t

            # PDF of standard normal at d1
            pdf_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)

            # Delta
            if option_type == "CE":
                delta = norm_cdf(d1)
            else:
                delta = norm_cdf(d1) - 1

            # Gamma (same for call and put)
            gamma = pdf_d1 / (spot * volatility * sqrt_t)

            # Theta
            term1 = -(spot * pdf_d1 * volatility) / (2 * sqrt_t)
            if option_type == "CE":
                term2 = risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry) * norm_cdf(d2)
                theta = (term1 - term2) / 365  # Per day
            else:
                term2 = risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry) * norm_cdf(-d2)
                theta = (term1 + term2) / 365  # Per day

            # Vega (same for call and put)
            vega = spot * sqrt_t * pdf_d1 / 100  # Per 1% change

            # Rho
            if option_type == "CE":
                rho = strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm_cdf(d2) / 100
            else:
                rho = -strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm_cdf(-d2) / 100

            return {
                "delta": round(delta, 4),
                "gamma": round(gamma, 6),
                "theta": round(theta, 2),
                "vega": round(vega, 2),
                "rho": round(rho, 2)
            }
        except (ValueError, ZeroDivisionError):
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}


def generate_spot_range(
    strikes: List[float],
    current_spot: float,
    interval: int = 100,
    padding: int = 200,
    breakevens: Optional[List[float]] = None,
    include_strikes: bool = True
) -> List[float]:
    """
    Generate spot price range for P/L columns.

    Args:
        strikes: List of strike prices in the strategy
        current_spot: Current spot price
        interval: Price interval between columns (50 or 100)
        padding: Padding beyond min/max strikes (default 200)
        breakevens: List of breakeven points to include
        include_strikes: Whether to include all strike prices in the range

    Returns:
        List of spot prices for P/L calculation
    """
    if not strikes:
        # If no strikes, use current spot as center
        if current_spot > 0:
            strikes = [current_spot]
        else:
            return []

    min_strike = min(strikes)
    max_strike = max(strikes)

    # Calculate base range with padding
    min_spot = min_strike - padding
    max_spot = max_strike + padding

    # Extend range to always include currentSpot ± 200
    min_spot = min(min_spot, current_spot - 200)
    max_spot = max(max_spot, current_spot + 200)

    # Generate spots at interval steps
    start = (min_spot // interval) * interval
    # Use ceiling division to ensure we include spots beyond max_spot
    # range() excludes endpoint, so we add one more interval
    end = math.ceil(max_spot / interval) * interval + interval

    spots = list(range(int(start), int(end), interval))

    # Add current spot rounded to nearest integer (not to interval)
    current_spot_rounded = round(current_spot)
    if current_spot_rounded not in spots:
        spots.append(int(current_spot_rounded))

    # Include all strike prices
    if include_strikes:
        for strike in strikes:
            strike_int = int(strike)
            if strike_int not in spots:
                spots.append(strike_int)

    # Include breakeven points (keep exact values for P/L = 0)
    if breakevens:
        for be in breakevens:
            # Keep exact breakeven value, not rounded, so P/L calculates to exactly 0
            # Check if a close value already exists (within 0.1 tolerance)
            if not any(abs(s - be) < 0.1 for s in spots):
                spots.append(be)

    spots.sort()
    return [float(s) for s in spots]


# Singleton instance
pnl_calculator = PnLCalculator()
