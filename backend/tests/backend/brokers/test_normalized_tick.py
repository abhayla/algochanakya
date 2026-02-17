"""Tests for NormalizedTick dataclass."""

import pytest
from datetime import datetime
from decimal import Decimal

from app.services.brokers.market_data.ticker.models import NormalizedTick


class TestNormalizedTick:
    """Test NormalizedTick creation and serialization."""

    def test_create_with_required_fields(self):
        tick = NormalizedTick(token=256265, ltp=Decimal("24500.50"))
        assert tick.token == 256265
        assert tick.ltp == Decimal("24500.50")
        assert tick.volume == 0
        assert tick.oi == 0
        assert tick.broker_type == ""

    def test_create_with_all_fields(self):
        ts = datetime(2026, 2, 16, 10, 30, 0)
        tick = NormalizedTick(
            token=256265,
            ltp=Decimal("24500.50"),
            open=Decimal("24400.00"),
            high=Decimal("24600.00"),
            low=Decimal("24350.00"),
            close=Decimal("24450.00"),
            change=Decimal("50.50"),
            change_percent=Decimal("0.21"),
            volume=1500000,
            oi=5000000,
            timestamp=ts,
            broker_type="smartapi",
            bid=Decimal("24500.00"),
            ask=Decimal("24501.00"),
            bid_qty=100,
            ask_qty=200,
        )
        assert tick.token == 256265
        assert tick.ltp == Decimal("24500.50")
        assert tick.open == Decimal("24400.00")
        assert tick.close == Decimal("24450.00")
        assert tick.change == Decimal("50.50")
        assert tick.volume == 1500000
        assert tick.oi == 5000000
        assert tick.broker_type == "smartapi"
        assert tick.bid == Decimal("24500.00")
        assert tick.ask_qty == 200
        assert tick.timestamp == ts

    def test_decimal_precision_preserved(self):
        tick = NormalizedTick(token=1, ltp=Decimal("0.05"))
        assert tick.ltp == Decimal("0.05")
        assert str(tick.ltp) == "0.05"

    def test_to_dict_basic(self):
        tick = NormalizedTick(
            token=256265,
            ltp=Decimal("24500.50"),
            broker_type="kite",
        )
        d = tick.to_dict()
        assert d["token"] == 256265
        assert d["ltp"] == 24500.50
        assert isinstance(d["ltp"], float)
        assert d["broker_type"] == "kite"
        assert d["volume"] == 0
        assert "bid" not in d  # Optional, not set
        assert "ask" not in d

    def test_to_dict_with_optional_fields(self):
        tick = NormalizedTick(
            token=256265,
            ltp=Decimal("100.00"),
            bid=Decimal("99.50"),
            ask=Decimal("100.50"),
            bid_qty=50,
            ask_qty=75,
            broker_type="smartapi",
        )
        d = tick.to_dict()
        assert d["bid"] == 99.50
        assert d["ask"] == 100.50
        assert d["bid_qty"] == 50
        assert d["ask_qty"] == 75

    def test_to_dict_timestamp_iso_format(self):
        ts = datetime(2026, 2, 16, 10, 30, 0)
        tick = NormalizedTick(token=1, ltp=Decimal("100"), timestamp=ts)
        d = tick.to_dict()
        assert d["timestamp"] == "2026-02-16T10:30:00"

    def test_to_dict_change_metrics(self):
        tick = NormalizedTick(
            token=1,
            ltp=Decimal("24500"),
            close=Decimal("24400"),
            change=Decimal("100"),
            change_percent=Decimal("0.41"),
        )
        d = tick.to_dict()
        assert d["change"] == 100.0
        assert d["change_percent"] == pytest.approx(0.41)
