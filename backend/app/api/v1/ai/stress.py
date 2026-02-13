"""
Stress Testing API - Priority 1.1

Endpoints for stress Greeks testing and scenario analysis.
Allows users to visualize portfolio risk under multiple spot price scenarios.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models import User
from app.models.ai import AIUserConfig
from app.services.options.greeks_calculator import GreeksCalculatorService
from app.services.ai.stress_greeks_engine import StressGreeksEngine, StressTestResult

router = APIRouter()


# Request/Response Models
class PositionLegInput(BaseModel):
    """Position leg for stress testing."""
    strike: float
    expiry: str  # ISO date format
    option_type: str  # CE or PE
    quantity: int
    action: str  # BUY or SELL
    iv: float = Field(default=0.20, ge=0.01, le=5.0)  # Implied volatility


class StressTestRequest(BaseModel):
    """Request for stress testing."""
    legs: List[PositionLegInput]
    current_spot: float = Field(gt=0)
    lot_size: int = Field(default=1, gt=0)


class DeploymentRiskRequest(BaseModel):
    """Request for deployment risk evaluation."""
    portfolio_legs: List[PositionLegInput]
    new_strategy_legs: List[PositionLegInput]
    current_spot: float = Field(gt=0)
    lot_size: int = Field(default=1, gt=0)


@router.post("/scenarios", response_model=Dict[str, Any])
async def calculate_stress_scenarios(
    request: StressTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate stress scenarios for a position or strategy.

    Returns Greeks and estimated P&L under multiple spot price scenarios
    (±1% to ±5% from current spot).

    **Use Cases:**
    - Visualize portfolio risk before deployment
    - Understand tail risk exposure
    - Compare strategies under stress

    **Example Response:**
    ```json
    {
      "current_spot": 25000,
      "stress_risk_score": 45.5,
      "risk_assessment": "MODERATE",
      "scenarios": [
        {
          "spot_change_pct": -5.0,
          "stressed_spot": 23750,
          "delta": -0.45,
          "gamma": 0.0012,
          "estimated_pnl": -2500
        },
        ...
      ],
      "max_loss_scenario": {...},
      "max_gain_scenario": {...}
    }
    ```
    """
    try:
        # Create services
        greeks_calculator = GreeksCalculatorService(db, current_user.id)
        stress_engine = StressGreeksEngine(greeks_calculator)

        # Convert legs to dict format
        legs = [leg.dict() for leg in request.legs]

        # Calculate stress scenarios
        result = await stress_engine.calculate_stress_scenarios(
            legs=legs,
            current_spot=request.current_spot,
            lot_size=request.lot_size
        )

        # Get risk assessment
        risk_assessment = stress_engine.get_risk_assessment(result.stress_risk_score)

        return {
            **result.to_dict(),
            'risk_assessment': risk_assessment
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating stress scenarios: {str(e)}"
        )


@router.post("/evaluate-deployment", response_model=Dict[str, Any])
async def evaluate_deployment_risk(
    request: DeploymentRiskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate if deploying a new strategy would exceed stress risk limits.

    Calculates combined portfolio stress after adding new strategy
    and checks against user-configured limits.

    **Decision Criteria:**
    - Combined stress risk score <= max_stress_risk_score (default: 75)
    - Max portfolio delta <= max_portfolio_delta (default: 1.0)
    - Max portfolio gamma <= max_portfolio_gamma (default: 0.05)

    **Returns:**
    - `acceptable`: Whether deployment is acceptable
    - `violations`: Reasons for rejection (if any)
    - `combined_stress_risk_score`: Risk score after deployment
    - `portfolio_stress`: Current portfolio stress analysis
    - `new_strategy_stress`: New strategy stress analysis

    **Example Response:**
    ```json
    {
      "acceptable": false,
      "violations": [
        "Combined stress risk score (82.5) exceeds limit (75.0)"
      ],
      "combined_stress_risk_score": 82.5,
      "portfolio_stress_risk_score": 55.2,
      "new_strategy_stress_risk_score": 48.3
    }
    ```
    """
    try:
        # Get user AI config for stress limits
        from sqlalchemy import select
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == current_user.id)
        result = await db.execute(stmt)
        ai_config = result.scalar_one_or_none()

        if not ai_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI configuration not found for user"
            )

        # Create services
        greeks_calculator = GreeksCalculatorService(db, current_user.id)
        stress_engine = StressGreeksEngine(greeks_calculator)

        # Convert legs to dict format
        portfolio_legs = [leg.dict() for leg in request.portfolio_legs]
        new_strategy_legs = [leg.dict() for leg in request.new_strategy_legs]

        # Calculate stress scenarios
        portfolio_stress = await stress_engine.calculate_stress_scenarios(
            legs=portfolio_legs,
            current_spot=request.current_spot,
            lot_size=request.lot_size
        )

        new_strategy_stress = await stress_engine.calculate_stress_scenarios(
            legs=new_strategy_legs,
            current_spot=request.current_spot,
            lot_size=request.lot_size
        )

        # Evaluate deployment risk
        evaluation = stress_engine.evaluate_deployment_risk(
            portfolio_stress_result=portfolio_stress,
            new_strategy_stress_result=new_strategy_stress,
            max_stress_risk_score=float(ai_config.max_stress_risk_score),
            max_portfolio_delta=float(ai_config.max_portfolio_delta),
            max_portfolio_gamma=float(ai_config.max_portfolio_gamma)
        )

        # Add stress test results
        evaluation['portfolio_stress'] = portfolio_stress.to_dict()
        evaluation['new_strategy_stress'] = new_strategy_stress.to_dict()

        # Add risk assessments
        evaluation['portfolio_risk_assessment'] = stress_engine.get_risk_assessment(
            portfolio_stress.stress_risk_score
        )
        evaluation['new_strategy_risk_assessment'] = stress_engine.get_risk_assessment(
            new_strategy_stress.stress_risk_score
        )
        evaluation['combined_risk_assessment'] = stress_engine.get_risk_assessment(
            evaluation['combined_stress_risk_score']
        )

        return evaluation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating deployment risk: {str(e)}"
        )


@router.get("/limits", response_model=Dict[str, float])
async def get_stress_limits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's stress Greeks limits.

    Returns the configured limits for stress risk score, delta, and gamma
    that gate autonomous deployments.
    """
    try:
        from sqlalchemy import select
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == current_user.id)
        result = await db.execute(stmt)
        ai_config = result.scalar_one_or_none()

        if not ai_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI configuration not found for user"
            )

        return {
            'max_stress_risk_score': float(ai_config.max_stress_risk_score),
            'max_portfolio_delta': float(ai_config.max_portfolio_delta),
            'max_portfolio_gamma': float(ai_config.max_portfolio_gamma)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stress limits: {str(e)}"
        )


__all__ = ["router"]
