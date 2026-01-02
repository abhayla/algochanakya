"""
OFO (Options For Options) Calculator Service

Generates and ranks the best strategy combinations from option chain data.
Finds top 3 most profitable combinations for each strategy type.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from itertools import combinations, product

from app.constants import get_lot_size, get_strike_step
from app.services.pnl_calculator import PnLCalculator, generate_spot_range


class OFOCalculator:
    """
    Service for finding optimal option strategy combinations.

    Generates all valid combinations for each strategy type,
    calculates P/L at expiry, and ranks by maximum profit.
    """

    # Minimum premium filter (in INR)
    MIN_PREMIUM = 1.0

    # Maximum combinations to evaluate per strategy (performance limit)
    MAX_COMBINATIONS_PER_STRATEGY = 5000

    def __init__(self):
        self.pnl_calculator = PnLCalculator()

    def is_valid_option(self, option_data: Optional[Dict]) -> bool:
        """
        Check if option data is valid for trading.

        Filters out:
        - None/missing data
        - CMP = 0, 0.5, or null
        - OI <= 0
        - Premium < MIN_PREMIUM
        """
        if option_data is None:
            return False

        ltp = option_data.get("ltp")
        if ltp is None or ltp == 0 or ltp == 0.5:
            return False

        oi = option_data.get("oi", 0)
        if oi is None or oi <= 0:
            return False

        if ltp < self.MIN_PREMIUM:
            return False

        return True

    def get_option_data(
        self,
        chain_data: List[Dict],
        strike: float,
        option_type: str
    ) -> Optional[Dict]:
        """Get option data for a specific strike and type (CE/PE)."""
        for row in chain_data:
            if row.get("strike") == strike:
                return row.get(option_type.lower())
        return None

    def get_valid_strikes(
        self,
        chain_data: List[Dict],
        atm_strike: float,
        strike_range: int,
        strike_step: int
    ) -> List[float]:
        """
        Get list of valid strikes within range of ATM.

        Returns strikes that have valid option data on both CE and PE sides.
        """
        min_strike = atm_strike - (strike_range * strike_step)
        max_strike = atm_strike + (strike_range * strike_step)

        valid_strikes = []
        for row in chain_data:
            strike = row.get("strike")
            if strike is None:
                continue
            if min_strike <= strike <= max_strike:
                valid_strikes.append(strike)

        return sorted(valid_strikes)

    def calculate_strategy_pnl(
        self,
        legs: List[Dict],
        spot_price: float,
        lot_size: int,
        lots: int,
        expiry_date: str
    ) -> Dict:
        """
        Calculate P/L metrics for a strategy combination.

        Uses PnLCalculator with mode='expiry' for max profit at expiry.
        """
        # Build legs in format expected by PnLCalculator
        pnl_legs = []
        for leg in legs:
            pnl_legs.append({
                "strike": leg["strike"],
                "contract_type": leg["type"],
                "transaction_type": leg["action"],
                "lots": lots,
                "lot_size": lot_size,
                "entry_price": leg["ltp"],
                "expiry_date": expiry_date
            })

        # Generate spot range around current price
        strikes = [leg["strike"] for leg in legs]
        spot_range = generate_spot_range(strikes, spot_price, interval=100, padding=500)

        # Calculate P/L grid at expiry
        result = self.pnl_calculator.calculate_pnl_grid(
            pnl_legs,
            spot_range,
            mode="expiry"
        )

        # Calculate net premium (credit/debit)
        net_premium = 0.0
        for leg in legs:
            premium = leg["ltp"] * lots * lot_size
            if leg["action"] == "SELL":
                net_premium += premium
            else:
                net_premium -= premium

        # Calculate risk-reward ratio
        max_profit = result.get("max_profit", 0)
        max_loss = result.get("max_loss", 0)
        risk_reward = abs(max_profit / max_loss) if max_loss != 0 else 0

        return {
            "max_profit": max_profit,
            "max_loss": max_loss,
            "breakevens": result.get("breakeven", []),
            "net_premium": round(net_premium, 2),
            "risk_reward_ratio": round(risk_reward, 2)
        }

    # =========================================================================
    # COMBINATION GENERATORS FOR EACH STRATEGY TYPE
    # =========================================================================

    def generate_iron_condor_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Iron Condor combinations.

        Structure: Buy OTM PE, Sell PE, Sell CE, Buy OTM CE
        Constraint: PE_buy < PE_sell < CE_sell < CE_buy
        """
        combinations_list = []

        # Get PE strikes below ATM and CE strikes above ATM
        pe_strikes = [s for s in valid_strikes if s < atm_strike]
        ce_strikes = [s for s in valid_strikes if s > atm_strike]

        for pe_buy in pe_strikes:
            pe_buy_data = self.get_option_data(chain_data, pe_buy, "PE")
            if not self.is_valid_option(pe_buy_data):
                continue

            for pe_sell in pe_strikes:
                if pe_sell <= pe_buy:
                    continue
                pe_sell_data = self.get_option_data(chain_data, pe_sell, "PE")
                if not self.is_valid_option(pe_sell_data):
                    continue

                for ce_sell in ce_strikes:
                    ce_sell_data = self.get_option_data(chain_data, ce_sell, "CE")
                    if not self.is_valid_option(ce_sell_data):
                        continue

                    for ce_buy in ce_strikes:
                        if ce_buy <= ce_sell:
                            continue
                        ce_buy_data = self.get_option_data(chain_data, ce_buy, "CE")
                        if not self.is_valid_option(ce_buy_data):
                            continue

                        combinations_list.append({
                            "legs": [
                                {"type": "PE", "action": "BUY", "strike": pe_buy, **pe_buy_data},
                                {"type": "PE", "action": "SELL", "strike": pe_sell, **pe_sell_data},
                                {"type": "CE", "action": "SELL", "strike": ce_sell, **ce_sell_data},
                                {"type": "CE", "action": "BUY", "strike": ce_buy, **ce_buy_data}
                            ]
                        })

                        if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                            return combinations_list

        return combinations_list

    def generate_iron_butterfly_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Iron Butterfly combinations.

        Structure: Buy OTM PE, Sell ATM PE, Sell ATM CE, Buy OTM CE
        Constraint: PE_buy < ATM (PE_sell = CE_sell) < CE_buy
        """
        combinations_list = []

        for center_strike in valid_strikes:
            pe_sell_data = self.get_option_data(chain_data, center_strike, "PE")
            ce_sell_data = self.get_option_data(chain_data, center_strike, "CE")

            if not self.is_valid_option(pe_sell_data) or not self.is_valid_option(ce_sell_data):
                continue

            # Wings must be equidistant from center
            for wing_width in [100, 200, 300, 400, 500]:
                pe_buy_strike = center_strike - wing_width
                ce_buy_strike = center_strike + wing_width

                if pe_buy_strike not in valid_strikes or ce_buy_strike not in valid_strikes:
                    continue

                pe_buy_data = self.get_option_data(chain_data, pe_buy_strike, "PE")
                ce_buy_data = self.get_option_data(chain_data, ce_buy_strike, "CE")

                if not self.is_valid_option(pe_buy_data) or not self.is_valid_option(ce_buy_data):
                    continue

                combinations_list.append({
                    "legs": [
                        {"type": "PE", "action": "BUY", "strike": pe_buy_strike, **pe_buy_data},
                        {"type": "PE", "action": "SELL", "strike": center_strike, **pe_sell_data},
                        {"type": "CE", "action": "SELL", "strike": center_strike, **ce_sell_data},
                        {"type": "CE", "action": "BUY", "strike": ce_buy_strike, **ce_buy_data}
                    ]
                })

                if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                    return combinations_list

        return combinations_list

    def generate_short_straddle_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Short Straddle combinations.

        Structure: Sell CE + Sell PE at same strike
        """
        combinations_list = []

        for strike in valid_strikes:
            ce_data = self.get_option_data(chain_data, strike, "CE")
            pe_data = self.get_option_data(chain_data, strike, "PE")

            if not self.is_valid_option(ce_data) or not self.is_valid_option(pe_data):
                continue

            combinations_list.append({
                "legs": [
                    {"type": "CE", "action": "SELL", "strike": strike, **ce_data},
                    {"type": "PE", "action": "SELL", "strike": strike, **pe_data}
                ]
            })

        return combinations_list

    def generate_short_strangle_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Short Strangle combinations.

        Structure: Sell OTM CE + Sell OTM PE at different strikes
        Constraint: PE_strike < ATM < CE_strike
        """
        combinations_list = []

        pe_strikes = [s for s in valid_strikes if s < atm_strike]
        ce_strikes = [s for s in valid_strikes if s > atm_strike]

        for pe_strike in pe_strikes:
            pe_data = self.get_option_data(chain_data, pe_strike, "PE")
            if not self.is_valid_option(pe_data):
                continue

            for ce_strike in ce_strikes:
                ce_data = self.get_option_data(chain_data, ce_strike, "CE")
                if not self.is_valid_option(ce_data):
                    continue

                combinations_list.append({
                    "legs": [
                        {"type": "CE", "action": "SELL", "strike": ce_strike, **ce_data},
                        {"type": "PE", "action": "SELL", "strike": pe_strike, **pe_data}
                    ]
                })

                if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                    return combinations_list

        return combinations_list

    def generate_long_straddle_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Long Straddle combinations.

        Structure: Buy CE + Buy PE at same strike
        """
        combinations_list = []

        for strike in valid_strikes:
            ce_data = self.get_option_data(chain_data, strike, "CE")
            pe_data = self.get_option_data(chain_data, strike, "PE")

            if not self.is_valid_option(ce_data) or not self.is_valid_option(pe_data):
                continue

            combinations_list.append({
                "legs": [
                    {"type": "CE", "action": "BUY", "strike": strike, **ce_data},
                    {"type": "PE", "action": "BUY", "strike": strike, **pe_data}
                ]
            })

        return combinations_list

    def generate_long_strangle_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Long Strangle combinations.

        Structure: Buy OTM CE + Buy OTM PE at different strikes
        Constraint: PE_strike < ATM < CE_strike
        """
        combinations_list = []

        pe_strikes = [s for s in valid_strikes if s < atm_strike]
        ce_strikes = [s for s in valid_strikes if s > atm_strike]

        for pe_strike in pe_strikes:
            pe_data = self.get_option_data(chain_data, pe_strike, "PE")
            if not self.is_valid_option(pe_data):
                continue

            for ce_strike in ce_strikes:
                ce_data = self.get_option_data(chain_data, ce_strike, "CE")
                if not self.is_valid_option(ce_data):
                    continue

                combinations_list.append({
                    "legs": [
                        {"type": "CE", "action": "BUY", "strike": ce_strike, **ce_data},
                        {"type": "PE", "action": "BUY", "strike": pe_strike, **pe_data}
                    ]
                })

                if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                    return combinations_list

        return combinations_list

    def generate_bull_call_spread_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Bull Call Spread combinations.

        Structure: Buy lower CE, Sell higher CE
        Constraint: buy_strike < sell_strike
        """
        combinations_list = []

        for buy_strike in valid_strikes:
            buy_data = self.get_option_data(chain_data, buy_strike, "CE")
            if not self.is_valid_option(buy_data):
                continue

            for sell_strike in valid_strikes:
                if sell_strike <= buy_strike:
                    continue

                sell_data = self.get_option_data(chain_data, sell_strike, "CE")
                if not self.is_valid_option(sell_data):
                    continue

                combinations_list.append({
                    "legs": [
                        {"type": "CE", "action": "BUY", "strike": buy_strike, **buy_data},
                        {"type": "CE", "action": "SELL", "strike": sell_strike, **sell_data}
                    ]
                })

                if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                    return combinations_list

        return combinations_list

    def generate_bear_put_spread_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Bear Put Spread combinations.

        Structure: Buy higher PE, Sell lower PE
        Constraint: sell_strike < buy_strike
        """
        combinations_list = []

        for buy_strike in valid_strikes:
            buy_data = self.get_option_data(chain_data, buy_strike, "PE")
            if not self.is_valid_option(buy_data):
                continue

            for sell_strike in valid_strikes:
                if sell_strike >= buy_strike:
                    continue

                sell_data = self.get_option_data(chain_data, sell_strike, "PE")
                if not self.is_valid_option(sell_data):
                    continue

                combinations_list.append({
                    "legs": [
                        {"type": "PE", "action": "BUY", "strike": buy_strike, **buy_data},
                        {"type": "PE", "action": "SELL", "strike": sell_strike, **sell_data}
                    ]
                })

                if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                    return combinations_list

        return combinations_list

    def generate_butterfly_spread_combinations(
        self,
        chain_data: List[Dict],
        valid_strikes: List[float],
        atm_strike: float
    ) -> List[Dict]:
        """
        Generate all valid Butterfly Spread combinations.

        Structure: Buy low CE, Sell 2x middle CE, Buy high CE
        Constraint: Equidistant strikes (low + high) / 2 = middle
        """
        combinations_list = []

        for middle_strike in valid_strikes:
            middle_data = self.get_option_data(chain_data, middle_strike, "CE")
            if not self.is_valid_option(middle_data):
                continue

            # Wings must be equidistant from middle
            for wing_width in [100, 200, 300, 400, 500]:
                low_strike = middle_strike - wing_width
                high_strike = middle_strike + wing_width

                if low_strike not in valid_strikes or high_strike not in valid_strikes:
                    continue

                low_data = self.get_option_data(chain_data, low_strike, "CE")
                high_data = self.get_option_data(chain_data, high_strike, "CE")

                if not self.is_valid_option(low_data) or not self.is_valid_option(high_data):
                    continue

                combinations_list.append({
                    "legs": [
                        {"type": "CE", "action": "BUY", "strike": low_strike, **low_data},
                        {"type": "CE", "action": "SELL", "strike": middle_strike, **middle_data},
                        {"type": "CE", "action": "SELL", "strike": middle_strike, **middle_data},
                        {"type": "CE", "action": "BUY", "strike": high_strike, **high_data}
                    ]
                })

                if len(combinations_list) >= self.MAX_COMBINATIONS_PER_STRATEGY:
                    return combinations_list

        return combinations_list

    # =========================================================================
    # MAIN CALCULATION METHOD
    # =========================================================================

    def calculate_best_strategies(
        self,
        chain_data: List[Dict],
        spot_price: float,
        expiry: str,
        underlying: str,
        strategy_types: List[str],
        strike_range: int = 10,
        lots: int = 1,
        top_n: int = 3
    ) -> Dict:
        """
        Calculate top N best combinations for each strategy type.

        Args:
            chain_data: Option chain data with CE/PE prices
            spot_price: Current spot price
            expiry: Expiry date (YYYY-MM-DD)
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            strategy_types: List of strategy types to calculate
            strike_range: Number of strikes to consider on each side of ATM
            lots: Number of lots per leg
            top_n: Number of top combinations to return per strategy

        Returns:
            Dict with results for each strategy type and metadata
        """
        start_time = time.time()

        # Get constants
        lot_size = get_lot_size(underlying)
        strike_step = get_strike_step(underlying)

        # Calculate ATM strike
        atm_strike = round(spot_price / strike_step) * strike_step

        # Get valid strikes within range
        valid_strikes = self.get_valid_strikes(
            chain_data, atm_strike, strike_range, strike_step
        )

        # Strategy generator mapping
        generators = {
            "iron_condor": self.generate_iron_condor_combinations,
            "iron_butterfly": self.generate_iron_butterfly_combinations,
            "short_straddle": self.generate_short_straddle_combinations,
            "short_strangle": self.generate_short_strangle_combinations,
            "long_straddle": self.generate_long_straddle_combinations,
            "long_strangle": self.generate_long_strangle_combinations,
            "bull_call_spread": self.generate_bull_call_spread_combinations,
            "bear_put_spread": self.generate_bear_put_spread_combinations,
            "butterfly_spread": self.generate_butterfly_spread_combinations
        }

        # Strategy display names
        display_names = {
            "iron_condor": "Iron Condor",
            "iron_butterfly": "Iron Butterfly",
            "short_straddle": "Short Straddle",
            "short_strangle": "Short Strangle",
            "long_straddle": "Long Straddle",
            "long_strangle": "Long Strangle",
            "bull_call_spread": "Bull Call Spread",
            "bear_put_spread": "Bear Put Spread",
            "butterfly_spread": "Butterfly Spread"
        }

        results = {}
        total_combinations = 0

        for strategy_type in strategy_types:
            if strategy_type not in generators:
                continue

            # Generate combinations
            combinations_list = generators[strategy_type](
                chain_data, valid_strikes, atm_strike
            )
            total_combinations += len(combinations_list)

            if not combinations_list:
                results[strategy_type] = []
                continue

            # Calculate P/L for each combination
            scored_combinations = []
            for combo in combinations_list:
                try:
                    pnl_result = self.calculate_strategy_pnl(
                        combo["legs"],
                        spot_price,
                        lot_size,
                        lots,
                        expiry
                    )

                    scored_combinations.append({
                        "strategy_type": strategy_type,
                        "strategy_name": display_names[strategy_type],
                        "legs": combo["legs"],
                        **pnl_result
                    })
                except Exception:
                    # Skip combinations that fail P/L calculation
                    continue

            # Sort by max_profit (descending) with secondary sort by risk_reward_ratio
            scored_combinations.sort(
                key=lambda x: (x["max_profit"], x["risk_reward_ratio"]),
                reverse=True
            )

            # Filter out duplicate P/L profiles (same max_profit, max_loss, breakevens)
            # to ensure we show meaningfully different combinations
            seen_profiles = set()
            unique_combinations = []
            for combo in scored_combinations:
                # Create a profile key based on P/L metrics
                profile_key = (
                    round(combo["max_profit"], 0),
                    round(combo["max_loss"], 0),
                    tuple(round(b, 0) for b in sorted(combo["breakevens"])) if combo["breakevens"] else ()
                )
                if profile_key not in seen_profiles:
                    seen_profiles.add(profile_key)
                    unique_combinations.append(combo)
                    if len(unique_combinations) >= top_n:
                        break

            top_combinations = unique_combinations

            # Format legs for response
            for combo in top_combinations:
                formatted_legs = []
                for leg in combo["legs"]:
                    formatted_legs.append({
                        "expiry": expiry,
                        "contract_type": leg["type"],
                        "transaction_type": leg["action"],
                        "strike": leg["strike"],
                        "cmp": leg.get("ltp", 0),
                        "lots": lots,
                        "qty": lots * lot_size,
                        "instrument_token": leg.get("instrument_token", 0),
                        "tradingsymbol": leg.get("tradingsymbol", "")
                    })
                combo["legs"] = formatted_legs

            results[strategy_type] = top_combinations

        end_time = time.time()
        calculation_time_ms = int((end_time - start_time) * 1000)

        return {
            "underlying": underlying,
            "expiry": expiry,
            "spot_price": spot_price,
            "atm_strike": atm_strike,
            "lot_size": lot_size,
            "calculated_at": datetime.now(),
            "calculation_time_ms": calculation_time_ms,
            "total_combinations_evaluated": total_combinations,
            "results": results
        }


# Singleton instance
ofo_calculator = OFOCalculator()
