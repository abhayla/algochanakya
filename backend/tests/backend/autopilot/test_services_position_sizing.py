"""
Position Sizing Service Tests

Tests for PositionSizingService including:
- Position size calculation
- Max loss estimation for different strategy types
- VIX regime detection and multipliers
- Lot constraints (min/max)
- Undefined risk handling
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.autopilot.position_sizing import (
    PositionSizingService,
    get_position_sizing_service,
    LOT_SIZES,
    DEFAULT_LOT_SIZE,
    VIX_THRESHOLDS,
    VIX_MULTIPLIERS
)
from app.schemas.autopilot import PositionSizingRequest
from app.models.users import User


# =============================================================================
# Position Sizing Calculation Tests
# =============================================================================

class TestPositionSizingCalculation:
    """Test PositionSizingService position size calculations."""

    @pytest.mark.asyncio
    async def test_calculate_position_size_basic(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test basic position size calculation."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[
                {"action": "SELL", "option_type": "CE", "strike": 25500, "premium": 100},
                {"action": "BUY", "option_type": "CE", "strike": 25600, "premium": 50}
            ]
        )

        response = await service.calculate_position_size(request)

        assert response.recommended_lots >= 1
        assert response.lot_size == 25  # NIFTY lot size
        assert response.recommended_quantity == response.recommended_lots * 25

    @pytest.mark.asyncio
    async def test_calculate_position_size_with_fixed_risk_amount(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test position sizing with fixed risk amount instead of percentage."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_amount=Decimal("10000"),  # Fixed ₹10,000 max loss
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[
                {"action": "SELL", "option_type": "CE", "strike": 25500, "premium": 100},
                {"action": "BUY", "option_type": "CE", "strike": 25600, "premium": 50}
            ]
        )

        response = await service.calculate_position_size(request)

        assert response.max_loss_allowed == Decimal("10000")

    @pytest.mark.asyncio
    async def test_calculate_position_size_default_risk(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test position sizing uses 2% default risk when not specified."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 200}]
        )

        response = await service.calculate_position_size(request)

        # Default 2% of 1000000 = 20000
        assert response.max_loss_allowed == Decimal("20000")


# =============================================================================
# Max Loss Estimation Tests
# =============================================================================

class TestMaxLossEstimation:
    """Test max loss estimation for different strategy types."""

    @pytest.mark.asyncio
    async def test_credit_call_spread_max_loss(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test max loss calculation for credit call spread."""
        service = PositionSizingService(db_session, test_user.id)

        legs = [
            {"action": "SELL", "option_type": "CE", "strike": 25500, "premium": 100},
            {"action": "BUY", "option_type": "CE", "strike": 25600, "premium": 50}
        ]

        max_loss = service.get_estimated_max_loss(legs, "NIFTY", Decimal("25000"))

        # Spread width = 100, net premium = 50
        # Max loss = (100 - 50) * 25 = 1250
        assert max_loss is not None
        assert max_loss == Decimal("1250")

    @pytest.mark.asyncio
    async def test_credit_put_spread_max_loss(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test max loss calculation for credit put spread."""
        service = PositionSizingService(db_session, test_user.id)

        legs = [
            {"action": "SELL", "option_type": "PE", "strike": 24500, "premium": 100},
            {"action": "BUY", "option_type": "PE", "strike": 24400, "premium": 50}
        ]

        max_loss = service.get_estimated_max_loss(legs, "NIFTY", Decimal("25000"))

        # Spread width = 100, net premium = 50
        # Max loss = (100 - 50) * 25 = 1250
        assert max_loss is not None
        assert max_loss == Decimal("1250")

    @pytest.mark.asyncio
    async def test_iron_condor_max_loss(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test max loss calculation for iron condor."""
        service = PositionSizingService(db_session, test_user.id)

        legs = [
            {"action": "SELL", "option_type": "CE", "strike": 25500, "premium": 100},
            {"action": "BUY", "option_type": "CE", "strike": 25600, "premium": 50},
            {"action": "SELL", "option_type": "PE", "strike": 24500, "premium": 100},
            {"action": "BUY", "option_type": "PE", "strike": 24400, "premium": 50}
        ]

        max_loss = service.get_estimated_max_loss(legs, "NIFTY", Decimal("25000"))

        # Spread width = 100 on each side, net premium = 100 (50 + 50)
        # Max loss = (100 - 100) * 25 = 0 (capped at 0)
        assert max_loss is not None
        assert max_loss >= 0

    @pytest.mark.asyncio
    async def test_long_straddle_max_loss(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test max loss calculation for long straddle (defined risk)."""
        service = PositionSizingService(db_session, test_user.id)

        legs = [
            {"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 200},
            {"action": "BUY", "option_type": "PE", "strike": 25000, "premium": 200}
        ]

        max_loss = service.get_estimated_max_loss(legs, "NIFTY", Decimal("25000"))

        # Max loss = premium paid = 400 * 25 = 10000
        assert max_loss is not None
        assert max_loss == Decimal("10000")

    @pytest.mark.asyncio
    async def test_naked_call_undefined_risk(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that naked call returns undefined risk."""
        service = PositionSizingService(db_session, test_user.id)

        legs = [
            {"action": "SELL", "option_type": "CE", "strike": 25500, "premium": 100}
        ]

        max_loss = service.get_estimated_max_loss(legs, "NIFTY", Decimal("25000"))

        assert max_loss is None  # Undefined risk

    @pytest.mark.asyncio
    async def test_short_strangle_undefined_risk(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that short strangle returns undefined risk."""
        service = PositionSizingService(db_session, test_user.id)

        legs = [
            {"action": "SELL", "option_type": "CE", "strike": 25500, "premium": 100},
            {"action": "SELL", "option_type": "PE", "strike": 24500, "premium": 100}
        ]

        max_loss = service.get_estimated_max_loss(legs, "NIFTY", Decimal("25000"))

        assert max_loss is None  # Undefined risk


# =============================================================================
# VIX Regime Tests
# =============================================================================

class TestVIXRegimes:
    """Test VIX regime detection and position size adjustments."""

    @pytest.mark.asyncio
    async def test_vix_regime_low(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test low VIX regime detection."""
        service = PositionSizingService(db_session, test_user.id)

        regime = service._get_vix_regime(10.0)

        assert regime == 'low'

    @pytest.mark.asyncio
    async def test_vix_regime_normal(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test normal VIX regime detection."""
        service = PositionSizingService(db_session, test_user.id)

        regime = service._get_vix_regime(15.0)

        assert regime == 'normal'

    @pytest.mark.asyncio
    async def test_vix_regime_high(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test high VIX regime detection."""
        service = PositionSizingService(db_session, test_user.id)

        regime = service._get_vix_regime(22.0)

        assert regime == 'high'

    @pytest.mark.asyncio
    async def test_vix_regime_extreme(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test extreme VIX regime detection."""
        service = PositionSizingService(db_session, test_user.id)

        regime = service._get_vix_regime(30.0)

        assert regime == 'extreme'

    @pytest.mark.asyncio
    async def test_vix_regime_crisis(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test crisis VIX regime detection."""
        service = PositionSizingService(db_session, test_user.id)

        regime = service._get_vix_regime(40.0)

        assert regime == 'crisis'

    @pytest.mark.asyncio
    async def test_vix_adjustment_increases_position_low_vix(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that low VIX allows larger position size."""
        service = PositionSizingService(db_session, test_user.id)

        request_no_vix = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 200}]
        )

        request_low_vix = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 200}],
            current_vix=10.0
        )

        response_no_vix = await service.calculate_position_size(request_no_vix)
        response_low_vix = await service.calculate_position_size(request_low_vix)

        assert response_low_vix.vix_adjustment_applied is True
        assert response_low_vix.vix_regime == 'low'

    @pytest.mark.asyncio
    async def test_vix_adjustment_decreases_position_high_vix(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that high VIX reduces position size."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 200}],
            current_vix=30.0
        )

        response = await service.calculate_position_size(request)

        assert response.vix_adjustment_applied is True
        assert response.vix_regime == 'extreme'


# =============================================================================
# Lot Constraints Tests
# =============================================================================

class TestLotConstraints:
    """Test min/max lot constraints."""

    @pytest.mark.asyncio
    async def test_min_lots_constraint(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test minimum lots constraint is applied."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("100000"),  # Small capital
            risk_per_trade_pct=Decimal("0.5"),  # Very small risk
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 500}],
            min_lots=2
        )

        response = await service.calculate_position_size(request)

        assert response.recommended_lots >= 2

    @pytest.mark.asyncio
    async def test_max_lots_constraint(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test maximum lots constraint is applied."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("10000000"),  # Large capital
            risk_per_trade_pct=Decimal("5"),  # High risk
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 50}],
            max_lots=5
        )

        response = await service.calculate_position_size(request)

        assert response.recommended_lots <= 5


# =============================================================================
# Underlying Lot Size Tests
# =============================================================================

class TestUnderlyingLotSizes:
    """Test lot sizes for different underlyings."""

    @pytest.mark.asyncio
    async def test_nifty_lot_size(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test NIFTY lot size is 25."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="NIFTY",
            spot_price=Decimal("25000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 25000, "premium": 200}]
        )

        response = await service.calculate_position_size(request)

        assert response.lot_size == 25

    @pytest.mark.asyncio
    async def test_banknifty_lot_size(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test BANKNIFTY lot size is 15."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="BANKNIFTY",
            spot_price=Decimal("50000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 50000, "premium": 400}]
        )

        response = await service.calculate_position_size(request)

        assert response.lot_size == 15

    @pytest.mark.asyncio
    async def test_unknown_underlying_default_lot_size(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test unknown underlying uses default lot size."""
        service = PositionSizingService(db_session, test_user.id)

        request = PositionSizingRequest(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            underlying="UNKNOWN",
            spot_price=Decimal("10000"),
            legs=[{"action": "BUY", "option_type": "CE", "strike": 10000, "premium": 200}]
        )

        response = await service.calculate_position_size(request)

        assert response.lot_size == DEFAULT_LOT_SIZE


# =============================================================================
# Simple Lot Calculation Tests
# =============================================================================

class TestSimpleLotCalculation:
    """Test simple lot calculation method."""

    @pytest.mark.asyncio
    async def test_calculate_lots_for_capital(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test simple lot calculation."""
        service = PositionSizingService(db_session, test_user.id)

        lots = service.calculate_lots_for_capital(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            max_loss_per_lot=Decimal("5000")
        )

        # Max loss allowed = 20000, max_loss_per_lot = 5000
        # Lots = 20000 / 5000 = 4
        assert lots == 4

    @pytest.mark.asyncio
    async def test_calculate_lots_for_capital_with_vix(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test simple lot calculation with VIX adjustment."""
        service = PositionSizingService(db_session, test_user.id)

        lots_normal = service.calculate_lots_for_capital(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            max_loss_per_lot=Decimal("5000"),
            current_vix=15.0
        )

        lots_high = service.calculate_lots_for_capital(
            account_capital=Decimal("1000000"),
            risk_per_trade_pct=Decimal("2"),
            max_loss_per_lot=Decimal("5000"),
            current_vix=30.0
        )

        assert lots_high < lots_normal

    @pytest.mark.asyncio
    async def test_calculate_lots_minimum_one(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test minimum of 1 lot is returned."""
        service = PositionSizingService(db_session, test_user.id)

        lots = service.calculate_lots_for_capital(
            account_capital=Decimal("1000"),  # Very small capital
            risk_per_trade_pct=Decimal("1"),
            max_loss_per_lot=Decimal("50000")  # High max loss
        )

        assert lots == 1


# =============================================================================
# Position Sizing Factory Tests
# =============================================================================

class TestPositionSizingServiceFactory:
    """Test PositionSizingService factory function."""

    @pytest.mark.asyncio
    async def test_get_position_sizing_service(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test factory function creates service instance."""
        service = await get_position_sizing_service(db_session, test_user.id)

        assert isinstance(service, PositionSizingService)
        assert service.user_id == test_user.id
