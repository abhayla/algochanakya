"""
Greeks Calculator Service Tests

Tests for GreeksCalculatorService including:
- Individual Greek calculations (Delta, Gamma, Theta, Vega, Rho)
- Position aggregate Greeks
- Greeks snapshot
- Delta hedge calculation
- Option pricing
- IV calculation
- P&L estimation
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.options.greeks_calculator import (
    GreeksCalculatorService,
    get_greeks_calculator_service,
    TRADING_DAYS_PER_YEAR,
    CALENDAR_DAYS_PER_YEAR,
    RISK_FREE_RATE
)
from app.models.users import User


# =============================================================================
# Delta Calculation Tests
# =============================================================================

class TestDeltaCalculation:
    """Test Delta calculations."""

    @pytest.mark.asyncio
    async def test_call_delta_atm(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test ATM call delta is approximately 0.5."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # ATM call delta should be approximately 0.5
        assert 0.45 < response.total_delta < 0.55

    @pytest.mark.asyncio
    async def test_put_delta_atm(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test ATM put delta is approximately -0.5."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "PE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # ATM put delta should be approximately -0.5
        assert -0.55 < response.total_delta < -0.45

    @pytest.mark.asyncio
    async def test_deep_itm_call_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test deep ITM call delta approaches 1."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 24000,  # Deep ITM
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Deep ITM call delta should be close to 1
        assert response.total_delta > 0.85

    @pytest.mark.asyncio
    async def test_deep_otm_call_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test deep OTM call delta approaches 0."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 27000,  # Deep OTM
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Deep OTM call delta should be close to 0
        assert response.total_delta < 0.15

    @pytest.mark.asyncio
    async def test_sell_action_reverses_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that selling reverses the delta sign."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "SELL",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Sold ATM call delta should be approximately -0.5
        assert -0.55 < response.total_delta < -0.45


# =============================================================================
# Gamma Calculation Tests
# =============================================================================

class TestGammaCalculation:
    """Test Gamma calculations."""

    @pytest.mark.asyncio
    async def test_gamma_highest_atm(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that Gamma is highest for ATM options."""
        service = GreeksCalculatorService(db_session, test_user.id)

        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        # ATM option
        legs_atm = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": expiry,
            "quantity": 1,
            "iv": 0.20
        }]

        # OTM option
        legs_otm = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 26000,
            "expiry": expiry,
            "quantity": 1,
            "iv": 0.20
        }]

        response_atm = await service.calculate_position_greeks(legs_atm, spot_price=25000)
        response_otm = await service.calculate_position_greeks(legs_otm, spot_price=25000)

        # ATM gamma should be higher than OTM gamma
        assert abs(response_atm.total_gamma) > abs(response_otm.total_gamma)

    @pytest.mark.asyncio
    async def test_gamma_increases_near_expiry(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that ATM Gamma increases as expiry approaches."""
        service = GreeksCalculatorService(db_session, test_user.id)

        # 30 days to expiry
        legs_30d = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        # 7 days to expiry
        legs_7d = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response_30d = await service.calculate_position_greeks(legs_30d, spot_price=25000)
        response_7d = await service.calculate_position_greeks(legs_7d, spot_price=25000)

        # Gamma should be higher for shorter expiry
        assert abs(response_7d.total_gamma) > abs(response_30d.total_gamma)


# =============================================================================
# Theta Calculation Tests
# =============================================================================

class TestThetaCalculation:
    """Test Theta (time decay) calculations."""

    @pytest.mark.asyncio
    async def test_long_option_negative_theta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that long options have negative theta (time decay)."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Long option has negative theta
        assert response.total_theta < 0

    @pytest.mark.asyncio
    async def test_short_option_positive_theta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that short options have positive theta (collect time decay)."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "SELL",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Short option has positive theta
        assert response.total_theta > 0

    @pytest.mark.asyncio
    async def test_theta_accelerates_near_expiry(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that theta decay accelerates near expiry."""
        service = GreeksCalculatorService(db_session, test_user.id)

        # 30 days to expiry
        legs_30d = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        # 7 days to expiry
        legs_7d = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response_30d = await service.calculate_position_greeks(legs_30d, spot_price=25000)
        response_7d = await service.calculate_position_greeks(legs_7d, spot_price=25000)

        # Theta decay should be faster (more negative) for shorter expiry
        assert response_7d.total_theta < response_30d.total_theta


# =============================================================================
# Vega Calculation Tests
# =============================================================================

class TestVegaCalculation:
    """Test Vega (volatility sensitivity) calculations."""

    @pytest.mark.asyncio
    async def test_long_option_positive_vega(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that long options have positive vega."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Long option has positive vega
        assert response.total_vega > 0

    @pytest.mark.asyncio
    async def test_short_option_negative_vega(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that short options have negative vega."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "SELL",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Short option has negative vega
        assert response.total_vega < 0

    @pytest.mark.asyncio
    async def test_vega_higher_longer_expiry(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that vega is higher for longer expiry options."""
        service = GreeksCalculatorService(db_session, test_user.id)

        # 7 days to expiry
        legs_7d = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        # 60 days to expiry
        legs_60d = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        response_7d = await service.calculate_position_greeks(legs_7d, spot_price=25000)
        response_60d = await service.calculate_position_greeks(legs_60d, spot_price=25000)

        # Vega should be higher for longer expiry
        assert response_60d.total_vega > response_7d.total_vega


# =============================================================================
# Position Aggregate Greeks Tests
# =============================================================================

class TestPositionAggregateGreeks:
    """Test aggregate Greeks for multi-leg positions."""

    @pytest.mark.asyncio
    async def test_iron_condor_near_zero_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test iron condor has near-zero delta."""
        service = GreeksCalculatorService(db_session, test_user.id)

        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        legs = [
            {"action": "SELL", "option_type": "CE", "strike": 25500, "expiry": expiry, "quantity": 1, "iv": 0.20},
            {"action": "BUY", "option_type": "CE", "strike": 25600, "expiry": expiry, "quantity": 1, "iv": 0.20},
            {"action": "SELL", "option_type": "PE", "strike": 24500, "expiry": expiry, "quantity": 1, "iv": 0.20},
            {"action": "BUY", "option_type": "PE", "strike": 24400, "expiry": expiry, "quantity": 1, "iv": 0.20}
        ]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Iron condor should have near-zero delta
        assert abs(response.total_delta) < 0.1

    @pytest.mark.asyncio
    async def test_straddle_near_zero_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test ATM straddle has near-zero delta."""
        service = GreeksCalculatorService(db_session, test_user.id)

        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        legs = [
            {"action": "BUY", "option_type": "CE", "strike": 25000, "expiry": expiry, "quantity": 1, "iv": 0.20},
            {"action": "BUY", "option_type": "PE", "strike": 25000, "expiry": expiry, "quantity": 1, "iv": 0.20}
        ]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # ATM straddle should have near-zero delta
        assert abs(response.total_delta) < 0.1

    @pytest.mark.asyncio
    async def test_credit_spread_positive_theta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test credit spread has positive theta."""
        service = GreeksCalculatorService(db_session, test_user.id)

        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        legs = [
            {"action": "SELL", "option_type": "CE", "strike": 25500, "expiry": expiry, "quantity": 1, "iv": 0.20},
            {"action": "BUY", "option_type": "CE", "strike": 25600, "expiry": expiry, "quantity": 1, "iv": 0.20}
        ]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        # Credit spread should have positive theta
        assert response.total_theta > 0


# =============================================================================
# Greeks Snapshot Tests
# =============================================================================

class TestGreeksSnapshot:
    """Test Greeks snapshot calculations."""

    @pytest.mark.asyncio
    async def test_greeks_snapshot_returns_decimals(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that Greeks snapshot returns Decimal values."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "quantity": 1,
            "iv": 0.20
        }]

        snapshot = service.calculate_greeks_snapshot(legs, spot_price=25000)

        assert isinstance(snapshot.delta, Decimal)
        assert isinstance(snapshot.gamma, Decimal)
        assert isinstance(snapshot.theta, Decimal)
        assert isinstance(snapshot.vega, Decimal)


# =============================================================================
# Delta Hedge Calculation Tests
# =============================================================================

class TestDeltaHedgeCalculation:
    """Test delta hedge quantity calculations."""

    @pytest.mark.asyncio
    async def test_delta_hedge_buy_when_negative(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test delta hedge suggests buying when delta is negative."""
        service = GreeksCalculatorService(db_session, test_user.id)

        result = service.calculate_delta_hedge_quantity(
            current_delta=-1.5,
            target_delta=0,
            spot_price=25000,
            lot_size=25
        )

        assert result['action_needed'] is True
        assert result['action'] == 'BUY'

    @pytest.mark.asyncio
    async def test_delta_hedge_sell_when_positive(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test delta hedge suggests selling when delta is positive."""
        service = GreeksCalculatorService(db_session, test_user.id)

        result = service.calculate_delta_hedge_quantity(
            current_delta=1.5,
            target_delta=0,
            spot_price=25000,
            lot_size=25
        )

        assert result['action_needed'] is True
        assert result['action'] == 'SELL'

    @pytest.mark.asyncio
    async def test_delta_hedge_not_needed_when_neutral(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test no hedge needed when already delta neutral."""
        service = GreeksCalculatorService(db_session, test_user.id)

        result = service.calculate_delta_hedge_quantity(
            current_delta=0.005,
            target_delta=0,
            spot_price=25000,
            lot_size=25
        )

        assert result['action_needed'] is False


# =============================================================================
# Option Pricing Tests
# =============================================================================

class TestOptionPricing:
    """Test Black-Scholes option pricing."""

    @pytest.mark.asyncio
    async def test_call_price_increases_with_spot(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test call price increases when spot increases."""
        service = GreeksCalculatorService(db_session, test_user.id)

        price_low = service.calculate_option_price(
            spot=24000,
            strike=25000,
            time_to_expiry=0.1,  # ~36 days
            volatility=0.20,
            is_call=True
        )

        price_high = service.calculate_option_price(
            spot=26000,
            strike=25000,
            time_to_expiry=0.1,
            volatility=0.20,
            is_call=True
        )

        assert price_high > price_low

    @pytest.mark.asyncio
    async def test_put_price_decreases_with_spot(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test put price decreases when spot increases."""
        service = GreeksCalculatorService(db_session, test_user.id)

        price_low = service.calculate_option_price(
            spot=24000,
            strike=25000,
            time_to_expiry=0.1,
            volatility=0.20,
            is_call=False
        )

        price_high = service.calculate_option_price(
            spot=26000,
            strike=25000,
            time_to_expiry=0.1,
            volatility=0.20,
            is_call=False
        )

        assert price_low > price_high

    @pytest.mark.asyncio
    async def test_expired_option_intrinsic_value(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test expired option returns intrinsic value."""
        service = GreeksCalculatorService(db_session, test_user.id)

        # ITM call at expiry
        price = service.calculate_option_price(
            spot=26000,
            strike=25000,
            time_to_expiry=0,
            volatility=0.20,
            is_call=True
        )

        # Should be intrinsic value = 26000 - 25000 = 1000
        assert price == 1000


# =============================================================================
# Implied Volatility Tests
# =============================================================================

class TestImpliedVolatility:
    """Test IV calculation from option price."""

    @pytest.mark.asyncio
    async def test_iv_calculation_converges(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test IV calculation converges for reasonable prices."""
        service = GreeksCalculatorService(db_session, test_user.id)

        # Calculate price with known IV
        known_iv = 0.25
        price = service.calculate_option_price(
            spot=25000,
            strike=25000,
            time_to_expiry=0.1,
            volatility=known_iv,
            is_call=True
        )

        # Calculate IV from price
        calculated_iv = service.calculate_iv_from_price(
            option_price=price,
            spot=25000,
            strike=25000,
            time_to_expiry=0.1,
            is_call=True
        )

        assert calculated_iv is not None
        assert abs(calculated_iv - known_iv) < 0.01

    @pytest.mark.asyncio
    async def test_iv_returns_none_for_expired(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test IV returns None for expired option."""
        service = GreeksCalculatorService(db_session, test_user.id)

        iv = service.calculate_iv_from_price(
            option_price=500,
            spot=25000,
            strike=25000,
            time_to_expiry=0,
            is_call=True
        )

        assert iv is None


# =============================================================================
# P&L Estimation Tests
# =============================================================================

class TestPnLEstimation:
    """Test P&L estimation using delta-gamma approximation."""

    @pytest.mark.asyncio
    async def test_pnl_estimation_positive_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test P&L estimation for position with positive delta."""
        service = GreeksCalculatorService(db_session, test_user.id)

        pnl = service.estimate_pnl_for_spot_change(
            current_delta=0.5,
            current_gamma=0.001,
            spot_change=100,  # Spot increases by 100
            lot_size=25
        )

        # With positive delta, spot increase should give positive P&L
        assert pnl > 0

    @pytest.mark.asyncio
    async def test_pnl_estimation_negative_delta(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test P&L estimation for position with negative delta."""
        service = GreeksCalculatorService(db_session, test_user.id)

        pnl = service.estimate_pnl_for_spot_change(
            current_delta=-0.5,
            current_gamma=0.001,
            spot_change=100,  # Spot increases by 100
            lot_size=25
        )

        # With negative delta, spot increase should give negative P&L
        assert pnl < 0


# =============================================================================
# Expired Options Tests
# =============================================================================

class TestExpiredOptions:
    """Test handling of expired options."""

    @pytest.mark.asyncio
    async def test_expired_option_zero_greeks(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test that expired options have zero Greeks (except intrinsic delta)."""
        service = GreeksCalculatorService(db_session, test_user.id)

        legs = [{
            "action": "BUY",
            "option_type": "CE",
            "strike": 25000,
            "expiry": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),  # Past expiry
            "quantity": 1,
            "iv": 0.20
        }]

        response = await service.calculate_position_greeks(legs, spot_price=25000)

        assert len(response.leg_greeks) == 1
        assert response.leg_greeks[0].get('expired') is True


# =============================================================================
# Factory Tests
# =============================================================================

class TestGreeksCalculatorFactory:
    """Test GreeksCalculatorService factory function."""

    @pytest.mark.asyncio
    async def test_get_greeks_calculator_service(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test factory function creates service instance."""
        service = await get_greeks_calculator_service(db_session, test_user.id)

        assert isinstance(service, GreeksCalculatorService)
        assert service.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_set_risk_free_rate(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test setting custom risk-free rate."""
        service = GreeksCalculatorService(db_session, test_user.id)

        service.set_risk_free_rate(0.08)

        assert service.risk_free_rate == 0.08
