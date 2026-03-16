---
name: add-strategy-template
description: >
  Add a new options strategy template with legs config, Greek flags,
  and test fixtures for the strategy wizard and AI recommendations.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<strategy-name>"
version: "1.0.0"
synthesized: true
private: false
---

# Add Strategy Template

## STEP 1: Define Template Data

Required fields: name (snake_case), display_name, category (neutral/bullish/bearish/volatile), description, legs_config (array of {type: CE/PE, position: BUY/SELL, strike_offset: int}), max_profit, max_loss, market_outlook, volatility_preference (high_iv/low_iv), risk_level (low/medium/high), Greek flags (theta_positive, vega_positive, delta_neutral, gamma_risk), win_probability, difficulty_level (beginner/intermediate/advanced), tags array.

## STEP 2: Add to Seed Script

Add template to `backend/scripts/seed_strategies.py`.

## STEP 3: Add Test Fixture

In `backend/tests/conftest.py`, add a `@pytest_asyncio.fixture` following the pattern of `iron_condor_template` and other existing fixtures.

## STEP 4: Include in Seeded Templates

Add to the `seeded_templates` fixture parameter list for comprehensive test coverage.

## STEP 5: Test Wizard Recommendations

Verify the wizard recommends the template for its target outlook via POST to `/api/strategy-library/wizard/recommend`.

## STEP 6: Add to Regime-Strategy Scoring (Optional)

For AI-recommended strategies, add to `REGIME_STRATEGY_SCORES` dict in `backend/app/services/ai/strategy_recommender.py` with confidence scores per regime type.

## CRITICAL RULES

- legs_config MUST define type (CE/PE), position (BUY/SELL), and strike_offset
- Greek flags must be financially correct (theta_positive=True for credit/short strategies)
- category must match market_outlook (neutral strategy with bullish outlook is wrong)
- Test with wizard API to verify recommendation scoring works
