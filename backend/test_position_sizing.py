"""
Test Position Sizing Calculation for AI-Deployed Strategy

This script tests Week 3 AI position sizing integration by:
1. Loading an AI-deployed strategy from the database
2. Simulating what OrderExecutor would calculate
3. Verifying the tier multiplier and final lots calculation

Expected Result:
- Strategy 415: 86% confidence → HIGH tier → 2.0x multiplier
- Base lots: 1 → Final lots: 2
"""
import asyncio
import sys
from decimal import Decimal
from sqlalchemy import select

# Add parent directory to path
sys.path.insert(0, 'D:\\Abhay\\VibeCoding\\algochanakya\\backend')

from app.database import AsyncSessionLocal
from app.models.autopilot import AutoPilotStrategy
from app.services.ai.config_service import AIConfigService


async def test_position_sizing():
    """Test AI position sizing calculation for Strategy 415."""

    print("=" * 80)
    print("Week 3 AI Position Sizing - Automated Test")
    print("=" * 80)
    print()

    async with AsyncSessionLocal() as db:
        # 1. Load Strategy 415
        print("[Step 1] Loading Strategy 415 from database...")
        result = await db.execute(
            select(AutoPilotStrategy).where(AutoPilotStrategy.id == 415)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            print("[ERROR] Strategy 415 not found")
            return False

        print(f"[OK] Strategy loaded: {strategy.name}")
        print(f"   - ID: {strategy.id}")
        print(f"   - AI Deployed: {strategy.ai_deployed}")
        print(f"   - Confidence Score: {strategy.ai_confidence_score}%")
        print(f"   - Lots Tier: {strategy.ai_lots_tier}")
        print(f"   - Base Lots: {strategy.lots}")
        print(f"   - Status: {strategy.status}")
        print()

        # 2. Load AI Config
        print("[Step 2] Loading AI Config for user...")
        ai_config = await AIConfigService.get_or_create_config(strategy.user_id, db)

        if not ai_config:
            print("[ERROR] AI Config not found")
            return False

        print(f"[OK] AI Config loaded")
        print(f"   - AI Enabled: {ai_config.ai_enabled}")
        print(f"   - Autonomy Mode: {ai_config.autonomy_mode}")
        print(f"   - Sizing Mode: {ai_config.sizing_mode}")
        print(f"   - Base Lots: {ai_config.base_lots}")
        print(f"   - Confidence Tiers: {ai_config.confidence_tiers}")
        print()

        # 3. Calculate Position Sizing
        print("[Step 3] Calculating position sizing...")

        if not strategy.ai_deployed or not strategy.ai_confidence_score:
            print("[ERROR] Strategy is not AI-deployed or missing confidence score")
            return False

        if not ai_config.ai_enabled:
            print("[WARN] AI is not enabled in config")
            return False

        # Calculate lots using AIConfigService
        calculated_lots = AIConfigService.calculate_lots_for_confidence(
            config=ai_config,
            confidence=float(strategy.ai_confidence_score)
        )

        # Get tier details
        tier = AIConfigService.get_confidence_tier(
            config=ai_config,
            confidence=float(strategy.ai_confidence_score)
        )

        print(f"[OK] Position sizing calculated:")
        print(f"   - Confidence Score: {strategy.ai_confidence_score}%")
        print(f"   - Tier: {tier['name'] if tier else 'N/A'}")
        print(f"   - Multiplier: {tier.get('multiplier', 0)}x")
        print(f"   - Base Lots: {ai_config.base_lots}")
        print(f"   - Calculated Lots: {calculated_lots}")
        print()

        # 4. Verify Expected Results
        print("[Step 4] Verifying expected results...")
        print()

        expected_tier = "HIGH"
        expected_multiplier = 2.0
        expected_lots = 2

        test_results = []

        # Test 1: Tier Detection
        if tier and tier['name'] == expected_tier:
            print(f"[PASS] Test 1: Tier correctly identified as {expected_tier}")
            test_results.append(True)
        else:
            print(f"[FAIL] Test 1: Expected tier {expected_tier}, got {tier['name'] if tier else 'None'}")
            test_results.append(False)

        # Test 2: Multiplier Calculation
        actual_multiplier = tier.get('multiplier', 0) if tier else 0
        if actual_multiplier == expected_multiplier:
            print(f"[PASS] Test 2: Multiplier correctly calculated as {expected_multiplier}x")
            test_results.append(True)
        else:
            print(f"[FAIL] Test 2: Expected multiplier {expected_multiplier}x, got {actual_multiplier}x")
            test_results.append(False)

        # Test 3: Final Lots Calculation
        if calculated_lots == expected_lots:
            print(f"[PASS] Test 3: Final lots correctly calculated as {expected_lots}")
            test_results.append(True)
        else:
            print(f"[FAIL] Test 3: Expected {expected_lots} lots, got {calculated_lots} lots")
            test_results.append(False)

        # Test 4: Confidence Range
        if 86.0 <= float(strategy.ai_confidence_score) <= 100.0:
            print(f"[PASS] Test 4: Confidence score {strategy.ai_confidence_score}% in HIGH tier range (86-100%)")
            test_results.append(True)
        else:
            print(f"[FAIL] Test 4: Confidence score {strategy.ai_confidence_score}% not in expected range")
            test_results.append(False)

        print()
        print("=" * 80)
        print("Test Results Summary")
        print("=" * 80)
        print(f"Tests Passed: {sum(test_results)}/{len(test_results)}")
        print(f"Tests Failed: {len(test_results) - sum(test_results)}/{len(test_results)}")
        print()

        if all(test_results):
            print("[SUCCESS] ALL TESTS PASSED - AI Position Sizing Working Correctly!")
            print()
            print("Simulation of OrderExecutor behavior:")
            print(f"   When Strategy 415 is executed:")
            print(f"   1. OrderExecutor receives base lots = {strategy.lots}")
            print(f"   2. Detects ai_deployed = true, ai_confidence_score = {strategy.ai_confidence_score}%")
            print(f"   3. Calls AIConfigService.calculate_lots_for_confidence()")
            print(f"   4. Returns tier = {tier['name']}, multiplier = {tier['multiplier']}x")
            print(f"   5. Calculates final lots: {strategy.lots} x {tier['multiplier']} = {calculated_lots} lots")
            print(f"   6. Uses {calculated_lots} lots for order quantity calculation")
            print()
            return True
        else:
            print("[FAILURE] SOME TESTS FAILED - Review calculations above")
            print()
            return False


if __name__ == "__main__":
    success = asyncio.run(test_position_sizing())
    sys.exit(0 if success else 1)
