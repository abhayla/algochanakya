"""
Bug Reproduction: NIFTY lot size returns 25 instead of 75

NSE changed NIFTY lot size from 25 → 75 in November 2024.
The constants in trading.py still have the old value of 25.

These tests FAIL until trading.py is corrected.
"""

import pytest
from app.constants.trading import LOT_SIZES, get_lot_size


class TestNiftyLotSize:
    """
    Reproduces: LOT_SIZES["NIFTY"] = 25 but NSE current lot size is 75.

    NSE lot size history:
      - Before Nov 2024: 50 lots (was 75 before that too — varies)
      - From Nov 28 2024 F&O expiry: 75 lots per contract
      - Source: NSE circular NSCCL/CMPT/54491 (Oct 2024)
    """

    def test_nifty_lot_size_is_75(self):
        """NIFTY lot size must be 75 (NSE changed it in Nov 2024, currently 75)."""
        assert LOT_SIZES["NIFTY"] == 75, (
            f"NIFTY lot size is {LOT_SIZES['NIFTY']} but should be 75. "
            "NSE changed NIFTY lot size to 75 in November 2024."
        )

    def test_get_lot_size_nifty_returns_75(self):
        """get_lot_size('NIFTY') must return 75."""
        result = get_lot_size("NIFTY")
        assert result == 75, (
            f"get_lot_size('NIFTY') returned {result} but should return 75."
        )

    def test_banknifty_lot_size_is_35(self):
        """BANKNIFTY lot size must be 35 (NSE changed it in Nov 2024)."""
        assert LOT_SIZES["BANKNIFTY"] == 35, (
            f"BANKNIFTY lot size is {LOT_SIZES['BANKNIFTY']} but should be 35. "
            "NSE changed BANKNIFTY lot size to 35 in November 2024."
        )

    def test_finnifty_lot_size_is_65(self):
        """FINNIFTY lot size must be 65 (NSE changed it in Nov 2024)."""
        assert LOT_SIZES["FINNIFTY"] == 65, (
            f"FINNIFTY lot size is {LOT_SIZES['FINNIFTY']} but should be 65. "
            "NSE changed FINNIFTY lot size to 65 in November 2024."
        )

    def test_sensex_lot_size_is_20(self):
        """SENSEX lot size must be 20 (BSE changed it in Nov 2024)."""
        assert LOT_SIZES["SENSEX"] == 20, (
            f"SENSEX lot size is {LOT_SIZES['SENSEX']} but should be 20. "
            "BSE changed SENSEX lot size to 20 in November 2024."
        )
